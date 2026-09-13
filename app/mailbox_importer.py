"""Phase 2A mailbox package parsing and local transport state primitives.

This module intentionally has no agenda mutation and no watcher/iCloud
production wiring. It operates on caller-provided roots so tests can use
temporary directories safely.
"""

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from app.agenda_store import agenda_lock


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SHORTCUTS_TRANSPORT_RE = re.compile(r"^[0-9]{14}-[0-9]{9}$")
_SAFE_EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_READY_RE = re.compile(r"^(?P<id>[0-9a-f-]+)\.ready$")
_ATTACHMENT_RE = re.compile(r"^(?P<id>[A-Za-z0-9-]+)\.attachment\.(?P<ext>[A-Za-z0-9][A-Za-z0-9._-]*)$")
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


def _is_iCloud_pending_error(exc: OSError) -> bool:
    """Return whether macOS reported an iCloud placeholder still syncing."""
    return exc.errno == errno.EDEADLK


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
        paths = [
            path
            for path in (
                self.json_path,
                *self.attachment_paths,
                *self.unexpected_attachment_paths,
                self.ready_path,
            )
            if path
        ]
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


def _validate_transport_id(value: Any, label: str) -> str:
    text = str(value or "").strip().lower()
    if _SHORTCUTS_TRANSPORT_RE.fullmatch(text):
        return text
    if not _UUID_RE.fullmatch(text):
        raise MalformedPackage(f"{label} must be yyyyMMddHHmmss-9digit-random or UUIDv4")
    try:
        parsed = uuid.UUID(text)
    except ValueError as exc:
        raise MalformedPackage(f"{label} must be a supported transport ID") from exc
    if parsed.version != 4:
        raise MalformedPackage(f"{label} must be a supported transport ID")
    return text


# Backward-compatible private name retained for existing callers/tests.
_validate_uuid4 = _validate_transport_id


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
    """Discover only ready-marked strict transport-ID packages."""
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
            _validate_transport_id(transport_id, "ready filename")
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
    except OSError as exc:
        if _is_iCloud_pending_error(exc):
            raise PendingSync("package JSON is still syncing") from exc
        raise MalformedPackage("package JSON is invalid") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
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


def _parse_flat_reminders(payload: dict[str, Any]) -> tuple[int, ...]:
    raw = payload.get("reminder_offsets")
    if not isinstance(raw, str) or not raw.strip():
        raise MalformedPackage("reminder_offsets must be a non-empty string")
    tokens = [token.strip() for token in raw.split(",")]
    if not tokens or any(not token or not token.isdigit() for token in tokens):
        raise MalformedPackage("reminder_offsets must contain comma-separated non-negative integers")
    return tuple(sorted({int(token) for token in tokens}, reverse=True))


def _parse_blinker(payload: dict[str, Any]) -> int:
    intent = payload.get("blinker_intent")
    if not isinstance(intent, dict):
        raise MalformedPackage("blinker_intent is required")
    value = intent.get("minutes_before")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MalformedPackage("blinker_intent.minutes_before must be a non-negative integer")
    return value


def _parse_flat_blinker(payload: dict[str, Any]) -> int:
    value = payload.get("blinker_minutes_before")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MalformedPackage("blinker_minutes_before must be a non-negative integer")
    return value


def _validate_flat_attachment(candidate: PackageCandidate, payload: dict[str, Any]) -> tuple[Path | None, str | None]:
    basename = payload.get("attachment_basename")
    original = payload.get("attachment_original_filename")
    if (basename is None) != (original is None):
        raise MalformedPackage("v2 attachment fields must be provided as a pair")
    if basename is None:
        if candidate.attachment_paths:
            raise MalformedPackage("undeclared attachment file")
        return None, None
    if not isinstance(basename, str) or basename != (candidate.attachment_paths[0].name if candidate.attachment_paths else ""):
        if not candidate.attachment_paths:
            raise PendingSync("ready marker is present but attachment is not locally available")
        raise MalformedPackage("attachment_basename does not match package file")
    if len(candidate.attachment_paths) != 1 or not _regular_local(candidate.attachment_paths[0]):
        raise MalformedPackage("v2 permits exactly one regular attachment")
    return candidate.attachment_paths[0], _safe_display_name(original)


