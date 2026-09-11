# Event Editor Calendar Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Blink event editor compact for short text, use a two-column layout with a larger calendar/time panel, and clearly mark today, event dates, and past event dates.

**Architecture:** Keep event persistence and scheduling unchanged. Add a small pure calendar-marker helper and a local SwiftUI calendar grid that receives the existing event list, while the editor remains responsible only for draft editing and layout.

**Tech Stack:** SwiftUI, Foundation `Calendar`, existing BlinkSwiftUICore models and test runner.

## Global Constraints

- Do not change event storage, IDs, recurrence, attachments, or notification behavior.
- History remains read-only; this change is presentation-only.
- The editor must keep Save/Cancel reachable by scrolling when the window is shorter than the form.
- Today uses a blue filled square; future event dates use the highest priority color; past dates with events use a gray background.

---

### Task 1: Add calendar-marker contract tests

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [x] **Step 1: Write failing tests** for a date marker helper: today wins with `today`, a future date uses the highest enabled event priority, a past date with an event uses `pastEvent`, and an empty date is `normal`.
- [x] **Step 2: Run `swift run BlinkSwiftUITestRunner`** and confirm the new tests fail because the helper does not exist.

### Task 2: Implement calendar grid and two-column editor layout

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [x] **Step 1: Implement the pure marker helper and calendar grid** with month navigation, date selection, today detection, event-priority lookup, and gray past-event cells.
- [x] **Step 2: Pass the loaded event list into `EventEditorView`** without changing persistence APIs.
- [x] **Step 3: Replace fixed-height title/description fields** with one-line minimum heights that grow to bounded multiline heights as content wraps or contains newlines.
- [x] **Step 4:** Place title/description/attachments/settings in the left column and the larger calendar/time controls in the right column; keep the whole editor scrollable and Save disabled unless dirty/valid as before.
- [x] **Step 5:** Run the focused Swift UI test runner and confirm marker tests pass.

### Task 3: Full verification and documentation

**Files:**
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`

- [x] **Step 1:** Document the editor layout and calendar color rules.
- [x] **Step 2:** Run `swift run BlinkSwiftUITestRunner`, `swift build -c release`, `python -m unittest discover -s . -p 'test_*.py' -q`, and `git diff --check` (using the project `.venv/bin/python`).
- [x] **Step 3: Review the diff for accidental persistence/scheduling changes and commit the scoped UI update.
