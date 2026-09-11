# Resizable Event Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the event editor nearly window-height, use a tighter calendar grid, and let the user move and resize the modal without changing event persistence.

**Architecture:** Keep the existing SwiftUI overlay and draft lifecycle. Add a geometry-aware modal host with bounded drag/resize state, and keep the calendar/editor views presentation-only.

**Tech Stack:** SwiftUI, AppKit geometry, existing BlinkSwiftUICore test runner.

## Global Constraints

- Do not change event JSON, IDs, recurrence, attachments, or notification scheduling.
- Keep the editor scrollable and keep Save/Cancel reachable.
- Clamp modal movement and size so the editor remains inside the Blink window.
- The compact calendar must retain today, future-priority, past-event, and selection markers.

---

### Task 1: Add UI contract tests

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [x] **Step 1: Write failing source-contract tests** for a taller modal, compact calendar spacing, and explicit drag/resize gestures with bounded geometry.
- [x] **Step 2: Run `swift run BlinkSwiftUITestRunner`** and confirm the new contracts fail against the current implementation.

### Task 2: Implement compact, movable, resizable editor

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [x] **Step 1:** Increase the default editor height and reduce calendar cell/grid spacing while preserving markers.
- [x] **Step 2:** Add geometry-aware modal size/offset state, a draggable header, a bottom-right resize handle, and clamping helpers.
- [x] **Step 3:** Keep the editor scrollable and ensure Cancel/Save remain visible in the right column.
- [x] **Step 4:** Run the focused Swift test runner and confirm the new contracts pass.

### Task 3: Verify, document, and commit

**Files:**
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`

- [x] **Step 1:** Document the taller, movable, resizable editor and compact calendar behavior.
- [x] **Step 2:** Run Swift tests, release build, Python tests, and `git diff --check`.
- [x] **Step 3:** Review the diff for presentation-only scope, restart the local app, verify the UI, and commit.
