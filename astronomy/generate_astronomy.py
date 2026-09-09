#!/usr/bin/env python3
"""Generate Blink astronomy data from canonical location.

Raw calculated astronomy facts and notification settings are deliberately
separate. This module refuses to fabricate precise Sun/Moon results when
Skyfield and a local JPL ephemeris are unavailable.
"""

from __future__ import annotations

import importlib
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


PROJECT_DIR = Path(__file__).resolve().parents[1]
ASTRONOMY_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

SUPPORTED_FACTS = {
    "sun": ["sunrise", "solar_noon", "sunset", "civil_twilight_end", "day_length"],
    "moon": [
        "moon_status_at_sunset",
        "moonrise",
        "moonset",
        "moon_phase",
        "illumination",
        "full_moon",
        "new_moon",
    ],
}


def default_location() -> dict[str, Any]:
    from app.location_store import default_location as _default_location

    return _default_location()


def load_canonical_location(path: Path | None = None) -> dict[str, Any]:
    from app.location_store import load_location

    return load_location(path or PROJECT_DIR / "location.json")


def default_event_setting(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
    }


def default_config(location: dict[str, Any] | None = None) -> dict[str, Any]:
    location = location or load_canonical_location()
    return {
        "version": 2,
        "location": location,
        "location_fingerprint": _location_fingerprint(location),
        "timezone": location["timezone"],
        "briefing": {
            "enabled": True,
            "time": "06:30",
            "include_day_night": True,
            "include_weather": True,
        },
        "notifications": {
            "sun": {
                "enabled": True,
                "events": {
                    "sunrise": default_event_setting(True),
                    "solar_noon": default_event_setting(True),
                    "sunset": default_event_setting(True),
                    "civil_twilight": default_event_setting(False),
                },
            },
            "moon": {
                "enabled": True,
                "events": {
                    "moon_status_at_sunset": default_event_setting(True),
                    "moonrise": default_event_setting(False),
                    "moonset": default_event_setting(False),
                    "full_moon": default_event_setting(False),
                    "new_moon": default_event_setting(False),
                },
            },
        },
    }


def horizon_end_date(start: date, months: int = 24) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, _days_in_month(year, month))
    return date(year, month, day)


def needs_horizon_extension(
    schedule: dict[str, Any],
    *,
    today: date,
    minimum_remaining_months: int = 6,
) -> bool:
    text = str(schedule.get("generated_through", "")).strip()
    if not text:
        return True
    try:
        generated_through = date.fromisoformat(text)
    except ValueError:
        return True
    return generated_through < horizon_end_date(today, minimum_remaining_months)


def dependency_status(importer: Callable[[str], Any] = importlib.import_module) -> dict[str, Any]:
    missing = []
    for module in ("skyfield", "numpy"):
        try:
            importer(module)
        except ImportError:
            missing.append(module)
    ephemeris_path = ASTRONOMY_DIR / "ephemeris" / "de440s.bsp"
    if missing or not ephemeris_path.exists():
        reason_parts = []
        if missing:
            reason_parts.append(f"missing Python package(s): {', '.join(missing)}")
        if not ephemeris_path.exists():
            reason_parts.append(f"missing local JPL ephemeris: {ephemeris_path}")
        return {
            "available": False,
            "required": "skyfield, numpy, and local JPL ephemeris de440s.bsp",
            "reason": "; ".join(reason_parts),
        }
    return {
        "available": True,
        "required": "skyfield, numpy, and local JPL ephemeris de440s.bsp",
        "ephemeris": str(ephemeris_path),
    }


def empty_daily_record(day: date, timezone_name: str, location: dict[str, Any] | None = None) -> dict[str, Any]:
    location = location or default_location()
    return {
        "date": day.isoformat(),
        "timezone": timezone_name,
        "location": location,
        "location_fingerprint": _location_fingerprint(location),
        "sunrise": None,
        "sunrise_status": "no_event_today",
        "solar_noon": None,
        "sunset": None,
        "sunset_status": "no_event_today",
        "civil_twilight_end": None,
        "day_length_minutes": None,
        "moon_status_at_sunset": None,
        "moonrise": None,
        "moonrise_status": "no_rise_this_local_date",
        "next_moonrise": None,
        "moonset": None,
        "moonset_status": "no_set_this_local_date",
        "next_moonset": None,
        "moon_phase": None,
        "illumination": None,
        "full_moon": None,
        "new_moon": None,
        "next_full_moon": None,
        "next_new_moon": None,
    }


