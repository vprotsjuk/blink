# Blink Active/Done/Attention Implementation Report

Date: 2026-09-07
Backup before work: `backups/blink_pre_active_done_attention_20260907-115528.zip`

## A. What Changed

Added a new personal-event lifecycle layer:

```text
Upcoming -> Active -> Done -> History
```

Personal events no longer disappear from the main screen merely because their start time passed. New GUI-created personal events become Active when `start <= now` and remain visible until the user presses `Done`.

Astronomy behavior was intentionally left separate: astronomy events do not become Active, do not require Done, do not enter History, and do not drive Dock/USB attention.

## B. New Personal Event Fields

New GUI-created personal events now include:

```json
{
  "requires_done": true,
  "done": false,
  "done_at": null,
  "attention_level": "green"
}
```

`done_at` is written as a timezone-aware `America/Los_Angeles` ISO timestamp when Done is pressed.

`attention_level` accepts:

- `green`
- `yellow`
- `red`

It is separate from existing `priority`.

## C. Legacy Compatibility

Legacy events without `requires_done` keep old behavior. A past legacy event goes to History and does not become Active or create attention after upgrade.

Editing an existing legacy event through the GUI can write the new fields for that event, but there is no automatic bulk migration.

## D. Upcoming / Active / History

For personal events:

- `requires_done == true && done != true && start > now` -> Upcoming
- `requires_done == true && done != true && start <= now` -> Active
- `requires_done == true && done == true` -> History
- `requires_done` missing -> legacy start-based Upcoming/History

Active events are excluded from Today/Upcoming to avoid duplication.

Astronomy events are excluded from Active/Done/History.

## E. Highest Attention State

Blink computes one global attention state from active personal events:

```text
red > yellow > green > off
```

Disabled events, future events, done events, legacy past events, and astronomy events do not contribute.

## F. Dock Blinking

Implemented in Swift/AppKit:

- `AttentionManager` is the single source of truth for outputs.
- `DockAttentionOutput` is the first real output adapter.
- `DockAttentionOutput` sends state changes to a main-actor AppKit driver.
- The driver uses `NSApp.dockTile.contentView` and `NSApp.dockTile.display()`.
- A repeating timer redraws a bright colored tile with changing opacity/size.
- `off` restores the normal Dock tile by clearing `contentView`.

The code compiles with the local Swift 6 toolchain. The native API is available. I did not create a separate screen recording/screenshot proof of the Dock animation in this run.

## G. Window Closed vs Quit

There is an app-level attention monitor in `BlinkAppState`, not only a view-local calculation.

Closing the main window should not intentionally stop the Dock attention monitor while the app process remains alive. Quitting the app stops Dock attention because the process no longer exists.

## H. USB Lamp Preparation

Added architecture only:

- `AttentionOutput`
- `AttentionManager`
- `DockAttentionOutput`
- `RecordingAttentionOutput` for tests

Future adapter shape:

```swift
final class USBLightAttentionOutput: AttentionOutput {
    func setState(_ state: AttentionState) {
        // real hardware adapter later
    }
}
```

No fake USB/HID protocol, VID/PID, random library, or hardware assumption was added.

## I. Files Changed / Created

Changed:

- `watcher.py`
- `app/agenda_store.py`
- `test_agenda_store.py`
- `test_watcher.py`
- `README.md`
- `app/BlinkSwiftUI/README.md`
- `app/BlinkSwiftUI/Sources/BlinkSwiftUI/BlinkApp.swift`
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

Created:

- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttentionOutputs.swift`
- `CODEX_ACTIVE_DONE_ATTENTION_REPORT.md`

## J. Test Results

Baseline before implementation:

- Python tests: OK, 32 tests.
- Python compile: OK.
- Swift build + Swift runner: OK.

After implementation:

- Python tests: OK, 41 tests.
- Python compile: OK.
- Swift build: OK.
- Swift runner: OK.
- Forbidden sender search in Swift sources: no matches for `ntfy`, `URLSession`, `POST`, or `http`.

Swift runner cases now include:

- lifecycle sections and Done persistence;
- highest attention and exclusions;
- legacy past events not becoming Active;
- new GUI event Done schema and green default;
- Done/attention writes preserving unknown fields;
- edit preserving existing Done state;
- attention output state transitions.

## K. macOS Limitations / Findings

Swift 6 enforces AppKit main-actor isolation for `NSApp.dockTile`. The implementation therefore keeps general attention logic non-AppKit and forwards Dock drawing to a main-actor driver.

`NSDockTile.contentView` is available and the project builds. Continuous colored Dock pulsing is implemented through repeated `NSDockTile.display()` redraws.

Not yet verified visually with a recorded Dock capture.

## L. Still Unfinished

- GUI start/stop/status controls for watcher.
- Launch-at-login / launchd installation.
- Real five-year astronomy generation.
- Astronomy toggle editing in GUI.
- Polished packaged/signed macOS app.
- Real USB RGB lamp adapter after exact hardware model is known.
- More refined event editor UX and delete confirmation.

