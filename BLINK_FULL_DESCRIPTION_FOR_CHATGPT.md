# Blink: Complete Current Specification, Architecture, Behavior, and Contracts

**Snapshot:** 2026-09-09  
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`  
**Document purpose:** one standalone current specification for the owner, ChatGPT analysis, and future Codex threads. It describes what is implemented now; it is not a wish-list.

This document is the canonical human/ChatGPT/Codex description of the current implementation, not a future product proposal. The linked contract and continuation files are shorter operational records; when they appear to differ, this complete specification and the running code are the reference to reconcile.

## 1. What Blink Is

Blink is a local macOS reminder and briefing application. It stores events and settings as local JSON, calculates weather and astronomy on the Mac, sends notifications through ntfy, and controls a physical USB blinker/lamp through the existing watcher process.

The current scope has four independent functional blocks:

1. Personal scheduled events and reminders.
2. Weather briefing and weather data refresh.
3. Astronomy calculation, briefing, and individual astronomy events.
4. Location, timezone, and coordinate configuration.

Health, menu-bar visibility, Dock attention, search, and diagnostics are supporting surfaces. They do not become alternate schedulers or alternate data stores.

## 2. Non-Negotiable Architecture

The central runtime chain is:

```text
SwiftUI GUI
    -> local JSON configuration and event files
        -> watcher.py
            -> ntfy notification service
                -> iPhone / Mac notification clients
            -> USB blinker / lamp
```

The boundaries are deliberate:

- SwiftUI is the editor and viewer. It does not send production notifications.
- `watcher.py` is the single production scheduler, sender, and blinker coordinator.
- Astronomy generation is a separate Python calculation module. It writes a schedule consumed by the watcher.
- Weather fetching is a separate store/fetch module. It writes normalized cached weather data consumed by the watcher and UI.
- ntfy is the transport and notification presentation service, not Blink's source of truth.
- JSON files are the source of truth. There is no SQLite database, cloud backend, AI memory, second sender, or second scheduler.
- The watcher and GUI may be restarted independently. They must remain behaviorally compatible through the JSON contracts.

The project intentionally keeps the blocks independent. A change to one block must be traced through its explicit dependencies, but unrelated blocks must not be mixed into the same implementation path.

## 3. Project Layout

Important files and directories:

```text
/Users/vitaliiprotsiuk/Desktop/Blink/
  watcher.py                         production scheduler/sender/blinker process
  requirements.txt                   Skyfield, NumPy, timezonefinder
  location.json                      active location and timezone
  agenda.json                         personal events
  event_data/
    attachments/                      Blink-local saved event files
    drafts/                            unsaved event attachment staging
  weather/
    weather_config.json              weather settings
    weather_cache.json               normalized latest forecast cache
  astronomy/
    astronomy_config.json            astronomy settings
    astronomy_schedule.json          generated rolling astronomy schedule
    generate_astronomy.py            astronomy calculation pipeline
    ephemeris/de440s.bsp             local JPL ephemeris data
  app/BlinkSwiftUI/
    Package.swift                    Swift package and macOS target definition
    Sources/BlinkSwiftUI/             GUI and shared Swift models
    Sources/BlinkSwiftUITestRunner/   deterministic Swift smoke runner
  app/notification_format.py         shared notification formatting helpers
  app/weather_store.py                Open-Meteo fetch/cache/format helpers
  app/location_store.py               location persistence/search helpers
  app/location_geocoder.py            geocoder CLI bridge
  install_launch_agent.command        installs and starts launchd jobs
  status_watcher.command              runtime status/heartbeat report
  docs/contracts/                    current invariants and contracts
  docs/HANDOFF.md                    current implementation handoff
