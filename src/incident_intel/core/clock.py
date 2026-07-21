"""Clock helper — the single source of "today" for prompt building."""

import os
from datetime import UTC, datetime


def today_str() -> str:
    """Returns the EVAL_TODAY override when set, otherwise the current UTC date."""
    override = os.getenv("EVAL_TODAY")
    if override:
        return override
    return datetime.now(UTC).strftime("%Y-%m-%d")
