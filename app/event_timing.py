"""Shared event timing rules used by lifecycle and notification layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def effective_event_start(event: dict[str, Any]) -> datetime | None:
    """Return the canonical event start.

    Kept as a compatibility helper while obsolete fields are migrated out.
    """
    return parse_aware_timestamp(event.get("start"))
