# Event Editor Date and Calendar Navigation Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the event editor show the saved event date clearly, restore the correct calendar date on every open, and let calendar double-click navigation work without a false dirty-editor warning.

**Architecture:** Keep event persistence and the selected-day view unchanged. Add one pure date-label helper for the editor, scope editor view identity to the event ID so SwiftUI rebuilds the calendar for a newly opened event, and suppress dirty callbacks during the editor's initial draft normalization only; genuine user edits continue to enable Save and protect navigation.

**Tech Stack:** Swift 5, SwiftUI, existing `BlinkSwiftUITestRunner` source-contract tests, macOS `Blink.app` bundle.

## Global Constraints

- Do not change the scheduler, watcher, weather, astronomy, attachment storage, or History semantics.
- Preserve the existing Save/Cancel dirty-editor safety for real user edits.
- Use the project-local Swift test runner and release build before claiming completion.

### Task 1: Add regression contracts for date display and initialization-safe navigation

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- The tests will require a public `eventEditorDateTitle(_:) -> String` helper.
- The source contract will require an initialization guard around editor dirty callbacks and event-scoped editor identity.

- [x] **Step 1: Write the failing tests**

Add a pure date-label assertion beside `testSelectedDayDateLabels`, and extend `testEventEditorLayoutContracts` with:

```swift
let eventDate = parseISODate("2026-09-22T06:59:00-07:00")!
try expect(eventEditorDateTitle(eventDate) == "September 22, 2026", "Editor should show the event's full local date")
try expect(source.contains(".id(event.id)"), "Opening another event should rebuild editor date state")
try expect(source.contains("isInitializing"), "Editor should suppress dirty callbacks during initial setup")
```

- [x] **Step 2: Run the targeted Swift runner and verify RED**

Run:

```bash
cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI
swift run BlinkSwiftUITestRunner
```

Expected: failure because `eventEditorDateTitle` and the new source contracts do not yet exist.

### Task 2: Implement explicit date display and reliable editor identity

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

**Interfaces:**
- Produce `public func eventEditorDateTitle(_ date: Date) -> String` using `blinkTimeZone` and `MMMM d, yyyy`.

- [x] **Step 1: Add the date helper**

Place the helper near the existing selected-day date formatters:

```swift
public func eventEditorDateTitle(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "MMMM d, yyyy"
    return formatter.string(from: date)
}
```

- [x] **Step 2: Render the date above the calendar**

In the editor's right column, keep `RequiredLabel("Date")`, then render:

```swift
Text(eventEditorDateTitle(draft.date))
    .font(.headline)
    .foregroundStyle(.primary)
```

The text must be driven by `$draft.date`, so a calendar selection updates it immediately and the next editor open uses the saved value reconstructed by `EditableEvent(event:)`.

- [x] **Step 3: Rebuild editor state when switching event IDs**

Apply `.id(event.id)` to the `EventEditorView` invocation inside `eventEditorOverlay`, leaving the event ID stable while an editor is open. This resets `EventCalendarView.displayedMonth` when another saved event is opened without changing persistence.

- [x] **Step 4: Run the targeted Swift runner and verify GREEN**

Run the same `swift run BlinkSwiftUITestRunner` command and confirm the new date and identity contracts pass.

### Task 3: Prevent false dirty state during initial editor setup

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

**Interfaces:**
- Add private `@State` initialization flag local to `EventEditorView`; no changes to store or scheduler APIs.

- [x] **Step 1: Add guarded dirty tracking**

Add:

```swift
@State private var isInitializing = true
```

Guard both `.onChange(of: draft)` and `.onChange(of: stagedAttachmentCount)` with `guard !isInitializing else { return }` before calling `onDirtyChange(hasUnsavedChanges)`.

- [x] **Step 2: Mark setup complete after initial normalization and preview count**

In `.onAppear`, keep `stagedAttachmentCount = stagedCount()`, then defer completion one main-queue turn so initial state propagation settles:

```swift
.onAppear {
    isInitializing = true
    stagedAttachmentCount = stagedCount()
    DispatchQueue.main.async {
        isInitializing = false
        onDirtyChange(false)
    }
}
```

The existing explicit user changes after this point continue to drive `onDirtyChange`, and Save remains disabled until an actual edit is made.

- [x] **Step 3: Run the targeted Swift runner and verify GREEN**

Run `swift run BlinkSwiftUITestRunner` and confirm all tests pass, including the selected-day navigation contracts.

### Task 4: Release verification and UI smoke test

**Files:**
- Modify: `docs/superpowers/plans/2026-09-10-event-editor-date-navigation.md` (mark completed steps and record evidence)

- [x] **Step 1: Run the full verification matrix**

```bash
cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI
swift run BlinkSwiftUITestRunner
swift build -c release
cd /Users/vitaliiprotsiuk/Desktop/Blink
.venv/bin/python -m unittest -q
python3 -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py
git diff --check
```

Expected: Swift runner passes, release build exits 0, Python tests pass, Python compilation succeeds, and `git diff --check` is clean.

- [x] **Step 2: Install and launch the release app**

Copy `app/BlinkSwiftUI/.build/arm64-apple-macosx/release/BlinkSwiftUI` to `Blink.app/Contents/MacOS/Blink`, quit any running Blink process, and relaunch the installed app from `/Users/vitaliiprotsiuk/Desktop/Blink`.

- [x] **Step 3: Manually verify the three user-visible cases**

1. Open `Фото` and `Замена колес` from Today/Upcoming: the editor date text matches the row date and the calendar outline matches it. Confirmed with `Биометрия` → `September 22, 2026` and disabled Save.
2. The saved event is reconstructed through `EditableEvent(event:)`, and `.id(event.id)` resets the calendar month/selection when another event is opened.
3. A real CUA double-click (`clickCount: 2`) on calendar day 15 closed the clean editor and opened the selected-day tab (`Sep 15`) with no dirty-editor feedback; the safety warning remains for drafts with edits beyond the transient calendar date selection.

- [x] **Step 4: Verify repository boundary**

Run `git status --short`, `git ls-files event_data`, and `git check-ignore -v event_data/attachments/*`; only intended source/tests/docs changes may remain, and no user attachments may be tracked.

Verification evidence: Swift runner passed, release build passed and was installed, Python unittest `133/133` passed, Python compilation passed, `git diff --check` passed, and `git status --short` contains only intended source/tests/docs changes plus this plan.

### Follow-up: Selected Day Exit layout and Escape parity (2026-09-10)

- [x] Add a source-contract regression test requiring a shared Selected Day exit handler for the button and `.onExitCommand`.
- [x] Move `Exit` immediately after the selected date/weekday block and keep `+ New Event` right-aligned.
- [x] Verify the Swift runner and release build after the change; update the current contract and handoff.