def _parse_done(candidate: PackageCandidate, payload: dict[str, Any]) -> ParsedCommand:
    if payload.get("version") != 1 or payload.get("type") != "DONE":
        raise MalformedPackage("invalid DONE version/type")
    command_id = _validate_transport_id(payload.get("command_id"), "command_id")
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
    version = payload.get("version")
    if isinstance(version, bool) or payload.get("type") != "CREATE_EVENT" or version not in {1, 2}:
        raise MalformedPackage("invalid CREATE_EVENT version/type")
    transfer_id = _validate_transport_id(payload.get("transfer_id"), "transfer_id")
    if transfer_id != candidate.transport_id:
        raise MalformedPackage("transfer_id does not match filename")
    forbidden = _INTERNAL_CREATE_FIELDS.intersection(payload)
    if version == 2:
        forbidden.discard("blinker_minutes_before")
        if any(field in payload for field in ("reminder_intent", "blinker_intent", "attachment")):
            raise MalformedPackage("v2 CREATE must use flat transport fields")
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
    if version == 1:
        reminders = _parse_reminders(payload)
        blinker = _parse_blinker(payload)
        attachment_path, original = _validate_attachment(candidate, payload)
    else:
        reminders = _parse_flat_reminders(payload)
        blinker = _parse_flat_blinker(payload)
        attachment_path, original = _validate_flat_attachment(candidate, payload)
    created_at = payload.get("created_at")
    if created_at is not None:
        created_at = _parse_aware_timestamp(created_at, "created_at")
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

    def lookup(self, transport_id: str) -> dict[str, Any] | None:
        _validate_uuid4(transport_id, "transport_id")
        return next(
            (dict(record) for record in self.records() if record.get("transport_id") == transport_id),
            None,
        )

    def record(
        self,
        transport_id: str,
        kind: str,
        result: str,
        *,
        event_id: str | None = None,
        result_code: str | None = None,
    ) -> None:
        _validate_uuid4(transport_id, "transport_id")
        with agenda_lock(self.lock_path):
            records = self.records()
            if any(item.get("transport_id") == transport_id for item in records):
                return
            record: dict[str, Any] = {
                "transport_id": transport_id,
                "type": kind,
                "result": result,
                "recorded_at": datetime.now().astimezone().isoformat(),
            }
            if event_id:
                record["event_id"] = event_id
            if result_code:
                record["result_code"] = result_code
            records.append(record)
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
        try:
            with os.fdopen(fd, "wb") as target, source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, target)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, destination)
        except OSError as exc:
            if _is_iCloud_pending_error(exc):
                raise PendingSync("attachment bytes are still syncing") from exc
            raise
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
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            if _is_iCloud_pending_error(exc):
                raise PendingSync("package bytes are still syncing") from exc
            raise
        copied.append(source)
    _atomic_write_json(target / "reason.json", {"version": 1, "reason": reason, "transport_id": candidate.transport_id})
    for source in copied:
        try:
            source.unlink()
        except FileNotFoundError:
            pass
    return target


def _event_from_create(command: ParsedCommand, event_id: str) -> dict[str, Any]:
    """Build a remote event through the canonical personal-event transform."""
    from app import agenda_store

    if not command.title or not command.start or command.blinker_minutes_before is None:
        raise ValueError("CREATE_EVENT command is incomplete")
    start = datetime.fromisoformat(command.start)
    local_start = start.astimezone(ZoneInfo(agenda_store.LOCAL_TIMEZONE))
    event = agenda_store.build_personal_event(
        event_id,
        command.title,
        local_start.date().isoformat(),
        local_start.strftime("%H:%M"),
        list(command.reminder_offsets),
        description=command.description or "",
        enabled=True,
        attention_level=command.attention_level or "green",
    )
    # Preserve the explicit transport offset exactly; local build rules still
    # provide defaults/normalization for every other field.
    event["start"] = command.start
    event["blinker_minutes_before"] = max(int(command.blinker_minutes_before), 0)
    event["recurrence"] = None
    event["mailbox_transfer_id"] = command.transfer_id
    return event


def _ledger_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "result": record.get("result", "applied"),
        "transport_id": record.get("transport_id"),
        "type": record.get("type"),
        "event_id": record.get("event_id"),
        "result_code": record.get("result_code"),
        "replayed": True,
    }


