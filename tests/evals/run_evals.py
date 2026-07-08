"""Run the RAG evaluation harness."""

import asyncio
import os
import sys

from dotenv import load_dotenv

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_intel_eval"
)
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # known-unreachable - Redis off
load_dotenv(override=False)

from incident_intel.core import database  # noqa: E402
from incident_intel.core.redis import REDIS_URL, check_redis_connection  # noqa: E402


def _guard() -> None:
    """Refuse to run unless the environment is isolated (eval DB, Redis off, real key, not pytest)."""
    # --- guard 1: refuse to run against anything but an _eval database ---
    db_name = database.DATABASE_URL.rsplit("/", 1)[-1]
    if not db_name.endswith("_eval"):
        sys.exit(f"REFUSING: bound to {db_name!r}, not an _eval database")

    # --- guard 2: never run under pytest (its autouse fixtures fake embeddings/Redis) ---
    if "pytest" in sys.modules:
        sys.exit(
            "REFUSING: do not run the eval under pytest — autouse fixtures fake embeddings/Redis"
        )

    # guard 3a (cheap): never point at the default Redis — even if it's momentarily down
    if REDIS_URL == "redis://localhost:6379/0":
        sys.exit("REFUSING: REDIS_URL is the default — set a known-unreachable endpoint")

    # guard 3b (authoritative): prove it's actually unreachable right now
    if asyncio.run(check_redis_connection()):
        sys.exit("REFUSING: Redis is reachable — it must be disabled (embedding-cache leakage)")

    # guard 4: real OpenAI calls need a key — fail fast unless this is a --dry-run
    dry_run = "--dry-run" in sys.argv
    if not dry_run and not os.environ.get("OPENAI_API_KEY"):
        sys.exit(
            "REFUSING: OPENAI_API_KEY is not set (needed for embeddings/chat; use --dry-run to skip)"
        )


def main() -> None:
    """Guard the environment, then run the evaluation."""
    _guard()
    print("bound to:", database.DATABASE_URL)


if __name__ == "__main__":
    main()
