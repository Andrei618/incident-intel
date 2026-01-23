"""Seed database with development data."""

import asyncio

from sqlalchemy import text

from incident_intel.core.database import engine


async def seed_services() -> None:
    """Create test services in the database."""
    services = [
        {
            "name": "Payment API",
            "description": "Stripe payment processing service",
        },
        {
            "name": "Auth Service",
            "description": "OAuth2 authentication service",
        },
        {
            "name": "Database Cluster",
            "description": "PostgreSQL primary database cluster",
        },
    ]

    async with engine.begin() as conn:
        for service in services:
            result = await conn.execute(
                text("""
                    INSERT INTO services (name, description)
                    VALUES (:name, :description)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id, name
                """),
                service,
            )
            row = result.fetchone()
            if row:
                print(f"  ✅ Created service: {row[1]} ({row[0]})")
            else:
                print(f"  ⏭️  Service already exists: {service['name']}")


async def main() -> None:
    """Run all seed functions."""
    print("🌱 Seeding database...")
    await seed_services()
    print("✅ Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
