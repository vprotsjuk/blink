# Blink — Complete Context for a New ChatGPT Thread

**Status:** current operational context
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`
**Language note:** technical collaboration and this document are in English;
communicate with the owner in Russian unless they request otherwise.

This document is the practical, self-contained entry point for a new ChatGPT
or Codex thread. It explains what Blink is, what is actually implemented,
which boundaries must not be crossed, and the one currently open feasibility
workstream. Read it before editing code or runtime data.

## 1. Authority and reading order

The current implementation is defined by running code and the documents below.
If sources differ, use this order:

1. Running code and
   [`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md).
2. [`BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`](BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md)
   for the full product and UI specification.
3. [`docs/HANDOFF.md`](docs/HANDOFF.md) for operational history and known
   implementation decisions.
4. [`docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`](docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md)
   for the separate iCloud/iPhone spike.
5. [`docs/feasibility/BLINK_NEW_THREAD_HANDOFF_PROMPT.md`](docs/feasibility/BLINK_NEW_THREAD_HANDOFF_PROMPT.md)
   for the immediately preceding handoff checkpoint.

Documents labelled **HISTORICAL** or **SUPERSEDED** are retained only for
traceability. Never restore an old feature merely because an old document is
detailed. In particular, Snooze, Quiet Hours, Templates, Eclipses, Calendar
integration, cloud backends, and a second sender/scheduler are not active
product features.

Before work, always inspect the actual checkout:

```bash
cd "/Users/vitaliiprotsiuk/Desktop/Blink"
git status --short
git log -4 --oneline --decorate
```

Do not reset, overwrite, or remove user changes. The rollback checkpoint before
the iCloud feasibility work is the tag
`rollback-before-icloud-feasibility-2026-09-10`, pointing to `d6476b6`.

## 2. Product in one paragraph

Blink is a local macOS reminder and daily-briefing app. It stores settings and
events in local JSON, calculates Astronomy locally, fetches Weather from
Open-Meteo, sends notifications through ntfy, and coordinates an existing USB
blinker/lamp. The native SwiftUI app is a local editor/viewer. A Python watcher
is the single production scheduler and sender. iPhone is a notification client,
not the source of truth.

## 3. Non-negotiable production architecture

```text
SwiftUI GUI
  -> local JSON files and Blink-owned attachment folders
    -> watcher.py
      -> ntfy
        -> iPhone / Mac notification clients
      -> USB blinker / lamp
```

The boundaries are deliberate:

- `Blink.app` owns visible UI, local editing, presentation of event state,
  Dock attention, and menu-bar state. It **never** sends production ntfy pushes.
- `watcher.py` is the only long-running delivery process, only production
  sender, and only scheduler/blinker coordinator.
- JSON files and Blink-owned attachment folders are canonical. ntfy is transport
  and notification presentation, never a database or source of truth.
- Weather fetch/cache, Astronomy calculation, location, personal events, queue,
  and UI are separate blocks with explicit contracts. Do not silently couple
  them or add a second store.
- Use atomic writes and preserve unknown JSON fields unless a documented
  migration intentionally removes a retired field.
- Do not add SQLite, Netlify, AI memory, a cloud backend, Calendar integration,
  or another background runner. A future SQLite index, if ever justified, may
  only be rebuildable derived data.

## 4. Repository map and persistent data

```text
watcher.py                         production scheduler/sender/blinker process
app/agenda_store.py                personal-event persistence and lifecycle
app/event_timing.py                timezone-aware event timing
app/attachment_store.py            local attachment ownership and transactions
app/notification_format.py         shared notification projection/formatting
app/weather_store.py               Open-Meteo fetch/cache/format helpers
app/location_store.py              location persistence
app/location_geocoder.py           city-search bridge
astronomy/generate_astronomy.py    Skyfield schedule generator
astronomy/ephemeris/de440s.bsp     local JPL ephemeris
app/BlinkSwiftUI/                  Swift package, GUI, and test runner
agenda.json                        personal-event source of truth
location.json                      selected location and timezone
config.json                        Blink runtime configuration
event_data/attachments/            saved private event files
event_data/drafts/                 temporary editor attachment staging
weather/                           weather config, cache, and delivery state
astronomy/                         Astronomy config and rolling schedule
launchd/                           app/watcher LaunchAgent definitions
```

