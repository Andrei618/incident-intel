"""Seed the eval fixture: schema, documents, and tickets for the RAG eval."""

from tests.evals import isolation  # isort: skip — must load first: sets env before incident_intel
import asyncio
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.base import Base
from incident_intel.models.service import Service
from incident_intel.schemas.document import DocumentCreate
from incident_intel.services.document_service import create_document
from tests.evals import fixture_data

SERVICES = ["payment-service", "api-gateway", "auth-service", "monitoring", "infra-vpn"]


async def create_schema() -> None:
    """Drop and recreate all tables in the eval DB (clean, rebuildable)."""
    async with isolation.database.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def seed_services(session: AsyncSession) -> dict[str, UUID]:
    """Create the eval services; return {name: id} for document FKs."""
    ids: dict[str, UUID] = {}
    for name in SERVICES:
        service = Service(name=name, description="Test description of service " + name)
        session.add(service)
        await session.flush()
        ids[name] = service.id
    await session.commit()
    return ids


async def seed_documents(session: AsyncSession, service_ids: dict[str, UUID]) -> None:
    """Create documents with chunking and embedding."""
    for d in fixture_data.DOCUMENTS:
        data = DocumentCreate(
            service_id=service_ids[d["service"]],
            title=d["title"],
            doc_type=d["doc_type"],
            content=d["content"],
        )
        await create_document(session, data)


async def seed_all() -> None:
    """Create the schema, then seed the eval fixture (services, …)."""
    await create_schema()
    async with isolation.database.Session() as session:
        service_ids = await seed_services(session)
        await seed_documents(session, service_ids)
    print("schema created in", isolation.database.DATABASE_URL)
    print("services ids", service_ids)


def main() -> None:
    """Guard the environment, then seed the eval fixture."""
    isolation.guard()
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
