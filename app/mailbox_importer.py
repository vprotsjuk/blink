"""Phase 2A mailbox package parsing and local transport state primitives.

This module intentionally has no agenda mutation and no watcher/iCloud
production wiring. It operates on caller-provided roots so tests can use
temporary directories safely.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agenda_store import agenda_lock


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SAFE_EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_READY_RE = re.compile(r"^(?P<id>[0-9a-f-]+)\.ready$")
_ATTACHMENT_RE = re.compile(r"^(?P<id>[0-9a-f-]+)\.attachment\.(?P<ext>[A-Za-z0-9][A-Za-z0-9._-]*)$")
_INTERNAL_CREATE_FIELDS = {
    "id",
    "enabled",
    "requires_done",
    "done",
    "done_at",
    "tags",
    "recurrence",
    "series_id",
    "reminders_minutes_before",
    "blinker_minutes_before",
}


class PendingSync(RuntimeError):
    """The ready marker exists but iCloud bytes are not available yet."""


class MalformedPackage(ValueError):
    """The package is present but violates the transport contract."""


@dataclass(frozen=True)
class PackageCandidate:
    root: Path
    transport_id: str
    kind: str
    json_path: Path | None
    ready_path: Path
    attachment_paths: tuple[Path, ...]
    unexpected_attachment_paths: tuple[Path, ...] = ()

    @property
    def package_paths(self) -> tuple[Path, ...]:
        paths = [path for path in (self.json_path, *self.attachment_paths, self.ready_path) if path]
        return tuple(paths)


@dataclass(frozen=True)
class ParsedCommand:
    kind: str
    transport_id: str
    event_id: str | None = None
    transfer_id: str | None = None
    title: str | None = None
    description: str | None = None
    start: str | None = None
    reminder_offsets: tuple[int, ...] = ()
    attention_level: str | None = None
    blinker_minutes_before: int | None = None
    created_at: str | None = None
    attachment_path: Path | None = None
    original_filename: str | None = None
    payload: dict[str, Any] | None = None


def _validate_uuid4(value: Any, label: str) -> str:
    text = str(value or "").strip().lower()
    if not _UUID_RE.fullmatch(text):
        raise MalformedPackage(f"{label} must be a canonical UUIDv4")
    try:
        parsed = uuid.UUID(text)
    except ValueError as exc:
        raise MalformedPackage(f"{label} must be a UUIDv4") from exc
    if parsed.version != 4:
        raise MalformedPackage(f"{label} must be a UUIDv4")
    return text


def _validate_event_id(value: Any) -> str:
    text = str(value or "").strip()
    if not _SAFE_EVENT_ID.fullmatch(text):
        raise MalformedPackage("event_id must be a safe relative identifier")
    return text


def _regular_local(path: Path) -> bool:
    return path.exists() and not path.is_symlink() and path.is_file()


def _safe_display_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text in {".", ".."} or "/" in text or "\\" in text or "\x00" in text:
        raise MalformedPackage("attachment original_filename is not a display name")
    return text


def discover_packages(root: Path) -> list[PackageCandidate]:
    """Discover only ready-marked UUID packages; unrelated files are ignored."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return []
    candidates: list[PackageCandidate] = []
    for ready in sorted(root.iterdir(), key=lambda item: item.name):
        if ready.is_symlink():
            continue
        match = _READY_RE.fullmatch(ready.name)
        if not match:
            continue
        transport_id = match.group("id").lower()
        try:
            _validate_uuid4(transport_id, "ready filename")
        except MalformedPackage:
            continue
        event_json = root / f"{transport_id}.event.json"
        done_json = root / f"{transport_id}.done.json"
        existing_json = [path for path in (event_json, done_json) if path.exists()]
        if len(existing_json) == 1:
            json_path = existing_json[0]
            kind = "CREATE_EVENT" if json_path == event_json else "DONE"
        elif len(existing_json) > 1:
            json_path = existing_json[0]
            kind = "AMBIGUOUS"
        else:
            json_path = None
            kind = "UNKNOWN"
        attachment_like = tuple(
            path
            for path in sorted(root.iterdir(), key=lambda item: item.name)
            if path.name.startswith(f"{transport_id}.attachment.")
        )
        attachments = tuple(
            path
            for path in attachment_like
            if _ATTACHMENT_RE.fullmatch(path.name)
            and path.name.split(".", 1)[0].lower() == transport_id
        )
        candidates.append(
            PackageCandidate(
                root,
                transport_id,
                kind,
                json_path,
                ready,
                attachments,
                tuple(path for path in attachment_like if path not in attachments),
            )
        )
    return candidates


