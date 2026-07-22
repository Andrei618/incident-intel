"""Run the RAG evaluation harness."""

import asyncio
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal
from uuid import UUID

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.evals import isolation  # isort: skip — must load first: sets env before incident_intel

from incident_intel.llm.openai_provider import OpenAIChatProvider
from incident_intel.models.document import Document, DocumentChunk
from incident_intel.services.chat_service import _build_messages
from incident_intel.services.classification_service import classify_query
from incident_intel.services.dispatch import dispatch
from incident_intel.services.sql_query_service import _count_phrase
from tests.evals import fixture_data
from tests.evals.metrics import precision_at_k, recall_at_k, reciprocal_rank_at_k

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RETRIEVAL_K = 5  # must match dispatch(..., limit=5) — the retrieval cutoff
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-set")
JUDGE_MODEL = os.getenv("OPENAI_MODEL_JUDGE", "gpt-4o")
JUDGE_PASS = 4  # pass/fail threshold for judge calibration
JUDGE_RUBRIC = """\
You are a strict evaluator of an IT-operations assistant. You receive a user QUESTION, \
the RETRIEVED CONTEXT the assistant was given, a human-written REFERENCE ANSWER, and the \
ANSWER TO GRADE. Score the answer to grade on two independent dimensions, each from 1 \
(worst) to 5 (best).

FAITHFULNESS - is every claim supported by the retrieved context?
- 5: fully grounded; nothing invented or contradicting the context.
- 3: mostly grounded, with a minor unsupported detail.
- 1: fabricates steps, commands, or facts absent from the context, or contradicts it.
If the context is empty or does not cover the question, an answer that honestly states it \
lacks the information is fully faithful (5). Inventing an answer with no supporting \
context is the worst failure (1).

RELEVANCE - does the answer address the question, completely?
- 5: directly and completely answers it, covering the key actions in the reference answer.
- 3: on topic but omits an important step, or includes irrelevant padding.
- 1: off topic, answers a different question, or declines when the context clearly \
contained the answer.
Judge completeness against the reference answer; an answer that drops its central action \
is incomplete. An honest refusal scores high on relevance only when the context genuinely \
lacks the answer.

Rules:
- Grade the two dimensions independently: a fluent, on-topic answer can still be \
unfaithful, and a faithful answer can still be irrelevant.
- Judge only what is written; do not reward length or confident tone.
- In your reasoning, give one or two sentences naming the specific claim or omission \
behind each score.
"""

judge_client = openai.AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=30.0,
    max_retries=2,
)


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


@dataclass
class CaseResult:
    """What the pipeline actually produced for one evaluation case.

    - case_id - id of the case in the golden dataset.
    - predicted_route - route chosen by classify_query.
    - actual_route - route the dispatcher actually used; differs from predicted after a fallback.
    - retrieved - (document_id, chunk_index) pairs in rank order, best first (empty for sql/clarify).
    - context - context the dispatcher produced; SQL counts are asserted against this.
    - answer - final answer text from the chat model.
    """

    case_id: str
    predicted_route: Literal["sql", "hybrid", "clarify"]
    actual_route: str
    retrieved: list[tuple[UUID, int]]
    context: str
    answer: str


@dataclass
class CaseScore:
    """One case's scores. Each judgment is None when it does not apply to the case.

    - case_id - id of the case in the golden dataset.
    - route_ok - the predicted route matched the expected route.
    - route_diverged - the dispatcher's actual route differed from the predicted one (a silent fallback).
    - recall - recall@k over the expected chunks (None for non-retrieval cases).
    - precision - precision@k over the expected chunks (None for non-retrieval cases).
    - rr - reciprocal rank of the first relevant chunk (None for non-retrieval cases).
    - sql_ok - both SQL layers passed: expected count-phrase in the context AND the count in the answer (None for non-SQL cases).
    - mentions_ok - every must_mention substring is present in the answer (None when the case has no must_mention).
    """

    case_id: str
    route_ok: bool
    route_diverged: bool
    recall: float | None
    precision: float | None
    rr: float | None
    sql_ok: bool | None
    mentions_ok: bool | None