Important runtime files also include `watcher_state.json`,
`watcher_runtime.json`, and `ntfy_schedule_state.json`. All Blink-owned runtime
data remains below the project root. `event_data/`, `agenda.json`, application
bundles, and build products are private/runtime material and must not be
committed to Git.

## 5. Personal events and lifecycle

Every personal event has at least `id`, `title`, `start`,
`reminders_minutes_before`, and `enabled`. `start` is an ISO timestamp with an
explicit UTC offset. Description is optional, multiline, and preserves
paragraphs. User-entered title/description may use any language; app labels are
English.

Lifecycle:

```text
Upcoming -> Active -> Done -> History
```

- `Done` persists completion, stops its blinker, clears attention, and retains
  the item in History.
- `On`/`Off` changes delivery eligibility; it is never completion or deletion.
  A disabled past unfinished item stays inspectable in History.
- A past enabled unfinished event stays Active until `Done`; its row and the
  Blink-owned Today tab can pulse as UI-only attention.
- Deleting removes the event and queued reminders; it does not create History.
- Editing is allowed only outside History and preserves unrelated fields while
  recalculating classification and future reminders.
- History is frozen. It can only be duplicated as a new event (fresh ID and
  attachment owner) or deleted. It cannot be edited in place.
- A stale legacy record marked `done=true` with a future start is repaired on
  load to `done=false`, `done_at=null` and returned to Today/Upcoming.
- Recurrence supports fixed weekly events and `days after Done`; completion may
  create at most one successor.
- New events default the independent Blinker control to `At event`
  (`blinker_minutes_before: 0`). Reminders and the Blinker picker are separate.

## 6. Local attachment contract

Attachments are local private files, not ntfy payloads.

```text
event_data/attachments/<event-id>/   saved files for one occurrence
event_data/drafts/<draft-id>/        temporary files for an open editor
```

- Every occurrence owns its folder by **event ID**. `series_id` is recurrence
  metadata only. A recurring successor starts with no files.
- JSON stores only attachment metadata (`owner_id`, count, `has_files`), never
  absolute paths or bytes.
- A new/edit editor creates a draft folder. Editor Add Files, Paste, and file
  drop stage files until Save. Cancel/Escape removes only the Blink-created
  draft; failed Save retains it for recovery.
- Today/Upcoming context-menu Add Files and Paste are different: they complete
  an immediate persisted-event transaction without opening the editor or
  requiring Save.
- Multi-file operations validate, stage, verify, and finalize all files
  transactionally. Any failure rolls back files created by that operation and
  leaves existing files/metadata intact.
- `Open Attachments Folder` is always available for writable Today/Upcoming
  events and creates an empty folder on demand. Frozen History may reveal a
  folder only when one already exists with files.
- Finder file URLs take precedence in Paste. Otherwise the first decodable
  image is written as a timestamped JPEG. Plain text, emoji, AutoCAD geometry,
  directories, and unsupported content are not attachments.
- Drag and drop is accepted only inside the editor attachment panel; rows do
  not accept drops. Image previews use thumbnails; other files show type icon,
  filename, and size without parsing their contents.
- Deleting an event with files asks for confirmation and moves only that
  Blink-owned folder to macOS Trash.
- Reloading reconciles attachment counts from owner folders. A malformed or
  unreadable `agenda.json` never replaces the last known good shared event
  snapshot with an empty list.
- Search includes visible attachment filenames/extensions but never searches
  inside file content.

## 7. GUI behavior that must remain stable

Navigation includes Today, Upcoming, History, Astronomy, Weather, Location,
Health, and Search. Blink-owned tab buttons have hover feedback. Today has one
compact round blue `+` button; do not restore a large duplicate New Event
control.