def _load_json(candidate: PackageCandidate) -> dict[str, Any]:
    if candidate.json_path is None or not candidate.json_path.exists():
        raise PendingSync("ready marker is present but JSON is not locally available")
    if not _regular_local(candidate.json_path):
        raise MalformedPackage("package JSON must be a regular non-symlink file")
    try:
        raw = json.loads(candidate.json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MalformedPackage("package JSON is invalid") from exc
    if not isinstance(raw, dict):
        raise MalformedPackage("package JSON must be an object")
    return raw


def _validate_attachment(candidate: PackageCandidate, payload: dict[str, Any]) -> tuple[Path | None, str | None]:
    if len(candidate.attachment_paths) > 1:
        raise MalformedPackage("CREATE_EVENT v1 permits at most one attachment")
    declared = payload.get("attachment")
    if declared is None:
        if candidate.attachment_paths:
            raise MalformedPackage("undeclared attachment file")
        return None, None
    if not isinstance(declared, dict):
        raise MalformedPackage("attachment must be an object")
    if not candidate.attachment_paths:
        raise PendingSync("ready marker is present but attachment is not locally available")
    attachment_path = candidate.attachment_paths[0]
    if not _regular_local(attachment_path):
        raise MalformedPackage("attachment must be a regular non-symlink file")
    basename = declared.get("basename")
    if basename != attachment_path.name:
        raise MalformedPackage("attachment basename does not match package file")
    original = _safe_display_name(declared.get("original_filename"))
    return attachment_path, original


def _parse_aware_timestamp(value: Any, label: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MalformedPackage(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MalformedPackage(f"{label} must include an explicit UTC offset")
    return text


def _parse_reminders(payload: dict[str, Any]) -> tuple[int, ...]:
    intent = payload.get("reminder_intent")
    if not isinstance(intent, dict) or not isinstance(intent.get("offsets_minutes_before"), list):
        raise MalformedPackage("reminder_intent.offsets_minutes_before is required")
    values = intent["offsets_minutes_before"]
    if not values:
        raise MalformedPackage("at least one reminder offset is required")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise MalformedPackage("reminder offsets must be non-negative integers")
    return tuple(sorted(set(values), reverse=True))


def _parse_blinker(payload: dict[str, Any]) -> int:
    intent = payload.get("blinker_intent")
    if not isinstance(intent, dict):
        raise MalformedPackage("blinker_intent is required")
    value = intent.get("minutes_before")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MalformedPackage("blinker_intent.minutes_before must be a non-negative integer")
    return value


def _parse_done(candidate: PackageCandidate, payload: dict[str, Any]) -> ParsedCommand:
    if payload.get("version") != 1 or payload.get("type") != "DONE":
        raise MalformedPackage("invalid DONE version/type")
    command_id = _validate_uuid4(payload.get("command_id"), "command_id")
    if command_id != candidate.transport_id:
        raise MalformedPackage("command_id does not match filename")
    if "occurrence_id" in payload:
        raise MalformedPackage("occurrence_id is not part of production DONE v1")
    event_id = _validate_event_id(payload.get("event_id"))
    created_at = payload.get("created_at")
    if created_at is not None:
        created_at = _parse_aware_timestamp(created_at, "created_at")
    return ParsedCommand(
        kind="DONE",
        transport_id=command_id,
        event_id=event_id,
        created_at=created_at,
        payload=payload,
    )


def _parse_create(candidate: PackageCandidate, payload: dict[str, Any]) -> ParsedCommand:
    if payload.get("version") != 1 or payload.get("type") != "CREATE_EVENT":
        raise MalformedPackage("invalid CREATE_EVENT version/type")
    transfer_id = _validate_uuid4(payload.get("transfer_id"), "transfer_id")
    if transfer_id != candidate.transport_id:
        raise MalformedPackage("transfer_id does not match filename")
    forbidden = _INTERNAL_CREATE_FIELDS.intersection(payload)
    if forbidden:
        raise MalformedPackage(f"internal fields are not CREATE v1 input: {sorted(forbidden)}")
    title = str(payload.get("title") or "").strip()
    if not title:
        raise MalformedPackage("title is required")
    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise MalformedPackage("description must be a string")
    start = _parse_aware_timestamp(payload.get("start"), "start")
    attention = str(payload.get("attention_level") or "").strip().lower()
    if attention not in {"green", "yellow", "red"}:
        raise MalformedPackage("attention_level must be green, yellow, or red")
    reminders = _parse_reminders(payload)
    blinker = _parse_blinker(payload)
    created_at = payload.get("created_at")
    if created_at is not None:
        created_at = _parse_aware_timestamp(created_at, "created_at")
    attachment_path, original = _validate_attachment(candidate, payload)
    return ParsedCommand(
        kind="CREATE_EVENT",
        transport_id=transfer_id,
        transfer_id=transfer_id,
        title=title,
        description=description,
        start=start,
        reminder_offsets=reminders,
        attention_level=attention,
        blinker_minutes_before=blinker,
        created_at=created_at,
        attachment_path=attachment_path,
        original_filename=original,
        payload=payload,
    )


def parse_package(candidate: PackageCandidate) -> ParsedCommand:
    if not _regular_local(candidate.ready_path):
        raise PendingSync("ready marker is not locally available")
    if candidate.kind == "AMBIGUOUS":
        raise MalformedPackage("package contains multiple command JSON files")
    if candidate.unexpected_attachment_paths:
        raise MalformedPackage("package contains an invalid attachment filename")
    payload = _load_json(candidate)
    if candidate.kind == "DONE":
        return _parse_done(candidate, payload)
    if candidate.kind == "CREATE_EVENT":
        return _parse_create(candidate, payload)
    raise MalformedPackage("package JSON shape is not a supported v1 command")


def classify_package(candidate: PackageCandidate) -> str:
    try:
        parse_package(candidate)
    except PendingSync:
        return "pending_sync"
    except MalformedPackage:
        return "malformed"
    return "ready"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class JournalStore:
    def __init__(self, blink_root: Path):
        self.root = Path(blink_root) / "mailbox" / "journal"

    def path_for(self, transport_id: str) -> Path:
        _validate_uuid4(transport_id, "transport_id")
        return self.root / f"{transport_id}.json"

    def write(self, transport_id: str, record: dict[str, Any]) -> None:
        payload = {"version": 1, "transport_id": transport_id, **record}
        _atomic_write_json(self.path_for(transport_id), payload)

    def load(self, transport_id: str) -> dict[str, Any]:
        path = self.path_for(transport_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise KeyError(transport_id) from None
        if not isinstance(payload, dict) or payload.get("transport_id") != transport_id:
            raise ValueError("invalid journal record")
        return payload

    def pending(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and payload.get("transport_id"):
                records.append(payload)
        return records


class ProcessedLedger:
    def __init__(self, blink_root: Path):
        self.mailbox_root = Path(blink_root) / "mailbox"
        self.path = self.mailbox_root / "processed_commands.json"
        self.lock_path = self.mailbox_root / "processed_commands.lock"

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("records"), list):
            raise ValueError("invalid processed command ledger")
        return [record for record in payload["records"] if isinstance(record, dict)]

    def contains(self, transport_id: str) -> bool:
        _validate_uuid4(transport_id, "transport_id")
        return any(record.get("transport_id") == transport_id for record in self.records())

    def record(self, transport_id: str, kind: str, result: str) -> None:
        _validate_uuid4(transport_id, "transport_id")
        with agenda_lock(self.lock_path):
            records = self.records()
            if any(item.get("transport_id") == transport_id for item in records):
                return
            records.append({
                "transport_id": transport_id,
                "type": kind,
                "result": result,
                "recorded_at": datetime.now().astimezone().isoformat(),
            })
            _atomic_write_json(self.path, {"version": 1, "records": records})


def stage_attachment(command: ParsedCommand, blink_root: Path) -> Path:
    if command.attachment_path is None:
        raise ValueError("command has no attachment")
    source = command.attachment_path
    if not _regular_local(source):
        raise PendingSync("attachment bytes are not locally available")
    destination_root = Path(blink_root) / "mailbox" / "journal" / "staging" / command.transport_id
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name
    fd, temporary = tempfile.mkstemp(prefix=f".{source.name}.", suffix=".tmp", dir=destination_root)
    try:
        with os.fdopen(fd, "wb") as target, source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return destination


def quarantine_package(candidate: PackageCandidate, blink_root: Path, reason: str) -> Path:
    target = Path(blink_root) / "mailbox" / "quarantine" / candidate.transport_id
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in candidate.package_paths:
        if not _regular_local(source):
            continue
        destination = target / source.name
        shutil.copy2(source, destination)
        copied.append(source)
    _atomic_write_json(target / "reason.json", {"version": 1, "reason": reason, "transport_id": candidate.transport_id})
    for source in copied:
        try:
            source.unlink()
        except FileNotFoundError:
            pass
    return target
