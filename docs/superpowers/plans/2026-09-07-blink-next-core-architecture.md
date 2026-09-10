# Blink Next Core Architecture Implementation Plan

> **HISTORICAL / SUPERSEDED PLAN**
>
> Do not use this document as the current product contract. It is retained for
> historical context only. Running code and the current contract/specification
> take precedence; Snooze, templates, quiet hours, and the other proposals in
> this plan are not current Blink features.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Snooze, recurring events, templates, menu bar status, quiet hours, search, better time input, and early blinker start without tangling Blink's event, notification, and UI layers.

**Architecture:** Keep `agenda.json` as the personal event source of truth and add small optional event fields with backward compatibility. Keep pure lifecycle decisions separate from UI controls and watcher side effects. SwiftUI edits JSON and computes visual attention; Python watcher sends notifications and applies notification-time policies.

**Tech Stack:** SwiftUI macOS app in `app/BlinkSwiftUI`, Python watcher/domain helpers in `app/`, JSON config files in the Blink root, local LaunchAgent for watcher.

## Compact Resume Contract

If context compacts or a new agent resumes, continue from this file first:

- Active folder: `/Users/vitaliiprotsiuk/Desktop/Blink`
- Current app bundle: `/Users/vitaliiprotsiuk/Desktop/Blink/Blink.app`
- Current plan file: `/Users/vitaliiprotsiuk/Desktop/Blink/docs/superpowers/plans/2026-09-07-blink-next-core-architecture.md`
- Previous completed plan: `/Users/vitaliiprotsiuk/Desktop/Blink/docs/superpowers/plans/2026-09-07-blink-ux-reminders-weather.md`
- Do not remove `title`; event JSON stays `title + description`.
- Do not move notification sending into SwiftUI. `watcher.py` remains the only push sender.
- Run `python3 -m unittest -v` and `swift run --package-path app/BlinkSwiftUI BlinkSwiftUITestRunner` before final claims.
- Rebuild the Dock app with `swift build --package-path app/BlinkSwiftUI -c release` and copy `.build/release/BlinkSwiftUI` to `Blink.app/Contents/MacOS/Blink`.

## Module Map

- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
  - Owns Codable data shapes, pure event lifecycle rules, JSON persistence adapters.
  - Must not import network APIs or send notifications.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
  - Owns visible controls and user actions.
  - Calls `BlinkStore` only; no direct file parsing outside store.
- `app/agenda_store.py`
  - Python-side pure event lifecycle helpers for tests and watcher-adjacent logic.
- `watcher.py`
  - Owns notification sending and due-reminder processing.
  - Reads optional event fields but does not own UI behavior.
- `app/ntfy_schedule.py`
  - Owns remote ntfy queue reconciliation.
- `templates.json`
  - Future simple template definitions; no separate database.
- `quiet_hours.json`
  - Future notification policy by source/category/priority.

## Dependency Matrix

- SwiftUI views may depend on Swift core models/store.
- Swift core models/store may depend on Foundation only.
- Python watcher may depend on `app/*` helpers.
- `app/*` helpers must not depend on SwiftUI.
- Config JSON files must not require code execution to be inspectable.
- Menu Bar, Dock, and future USB lamp must consume the same computed `AttentionState`.

## Event Contract Additions

All fields are optional for backward compatibility:

- `snoozed_until: ISO8601 | null`
  - If now is before this value, the event is hidden from Active and does not contribute to attention.
- `blinker_minutes_before: int | null`
  - If absent or `0`, attention starts at event start.
  - If present, attention starts at `start - blinker_minutes_before`.
  - Only one blinker offset can be active per event.
- `recurrence: object | null`
  - Future phase.
- `template_id: string | null`
  - Future phase.
- `category: string | null`
  - Future quiet-hours/search grouping.

## Test Matrix

- Event lifecycle: Swift runner + `test_agenda_store.py`
- Notification timing: `test_watcher.py` + `test_ntfy_schedule.py`
- UI persistence: Swift runner
- Weather/location unchanged: `test_weather_store.py`, `test_location_store.py`, Swift runner
- Full release gate: `python3 -m unittest -v`, Swift runner, release build, app launch, watcher status

---

### Phase 1: Snooze, Blinker Start, Time Input

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/agenda_store.py`
- Modify: `watcher.py`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`
- Test: `test_agenda_store.py`
- Test: `test_watcher.py`