- Today/Upcoming rows show full date/year, time, saturated priority dot,
  title/description, compact paperclip/count, folder action, and applicable
  actions. Row content opens the editor only on **double-click**.
- History rows are immutable: no Edit, no edit-on-click, and no On/Off. They
  offer duplication, attachment access only when valid, and Delete.
- Row context menus show only applicable actions. In writable rows, Paste and
  Add Files are immediate actions; editor attachment actions stay draft-based.
- Disabled rows dim non-priority text but keep the priority circle saturated.
- Forms use English labels, required-field asterisks, 24-hour `HH:mm`, and
  consistent Cancel/Save feedback. After successful save, Save reads `Saved`
  until a genuine new edit occurs.
- The event editor is a nearly full-height, scrollable two-column form with a
  draggable header and bounded lower-right resize handle. It keeps all controls
  reachable in smaller windows.
- The compact calendar marks today blue, future event dates by highest priority,
  and past event dates muted gray. These are presentation-only.
- A clean editor can double-click a calendar day to enter transient Selected Day
  view. Dirty drafts retain the Save-or-Cancel guard. Initial normalization and
  attachment preview loading must not falsely mark a draft dirty.
- Selected Day reuses the shared snapshot; it filters a local calendar day,
  sorts by local start then ID, has an Exit button next to date/weekday, and
  exits identically by button or Escape. It never persists across relaunch.
- Health reports source path, event count, last successful load, and load
  error/staleness; it must distinguish valid empty data from an error.

## 8. Notification, queue, and blinker contract

ntfy metadata belongs in headers (`Title`, `Priority`, `Tags`); the body is
human-readable text, never raw JSON, internal keys, or scheduling objects.

- Personal and Astronomy reminders use the rolling 24-hour remote queue.
- Personal titles begin with `🟢`, `🟡`, or `🔴` according to attention. Local
  attachments add exactly one `📎` marker. Paths, filenames, and bytes never
  leave the Mac.
- Queue reconciliation includes attachment presence (`has_files`), so a visible
  paperclip appearance/disappearance rebuilds pending payloads. A count-only
  change does not create a duplicate delivery.
- The watcher owns shared formatting; SwiftUI mirrors approved presentation
  language but must not calculate alternate lunar facts or send independently.
- A blinker starts at `event start - blinker_minutes_before` and continues until
  Done. Attention and pulsing are presentation/output consumers of the same
  event lifecycle, not alternate lifecycle implementations.

## 9. Weather

Weather uses Open-Meteo and local normalized cache/state. Its configuration
supports enable/disable, a 24-hour briefing time, and independent groups for
temperature, humidity, wind, rain, and snow.

- Location is shared by Weather and Astronomy. City search supplies name,
  coordinates, and IANA timezone together; custom coordinates require an
  explicit valid timezone. A changed location invalidates Weather cache and
  marks Astronomy for regeneration.
- Weather is **never** inserted into the remote ntfy schedule. At/after its
  configured local time, the watcher fetches fresh forecast data and sends a
  direct briefing.
- After Mac sleep, first watcher cycle catches up once for the local day if the
  briefing was not delivered. There is no late cutoff, and only one automatic
  Weather briefing is delivered per local date.
- Saving a new Weather or Astronomy briefing time after today’s target has
  passed records its change instant and defers that newly configured delivery
  to the next local day. Saving must not cause an immediate accidental push.
- Humidity is shown as Today’s range plus local fetch-hour `Now`, not as a
  day/night value. A failed refresh must be surfaced, never represented as
  fresh data.

## 10. Astronomy

Astronomy uses Skyfield, local `de440s.bsp`, configured coordinates, and IANA
timezone. It generates a rolling 24-month schedule and regenerates on location
change or insufficient horizon.

- Supported Sun/Moon items: sunrise, solar noon, sunset, civil twilight,
  moonrise, moonset, Full Moon, New Moon, and moon status at sunset.
- Individual event toggles fire at the exact calculated time (offset zero).
  Sunset plus Moon Status is one combined event-time notification when both are
  enabled.
