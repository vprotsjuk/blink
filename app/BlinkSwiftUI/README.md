# Blink SwiftUI

Native macOS GUI for Blink. The GUI is an editor/viewer over the project's local JSON contracts; it is not a notification sender.

Current scope:

- reads `agenda.json`
- reads `astronomy/astronomy_config.json`
- reads `location.json`
- reads `weather/weather_config.json`
- reads `weather/weather_cache.json`
- shows Today, Upcoming, History, Astronomy, Weather, Location, and Health tabs
- searches visible personal events across active/upcoming/history views
- creates, edits, disables/enables, completes, and deletes personal events in `agenda.json`
- supports 24-hour time entry, recurrence, applicable reminders, and one blinker start offset
- supports clean/dirty modal dismissal, scrolling lists/forms, and shared `Saved` feedback on settings forms
- edits Location through Open-Meteo city suggestions or validated custom coordinates plus an IANA timezone
- edits Weather and Astronomy settings and shows cached Weather plus today's calculated Sun/Moon summaries
- computes one global attention state from active personal events, including overdue row/tab attention
- updates a pulsing colored Dock tile and a SwiftUI menu-bar extra through AppKit
- does not send ntfy pushes; `watcher.py` remains the only production sender and hardware-blinker owner

Run from this directory:

```bash
swift run
```

If launched from another directory, set:

```bash
BLINK_DIR=/Users/vitaliiprotsiuk/Desktop/Blink swift run
```

Swift logic checks use a small runner because this Mac has Swift command-line tools without full Xcode/XCTest:

```bash
swift run BlinkSwiftUITestRunner
```

New GUI-created personal events write:

- `requires_done`
- `done`
- `done_at`
- `attention_level`

The Python watcher remains the only scheduled push sender and owns weather refresh, astronomy scheduling, remote queue reconciliation, and hardware-blinker timing.
