# Blink UX Reminders Weather Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Blink event, reminder, weather, location, and astronomy controls coherent and safe for daily use.

**Architecture:** Keep the existing `title + description` event schema because watcher and ntfy scheduling already depend on `title`. Add shared reminder availability logic so impossible offsets are hidden/disabled in UI and ignored before delivery. Preserve local JSON files as source of truth; SwiftUI edits settings, Python watcher sends notifications.

**Tech Stack:** SwiftUI macOS app in `app/BlinkSwiftUI`, Python watcher/tests, JSON config files in the Blink root.

## Global Constraints

- Do not remove `title` from existing/new event JSON unless the notifier chain is redesigned.
- Mark required fields with a red `*` in every editor.
- Reminder offsets must be centrally defined and filtered by event lead time.
- If event time changes, selected reminder offsets that can no longer fire must be removed.
- Weather settings must preserve unknown JSON fields.
- Location changes must invalidate weather and astronomy derived data.
- SwiftUI must not send ntfy notifications or contain ntfy/POST sender code.
- Run Python and Swift test suites before declaring completion.

---

### Task 1: Event Date And Reminder Rules

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Produces: `isReminderOffsetAvailable(_:eventStart:now:) -> Bool`
- Produces: `availableReminderOffsets(_:eventStart:now:) -> [Int]`
- Produces: `EditableEvent.startDate() -> Date`
- Produces: `EditableEvent.toDictionary(now:) -> [String: Any]`

- [x] Write failing Swift tests for year labels and unavailable reminders.
- [x] Verify tests fail for missing reminder functions.
- [x] Add shared reminder availability functions.
- [x] Save only currently available reminder offsets.
- [x] Show year in event date/time labels.
- [x] Verify Swift runner passes after UI compile fixes.
- [x] Add `reminders.json` and load custom reminder presets with fallback.

### Task 2: Required Field UX

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

**Interfaces:**
- Produces: `RequiredLabel`
- Produces: `.formLabel(_:required:)`

- [x] Add red-star labels for event title/date/time/reminders.
- [x] Add red-star labels for location name/latitude/longitude/timezone.
- [x] Add red-star label for weather morning time.
- [x] Review all editor buttons for clear labels and disabled states.
- [x] Replace event sheet with modal overlay: outside click dismisses only unchanged event drafts.

### Task 3: Weather Settings

**Files:**
- Modify: `app/weather_store.py`
- Modify: `weather/weather_config.json`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `test_weather_store.py`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Produces: `WeatherConfig.Include`
- Produces: `BlinkStore.saveWeatherSettings(_:)`

- [x] Add include flags for temperature, humidity, wind, rain, snow.
- [x] Make weather briefing message respect include flags.
- [x] Add Swift store save preserving unknown fields.
- [x] Add editable weather controls in SwiftUI.
- [x] Save current `weather/weather_config.json` with include defaults.
- [x] Run Python weather tests.

### Task 4: Location And Timezone UX

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`

**Interfaces:**
- Produces: timezone picker using common IANA zones.
- Produces: manual coordinate edit remains available.

- [x] Replace free-text timezone-only UX with a picker plus editable manual values.
- [x] Keep manual latitude/longitude for desert/astronomy use.
- [x] Avoid adding network geocoding until basic picker/manual UX is stable.

### Task 5: Astronomy Start

**Files:**
- Inspect: `astronomy/generate_astronomy.py`
- Inspect: `astronomy/astronomy_config.json`
- Inspect: `astronomy/astronomy_schedule.json`

**Interfaces:**
- Existing: precise astronomy requires `skyfield`, `numpy`, and local ephemeris.

- [x] Check dependency status.
- [x] Skip precise schedule generation because dependencies are missing.
- [x] Record exact blocker: missing `skyfield`, `numpy`, and `astronomy/ephemeris/de440s.bsp`.

### Task 6: Backend Reminder Safety

**Files:**
- Modify: `watcher.py`
- Modify: `app/ntfy_schedule.py`
- Test: `test_watcher.py`
- Test: `test_ntfy_schedule.py`

**Interfaces:**
- Backend must skip reminder offsets whose reminder time is already past when planning future remote queue.
- Existing late grace behavior for due reminders must remain unchanged.

- [x] Add tests for remote queue not scheduling impossible future offsets.
- [x] Add tests that due direct sending still respects grace only.
- [x] Implement minimal backend filtering.

### Task 7: Verification And App Rebuild

**Files:**
- Build output: `Blink.app/Contents/MacOS/Blink`

- [x] Run `python3 -m unittest`.
- [x] Run `swift run --package-path app/BlinkSwiftUI BlinkSwiftUITestRunner`.
- [x] Build Swift app.
- [x] Copy fresh binary into `Blink.app`.
- [x] Open app and verify it launches.
