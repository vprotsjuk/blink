"""Pure scheduling and formatting helpers for the personal morning briefing.

The watcher owns I/O and notification delivery.  Keeping the decision logic
here makes the daily send idempotent and straightforward to test.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Callable
from zoneinfo import ZoneInfo


def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(str(name or "America/Los_Angeles"))


def _event_start(event: dict[str, Any]) -> datetime | None:
    value = event.get("effective_start_dt") or event.get("start_dt")
    if isinstance(value, datetime):
        return value
    raw = event.get("effective_start") or event.get("start")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo and parsed.utcoffset() is not None else None


def _today_events(events: list[dict[str, Any]], now: datetime, timezone_name: str) -> list[dict[str, Any]]:
    local_now = now.astimezone(_zone(timezone_name))
    selected: list[dict[str, Any]] = []
    for event in events:
        if event.get("source", "personal") != "personal":
            continue
        if event.get("enabled") is not True or event.get("done") is True:
            continue
        start = _event_start(event)
        if start is None or start.astimezone(local_now.tzinfo).date() != local_now.date():
            continue
        selected.append(event)
    selected.sort(key=lambda item: _event_start(item).astimezone(local_now.tzinfo))
    return selected


def build_message(events: list[dict[str, Any]], now: datetime, timezone_name: str) -> str:
    """Render enabled, unfinished personal events scheduled for today."""
    local_zone = _zone(timezone_name)
    lines = ["Blink — Today", ""]
    for event in _today_events(events, now, timezone_name):
        start = _event_start(event).astimezone(local_zone)
        icon = "🔴" if str(event.get("attention_level", "green")).lower() == "red" else "🟢"
        title = str(event.get("title", "")).strip()
        lines.append(f"{icon} {start:%H:%M} — {title}")
        description = " ".join(str(event.get("description", "")).split())
        if description:
            lines.append(f"  {description}")
    return "\n".join(lines)


def _schedule_key(now: datetime, configured_time: str) -> str:
    return f"{now.date().isoformat()}|{configured_time}"


def _configured_time(value: Any) -> time | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M")
    except ValueError:
        return None
    return parsed.time()


def decide(
    config: dict[str, Any],
    state: dict[str, Any],
    events: list[dict[str, Any]],
    now: datetime,
    timezone_name: str,
) -> dict[str, Any]:
    """Return an idempotent send decision for the current local day."""
    if config.get("enabled") is not True:
        return {"action": "none", "reason": "disabled"}
    configured = str(config.get("time", "")).strip()
    target_time = _configured_time(configured)
    if target_time is None:
        return {"action": "none", "reason": "invalid_time"}
    local_now = now.astimezone(_zone(timezone_name))
    key = _schedule_key(local_now, configured)
    if state.get("last_sent_key") == key or state.get("last_evaluated_key") == key:
        return {"action": "none", "reason": "already_evaluated", "key": key}
    if local_now.time() < target_time:
        return {"action": "none", "reason": "not_due", "key": key}
    if not _today_events(events, now, timezone_name):
        return {"action": "none", "reason": "empty_today", "mark_evaluated": True, "key": key}
    return {
        "action": "send_now",
        "key": key,
        "message": build_message(events, now, timezone_name),
        "items": _today_events(events, now, timezone_name),
    }


def process(
    config: dict[str, Any],
    state: dict[str, Any],
    events: list[dict[str, Any]],
    now: datetime,
    timezone_name: str,
    send_func: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    """Apply one decision, marking delivery only after the sender succeeds."""
    result = dict(state or {})
    decision = decide(config, result, events, now, timezone_name)
    if decision.get("action") != "send_now":
        if decision.get("mark_evaluated"):
            result["last_evaluated_key"] = decision["key"]
            result["last_status"] = "empty_today"
        return result
    try:
        delivered = bool(send_func(decision))
    except Exception:
        delivered = False
    if delivered:
        result["last_sent_key"] = decision["key"]
        result["last_status"] = "sent"
        result["last_sent_at"] = now.isoformat()
    else:
        result["last_status"] = "send_failed"
    return result
