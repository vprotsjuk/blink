"""Safe agenda.json helpers for the Blink GUI layer."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app import attachment_store
from app.event_timing import effective_event_start


LOCAL_TIMEZONE = "America/Los_Angeles"


def load_agenda_document(path: Path) -> dict[str, Any]:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("agenda.json must contain an object")
    if not isinstance(raw.get("events"), list):
        raw["events"] = []
    migrated = migrate_obsolete_fields(raw)
    migrated = repair_completed_future_events(migrated)
    if migrated != raw:
        save_agenda_document_atomic(path, migrated)
    return migrated


def migrate_obsolete_fields(document: dict[str, Any]) -> dict[str, Any]:
    """Remove retired Snooze/Templates fields without changing event meaning."""
    result = json.loads(json.dumps(document))
    for event in result.get("events", []):
        if not isinstance(event, dict):
            continue
        event.pop("snoozed_until", None)
        event.pop("snoozed_for_minutes", None)
        event.pop("template_id", None)
    return result


def repair_completed_future_events(document: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Reopen stale records left by older builds after a completed event was moved forward."""
    result = json.loads(json.dumps(document))
    current = now or datetime.now(ZoneInfo(LOCAL_TIMEZONE))
    for event in result.get("events", []):
        if not isinstance(event, dict) or not is_personal_event(event):
            continue
        if event.get("requires_done") is not True or event.get("done") is not True:
            continue
        start = parse_aware_start(event)
        if start is not None and start > current.astimezone(start.tzinfo):
            event["done"] = False
            event["done_at"] = None
    return result


