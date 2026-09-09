# Unicode Event Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use one approved Unicode icon vocabulary for Blink's Weather and Astronomy UI and for ntfy push text.

**Architecture:** Keep icon selection in the existing domain formatters. `app/weather_store.py` owns weather-line formatting; `app/notification_format.py` owns individual event titles; `watcher.py` owns astronomy briefing composition; SwiftUI renders the equivalent native symbols for the on-screen settings and facts. No scheduling, data storage, or astronomy mathematics changes.

**Tech Stack:** Python 3 standard library, SwiftUI, ntfy text notifications.

## Global Constraints

- Pushes use standard Unicode emoji only; no generated images or remote icon URLs.
- Personal reminders begin with their green/yellow/red priority marker and have no calendar emoji.
- Weather briefing facts each begin with their own icon.
- Sun uses `🔆`, `☀️`, `🔆`, and `✨` for Sunrise, Solar Noon, Sunset, and Civil Twilight.
- Moon retains a calculated phase glyph and a waxing/waning arrow where applicable.
- Do not change stored event schemas, scheduling, or astronomy calculations.

---

### Task 1: Lock Push Formatting With Tests

**Files:**
- Modify: `test_notification_format.py`
- Modify: `test_weather_store.py`
- Modify: `test_watcher.py`

- [x] Add assertions for Sun event title icons, moon phase/trend markers, and weather fact-line icons.
- [x] The focused assertions now lock the approved Unicode vocabulary.

### Task 2: Implement Python Formatters

**Files:**
- Modify: `app/notification_format.py`
- Modify: `app/weather_store.py`
- Modify: `watcher.py`

- [x] Implement the smallest shared icon selection helpers required by the assertions.
- [x] Apply icons only to title/body presentation; preserve payload fields and tag behavior.
- [x] Re-run focused tests until green.

### Task 3: Align Blink's SwiftUI Presentation

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [x] Use the same semantic Weather and Astronomy symbols in visible UI labels.
- [x] Preserve current layout, controls, and save-state behavior.
- [x] Run the SwiftUI test runner.

### Task 4: End-to-End Verification

**Files:**
- Verify: `test_*.py`

- [x] Run all Python tests.
- [x] Restart the LaunchAgent watcher and validate status.
- [x] Quit and reopen Blink so the running app uses the new build.
