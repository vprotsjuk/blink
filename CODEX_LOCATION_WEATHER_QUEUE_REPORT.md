# Blink Location / Weather / Remote Queue Report

Date: 2026-09-07
Backup before this work: `backups/blink_pre_location_weather_queue_20260907-124941.zip`

## What Changed

Implemented the next architecture layer around the existing Blink prototype:

```text
location.json
    -> astronomy/astronomy_config.json + astronomy/astronomy_schedule.json
    -> weather/weather_config.json + weather/weather_cache.json

agenda.json + astronomy events + weather briefing
    -> watcher.py
    -> ntfy immediate or ntfy scheduled delivery
    -> iPhone
```

`watcher.py` remains the single notification sender. SwiftUI still has no `ntfy`, `URLSession`, `POST`, or direct HTTP sender code.

## Canonical Location

Added `app/location_store.py` and `location.json`.

The canonical default is Sunnyvale, California, USA:

- latitude `37.3688`
- longitude `-122.0363`
- timezone `America/Los_Angeles`

Location validation requires explicit latitude, longitude, and IANA timezone. Manual coordinates without timezone are rejected. Blink does not guess timezone from longitude.

Location-change logic preserves `agenda.json`, invalidates astronomy/weather derived data, and marks future old-location astronomy scheduled notifications as `pending_cancel`.

## Astronomy v2

Reworked the astronomy generator contract:

- 24-month rolling horizon fields.
- v2 per-event notification settings: `{enabled, offsets_minutes_before}`.
- sunrise support added to supported facts/settings.
- missing moonrise/moonset is valid.
- disabled astronomy notification settings do not delete raw astronomy facts.

The generator now refuses to fake precise astronomy. On this Mac, real generation is still blocked because `skyfield`, `numpy`, and the local JPL ephemeris file are not installed/provided.

## Weather

Added `app/weather_store.py` and default files:

- `weather/weather_config.json`
- `weather/weather_cache.json`
- `weather/weather_state.json`

The weather source is Open-Meteo. The normalized cache stores high/low, humidity range, rain probability/window, snow flag, wind speed/gust, and wind warning. Morning briefing text is factual only and intentionally avoids clothing advice.

Watcher integration:

- Fetch forecast.
- Save normalized cache.
- Before the configured morning time, schedule the briefing remotely through ntfy.
- After the configured morning time, send immediately.
- Fetch failure records `unavailable` and does not mark the date delivered.

## Remote ntfy 24-Hour Queue

Added `app/ntfy_schedule.py` and watcher integration.

Blink builds desired remote notifications for the next 24 hours, then reconciles them against `ntfy_schedule_state.json`.

Rules:

- deterministic sequence IDs;
- no ntfy topic in sequence IDs;
- queued remote notification is not local delivery;
- Mac-awake direct send is skipped for a reminder already queued remotely;
- matured remote queued reminders are moved to remote `assumed_delivered` state so Watcher does not send a second direct notification immediately after the scheduled time;
- event time edits replace the same logical sequence;
- delete/disable/Done attempts to cancel future queued reminders;
- failed schedules remain `pending_schedule`.

The watcher uses ntfy scheduled delivery headers and the ntfy scheduled-delete endpoint for cancellation.

## Sleep / Wake / Watcher Lifecycle

Added `app/watcher_lifecycle.py`.

Watcher now writes `watcher_runtime.json` heartbeat data with PID and timestamp. It also detects large gaps between poll loops and logs a wake-gap event.

Added user scripts:

- `install_launch_agent.command`
- `uninstall_launch_agent.command`
- `status_watcher.command`
- `launchd/com.vitalii.blink.watcher.plist`

Live testing found an important operational issue: an old manually started `watcher.py` process can coexist with the LaunchAgent watcher and cause duplicate checks/sends. `stop_watcher.command` was used to remove the old manual PID, and `start_watcher.command` / `status_watcher.command` were updated so manual start does not create a second watcher when the LaunchAgent is loaded.

## SwiftUI

Updated SwiftUI read-side models:

- Astronomy v2 event settings decode correctly.
- Legacy astronomy boolean settings still decode.
- Location tab reads `location.json`.
- Weather tab reads weather config/cache.

SwiftUI remains a local JSON editor/viewer and does not send push notifications.

## Tests

Added/updated tests:

- `test_location_store.py`
- `test_astronomy.py`
- `test_ntfy_schedule.py`
- `test_weather_store.py`
- `test_watcher_lifecycle.py`
- `test_watcher.py`
- Swift test runner in `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

Verified during implementation:

- targeted Python tests: OK.
- Swift build + Swift test runner: OK.
- `status_watcher.command` runs and reports `stopped` when no runtime heartbeat exists.
- Live LaunchAgent start/status: OK, one watcher process.
- Live personal reminder test: ntfy returned `200`. A duplicate-risk path was observed and fixed afterward by remote `assumed_delivered` state plus script duplicate-process protection.

## External References

Used official docs:

- ntfy publish/scheduled delivery/cancellation: https://docs.ntfy.sh/publish/
- Open-Meteo forecast API: https://open-meteo.com/en/docs
- Open-Meteo geocoding API: https://open-meteo.com/en/docs/geocoding-api
- Skyfield almanac capabilities: https://rhodesmill.org/skyfield/almanac.html

## Remaining Blockers

Real astronomy data is not generated yet. Exact blocker: install/provide `skyfield`, `numpy`, and `astronomy/ephemeris/de440s.bsp`, then implement/run precise generation for the rolling 24-month horizon.

Location search/edit in SwiftUI is not implemented yet; Python has the geocoder helper and invalidation logic.

LaunchAgent scripts are present, but the LaunchAgent has not been installed in this run.

No manual iPhone sleep/wake test has been performed after these code changes.
