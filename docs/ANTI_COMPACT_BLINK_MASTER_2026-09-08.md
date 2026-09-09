# Blink Anti-Compact Master Handoff

## Goal (current)

Maintain the existing Blink architecture while simplifying Astronomy, removing Eclipses completely, and keeping the macOS UI consistent, native, predictable, and independently testable.

## Architecture contract

```text
SwiftUI GUI -> local JSON -> watcher.py -> ntfy -> iPhone
```

`watcher.py` is the only push sender and owns direct delivery, the rolling 24-hour ntfy queue, retries, deduplication, and the runtime heartbeat. SwiftUI owns UI, local JSON editing, lifecycle actions, Attention, Dock, and menu bar. Do not add a second sender, cloud backend, SQLite, Netlify, AI, Calendar integration, or another background runner.

## Lifecycle and Attention

Personal events remain `Upcoming -> Active -> Done -> History`. Attention is independent: `attention_start = event start - blinker_minutes_before`; Done clears Attention. Importance ordering is red > yellow > green > off. Snooze, Quiet Hours, and Templates remain removed.

## Astronomy final rules

Astronomy has two independent notification mechanisms:

1. Daily Astronomy Briefing: optional, one selected local time, optionally combined into the Weather briefing.
2. Individual event-time notifications: independent Sun/Moon checkboxes and exactly offset `0` at the calculated event instant. No Astronomy reminder-offset UI.

Supported individual events: Sunrise, Solar Noon, Sunset, Civil Twilight, Full Moon, New Moon, Moonrise, Moonset, and Moon Status At Sunset. If Sunset and Moon Status At Sunset are both enabled, one combined sunset push is sent. Full/New Moon use exact Skyfield phase instants. No Eclipses are supported or represented anywhere in active runtime, UI, generated JSON, or user documentation. Legacy eclipse keys are ignored/migrated away while loading remains safe.

Astronomy uses Skyfield with local JPL DE440s, timezone-aware canonical coordinates, topocentric visibility checks, explicit no-event states, moon phase/illumination, and waxing/waning labels.

## UI contract

Keep the common navigation: Today, Upcoming, History, Astronomy, Weather, Location, Search, New Event, with Health as secondary diagnostics if present. Settings-like screens use shared card/padding/typography/button conventions; personal screens use consistent list rows. Every form uses one required-field red asterisk convention, 24-hour `HH:mm`, stable field width, Cancel/Save placement, and identical dirty/clean/saved feedback. Clean modals close from Cancel, Escape, or backdrop; dirty forms do not silently discard edits.

Today shows `Today`, `Active`, and `Today's Events` without a second giant Blink heading or duplicate New Event action. History does not show a meaningless On/Off action for completed items. On/Off means notification eligibility, never Done.

Location remains the shared source for Weather and Astronomy. City Search uses Open-Meteo global geocoding and fills display name, coordinates, and IANA timezone from a selected suggestion. Custom Coordinates lets the user enter coordinates independently; timezone validation rejects inconsistent combinations. Saving a changed location invalidates Weather and Astronomy derived data.

## Push contract

ntfy metadata stays in headers (`Title`, `Priority`, `Tags`); the visible body is plain, human-readable text. Personal notifications retain Title plus description/date/reminder information. Weather begins with `WEATHER`, location, and date; Astronomy begins with `ASTRONOMY` and uses Sun/Moon icons and readable event blocks. Every Moon-related Astronomy message ends with `Moon is waxing.` or `Moon is waning.`, then the calendar-day countdown to the next Full Moon or New Moon. A single watcher formatter reads these facts from the Skyfield-generated schedule for both group and individual notifications. No raw JSON, braces, tags, calendar metadata, or internal ISO strings are user-facing.

## Status (2026-09-08)

- Fresh master prompt saved at `docs/checkpoints/2026-09-08-anti-compact/MASTER_PROMPT_SOURCE.txt`.
- Pre-change checkpoint saved under `docs/checkpoints/2026-09-08-anti-compact/`.
- Python verification: 101 tests passing.
- Swift baseline: `swift run BlinkSwiftUITestRunner` from `app/BlinkSwiftUI`, passing.
- Eclipse group removed from generator, current config, generated schedule, Swift UI, and watcher settings boundary.
- Astronomy schedule regenerated: 732 daily records; exact lunar phases retained.
- Open-Meteo geocoding matrix: 20/20 international cities returned coordinates and IANA timezones.
- Watcher runtime verification: running with a fresh heartbeat; LaunchAgent entries present.
- Release executable copied into `Blink.app/Contents/MacOS/Blink`; app bundle remains unsigned/local, as before.
- Current watcher architecture and LaunchAgents remain unchanged.

## Remaining verification

Release gate completed for Python tests, Swift test runner, Python compile, release build, direct JSON validation, 20-city geocoding, and `status_watcher.command`. Manual visual QA must still cover Today, Upcoming, History, New/Edit Event, Astronomy, Weather, Location, and Health at normal and reduced window sizes.

## Files touched in this stage

- `astronomy/generate_astronomy.py`
- `astronomy/astronomy_config.json`
- `astronomy/astronomy_schedule.json` (generated)
- `watcher.py`
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- `docs/ANTI_COMPACT_BLINK_MASTER_2026-09-08.md`

## DoD

No active Eclipse implementation or UI remains; Astronomy has only event-time individual notifications plus the optional daily/Weather briefing; legacy JSON loads safely; automated tests, build, JSON, geocoding, and runtime checks pass; the full report and README describe the actual implementation without stale blockers.
