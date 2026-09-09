# Active Attention UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show ongoing visual attention for overdue unfinished events, use `On`/`Off` labels, and make disabled rows visibly inactive without hiding priority.

**Architecture:** `EventSnapshot.active` remains the only lifecycle source. A UI-only pulse state in `ContentView` is passed into list presentation views with the active event IDs; rendering decides opacity without mutating events. The event data store, watcher, notification formatter, and attention outputs are intentionally untouched.

**Tech Stack:** Swift 5, SwiftUI, existing `BlinkSwiftUITestRunner`, macOS `Blink.app` bundle.

## Global Constraints

- Do not alter JSON event schema, watcher scheduling, ntfy sending, or `EventSnapshot` lifecycle classification.
- `Done` remains the only completion action; `On`/`Off` remains the enable toggle.
- Keep the colored priority dot fully visible for enabled, disabled, and pulsing rows.
- Rebuild and relaunch the installed `Blink.app` after verification.

---

## File Structure

- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`: Owns UI pulse state and renders event row/tab visual state.
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`: Keeps source-level UI contracts executable without a UI automation harness.
- `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`: Documents the interaction contract for later agents.
- `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md` and `docs/HANDOFF.md`: Capture the completed product behavior and handoff state.

### Task 1: Add failing attention UI contract test

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Consumes: Swift source at `Sources/BlinkSwiftUICore/ContentView.swift`.
- Produces: `testActiveAttentionUiContracts()`.

- [x] **Step 1: Write the failing test**

Add a test that reads `ContentView.swift` and requires all of the following source contracts:

```swift
try expect(source.contains("attentionPulseOn"), "ContentView should own a UI-only attention pulse state")
try expect(source.contains("Button(event.enabled ? \"On\" : \"Off\")"), "Event state button should use On/Off labels")
try expect(source.contains("activeEventIDs"), "Event rows should receive active event identity")
try expect(source.contains("pulseVisible"), "Event rows should receive pulse visibility")
try expect(source.contains("rowContentOpacity"), "Rows should dim disabled content separately from the priority dot")
```

- [x] **Step 2: Run test to verify it fails**

Run: `swift run BlinkSwiftUITestRunner`

Expected: `FAIL` mentioning a missing active-attention UI contract.

### Task 2: Implement UI-only active attention rendering

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

**Interfaces:**
- Consumes: `snapshot.active` and a local `Bool` pulse state.
- Produces: `TodayView`, `EventListView`, and `EventRows` inputs `activeEventIDs: Set<String>` and `pulseVisible: Bool`.

- [x] **Step 1: Add a local pulse clock**

Add `@State private var attentionPulseOn = true` to `ContentView` and a 0.7-second main-runloop timer that toggles it only when `snapshot.active` is not empty.

- [x] **Step 2: Pass active identity into all personal-event list renderers**

Build `Set(snapshot.active.map(\.id))` in `ContentView`, pass it with `attentionPulseOn` into Today, Upcoming, and History views, and use the same state to animate the `Today` tab label when there are active events. The final implementation uses an app-owned `BlinkTabBar`/`BlinkTabButton`: macOS `TabView.tabItem` ignores dynamic label color. The button alternates the label between `.primary` and the highest active priority color.

- [x] **Step 3: Render row content independently from the priority dot**

Keep `Circle().fill(color(for: event.attentionLevel))` outside the dimmed group. Put the date and title/description in a group whose opacity is `0.42` for disabled events, `0.35` during the hidden pulse phase for active enabled events, and `1` otherwise. Apply a short ease-in-out animation.

- [x] **Step 4: Change only the toggle copy**

Replace `Enabled`/`Disabled` with `On`/`Off`, preserving the existing green/red foreground colors and action closure.

- [x] **Step 5: Run test to verify it passes**

Run: `swift run BlinkSwiftUITestRunner`

Expected: all tests pass including `active attention UI contracts`.

### Task 3: Record contracts and ship a verified bundle

**Files:**
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: final UI behavior from Task 2.
- Produces: durable handoff guidance consistent with the code.

- [x] **Step 1: Update product contracts**

Document the `On`/`Off` wording, disabled row dimming with visible dot, and active event/text plus `Today` tab pulse rule. State that it is presentation-only and does not change lifecycle or output routing.

- [x] **Step 2: Run complete verification**

Run:

```bash
cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner && swift build -c release
cd /Users/vitaliiprotsiuk/Desktop/Blink && .venv/bin/python -m unittest -q && .venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py
```

Expected: Swift tests, release build, Python tests, and Python compilation all succeed.

- [x] **Step 3: Install and relaunch**

Run:

```bash
cp app/BlinkSwiftUI/.build/arm64-apple-macosx/release/BlinkSwiftUI Blink.app/Contents/MacOS/Blink
osascript -e 'tell application "Blink" to quit'
sleep 1
open /Users/vitaliiprotsiuk/Desktop/Blink/Blink.app
sleep 3
./status_watcher.command
```

Expected: Blink is running from the newly copied bundle and watcher diagnostics report a running process with a fresh heartbeat.

## Self-Review

- Spec coverage: Task 2 covers active-row pulse, `Today` pulse, On/Off naming, and disabled visual state; Task 3 covers persistence and launch requirements.
- Placeholder scan: no deferred implementation or unspecified testing step remains.
- Type consistency: the same `Set<String>` `activeEventIDs` and `Bool` `pulseVisible` are passed through all three view layers.