```

## 4. Dependencies and External Services

### Python

- Python 3 with the project virtual environment `.venv`.
- `skyfield>=1.49` for solar/lunar ephemeris calculations.
- `numpy>=2.0` used by the calculation stack.
- `timezonefinder>=8.0` for coordinate/timezone consistency checks.

### Swift

- Swift Package Manager.
- Swift tools version 6.
- macOS 14 deployment target.
- Executables: `BlinkSwiftUI` and `BlinkSwiftUITestRunner`.
- Shared SwiftUI model/core target keeps UI tests independent of the application process.

### Network services

- Open-Meteo geocoding for city suggestions and selected city coordinates/timezone.
- Open-Meteo forecast for weather data.
- ntfy for push delivery.
- Local JPL `de440s.bsp` for astronomy. Astronomy does not depend on a live astronomy API during normal generation.

Network is required for city search and weather refresh. The astronomy schedule is calculated locally once the ephemeris is available.

## 5. Persistent Data Contracts

### Location

`location.json` contains:

- `display_name`
- `latitude`
- `longitude`
- `timezone` as an IANA zone, for example `America/Los_Angeles`
- `coordinate_source`: `city` or `custom`
- `version`

In city mode, selecting an Open-Meteo suggestion fills the display name, coordinates, and timezone together. In custom mode, the user enters coordinates and selects a timezone. Custom coordinates intentionally override the selected city's coordinates; the selected timezone remains explicit and is validated for plausibility. Coordinates and timezone must be treated as one astronomy input tuple.

### Personal events

Personal events contain an id, title, optional multiline description, local start datetime with explicit timezone offset, enabled state, importance, reminder offsets, optional blinker offset, tags, repeat information, and optional local-attachment metadata. Attachment metadata contains no absolute paths or file bytes. The full title and description are stored locally, including paragraph breaks.

The user-facing editor requires:

- Title.
- Date.
- Time in 24-hour `HH:mm` form.
- Reminders, with at least one applicable reminder.

Description is optional and may be written in any language. Title and Description use multiline editors. System labels and all non-user-entered UI are English. New events stage selected files and pasted screenshots in a temporary Blink-local draft folder before Save.

### Event attachments

Blink keeps attachment bytes in `event_data/attachments/` under the project root. Non-recurring events use their event ID as the folder owner. Recurring occurrences retain unique internal IDs for scheduling safety and share one attachment folder through their stable `series_id`. A saved event shows a paperclip and can open its folder from the Mac; files are never sent through ntfy or committed to the public repository. A Finder multi-select adds files to the draft. When the macOS pasteboard contains file URLs (for example, a copied PDF or Excel file), the context menu and editor show `Paste Attachment` and copy those regular files into Blink; when file URLs are present, `Paste Screenshot` is hidden. If the pasteboard contains image data without file URLs, `Paste Screenshot` converts the first image to a unique JPEG. Cancel/Escape discards the current draft folder; a failed Save retains it for recovery. Deleting an event with attachments confirms and moves the Blink-owned folder to Trash.

## 5A. Complete attachment interaction specification

This section is the definitive behavior for files, screenshots, clipboard actions, Finder folders, previews, and event context menus.

### Attachment ownership and paths

All runtime data stays inside the Blink project root:

```text
/Users/vitaliiprotsiuk/Desktop/Blink/
  event_data/
    attachments/<owner-id>/   saved files for an event or recurring series
    drafts/<draft-id>/        temporary files while an editor is open