def _find_provenance(document: dict[str, Any], transfer_id: str) -> dict[str, Any] | None:
    return next(
        (
            event
            for event in document.get("events", [])
            if isinstance(event, dict) and event.get("mailbox_transfer_id") == transfer_id
        ),
        None,
    )


def _remove_staging(blink_root: Path, transport_id: str) -> None:
    folder = Path(blink_root) / "mailbox" / "journal" / "staging" / transport_id
    if folder.exists():
        shutil.rmtree(folder)


def _apply_done_locked(
    command: ParsedCommand,
    agenda_path: Path,
    blink_root: Path,
    now: datetime,
) -> dict[str, Any]:
    from app import agenda_store

    journal = JournalStore(blink_root)
    journal.write(command.transport_id, {"phase": "validated", "kind": "DONE", "event_id": command.event_id})
    document = agenda_store.load_agenda_document(agenda_path, assume_locked=True)
    event = next(
        (item for item in document.get("events", []) if isinstance(item, dict) and item.get("id") == command.event_id),
        None,
    )
    if event is None:
        result = {"result": "stale_event", "transport_id": command.transport_id, "type": "DONE", "event_id": command.event_id}
    elif event.get("done") is True:
        result = {"result": "noop_done", "transport_id": command.transport_id, "type": "DONE", "event_id": command.event_id}
    else:
        updated = agenda_store.complete_event(document, command.event_id, now)
        agenda_store.save_agenda_document_atomic(agenda_path, updated, assume_locked=True)
        successor = next(
            (item for item in updated.get("events", []) if item.get("recurrence_parent_id") == command.event_id),
            None,
        )
        result = {"result": "applied", "transport_id": command.transport_id, "type": "DONE", "event_id": command.event_id}
        if successor:
            result["successor_id"] = successor.get("id")
    journal.write(command.transport_id, {"phase": "agenda_committed", "kind": "DONE", **result})
    return result


def _apply_create_locked(
    command: ParsedCommand,
    agenda_path: Path,
    blink_root: Path,
    staged: Path | None,
) -> dict[str, Any]:
    from app import agenda_store, attachment_store

    journal = JournalStore(blink_root)
    document = agenda_store.load_agenda_document(agenda_path, assume_locked=True)
    existing = _find_provenance(document, command.transfer_id or command.transport_id)
    if existing is not None:
        result = {
            "result": "applied",
            "transport_id": command.transport_id,
            "type": "CREATE_EVENT",
            "event_id": existing.get("id"),
            "replayed": True,
        }
        journal.write(command.transport_id, {"phase": "agenda_committed", "kind": "CREATE_EVENT", **result})
        return result
    event_id = f"event-{uuid.uuid4()}".lower()
    if staged is not None:
        attachment_store.import_staged_file(
            blink_root,
            event_id,
            staged,
            command.original_filename or staged.name,
        )
        journal.write(
            command.transport_id,
            {
                "phase": "attachment_finalized",
                "kind": "CREATE_EVENT",
                "event_id": event_id,
            },
        )
    event = _event_from_create(command, event_id)
    event["attachments"] = attachment_store.manifest_for_event(blink_root, event)
    updated = agenda_store.upsert_event(document, event)
    agenda_store.save_agenda_document_atomic(agenda_path, updated, assume_locked=True)
    result = {
        "result": "applied",
        "transport_id": command.transport_id,
        "type": "CREATE_EVENT",
        "event_id": event_id,
    }
    journal.write(command.transport_id, {"phase": "agenda_committed", "kind": "CREATE_EVENT", **result})
    return result