- Daily Astronomy Briefing is optional. `Use Weather briefing time` appends a
  plain `ASTRONOMY` section to Weather; otherwise it sends a separate native
  ntfy `ASTRONOMY` briefing.
- Rise/set notation is `☀️ ↑ Sunrise`, `☀️ ↓ Sunset`, `🌙 ↑ Moonrise`,
  `🌙 ↓ Moonset`. Solar Noon uses `☀️` only. The retired `🌅` icon is never sent.
- Daily lunar text uses `Waxing Moon`/`Waning Moon` on ordinary days and
  `New Moon`/`Full Moon` only on their exact event day. It shows at most one
  large phase arrow (`⬆️`/`⬇️`) and one schedule-derived countdown; exact phase
  events omit the arrow. Thin arrows mean rise/set only.
- Polar no-rise/no-set states are explicit; never fabricate times.
- Eclipses and Astronomy advance offsets are intentionally absent. Ignore or
  safely migrate legacy Eclipse/offset keys; never reintroduce them.

## 11. Startup and verification

`install_launch_agent.command` installs Blink.app and watcher LaunchAgents.
The watcher must run with the project `.venv/bin/python`. The app and watcher
can restart independently. `status_watcher.command` is the runtime diagnostic.
The local app bundle is unsigned and intended for this Mac.

Run relevant checks from the stated directories before claiming work complete:

```bash
cd "/Users/vitaliiprotsiuk/Desktop/Blink"
.venv/bin/python -m unittest -q
.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py
plutil -lint Blink.app/Contents/Info.plist launchd/*.plist
./status_watcher.command
git diff --check

cd app/BlinkSwiftUI
swift run BlinkSwiftUITestRunner
swift build -c release
```

After a release build, copy the built executable into
`Blink.app/Contents/MacOS/Blink`, restart the app, and rerun relevant runtime
checks. Manual UI QA is required for changed surfaces, especially normal and
reduced window size, Today/Upcoming/History, New/Edit Event, Astronomy, Weather,
Location, Health, native notifications, and physical lamp behavior where
applicable.

The recorded baseline before the dedicated iCloud spike included passing Python
tests, Swift store/UI runner, release build, JSON/plist checks, a fresh watcher
heartbeat, a 732-day Astronomy schedule with no active Eclipse/offset keys, and
an Open-Meteo city matrix of 20/20 successful timezone-bearing results. Treat
this as historical evidence, not a replacement for running relevant current
checks after a change.

## 12. Separate iCloud ↔ iPhone feasibility spike — not production

This is the only unfinished workstream. It is a robustness/feasibility spike,
not an approved feature. It must not be mixed into production changes.

The candidate topology is:

```text
iPhone Shortcut <-> private iCloud Drive mailbox <-> future Mac-side worker

ntfy remains Mac -> iPhone notification transport only.
```

The dedicated test area is outside the repository:

```text
iCloud Drive/Shortcuts/Blink_Feasibility/
  ToMac/
  ToPhone/
```

Actual local iCloud root:

```text
/Users/vitaliiprotsiuk/Library/Mobile Documents/com~apple~CloudDocs
```

### Spike rules

- The mailbox is transport only. It is not a database or source of truth.
- iPhone never edits or synchronizes `agenda.json` directly. Blink-local event
  folders and Mac JSON remain canonical.
- Candidate incoming commands are `CREATE_EVENT` and `DONE`.
- No changes to `watcher.py`, production SwiftUI behavior, `agenda.json`, ntfy
  configuration, or normal production attachments belong to this spike.
- Do not use public iCloud links, “Anyone with the link”, HTTP/ntfy for reverse
  file transfer, symbolic links, or scanning/accessing Photos, Documents,
  Downloads, Desktop, or other user folders.
- Do not connect the exchange to production until the separate manual iPhone
  acceptance test has succeeded.

### Tested mailbox package shape

Incoming event package:

```text
ToMac/<transfer_id>.event.json
ToMac/<transfer_id>.attachment.<extension>   # optional
ToMac/<transfer_id>.ready                    # written last
```