**Interfaces:**
- Produce `BlinkEvent.snoozed_until`.
- Produce `BlinkEvent.blinker_minutes_before`.
- Produce `BlinkStore.snooze(eventID:until:)`.
- Produce `attentionStartDate(event:)`.
- Produce manual `HH:mm` event editor input.

- [x] Write failing Swift tests: snoozed active event leaves Active/Attention until `snoozed_until`.
- [x] Write failing Swift tests: `blinker_minutes_before` activates attention before event start.
- [x] Write failing Swift tests: store writes `snoozed_until` and `blinker_minutes_before`.
- [x] Write failing Python tests for `agenda_store` matching Swift lifecycle.
- [x] Write failing watcher test: snoozed event reminders are skipped until unsnoozed.
- [x] Implement optional fields and pure lifecycle helpers.
- [x] Add Active row buttons: `Done`, `10 min`, `30 min`, `1 hour`, `Tomorrow`.
- [x] Add one-choice blinker selector beside reminder offsets.
- [x] Replace separate Hour/Minute UX with validated manual `HH:mm` plus small up/down stepping.
- [x] Run Swift runner and Python targeted tests.

### Phase 2: Search

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Produce `matchesEventSearch(_ event: BlinkEvent, query: String) -> Bool`.

- [x] Add pure search matching across title, description, tags/category, date string, status.
- [x] Add search field above event lists.
- [x] Search must include Active, Upcoming, and History without changing stored data.

### Phase 3: Templates

**Files:**
- Create: `templates.json`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Produce `EventTemplate`.
- Produce `BlinkStore.loadTemplates()`.
- Produce `EditableEvent.blank(template:)`.

- [x] Add templates for Site Visit, Doctor, Critical.
- [x] Template fills title seed, importance, reminders, and blinker offset only.
- [x] User still edits date/time/title before Save.

### Phase 4: Recurring Events

**Files:**
- Modify: `app/agenda_store.py`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `test_agenda_store.py`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Produce recurrence modes `weekly_fixed` and `after_done_days`.
- Produce completion logic that appends the next event while preserving completed history.

- [x] `Every Monday 8:00` creates next calendar occurrence after Done.
- [x] `N days after Done` creates next event from actual completion timestamp.
- [x] Completed event remains immutable history except `done/done_at`.

### Phase 5: Quiet Hours

**Files:**
- Create: `quiet_hours.json`
- Modify: `watcher.py`
- Modify: `app/ntfy_schedule.py`
- Test: `test_watcher.py`
- Test: `test_ntfy_schedule.py`

**Interfaces:**
- Produce notification policy by source/category/attention level.

- [x] Personal critical bypasses quiet hours.
- [x] Personal normal/yellow respects configured allowed window.
- [x] Astronomy respects per-event setting.
- [x] Weather remains morning-only.
- [x] Remote scheduling and direct send use the same policy.

### Phase 6: Menu Bar Blink

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUI/BlinkApp.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttentionOutputs.swift`
- Possibly create: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/MenuBarController.swift`

**Interfaces:**
- Menu bar consumes `EventSnapshot` and `AttentionState`.

- [x] Add status item color/state.
- [x] Show active count and active events.
- [x] Show next upcoming event.
- [x] Add `+ New` and `Open Blink`.
- [x] Ensure Dock and menu bar use the same attention source.

### Phase 7: Verification And Release

- [x] Run `python3 -m unittest -v`.
- [x] Run `swift run --package-path app/BlinkSwiftUI BlinkSwiftUITestRunner`.
- [x] Build release Swift app.
- [x] Copy binary to `Blink.app/Contents/MacOS/Blink`.
- [x] Launch app.
- [x] Check watcher status.
- [x] Update README with new JSON contracts and user workflow.

## 2026-09-07 Notification And Deferred-Event Expansion

Scope approved by Vitalii:

- Restore a proper ntfy `Title` + `Description` notification contract while keeping the visible push concise and human-readable.
- Preserve original event time, record Snooze metadata, show the deferred time and remaining time, keep Attention blinking until `Done`, and keep `Done` available after the deferred time arrives.
- Recalculate only reminders that still fit after Snooze.
- Remove Templates from the active code path and interface.
- Add independent Astronomy event toggles and a separate astronomy briefing time; support both grouped astronomy/weather delivery and individual event-time pushes.
- Keep search results visible and prevent the result list from being displaced above the viewport.

Architecture boundaries:

