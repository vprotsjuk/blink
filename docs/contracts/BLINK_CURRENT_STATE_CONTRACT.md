# Blink Current State Contract

**Snapshot:** 2026-09-09  
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`

The complete technical description for ChatGPT is [`BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`](../../BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md). The immediate continuation prompt for a new Codex task is [`CODEX_NEXT_THREAD_PROMPT.md`](../../CODEX_NEXT_THREAD_PROMPT.md).

This is the current implementation contract for future agents. The older master prompt is historical requirements context. This file describes what is currently true and what must not be broken.

## 1. Non-Negotiable Architecture

```text
SwiftUI GUI -> local JSON files -> watcher.py -> ntfy -> iPhone
```

- `Blink.app` is the native macOS SwiftUI GUI. It owns the visible tab bar, settings forms, today's Astronomy summary, menu-bar extra, Dock attention, and local event state presentation.
- `watcher.py` is the only push sender and the only long-running delivery process.
- SwiftUI edits local JSON and owns GUI, lifecycle, Attention, Dock, and menu-bar state. It must never publish ntfy messages directly.
- Do not add a second sender, cloud backend, SQLite, Netlify, AI, Calendar integration, or another background runner.
- Keep personal events, transport/queue, weather, astronomy, location, and UI as independent blocks connected by explicit JSON contracts.
- Use atomic writes and preserve unknown JSON fields unless a documented migration removes a retired field.

## 2. Runtime Boundaries

| Block | Owner | Contract |
|---|---|---|
| Personal events | `app/agenda_store.py`, SwiftUI | `agenda.json`; lifecycle and recurrence |
| Event timing | `app/event_timing.py` | timezone-aware timestamps with explicit UTC offset |
| Push formatting | `app/notification_format.py` | ntfy headers plus human-readable body |
| Remote queue | `app/ntfy_schedule.py`, `watcher.py` | rolling 24-hour personal/Astronomy queue |
| Weather | `app/weather_store.py`, `watcher.py` | Open-Meteo fetch, cache, due-time direct push |
| Astronomy | `astronomy/generate_astronomy.py`, `watcher.py` | Skyfield + local DE440s schedule |
| Location | `app/location_store.py`, `app/location_geocoder.py` | canonical coordinates + IANA timezone |
| GUI | `app/BlinkSwiftUI/` | reads/writes local contracts; no sender symbols |
| Health | SwiftUI diagnostics + runtime files | status only; never exposes private ntfy topic |

Important runtime files include `agenda.json`, `location.json`, `config.json`, `watcher_state.json`, `watcher_runtime.json`, `ntfy_schedule_state.json`, `event_data/attachments/`, `event_data/drafts/`, `weather/weather_config.json`, `weather/weather_cache.json`, `weather/weather_state.json`, `astronomy/astronomy_config.json`, and `astronomy/astronomy_schedule.json`. All Blink-owned runtime data stays below the Blink project root; `event_data/` is private and ignored by Git.

## 3. Personal Event Contract

Required fields: `id`, `title`, `start`, `reminders_minutes_before`, `enabled`. `start` must contain an explicit UTC offset. Optional `description` preserves newlines and paragraphs. Optional attachment metadata records only an owner ID and count/boolean; it never stores file bytes or absolute paths.

Lifecycle:

```text
Upcoming -> Active -> Done -> History
```

- `Done` persists completion and clears Attention.
- `On/Off` changes notification eligibility only; it is never `Done`.
- A past unfinished event remains visible in History even when disabled; disabling stops attention and delivery but never erases the event.
- A past enabled unfinished personal event remains Active until `Done`. Its text/date content pulses in the GUI, and the `Today` tab label alternates between its normal text color and the highest current active priority color (red, yellow, or green) from any tab. Blink owns this tab bar because macOS `TabView.tabItem` does not reliably render a dynamic label color. This is presentation-only; lifecycle classification and outputs remain owned by `EventSnapshot` and `AttentionManager`.
- `Delete` removes the event and its queued reminders; deleted events do not enter History.
- `Edit` is available only for non-History events and preserves unrelated fields and existing lifecycle state while recalculating the view classification and future reminder schedule.
- History is frozen. A historical event cannot be edited in place; it can only be duplicated as a new event with a new ID and new attachment owner, or deleted. The source history record remains unchanged when duplicated.
- On load, a legacy/stale personal record with `done=true` and a future `start` is repaired to unfinished (`done=false`, `done_at=null`) and immediately classified into `Today`/`Upcoming`.
- Recurrence supports fixed weekly events and `days after Done`; completion creates at most one successor.
- Non-recurring events own `event_data/attachments/<event-id>`. Recurring occurrences retain unique internal IDs for queue safety and resolve attachments through one stable `series_id` folder.
- New-event drafts own `event_data/drafts/<draft-id>` while the editor is open. Files and pasted screenshots are staged before Save; Cancel/Escape removes only the Blink-created draft. Failed Save keeps the draft recoverable.
- Snooze, Quiet Hours, and Templates are retired and must not be reintroduced.
- Reminder offsets are centrally defined and unavailable offsets are removed when they no longer fit before the event.
- New events default the blinker to the last reminder row, `At time` (`blinker_minutes_before: 0`); existing events are not silently rewritten.
- Blinker starts at `event start - blinker_minutes_before` and continues until `Done`.

## 4. Push Contract

ntfy metadata belongs in headers: `Title`, `Priority`, and `Tags`. The visible body must never be raw JSON and must not contain braces, JSON keys, internal tags, or scheduling objects.

Personal pushes retain a useful title and description, with date/time and reminder context in the body. Personal titles begin with the event attention icon `🟢`, `🟡`, or `🔴`; if local attachments exist, exactly one `📎` marker is added. ntfy urgency remains independently controlled by its `Priority` header. The full multiline title/description remains local; the push uses a compact single-line title and a UTF-8 byte-safe body projection bounded by the current ntfy limits. Local paths, filenames, and file bytes are never sent. Weather identifies its block as `WEATHER` in the ntfy title/header, then shows location/date and selected weather blocks. If Astronomy is included with Weather, the body contains a plain `ASTRONOMY` section. If `Use Weather briefing time` is off, Astronomy is sent as its own briefing with the native ntfy title/header `ASTRONOMY` and a body beginning with the date; no Markdown markers are sent because the phone app displays them literally. Standalone notification titles use the same ntfy title/header styling. Astronomy rise/set labels use thin arrows after their matching icon: `☀️ ↑ Sunrise`, `☀️ ↓ Sunset`, `🌙 ↑ Moonrise`, and `🌙 ↓ Moonset`; Solar Noon remains `☀️` without a direction arrow, and `🌅` is not emitted. Group Astronomy briefings show the lunar phase with exactly one large direction arrow (`⬆️` waxing or `⬇️` waning), followed by one `<N> days until Full Moon.` or `<N> days until New Moon.` line derived from the generated Skyfield schedule; exact Full/New Moon events omit the arrow. Standalone Moonrise/Moonset titles use the thin rise/set arrow, while standalone phase-event titles use the phase icon and omit the arrow at the exact boundary. The watcher owns this presentation and must not introduce a second approximate lunar calculation. The body must not repeat an event title: Sunset starts with its next useful fact, and standalone Moonrise/Moonset/New Moon/Full Moon bodies contain the countdown only. User-entered personal title/description may be in any language; application labels are English.

Personal and Astronomy event reminders use the rolling 24-hour queue. Weather is checked at its configured local time and sent directly after a fresh fetch. When a Weather or Astronomy briefing time is saved after today's local target has already passed, the watcher records the configuration-change instant and defers that newly configured briefing to the next local day; it does not send a late catch-up immediately from the Save action. Saving before today's target still permits delivery at that target, and an ordinary missed target without a configuration change remains eligible for the existing late catch-up behavior.

## 5. Astronomy Contract

- Calculation uses Skyfield, local JPL `de440s.bsp`, configured latitude/longitude, and an IANA timezone.
- Schedule horizon is 24 months and is regenerated when location changes or the horizon is insufficient.
- Individual notifications are independent checkboxes and fire strictly at the calculated event time (`offset 0`).
- Supported groups are only `Sun` and `Moon`: sunrise, solar noon, sunset, civil twilight, moonrise, moonset, full moon, new moon, and moon status at sunset.
- Sunset plus Moon Status at Sunset is one combined event-time push when both are selected.
- Daily Astronomy Briefing is optional. `Use Weather briefing time` means it uses the Weather briefing time; otherwise its own `HH:mm` is editable.
- Full/New Moon use exact Skyfield phase instants. A daily record is named `New Moon` or `Full Moon` only when that exact event falls on the record's calendar date; all other records use only `Waxing Moon` or `Waning Moon`. `watcher.moon_notification_tail()` is the single countdown formatter for both briefing and individual lunar pushes; `watcher.moon_phase_summary_line()` renders the phase and one optional direction arrow. At an exact Full/New Moon event no arrow is shown; the precise phase instant selects the post-event target for the countdown.
- Polar/no-rise/no-set conditions are explicit no-event states, never fabricated times.
- Eclipses are intentionally absent from active UI, config, schedule, normalization, queue, and tests. Legacy Eclipse keys and legacy Astronomy advance offsets are ignored or migrated away safely.

## 6. Location, Weather, and Time

- Location is the shared source for Weather and Astronomy.
- City Search uses Open-Meteo global geocoding. Selecting a suggestion fills display name, coordinates, and IANA timezone in one operation.
- Custom Coordinates allows independent coordinate entry plus timezone selection. Invalid or inconsistent values must be rejected, not silently guessed.
- Saving a changed location invalidates Weather cache and marks Astronomy for regeneration.
- All application times use 24-hour `HH:mm`; persisted event timestamps remain timezone-aware ISO timestamps.
- Weather settings include enable/disable, briefing time, and independent content selection for temperature, humidity, wind, rain, and snow. A fresh forecast is fetched before each due weather push. The weather state keeps `briefing_config_changed_at` so a saved time that is already past today is scheduled for the next local day.

## 7. GUI and UX Contract

- Navigation: Today, Upcoming, History, Astronomy, Weather, Location, Health, Search, New Event.
- Today must not contain duplicate giant branding or duplicate New Event controls.
- Today and Upcoming show clear dates including year, color/Attention, title/description, an attachment paperclip when applicable, and actions. The content area reacts to hover and a single click opens the editor.
- History does not show meaningless On/Off for completed entries and is frozen: there is no Edit button or edit-on-click. History offers Duplicate as new event, attachment actions, and Delete.
- Event rows show a green `On` button for enabled events and a red `Off` button for disabled events. The status remains a toggle, not completion.
- Disabled rows dim their date/title/description to show that they are inactive, but their priority circle stays fully saturated. Active-row pulsing also leaves the priority circle solid and readable.
- Forms use English labels, red asterisks for required fields, stable `HH:mm` widths, consistent Cancel/Save placement, and shared save feedback: after successful save the button reads `Saved`, dims, and reactivates only after a new edit.
- Clean modal forms close on Cancel, Escape, or backdrop click. Dirty forms require an explicit choice.
- Event forms use multiline Title/Description editors, Finder multi-file selection, and screenshot paste. New-event drafts live under Blink-local `event_data/drafts/` until Save; saved files live under `event_data/attachments/`.
- Event-row context menus expose applicable actions: Edit (Today/Upcoming only), Duplicate as new event, Add Files, Paste Screenshot, Open Attachments Folder, On/Off, Done, and Delete. A pasted screenshot becomes a unique JPEG. Attachments are never sent to ntfy or committed to GitHub.
- Astronomy, Weather, and long event lists scroll inside the available window. Astronomy uses one shared two-column layout: the lower Sun/Moon summary is directly beneath its corresponding upper settings column, with matching left edges and icon alignment. It uses the generated schedule rather than a second calculation path. Thin `↑`/`↓` arrows indicate Sunrise/Sunset and Moonrise/Moonset; large `⬆️`/`⬇️` arrows appear only beside the current lunar phase to indicate waxing/waning.
- If a control is disabled because another option owns the value, the owning option must be visible beside it.

## 8. Startup and Operations

`install_launch_agent.command` installs the watcher and Blink app LaunchAgents. The watcher uses the project `.venv/bin/python`. The menu-bar item exists when `Blink.app` is running; the LaunchAgent starts it at login, and the watcher may run independently. `status_watcher.command` is the diagnostic command.

The current local app bundle is unsigned and intended for this Mac. The Mac must be awake for direct delivery and fresh weather fetches. iPhone permissions, Focus, Do Not Disturb, network, and ntfy subscription remain external conditions.

## 9. Verification Before Completion

Run from the correct directories:

```bash
cd "/Users/vitaliiprotsiuk/Desktop/Blink"
.venv/bin/python -m unittest -q
.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py
plutil -lint Blink.app/Contents/Info.plist launchd/*.plist
./status_watcher.command

cd app/BlinkSwiftUI
swift run BlinkSwiftUITestRunner
swift build -c release
```

After a release build, copy the release executable into `Blink.app/Contents/MacOS/Blink`, close Blink, and relaunch it. Verify runtime status again. Manual visual QA must cover Today, Upcoming, History, New/Edit Event, Astronomy, Weather, Location, and Health at normal and reduced window sizes.

## 10. Current Verification Snapshot

- Python: 120 tests passing.
- Swift UI/store contract runner: passing.
- Swift release build: passing.
- JSON and plist validation: passing.
- Open-Meteo international city matrix: 20/20 returned coordinates and IANA timezones.
- Astronomy schedule: 732 daily records, no active Eclipse or advance-offset keys.
- Watcher: running with a fresh heartbeat.
- Manual visual walkthrough is still required for compact window layouts, modal/backdrop behavior, search positioning, native notification rendering, and physical lamp behavior.

When a new requirement conflicts with this contract, stop and ask before changing a boundary. Update this file, `docs/HANDOFF.md`, and the relevant full report in the same change.