class JudgeVerdict(BaseModel):
    """The LLM judge's structured verdict for one answer.

    - faithfulness - 1-5: is every claim grounded in the retrieved context?
    - relevance - 1-5: does the answer address the question, completely?
    - reasoning - one or two sentences justifying the two scores.
    """

    faithfulness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    reasoning: str


@dataclass
class JudgeResult:
    """The LLM judge's verdict for one case, keyed to the golden dataset by case_id.

    - case_id - id of the case in the golden dataset.
    - faithfulness - 1-5: is every claim grounded in the retrieved context?
    - relevance - 1-5: does the answer address the question?
    - reasoning - the judge's brief justification for the two scores.
    """

    case_id: str
    faithfulness: int
    relevance: int
    reasoning: str


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


async def run_case(
    session: AsyncSession,
    provider: OpenAIChatProvider,
    case: Case,
) -> CaseResult:
    """Run evaluation for one case."""
    intent = await classify_query(query=case.question)
    result = await dispatch(session=session, intent=intent, original_query=case.question)
    messages = _build_messages(
        context=result.context,
        message=case.question,
        history=[],
        sources=result.sources,
        route=result.route,
    )
    answer = await provider.generate(messages)
    return CaseResult(
        case_id=case.id,
        predicted_route=intent.route,
        actual_route=result.route,
        retrieved=[(s["document_id"], s["chunk_index"]) for s in result.sources],
        context=result.context,
        answer=answer,
    )


def score_case(case: Case, case_result: CaseResult, doc_ids: dict[str, UUID]) -> CaseScore:
    """Compute all deterministic scores for one case."""
    # route scoring
    route_ok = case.expected_route == case_result.predicted_route
    route_diverged = case_result.predicted_route != case_result.actual_route

    # retrieval scoring
    if case.expected_chunks is None:
        recall = precision = rr = None
    else:
        relevant = {(doc_ids[ec.doc_key], ec.chunk_index) for ec in case.expected_chunks}
        recall = recall_at_k(case_result.retrieved, relevant, RETRIEVAL_K)
        precision = precision_at_k(case_result.retrieved, relevant, RETRIEVAL_K)
        rr = reciprocal_rank_at_k(case_result.retrieved, relevant, RETRIEVAL_K)

    # SQL scoring
    if case.expected_count is None:
        sql_ok = None
    else:
        layer1 = _count_phrase(case.expected_count, "ticket") in case_result.context
        layer2 = re.search(rf"\b{case.expected_count}\b", case_result.answer) is not None
        sql_ok = layer1 and layer2

    # must_mention scoring
    if case.must_mention is None:
        mentions_ok = None
    else:
        mentions_ok = all(m.lower() in case_result.answer.lower() for m in case.must_mention)

    return CaseScore(
        case_id=case.id,
        route_ok=route_ok,
        route_diverged=route_diverged,
        recall=recall,
        precision=precision,
        rr=rr,
        sql_ok=sql_ok,
        mentions_ok=mentions_ok,
    )


async def run_all(dataset: Dataset) -> tuple[list[CaseResult], dict[str, UUID]]:
    """Resolve keys, run the drift gate, then drive every case."""
    async with isolation.database.Session() as session:
        doc_ids = await resolve_doc_keys(session)
        await verify_chunk_hashes(session, dataset, doc_ids)
        provider = OpenAIChatProvider(temperature=0.0)
        results = []
        cases = dataset.cases
        n = len(cases)
        for i, case in enumerate(cases, start=1):
            try:
                case_result = await run_case(session, provider, case)
                results.append(case_result)
                print(f"[{i}/{n}] {case.id} → {case_result.actual_route}")
            except Exception as e:
                print(f"FAILED {case.id}: {e}")
        return results, doc_ids