def validate_daily_record_shape(record: dict[str, Any]) -> None:
    required = {
        "date",
        "timezone",
        "location_fingerprint",
        "sunrise",
        "solar_noon",
        "sunset",
        "civil_twilight_end",
        "moonrise",
        "moonset",
    }
    missing = sorted(required - set(record))
    if missing:
        raise ValueError(f"Daily astronomy record missing: {', '.join(missing)}")


def build_empty_schedule(location: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    return {
        "version": 2,
        "location": location,
        "location_fingerprint": _location_fingerprint(location),
        "timezone": location["timezone"],
        "supported_facts": SUPPORTED_FACTS,
        "horizon_months": 24,
        "generated_from": today.isoformat(),
        "generated_through": horizon_end_date(today, 24).isoformat(),
        "generation_status": "pending_precise_ephemeris",
        "daily_records": [],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(path)


def write_default_files(root: Path | None = None, location_path: Path | None = None) -> None:
    root = root or ASTRONOMY_DIR
    location = load_canonical_location(location_path) if location_path else default_location()
    config_path = root / "astronomy_config.json"
    existing_config = None
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing_config = loaded
        except (OSError, json.JSONDecodeError):
            existing_config = None
    config = default_config(location)
    if existing_config is not None:
        config.update(existing_config)
        if isinstance(config.get("notifications"), dict):
            config["notifications"] = {
                key: value
                for key, value in config["notifications"].items()
                if key != "eclipses"
            }
            for group in config["notifications"].values():
                if isinstance(group, dict) and isinstance(group.get("events"), dict):
                    for event in group["events"].values():
                        if isinstance(event, dict):
                            event.pop("offsets_minutes_before", None)
        config.pop("eclipses", None)
        config.pop("reminder_presets_minutes_before", None)
    config["location"] = location
    config["location_fingerprint"] = _location_fingerprint(location)
    config["timezone"] = location["timezone"]
    schedule = build_empty_schedule(location)
    write_json(root / "astronomy_config.json", config)
    write_json(root / "astronomy_schedule.json", schedule)


def main() -> int:
    root = ASTRONOMY_DIR
    status = dependency_status()
    if not status["available"]:
        write_default_files(root)
        print("Astronomy default files written.")
        print(status["reason"])
        print("Install/approve Skyfield + NumPy and place local JPL ephemeris at astronomy/ephemeris/de440s.bsp.")
        return 2
    location = load_canonical_location()
    config_path = root / "astronomy_config.json"
    existing_config = None
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing_config = loaded
        except (OSError, json.JSONDecodeError):
            existing_config = None
    config = default_config(location)
    if existing_config is not None:
        config.update(existing_config)
        if isinstance(config.get("notifications"), dict):
            config["notifications"] = {
                key: value
                for key, value in config["notifications"].items()
                if key != "eclipses"
            }
            for group in config["notifications"].values():
                if isinstance(group, dict) and isinstance(group.get("events"), dict):
                    for event in group["events"].values():
                        if isinstance(event, dict):
                            event.pop("offsets_minutes_before", None)
        config.pop("eclipses", None)
        config.pop("reminder_presets_minutes_before", None)
    config["location"] = location
    config["location_fingerprint"] = _location_fingerprint(location)
    config["timezone"] = location["timezone"]
    schedule = generate_schedule(location, today=date.today(), horizon_months=24)
    write_json(root / "astronomy_config.json", config)
    write_json(root / "astronomy_schedule.json", schedule)
    print(f"Astronomy schedule generated: {len(schedule['daily_records'])} day(s).")
    return 0


def generate_schedule(
    location: dict[str, Any], *, today: date | None = None, horizon_months: int = 24
) -> dict[str, Any]:
    """Calculate raw facts; notification toggles are applied later by watcher.py."""
    status = dependency_status()
    if not status["available"]:
        return build_empty_schedule(location, today=today)

    from skyfield import almanac
    from skyfield.api import load, wgs84

    start = today or date.today()
    end = horizon_end_date(start, horizon_months)
    timezone_name = location["timezone"]
    local_zone = ZoneInfo(timezone_name)
    planets = load(str(ASTRONOMY_DIR / "ephemeris" / "de440s.bsp"))
    timescale = load.timescale()
    observer = wgs84.latlon(location["latitude"], location["longitude"])
    phase_events = _calculate_lunar_phase_events(start, end, planets, timescale, almanac, local_zone)
    records = []
    current = start
    while current <= end:
        records.append(
            _calculate_daily_record(
                current, timezone_name, local_zone, planets, timescale, observer, almanac, location, phase_events
            )
        )
        current += timedelta(days=1)
    schedule = {
        "version": 2,
        "location": location,
        "location_fingerprint": _location_fingerprint(location),
        "timezone": timezone_name,
        "supported_facts": SUPPORTED_FACTS,
        "horizon_months": horizon_months,
        "generated_from": start.isoformat(),
        "generated_through": end.isoformat(),
        "generation_status": "fresh",
        "daily_records": records,
    }
    return schedule


def _calculate_daily_record(day, timezone_name, local_zone, planets, timescale, observer, almanac, location, phase_events):
    start_local = datetime.combine(day, time.min, tzinfo=local_zone)
    end_local = start_local + timedelta(days=1)
    start = timescale.from_datetime(start_local.astimezone(timezone.utc))
    end = timescale.from_datetime(end_local.astimezone(timezone.utc))

    sun_times, sun_values = almanac.find_discrete(
        start, end, almanac.sunrise_sunset(planets, observer)
    )
    sunrise = _event_on_day(sun_times, sun_values, day, local_zone, 1)
    sunset = _event_on_day(sun_times, sun_values, day, local_zone, 0)
    transit_times, _ = almanac.find_discrete(
        start, end, almanac.meridian_transits(planets, planets["Sun"], observer)
    )
    solar_noon = _closest_midday(transit_times, day, local_zone)

    twilight_times, twilight_values = almanac.find_discrete(
        start, end, almanac.dark_twilight_day(planets, observer)
    )
    twilight_end = _twilight_end(twilight_times, twilight_values, day, local_zone)

    moon_times, moon_values = almanac.find_discrete(
        start, timescale.from_datetime((end_local + timedelta(days=2)).astimezone(timezone.utc)),
        almanac.risings_and_settings(planets, planets["Moon"], observer)
    )
    moonrise = _event_on_day(moon_times, moon_values, day, local_zone, 1, as_string=True)
    moonset = _event_on_day(moon_times, moon_values, day, local_zone, 0, as_string=True)
    next_moonrise = _next_event_after(moon_times, moon_values, end_local, local_zone, 1)
    next_moonset = _next_event_after(moon_times, moon_values, end_local, local_zone, 0)
    illumination = None
    phase_degrees = None
    moon_status = None
    if sunset:
        sunset_datetime = _parse_iso_time(sunset, timezone.utc)
        sunset_time = timescale.from_datetime(sunset_datetime.astimezone(timezone.utc))
        illumination = round(float(almanac.fraction_illuminated(planets, "Moon", sunset_time)) * 100, 1)
        phase_degrees = round(float(almanac.moon_phase(planets, sunset_time).degrees), 1)
        full_moon = next(
            (item for item in phase_events if item["type"] == "Full Moon" and item["time"].startswith(day.isoformat())),
            None,
        )
        new_moon = next(
            (item for item in phase_events if item["type"] == "New Moon" and item["time"].startswith(day.isoformat())),
            None,
        )
        exact_phase = "Full Moon" if full_moon else "New Moon" if new_moon else None
        astrometric = (planets["earth"] + observer).at(sunset_time).observe(planets["Moon"]).apparent()
        altitude, _azimuth, _distance = astrometric.altaz()
        altitude_degrees = round(float(altitude.degrees), 2)
        moon_status = {
            "summary": f"{illumination:g}% illuminated",
            "illumination_percent": illumination,
            "phase_degrees": phase_degrees,
            "phase_name": moon_phase_name(phase_degrees, exact_event=exact_phase),
            "phase_trend": moon_phase_trend(phase_degrees),
            "above_horizon": altitude_degrees >= 0,
            "altitude_degrees": altitude_degrees,
            "moonrise": moonrise,
            "moonset": moonset,
        }
    day_length = None
    if sunrise and sunset:
        day_length = max(0, int(round((_parse_iso_time(sunset, timezone.utc) - _parse_iso_time(sunrise, timezone.utc)).total_seconds() / 60)))

    return {
        "date": day.isoformat(),
        "timezone": timezone_name,
        "location": location,
        "location_fingerprint": _location_fingerprint(location),
        "sunrise": {"time": sunrise} if sunrise else None,
        "sunrise_status": "available" if sunrise else "no_event_today",
        "solar_noon": {"time": solar_noon} if solar_noon else None,
        "sunset": {
            "time": sunset,
            "civil_twilight_end": twilight_end,
            "day_length_minutes": day_length,
        } if sunset else None,
        "sunset_status": "available" if sunset else "no_event_today",
        "civil_twilight_end": {"time": twilight_end} if twilight_end else None,
        "day_length_minutes": day_length,
        "moon_status_at_sunset": moon_status,
        "moonrise": moonrise,
        "moonrise_status": "available" if moonrise else "no_rise_this_local_date",
        "next_moonrise": next_moonrise,
        "moonset": moonset,
        "moonset_status": "available" if moonset else "no_set_this_local_date",
        "next_moonset": next_moonset,
        "moon_phase": phase_degrees,
        "illumination": illumination,
        "full_moon": next((item for item in phase_events if item["type"] == "Full Moon" and item["time"].startswith(day.isoformat())), None),
        "new_moon": next((item for item in phase_events if item["type"] == "New Moon" and item["time"].startswith(day.isoformat())), None),
        "next_full_moon": _next_phase_after(phase_events, end_local, "Full Moon"),
        "next_new_moon": _next_phase_after(phase_events, end_local, "New Moon"),
    }


def _calculate_lunar_phase_events(start, end, planets, timescale, almanac, local_zone):
    """Calculate exact geocentric phase instants once for the whole horizon."""
    start_time = timescale.from_datetime(datetime.combine(start, time.min, tzinfo=timezone.utc))
    end_time = timescale.from_datetime(datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc))
    times, values = almanac.find_discrete(start_time, end_time, almanac.moon_phases(planets))
    names = {0: "New Moon", 1: "First Quarter", 2: "Full Moon", 3: "Last Quarter"}
    return [
        {"type": names.get(int(value), "Moon Phase"), "time": sky_time.utc_datetime().astimezone(local_zone).isoformat()}
        for sky_time, value in zip(times, values)
        if int(value) in (0, 2)
    ]


def _event_on_day(times, values, day, local_zone, wanted, as_string=False):
    for sky_time, value in zip(times, values):
        local = sky_time.utc_datetime().astimezone(local_zone)
        if local.date() == day and int(value) == wanted:
            value = local.isoformat()
            return value if as_string else value
    return None


def _next_event_after(times, values, boundary, local_zone, wanted):
    candidates = []
    for sky_time, value in zip(times, values):
        if int(value) != wanted:
            continue
        local = sky_time.utc_datetime().astimezone(local_zone)
        if local > boundary:
            candidates.append(local)
    return min(candidates).isoformat() if candidates else None


def _next_phase_after(events, boundary, event_type):
    candidates = [
        item["time"] for item in events
        if item.get("type") == event_type
        and _parse_iso_time(str(item.get("time")), timezone.utc) > boundary
    ]
    return min(candidates) if candidates else None


def _closest_midday(times, day, local_zone):
    candidates = [t.utc_datetime().astimezone(local_zone) for t in times]
    candidates = [value for value in candidates if value.date() == day]
    if not candidates:
        return None
    return min(candidates, key=lambda value: abs(value.hour * 60 + value.minute - 720)).isoformat()


def _twilight_end(times, values, day, local_zone):
    previous = None
    for sky_time, value in zip(times, values):
        local = sky_time.utc_datetime().astimezone(local_zone)
        if local.date() == day and int(value) == 2 and previous in (3, 4):
            return local.isoformat()
        previous = int(value)
    return None


def moon_phase_name(phase_degrees: int | float, exact_event: str | None = None) -> str:
    """Return a boundary name only for its exact event day, otherwise its trend."""
    if exact_event in {"New Moon", "Full Moon"}:
        return exact_event
    return "Waxing Moon" if moon_phase_trend(phase_degrees) == "waxing" else "Waning Moon"


def moon_phase_trend(phase_degrees: int | float) -> str:
    """Return whether the illuminated fraction is increasing or decreasing."""
    phase = float(phase_degrees) % 360.0
    return "waxing" if 0 < phase < 180 else "waning"


def _parse_iso_time(value, fallback_timezone):
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=fallback_timezone)


def _location_fingerprint(location: dict[str, Any]) -> str:
    return (
        f"{float(location['latitude']):.5f},"
        f"{float(location['longitude']):.5f},"
        f"{location['timezone']}"
    )


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    return (next_month - date(year, month, 1)).days


if __name__ == "__main__":
    raise SystemExit(main())
