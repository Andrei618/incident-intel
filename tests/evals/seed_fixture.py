"""Seed the eval fixture: schema, documents, and tickets for the RAG eval."""

from tests.evals import isolation  # isort: skip — must load first: sets env before incident_intel
import asyncio

from sqlalchemy import text

from incident_intel.models.base import Base


async def create_schema() -> None:
    """Drop and recreate all tables in the eval DB (clean, rebuildable)."""
    async with isolation.database.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def main() -> None:
    """Guard the environment, then create the eval DB schema."""
    isolation.guard()
    asyncio.run(create_schema())
    print("schema created in", isolation.database.DATABASE_URL)


if __name__ == "__main__":
    main()
