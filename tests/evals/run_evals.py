"""Run the RAG evaluation harness."""

import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.evals import isolation  # isort: skip — must load first: sets env before incident_intel

from incident_intel.models.document import Document, DocumentChunk
from tests.evals import fixture_data

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


@dataclass
class ExpectedChunk:
    """One chunk of a document.

    - doc_key - stable kebab-case key identifying the source document (defined in fixture_data.py).
    - chunk_index - index of a chunk within the document.
    - content_sha256 - SHA-256 hash of the chunk's content (used by the drift gate).
    """

    doc_key: str
    chunk_index: int
    content_sha256: str


@dataclass
class Case:
    """Data of one evaluation case.

    - id - identifier of a case.
    - category - category of the case: hybrid, sql_count, sql_list, clarify, adversarial.
    - question - question from a user.
    - expected_route - the route the question is sent to: hybrid, sql, clarify.
    - expected_chunks - list of expected chunks (hybrid route).
    - expected_count - expected number of tickets (sql route).
    - reference_answer - the ideal answer, used as the reference the LLM judge scores against (hybrid route).
    - must_mention - keywords from a document chunk that must be in the LLM answer (hybrid route).
    - note - note that describes the purpose of the case (sql route).
    - difficulty - category of case difficulty: easy, medium, hard.
    """

    id: str
    category: str
    question: str
    expected_route: str
    expected_chunks: list[ExpectedChunk] | None = None
    expected_count: int | None = None
    reference_answer: str | None = None
    must_mention: list[str] | None = None
    note: str | None = None
    difficulty: str | None = None


@dataclass
class Dataset:
    """Wrapper of all evaluation cases and metadata.

    - dataset_version - version of golden dataset.
    - eval_today - the frozen date used as "today", so relative-date routing (e.g. "last 7 days") is reproducible.
    - cases - list of evaluation cases.
    """

    dataset_version: str
    eval_today: date
    cases: list[Case]


def load_dataset(path: Path = DATASET_PATH) -> Dataset:
    """Load the golden dataset from JSON file."""
    raw = json.loads(path.read_text())
    eval_today = date.fromisoformat(raw["eval_today"])
    cases = []
    for c in raw["cases"]:
        raw_chunks = c.get("expected_chunks")
        expected_chunks = (
            [ExpectedChunk(**ch) for ch in raw_chunks] if raw_chunks is not None else None
        )
        cases.append(
            Case(
                id=c["id"],
                category=c["category"],
                question=c["question"],
                expected_route=c["expected_route"],
                expected_chunks=expected_chunks,
                expected_count=c.get("expected_count"),
                reference_answer=c.get("reference_answer"),
                must_mention=c.get("must_mention"),
                note=c.get("note"),
                difficulty=c.get("difficulty"),
            )
        )
    return Dataset(raw["dataset_version"], eval_today, cases)


async def resolve_doc_keys(session: AsyncSession) -> dict[str, UUID]:
    """Provide a bridge between doc_key from golden cases and document_id from retrieved chunks.

    Bridge: doc_key → title → id.
    """
    doc_key_to_title = {d["doc_key"]: d["title"] for d in fixture_data.DOCUMENTS}
    result = await session.execute(select(Document.id, Document.title))
    title_to_id = {title: id_ for id_, title in result.all()}
    return {doc_key: title_to_id[title] for doc_key, title in doc_key_to_title.items()}


async def verify_chunk_hashes(
    session: AsyncSession, dataset: Dataset, doc_ids: dict[str, UUID]
) -> None:
    """Verify that no chunk content has drifted from the pinned hashes.

    SystemExit: if an expected chunk is missing from the live database,
        or its content hash differs from the hash pinned in the golden dataset.
    """
    stmt = select(DocumentChunk.document_id, DocumentChunk.chunk_index, DocumentChunk.content)
    result = await session.execute(stmt)
    live = {
        (document_id, chunk_index): hashlib.sha256(content.encode()).hexdigest()
        for document_id, chunk_index, content in result
    }
    collected_mismatches = []
    for case in dataset.cases:
        if case.expected_chunks is None:  # for SQL/clarify cases
            continue
        for ec in case.expected_chunks:
            document_id = doc_ids[ec.doc_key]
            live_sha = live.get((document_id, ec.chunk_index))
            if live_sha is None:
                collected_mismatches.append(f"{case.id}: {ec.doc_key}#{ec.chunk_index} not found")
            elif live_sha != ec.content_sha256:
                collected_mismatches.append(
                    f"{case.id}: {ec.doc_key}#{ec.chunk_index}: sha256 mismatch"
                )
    if collected_mismatches:
        sys.exit(
            f"REFUSING: Mismatches between chunks content in live database and golden dataset are found: {collected_mismatches}"
        )


async def run_eval(dataset: Dataset) -> None:
    """Async part of evaluation: resolution of doc_key and drift gate."""
    async with isolation.database.Session() as session:
        doc_ids = await resolve_doc_keys(session)
        await verify_chunk_hashes(session, dataset, doc_ids)


def main() -> None:
    """Guard the environment, then run the evaluation."""
    isolation.guard()
    print("bound to:", isolation.database.DATABASE_URL)
    dataset = load_dataset()
    os.environ["EVAL_TODAY"] = dataset.eval_today.isoformat()
    asyncio.run(run_eval(dataset))


if __name__ == "__main__":
    main()
