# Blink Current State Contract

> **CURRENT CANONICAL CONTRACT** — running code and this document outrank
> `docs/HANDOFF.md` and all historical plans. Historical plans never override a
> newer owner decision recorded here.

**Snapshot:** 2026-09-12
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`

The complete technical description for ChatGPT is [`BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`](../../BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md). The immediate continuation prompt for a new Codex task is [`CODEX_NEXT_THREAD_PROMPT.md`](../../CODEX_NEXT_THREAD_PROMPT.md).

The authoritative post-Phase-7 remaining roadmap is
[`docs/implementation/BLINK_REMAINING_ROADMAP.md`](../implementation/BLINK_REMAINING_ROADMAP.md).
Stage 0 reconciliation and Stage 1 manual acceptance are complete; Stage 2
production iPhone attachment viewing is current.

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

### iPhone exchange (manual Phase 4B/5/6 complete; Stage 2 Mac-side implemented, physical acceptance pending)

A private Apple Shortcuts container has been manually verified at
`~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents` with
`Blink_Feasibility/{ToMac,ToPhone}` and the separate acceptance inbox
`Blink_Acceptance/ToMac`. This is transport only, not a database or source of
truth: `agenda.json` and Blink-local attachment folders remain
Mac-only, and ntfy remains Mac → iPhone push transport. Manual feasibility
coverage is complete for file transport, Quick Look, external Shortcut input,
DONE, and CREATE_EVENT with no attachment, image, and PDF. Phase 2B canonical
transactions and Phase 3's single opt-in watcher worker are implemented, but
production iCloud processing remains disabled by default; no real
`Blink_Production/ToMac` root is configured. Phase 5 manual CREATE acceptance
passed with the migrated `Blink Create Test`; its historical artifacts are
archived outside the now-empty acceptance inbox. No public links, HTTP, production
ntfy Actions, production Shortcut changes, or Photos/Documents access is
enabled. See
[`docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`](../feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md).

Controlled Phase 6A/6B CREATE acceptance also passed against
`Blink_Acceptance/ToMac`. The reader observed iCloud `dataless` files and now
classifies macOS `Errno 11 (Resource deadlock avoided)` during package or
attachment reads as `PENDING_SYNC`, preserving the exact package for retry.
The accepted PDF was committed to a Mac-generated event-ID owner folder only
after its bytes became local. A past-start event was observed in Today/Active
until completion. Phase 6 DONE passed: after the accepted ntfy action was
tapped, package `20260912221340-109486748.done.json` + `.ready` arrived in the
acceptance inbox, was applied, and the event became `done=true`. The historical
feasibility tree is never used by the production/acceptance importer. The
controlled mailbox is currently disabled.

Real Apple Shortcuts has no native Generate UUID action. Production phone
transport IDs therefore use `<yyyyMMddHHmmss>-<9-digit-random>`, for example
`20260912154532-482193775`; UUIDv4 remains accepted for backward compatibility.
This combined value is transport/dedupe identity only, never an event ID or
event start time. The Mac importer uses normal Blink business logic, remains
idempotent, and preserves the local source of truth. The originating ntfy DONE
notification remains unchanged; a newly applied remote DONE emits one separate
short confirmation without an action button or `clear=true`, while repeats,
no-ops, stale, malformed, pending, and failed commands remain silent.

Mac-side DONE action support is implemented but disabled by default. When
`BLINK_NTFY_DONE_ACTION_ENABLED=1` is explicitly set, eligible personal
notifications expose one encoded `Blink DONE` Shortcut action using
`blink-done-v1|<event_id>`; queue and direct paths share the same payload.
Controlled Phase 4B acceptance passed with `Blink DONE Test`, input
`blink-done-v1|EVENT123`, and the exact feasibility package pair
`20260912163022-101411924.done.json` + `20260912163022-101411924.ready`.
The importer remained disabled; this does not enable production mailbox
processing.

Stage 2 Mac-side attachment viewing is now implemented behind the separate
opt-in controls `BLINK_NTFY_FILES_ACTION_ENABLED=1` and
`BLINK_TO_PHONE_ROOT` (physical iPhone acceptance is still pending). The Mac
keeps `event_data/attachments/<owner-id>/` canonical and stages flat,
event-specific ToPhone snapshots with deterministic
`blink-files-v1-<sha256-prefix>` package IDs. Queue reconciliation refreshes a
queued/delayed package when canonical files change; after the reminder becomes
due, the delivered snapshot is immutable until bounded cleanup. The ntfy
payload uses the canonical percent-encoded `Files` action with input
`blink-files-v1|<package-id>`; no `clear=true` is added. The isolated WORK
candidate reads only the matching package, then uses
`Choose from Attachments` → `Show Selected Item in Quick Look` for both the
one-file and multiple-file branches. The original and backup `Blink Files`
Shortcuts remain unchanged. Production mailbox remains disabled and
`Blink_Production/ToMac` remains unused.

For controlled acceptance only, `BLINK_NTFY_FILES_SHORTCUT_NAME` may override
the Files action target; when unset, the production default remains
`Blink Files`. The current retest uses the explicit target
`Blink Files Stage2 WORK` and does not change production Shortcut naming.

The first controlled Files push to `Blink Files Stage2 WORK` was accepted by
ntfy (HTTP 200), but tapping the action on iPhone opened the Shortcuts library
instead of Quick Look. The Mac candidate and URL were verified, and a later
iPhone screenshot confirmed that the full candidate and escaped-pipe regex are
present there, and the Shortcut showed a completion checkmark after the tap.
The PDF opened manually from Files, proving package availability, while the
iOS Quick Look action produced no preview. The owner has now confirmed the
same result in the visible iPhone Shortcuts screen: WORK runs to a checkmark,
but no chooser or PDF appears. The WORK candidate's acquisition prefix was
repaired to the proven `Get file from Shortcuts at path
Blink_Acceptance/ToPhone` → `Get Contents of File` pattern, with `AllFiles`
bound to `Folder Contents`. The WORK candidate still uses
`Choose from Attachments` followed by `Show Selected Item in Quick Look` in
both count branches; the original and backup Shortcuts remain unchanged. One
new controlled push was sent after the repair and again finished on iPhone
with a checkmark but no chooser or PDF. Immediately before that push, the Mac
package evaluation was `AllFiles = 3`, ready = 1, manifest = 1, and
attachments = 1, so no fail-closed count branch should have stopped the
Shortcut. The Mac database contains the repaired 46-action WORK tree, and the
owner's iPhone editor screenshot now confirms the repaired acquisition prefix
is present on the phone. The stale-version hypothesis is removed. The
unchanged canonical `Blink Files` control and the temporary `Blink Files
Acquisition Test` have both displayed choosers and opened PDFs successfully
on the current iPhone, proving the general iOS presentation path, acceptance
folder acquisition, and basic folder-contents path. The remaining failure is
specific to WORK parsing, filters, counts/conditionals, or the filtered item
type. No additional push is allowed until that boundary is diagnosed.
The temporary `Blink Files Acquisition Test` is now renamed `Blink Files
Runtime Diagnostic`; it reports `AllFiles` and paired literal/dynamic filter
counts on-device, with no presentation or fail-closed branch. Run it once
before any new WORK edit or ntfy push.
Its first run showed only a blank `Cancel`/`Done` sheet, so it did not yet
measure runtime values. The aggregate output was corrected to direct
`ActionOutput` references from the seven `Count` actions; the next run is the
valid diagnostic observation.
It has now been reduced to a four-action count probe (`Get file` → `Get
Contents` → `Count` → one-line `Show Result`). Run only this simplified probe
after synchronization; do not run the former long diagnostic.
SQLite/editor inspection confirms the filtered values are File items/
references. No production mailbox was enabled. The unresolved gate is still
physical iPhone viewing.

SwiftUI also has the approved Phase 7 fast refresh: `ContentView` observes the
parent directory containing `agenda.json`, filters/debounces atomic-replace
events, and rereads the file through `BlinkStore.loadEventResult()` so the
normal snapshot, Attention, Dock, and search flow remains canonical. The
30-second polling fallback remains enabled; observer failure is non-fatal and
does not write agenda data.

The following are core remaining requirements, not implemented behavior:

- physical iPhone acceptance of the implemented event-specific `ToPhone`
  attachment viewing action, including one-file direct open and multi-file
  chooser behavior;
- an optional personal Today Morning Briefing containing every applicable
  Today event, with persistent enable/disable, watcher-owned delivery,
  local-date dedupe, wake/timezone/empty-day rules, and Weather/Astronomy
  coexistence.

The physical USB device adapter and numeric mailbox/package/worker limits are
separate pre-production gates. The complete staged roadmap is in
`docs/implementation/BLINK_REMAINING_ROADMAP.md`.

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
| Mailbox transport | `app/mailbox_importer.py`, optional worker in `watcher.py` | temporary/test roots by default; agenda remains source of truth |

Important runtime files include `agenda.json`, `location.json`, `config.json`, `watcher_state.json`, `watcher_runtime.json`, `ntfy_schedule_state.json`, `event_data/attachments/`, `event_data/drafts/`, `weather/weather_config.json`, `weather/weather_cache.json`, `weather/weather_state.json`, `astronomy/astronomy_config.json`, and `astronomy/astronomy_schedule.json`. All Blink-owned runtime data stays below the Blink project root; `event_data/` is private and ignored by Git.

Mailbox operational state, when the opt-in worker is enabled, stays below
`mailbox/journal/`, `mailbox/quarantine/`, `mailbox/mailbox_runtime.json`, and
`mailbox/processed_commands.json`; it is transport diagnostics only and never
replaces `agenda.json` as the event source of truth.

CREATE mailbox transport accepts v1 (nested) and v2 (flat Shortcut-friendly)
payloads. V2 carries `reminder_offsets` as a strict comma-separated string and
`blinker_minutes_before` as an integer, with optional flat attachment fields.
The importer normalizes both versions into the same canonical CREATE
transaction; no agenda or lifecycle contract changes.

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
- `done=true` is authoritative regardless of whether `start` is in the past or
  future: the event is classified into `History`, its original `start` is
  preserved, and load never reopens it automatically.
- Recurrence supports fixed weekly events and `days after Done`; completion creates at most one successor.
- Every event occurrence owns `event_data/attachments/<event-id>`. `series_id`
  is recurrence metadata only and is never a production attachment owner.
  Recurring successors receive a new event ID and start with zero attachments.
  Legacy shared-series folders are copied by an idempotent migration helper only
  when encountered; the legacy source is preserved.
- New-event drafts own `event_data/drafts/<draft-id>` while the editor is open. Files and pasted screenshots are staged before Save; Cancel/Escape removes only the Blink-created draft. Failed Save keeps the draft recoverable.
- Row attachment actions have a separate short-lived lifecycle: Today/Upcoming
  `Paste` and `Add Files` validate all inputs, stage and verify them, finalize
  them into the persisted event-ID folder, update `agenda.json`, and finish
  without opening the editor or requiring Save. A batch failure rolls back all
  files created by that operation and leaves existing attachments/metadata
  unchanged.
- Event loading is explicit: a valid empty `agenda.json` is `Loaded (0)`, while
  unreadable or malformed JSON is `Error/Stale`. A reload failure never replaces
  the last-good in-memory event snapshot with `[]`; Today, Upcoming, History,
  and Search continue to use that shared last-good snapshot and Health reports
  the source, count, last successful load, and error.
- Snooze, Quiet Hours, and Templates are retired and must not be reintroduced.
- Reminder offsets are canonical non-negative integer minutes and may include
  arbitrary values or multiple entries. Presets are UI convenience only;
  custom reminder values are preserved during editor save, and `0` is
  represented as `At time`. Blinker has one integer-minute offset and no
  Custom value in the current UI.
- New events default the independent Blinker picker to `At event`
  (`blinker_minutes_before: 0`). Reminders are a separate multi-select; changing
  either control never changes the other.
- Blinker starts at `event start - blinker_minutes_before` and continues until `Done`.

### Owner timing decision (2026-09-13)

Keep the existing Mac timing UI and data model. Reminders retain their current
presets, integer-minute `Custom minutes`, and multiple offsets. Blinker retains
its current presets, integer-minute values, and one offset, with no Custom value
for now. Do not add fractional minutes, seconds, or a universal timing control;
timing is not the current Files task.

## 4. Push Contract

ntfy metadata belongs in headers: `Title`, `Priority`, and `Tags`. The visible body must never be raw JSON and must not contain braces, JSON keys, internal tags, or scheduling objects.

The watcher remote-queue reconciliation signature includes the visible
attachment-presence bit (`has_files`). A transition `false → true` or
`true → false` rebuilds the queued payload so the paperclip cannot become
stale; a count-only change such as `📎 2 → 📎 3` does not create a duplicate
remote delivery because the visible payload is unchanged.

Personal pushes retain a useful title and description, with date/time and reminder context in the body. Personal titles begin with the event attention icon `🟢`, `🟡`, or `🔴`; if local attachments exist, exactly one `📎` marker is added. ntfy urgency remains independently controlled by its `Priority` header. The full multiline title/description remains local; the push uses a compact single-line title and a UTF-8 byte-safe body projection bounded by the current ntfy limits. Local paths, filenames, and file bytes are never sent. Weather identifies its block as `WEATHER` in the ntfy title/header, then shows location/date and selected weather blocks. If Astronomy is included with Weather, the body contains a plain `ASTRONOMY` section. If `Use Weather briefing time` is off, Astronomy is sent as its own briefing with the native ntfy title/header `ASTRONOMY` and a body beginning with the date; no Markdown markers are sent because the phone app displays them literally. Standalone notification titles use the same ntfy title/header styling. Astronomy rise/set labels use thin arrows after their matching icon: `☀️ ↑ Sunrise`, `☀️ ↓ Sunset`, `🌙 ↑ Moonrise`, and `🌙 ↓ Moonset`; Solar Noon remains `☀️` without a direction arrow, and `🌅` is not emitted. Individual Astronomy bodies include date/time and preserve useful calculated facts, but remove the duplicated event sentence and generic `Event starts now` line. Solar Noon renders solar altitude as a separate `Sun altitude: …° above horizon.` fact. Individual Astronomy notifications omit outgoing ntfy tags; internal event tags remain for classification and icon selection. Group Astronomy briefings show the lunar phase with exactly one large direction arrow (`⬆️` waxing or `⬇️` waning), followed by one `<N> days until Full Moon.` or `<N> days until New Moon.` line derived from the generated Skyfield schedule; exact Full/New Moon events omit the arrow. Standalone Moonrise/Moonset titles use the thin rise/set arrow, while standalone phase-event titles use the phase icon and omit the arrow at the exact boundary. The watcher owns this presentation and must not introduce a second approximate lunar calculation. The body must not repeat an event title: Sunset starts with its next useful fact, and standalone Moonrise/Moonset/New Moon/Full Moon bodies contain the countdown only. User-entered personal title/description may be in any language; application labels are English.

Personal and Astronomy event reminders use the rolling 24-hour queue. Weather is never added to that remote queue: at/after its configured local time the watcher fetches Open-Meteo fresh and sends directly. After a Mac sleep, the first watcher cycle checks today's delivered key and, if absent, performs the same fresh fetch and direct send; there is no late cutoff and only one automatic Weather briefing per local date. When a Weather or Astronomy briefing time is saved after today's local target has already passed, the watcher records the configuration-change instant and defers that newly configured briefing to the next local day; it does not send a late catch-up immediately from the Save action.

After a remote DONE is newly applied, the mailbox worker may send exactly one
short Mac confirmation using the same ntfy topic. Its title is
`✓ Done — <event title>` and its body is the optional description followed by
`Scheduled: <local date/time>`. The confirmation has no action button and never
uses `clear=true`; duplicate, already-done, stale, malformed, pending, or
failed commands are silent. A confirmation delivery failure is diagnostic only
and never rolls back the committed completion or changes the originating
notification.

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
- Weather settings include enable/disable, briefing time, and independent content selection for temperature, humidity, wind, rain, and snow. A fresh forecast is fetched before each due weather push. Humidity is date-scoped from Open-Meteo hourly values and is presented as a `Today` range plus the value for the local fetch hour (`Now`); it is not labeled as day/night. The weather state keeps `briefing_config_changed_at` so a saved time that is already past today is scheduled for the next local day.

## 7. GUI and UX Contract

- Navigation: Today, Upcoming, History, Astronomy, Weather, Location, Health, and Search. The Today header owns one compact round blue `+` action for creating a new event; there is no wide duplicate `New Event` button in the content area.
- All navigation tabs use the Blink-owned tab buttons and provide a subtle hover background before selection, so pointer users can see the interactive target.
- Today must not contain duplicate giant branding or duplicate New Event controls.
- Today and Upcoming show clear dates including year, color/Attention,
  title/description, a compact paperclip plus attachment count when applicable,
  a folder button, and actions. They do not render filename mini-lists or nested
  attachment scroll areas. The content area reacts to hover and a double-click
  opens the editor.
- History does not show meaningless On/Off for completed entries and is frozen: there is no Edit button or edit-on-click. History offers Duplicate as new event, attachment actions, and Delete.
- Active and Upcoming context menus always offer `Open Attachments Folder`; Blink creates the owner folder on demand even when it is empty. Frozen History offers that action only when an existing attachment folder is present.
- One `Paste` action is offered when the macOS pasteboard contains regular file
  URLs or decodable image data. File URLs take precedence and are copied as
  regular files; otherwise the first image is converted to a timestamped JPEG.
  Plain text, emoji, AutoCAD geometry, directories, and unsupported clipboard
  types do not expose an attachment paste action. The editor shows thumbnails
  for images and type icons for other files, without parsing file contents.
- Search also matches visible attachment filenames and extensions by reading the local owner folder; it does not inspect file contents. JSON metadata and folders remain canonical, leaving room for a rebuildable SQLite index only if scale later requires it.
- Event rows show a green `On` button for enabled events and a red `Off` button for disabled events. The status remains a toggle, not completion.
- Disabled rows dim their date/title/description to show that they are inactive, but their priority circle stays fully saturated. Active-row pulsing also leaves the priority circle solid and readable.
- Forms use English labels, red asterisks for required fields, stable `HH:mm` widths, consistent Cancel/Save placement, and shared save feedback: after successful save the button reads `Saved`, dims, and reactivates only after a new edit.
- The event editor is a scrollable two-column form: Title/Description, attachments, and event options are in the left column; the explicit full local event date, date calendar, time controls, and Cancel/Save actions are in the right column. It opens nearly full-height, has a draggable header and a bounded lower-right resize handle, and keeps content scrollable at every size. Empty/short Title and Description fields stay compact and grow only for wrapping or paragraph breaks, within a bounded height. The custom compact-spacing calendar marks today with a blue filled square, colors future event dates by that date's highest personal-event priority, and gives past event dates a muted gray background. These are presentation-only markers. The explicit date label is driven by the draft date and the editor view is keyed by event ID so reopening another event resets the calendar month and selection to that event.
- Clean modal forms close on Cancel, Escape, or backdrop click. Dirty forms require an explicit choice.
- A clean editor may double-click a calendar day to leave the editor and open the selected-day view. Initial draft normalization and attachment preview loading never mark the editor dirty. If the draft contains real edits beyond the calendar's transient date selection, the existing Save-or-Cancel guard remains in force.
- Event forms use multiline Title/Description editors, Finder multi-file selection, and screenshot paste. New-event drafts live under Blink-local `event_data/drafts/` until Save; saved files live under `event_data/attachments/`.
- Event-row context menus expose only currently applicable actions: Edit
  (Today/Upcoming only), Duplicate as new event, Duplicate with Attachments when
  files exist, Add Files, one unified Paste action when the clipboard supports
  it, Open Attachments Folder, On/Off, Done, and Delete. On Today/Upcoming,
  Paste and Add Files are immediate persisted-event actions: they do not open
  the editor and do not require Save. They use a short-lived transactional
  staging/verify/finalize operation with all-or-nothing rollback. The editor's
  Add Files/Paste/drop controls remain draft-based until Save. Drag-and-drop is
  accepted only inside the editor attachment panel; rows never accept drops.
  Attachments are never sent to ntfy or committed to GitHub.
- The editor attachment panel shows staged and saved filenames, sizes, image
  thumbnails/file-type icons, `+ Add Files`, one `Paste`, `Open Folder`, and an
  editor-only drop zone. Removing a staged file is immediate for the draft;
  removing a saved file is pending until Save, while Cancel restores it. Save
  moves accepted removals to macOS Trash and refreshes the manifest.
- Clicking a row paperclip/count opens a compact filename/type popover. Rows do
  not contain a filename mini-list or nested attachment scroll area.
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

- Python: 195 tests passing via `.venv/bin/python -m unittest -q`, including
  explicit mailbox arbitrary-minute and title-validation coverage.
- Alternate discovery command `.venv/bin/python -m unittest discover -s tests -p
  'test_*.py' -v` is not runnable here because this checkout has no importable
  `tests/` directory; root-level `test_*.py` modules are covered by the default
  command.
- Swift UI/store contract runner: passing, including custom reminder/blinker
  round-trip and observer save-loop coverage.
- Swift release build: passing.
- Python compile checks: passing.
- Plist validation: passing.
- `./status_watcher.command`: watcher running with a fresh heartbeat.
- Open-Meteo international city matrix: 20/20 returned coordinates and IANA timezones.
- Astronomy schedule: 732 daily records, no active Eclipse or advance-offset keys.
- Watcher: running with a fresh heartbeat.
- Manual visual walkthrough is still required for compact window layouts, modal/backdrop behavior, search positioning, native notification rendering, and physical lamp behavior.

When a new requirement conflicts with this contract, stop and ask before changing a boundary. Update this file, `docs/HANDOFF.md`, and the relevant full report in the same change.

### Selected Day contract

Double-clicking a non-today day in the editor calendar enters a transient
Selected Day mode by relabeling the first tab with `MMM d`. It uses the shared
snapshot (no second store), filters by the event's local calendar date, includes
unfinished/Done/Off records, and sorts by local start then event ID. The page
shows full date/weekday, then an `Exit` button immediately to the right of that
date block, with `+ New Event` kept on the right and the selected date
prefilled. The button and keyboard Escape call the same guarded exit action and
are behaviorally identical. Search is cleared on entry and is scoped to the selected day.
Double-clicking today returns Today; switching tabs preserves selection; Exit
clears it; relaunch does not restore it. Frozen rows retain History actions, and
dirty editor drafts require Save or Cancel before navigation. Failed reloads
retain the last-good snapshot and never render a false empty selected day.
