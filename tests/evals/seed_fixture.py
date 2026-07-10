"""Seed the eval fixture: schema, documents, and tickets for the RAG eval."""

import hashlib
import json
from pathlib import Path

from tests.evals import isolation  # isort: skip — must load first: sets env before incident_intel
import asyncio
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.base import Base
from incident_intel.models.document import DocumentChunk
from incident_intel.models.service import Service
from incident_intel.schemas.document import DocumentCreate
from incident_intel.services.document_service import create_document
from tests.evals import fixture_data

SERVICES = ["payment-service", "api-gateway", "auth-service", "monitoring", "infra-vpn"]
MANIFEST_PATH = Path(__file__).parent / "fixture_manifest.json"


async def create_schema() -> None:
    """Drop and recreate all tables in the eval DB (clean, rebuildable)."""
    async with isolation.database.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def seed_services(session: AsyncSession) -> dict[str, UUID]:
    """Create the eval services; return {name: id} for document FKs."""
    service_ids: dict[str, UUID] = {}
    for name in SERVICES:
        service = Service(name=name, description="Test description of service " + name)
        session.add(service)
        await session.flush()
        service_ids[name] = service.id
    await session.commit()
    return service_ids


async def seed_documents(session: AsyncSession, service_ids: dict[str, UUID]) -> dict[str, UUID]:
    """Create documents; return {doc_key: document_id} for the manifest."""
    doc_ids: dict[str, UUID] = {}
    for d in fixture_data.DOCUMENTS:
        data = DocumentCreate(
            service_id=service_ids[d["service"]],
            title=d["title"],
            doc_type=d["doc_type"],
            content=d["content"],
        )
        document = await create_document(session, data)
        doc_ids[d["doc_key"]] = document.id
    return doc_ids


async def build_manifest(session: AsyncSession, doc_ids: dict[str, UUID]) -> None:
    """Write {doc_key: [{chunk_index, content_sha256}]} to the fixture manifest."""
    manifest: dict[str, list[dict[str, object]]] = {}
    for doc_key, document_id in doc_ids.items():
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        manifest[doc_key] = [
            {
                "chunk_index": c.chunk_index,
                "content_sha256": hashlib.sha256(c.content.encode()).hexdigest(),
            }
            for c in chunks
        ]
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


async def seed_all() -> None:
    """Create the schema, then seed the eval fixture (services, …)."""
    await create_schema()
    async with isolation.database.Session() as session:
        service_ids = await seed_services(session)
        doc_ids = await seed_documents(session, service_ids)
        await build_manifest(session, doc_ids)
    print(
        f"seeded {len(service_ids)} services, {len(doc_ids)} documents into {isolation.database.DATABASE_URL}"
    )


def main() -> None:
    """Guard the environment, then seed the eval fixture."""
    isolation.guard()
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
