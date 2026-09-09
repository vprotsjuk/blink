"""Remote ntfy scheduling reconciliation for Blink.

This module models the 24-hour remote queue separately from watcher history.
A queued remote reminder is not treated as sent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from app.event_timing import effective_event_start
from app.notification_format import build_event_notification, push_tags_for_event


def empty_state() -> dict[str, Any]:
    return {"version": 1, "scheduled": {}, "delivered": {}}


def sequence_id(event: dict[str, Any], offset_minutes: int) -> str:
    source = str(event.get("source", "personal")).strip() or "personal"
    event_id = str(event.get("id", "")).strip()
    if source == "personal":
        logical = f"{source}:{event_id}:{offset_minutes}"
    else:
        logical = f"{source}:{event_id}:{offset_minutes}"
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", logical).strip("-").lower()
    digest = hashlib.sha256(logical.encode("utf-8")).hexdigest()[:12]
    return f"blink-{safe[:42]}-{digest}"


def build_desired_queue(
    *,
    events: list[dict[str, Any]],
    now: datetime,
    window_hours: int,
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    desired: dict[str, dict[str, Any]] = {}
    window_end = now + timedelta(hours=window_hours)
    for event in events:
        if event.get("source", "personal") not in {"personal", "astronomy"}:
            continue
        if event.get("enabled") is not True or event.get("done") is True:
            continue
        effective_start = event.get("effective_start_dt") or effective_event_start(event)
        if effective_start is None:
            continue
        for offset in event.get("reminders_minutes_before", []):
            reminder_time = effective_start - timedelta(minutes=offset)
            now_for_event = now.astimezone(reminder_time.tzinfo)
            if reminder_time < now_for_event or reminder_time > window_end.astimezone(reminder_time.tzinfo):
                continue
            seq = sequence_id(event, offset)
            reminder_key = f"{event['id']}|{effective_start.isoformat()}|{offset}"
            title, body, priority, tags = build_payload(config, event, offset)
            payload = {
                "title": title,
                "body": body,
                "priority": priority,
                "tags": tags,
                "delivery_time": reminder_time.isoformat(),
            }
            desired[seq] = {
                "sequence_id": seq,
                "reminder_key": reminder_key,
                "source": event.get("source", "personal"),
                "event_id": event["id"],
                "offset_minutes": offset,
                "delivery_time": reminder_time.isoformat(),
                "payload": payload,
                "payload_hash": payload_hash(payload),
            }
    return desired


def reconcile(
    *,
    desired: dict[str, dict[str, Any]],
    state: dict[str, Any],
    schedule_func: Callable[[dict[str, Any]], bool],
    cancel_func: Callable[[dict[str, Any]], bool],
    now: datetime,
) -> dict[str, Any]:
    result = json.loads(json.dumps(state or empty_state()))
    result.setdefault("version", 1)
    scheduled = result.setdefault("scheduled", {})
    delivered = result.setdefault("delivered", {})

    for seq, existing in list(scheduled.items()):
        if not isinstance(existing, dict):
            scheduled.pop(seq, None)
            continue
        if seq not in desired:
            if existing.get("status") == "queued" and _future_time(existing.get("delivery_time"), now):
                if cancel_func(existing):
                    scheduled.pop(seq, None)
                else:
                    existing["status"] = "pending_cancel"
                    existing["pending_since"] = now.isoformat()
            elif existing.get("status") == "queued" and _matured_time(existing.get("delivery_time"), now):
                delivered[seq] = {
                    **existing,
                    "status": "assumed_sent",
                    "assumed_sent_at": now.isoformat(),
                }
                scheduled.pop(seq, None)
            else:
                scheduled.pop(seq, None)

    for seq, desired_item in desired.items():
        existing = scheduled.get(seq)
        if existing and existing.get("status") == "queued":
            if (
                existing.get("payload_hash") == desired_item["payload_hash"]
                and existing.get("delivery_time") == desired_item["delivery_time"]
            ):
                continue
        item = dict(desired_item)
        if schedule_func(item):
            item["status"] = "queued"
            item["queued_at"] = now.isoformat()
        else:
            item["status"] = "pending_sync"
            item["pending_since"] = now.isoformat()
        scheduled[seq] = item

    return result


def is_reminder_owned_by_remote(state: dict[str, Any], reminder_key: str) -> bool:
    for item in list(state.get("scheduled", {}).values()) + list(state.get("delivered", {}).values()):
        if (
            isinstance(item, dict)
            and item.get("status") in {"queued", "assumed_sent", "assumed_delivered"}
            and item.get("reminder_key") == reminder_key
        ):
            return True
    return False


def load_state(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return empty_state()
    if not isinstance(raw, dict) or not isinstance(raw.get("scheduled"), dict):
        return empty_state()
    return {
        "version": 1,
        "scheduled": dict(raw.get("scheduled", {})),
        "delivered": dict(raw.get("delivered", {})),
    }


def save_state_atomic(path: Path, state: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def build_payload(
    config: dict[str, Any], event: dict[str, Any], offset_minutes: int
) -> tuple[str, str, str, list[str]]:
    effective_start = event.get("effective_start_dt") or effective_event_start(event)
    title, body = build_event_notification(
        event,
        offset_minutes,
        effective_start.isoformat() if effective_start is not None else None,
    )
    priority = event.get("priority", "default")
    if priority == "default":
        priority = config.get("default_priority", "high")
    tags = push_tags_for_event(event, config.get("default_tags", ["calendar"]))
    return title, body, priority, tags


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _future_time(value: Any, now: datetime) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return False
    return parsed.astimezone(timezone.utc) > now.astimezone(timezone.utc)


def _matured_time(value: Any, now: datetime) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return False
    return parsed.astimezone(timezone.utc) <= now.astimezone(timezone.utc)
