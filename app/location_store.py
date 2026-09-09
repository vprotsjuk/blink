"""Canonical location helpers for Blink."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.error
import urllib.request
import time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # Keep basic location validation available before optional setup.
    TimezoneFinder = None


_TIMEZONE_FINDER = TimezoneFinder() if TimezoneFinder is not None else None


DEFAULT_LOCATION = {
    "version": 1,
    "display_name": "Sunnyvale, California, USA",
    "latitude": 37.3688,
    "longitude": -122.0363,
    "timezone": "America/Los_Angeles",
}


def default_location() -> dict[str, Any]:
    return dict(DEFAULT_LOCATION)


def load_location(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default_location()
    if not isinstance(raw, dict):
        raise ValueError("location.json must contain an object")
    return validate_location(raw)


def save_location_atomic(path: Path, location: dict[str, Any]) -> None:
    payload = validate_location(location)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def validate_location(raw: dict[str, Any]) -> dict[str, Any]:
    display_name = str(raw.get("display_name") or raw.get("name") or "").strip()
    latitude = _parse_float(raw.get("latitude"), "latitude")
    longitude = _parse_float(raw.get("longitude"), "longitude")
    timezone_name = str(raw.get("timezone", "")).strip()
    if not display_name:
        raise ValueError("display_name is required")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    expected_timezone = timezone_for_coordinates(latitude, longitude)
    if expected_timezone and not timezones_equivalent(timezone_name, expected_timezone):
        raise ValueError(
            f"timezone does not match coordinates; expected {expected_timezone}"
        )
    return {
        "version": int(raw.get("version", 1)),
        "display_name": display_name,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone_name,
    }


def build_manual_location(
    display_name: str,
    latitude: str | float,
    longitude: str | float,
    timezone_name: str,
) -> dict[str, Any]:
    return validate_location(
        {
            "version": 1,
            "display_name": display_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name,
        }
    )


def location_from_geocoder_result(result: dict[str, Any]) -> dict[str, Any]:
    parts = [
        str(result.get("name", "")).strip(),
        str(result.get("admin1", "")).strip(),
        str(result.get("country", "")).strip(),
    ]
    display_name = ", ".join(part for part in parts if part)
    return validate_location(
        {
            "version": 1,
            "display_name": display_name,
            "latitude": result.get("latitude"),
            "longitude": result.get("longitude"),
            "timezone": result.get("timezone"),
        }
    )


def search_city(
    city: str,
    country: str = "",
    *,
    opener: Any = urllib.request.urlopen,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    query = " ".join(part for part in [city.strip(), country.strip()] if part)
    if not query:
        raise ValueError("city is required")
    params = urllib.parse.urlencode(
        {
            "name": query,
            "count": 10,
            "language": "en",
            "format": "json",
        }
    )
    url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
    with opener(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results", []) if isinstance(payload, dict) else []
    normalized = []
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            normalized.append(location_from_geocoder_result(item))
        except (TypeError, ValueError, KeyError):
            continue
    return normalized


def search_city_from_url(url: str, *, opener: Any = urllib.request.urlopen, timeout: int = 10) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with opener(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(0.4 * (attempt + 1))
    else:
        raise last_error or RuntimeError("location search failed")
    results = payload.get("results", []) if isinstance(payload, dict) else []
    normalized = []
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            normalized.append(location_from_geocoder_result(item))
        except (TypeError, ValueError, KeyError):
            continue
    return normalized


def location_fingerprint(location: dict[str, Any]) -> str:
    validated = validate_location(location)
    return (
        f"{validated['latitude']:.5f},"
        f"{validated['longitude']:.5f},"
        f"{validated['timezone']}"
    )


def timezone_for_coordinates(latitude: float, longitude: float) -> str | None:
    """Return the offline IANA zone for coordinates when the bundled map knows it."""
    if _TIMEZONE_FINDER is None:
        return None
    return _TIMEZONE_FINDER.timezone_at(lat=float(latitude), lng=float(longitude))


def timezones_equivalent(actual: str, expected: str) -> bool:
    """Accept canonical aliases while rejecting a genuinely wrong local zone."""
    aliases = {
        "Europe/Kiev": "Europe/Kyiv",
        "Asia/Calcutta": "Asia/Kolkata",
    }
    return aliases.get(actual, actual) == aliases.get(expected, expected)


def apply_location_change(
    *,
    agenda: dict[str, Any],
    astronomy_schedule: dict[str, Any],
    weather_cache: dict[str, Any],
    remote_schedule_state: dict[str, Any],
    new_location: dict[str, Any],
) -> dict[str, Any]:
    validated = validate_location(new_location)
    fingerprint = location_fingerprint(validated)

    new_astronomy = json.loads(json.dumps(astronomy_schedule))
    new_astronomy["location"] = validated
    new_astronomy["location_fingerprint"] = fingerprint
    new_astronomy["timezone"] = validated["timezone"]
    new_astronomy["generation_status"] = "needs_regeneration"
    new_astronomy["daily_records"] = []

    new_weather = json.loads(json.dumps(weather_cache))
    new_weather["location"] = validated
    new_weather["location_fingerprint"] = fingerprint
    new_weather["status"] = "stale_location_changed"
    new_weather["fetched_at"] = None
    new_weather["forecast"] = None

    new_schedule_state = json.loads(json.dumps(remote_schedule_state))
    for record in new_schedule_state.get("scheduled", {}).values():
        if not isinstance(record, dict):
            continue
        if record.get("source") == "astronomy" and record.get("status") == "queued":
            record["status"] = "pending_cancel"
            record["pending_reason"] = "location_changed"

    return {
        "agenda": json.loads(json.dumps(agenda)),
        "astronomy_schedule": new_astronomy,
        "weather_cache": new_weather,
        "remote_schedule_state": new_schedule_state,
    }


def _parse_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