```

The event record stores only attachment metadata (`owner_id`, `count`, `has_files`). It never stores absolute paths or file bytes. The filesystem is canonical for the bytes; `agenda.json` is canonical for event metadata. There is currently no SQL database. Search derives attachment names from the owner folder, so adding a file in Finder does not require a second database or a second watcher.

Owner rules:

- A normal event owns a folder named by its event ID.
- A recurring event occurrence keeps its own internal event ID for scheduling safety, but occurrences in one series share the stable `series_id` folder.
- `Duplicate as new event` always creates a new event ID and a new attachment owner. The source History record is not changed and files are not silently shared.
- Active and Upcoming events can always create/open an empty owner folder. History can reveal a folder only when it already exists; opening History never creates a new folder.

### New event and edit draft lifecycle

Opening the New Event editor or editing an existing writable event creates a Blink-local temporary draft ID/folder immediately. This allows the user to attach files before pressing Save.

While the editor is open:

1. `Attach Files` opens an `NSOpenPanel` with multiple file selection enabled and directories disabled.
2. `Paste Attachment` copies regular file URLs from the macOS pasteboard into the draft.
3. `Paste Screenshot` converts the first decodable clipboard image to a unique timestamped JPEG in the draft.
4. The attachment list shows both already-saved files and staged draft files. Images use thumbnails; PDF, Excel, and other files use a generic document icon plus filename and size.
5. A staged file has a `Remove` action. Removing it affects only the draft.
6. `Save` finalizes staged files into the permanent owner folder, writes the manifest into `agenda.json`, and removes the draft folder after the metadata save succeeds.
7. `Cancel` or `Escape` discards only the draft folder. Existing saved files are untouched.
8. If finalization or metadata saving fails, the draft is retained so the operation can be retried without losing staged files.

Editing an existing event preserves its event ID and owner folder. It can add or remove staged files without changing the event's identity. History records are frozen and cannot be opened in this editor.

### Clipboard decision matrix

Blink examines the current pasteboard only when building the editor controls or an event-row context menu. The actions are deliberately type-specific:

| Clipboard contents | Available action | Result |
|---|---|---|
| One or more regular file URLs copied in Finder, including PDF, Excel, image, DWG, or another file | `Paste Attachment` | Copies all regular files into the event/draft folder using unique names. |
| Image data (TIFF/PNG/JPEG/HEIC) with no file URLs, including a screenshot or copied photo | `Paste Screenshot` | Converts the first image to a timestamped JPEG and stages/copies it. |
| File URLs and image representations at the same time | `Paste Attachment` only | File URLs take precedence; `Paste Screenshot` is hidden. |
| Plain text, emoji, or a text-only selection | No attachment action | In a focused `Title`/`Description` editor, normal macOS `⌘V` inserts the text. It does not create a file. |
| PDF/Excel text or page content copied from Preview/Office rather than the file itself | Usually no file action | Use `Attach Files`, or copy the actual file from Finder. If the source provides image data, only the screenshot action may be available. |
| AutoCAD object/geometry | No special import | Blink does not parse AutoCAD clipboard objects. Save/export the object as a file or image, then use `Attach Files` or `Paste Attachment`. |
| A directory or copied folder contents | No `Paste Attachment` | Directories are rejected; use `Attach Files` to choose individual files. Blink never recursively imports a folder tree or hidden/service files. |
| Unsupported/empty clipboard | No paste action | The context menu exposes only actions that are currently possible. |

`⌘V` itself is not a global “attach” command. It is native text insertion when a text editor has focus. In an event row or its context menu, `⌘V` has no custom effect; use the visible `Paste Attachment` or `Paste Screenshot` action.

### Finder workflow and direct folder changes

For a saved Active or Upcoming event, `Open Attachments Folder` always opens (and creates if necessary) the event's owner folder in Finder. The user may place files there manually. A `Save` press in Blink is not required for this direct Finder workflow.

Blink's GUI performs its normal event reload on appearance and approximately every 30 seconds. During that reload it scans each owner folder and reconciles `count`/`has_files` in `agenda.json`. Consequently:

- a newly added Finder file eventually makes the row show `📎`;
- the editor's preview list is refreshed reliably when the editor is reopened (the open editor is not a live Finder watcher);
- filename/extension search sees the file after the same reload;
- no watcher restart or SQL synchronization is required.

The current Upcoming records have their owner folders provisioned. Future editable events receive an empty folder on demand through the same action.

### Drag-and-drop policy

Dragging a file or a group of files onto an event row currently does nothing. It is intentionally not a second attachment pipeline. The supported, predictable paths are `Attach Files`, `Paste Attachment`, `Paste Screenshot`, and direct Finder placement into `Open Attachments Folder`. Any future drag-and-drop feature must reuse the existing draft/storage path, accept regular files only, reject directories, and remain disabled for frozen History.

### Context menus by tab

The context menu is dynamic and never offers an action that cannot work with the current event state or pasteboard.

**Today and Upcoming (writable rows):**

- `Edit` — opens the multiline event editor; clicking the row content does the same.
- `Add Files` — Finder multi-select; copies selected regular files.
- `Paste Attachment` — shown for regular file URLs in the clipboard.
- `Paste Screenshot` — shown for image-only clipboard data when no file URLs are present.
- `Open Attachments Folder` — always available, including for an empty folder.
- `Duplicate as new event` — creates a new ID/folder.
- `Done` (Today where applicable).
- `Turn On`/`Turn Off`.
- `Delete`.

**History (frozen rows):**

- `Duplicate as new event`.
- `Open Attachments Folder` only when an existing folder with attachments is present.
- `Delete`.

History has no `Edit`, `Add Files`, paste actions, `Done`, or On/Off. The source event remains immutable; duplication is the only way to reuse it.

### Preview and visibility rules

- Image files are decoded only for a small visual thumbnail; Blink does not OCR or inspect their contents.
- PDF, Excel, DWG, text, and other non-image files show a generic type icon, filename, and byte size.
- Hidden files and nested directories are omitted from the preview list and manifest count.
- The push contains only one `📎` marker when an event has local attachments. It never contains local paths, filenames, or file bytes.
- Deleting an event with attachments asks for confirmation and moves the Blink-owned folder to macOS Trash. A shared recurring-series folder is moved only when no remaining event uses it.

### Search behavior

The toolbar search covers title, multiline description, date, status, and visible attachment filenames/extensions. It does not search inside PDF, Excel, image, DWG, or text-file contents. It scans local owner folders during the existing filtered-view pass. JSON plus folders remain the source of truth; a future SQLite database, if ever justified by scale, may only be a rebuildable derived index and must not become a second canonical store.

### Weather

`weather/weather_config.json` stores whether pushes are enabled, one 24-hour briefing time, selected output fields, units, and thresholds. Current selectable output groups are:

- Temperature.
- Humidity.
- Wind.
- Rain.
- Snow.

### Astronomy

`astronomy/astronomy_config.json` is version 2. It stores briefing settings, whether the briefing follows the weather time, day/night duration inclusion, and independent Sun/Moon event selections. Only the supported Sun and Moon event groups are persisted. Eclipse settings are not part of the current UI contract.

`astronomy/astronomy_schedule.json` contains a rolling 24-month schedule. Each daily record includes the local date, solar times, day/night lengths, lunar phase and illumination, lunar rise/set, moon status at sunset, and next new/full moon information.

## 6. Event Lifecycle

The same event object can be viewed in different tabs based on its state. Tabs are views, not separate copies of an event.

- **Today:** enabled unfinished events relevant to the current local date, including overdue events that remain unfinished.
- **Upcoming:** enabled unfinished events after the current day/time horizon.
- **History:** completed events and intentionally disabled/retired event records that must remain inspectable.
- A historical event is frozen and cannot be edited. `Duplicate as new event` creates a new ID and new folder; the source remains in History unchanged.

### Event actions

- `Done`: marks the event completed, stops its blinker, removes it from active attention, and preserves it in History.
- `On` / `Off`: controls whether future reminders are active. `Off` is not a replacement for `Done`. Disabling a due or completed-looking item must not delete it or remove its history record.
- `Edit`: edits the same non-History event record. Saving a changed date/time recalculates its view classification and future reminder schedule.
- `Duplicate as new event`: creates a fresh unfinished event with a new ID and new attachment owner from a History record without modifying the source.
- `Delete`: removes the event record intentionally. This is the destructive action and is separate from Off.
- `Snooze`: moves the active event's effective due time forward while preserving the original scheduled time and the snooze history. The event remains active, continues blinking, and retains Done.

Today shows `Done`, a folder button, `On/Off`, `Edit`, attachment actions, and `Delete`. Upcoming shows a folder button, `On/Off`, `Edit`, attachment actions, and `Delete`. History shows `Duplicate as new event`, a folder button only when attachments exist, and `Delete`; it never shows Edit or edit-on-click. In Today/Upcoming, the row content opens the editor by double-click, not single-click. The UI must not hide Done merely because an event has become overdue or has been snoozed.

## 7. Attention, Colors, and Blinker

Importance has three levels:

- Normal: green.
- Important: yellow.
- Critical: red.

The priority dot remains saturated even when an event is Off. The rest of an Off row is dimmed/gray. The On/Off control is green for On and red for Off.

### Blinker rules

- An event can have one blinker start offset at most.
- The blinker checkbox is attached to each reminder row.
- Selecting a different blinker row clears the previous selection.
- New events default the blinker to the final reminder row, normally `At time`.
- If a blinker offset is selected, the lamp starts at that offset and continues until Done.
- If no blinker offset is explicitly selected, the lamp starts when the event becomes due.
- Snooze does not stop the blinker. Only Done stops the active attention state.
- Reminder offsets that no longer fit before the effective event time are not active/schedulable. For example, after a one-hour snooze, a two-hour reminder is discarded for the current occurrence while 30-minute, 10-minute, and 5-minute reminders can remain.

### In-app attention

- An enabled overdue unfinished event has a pulsing row/text state.
- The `Today` tab label pulses between its normal appearance and the highest priority color among open attention events, even when another tab is selected.
- Menu-bar and Dock attention use the same global attention state but remain independent UI surfaces.
- The menu-bar item is available while `Blink.app` is running. It is not created solely because an event exists. The Blink LaunchAgent starts the application at login.

## 8. Reminder Timing

The shared reminder preset list is defined centrally so that future changes to available ranges do not require editing each screen separately. The current presets are:

```text
1 day, 12 hours, 5 hours, 60 minutes, 30 minutes,
10 minutes, 5 minutes, and at time
```

The UI filters presets against the effective event start. The watcher schedules only reminders with valid due timestamps. Duplicate sends are prevented using the event identity, occurrence, and reminder offset.

Time input is 24-hour `HH:mm` everywhere. Users may type a valid time directly or use the stepper arrows. Inputs have stable width so `00:00` through `23:59` always fit. Date selection explicitly preserves/loads the selected year.

## 9. Notification Transport and Formatting

The production sender is `watcher.py` through the shared `app/notification_format.py` helpers. The ntfy request uses headers such as:

- `Title` for the short notification title.
- `Priority`.
- `Tags`.
- `Content-Type`.
- `Delay` where appropriate.
- An internal sequence/id header for deduplication and diagnostics.

Raw JSON is metadata/internal transport data only. It must never be the user-facing notification body.

Unicode emoji are used as the portable colored visual language because ntfy/iOS cannot receive Blink's native macOS colored UI circles as a native widget. The same semantic color is shown in the app row and in the personal notification title.

### Personal event push

The title starts with the priority icon and user title:

```text
🔴 Client visit
```

The body contains clean English system lines while preserving the user-entered title/description language. Multiline local text is projected into the ntfy title/body within the service's current UTF-8 limits; truncation affects only the push, not the saved event:

```text
September 14, 2026 at 15:00
Do not forget the tape measure
10 min before start
```

The calendar icon and internal tags are not put into the body. The title/description content is not converted or translated.

If the event has local attachments, one `📎` marker is added to the personal push. The push never includes local paths, filenames, or file bytes.

### Weather push

The ntfy title/header identifies the block as `WEATHER`. The body begins with the weather-state icon and location/date, then only the selected metrics. Example:

```text
🌤️ Sunnyvale
September 8, 2026