Incoming completion command:

```text
ToMac/<command_id>.done.json
ToMac/<command_id>.ready                     # written last
```

Mac-to-iPhone viewing package:

```text
ToPhone/<occurrence_id>.manifest.json
ToPhone/<occurrence_id>__01__Permit.pdf
ToPhone/<occurrence_id>__02__Estimate.pdf
ToPhone/<occurrence_id>__03__Photo.jpg
ToPhone/<occurrence_id>.ready                # written last
```

A future reader must ignore a package until its `.ready` exists, validate its
JSON and every listed file, process it once, and only then mark or move it.
Flat package names are intentional: different UUIDs may have the same display
filename. The test validated Mac filesystem create/read/rename/delete,
subdirectories, Unicode, spaces, duplicate display names, and atomic
temp-to-rename. It created two CREATE_EVENT fixtures, one DONE fixture, and one
outgoing manifest. Outgoing PDF/JPG files are minimal placeholders proving
package shape only; they are not user documents.

`/usr/bin/shortcuts` exists but only provides `run`, `list`, `view`, and `sign`;
this Mac cannot create or import a Shortcut from its CLI.

### Required manual iPhone validation — still open

The owner must verify on a real iPhone:

1. `Blink Test` appears in Files Share Sheet.
2. It accepts a PDF.
3. It accepts an explicitly shared photo/image.
4. It accepts at most one attachment with a clear multiple-input rule.
5. Direct Home Screen/Shortcuts launch works without input.
6. It collects Title, Description, Event Date/Time, Priority
   (green/yellow/red), and Blink Date/Time.
7. It generates a UUID `transfer_id`.
8. It writes JSON first, attachment second if present, and `.ready` last.
9. Destination remains fixed at
   `iCloud Drive/Shortcuts/Blink_Feasibility/ToMac`, without a folder picker on
   each launch.
10. The Mac sees the complete package.

If iOS forces destination selection each time, record that as an architecture
blocker. Do not invent a workaround until the owner makes a separate decision.

The future `Blink Files` Shortcut may read only `ToPhone`, select by
`occurrence_id`, ignore manifest/ready markers, directly open one file or show
a list for multiple files. It must not create public links or use HTTP/ntfy.

## 13. Safe workflow for the next thread

1. Read this document plus the authoritative contract and the relevant detailed
   report before touching code.
2. Inspect `git status --short` and recent decorated log. Preserve unrelated
   edits.
3. State explicitly whether the request is a production change or the isolated
   iCloud spike. Never combine them casually.
4. For a production change, trace each altered field through model, persistence,
   watcher, notification projection, UI, and tests. Keep modules independent.
5. For a spike-only task, operate only within the dedicated iCloud test area and
   update its feasibility report; do not claim iPhone/cross-device behavior
   without a real manual test.
6. Run proportional automated and manual verification. Before final response,
   run `git diff --check` and report actual results, changed files, remaining
   blockers, and the next safe step.

## 14. Explicitly prohibited regressions

- No second scheduler, sender, cloud database, or alternate attachment store.
- No direct SwiftUI ntfy publishing.
- No restoration of Snooze, Quiet Hours, Templates, Eclipses, or retired
  Astronomy offsets.
- No modification of a frozen History event.
- No recurrence attachment sharing by `series_id`.
- No attachment bytes, filenames, or local paths in pushes.
- No false-empty event list after failed JSON reload.
- No remote-scheduled Weather push or stale data presented as fresh.
- No production iCloud/Shortcuts integration, public links, reverse HTTP/ntfy
  files, or iPhone access to `agenda.json` without a separate accepted design.

## 15. What a final report must say

For any completed task, state:

- changed files and why;
- Git commit/tag information when applicable;
- exact verification commands and factual outcomes;
- what was not verified manually or on-device;
- any open blocker and the next safe action.

Do not describe iPhone Share Sheet behavior or cross-device iCloud sync as
verified until the owner has performed the manual iPhone checklist above.
