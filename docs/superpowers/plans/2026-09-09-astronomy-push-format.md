# Astronomy Push Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Astronomy notifications compact, use the same visual icon language as Blink, and show a single large lunar direction arrow except at an exact New/Full Moon event.

**Architecture:** Keep Skyfield schedule generation and JSON data untouched. `watcher.py` remains the sole formatter for grouped and individual Astronomy payload bodies; `app/notification_format.py` supplies their titles. SwiftUI only mirrors the approved icon mapping in its reader UI.

**Tech Stack:** Python 3 `unittest`; Swift 6 / SwiftUI smoke runner.

## Global Constraints

- Preserve `SwiftUI GUI -> local JSON -> watcher.py -> ntfy + USB blinker`.
- Do not add a sender, scheduler, persistence layer, or new JSON fields.
- `☀️` is the only Sunrise/Sunset/Solar noon icon; `🌅` must not be emitted.
- Moon direction is `⬆️` for waxing and `⬇️` for waning, exactly once in a moon message; exact Full/New Moon events omit it.
- Preserve horizon, Moonrise, and Moonset information without duplicate lines.

---

### Task 1: Add formatter regression tests

**Files:**
- Modify: `test_notification_format.py`
- Modify: `test_watcher.py`

**Interfaces:**
- Consumes: `app.notification_format.build_event_notification`, `watcher.build_astronomy_briefing_message`, `watcher.build_evening_astronomy_description`, `watcher.build_moon_event_description`.
- Produces: failing behavioral assertions for the approved payload text.

- [ ] **Step 1: Write the failing title and moon-format tests**

```python
def test_astronomy_titles_use_sun_and_large_moon_direction_icons(self):
    self.assertEqual(title_for(["astronomy", "sunrise"]), "☀️ Sunrise")
    self.assertEqual(title_for(["astronomy", "sunset"]), "☀️ Sunset")
    self.assertEqual(title_for_moon("🌔", "waxing"), "🌔 ⬆️ Moonrise")
    self.assertEqual(title_for_exact_new_moon(), "🌑 New Moon")
```

```python
def test_grouped_and_evening_moon_lines_are_compact_and_not_duplicated(self):
    self.assertIn("🌑 ⬇️ New Moon — 1.4% illuminated", message)
    self.assertNotIn("Moon: ", message)
    self.assertNotIn("Moon is waning.", message)
    self.assertNotIn("\nSunset.\n", message)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m unittest test_notification_format test_watcher -q`

Expected: failures show the previous `🔆`, textual `Moon is waning.`, or repeated `Sunset.` output.

### Task 2: Implement compact Python presentation rules

**Files:**
- Modify: `app/notification_format.py`
- Modify: `watcher.py`
- Test: `test_notification_format.py`, `test_watcher.py`

**Interfaces:**
- Consumes: schedule-provided `phase_name`, `phase_trend`, `summary`, rise/set, and exact phase event time.
- Produces: `moon_phase_summary_line(...)` and compact title/body output without changing scheduler inputs or stored data.

- [ ] **Step 1: Implement only the tested title mapping**

```python
if "sunrise" in tags or "sunset" in tags or "solar-noon" in tags:
    return "☀️"
if phase_icon:
    return phase_icon if exact_phase else f"{phase_icon} {large_trend_arrow(trend)}"
```

- [ ] **Step 2: Implement the tested body mapping**

```python
def moon_phase_summary_line(status, reference_time=None):
    icon = moon_phase_icon(status["phase_degrees"])
    arrow = "" if is_exact_phase(status, reference_time) else f" {large_trend_arrow(trend)}"
    return f"{icon}{arrow} {status['phase_name']} — {status['summary_without_trend']}"
```

`build_sunset_description` begins with `Dark:` rather than `Sunset.`. The common moon tail returns only the next-phase countdown. Standalone Moonrise/Moonset/phase-event bodies contain no repeated event-name line.

- [ ] **Step 3: Run the focused tests and verify GREEN**

Run: `.venv/bin/python -m unittest test_notification_format test_watcher -q`

Expected: exit code 0 with all focused tests passing.

### Task 3: Mirror approved Astronomy icons in Blink UI

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Consumes: existing Astronomy UI event keys and phase/trend values.
- Produces: `☀️` for Sunrise/Solar noon/Sunset and `⬆️`/`⬇️` as the phase-direction visual in UI rows.

- [ ] **Step 1: Write a failing Swift smoke assertion**

```swift
try expect(astronomyEventIcon("sunrise") == "☀️", "Sunrise must use the shared sun icon")
try expect(moonDirectionIcon("waxing") == "⬆️", "Waxing must use the shared large up arrow")
```

- [ ] **Step 2: Run the Swift runner and verify RED**

Run: `(cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner)`

Expected: failure because the existing UI uses `🔆` and diagonal arrows.

- [ ] **Step 3: Implement the smallest UI-only mapping change**

```swift
func astronomyEventIcon(_ event: String) -> String {
    switch event {
    case "sunrise", "solar_noon", "sunset": return "☀️"
    case "civil_twilight": return "✨"
    default: return "🌙"
    }
}

func moonDirectionIcon(_ trend: String) -> String {
    trend == "waxing" ? "⬆️" : "⬇️"
}
```

- [ ] **Step 4: Run the Swift runner and verify GREEN**

Run: `(cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner)`

Expected: exit code 0 and `Swift Blink store tests passed.`

### Task 4: Document and release-verify the scoped behavior

**Files:**
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: approved message examples and verification outputs.
- Produces: matching current-state documentation.

- [ ] **Step 1: Update the notification contract**

Document the single-sun icon, compact moon phase line, conditional direction arrow, no duplicate Sunset body label, and no duplicate Moonrise/Moonset lines.

- [ ] **Step 2: Run the complete release gate**

Run:

```bash
.venv/bin/python -m unittest -q
.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py
(cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner)
(cd app/BlinkSwiftUI && swift build -c release)
plutil -lint Blink.app/Contents/Info.plist launchd/*.plist
./status_watcher.command
```

Expected: each command exits 0; then copy `app/BlinkSwiftUI/.build/release/BlinkSwiftUI` to `Blink.app/Contents/MacOS/Blink` only after confirming the release executable name.

- [ ] **Step 3: Manually inspect the app and a delivered test push**

Confirm UI symbols match the approved set and that a delivered grouped/individual message has one lunar arrow, no `🌅`, and no duplicated Sunset/Moon event text.
