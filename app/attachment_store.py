"""Blink-local attachment metadata and path helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_SAFE_OWNER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _validated_owner_id(value: Any) -> str:
    owner_id = str(value or "").strip()
    if not owner_id or not _SAFE_OWNER_ID.fullmatch(owner_id):
        raise ValueError("attachment owner id must be a safe relative identifier")
    return owner_id


def owner_id_for_event(event: dict[str, Any]) -> str:
    return _validated_owner_id(event.get("series_id") or event.get("id"))


def attachments_root(blink_root: Path) -> Path:
    return Path(blink_root) / "event_data" / "attachments"


def draft_root(blink_root: Path) -> Path:
    return Path(blink_root) / "event_data" / "drafts"


def attachment_manifest(raw: Any, event: dict[str, Any]) -> dict[str, Any]:
    owner_id = owner_id_for_event(event)
    if not isinstance(raw, dict):
        return {"owner_id": owner_id, "count": 0, "has_files": False}
    raw_owner = str(raw.get("owner_id") or owner_id).strip()
    if raw_owner != owner_id:
        raw_owner = owner_id
    try:
        count = int(raw.get("count", 0))
    except (TypeError, ValueError):
        count = 0
    count = max(count, 0)
    has_files = bool(raw.get("has_files")) and count > 0
    return {"owner_id": raw_owner, "count": count, "has_files": has_files}