def apply_command(
    command: ParsedCommand,
    agenda_path: Path,
    blink_root: Path,
    *,
    now: datetime | None = None,
    blocking: bool = True,
    record_ledger: bool = True,
) -> dict[str, Any]:
    """Apply one validated command using the canonical agenda transforms."""
    agenda_path = Path(agenda_path)
    blink_root = Path(blink_root)
    ledger = ProcessedLedger(blink_root)
    prior = ledger.lookup(command.transport_id)
    if prior is not None:
        return _ledger_result(prior)
    staged: Path | None = None
    if command.kind == "CREATE_EVENT" and command.attachment_path is not None:
        staged = stage_attachment(command, blink_root)
        JournalStore(blink_root).write(command.transport_id, {"phase": "attachment_staged", "kind": "CREATE_EVENT"})
    lock_path = agenda_path.with_name("agenda.lock")
    try:
        with agenda_lock(lock_path, blocking=blocking):
            prior = ledger.lookup(command.transport_id)
            if prior is not None:
                result = _ledger_result(prior)
            elif command.kind == "DONE":
                result = _apply_done_locked(command, agenda_path, blink_root, now or datetime.now().astimezone())
            elif command.kind == "CREATE_EVENT":
                result = _apply_create_locked(command, agenda_path, blink_root, staged)
            else:
                raise MalformedPackage(f"unsupported command type: {command.kind}")
    except BlockingIOError:
        return {"result": "busy", "transport_id": command.transport_id, "type": command.kind}
    if record_ledger:
        ledger.record(
            command.transport_id,
            command.kind,
            str(result.get("result", "applied")),
            event_id=result.get("event_id"),
        )
        if staged is not None:
            _remove_staging(blink_root, command.transport_id)
    return result


def recover_pending_transactions(blink_root: Path, agenda_path: Path | None = None) -> list[dict[str, Any]]:
    """Repair ledger records and remove only safe orphan staging on restart."""
    root = Path(blink_root)
    ledger = ProcessedLedger(root)
    agenda_path = Path(agenda_path or root / "agenda.json")
    try:
        document = __import__("app.agenda_store", fromlist=["load_agenda_document"]).load_agenda_document(agenda_path)
    except (OSError, ValueError, json.JSONDecodeError):
        document = {"events": []}
    repaired: list[dict[str, Any]] = []
    for record in JournalStore(root).pending():
        transport_id = record.get("transport_id")
        phase = record.get("phase")
        if not isinstance(transport_id, str):
            continue
        if phase == "agenda_committed":
            if not ledger.contains(transport_id):
                ledger.record(
                    transport_id,
                    str(record.get("type", "UNKNOWN")),
                    str(record.get("result", "applied")),
                    event_id=record.get("event_id"),
                )
            _remove_staging(root, transport_id)
            repaired.append(record)
        elif phase in {"attachment_staged", "attachment_finalized"}:
            provenance = _find_provenance(document, transport_id)
            if provenance is None:
                _remove_staging(root, transport_id)
                if phase == "attachment_finalized" and isinstance(record.get("event_id"), str):
                    owner = root / "event_data" / "attachments" / record["event_id"]
                    if owner.exists():
                        shutil.rmtree(owner)
                repaired.append(record)
    return repaired


def process_mailbox_iteration(
    mailbox_root: Path,
    blink_root: Path,
    agenda_path: Path,
    *,
    max_packages: int = 8,
    on_done_applied: Callable[[ParsedCommand, dict[str, Any]], bool] | None = None,
) -> dict[str, int]:
    """Process one bounded mailbox scan; transport cleanup is last."""
    stats = {
        "scanned": 0,
        "applied": 0,
        "pending": 0,
        "malformed": 0,
        "busy": 0,
        "confirmation_sent": 0,
        "confirmation_failed": 0,
    }
    recover_pending_transactions(blink_root, agenda_path)
    for candidate in discover_packages(mailbox_root)[: max(0, int(max_packages))]:
        stats["scanned"] += 1
        try:
            command = parse_package(candidate)
        except PendingSync:
            stats["pending"] += 1
            continue
        except MalformedPackage as exc:
            try:
                quarantine_package(candidate, blink_root, str(exc))
            except PendingSync:
                stats["pending"] += 1
                continue
            stats["malformed"] += 1
            continue
        try:
            result = apply_command(command, agenda_path, blink_root, blocking=False)
        except PendingSync:
            stats["pending"] += 1
            continue
        outcome = result.get("result")
        if outcome == "busy":
            stats["busy"] += 1
            continue
        stats["applied"] += 1
        if (
            command.kind == "DONE"
            and outcome == "applied"
            and not result.get("replayed")
            and on_done_applied is not None
        ):
            try:
                if on_done_applied(command, result):
                    stats["confirmation_sent"] += 1
                else:
                    stats["confirmation_failed"] += 1
            except Exception:
                stats["confirmation_failed"] += 1
        for path in candidate.package_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                if _is_iCloud_pending_error(exc):
                    continue
                raise
    return stats
