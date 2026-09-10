"""Blink-local attachment metadata and path helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any


_SAFE_OWNER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _validated_owner_id(value: Any) -> str:
    owner_id = str(value or "").strip()
    if not owner_id or not _SAFE_OWNER_ID.fullmatch(owner_id):
        raise ValueError("attachment owner id must be a safe relative identifier")
    return owner_id


def owner_id_for_event(event: dict[str, Any]) -> str:
    """Return the production attachment owner for one event occurrence."""
    return _validated_owner_id(event.get("id"))


def legacy_owner_id_for_event(event: dict[str, Any]) -> str:
    """Return the pre-migration shared owner used only for legacy fixtures."""
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


def manifest_for_event(blink_root: Path, event: dict[str, Any]) -> dict[str, Any]:
    """Build metadata from the canonical event-ID folder on disk."""
    owner_id = owner_id_for_event(event)
    count = len(_visible_files(attachments_root(Path(blink_root)) / owner_id))
    return {"owner_id": owner_id, "count": count, "has_files": count > 0}


def _visible_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        (item for item in folder.iterdir() if not item.name.startswith(".") and item.is_file()),
        key=lambda item: item.name.casefold(),
    )


def _collision_free_path(folder: Path, name: str) -> Path:
    candidate = folder / Path(name).name
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while candidate.exists():
        candidate = folder / (f"{stem} ({index}){suffix}")
        index += 1
    return candidate


def _same_bytes(left: Path, right: Path) -> bool:
    try:
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as left_handle, right.open("rb") as right_handle:
            while True:
                left_chunk = left_handle.read(1024 * 1024)
                right_chunk = right_handle.read(1024 * 1024)
                if left_chunk != right_chunk:
                    return False
                if not left_chunk:
                    return True
    except OSError:
        return False


def migrate_legacy_series_attachments(
    blink_root: Path, events: list[dict[str, Any]]
) -> dict[str, int]:
    """Copy legacy shared-series files into occurrence folders without loss.

    The legacy source is never removed. Existing identical files are treated as
    already migrated, while different collisions receive deterministic suffixes.
    This makes retries safe and keeps user-created target files intact.
    """
    root = Path(blink_root)
    source_root = attachments_root(root)
    migrated: dict[str, int] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if not isinstance(event, dict) or not event.get("series_id"):
            continue
        try:
            series_id = _validated_owner_id(event.get("series_id"))
            event_id = _validated_owner_id(event.get("id"))
        except ValueError:
            continue
        if series_id == event_id:
            continue
        groups.setdefault(series_id, []).append(event)
    for series_id, occurrences in groups.items():
        source = source_root / series_id
        source_files = _visible_files(source)
        if not source_files:
            continue
        for event in occurrences:
            event_id = _validated_owner_id(event["id"])
            target = source_root / event_id
            target.mkdir(parents=True, exist_ok=True)
            copied = 0
            for source_file in source_files:
                same_name = target / source_file.name
                if same_name.exists() and _same_bytes(source_file, same_name):
                    continue
                if any(_same_bytes(source_file, existing) for existing in _visible_files(target)):
                    continue
                destination = _collision_free_path(target, source_file.name)
                shutil.copy2(source_file, destination)
                copied += 1
            if copied:
                migrated[event_id] = migrated.get(event_id, 0) + copied
    return migrated
