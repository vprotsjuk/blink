"""Watcher runtime heartbeat, status, and sleep-gap helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_heartbeat(path: Path, *, now: datetime, pid: int | None = None) -> None:
    payload = {
        "version": 1,
        "pid": int(pid if pid is not None else os.getpid()),
        "last_heartbeat_at": now.isoformat(),
    }
    save_json_atomic(path, payload)


def status(
    path: Path,
    *,
    now: datetime | None = None,
    stale_after_seconds: int = 120,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc).astimezone()
    raw = load_json(path)
    if not isinstance(raw, dict):
        return {"state": "stopped", "reason": "runtime_file_missing"}

    pid = raw.get("pid")
    heartbeat_text = raw.get("last_heartbeat_at")
    if not isinstance(pid, int) or not isinstance(heartbeat_text, str):
        return {"state": "stopped", "reason": "runtime_file_invalid"}
    if not process_exists(pid):
        return {"state": "stopped", "pid": pid, "reason": "process_not_running"}

    try:
        heartbeat = datetime.fromisoformat(heartbeat_text)
    except ValueError:
        return {"state": "stopped", "pid": pid, "reason": "heartbeat_invalid"}
    if heartbeat.tzinfo is None or heartbeat.utcoffset() is None:
        return {"state": "stopped", "pid": pid, "reason": "heartbeat_has_no_timezone"}

    age_seconds = (now.astimezone(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
    if age_seconds > stale_after_seconds:
        return {
            "state": "stale",
            "pid": pid,
            "last_heartbeat_at": heartbeat_text,
            "age_seconds": round(age_seconds),
        }
    return {
        "state": "running",
        "pid": pid,
        "last_heartbeat_at": heartbeat_text,
        "age_seconds": round(max(0, age_seconds)),
    }


def detect_sleep_gap(
    previous: datetime,
    current: datetime,
    *,
    poll_interval_seconds: int,
    multiplier: int = 6,
    minimum_gap_seconds: int = 180,
) -> bool:
    threshold = max(minimum_gap_seconds, poll_interval_seconds * multiplier)
    elapsed = (current.astimezone(timezone.utc) - previous.astimezone(timezone.utc)).total_seconds()
    return elapsed > threshold


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def load_json(path: Path) -> Any | None:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)