- `app/agenda_store.py`: pure lifecycle, Snooze metadata, reminder eligibility, and completion transitions.
- `app/ntfy_schedule.py` and `watcher.py`: notification payload formatting and delivery only.
- `astronomy/` and `app/astronomy_store.py`: astronomy facts, configuration, and delivery schedule only.
- SwiftUI models/views: presentation and JSON editing only; no network sender.
- `AttentionOutputs.swift`: consumes the resulting Attention state and remains independent of event persistence.

Execution order:

- [x] Add failing contract tests for notification payloads and clean ntfy title/body rendering.
- [x] Implement Title + Description payload formatting and verify direct/remote parity.
- [x] Add failing lifecycle tests for Snooze metadata, retained Done action, continued Attention, and reminder pruning.
- [x] Implement deferred-event state and UI details using existing row/editor surfaces.
- [x] Add failing Astronomy configuration and delivery tests for independent event toggles and grouped briefing.
- [x] Implement Astronomy delivery without coupling it to personal event lifecycle.
- [x] Remove Templates from active SwiftUI code and configuration loading, preserving ordinary existing events.
- [x] Fix search result viewport behavior and add a regression test.
- [x] Run the mandatory Python/Swift test matrix, rebuild the app, restart runtime, and inspect watcher status.

## 2026-09-07 Unified 24-Hour Time And Save Feedback

Architecture boundaries:

- Shared Swift formatting helpers define the visible `HH:mm` contract for event dates, times, and editable time fields.
- Python weather and astronomy message builders emit the same 24-hour convention before notification delivery.
- Astronomy and Weather forms own their saved snapshots and expose Save state without coupling persistence to notification delivery.

- [x] Replace 12-hour UI labels and notification labels with `HH:mm`.
- [x] Normalize weather precipitation windows to 24-hour ranges.
- [x] Give event, Weather, and Astronomy time inputs a stable width and manual `HH:mm` entry with steppers.
- [x] Dim and disable Astronomy/Weather Save buttons after successful save; re-enable them after a change.
- [x] Run Python/Swift tests, release-build the app, relaunch Blink, and verify the Watcher heartbeat.

## 2026-09-07 Location Resolver And Coordinate Modes

Architecture boundaries:

- `app/location_store.py` remains the canonical geocoding/normalization boundary.
- `app/location_geocoder.py` is a small CLI adapter used by the UI; network access stays outside SwiftUI.
- `LocationGeocoder.swift` owns only the process/service contract and response decoding.
- SwiftUI owns the city-suggestion and Custom coordinates presentation; `BlinkStore` persists the selected canonical location and synchronizes Astronomy location metadata.

- [x] Use Open-Meteo Geocoding API for global partial-name city search and ranked suggestions.
- [x] Add city search UI with debounced suggestions and atomic selection of name, coordinates, and timezone.
- [x] Add Custom coordinates mode with editable latitude/longitude and explicit timezone selection.
- [x] Keep unresolved typed city names from being saved until a suggestion is selected.
- [x] Expose the full system IANA timezone list in the picker.
- [x] Synchronize Astronomy config and invalidate derived weather/Astronomy data after location changes.
- [x] Run Python/Swift tests, verify the live geocoder response, build release, and reinstall the app.

## 2026-09-07 Weather Save Feedback And Delivery Retry State

Architecture boundaries:

- SwiftUI Weather form owns only edit/save feedback; persistence remains in `BlinkStore`.
- `weather_store.py` owns briefing identity and delivery-state rules.
- `watcher.py` fetches a fresh forecast before each direct Weather send and does not mark failed sends as delivered.

- [x] Make Weather Save visibly change to `Saved` and become inactive after save.
- [x] Re-enable Weather Save after any later setting change.
- [x] Treat briefing identity as forecast date plus configured briefing time, so changing the time can deliver again on the same day.
- [x] Reset stale delivery markers when Weather briefing time or enabled state changes.
- [x] Rename visible `Morning` label to `Weather briefing time` while preserving the internal JSON contract.
- [x] Run the full test matrix, rebuild/reinstall Blink, and verify Watcher heartbeat.

## 2026-09-07 Human-readable ntfy transport and briefing format

- [x] Send plain UTF-8 message bodies with ntfy Title, Priority, Tags, Delay, and Sequence-ID headers.
- [x] Prevent JSON transport metadata from appearing in user-visible notifications.
- [x] Format Weather as a titled briefing with location, date, temperature, humidity, precipitation, snow, and wind sections.
- [x] Format grouped Astronomy as a titled section with sunrise, sunset, and day/night duration.
- [x] Run the full Python verification suite and inspect the generated ntfy request.
- [ ] Run the Swift verification suite and inspect a real ntfy delivery.