async def judge_answer(
    question: str, reference: str, context: str, answer: str
) -> JudgeVerdict | None:
    """Ask the LLM judge to grade one answer; returns None on refusal or parse failure."""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": JUDGE_RUBRIC},
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Reference answer:\n{reference}\n\n"
                f"Retrieved context:\n{context}\n\n"
                f"Answer to grade:\n{answer}"
            ),
        },
    ]
    response = await judge_client.chat.completions.parse(
        model=JUDGE_MODEL,
        messages=messages,
        response_format=JudgeVerdict,
        temperature=0.0,
    )
    message = response.choices[0].message
    if message.refusal is not None or message.parsed is None:
        return None
    return message.parsed


async def judge_all(dataset: Dataset, results: list[CaseResult]) -> list[JudgeResult]:
    """Grade each golden case's answer with the LLM judge (faithfulness + relevance).

    Only cases with a reference_answer (free-text hybrid/adversarial) are judged;
    SQL and clarify cases are skipped. Returns one JudgeResult per judged case.
    """
    cases_by_id = {c.id: c for c in dataset.cases}
    judge_results = []
    for case_result in results:
        case = cases_by_id[case_result.case_id]
        if case.reference_answer is None:  # only free-text answers get judged
            continue
        verdict = await judge_answer(
            question=case.question,
            reference=case.reference_answer,  # the ideal answer
            context=case_result.context,  # the ACTUALLY retrieved context
            answer=case_result.answer,  # the pipeline's final generated answer
        )
        if verdict is None:
            continue
        judge_results.append(
            JudgeResult(
                case_id=case_result.case_id,
                faithfulness=verdict.faithfulness,
                relevance=verdict.relevance,
                reasoning=verdict.reasoning,
            )
        )
    return judge_results


async def validate_judge(dataset: Dataset) -> tuple[int, int, int]:
    """Validate judge on calibration dataset (judge_calibration.json)."""
    raw = json.loads((Path(__file__).parent / "judge_calibration.json").read_text())
    cases_by_id = {c.id: c for c in dataset.cases}
    agreed = 0
    errored = 0
    for item in raw["items"]:
        ref = cases_by_id[item["base_case"]].reference_answer
        verdict = await judge_answer(
            question=item["question"],
            reference=ref,
            context=ref,
            answer=item["answer"],
        )
        if verdict is None:
            errored += 1
        else:
            predicted_pass = min(verdict.faithfulness, verdict.relevance) >= JUDGE_PASS
            expected_pass = item["expected_verdict"] == "pass"
            agrees = predicted_pass == expected_pass
            if agrees:
                agreed += 1
    return agreed, errored, len(raw["items"])


def score_all(
    dataset: Dataset, results: list[CaseResult], doc_ids: dict[str, UUID]
) -> list[CaseScore]:
    """Score all cases."""
    cases_by_id = {case.id: case for case in dataset.cases}
    scores = []
    for case_result in results:
        case = cases_by_id[case_result.case_id]
        scores.append(score_case(case, case_result, doc_ids))
    return scores


def main() -> None:
    """Guard the environment, then run the evaluation."""
    isolation.guard()
    print("bound to:", isolation.database.DATABASE_URL)
    dataset = load_dataset()
    os.environ["EVAL_TODAY"] = dataset.eval_today.isoformat()

    # drive + score
    results, doc_ids = asyncio.run(run_all(dataset))
    scores = score_all(dataset, results, doc_ids)
    correct = sum(s.route_ok for s in scores)
    diverged = sum(s.route_diverged for s in scores)
    print(f"routing: {correct}/{len(scores)} correct, {diverged} diverged")

    # validate judge
    agreed, errored, total = asyncio.run(validate_judge(dataset))
    print(f"agreed: {agreed}/{total}, errored: {errored}")

    # judge golden dataset
    asyncio.run(judge_all(dataset, results))


if __name__ == "__main__":
    main()
