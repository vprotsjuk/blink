"""Human-readable ntfy payload formatting for Blink events."""

from __future__ import annotations

from datetime import datetime
from typing import Any


MAX_NTFY_BODY_BYTES = 4096
MAX_NTFY_TITLE_BYTES = 1024
_ELLIPSIS = "…"

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _event_date_label(event: dict[str, Any], start_value: str | None = None) -> str:
    start = datetime.fromisoformat(str(start_value or event["start"]))
    return f"{_MONTHS[start.month - 1]} {start.day}, {start.year} at {start:%H:%M}"


def _reminder_label(offset_minutes: int) -> str:
    return "Event starts now" if offset_minutes == 0 else f"{offset_minutes} min before start"


def build_event_notification(
    event: dict[str, Any], offset_minutes: int, start_value: str | None = None
) -> tuple[str, str]:
    """Return ntfy title and a concise, user-facing message body."""
    title = _single_line_title(event.get("title", ""))
    if event.get("source") == "astronomy":
        title = f"{_astronomy_icon(event)} {title}"
    else:
        marker = " 📎" if _has_attachments(event) else ""
        title = f"{_attention_icon(event)}{marker} {title}"
    title = _truncate_utf8(title, MAX_NTFY_TITLE_BYTES)
    date_line = _event_date_label(event, start_value)
    if event.get("source") == "astronomy":
        return title, _build_astronomy_body(date_line, event)
    description = str(event.get("description", "")).strip()
    reminder_line = _reminder_label(offset_minutes)
    return title, _build_bounded_body(date_line, description, reminder_line)


def _single_line_title(value: Any) -> str:
    lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    return lines[0] if lines else "Reminder"


def _has_attachments(event: dict[str, Any]) -> bool:
    manifest = event.get("attachments")
    return isinstance(manifest, dict) and bool(manifest.get("has_files"))


def _truncate_utf8(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    suffix = _ELLIPSIS.encode("utf-8")
    if limit <= len(suffix):
        return suffix[:limit].decode("utf-8", "ignore")
    prefix = encoded[: limit - len(suffix)].decode("utf-8", "ignore")
    return prefix + _ELLIPSIS


def _build_bounded_body(date_line: str, description: str, reminder_line: str) -> str:
    if not description:
        return _truncate_utf8(f"{date_line}\n{reminder_line}", MAX_NTFY_BODY_BYTES)
    fixed_bytes = len(date_line.encode("utf-8")) + len(reminder_line.encode("utf-8")) + 2
    available = MAX_NTFY_BODY_BYTES - fixed_bytes
    if available <= 0:
        return _truncate_utf8(f"{date_line}\n{reminder_line}", MAX_NTFY_BODY_BYTES)
    bounded_description = _truncate_utf8(description, available)
    return f"{date_line}\n{bounded_description}\n{reminder_line}"


def _build_astronomy_body(date_line: str, event: dict[str, Any]) -> str:
    """Keep astronomy facts while removing duplicated event boilerplate."""
    event_name = _single_line_title(event.get("title", "")).casefold().rstrip(".")
    cleaned: list[str] = []
    for raw_line in str(event.get("description", "")).splitlines():
        line = raw_line.strip()
        normalized = line.casefold().rstrip(".")
        if not line or normalized in {event_name, "event starts now"}:
            continue
        if normalized.startswith("solar noon. sun:"):
            altitude = line[len("Solar noon. Sun:"):].strip()
            if altitude:
                cleaned.append(f"Sun altitude: {altitude}")
            continue
        cleaned.append(line)
    return "\n".join([date_line, *cleaned])


def push_tags_for_event(event: dict[str, Any], default_tags: list[str] | None = None) -> list[str]:
    """Return ntfy tags without Blink's internal calendar marker for reminders."""
    if event.get("source", "personal") == "astronomy":
        return []
    raw_tags = event.get("tags") or default_tags or []
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if event.get("source", "personal") == "personal":
        return [tag for tag in tags if tag.lower() != "calendar"]
    return tags


def _astronomy_icon(event: dict[str, Any]) -> str:
    tags = {str(tag).lower() for tag in event.get("tags", [])}
    if "sunrise" in tags:
        return "☀️ ↑"
    if "sunset" in tags:
        return "☀️ ↓"
    if "solar-noon" in tags:
        return "☀️"
    if "civil-twilight" in tags:
        return "✨"
    if "moonrise" in tags:
        return "🌙 ↑"
    if "moonset" in tags:
        return "🌙 ↓"
    explicit_icon = str(event.get("notification_icon", "")).strip()
    if explicit_icon:
        return explicit_icon
    phase_icon = str(event.get("moon_phase_icon", "")).strip()
    if phase_icon:
        trend = str(event.get("moon_phase_trend", "")).strip().lower()
        arrow = {"waxing": "⬆️", "waning": "⬇️"}.get(trend)
        return f"{phase_icon} {arrow}" if arrow else phase_icon
    if "moon" in tags or "moonrise" in tags or "moonset" in tags:
        return "🌙"
    return "✨"


def _attention_icon(event: dict[str, Any]) -> str:
    """Make the app's green/yellow/red attention level visible in event pushes."""
    return {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
    }.get(str(event.get("attention_level", "green")).lower(), "🟢")
