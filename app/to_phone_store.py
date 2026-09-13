"""Safe, idempotent snapshots of Blink event attachments for iPhone viewing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.attachment_store import owner_id_for_event
from app.event_timing import effective_event_start


FILES_ACTION_VERSION = "blink-files-v1"
_PACKAGE_RE = re.compile(r"^blink-files-v1-[0-9a-f]{32}$")
_STATE_NAME = "to_phone_state.json"


@dataclass(frozen=True)
class SnapshotResult:
    package_id: str
    ready: bool
    has_files: bool
    manifest: dict[str, Any] | None
    source_hash: str | None


def _effective_start(event: dict[str, Any]):
    return event.get("effective_start_dt") or event.get("start_dt") or effective_event_start(event)


def package_id(event: dict[str, Any], offset_minutes: int) -> str:
    start = _effective_start(event)
    start_text = start.isoformat() if start is not None else str(event.get("start", ""))
    logical = f"{str(event.get('id', '')).strip()}|{start_text}|{int(offset_minutes)}"
    return f"{FILES_ACTION_VERSION}-{hashlib.sha256(logical.encode('utf-8')).hexdigest()[:32]}"


def _safe_basename(value: Any) -> str:
    name = str(value or "").strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError("attachment filename must be a safe basename")
    if name.startswith(".") or len(name) > 180:
        raise ValueError("attachment filename is hidden or too long")
    return name


def _source_files(source_root: Path, event: dict[str, Any]) -> list[Path]:
    owner = owner_id_for_event(event)
    folder = Path(source_root) / owner
    if not folder.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
        if path.name.startswith(".") or path.is_symlink() or not path.is_file():
            continue
        _safe_basename(path.name)
        files.append(path)
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(package: str, files: list[Path]) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for index, source in enumerate(files, 1):
        name = _safe_basename(source.name)
        size = source.stat().st_size
        checksum = _sha256(source)
        transport = f"{package}__{index:02d}__{name}"
        records.append(
            {
                "ordinal": index,
                "transport_name": transport,
                "original_name": name,
                "size": size,
                "sha256": checksum,
            }
        )
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(checksum.encode("ascii"))
        digest.update(b"\0")
    return records, digest.hexdigest()


def source_fingerprint(source_root: Path, event: dict[str, Any]) -> str | None:
    """Return a stable fingerprint for the current visible source files."""
    files = _source_files(Path(source_root), event)
    if not files:
        return None
    return _records("fingerprint", files)[1]


def _state_path(root: Path) -> Path:
    return Path(root).parent / _STATE_NAME


def _load_state(root: Path) -> dict[str, Any]:
    try:
        raw = json.loads(_state_path(root).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"version": 1, "packages": {}}
    if not isinstance(raw, dict) or not isinstance(raw.get("packages"), dict):
        return {"version": 1, "packages": {}}
    return {"version": 1, "packages": dict(raw["packages"])}


def _save_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _package_paths(root: Path, package: str) -> list[Path]:
    return [path for path in Path(root).iterdir() if path.name == f"{package}.ready" or path.name == f"{package}.manifest.json" or path.name.startswith(f"{package}__")]


def _remove_package(root: Path, package: str) -> None:
    for path in _package_paths(root, package):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def prepare_snapshot(
    root: Path,
    event: dict[str, Any],
    offset_minutes: int,
    *,
    source_root: Path,
    now: datetime,
    delivered: bool = False,
) -> SnapshotResult:
    """Create or refresh one complete package; queued packages stay mutable."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    package = package_id(event, offset_minutes)
    state = _load_state(root)
    entry = state["packages"].get(package)
    immutable = delivered or (isinstance(entry, dict) and entry.get("status") == "delivered")
    existing = validate_package(root, package)
    if immutable:
        if existing is not None:
            return SnapshotResult(package, True, True, existing, existing.get("source_hash"))
        return SnapshotResult(package, False, False, None, None)

    files = _source_files(Path(source_root), event)
    if not files:
        if not immutable:
            _remove_package(root, package)
            state["packages"].pop(package, None)
            _save_state(root, state)
        return SnapshotResult(package, False, False, None, None)

    records, source_hash = _records(package, files)
    if existing is not None and existing.get("source_hash") == source_hash:
        state["packages"].setdefault(package, {"status": "queued", "prepared_at": now.isoformat()})
        _save_state(root, state)
        return SnapshotResult(package, True, True, existing, source_hash)

    manifest = {
        "version": 1,
        "type": "ATTACHMENTS",
        "package_id": package,
        "event_id": str(event.get("id", "")).strip(),
        "reminder_key": f"{str(event.get('id', '')).strip()}|{(_effective_start(event).isoformat() if _effective_start(event) else '')}|{int(offset_minutes)}",
        "source_hash": source_hash,
        "created_at": now.astimezone(timezone.utc).isoformat(),
        "files": records,
    }
    tmp_dir = root / f".{package}.{os.getpid()}.tmp"
    backup_dir = root / f".{package}.{os.getpid()}.bak"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    shutil.rmtree(backup_dir, ignore_errors=True)
    tmp_dir.mkdir()
    try:
        for record, source in zip(records, files):
            destination = tmp_dir / record["transport_name"]
            with source.open("rb") as source_handle, destination.open("wb") as target:
                shutil.copyfileobj(source_handle, target)
                target.flush()
                os.fsync(target.fileno())
        manifest_path = tmp_dir / f"{package}.manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        old_paths = _package_paths(root, package)
        backup_dir.mkdir()
        for old in old_paths:
            shutil.copy2(old, backup_dir / old.name)
        for old in old_paths:
            old.unlink()
        for staged in tmp_dir.iterdir():
            os.replace(staged, root / staged.name)
        ready = root / f"{package}.ready"
        with ready.open("w", encoding="utf-8") as handle:
            handle.write("")
            handle.flush()
            os.fsync(handle.fileno())
        state["packages"][package] = {"status": "queued", "prepared_at": now.isoformat()}
        _save_state(root, state)
    except Exception:
        _remove_package(root, package)
        if backup_dir.exists():
            for backup in backup_dir.iterdir():
                os.replace(backup, root / backup.name)
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(backup_dir, ignore_errors=True)
    return SnapshotResult(package, True, True, manifest, source_hash)


