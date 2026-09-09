#!/usr/bin/env python3
"""Blink watcher: read agenda.json and send due reminders through ntfy."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import hashlib
import urllib.error
import urllib.request
from email.header import Header
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Callable

from app import agenda_store, location_store, watcher_lifecycle, weather_store
from app import ntfy_schedule
from app.event_timing import effective_event_start
from app.notification_format import build_event_notification, push_tags_for_event


PROJECT_DIR = Path(__file__).resolve().parent
SHUTTING_DOWN = False
LOGGER = logging.getLogger("blink-watcher")
_last_remote_reconcile_at: datetime | None = None
_last_remote_reconcile_signature: str | None = None


class SetupError(Exception):
    """Raised when Watcher cannot safely send notifications."""


def project_path(name: str) -> Path:
    return PROJECT_DIR / name


def setup_logging() -> None:
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.FileHandler(project_path("watcher.log"), encoding="utf-8")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


def redact_topic(topic: str) -> str:
    if not topic:
        return "<empty>"
    if len(topic) <= 8:
        return "<redacted>"
    return f"{topic[:16]}...{topic[-3:]}"


def load_json_file(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        LOGGER.error("%s is missing", path.name)
    except json.JSONDecodeError as exc:
        LOGGER.error("%s contains invalid JSON: %s", path.name, exc)
    except OSError as exc:
        LOGGER.error("Could not read %s: %s", path.name, exc)
    return None


def validate_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SetupError("config.json must contain a JSON object.")

    topic = str(raw.get("ntfy_topic", "")).strip()
    if not topic or topic.startswith("REPLACE_WITH"):
        raise SetupError(
            "config.json still contains the ntfy topic placeholder. Paste your private topic first."
        )

    server = str(raw.get("ntfy_server", "https://ntfy.sh")).strip().rstrip("/")
    if not server.startswith(("https://", "http://")):
        raise SetupError("config.json ntfy_server must start with https:// or http://.")

    poll_interval = _positive_int(raw.get("poll_interval_seconds"), 10, minimum=1)
    grace_minutes = _positive_int(raw.get("late_delivery_grace_minutes"), 180, minimum=0)
    default_priority = str(raw.get("default_priority", "high")).strip() or "high"
    default_tags = raw.get("default_tags", ["calendar"])
    if not isinstance(default_tags, list):
        default_tags = ["calendar"]
    default_tags = [str(tag).strip() for tag in default_tags if str(tag).strip()]

    return {
        "ntfy_server": server,
        "ntfy_topic": topic,
        "poll_interval_seconds": poll_interval,
        "late_delivery_grace_minutes": grace_minutes,
        "default_priority": default_priority,
        "default_tags": default_tags or ["calendar"],
    }


def _positive_int(value: Any, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def load_config(path: Path | None = None) -> dict[str, Any] | None:
    config_path = path or project_path("config.json")
    raw = load_json_file(config_path)
    if raw is None:
        return None
    try:
        config = validate_config(raw)
    except SetupError as exc:
        LOGGER.error("Setup error: %s", exc)
        print(f"Setup error: {exc}", file=sys.stderr)
        return None
    LOGGER.info(
        "Configuration loaded: server=%s topic=%s poll=%ss grace=%sm",
        config["ntfy_server"],
        redact_topic(config["ntfy_topic"]),
        config["poll_interval_seconds"],
        config["late_delivery_grace_minutes"],
    )
    return config


def validate_event(
    event: Any, seen_ids: set[str], index: int
) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        LOGGER.warning("Invalid event at index %s: event must be an object", index)
        return None

    missing = [
        field
        for field in ("id", "title", "start", "reminders_minutes_before", "enabled")
        if field not in event
    ]
    if missing:
        LOGGER.warning("Invalid event at index %s: missing %s", index, ", ".join(missing))
        return None

    event_id = str(event["id"]).strip()
    title = str(event["title"]).strip()
    start_text = str(event["start"]).strip()
    if not event_id or not title or not start_text:
        LOGGER.warning("Invalid event at index %s: id, title, and start must be non-empty", index)
        return None

    if event_id in seen_ids:
        LOGGER.warning("Duplicate event id found: %s", event_id)
    seen_ids.add(event_id)

    if event["enabled"] is not True:
        return None

    try:
        start_dt = datetime.fromisoformat(start_text)
    except ValueError as exc:
        LOGGER.warning("Invalid event %s: bad start timestamp: %s", event_id, exc)
        return None
    if start_dt.tzinfo is None or start_dt.utcoffset() is None:
        LOGGER.warning("Invalid event %s: start timestamp must include UTC offset", event_id)
        return None

    reminders = event["reminders_minutes_before"]
    if not isinstance(reminders, list):
        LOGGER.warning("Invalid event %s: reminders_minutes_before must be a list", event_id)
        return None
    cleaned_reminders: set[int] = set()
    for value in reminders:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            LOGGER.warning(
                "Invalid event %s: reminder offsets must be non-negative integers",
                event_id,
            )
            return None
        cleaned_reminders.add(value)

    tags = event.get("tags")
    if tags is not None and not isinstance(tags, list):
        LOGGER.warning("Invalid event %s: tags must be a list when provided", event_id)
        return None

    effective_start_dt = effective_event_start(event)
    if effective_start_dt is None:
        LOGGER.warning("Invalid event %s: bad effective start", event_id)
        return None

    return {
        "id": event_id,
        "title": title,
        "description": str(event.get("description", "")).strip(),
        "start": start_text,
        "start_dt": start_dt,
        "effective_start_dt": effective_start_dt,
        "reminders_minutes_before": sorted(cleaned_reminders, reverse=True),
        "priority": str(event.get("priority", "default")).strip() or "default",
        "tags": [str(tag).strip() for tag in (tags or []) if str(tag).strip()],
        "enabled": True,
        "source": str(event.get("source", "personal")).strip() or "personal",
        "requires_done": event.get("requires_done"),
        "done": event.get("done"),
        "done_at": event.get("done_at"),
        "attention_level": str(event.get("attention_level", "green")).strip().lower() or "green",
        "blinker_minutes_before": event.get("blinker_minutes_before"),
        "notification_icon": str(event.get("notification_icon", "")).strip(),
    }


def load_agenda(path: Path | None = None) -> list[dict[str, Any]] | None:
    agenda_path = path or project_path("agenda.json")
    try:
        raw = agenda_store.load_agenda_document(agenda_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        LOGGER.error("Could not load agenda.json: %s", exc)
        LOGGER.error("Agenda reload failed; will retry")
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("events"), list):
        LOGGER.error("agenda.json must contain an events list")
        return None

    seen_ids: set[str] = set()
    valid_events = []
    for index, event in enumerate(raw["events"]):
        validated = validate_event(event, seen_ids, index)
        if validated is not None:
            valid_events.append(validated)
    LOGGER.info("Agenda loaded: %s enabled valid event(s)", len(valid_events))
    return valid_events


def ensure_astronomy_schedule(
    location: dict[str, Any], path: Path | None = None, *, today: Any | None = None
) -> dict[str, Any] | None:
    """Regenerate derived astronomy facts after a canonical location change."""
    schedule_path = path or project_path("astronomy/astronomy_schedule.json")
    raw = load_json_file(schedule_path)
    expected = location_store.location_fingerprint(location)
    if isinstance(raw, dict):
        actual = str(raw.get("location_fingerprint", ""))
        status = str(raw.get("generation_status", ""))
        if actual == expected and status == "fresh" and isinstance(raw.get("daily_records"), list) and raw["daily_records"]:
            return raw
        if actual == expected and status == "pending_precise_ephemeris":
            return raw

    try:
        from astronomy import generate_astronomy

        local_today = today or datetime.now(ZoneInfo(str(location["timezone"]))).date()
        regenerated = generate_astronomy.generate_schedule(location, today=local_today, horizon_months=24)
        generate_astronomy.write_json(schedule_path, regenerated)
        LOGGER.info(
            "Astronomy schedule refreshed: status=%s location=%s days=%s",
            regenerated.get("generation_status"), expected, len(regenerated.get("daily_records", [])),
        )
        return regenerated
    except Exception as exc:  # noqa: BLE001 - watcher must remain alive.
        LOGGER.error("Astronomy regeneration failed: %s", exc)
        return raw if isinstance(raw, dict) else None


def load_astronomy_settings(path: Path | None = None) -> dict[str, Any]:
    settings_path = path or project_path("astronomy/astronomy_config.json")
    raw = load_json_file(settings_path)
    if not isinstance(raw, dict):
        LOGGER.warning("Using empty astronomy settings because astronomy_config.json is missing or invalid")
        return {
            "timezone": None,
            "notifications": {},
            "briefing": {"enabled": False, "time": "06:30", "include_day_night": True, "include_weather": True},
        }
    notifications = raw.get("notifications")
    if not isinstance(notifications, dict):
        notifications = {}
    # Astronomy supports only Sun and Moon groups. Legacy groups and reminder
    # offsets are ignored at this boundary so old JSON remains loadable without
    # reintroducing retired behavior.
    notifications = {
        key: value for key, value in notifications.items()
        if key in {"sun", "moon"} and isinstance(value, dict)
    }
    briefing = raw.get("briefing")
    if not isinstance(briefing, dict):
        briefing = {"enabled": True, "time": "06:30", "include_day_night": True, "include_weather": True}
    return {
        "timezone": str(raw.get("timezone", "")).strip() or None,
        "notifications": notifications,
        "briefing": briefing,
    }


def astronomy_event_enabled(settings: dict[str, Any], group: str, event_name: str) -> bool:
    group_settings = settings.get("notifications", {}).get(group, {})
    if not isinstance(group_settings, dict) or group_settings.get("enabled") is not True:
        return False
    events = group_settings.get("events", {})
    if not isinstance(events, dict):
        return False
    event_setting = events.get(event_name)
    if isinstance(event_setting, dict):
        return event_setting.get("enabled") is True
    return event_setting is True


def astronomy_event_offsets(
    settings: dict[str, Any], group: str, event_name: str, default: list[int] | None = None
) -> list[int]:
    # Individual Astronomy notifications are event-time notifications. The
    # briefing has its own delivery time and does not use event reminders.
    return [0]


def load_astronomy_events(
    path: Path | None = None, settings_path: Path | None = None
) -> list[dict[str, Any]] | None:
    schedule_path = path or project_path("astronomy/astronomy_schedule.json")
    raw = load_json_file(schedule_path)
    if raw is None:
        LOGGER.warning("Astronomy schedule unavailable; continuing with personal events only")
        return []
    if not isinstance(raw, dict) or not isinstance(raw.get("daily_records"), list):
        LOGGER.error("astronomy_schedule.json must contain a daily_records list")
        return []

    settings = load_astronomy_settings(settings_path)
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for record in raw["daily_records"]:
        if not isinstance(record, dict):
            LOGGER.warning("Invalid astronomy record: record must be an object")
            continue
        events.extend(normalize_astronomy_record(record, settings, seen_ids))
    LOGGER.info("Astronomy loaded: %s enabled notification event(s)", len(events))
    return events


def normalize_astronomy_record(
    record: dict[str, Any], settings: dict[str, Any], seen_ids: set[str]
) -> list[dict[str, Any]]:
    date = str(record.get("date", "")).strip()
    if not date:
        LOGGER.warning("Invalid astronomy record: missing date")
        return []

    normalized = []
    sunset_enabled = astronomy_event_enabled(settings, "sun", "sunset")
    moon_status_enabled = astronomy_event_enabled(settings, "moon", "moon_status_at_sunset")
    sunset = record.get("sunset") if isinstance(record.get("sunset"), dict) else None
    moon_status = (
        record.get("moon_status_at_sunset")
        if isinstance(record.get("moon_status_at_sunset"), dict)
        else None
    )

    if sunset_enabled and sunset:
        if moon_status_enabled and moon_status:
            event = build_evening_astronomy_event(
                date,
                sunset,
                moon_status,
                astronomy_event_offsets(settings, "sun", "sunset"),
                record,
            )
        else:
            event = build_simple_astronomy_event(
                event_id=f"astro-sunset-{date}",
                title="Sunset",
                start=sunset.get("time"),
                description=build_sunset_description(sunset),
                tags=["astronomy", "sunset"],
                offsets=astronomy_event_offsets(settings, "sun", "sunset"),
            )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    if astronomy_event_enabled(settings, "sun", "sunrise") and isinstance(record.get("sunrise"), dict):
        sunrise = record["sunrise"]
        event = build_simple_astronomy_event(
            event_id=f"astro-sunrise-{date}",
            title="Sunrise",
            start=sunrise.get("time"),
            description="Sunrise.",
            tags=["astronomy", "sunrise"],
            offsets=astronomy_event_offsets(settings, "sun", "sunrise"),
        )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    if astronomy_event_enabled(settings, "sun", "solar_noon") and isinstance(record.get("solar_noon"), dict):
        solar_noon = record["solar_noon"]
        event = build_simple_astronomy_event(
            event_id=f"astro-solar-noon-{date}",
            title="Solar noon",
            start=solar_noon.get("time"),
            description=build_solar_noon_description(solar_noon),
            tags=["astronomy", "solar-noon"],
            offsets=astronomy_event_offsets(settings, "sun", "solar_noon"),
        )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    if astronomy_event_enabled(settings, "sun", "civil_twilight") and isinstance(record.get("civil_twilight_end"), dict):
        twilight = record["civil_twilight_end"]
        event = build_simple_astronomy_event(
            event_id=f"astro-civil-twilight-{date}",
            title="Civil twilight ends",
            start=twilight.get("time"),
            description="Civil twilight ends.",
            tags=["astronomy", "civil-twilight"],
            offsets=astronomy_event_offsets(settings, "sun", "civil_twilight"),
        )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    if astronomy_event_enabled(settings, "moon", "moonrise") and isinstance(record.get("moonrise"), str):
        event = build_simple_astronomy_event(
            event_id=f"astro-moonrise-{date}",
            title="Moonrise",
            start=record["moonrise"],
            description=build_moon_event_description(record, "Moonrise.", record["moonrise"]),
            tags=["astronomy", "moonrise"],
            offsets=astronomy_event_offsets(settings, "moon", "moonrise"),
            notification_icon=moon_notification_icon(record, "moonrise"),
        )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    if astronomy_event_enabled(settings, "moon", "moonset") and isinstance(record.get("moonset"), str):
        event = build_simple_astronomy_event(
            event_id=f"astro-moonset-{date}",
            title="Moonset",
            start=record["moonset"],
            description=build_moon_event_description(record, "Moonset.", record["moonset"]),
            tags=["astronomy", "moonset"],
            offsets=astronomy_event_offsets(settings, "moon", "moonset"),
            notification_icon=moon_notification_icon(record, "moonset"),
        )
        validated = validate_event(event, seen_ids, len(seen_ids))
        if validated is not None:
            normalized.append(validated)

    for phase_name, key in (("Full Moon", "full_moon"), ("New Moon", "new_moon")):
        phase = record.get(key)
        if astronomy_event_enabled(settings, "moon", key) and isinstance(phase, dict) and phase.get("time"):
            event = build_simple_astronomy_event(
                event_id=f"astro-{key.replace('_', '-')}-{phase['time']}",
                title=phase_name,
                start=phase["time"],
                description=build_moon_event_description(
                    record,
                    f"{moon_phase_icon(record.get('moon_phase', 0))} {phase_name}.",
                    phase["time"],
                ),
                tags=["astronomy", "moon", key.replace("_", "-")],
                offsets=[0],
                notification_icon=moon_notification_icon(record, key),
            )
            validated = validate_event(event, seen_ids, len(seen_ids))
            if validated is not None:
                normalized.append(validated)

    return normalized


def build_simple_astronomy_event(
    event_id: str,
    title: str,
    start: Any,
    description: str,
    tags: list[str],
    offsets: list[int] | None = None,
    notification_icon: str | None = None,
) -> dict[str, Any]:
    event = {
        "id": event_id,
        "title": title,
        "description": description,
        "start": str(start or ""),
        "reminders_minutes_before": offsets or [0],
        "priority": "default",
        "tags": tags,
        "enabled": True,
        "source": "astronomy",
    }
    if notification_icon:
        event["notification_icon"] = notification_icon
    return event


def build_evening_astronomy_event(
    date: str,
    sunset: dict[str, Any],
    moon_status: dict[str, Any],
    offsets: list[int] | None = None,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_simple_astronomy_event(
        event_id=f"astro-evening-{date}",
        title="Sunset",
        start=sunset.get("time"),
        description=build_evening_astronomy_description(sunset, moon_status, record),
        tags=["astronomy", "sunset", "moon"],
        offsets=offsets,
    )


def build_sunset_description(sunset: dict[str, Any]) -> str:
    lines = []
    dark = sunset.get("civil_twilight_end")
    if dark:
        lines.append(f"Dark: {format_time_label(str(dark))}")
    day_length = sunset.get("day_length_minutes")
    if isinstance(day_length, int):
        lines.append(f"Day length: {day_length // 60} h {day_length % 60:02d} min")
    return "\n".join(lines)


def build_solar_noon_description(solar_noon: dict[str, Any]) -> str:
    elevation = solar_noon.get("solar_elevation_degrees")
    if isinstance(elevation, (int, float)):
        return f"Solar noon. Sun: {float(elevation):.1f}° above horizon."
    return "Solar noon."


def build_evening_astronomy_description(
    sunset: dict[str, Any], moon_status: dict[str, Any], record: dict[str, Any] | None = None
) -> str:
    lines = build_sunset_description(sunset).splitlines()
    if lines:
        lines.append("")
    lines.append(moon_phase_summary_line(moon_status, record, sunset.get("time")))
    if "above_horizon" in moon_status:
        lines.append("Above horizon" if moon_status["above_horizon"] else "Below horizon")
    if moon_status.get("moonset"):
        lines.append(f"🌙 Moonset: {format_time_label(str(moon_status['moonset']))}")
    if moon_status.get("moonrise"):
        lines.append(f"🌙 Moonrise: {format_time_label(str(moon_status['moonrise']))}")
    moon_context = dict(record or {})
    moon_context["moon_status_at_sunset"] = moon_status
    lines.extend(moon_notification_tail(moon_context, sunset.get("time")))
    return "\n".join(lines)


def build_moon_event_description(record: dict[str, Any], heading: str, event_time: str) -> str:
    """Keep every standalone lunar event in the same readable shape."""
    del heading
    return "\n".join(moon_notification_tail(record, event_time))


def moon_trend(source: dict[str, Any], reference_time: Any = None) -> str:
    moon_status = source.get("moon_status_at_sunset")
    status = moon_status if isinstance(moon_status, dict) else source
    phase = status.get("phase_degrees", source.get("moon_phase"))
    reference = _moon_reference_time(source, reference_time)
    trend = str(status.get("phase_trend", "")).strip().lower()
    full_moon_today = _moon_phase_time(source.get("full_moon"))
    new_moon_today = _moon_phase_time(source.get("new_moon"))
    if reference and full_moon_today:
        trend = "waxing" if reference < full_moon_today else "waning"
    elif reference and new_moon_today:
        trend = "waxing" if reference >= new_moon_today else "waning"
    if trend not in {"waxing", "waning"} and isinstance(phase, (int, float)):
        trend = "waxing" if float(phase) % 360.0 < 180.0 else "waning"
    if trend not in {"waxing", "waning"}:
        trend = "waxing"
    return trend


def moon_direction_arrow(trend: str) -> str:
    return {"waxing": "⬆️", "waning": "⬇️"}.get(trend, "⬆️")


def moon_phase_summary_line(
    status: dict[str, Any], source: dict[str, Any] | None = None, reference_time: Any = None
) -> str:
    source = source or status
    exact_phase = _exact_phase_name(source)
    trend = moon_trend(source, reference_time)
    phase_icon = "🌕" if exact_phase == "Full Moon" else "🌑" if exact_phase == "New Moon" else ("🌒" if trend == "waxing" else "🌘")
    phase_name = exact_phase or ("Waxing Moon" if trend == "waxing" else "Waning Moon")
    summary = str(status.get("summary") or "status unavailable").strip()
    for prefix in ("waxing - ", "waning - "):
        if summary.lower().startswith(prefix):
            summary = summary[len(prefix):]
            break
    direction = "" if exact_phase else f" {moon_direction_arrow(trend)}"
    return f"{phase_icon}{direction} {phase_name} — {summary}"


def _exact_phase_name(source: dict[str, Any]) -> str | None:
    if isinstance(source.get("new_moon"), dict) and source["new_moon"].get("time"):
        return "New Moon"
    if isinstance(source.get("full_moon"), dict) and source["full_moon"].get("time"):
        return "Full Moon"
    return None


def moon_notification_tail(source: dict[str, Any], reference_time: Any = None) -> list[str]:
    """Return the final next-phase countdown line for a lunar message."""
    trend = moon_trend(source, reference_time)
    reference = _moon_reference_time(source, reference_time)

    target_name = "Full Moon" if trend == "waxing" else "New Moon"
    candidate_values = (
        [source.get("full_moon"), source.get("next_full_moon")]
        if trend == "waxing"
        else [source.get("new_moon"), source.get("next_new_moon")]
    )
    target = next(
        (
            candidate
            for candidate in (_moon_phase_time(value) for value in candidate_values)
            if candidate and (reference is None or candidate.date() >= reference.date())
        ),
        None,
    )
    days_label = f"Days until {target_name}: unavailable"
    if target and reference:
        days = max(0, (target.date() - reference.date()).days)
        day_label = "day" if days == 1 else "days"
        days_label = f"{days} {day_label} until {target_name}."
    return [days_label]


def _moon_reference_time(source: dict[str, Any], reference_time: Any) -> datetime | None:
    raw = reference_time or source.get("date")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw))
        if parsed.tzinfo is None and source.get("timezone"):
            parsed = parsed.replace(tzinfo=ZoneInfo(str(source["timezone"])))
        return parsed
    except ValueError:
        return None


def _moon_phase_time(value: Any) -> datetime | None:
    raw = value.get("time") if isinstance(value, dict) else value
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def build_astronomy_briefing_message(
    schedule: dict[str, Any] | None,
    forecast_date: str,
    settings: dict[str, Any],
    *,
    include_heading: bool = True,
) -> str:
    """Build only the astronomy section for the grouped daily briefing."""
    briefing = settings.get("briefing", {})
    if not isinstance(briefing, dict) or briefing.get("enabled") is not True:
        return ""
    records = schedule.get("daily_records", []) if isinstance(schedule, dict) else []
    record = next((item for item in records if isinstance(item, dict) and item.get("date") == forecast_date), None)
    if record is None:
        return ""
    lines = (["ASTRONOMY", forecast_date] if include_heading else [forecast_date])
    sunrise = record.get("sunrise")
    sunset = record.get("sunset")
    if isinstance(sunrise, dict) and sunrise.get("time"):
        lines.append(f"☀️ Sunrise: {format_time_label(str(sunrise['time']))}")
    elif record.get("sunrise_status") == "no_event_today":
        lines.append("☀️ Sunrise: no event today")
    if isinstance(sunset, dict) and sunset.get("time"):
        lines.append(f"☀️ Sunset: {format_time_label(str(sunset['time']))}")
    elif record.get("sunset_status") == "no_event_today":
        lines.append("☀️ Sunset: no event today")
    if briefing.get("include_day_night") is True:
        day_length = record.get("day_length_minutes")
        if isinstance(day_length, int):
            night_length = max(0, 1440 - day_length)
            lines.append(f"🌞 Day length: {day_length // 60} h {day_length % 60:02d} min")
            lines.append(f"🌙 Night length: {night_length // 60} h {night_length % 60:02d} min")
    moon = record.get("moon_status_at_sunset")
    if isinstance(moon, dict) and moon.get("summary"):
        lines.append(moon_phase_summary_line(moon, record))
    moonrise = record.get("moonrise") or (moon or {}).get("moonrise")
    moonset = record.get("moonset") or (moon or {}).get("moonset")
    if moonrise:
        lines.append(f"🌙 Moonrise: {format_time_label(str(moonrise))}")
    else:
        next_rise = record.get("next_moonrise")
        lines.append(
            f"🌙 Moonrise: {format_time_label(str(next_rise))} next" if next_rise else "🌙 Moonrise: no event today"
        )
    if moonset:
        lines.append(f"🌙 Moonset: {format_time_label(str(moonset))}")
    else:
        next_set = record.get("next_moonset")
        lines.append(
            f"🌙 Moonset: {format_time_label(str(next_set))} next" if next_set else "🌙 Moonset: no event today"
        )
    lines.extend(moon_notification_tail(record))
    return "\n".join(lines) if len(lines) > 2 else ""


def astronomy_briefing_key(forecast_date: str, briefing_time: str) -> str:
    return f"astronomy-briefing|{forecast_date}|{briefing_time}"


def build_astronomy_briefing_item(
    schedule: dict[str, Any],
    forecast_date: str,
    settings: dict[str, Any],
    delivery_time: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    body = build_astronomy_briefing_message(
        schedule,
        forecast_date,
        settings,
        include_heading=False,
    )
    if not body:
        return None
    briefing_time = str(settings.get("briefing", {}).get("time", "06:30"))
    safe_briefing_time = briefing_time.replace(":", "")
    return {
        "sequence_id": f"blink-astronomy-briefing-{forecast_date}-{safe_briefing_time}",
        "delivery_time": delivery_time,
        "payload": {
            "title": "ASTRONOMY",
            "body": body,
            "priority": config.get("default_priority", "default"),
            "tags": ["astronomy"],
        },
    }


def process_astronomy_briefing(
    *,
    config: dict[str, Any],
    state: dict[str, Any],
    schedule: dict[str, Any] | None,
    settings: dict[str, Any],
    now: datetime,
    send_now_func: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    briefing = settings.get("briefing", {})
    if not isinstance(briefing, dict) or briefing.get("enabled") is not True:
        return state
    if briefing.get("include_weather") is True:
        return state
    if not isinstance(schedule, dict):
        return state
    records = schedule.get("daily_records")
    if not isinstance(records, list):
        return state
    timezone_name = str(
        settings.get("timezone")
        or schedule.get("timezone")
        or ((schedule.get("location") or {}).get("timezone") if isinstance(schedule.get("location"), dict) else "")
        or "UTC"
    )
    try:
        local_now = now.astimezone(ZoneInfo(timezone_name))
    except Exception:  # noqa: BLE001 - invalid settings must not stop the watcher.
        LOGGER.error("Astronomy briefing timezone is invalid: %s", timezone_name)
        return state
    briefing_time = str(briefing.get("time", "06:30"))
    try:
        hour, minute = [int(part) for part in briefing_time.split(":", 1)]
        target = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, TypeError):
        LOGGER.error("Astronomy briefing time is invalid: %s", briefing_time)
        return state
    forecast_date = local_now.date().isoformat()
    key = astronomy_briefing_key(forecast_date, briefing_time)
    delivered = state.setdefault("delivered", {})
    if key in delivered or local_now < target:
        return state
    item = build_astronomy_briefing_item(schedule, forecast_date, settings, now.isoformat(), config)
    send_now = send_now_func or send_astronomy_briefing_notification
    if item is None or not send_now(config, item):
        return state
    delivered[key] = {"delivered_at": now.isoformat()}
    cleanup_old_state(state, now)
    LOGGER.info("Astronomy briefing sent: date=%s time=%s", forecast_date, briefing_time)
    return state


def moon_phase_icon(phase_degrees: int | float) -> str:
    """Map the illuminated lunar phase angle to the closest Unicode phase icon."""
    phase = float(phase_degrees) % 360.0
    if phase < 22 or phase >= 338:
        return "🌑"
    if phase < 68:
        return "🌒"
    if phase < 112:
        return "🌓"
    if phase < 158:
        return "🌔"
    if phase < 202:
        return "🌕"
    if phase < 248:
        return "🌖"
    if phase < 292:
        return "🌗"
    return "🌘"


def moon_notification_icon(record: dict[str, Any], event_name: str) -> str:
    """Return a phase glyph and trend arrow for an individual Moon notification."""
    if event_name == "full_moon":
        return "🌕"
    if event_name == "new_moon":
        return "🌑"
    exact_phase = _exact_phase_name(record)
    if exact_phase:
        return "🌕" if exact_phase == "Full Moon" else "🌑"
    status = record.get("moon_status_at_sunset")
    status_trend = status.get("phase_trend") if isinstance(status, dict) else None
    trend = str(record.get("moon_phase_trend") or status_trend or "").strip().lower()
    glyph = "🌒" if trend == "waxing" else "🌘" if trend == "waning" else "🌙"
    arrow = {"waxing": "⬆️", "waning": "⬇️"}.get(trend)
    return f"{glyph} {arrow}" if arrow else glyph


def format_time_label(iso_text: str) -> str:
    try:
        return datetime.fromisoformat(iso_text).strftime("%H:%M")
    except ValueError:
        return iso_text


def format_date_label(iso_text: str) -> str:
    try:
        return datetime.fromisoformat(iso_text).strftime("%b %-d, %Y %H:%M")
    except ValueError:
        return iso_text


def load_notification_events(
    config: dict[str, Any],
    agenda_path: Path | None = None,
    astronomy_path: Path | None = None,
    astronomy_config_path: Path | None = None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    personal_events = load_agenda(agenda_path)
    if personal_events is not None:
        events.extend(personal_events)
    astronomy_events = load_astronomy_events(astronomy_path, astronomy_config_path)
    if astronomy_events is not None:
        events.extend(astronomy_events)
    return events


def load_state(path: Path | None = None) -> dict[str, Any]:
    state_path = path or project_path("watcher_state.json")
    raw = load_json_file(state_path)
    if not isinstance(raw, dict) or not isinstance(raw.get("delivered"), dict):
        LOGGER.warning("Using empty state because watcher_state.json is missing or invalid")
        return {"version": 1, "delivered": {}}
    return {"version": 1, "delivered": dict(raw["delivered"])}


def save_state_atomic(path: Path, state: dict[str, Any]) -> None:
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def cleanup_old_state(state: dict[str, Any], now: datetime) -> None:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=90)
    delivered = state.get("delivered", {})
    for key, info in list(delivered.items()):
        if not isinstance(info, dict):
            continue
        delivered_at = info.get("delivered_at")
        if not isinstance(delivered_at, str):
            continue
        try:
            delivered_dt = datetime.fromisoformat(delivered_at)
        except ValueError:
            continue
        if delivered_dt.tzinfo is None or delivered_dt.utcoffset() is None:
            continue
        if delivered_dt.astimezone(timezone.utc) < cutoff:
            del delivered[key]


def build_reminder_key(event_id: str, event_start: str, offset_minutes: int) -> str:
    return f"{event_id}|{event_start}|{offset_minutes}"


def _header_value(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _ntfy_header_value(value: str) -> str:
    """Return an ASCII-safe ntfy header, including RFC 2047 for Unicode."""
    value = _header_value(value)
    if any(ord(character) > 127 for character in value):
        return Header(value, "utf-8").encode()
    return value


def build_ntfy_request(
    *,
    config: dict[str, Any],
    title: str | None,
    message: str,
    priority: str,
    tags: list[str],
    sequence_id: str | None = None,
    delivery_time: str | None = None,
) -> urllib.request.Request:
    # Use ntfy's documented topic endpoint. Metadata stays in headers and the
    # user sees only the plain message body, never a JSON envelope.
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Priority": _ntfy_header_value(priority),
        "Tags": _ntfy_header_value(",".join(tags)),
    }
    if title:
        headers["Title"] = _ntfy_header_value(title)
    if sequence_id:
        headers["X-Sequence-ID"] = _header_value(sequence_id)
    if delivery_time:
        headers["Delay"] = str(int(datetime.fromisoformat(delivery_time).timestamp()))
    return urllib.request.Request(
        f"{config['ntfy_server']}/{config['ntfy_topic']}",
        data=message.encode("utf-8"),
        method="POST",
        headers=headers,
    )


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def send_ntfy_notification(
    config: dict[str, Any], event: dict[str, Any], offset_minutes: int
) -> bool:
    effective_start = event.get("effective_start_dt") or event.get("start_dt") or effective_event_start(event)
    if effective_start is None:
        LOGGER.error("Notification skipped: event %s has no valid start", event.get("id", "<unknown>"))
        return False
    title, body = build_event_notification(event, offset_minutes, effective_start.isoformat())
    priority = event["priority"] if event["priority"] != "default" else config["default_priority"]
    tags = push_tags_for_event(event, config["default_tags"])
    request = build_ntfy_request(
        config=config,
        title=title,
        message=body,
        priority=priority,
        tags=tags,
    )

    LOGGER.info(
        "Notification attempt: event=%s offset=%s topic=%s",
        event["id"],
        offset_minutes,
        redact_topic(config["ntfy_topic"]),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        LOGGER.error(
            "Notification failure: event=%s offset=%s HTTP %s: %s; will retry within grace window",
            event["id"], offset_minutes, exc.code, _http_error_detail(exc),
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOGGER.error(
            "Notification failure: event=%s offset=%s error=%s; will retry within grace window",
            event["id"],
            offset_minutes,
            exc,
        )
        return False

    if 200 <= status < 300:
        LOGGER.info("Notification success: event=%s offset=%s status=%s", event["id"], offset_minutes, status)
        return True

    LOGGER.error(
        "Notification failure: event=%s offset=%s status=%s; will retry within grace window",
        event["id"],
        offset_minutes,
        status,
    )
    return False


def process_due_reminders(
    config: dict[str, Any],
    events: list[dict[str, Any]],
    state: dict[str, Any],
    now: datetime,
    send_func: Callable[[dict[str, Any], dict[str, Any], int], bool] = send_ntfy_notification,
    state_path: Path | None = None,
    remote_schedule_state: dict[str, Any] | None = None,
) -> None:
    delivered = state.setdefault("delivered", {})
    grace = timedelta(minutes=config.get("late_delivery_grace_minutes", 5))

    for event in events:
        if event.get("source", "personal") == "personal" and event.get("done") is True:
            LOGGER.info("Skipped done event reminders: %s", event["id"])
            continue
        due_offsets: list[tuple[int, str]] = []
        for offset in event["reminders_minutes_before"]:
            effective_start = event["start_dt"]
            effective_start_text = effective_start.isoformat()
            key = build_reminder_key(event["id"], effective_start_text, offset)
            reminder_time = effective_start - timedelta(minutes=offset)
            now_for_event = now.astimezone(reminder_time.tzinfo)
            if now_for_event < reminder_time:
                continue
            if now_for_event > reminder_time + grace:
                LOGGER.info("Skipped expired reminder: %s", key)
                continue
            due_offsets.append((offset, key))

        if not due_offsets:
            continue
        offset, key = min(due_offsets, key=lambda item: item[0])
        effective_start = event["start_dt"]
        reminder_time = effective_start - timedelta(minutes=offset)
        if key in delivered:
            continue
        if remote_schedule_state and ntfy_schedule.is_reminder_owned_by_remote(remote_schedule_state, key):
            LOGGER.info("Skipped direct send for remotely queued reminder: %s", key)
            continue

        if send_func(config, event, offset):
            delivered[key] = {"delivered_at": now.isoformat()}
            cleanup_old_state(state, now)
            if state_path is not None:
                save_state_atomic(state_path, state)


def send_scheduled_ntfy_notification(config: dict[str, Any], item: dict[str, Any]) -> bool:
    payload = item["payload"]
    request = build_ntfy_request(
        config=config,
        title=str(payload["title"]),
        message=str(payload["body"]),
        priority=str(payload["priority"]),
        tags=list(payload["tags"]),
        sequence_id=str(item["sequence_id"]),
        delivery_time=str(item["delivery_time"]),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        LOGGER.error(
            "Remote schedule failure: seq=%s HTTP %s: %s",
            item["sequence_id"], exc.code, _http_error_detail(exc),
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOGGER.error("Remote schedule failure: seq=%s error=%s", item["sequence_id"], exc)
        return False
    return 200 <= status < 300


def send_astronomy_briefing_notification(config: dict[str, Any], item: dict[str, Any]) -> bool:
    payload = item["payload"]
    request = build_ntfy_request(
        config=config,
        title=str(payload["title"]),
        message=str(payload["body"]),
        priority=str(payload["priority"]),
        tags=list(payload["tags"]),
        sequence_id=str(item["sequence_id"]),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        LOGGER.error(
            "Astronomy briefing notification failure: seq=%s HTTP %s: %s",
            item["sequence_id"], exc.code, _http_error_detail(exc),
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOGGER.error("Astronomy briefing notification failure: seq=%s error=%s", item["sequence_id"], exc)
        return False
    return 200 <= status < 300


def send_weather_ntfy_notification(config: dict[str, Any], item: dict[str, Any]) -> bool:
    payload = item["payload"]
    request = build_ntfy_request(
        config=config,
        title=str(payload["title"]),
        message=str(payload["body"]),
        priority=str(payload["priority"]),
        tags=list(payload["tags"]),
        sequence_id=str(item["sequence_id"]),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        LOGGER.error(
            "Weather notification failure: seq=%s HTTP %s: %s",
            item["sequence_id"], exc.code, _http_error_detail(exc),
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOGGER.error("Weather notification failure: seq=%s error=%s", item["sequence_id"], exc)
        return False
    return 200 <= status < 300


def cancel_scheduled_ntfy_notification(config: dict[str, Any], item: dict[str, Any]) -> bool:
    url = f"{config['ntfy_server']}/{config['ntfy_topic']}/{item['sequence_id']}"
    request = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOGGER.error("Remote schedule cancel failure: seq=%s error=%s", item["sequence_id"], exc)
        return False
    return 200 <= status < 300 or status == 404


def reconcile_remote_schedule(
    config: dict[str, Any],
    events: list[dict[str, Any]],
    now: datetime,
    schedule_state_path: Path | None = None,
) -> dict[str, Any]:
    schedule_state_path = schedule_state_path or project_path("ntfy_schedule_state.json")
    state = ntfy_schedule.load_state(schedule_state_path)
    desired = ntfy_schedule.build_desired_queue(
        events=events,
        now=now,
        window_hours=24,
        config=config,
    )
    reconciled = ntfy_schedule.reconcile(
        desired=desired,
        state=state,
        schedule_func=lambda item: send_scheduled_ntfy_notification(config, item),
        cancel_func=lambda item: cancel_scheduled_ntfy_notification(config, item),
        now=now,
    )
    ntfy_schedule.save_state_atomic(schedule_state_path, reconciled)
    return reconciled


def remote_reconcile_due(events: list[dict[str, Any]], now: datetime, interval_minutes: int = 60) -> bool:
    """Reconcile on startup/config changes and at a slow safety interval."""
    global _last_remote_reconcile_at, _last_remote_reconcile_signature
    signature_payload = [
        {
            "id": event.get("id"),
            "start": event.get("start"),
            "enabled": event.get("enabled"),
            "done": event.get("done"),
            "title": event.get("title"),
            "description": event.get("description"),
            "attention_level": event.get("attention_level"),
            "reminders": event.get("reminders_minutes_before"),
        }
        for event in events
    ]
    signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if _last_remote_reconcile_at is None or _last_remote_reconcile_signature != signature:
        _last_remote_reconcile_at = now
        _last_remote_reconcile_signature = signature
        return True
    if now - _last_remote_reconcile_at >= timedelta(minutes=interval_minutes):
        _last_remote_reconcile_at = now
        return True
    return False


def load_weather_config(path: Path | None = None) -> dict[str, Any]:
    raw = load_json_file(path or project_path("weather/weather_config.json"))
    if not isinstance(raw, dict):
        return weather_store.default_config()
    default = weather_store.default_config()
    default.update(raw)
    if not isinstance(default.get("morning_briefing"), dict):
        default["morning_briefing"] = weather_store.default_config()["morning_briefing"]
    if not isinstance(default.get("thresholds"), dict):
        default["thresholds"] = weather_store.default_config()["thresholds"]
    return default


def load_weather_state(path: Path | None = None) -> dict[str, Any]:
    raw = load_json_file(path or project_path("weather/weather_state.json"))
    if not isinstance(raw, dict):
        return weather_store.default_state()
    default = weather_store.default_state()
    default.update(raw)
    return default


def build_weather_briefing_item(
    forecast: dict[str, Any], delivery_time: str, config: dict[str, Any], body: str | None = None
) -> dict[str, Any]:
    forecast_date = str(forecast["forecast_date"])
    return {
        "sequence_id": f"blink-weather-morning-{forecast_date}",
        "delivery_time": delivery_time,
        "payload": {
            "title": "WEATHER",
            "body": body or weather_store.build_morning_briefing_message(forecast),
            "priority": config.get("default_priority", "default"),
            "tags": ["weather"],
        },
    }


def process_weather_briefing(
    *,
    config: dict[str, Any],
    weather_config: dict[str, Any],
    weather_state: dict[str, Any],
    forecast: dict[str, Any],
    now: datetime,
    send_now_func: Callable[[dict[str, Any], dict[str, Any]], bool] = send_weather_ntfy_notification,
    schedule_func: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
    astronomy_message: str = "",
) -> dict[str, Any]:
    briefing_time = str(weather_config.get("morning_briefing", {}).get("time", "06:30"))
    briefing_key = f"{forecast['forecast_date']}|{briefing_time}"

    if not weather_store.briefing_due(
        config=weather_config,
        state=weather_state,
        forecast_date=str(forecast["forecast_date"]),
        now=now,
        timezone_name=str(forecast["location"]["timezone"]),
    ):
        return weather_state
    delivery_time = now.isoformat()
    body = weather_store.build_morning_briefing_message(forecast)
    if astronomy_message:
        body = f"{body}\n\n{astronomy_message}"
    item = build_weather_briefing_item(forecast, delivery_time, config, body=body)
    if not send_now_func(config, item):
        result = dict(weather_state)
        result["status"] = "pending_weather_briefing"
        result["last_weather_briefing_status"] = "send_failed"
        return result

    weather_state["briefing_time"] = briefing_time
    return weather_store.mark_briefing_delivered(weather_state, forecast, "direct_sent")


def update_weather_briefing(
    *,
    config: dict[str, Any],
    location: dict[str, Any],
    weather_config: dict[str, Any],
    now: datetime,
    weather_state_path: Path | None = None,
    weather_cache_path: Path | None = None,
    fetch_func: Callable[[dict[str, Any]], dict[str, Any]] = weather_store.fetch_open_meteo_forecast,
    send_now_func: Callable[[dict[str, Any], dict[str, Any]], bool] = send_weather_ntfy_notification,
    schedule_func: Callable[[dict[str, Any], dict[str, Any]], bool] | None = None,
    astronomy_schedule: dict[str, Any] | None = None,
    astronomy_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weather_state_path = weather_state_path or project_path("weather/weather_state.json")
    weather_cache_path = weather_cache_path or project_path("weather/weather_cache.json")
    state = load_weather_state(weather_state_path)
    local_now = now.astimezone(ZoneInfo(str(location["timezone"])))
    forecast_date = local_now.date().isoformat()
    if not weather_store.briefing_due(
        config=weather_config,
        state=state,
        forecast_date=forecast_date,
        now=now,
        timezone_name=str(location["timezone"]),
    ):
        return state
    if not weather_store.retry_allowed(state, now):
        return state
    state["last_fetch_attempt_at"] = now.isoformat()
    try:
        payload = fetch_func(location)
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=payload,
            location=location,
            fetched_at=now,
            config=weather_config,
        )
    except Exception as exc:  # noqa: BLE001 - watcher must keep running after weather failures.
        result = weather_store.record_fetch_failure(state, str(exc))
        weather_store.save_json_atomic(weather_state_path, result)
        return result

    weather_store.save_json_atomic(weather_cache_path, forecast)
    astronomy_message = ""
    if isinstance(astronomy_settings, dict):
        briefing = astronomy_settings.get("briefing", {})
        if isinstance(briefing, dict) and briefing.get("include_weather") is True:
            astronomy_message = build_astronomy_briefing_message(
                astronomy_schedule,
                str(forecast["forecast_date"]),
                astronomy_settings,
            )
    result = process_weather_briefing(
        config=config,
        weather_config=weather_config,
        weather_state=state,
        forecast=forecast,
        now=now,
        send_now_func=send_now_func,
        schedule_func=None,
        astronomy_message=astronomy_message,
    )
    weather_store.save_json_atomic(weather_state_path, result)
    return result


def run_weather_cycle(config: dict[str, Any], now: datetime) -> dict[str, Any]:
    location = location_store.load_location(project_path("location.json"))
    weather_config = load_weather_config()
    astronomy_schedule = load_json_file(project_path("astronomy/astronomy_schedule.json"))
    astronomy_settings = load_astronomy_settings()
    return update_weather_briefing(
        config=config,
        location=location,
        weather_config=weather_config,
        now=now,
        astronomy_schedule=astronomy_schedule,
        astronomy_settings=astronomy_settings,
    )


def run_astronomy_briefing_cycle(
    config: dict[str, Any], state: dict[str, Any], now: datetime
) -> dict[str, Any]:
    schedule = load_json_file(project_path("astronomy/astronomy_schedule.json"))
    settings = load_astronomy_settings()
    return process_astronomy_briefing(
        config=config,
        state=state,
        schedule=schedule,
        settings=settings,
        now=now,
    )


def handle_shutdown(signum: int, _frame: Any) -> None:
    global SHUTTING_DOWN
    SHUTTING_DOWN = True
    LOGGER.info("Watcher stop requested by signal %s", signum)


def main() -> int:
    setup_logging()
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    LOGGER.info("Watcher start")
    config = load_config()
    if config is None:
        LOGGER.error("Watcher did not start because configuration is incomplete")
        return 2

    print(
        "Blink Watcher started. "
        f"Topic: {redact_topic(config['ntfy_topic'])}. "
        f"Log: {project_path('watcher.log')}"
    )
    state_path = project_path("watcher_state.json")
    runtime_path = project_path("watcher_runtime.json")
    previous_loop_at: datetime | None = None

    while not SHUTTING_DOWN:
        config = load_config()
        if config is None:
            time.sleep(10)
            continue

        now = datetime.now(timezone.utc).astimezone()
        try:
            watcher_lifecycle.write_heartbeat(runtime_path, now=now)
            if previous_loop_at and watcher_lifecycle.detect_sleep_gap(
                previous_loop_at,
                now,
                poll_interval_seconds=int(config["poll_interval_seconds"]),
            ):
                LOGGER.info(
                    "Wake gap detected: previous_loop_at=%s current_loop_at=%s",
                    previous_loop_at.isoformat(),
                    now.isoformat(),
                )
            previous_loop_at = now
            location = location_store.load_location(project_path("location.json"))
            ensure_astronomy_schedule(
                location,
                today=now.astimezone(ZoneInfo(location["timezone"])).date(),
            )
            events = load_notification_events(config)
            state = load_state(state_path)
            run_weather_cycle(config, now)
            state = run_astronomy_briefing_cycle(config, state, now)
            save_state_atomic(state_path, state)
            if remote_reconcile_due(events, now):
                remote_schedule_state = reconcile_remote_schedule(config, events, now)
            else:
                remote_schedule_state = ntfy_schedule.load_state(project_path("ntfy_schedule_state.json"))
            process_due_reminders(
                config,
                events,
                state,
                now,
                state_path=state_path,
                remote_schedule_state=remote_schedule_state,
            )
        except OSError as exc:
            LOGGER.error("State save or processing error: %s", exc)

        for _ in range(max(1, int(config["poll_interval_seconds"]))):
            if SHUTTING_DOWN:
                break
            time.sleep(1)

    LOGGER.info("Watcher stop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