## 2026-09-08 Location search runtime and English system copy

- [x] Diagnose city-search failure with a real Open-Meteo request.
- [x] Remove Dock PATH dependency from the Swift-to-Python resolver bridge.
- [x] Keep resolver stderr separate from machine-readable JSON stdout.
- [x] Change system Weather, Astronomy, notification, and deferred-state copy to English.
- [x] Run Python and Swift tests, rebuild the release app, and relaunch Blink.

## 2026-09-07 Weather Delivery Diagnosis And ntfy Compatibility

Architecture boundaries:

- `watcher.py` owns ntfy transport and retry logging only; Weather formatting remains in `app/weather_store.py`.
- Weather and Astronomy remain separate schedules. A Weather briefing may include a generated Astronomy section, but an empty Astronomy schedule cannot create events.
- Unicode user titles are encoded only at the HTTP-header boundary; message bodies remain plain UTF-8 text.

- [x] Confirm the selected Weather briefing time was blocked by the stale Weather Quiet Hours window.
- [x] Replace the rejected ntfy JSON-root request with the documented topic POST format and RFC-2047-safe Unicode headers.
- [x] Add response-body logging for HTTP failures in direct, remote-scheduled, and Weather sends.
- [x] Confirm the Weather state is `delivered` for `2026-09-07|21:26`.
- [x] Clear stale Weather error text when a later delivery succeeds.
- [x] Send one real Weather briefing through the production topic; ntfy returned success.
- [x] Run the Python test suite: 100 tests passed.
- [x] Confirm Astronomy delivery is currently blocked independently: schedule has zero records, status `needs_regeneration`, and the local generator lacks Skyfield/NumPy plus `astronomy/ephemeris/de440s.bsp`.

## 2026-09-07 City Search And Astronomy Save Regression

- [x] Verify 20 international cities with population comfortably above 50,000 through the live Open-Meteo geocoder; every result returned coordinates and an IANA timezone.
- [x] Make the resolver bridge wait for process termination before consuming its bounded JSON output.
- [x] Retry transient geocoder HTTP/network failures up to three times while keeping network access outside SwiftUI.
- [x] Give Astronomy Save the same Saved/disabled/dirty feedback contract as Weather.
- [x] Rebuild and run the current Swift app, then verify the city-search and Save Astronomy contracts in the Swift runner.
- [x] Generate the precise Astronomy schedule and verify individual event-time delivery.
- [x] Verify Sunnyvale and Kyiv against independent sunrise/sunset tables, including PDT/EEST conversion.
- [x] Verify representative cities across Europe, Asia, Australia, and South Africa.
- [x] Add phase name/trend fields and phase-aware Moon push text.
- [x] Add offline coordinate/timezone mismatch validation for precise astronomy generation.

## 2026-09-07 Astronomy Layout And Semantic Icons

Architecture boundaries:

- Astronomy calculation data remains in `astronomy/` and `app/astronomy_store.py`.
- `watcher.py` formats astronomy facts into push content, including the phase icon; it does not own UI state.
- SwiftUI owns only the responsive layout and SF Symbol presentation for Weather and Astronomy.
- Weather and Astronomy delivery continue to use the same ntfy transport contract without sharing configuration state.

- [x] Reorganize Astronomy into a scrollable common settings block plus Sun and Moon panels.
- [x] Add semantic interface icons for astronomy events and weather measurements.
- [x] Add phase-aware Moon Unicode icons to individual and grouped astronomy notifications.
- [x] Ensure ordinary wind values remain visible in Weather even when below the warning threshold.
- [x] Add regression coverage for Moon phase icon mapping and push formatting.
- [ ] Release-build and visually verify the updated app after granting macOS Desktop-folder access if prompted.

## 2026-09-07 Location Search Decoder Regression

- [x] Trace the live failure through SwiftUI, the resolver process, and Open-Meteo.
- [x] Align Swift `LocationGeocoder` decoding with the canonical resolver contract (`display_name`, coordinates, timezone).
- [x] Verify the resolver against Cupertino and confirm coordinates plus IANA timezone.
- [x] Rebuild the release app and confirm the Watcher remains running.
- [x] Ignore stale city-search responses after the user continues typing.
- [x] Render suggestions inside a bounded scrolling list so they cannot overlap the editor form.