🌡️ Temperature:
☀️ 90°F   🌙 66°F

💧 Humidity:
☀️ 73%   🌙 16%
🌧️ Rain: probability 1%
❄️ Snow: probability 0%
💨 Wind: 7 mph, gusts up to 14 mph
```

The visible app weather summary uses the same icons and metric order. Before each weather push, the watcher attempts a fresh Open-Meteo forecast fetch, normalizes the result, and then sends. A failed refresh does not silently pretend that the old data is current; the watcher records the failure and retries according to its bounded retry behavior. Saving a briefing time after today's local target records the change and defers the newly configured briefing until the next local day, preventing the Save action from causing an immediate late push. A save before today's target still delivers at the configured target, while an ordinary missed target remains eligible for late catch-up.

### Astronomy briefing push

The body contains the selected Sun and Moon information, solar day/night duration, location/date context, and the same icons used in the app. If `Include with weather briefing` / `Use Weather briefing time` is enabled, the Astronomy section is appended to the Weather briefing rather than sent as a second briefing at another time; the section label is plain `ASTRONOMY` because the phone app displays Markdown markers literally. If the option is disabled, the watcher sends a separate briefing with the native ntfy title/header `ASTRONOMY` and a body beginning with the date. Standalone personal and Astronomy event titles use ntfy's title/header styling as well.

### Individual astronomy push

Individual Sun and Moon events are sent strictly at the calculated event time with offset zero. They are independent toggles, for example separate `Sunset`, `Sunrise`, `Moonrise`, and `Moonset` switches. Rise/set notifications use thin arrows after the matching icon: `☀️ ↑ Sunrise`, `☀️ ↓ Sunset`, `🌙 ↑ Moonrise`, and `🌙 ↓ Moonset`; Solar Noon remains `☀️` without a direction arrow. The retired `🌅` icon is never emitted. Group Astronomy briefings show the lunar phase with one large phase-direction arrow (`⬆️` waxing or `⬇️` waning), followed by one distance-to-the-next-relevant-phase line. Standalone Moonrise/Moonset titles prioritize the thin rise/set arrow; standalone New/Full Moon titles use the phase icon and omit the direction arrow at the exact boundary:

```text
🌒 ⬆️ Waxing Moon — 75% illuminated
4 days until Full Moon.
```

The number and target are computed from the generated schedule. The rule applies both to individual Moon pushes and to a group Astronomy briefing whenever Moon information is present. The message does not repeat its title in its body: a Sunset body begins with its next useful detail, and standalone Moonrise/Moonset/New Moon/Full Moon bodies contain only the countdown. The combined Sunset + Moon Status message retains horizon, Moonrise, and Moonset facts once each. In the GUI, thin `↑`/`↓` arrows mark event rise/set; the larger `⬆️`/`⬇️` arrows are reserved exclusively for lunar waxing/waning.

If Sunset and Moon Status At Sunset are both enabled and occur at the same calculated instant, the watcher may combine their content into one event-specific push while preserving both semantic sections. This is not a second scheduler.

## 10. Weather Block

### Data source and normalization

`app/weather_store.py` calls Open-Meteo with the active coordinates and IANA timezone. It obtains daily high/low, precipitation probability, rain/snow values, wind and gust values, and hourly humidity/temperature/precipitation inputs. It writes a normalized cache with a location fingerprint and fetch timestamp.

### UI

The `Weather` tab is scrollable and contains:

- `🌤️ Weather` heading.
- `Weather pushes` on/off toggle.
- Required `Weather briefing time` in 24-hour form.
- Checkboxes for Temperature, Humidity, Wind, Rain, and Snow, each with the same color emoji used in the summary/push.
- `Save Weather`.
- Saved feedback: after a successful save, the button changes to `Saved` and is dimmed/disabled until a setting changes again.
- The latest cached daily summary with date, selected metrics, icons, and update time.

Weather push timing is not limited to morning. The UI uses the neutral `Weather briefing time` label and accepts evening times. The weather state persists `briefing_config_changed_at` to distinguish a newly saved, already-past target from a watcher that simply missed a target.

## 11. Astronomy Block

### Calculation model

`astronomy/generate_astronomy.py` uses:

- Skyfield.
- Local JPL `de440s.bsp`.
- NumPy.
- IANA timezone conversion.
- Topocentric observer coordinates for local visibility.

The generator creates a rolling 24-month schedule. Solar events include civil twilight end, solar noon, sunrise, and sunset. Lunar data includes exact/new-full phase timing, illumination, waxing/waning trend, moonrise, moonset, and status at sunset. If an event does not occur at a location/date, the schedule records an explicit no-event state instead of inventing a time.

The calculation is only correct when latitude, longitude, and IANA timezone are a coherent tuple. City selection supplies all three together. Custom coordinates require an explicit timezone selection; a deliberately incorrect timezone produces deliberately shifted local times and must be treated as invalid input, not silently corrected. The UI/runtime validate known mismatches where possible and show the selected timezone as part of the location state.

### Astronomy UI

The `Astronomy` tab is scrollable and follows the Weather visual language: same typography, row density, icon scale, spacing, and Save feedback.

Top settings include:

- `✨ Astronomy` heading.
- Current timezone and schedule status/horizon.
- `Daily Astronomy Briefing` toggle.
- Briefing time in 24-hour form.
- `Use Weather briefing time`, which disables the separate Astronomy time when selected.
- `Include day/night duration`.
- Two-column logical layout: Sun on the left and Moon on the right.
- Independent Sun event checkboxes: Civil Twilight, Solar Noon, Sunrise, Sunset.
- Independent Moon event checkboxes: Full Moon, Moon Status At Sunset, Moonrise, Moonset, New Moon.
- `Save Astronomy` with the same `Saved` disabled feedback as Weather.

The lower part shows today's calculated summary in the same shared Sun/Moon columns as the upper settings: each lower block sits directly under its corresponding upper block, with matching left edges and icon alignment. It includes date, solar times, day/night lengths, lunar phase, illumination, trend, rise/set, and next new/full moon with date and days remaining. The summary is a reader of the generated schedule; changing the UI does not implement a second astronomy calculation.

## 12. Location and Timezone Block

The `Location` tab shows the active display name, coordinates, timezone, and `Edit`.

The editor has two mutually exclusive modes:

### City search

- User starts typing a city.
- The query is debounced by 350 ms.
- Open-Meteo geocoding returns suggestions from a broad global city database.
- Each suggestion shows city/region/country, coordinates, and timezone.
- Selecting a suggestion is required; merely typing text is not enough.
- Selection fills display name, latitude, longitude, and timezone as one atomic location candidate.

### Custom coordinates

- User enters latitude and longitude manually.
- User selects an IANA timezone.
- The custom tuple becomes the source for astronomy and weather.
- The city-derived coordinates are inactive while custom mode is selected.

`Save` is disabled until the candidate is valid. A successful location save persists the tuple, invalidates/rekeys weather cache, requests astronomy regeneration, and causes dependent views to refresh. The location editor closes by Save/Cancel or by clicking outside the modal when the form is clean; dirty changes are guarded.

## 13. GUI Tabs and Controls

### Today

Shows active events for today, including overdue unfinished items. The header places one compact round blue `+` button immediately to the left of `Today` for creating a new event. Each row displays date/time, saturated priority dot, title, description, `📎` when attachments exist, a compact scrollable attachment filename/type column when files exist, a folder button, `Done`, `On/Off`, `Edit`, and `Delete`. The content area opens Edit on double-click and reacts to hover. Overdue rows and the Today tab may pulse according to attention rules.

### Upcoming

Shows future enabled events sorted by effective time. Each row displays full date including year, time, priority dot, title, description, `📎` when attachments exist, a compact scrollable attachment filename/type column when files exist, a folder button, `On/Off`, `Edit`, and `Delete`. The content area opens Edit on double-click.

### History

Shows completed, disabled-retained, and past event records with full dates including year. History rows are immutable and expose `Duplicate as new event`, attachment actions, and Delete; they do not expose Edit or edit-on-click. The duplicate appears in Today/Upcoming according to its new date and time.

### Astronomy

See the full Astronomy section above. It has independent event toggles, shared briefing coordination with Weather, today's calculated Sun/Moon summary, scroll support, and Save feedback.

### Weather

See the full Weather section above. It has independent data-field toggles, a shared 24-hour briefing time, fresh-before-send behavior, cached display, and Save feedback.

### Location

See the Location section above. It owns the active city/custom coordinate/timezone tuple and is the dependency root for weather/astronomy recalculation.

### Health

Health is a diagnostics surface. It should report watcher heartbeat, launch/runtime state, configuration validity, schedule freshness, and relevant errors without becoming a second control plane.

### Search

The toolbar search field searches user-visible event title, description, and local attachment filenames/extensions across Active/Today, Upcoming, and History. It does not inspect file contents. Results remain visible in the content viewport; search must not scroll the first match underneath the toolbar or into an invisible top region. Clearing the query restores the current tab view.

All navigation tabs use Blink-owned buttons with a subtle pointer-hover background before selection. This keeps hover feedback consistent across Today, Upcoming, History, Astronomy, Weather, Location, and Health without changing navigation state or data ownership.

### New Event

Opens the event editor with the default final-row blinker selection. The modal supports date picking, direct 24-hour time entry, stepper arrows, importance, enabled state, recurrence, reminders, multiline Title/Description, Finder multi-file selection, file-URL paste, screenshot paste, and a folder button beside the attachment count. It creates a temporary draft ID/folder before Save. Clicking outside a clean modal closes it. A dirty form requires the user to choose whether to discard, so accidental outside clicks do not erase edits.

### Event context menu

Today and Upcoming rows support hover, content-click editing, and a context menu with Edit, Add Files, Paste Attachment or Paste Screenshot (whichever the current pasteboard supports), Open Attachments Folder, Duplicate as new event, On/Off, Done, and Delete as applicable. `Open Attachments Folder` is always available for these editable rows and creates an empty owner folder on demand. `Paste Attachment` appears for regular file URLs; it takes precedence over `Paste Screenshot`, which appears only for image data without file URLs. History rows are frozen and omit Edit/On/Off; they offer Duplicate as new event, reveal an existing attachment folder, and Delete.

`Paste Screenshot` accepts image data currently available on the macOS pasteboard (including a copied photo), converts it to a timestamped JPEG, and stages it in the event draft. `Paste Attachment` accepts regular file URLs currently available on the pasteboard, including PDF/Excel/image files, and stages/copies them using the same attachment path as `Attach Files`; directories and folder contents are not imported. The editor immediately lists staged and saved attachments: images use thumbnails, while PDF/Excel/other files use type icons with filename and size; staged files can be removed before Save. Dragging files onto a row is intentionally not a second attachment path yet.

### Save buttons

All settings Save buttons use one pattern:

1. Enabled when the form is dirty and valid.
2. On success, persist the change and refresh dependent state.
3. Change label to `Saved`.
4. Become dimmed/disabled while no further changes exist.
5. Become active again only after a new change.

This applies to event Save, Location Save, Save Weather, and Save Astronomy.

### Modal behavior

Clean modal forms close on backdrop click as well as Cancel. Dirty forms are guarded. Dialog contents are scrollable when they exceed the available window height. Fixed-width time controls, buttons, and rows prevent layout shifts and clipping.

## 14. Menu Bar, Dock, and Startup

`Blink.app` uses SwiftUI `MenuBarExtra` for a small menu-bar item. It reflects global attention color/state and can show:

- Number of active attention events.
- Critical/high-priority open items.
- Next scheduled event.
- `+ New`.
- `Open Blink`.

The menu-bar extra exists while the application is running. The Blink GUI LaunchAgent launches the app at login. A separate watcher LaunchAgent starts `watcher.py` using the project `.venv/bin/python`, not an ambient Python executable.

The physical lamp is controlled by the watcher. The GUI's row/tab animation is visual attention only and must not be confused with the hardware blinker process.

## 15. Watcher Runtime

At startup and in its loop, the watcher:

1. Writes/updates a heartbeat.
2. Validates and loads location, weather, astronomy, and personal event JSON.
3. Ensures the astronomy schedule is present and sufficiently current.
4. Runs the weather cycle and refreshes weather before a due weather push.
5. Reconciles the rolling remote queue for personal and astronomy events.
6. Determines due reminders and independent astronomy events.
7. Sends ntfy messages with dedupe identifiers.
8. Updates the physical blinker state until the relevant event is Done.
9. Records failures for Health/status inspection and retries within bounded rules.

The remote queue is limited to the supported rolling horizon and is an aid for future personal/astronomy delivery. Weather is fetched close to send time because its value must be current. Briefing configuration changes are carried through the local JSON contracts: SwiftUI writes the change instant, and `watcher.py` applies the next-local-day deferral for an already-past target.

## 16. Verification Snapshot

The latest recorded verification state is:

- Python test suite: 128 passing.
- Swift test runner: passes.
- Swift release build: completed.
- Python compile checks: pass.
- plist/JSON validation: pass.
- Open-Meteo city matrix: 20/20 tested cities returned a selectable city with coordinates/timezone.
- Astronomy schedule: 732 daily records over the current 24-month horizon.
- Astronomy schedule contains no Eclipse/advance-offset keys.
- Watcher heartbeat is fresh and the watcher LaunchAgent is configured.
- Release executable is copied to `Blink.app/Contents/MacOS/Blink`.
- Manual visual walkthrough remains necessary for every modal, compact window size, search scrolling, notification appearance, and physical lamp behavior.

Recommended commands from the project root:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m py_compile watcher.py app/agenda_store.py app/event_timing.py app/location_geocoder.py app/location_store.py app/notification_format.py app/weather_store.py astronomy/generate_astronomy.py
(cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner)
(cd app/BlinkSwiftUI && swift build -c release)
./status_watcher.command
```