def validate_package(root: Path, package: str) -> dict[str, Any] | None:
    root = Path(root)
    if not root.is_dir():
        return None
    if not _PACKAGE_RE.fullmatch(str(package)):
        return None
    manifest_path = root / f"{package}.manifest.json"
    ready_path = root / f"{package}.ready"
    try:
        if not ready_path.is_file() or not manifest_path.is_file():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or manifest.get("type") != "ATTACHMENTS":
        return None
    if manifest.get("package_id") != package or not isinstance(manifest.get("files"), list) or not manifest.get("files"):
        return None
    expected_names: set[str] = set()
    for index, record in enumerate(manifest["files"], 1):
        if not isinstance(record, dict) or record.get("ordinal") != index:
            return None
        transport = record.get("transport_name")
        if not isinstance(transport, str) or not transport.startswith(f"{package}__{index:02d}__"):
            return None
        try:
            _safe_basename(transport.split(f"{package}__{index:02d}__", 1)[1])
            size = int(record["size"])
            checksum = str(record["sha256"])
        except (KeyError, TypeError, ValueError):
            return None
        path = root / transport
        expected_names.add(transport)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size or _sha256(path) != checksum:
                return None
        except OSError:
            return None
    prefix = f"{package}__"
    for path in root.iterdir():
        if path.name.startswith(prefix) and path.name not in expected_names:
            return None
    return manifest


def mark_delivered(root: Path, package: str, delivered_at: datetime) -> None:
    if not _PACKAGE_RE.fullmatch(str(package)):
        return
    state = _load_state(Path(root))
    state["packages"][package] = {"status": "delivered", "delivered_at": delivered_at.astimezone(timezone.utc).isoformat()}
    _save_state(Path(root), state)


def cleanup(root: Path, now: datetime, ttl_seconds: int) -> list[str]:
    root = Path(root)
    state = _load_state(root)
    removed: list[str] = []
    for package, entry in list(state["packages"].items()):
        if not _PACKAGE_RE.fullmatch(str(package)) or not isinstance(entry, dict) or entry.get("status") != "delivered":
            continue
        try:
            delivered_at = datetime.fromisoformat(str(entry["delivered_at"]))
        except (KeyError, TypeError, ValueError):
            continue
        if (now - delivered_at).total_seconds() < max(int(ttl_seconds), 0):
            continue
        _remove_package(root, package)
        state["packages"].pop(package, None)
        removed.append(package)
    if removed:
        _save_state(root, state)
    return removed