def save_agenda_document_atomic(path: Path, document: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def build_personal_event(
    event_id: str,
    title: str,
    local_date: str,
    local_time: str,
    reminder_offsets: list[int],
    description: str = "",
    enabled: bool = True,
    attention_level: str = "green",
) -> dict[str, Any]:
    event_id = event_id.strip()
    title = title.strip()
    if not event_id or not title:
        raise ValueError("event_id and title are required")
    naive = datetime.fromisoformat(f"{local_date}T{local_time}:00")
    local = naive.replace(tzinfo=ZoneInfo(LOCAL_TIMEZONE))
    offsets = sorted({int(offset) for offset in reminder_offsets if int(offset) >= 0}, reverse=True)
    attention = normalize_attention_level(attention_level)
    return {
        "id": event_id,
        "title": title,
        "description": description.strip(),
        "start": local.isoformat(),
        "reminders_minutes_before": offsets,
        "priority": "default",
        "tags": ["calendar"],
        "enabled": bool(enabled),
        "requires_done": True,
        "done": False,
        "done_at": None,
        "attention_level": attention,
        "attachments": {"owner_id": event_id, "count": 0, "has_files": False},
    }


def duplicate_event(
    event: dict[str, Any],
    new_id: str,
    new_start: str | None = None,
    preserve_recurrence: bool = False,
) -> dict[str, Any]:
    """Create a new unfinished event without mutating the source record."""
    result = json.loads(json.dumps(event))
    new_id = str(new_id).strip()
    if not new_id:
        raise ValueError("new_id is required")
    result["id"] = new_id
    if new_start is not None:
        result["start"] = str(new_start).strip()
    result["enabled"] = True
    result["requires_done"] = True
    result["done"] = False
    result["done_at"] = None
    result.pop("recurrence_parent_id", None)
    result.pop("generation", None)
    result.pop("series_id", None)
    if not preserve_recurrence:
        result.pop("recurrence", None)
    else:
        result["series_id"] = new_id
    result["attachments"] = attachment_store.attachment_manifest(None, result)
    return result


def upsert_event(
    document: dict[str, Any], event: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    events = result.setdefault("events", [])
    for index, existing in enumerate(events):
        if existing.get("id") == event.get("id"):
            if existing.get("done") is True:
                raise ValueError("history events are frozen; duplicate the event instead")
            merged = dict(existing)
            merged.update(event)
            events[index] = merged
            return result
    events.append(dict(event))
    return result


def set_event_enabled(document: dict[str, Any], event_id: str, enabled: bool) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    for event in result.get("events", []):
        if event.get("id") == event_id:
            event["enabled"] = bool(enabled)
            return result
    raise KeyError(event_id)


def delete_event(document: dict[str, Any], event_id: str) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    result["events"] = [event for event in result.get("events", []) if event.get("id") != event_id]
    return result


def normalize_attention_level(value: Any) -> str:
    text = str(value or "green").strip().lower()
    return text if text in {"green", "yellow", "red"} else "green"


def is_personal_event(event: dict[str, Any]) -> bool:
    return event.get("source", "personal") == "personal"


def parse_aware_start(event: dict[str, Any]) -> datetime | None:
    try:
        start = datetime.fromisoformat(str(event.get("start", "")))
    except ValueError:
        return None
    if start.tzinfo is None or start.utcoffset() is None:
        return None
    return start


def is_active_personal_event(event: dict[str, Any], now: datetime) -> bool:
    if not is_personal_event(event):
        return False
    if event.get("enabled") is not True:
        return False
    if event.get("requires_done") is not True:
        return False
    if event.get("done") is True:
        return False
    start = parse_aware_start(event)
    if start is None:
        return False
    return start <= now.astimezone(start.tzinfo)


def is_attention_eligible(event: dict[str, Any], now: datetime) -> bool:
    """Return whether an unfinished event should currently drive the lamp."""
    if not is_personal_event(event) or event.get("enabled") is not True:
        return False
    if event.get("requires_done") is not True or event.get("done") is True:
        return False
    start = parse_aware_start(event)
    return start is not None and attention_start(event, start) <= now.astimezone(start.tzinfo)


def attention_start(event: dict[str, Any], start: datetime | None = None) -> datetime:
    start = start or parse_aware_start(event)
    if start is None:
        raise ValueError("event start must be timezone-aware")
    try:
        minutes = int(event.get("blinker_minutes_before") or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes < 0:
        minutes = 0
    from datetime import timedelta

    return start - timedelta(minutes=minutes)


def split_personal_event_sections(
    document: dict[str, Any], now: datetime
) -> dict[str, list[dict[str, Any]]]:
    active = []
    history = []
    upcoming = []
    for event in document.get("events", []):
        if not isinstance(event, dict) or not is_personal_event(event):
            continue
        start = parse_aware_start(event)
        if start is None:
            continue
        if is_active_personal_event(event, now):
            active.append(event)
            continue
        if event.get("requires_done") is True:
            if event.get("done") is True:
                history.append(event)
            elif start > now.astimezone(start.tzinfo):
                upcoming.append(event)
            else:
                # Disabling stops attention but must not hide a past event.
                history.append(event)
            continue
        if start < now.astimezone(start.tzinfo):
            history.append(event)
        else:
            upcoming.append(event)
    active.sort(key=lambda event: event["start"])
    history.sort(key=lambda event: event.get("done_at") or event["start"], reverse=True)
    upcoming.sort(key=lambda event: event["start"])
    return {"active": active, "history": history, "upcoming": upcoming}


def compute_attention_state(document: dict[str, Any], now: datetime) -> str:
    rank = {"off": 0, "green": 1, "yellow": 2, "red": 3}
    winner = "off"
    for event in document.get("events", []):
        if not is_attention_eligible(event, now):
            continue
        level = normalize_attention_level(event.get("attention_level"))
        if rank[level] > rank[winner]:
            winner = level
    return winner


def complete_event(document: dict[str, Any], event_id: str, now: datetime) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    local_now = now.astimezone(ZoneInfo(LOCAL_TIMEZONE))
    for event in result.get("events", []):
        if event.get("id") == event_id:
            event["requires_done"] = True
            event["done"] = True
            event["done_at"] = local_now.isoformat()
            generation = int(event.get("generation", 0) or 0)
            if not any(
                isinstance(candidate, dict)
                and candidate.get("recurrence_parent_id") == event_id
                and int(candidate.get("generation", -1) or -1) == generation + 1
                for candidate in result.get("events", [])
            ):
                next_event = build_next_recurring_event(event, local_now)
                if next_event is not None:
                    result.setdefault("events", []).append(next_event)
            return result
    raise KeyError(event_id)


def build_next_recurring_event(event: dict[str, Any], completed_at: datetime) -> dict[str, Any] | None:
    recurrence = event.get("recurrence")
    if not isinstance(recurrence, dict):
        return None
    start = parse_aware_start(event)
    if start is None:
        return None
    local_zone = ZoneInfo(LOCAL_TIMEZONE)
    completed_local = completed_at.astimezone(local_zone)
    start_local = start.astimezone(local_zone)
    mode = str(recurrence.get("mode", "")).strip()
    if mode == "after_done_days":
        try:
            days = int(recurrence.get("days"))
        except (TypeError, ValueError):
            return None
        if days <= 0:
            return None
        next_date = completed_local.date() + timedelta(days=days)
        next_start = datetime(
            next_date.year,
            next_date.month,
            next_date.day,
            start_local.hour,
            start_local.minute,
            tzinfo=local_zone,
        )
    elif mode == "weekly_fixed":
        try:
            weekday = int(recurrence.get("weekday"))
        except (TypeError, ValueError):
            return None
        if weekday < 1 or weekday > 7:
            return None
        time_text = str(recurrence.get("time") or f"{start_local.hour:02d}:{start_local.minute:02d}")
        try:
            hour_text, minute_text = time_text.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError:
            return None
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None
        days_ahead = (weekday - completed_local.isoweekday()) % 7
        candidate_date = completed_local.date() + timedelta(days=days_ahead)
        next_start = datetime(
            candidate_date.year,
            candidate_date.month,
            candidate_date.day,
            hour,
            minute,
            tzinfo=local_zone,
        )
        if next_start <= completed_local:
            next_start = next_start + timedelta(days=7)
    else:
        return None

    next_event = json.loads(json.dumps(event))
    series_id = str(event.get("series_id") or event.get("id") or "event")
    generation = int(event.get("generation", 0) or 0) + 1
    next_event["id"] = f"{series_id}-g{generation}"
    next_event["series_id"] = series_id
    next_event["generation"] = generation
    next_event["recurrence_parent_id"] = event.get("id")
    next_event["start"] = next_start.isoformat()
    next_event["requires_done"] = True
    next_event["done"] = False
    next_event["done_at"] = None
    next_event["enabled"] = True
    next_event.pop("snoozed_until", None)
    next_event.pop("snoozed_for_minutes", None)
    next_event.pop("template_id", None)
    return next_event


def set_attention_level(document: dict[str, Any], event_id: str, level: str) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    for event in result.get("events", []):
        if event.get("id") == event_id:
            event["attention_level"] = normalize_attention_level(level)
            return result
    raise KeyError(event_id)


def split_history_upcoming(
    document: dict[str, Any], now: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sections = split_personal_event_sections(document, now)
    return sections["history"], sections["upcoming"]