## 17. Current Limitations and Operational Assumptions

- City search needs network access and a reachable Open-Meteo geocoding endpoint.
- Weather freshness depends on network availability at send time.
- The Mac must be awake and the watcher must be running for direct local processing; iPhone notification delivery also depends on iOS/ntfy notification permissions and network.
- A custom coordinate does not magically determine the timezone. The timezone is explicit input and must be kept coherent with the coordinates.
- Unicode emoji rendering varies slightly by client, but the notification content remains textually understandable.
- Astronomy is only as accurate as the coordinate/timezone tuple, local ephemeris, and generation status. A stale or invalid schedule must be surfaced, not presented as fresh.
- The current project is local-first and single-user. There is no account synchronization or multi-device event database.

## 18. Rules for Future Changes

Before changing code, a future Codex thread must:

1. Read this document, [`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](/Users/vitaliiprotsiuk/Desktop/Blink/docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md), and [`docs/HANDOFF.md`](/Users/vitaliiprotsiuk/Desktop/Blink/docs/HANDOFF.md).
2. Read [`CODEX_NEXT_THREAD_PROMPT.md`](/Users/vitaliiprotsiuk/Desktop/Blink/CODEX_NEXT_THREAD_PROMPT.md) for the immediate task.
3. Inspect the current source and runtime files; screenshots are evidence, not the source of truth.
4. Preserve the SwiftUI -> JSON -> watcher -> ntfy/lamp boundary.
5. Keep Weather, Astronomy, Location, Personal Events, and Attention as separate modules with explicit dependencies.
6. Trace every changed field through model, persistence, watcher, notification format, UI, and tests.
7. Do not claim a feature is working without running the relevant tests and a manual path when OS/UI behavior is involved.
8. Update this report, the contract, and the handoff whenever a boundary or user-visible behavior changes.

The most important invariant is simple: one source of truth per block, one production watcher, explicit location/timezone inputs, deterministic event state transitions, and user-facing notifications that contain readable content rather than transport JSON.
