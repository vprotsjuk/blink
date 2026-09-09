"""Human-readable ntfy payload formatting for Blink events."""

from __future__ import annotations

from datetime import datetime
from typing import Any


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
    title = str(event.get("title", "")).strip()
    if event.get("source") == "astronomy":
        title = f"{_astronomy_icon(event)} {title}"
    else:
        title = f"{_attention_icon(event)} {title}"
    lines = [_event_date_label(event, start_value)]
    description = str(event.get("description", "")).strip()
    if description:
        lines.append(description)
    lines.append(_reminder_label(offset_minutes))
    return title, "\n".join(lines)


def push_tags_for_event(event: dict[str, Any], default_tags: list[str] | None = None) -> list[str]:
    """Return ntfy tags without Blink's internal calendar marker for reminders."""
    raw_tags = event.get("tags") or default_tags or []
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if event.get("source", "personal") == "personal":
        return [tag for tag in tags if tag.lower() != "calendar"]
    return tags


def _astronomy_icon(event: dict[str, Any]) -> str:
    tags = {str(tag).lower() for tag in event.get("tags", [])}
    if "sunrise" in tags or "sunset" in tags or "solar-noon" in tags:
        return "☀️"
    if "civil-twilight" in tags:
        return "✨"
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
