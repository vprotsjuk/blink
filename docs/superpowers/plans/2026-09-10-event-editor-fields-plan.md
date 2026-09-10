# Event Editor Text Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give the event editor Title and Description fields a softer card-style appearance with readable internal padding while preserving multiline editing and all existing data behavior.

**Architecture:** Keep the existing SwiftUI `EventEditorView` and `TextEditor` controls. Add one local reusable field-card modifier/view style for the two fields only; do not change models, persistence, attachment flow, or notification formatting.

**Tech Stack:** SwiftUI, AppKit, existing `BlinkSwiftUITestRunner` source-contract tests.

## Global Constraints

- Preserve multiline Title and Description input, including paragraphs.
- Do not change serialized event fields or ntfy payloads.
- Keep the current modal layout and attachment/date/reminder sections unchanged.
- Use only existing SwiftUI/AppKit dependencies.

### Task 1: Add visual contract and field-card styling

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [x] **Step 1: Write the failing source contract**

Add assertions that `EventEditorView` uses a rounded bordered field-card style and explicit content padding around both text editors.

- [x] **Step 2: Run the Swift test runner and verify the new contract fails**

Run `swift run BlinkSwiftUITestRunner` from `app/BlinkSwiftUI`. It should fail only on the new styling contract.

- [x] **Step 3: Implement the smallest UI-only change**

Add a local field-card style with a subtle secondary border, quaternary background, 10–12 point corner radius, and 10–12 point content padding. Apply it to the existing Title `ZStack` and Description `TextEditor`; keep the current min/max heights and multiline bindings.

- [x] **Step 4: Run focused and full verification**

Run `swift run BlinkSwiftUITestRunner`, `swift build -c release`, `.venv/bin/python -m unittest -q`, `python3 -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py`, and `git diff --check`. Expected: all tests pass and the release build succeeds.

- [x] **Step 5: Rebuild and restart the app for visual verification**

Copy `app/BlinkSwiftUI/.build/release/BlinkSwiftUI` to `Blink.app/Contents/MacOS/Blink`, restart `Blink.app`, and inspect the editor at normal window size. Confirm text has visible breathing room, rounded cards are balanced, and no other editor sections move unexpectedly.

- [x] **Step 6: Commit the UI-only change**

```bash
git add app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift docs/superpowers/plans/2026-09-10-event-editor-fields-plan.md
git commit -m "ui: soften event editor text fields"
```
