"""Weather forecast/cache helpers for Blink."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app import location_store


def default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "weather_enabled": True,
        "morning_briefing": {"enabled": True, "time": "06:30"},
        "include": {
            "temperature": True,
            "humidity": True,
            "wind": True,
            "rain": True,
            "snow": True,
        },
        "units": {"temperature": "fahrenheit", "wind_speed": "mph", "precipitation": "inch"},
        "thresholds": {
            "rain_probability_percent": 40,
            "wind_warning_speed_mph": 15,
            "wind_gust_mph": 25,
        },
    }


def default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "status": "not_prepared",
        "last_fetch_attempt_at": None,
        "last_weather_briefing_date": None,
        "last_weather_briefing_status": None,
    }


def open_meteo_forecast_url(location: dict[str, Any]) -> str:
    params = urllib.parse.urlencode(
        {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": location["timezone"],
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "forecast_days": 2,
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "rain_sum",
                    "snowfall_sum",
                    "wind_speed_10m_max",
                    "wind_gusts_10m_max",
                ]
            ),
            "hourly": ",".join(
                [
                    "relative_humidity_2m",
                    "temperature_2m",
                    "precipitation_probability",
                    "rain",
                    "snowfall",
                ]
            ),
        }
    )
    return f"https://api.open-meteo.com/v1/forecast?{params}"


def fetch_open_meteo_forecast(
    location: dict[str, Any],
    *,
    opener: Any = urllib.request.urlopen,
    timeout: int = 10,
) -> dict[str, Any]:
    with opener(open_meteo_forecast_url(location), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_open_meteo_forecast(
    *,
    payload: dict[str, Any],
    location: dict[str, Any],
    fetched_at: datetime,
    config: dict[str, Any],
) -> dict[str, Any]:
    daily = payload.get("daily", {})
    hourly = payload.get("hourly", {})
    forecast_date = _first(daily.get("time"))
    humidity_values = [int(value) for value in hourly.get("relative_humidity_2m", []) if value is not None]
    rain_probability = int(_first(daily.get("precipitation_probability_max"), 0) or 0)
    rain_window = _precip_window(hourly, "rain", config["thresholds"]["rain_probability_percent"])
    snow_amount = float(_first(daily.get("snowfall_sum"), 0) or 0)
    snow_probability = _first(daily.get("snowfall_probability_max"))
    if snow_probability is None:
        snow_probability = rain_probability if snow_amount > 0 else 0
    wind_speed = float(_first(daily.get("wind_speed_10m_max"), 0) or 0)
    wind_gust = float(_first(daily.get("wind_gusts_10m_max"), 0) or 0)
    high_today = round(float(_first(daily.get("temperature_2m_max"), 0) or 0))
    low_tonight = _low_tonight(hourly, forecast_date, location["timezone"])
    if low_tonight is None:
        low_tonight = round(float(_first(daily.get("temperature_2m_min"), 0) or 0))

    return {
        "version": 1,
        "status": "fresh",
        "location": location_store.validate_location(location),
        "location_fingerprint": location_store.location_fingerprint(location),
        "fetched_at": fetched_at.astimezone(ZoneInfo(location["timezone"])).isoformat(),
        "forecast_date": forecast_date,
        "include": config.get("include", default_config()["include"]),
        "high_f": high_today,
        "low_f": low_tonight,
        "high_today_f": high_today,
        "low_tonight_f": low_tonight,
        "humidity_min_percent": min(humidity_values) if humidity_values else None,
        "humidity_max_percent": max(humidity_values) if humidity_values else None,
        "rain_probability_percent": rain_probability,
        "rain_amount_in": float(_first(daily.get("rain_sum"), 0) or 0),
        "rain_window": rain_window,
        "snow_expected": snow_amount > 0,
        "snow_probability_percent": int(snow_probability or 0),
        "snow_amount_in": snow_amount,
        "wind_speed_mph": round(wind_speed),
        "wind_gust_mph": round(wind_gust),
        "wind_warning": (
            wind_speed >= config["thresholds"]["wind_warning_speed_mph"]
            or wind_gust >= config["thresholds"]["wind_gust_mph"]
        ),
    }


def build_morning_briefing_message(forecast: dict[str, Any]) -> str:
    location = forecast["location"]["display_name"].split(",")[0]
    forecast_date = datetime.fromisoformat(str(forecast["forecast_date"]))
    include = forecast.get("include") or {}
    show_temperature = include.get("temperature", True)
    show_humidity = include.get("humidity", True)
    show_rain = include.get("rain", True)
    show_snow = include.get("snow", True)
    show_wind = include.get("wind", True)
    lines = [
        f"🌤️ {location}",
        f"{_MONTHS[forecast_date.month - 1]} {forecast_date.day}, {forecast_date.year}",
        "",
    ]
    if show_temperature:
        lines.extend([
            "🌡️ Temperature:",
            f"☀️ {forecast.get('high_today_f', forecast['high_f'])}°F   🌙 {forecast.get('low_tonight_f', forecast['low_f'])}°F",
        ])
    if show_humidity and forecast.get("humidity_min_percent") is not None and forecast.get("humidity_max_percent") is not None:
        lines.extend([
            "",
            "💧 Humidity:",
            f"☀️ {forecast['humidity_max_percent']}%   🌙 {forecast['humidity_min_percent']}%",
        ])
    if show_rain:
        rain = f"🌧️ Rain: probability {forecast.get('rain_probability_percent', 0)}%"
        if forecast.get("rain_window"):
            rain += f" ({forecast['rain_window']})"
        lines.append(rain)
    if show_snow:
        lines.append(f"❄️ Snow: probability {forecast.get('snow_probability_percent', 0)}%")
    if show_wind:
        lines.append(
            f"💨 Wind: {forecast['wind_speed_mph']} mph, gusts up to {forecast['wind_gust_mph']} mph"
        )
    return "\n".join(lines)


_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def morning_briefing_decision(
    *,
    config: dict[str, Any],
    state: dict[str, Any],
    forecast: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    if not config.get("weather_enabled") or not config.get("morning_briefing", {}).get("enabled"):
        return {"action": "none"}
    forecast_date = forecast["forecast_date"]
    briefing_time = str(config.get("morning_briefing", {}).get("time", "06:30"))
    briefing_key = f"{forecast_date}|{briefing_time}"
    if state.get("last_weather_briefing_key") == briefing_key:
        return {"action": "none"}
    if "last_weather_briefing_key" not in state and state.get("last_weather_briefing_date") == forecast_date:
        return {"action": "none"}
    timezone_name = forecast["location"]["timezone"]
    local_now = now.astimezone(ZoneInfo(timezone_name))
    hour, minute = [int(part) for part in config["morning_briefing"]["time"].split(":", 1)]
    delivery_time = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_now >= delivery_time:
        return {"action": "send_now"}
    # Weather is fetched and sent only when the local briefing time is due.
    # Keeping a future remote schedule would make the cache stale and obscure
    # whether the watcher actually delivered the latest forecast.
    return {"action": "none"}


def briefing_due(*, config: dict[str, Any], state: dict[str, Any], forecast_date: str, now: datetime, timezone_name: str) -> bool:
    if not config.get("weather_enabled") or not config.get("morning_briefing", {}).get("enabled"):
        return False
    briefing_time = str(config.get("morning_briefing", {}).get("time", "06:30"))
    if state.get("last_weather_briefing_key") == f"{forecast_date}|{briefing_time}":
        return False
    local_now = now.astimezone(ZoneInfo(timezone_name))
    hour, minute = [int(part) for part in briefing_time.split(":", 1)]
    due = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return local_now >= due


def retry_allowed(state: dict[str, Any], now: datetime, minimum_minutes: int = 15) -> bool:
    value = state.get("last_fetch_attempt_at")
    if not value:
        return True
    try:
        previous = datetime.fromisoformat(str(value))
    except ValueError:
        return True
    return now - previous >= timedelta(minutes=minimum_minutes)


def mark_briefing_delivered(state: dict[str, Any], forecast: dict[str, Any], method: str) -> dict[str, Any]:
    result = json.loads(json.dumps(state))
    forecast_date = str(forecast["forecast_date"])
    briefing_time = str(result.get("briefing_time", ""))
    if not briefing_time:
        briefing_time = str(forecast.get("briefing_time", "06:30"))
    result["last_weather_briefing_date"] = forecast_date
    result["last_weather_briefing_key"] = f"{forecast_date}|{briefing_time}"
    result["last_weather_briefing_status"] = method
    result["status"] = "delivered"
    result["last_error"] = None
    return result


def record_fetch_failure(state: dict[str, Any], reason: str) -> dict[str, Any]:
    result = json.loads(json.dumps(state))
    result["status"] = "unavailable"
    result["last_error"] = str(reason)
    return result


def _low_tonight(hourly: dict[str, Any], forecast_date: str | None, timezone_name: str) -> int | None:
    if not forecast_date:
        return None
    values = hourly.get("temperature_2m", [])
    times = hourly.get("time", [])
    candidates: list[float] = []
    for index, value in enumerate(values):
        if value is None or index >= len(times):
            continue
        try:
            stamp = datetime.fromisoformat(str(times[index]))
        except ValueError:
            continue
        if stamp.date().isoformat() == forecast_date and stamp.hour >= 18:
            candidates.append(float(value))
        elif stamp.date().isoformat() != forecast_date and stamp.hour <= 8 and candidates:
            candidates.append(float(value))
    return round(min(candidates)) if candidates else None


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def _first(values: Any, default: Any = None) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return default


def _precip_window(hourly: dict[str, Any], amount_key: str, probability_threshold: int) -> str | None:
    times = hourly.get("time", [])
    probabilities = hourly.get("precipitation_probability", [])
    amounts = hourly.get(amount_key, [])
    active = []
    for index, timestamp in enumerate(times):
        probability = probabilities[index] if index < len(probabilities) else 0
        amount = amounts[index] if index < len(amounts) else 0
        if (probability or 0) >= probability_threshold or (amount or 0) > 0:
            active.append(str(timestamp))
    if not active:
        return None
    return _hour_range_label(active[0], active[-1])


def _hour_label(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    return f"{parsed.hour:02d}:00"


def _hour_range_label(start: str, end: str) -> str:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    return f"{start_dt.hour:02d}:00-{end_dt.hour:02d}:00"
