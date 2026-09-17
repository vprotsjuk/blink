# Blink — Product and Architecture Design Document

**Audience:** programmer joining the project
**Product assumption:** Blink is a completed, working product. This document
describes the intended product and architecture, not unfinished laboratory
states or historical experiments.

## 1. Product in one sentence

Blink is a local-first macOS personal event and attention system: the user
creates timed events on the Mac, Blink preserves them as canonical local data,
calculates contextual weather and astronomy information, sends concise ntfy
notifications to the iPhone, and exposes carefully bounded iPhone Shortcuts
for event creation, completion, and attachment viewing.

The Mac is the source of truth. The phone is a fast interaction and
notification surface, not a second database.

The governing product principle is documented in
[`BLINK_PRODUCT_PHILOSOPHY.md`](BLINK_PRODUCT_PHILOSOPHY.md): Blink preserves
the reason and source context behind an action, then returns that context when
the action needs to happen. This is the product test for future features; the
architecture exists to protect it.

## 2. Why Blink exists for the user

The user wants one quiet, dependable place to remember things that require
attention at a particular time. A Blink event combines:

- a title and optional rich human description;
- an explicit local date and time;
- one or more reminders before the event;
- an independent visual/audio attention lead time (the Blinker);
- an importance level;
- optional files such as PDFs, photos, notices, or schedules;
- optional recurrence;
- completion and history.

The user works primarily in the Mac editor. The iPhone is useful when the user
is away from the Mac: it receives a readable notification, can complete an
event, and can open the event's current attachment package. The final phone
experience is intentionally small: one user-facing `Blink` Shortcut for
creation, with `Blink DONE` and `Blink Files` as notification actions.

## 3. Product principles

### Local-first ownership

Event data, settings, lifecycle, attachment ownership, and delivery state live
on the Mac. iCloud and ntfy transport data are derived or transient.

### One scheduler and one sender

`watcher.py` is the only long-running scheduler and ntfy sender. Blink does not
create a competing scheduler in Shortcuts, Calendar, a cloud function, or a
second Mac process.

### Lossless user text

Descriptions are ordinary user content, not a command language. Unicode,
emoji, quotes, backslashes, punctuation, and paragraph breaks are preserved.

### Explicit time semantics

Every event start carries an explicit UTC offset. Reminder and Blinker values
are integer minutes and are never silently rounded or coerced.

### Fail closed at boundaries

Malformed Shortcut input, ambiguous attachments, missing transport markers, or
foreign package files must stop safely rather than produce a plausible but
wrong event or file.

### Derived notification snapshots

Notifications and attachment packages are representations of canonical Mac
state. They are not authoritative edits to that state.

## 4. System context

```text
                         ┌──────────────────────┐
                         │      Mac user         │
                         │  Blink SwiftUI editor │
                         └──────────┬───────────┘
                                    │ atomic local JSON/files
                                    ▼
                         ┌──────────────────────┐
                         │  Mac canonical store  │
                         │ agenda + attachments  │
                         └──────────┬───────────┘
                                    │ read / reconcile
                                    ▼
                         ┌──────────────────────┐
                         │       watcher.py      │
                         │ scheduler + sender    │
                         │ lifecycle + blinker   │
                         └───────┬────────┬─────┘
                                 │        │
                       notification       │ LAN/USB attention output
                                 ▼        ▼
                         ┌────────────┐  ┌──────────────┐
                         │    ntfy    │  │ lamp/blinker │
                         └─────┬──────┘  └──────────────┘
                               │
                               ▼
                         ┌──────────────┐
                         │ iPhone        │
                         │ ntfy + iOS    │
                         │ Shortcuts     │
                         └──────┬───────┘
                                │ reads derived package
                                ▼
                         ┌──────────────┐
                         │ iCloud        │
                         │ Shortcuts     │
                         │ transport     │
                         └──────────────┘
```

The arrows have different meanings:

- Mac → local files: authoritative persistence;
- Mac → watcher: scheduling input;
- watcher → ntfy: notification transport;
- watcher → lamp: attention output;
- ntfy → iPhone: user-visible message and optional Shortcut action;
- Mac → iCloud Shortcuts container: derived attachment/command transport;
- iPhone Shortcut → iCloud Shortcuts container: read or write a bounded
  transport package.

## 5. Main user journeys

### 5.1 Create on Mac

1. User opens Blink and chooses Today or Upcoming.
2. User creates or edits an event.
3. Blink validates title, date/time, reminders, Blinker, importance, recurrence,
   and attachments.
4. On Save, staged attachments are copied into the event-owned folder and the
   event document is atomically persisted.
5. The watcher observes the canonical data and reconciles future deliveries.
6. At each due reminder, the user receives a concise ntfy notification.

### 5.2 Create from iPhone Share Sheet

1. User shares one accepted image, PDF, or file to `Blink`.
2. `Blink` receives the Share Sheet item or direct-launch input.
3. The Shortcut asks for Title, Description, date, time, importance, reminders,
   and independent Blinker settings.
4. The Shortcut validates the input and serializes one `CREATE_EVENT` payload.
5. It writes the payload to the Acceptance or Production `ToMac` mailbox and
   writes `.ready` last.
6. The Mac mailbox importer validates and applies the command under the normal
   agenda lock. The iPhone never edits `agenda.json` directly.

### 5.3 Create from Mac context

The same context-preserving capture should be available from the Mac without
requiring the user to open the editor first:

- right-click a supported Finder file and choose the Blink create action;
- when the clipboard contains a supported object, invoke the same create flow
  from a context-menu or equivalent Mac command;
- pass the selected object as the one optional attachment into the existing
  event editor/create contract.

These are additional entry points only. They reuse canonical validation,
attachment ownership, and persistence; they do not introduce a second event
type or storage path.

The Mac context entry points also include creating an event from selected text.
Blink should preserve the selection as a text-document attachment owned by the
event, so it can be returned together with the reminder rather than lost in a
temporary clipboard state.

### 5.4 Complete from a notification

1. User presses the `Done` action in an ntfy notification.
2. The action launches `Blink DONE` with
   `blink-done-v1|<event-id>`.
3. The Shortcut writes a bounded DONE command package to `ToMac`.
4. The Mac importer applies completion idempotently.
5. The event moves from Upcoming/Active to History, preserving its scheduled
   start and recording actual `done_at`.
6. Blink may send one short confirmation push. Replays are silent.

### 5.5 View attachments from a notification

1. For an eligible event, the Mac creates a deterministic `ToPhone` snapshot.
2. The normal event notification contains a paperclip marker and a `Files`
   action carrying only `blink-files-v1|<package-id>`.
3. The action launches `Blink Files` on the iPhone.
4. The Shortcut reads the shared `ToPhone` folder, validates the package
   markers, filters only that package's attachment files, presents a chooser,
   and opens the selected file in Quick Look.
5. The Shortcut does not modify the event or send data back to the Mac.

As a later read-only capability, the iPhone may browse event folders by their
real event names and open the attachments within them. This browser must use
derived, bounded transport data and must not become a second source of truth.

## 6. Event domain model

### Canonical event

Required fields:

```json
{
  "id": "event-uuid",
  "title": "Biometry",
  "description": "Optional multiline text",
  "start": "2026-09-22T06:59:00-07:00",
  "reminders_minutes_before": [1440, 60, 0],
  "blinker_minutes_before": 17,
  "attention_level": "red",
  "enabled": true,
  "done": false
}
```

The actual persisted document may also contain recurrence, `done_at`, source,
and attachment metadata. Event IDs are stable across ordinary edits. History is
frozen: a historical event is duplicated or deleted, not edited in place.

### Timing

- Reminder offsets are zero or more non-negative integer minutes.
- Presets include 1440, 720, 300, 60, 30, 10, 5, and 0.
- `0` means “at time”.
- Blinker is one independent non-negative integer-minute value.
- The Blinker affects attention output and does not change event lifecycle.
- An event becomes Active at its scheduled start, not when attention begins.

### Lifecycle

```text
Upcoming ──start reached──> Active ──Done──> History
    │                           │
    └────────────── Done ───────┘
```

Disabling an event changes delivery eligibility. It does not delete data or
rewrite history. Completing an event is idempotent.

## 7. Persistence and attachment ownership

The primary local stores are:

| Store | Responsibility |
|---|---|
| `agenda.json` | canonical personal events and lifecycle |
| `location.json` | canonical location, coordinates, timezone |
| `config.json` | private ntfy and runtime configuration |
| `weather/` | weather configuration, cache, delivery state |
| `astronomy/` | astronomy settings and generated schedule |
| `event_data/attachments/<event-id>/` | event-owned attachment bytes |
| `event_data/drafts/` | Blink-created unsaved attachment staging |
| `watcher_state.json` | direct-send deduplication |
| `ntfy_schedule_state.json` | rolling remote delivery queue |
| `watcher_runtime.json` | heartbeat and operational status |
| `mailbox/` | command import state and processed-command ledger |

Writes use atomic replacement and the agenda lock. Attachment Save follows:

```text
draft files
  -> validate file type and ownership
  -> copy into event-owned folder
  -> atomically persist event metadata
  -> remove only the Blink-created draft marker
```

A failed Save leaves a recoverable draft. User files are not silently deleted;
Blink-owned deletions use confirmation and a recoverable Trash path.

## 8. Runtime architecture

### 8.1 SwiftUI application

The native Mac application owns presentation and editing:

- Today, Upcoming, History, Astronomy, Weather, Location, and Health surfaces;
- event cards, search, drag-to-move, context actions, and completion;
- editor validation and attachment staging;
- persistence through the JSON/domain-store contracts;
- menu-bar and Dock attention presentation.

It does not send ntfy notifications and does not become a second scheduler.

The Swift package is at `app/BlinkSwiftUI`. Its core target should remain
testable without the graphical application.

### 8.2 Python domain modules

The `app/` package contains side-effect-isolated domain services:

| Module | Boundary |
|---|---|
| `agenda_store.py` | event validation, persistence, lifecycle, recurrence |
| `attachment_store.py` | attachment ownership, import, migration |
| `event_timing.py` | explicit-offset timestamp parsing |
| `weather_store.py` | Open-Meteo fetch, normalization, briefing state |
| `location_store.py` | location validation and timezone changes |
| `personal_briefing.py` | local-day personal briefing decision/message |
| `ntfy_schedule.py` | desired queue, reconciliation, dedupe, payload hashes |
| `notification_format.py` | titles, bodies, tags, Done/Files actions |
| `to_phone_store.py` | deterministic attachment snapshots and integrity markers |
| `mailbox_importer.py` | validate/apply/quarantine iPhone commands |
| `watcher_lifecycle.py` | heartbeat, sleep-gap and process health |
| `create_shortcut_simulator.py` | non-runtime CREATE logic harness |
| `done_shortcut_simulator.py` | non-runtime DONE logic harness |
| `files_shortcut_simulator.py` | non-runtime Files logic harness |
| `watcher.py` | orchestration, scheduling, network side effects |

`watcher.py` is the orchestration layer. Domain modules should not import the
GUI or call each other through hidden global state.

### 8.3 Watcher cycle

At startup and on each polling cycle, the watcher:

1. loads and validates configuration;
2. loads canonical agenda data;
3. refreshes/loads astronomy data when location or horizon requires it;
4. evaluates lifecycle and due reminders;
5. reconciles the rolling ntfy queue;
6. prepares attachment snapshots for eligible events;
7. sends ntfy requests and records delivery/dedupe state;
8. updates weather, astronomy, personal briefing, and heartbeat state;
9. drives the attention output boundary.

LaunchAgents keep the Mac application and watcher available at login. They may
be restarted independently while preserving their shared JSON contracts.

## 9. Weather, astronomy, and location

### Weather

Weather is fetched only when its configured local briefing is due. The result
is normalized and cached. Failed fetches remain eligible for bounded retry and
do not create a second scheduler. Weather is contextual information, not part
of the personal-event source of truth.

### Astronomy

Astronomy is calculated locally using Skyfield/JPL data for a rolling horizon.
The schedule contains Sun and Moon events, phases, trends, day/night facts, and
explicit no-event states. Astronomy notifications are independently scheduled;
they do not mutate personal events.

### Location

Location stores a city or validated custom coordinates plus an IANA timezone.
Changing location invalidates derived weather/astronomy data and causes the
watcher to regenerate it before using the new schedule.

## 10. iPhone Shortcut architecture

Shortcuts are adapters at two boundaries. They are deliberately not a cloud
database, scheduler, or business-logic authority.

### `Blink` — CREATE adapter

```text
receive direct/Share input
  -> distinguish no input / one attachment / too many attachments
  -> collect and validate Title, Description, Date, Time, Importance
  -> collect integer Reminders
  -> collect independent integer Blinker
  -> normalize explicit-offset date/time
  -> build CREATE_EVENT v1 payload
  -> write .event.json
  -> write .ready last
```

Contract highlights:

- Title is required and nonblank;
- Description is optional and lossless;
- Share Sheet accepts at most one attachment;
- folders are not attachments;
- reminders and Blinker reject negative, fractional, alphabetic, and malformed
  values;
- transport ID is `yyyyMMddHHmmss-<9-digit-random>`;
- `.ready` is the commit marker and is written last.

### `Blink DONE` — completion adapter

```text
blink-done-v1|<event-id>
  -> validate command
  -> build DONE command JSON
  -> write .done.json
  -> write .ready last
```

The importer, not the Shortcut, decides whether the command is new, duplicate,
stale, malformed, or applicable.

### `Blink Files` — read-only attachment adapter

```text
blink-files-v1|<package-id>
  -> validate package ID
  -> Get File: Shortcuts/Blink_Acceptance/ToPhone
  -> Get Contents: Folder -> List[File]
  -> require exact .ready and manifest
  -> filter package prefix <package-id>__
  -> Choose from Attachments
  -> Quick Look selected file
```

The production path is flat because iOS Shortcuts has a typed boundary between
the folder returned by `Get File` and the list returned by `Get Contents`.
Filtering the shared flat root prevents unrelated packages and technical
markers from reaching the chooser.

## 11. iCloud transport contracts

The iCloud Shortcuts container is a mailbox, not canonical storage.

### Mac → iPhone attachment package

```text
ToPhone/
  <package-id>.manifest.json
  <package-id>__01__<safe-basename>
  <package-id>__02__<safe-basename>
  <package-id>.ready
```

The package ID is deterministic for event/reminder identity. The manifest
contains package identity, event/reminder identity, ordered filenames, sizes,
and SHA-256 checksums. The `.ready` marker is written last. A delivered
snapshot is immutable for that reminder occurrence; queued snapshots may be
refreshed from current canonical attachments.

### iPhone → Mac command package

The CREATE and DONE Shortcuts write into `ToMac`. The importer requires a
complete validated package and a final `.ready` marker. Incomplete, malformed,
duplicate, or untrusted commands are quarantined or ignored according to the
mailbox contract.

## 12. ntfy notification contract

ntfy receives a plain-text message body plus metadata headers. It does not
receive an event JSON envelope or attachment bytes.

For an event with files, the notification contains:

- human-readable title/body and a paperclip indicator;
- optional `Done` action with Event ID;
- `Files` action with Package ID.

The Files action is a `shortcuts://run-shortcut` URL. It contains the Shortcut
name and package identifier, not an absolute iCloud path. The iPhone Shortcut
has the logical Shortcuts-container path compiled into its own action.

## 13. Security model

### Protected boundaries

- Attachment bytes stay in the user's local event store and iCloud package;
- ntfy receives metadata and action identifiers, not attachment contents;
- absolute local paths and Apple account credentials never enter payloads;
- public Git history excludes private runtime data, event files, topics, and
  attachment bytes;
- Shortcuts accept only versioned, validated command formats.

### Trust assumptions

The ntfy topic behaves like a bearer identifier unless server-side
authentication is configured. Anyone who learns it may be able to subscribe or
publish. Therefore event titles, descriptions, dates, and action URLs should
be treated as visible to topic participants. The package ID is an identifier,
not a secret, and must never be treated as an authorization token.

### Operational rule

Use TLS, protect the topic, avoid placing secrets in event text, and use a
controlled/authenticated ntfy deployment when event metadata or notification
actions are sensitive.

## 14. Development and verification model

The simulator is a development/test harness, never a runtime dependency.

```text
Apple Shortcuts semantics
  -> inspect complete physical tree/oracle
  -> run role simulator/profile
  -> run focused and full tests
  -> make minimal physical Shortcut edit
  -> GUI save and iCloud sync
  -> verify complete iPhone tree
  -> perform only Apple-specific physical acceptance
```

The three simulators model the same meaningful blocks as their physical roles:

| Role | Simulator verifies | Physical-only boundary |
|---|---|---|
| CREATE | validation, branches, variables, JSON, filenames, marker order | Share Sheet, iOS prompts, iCloud sync |
| DONE | command validation, JSON, filenames, marker order | ntfy action launch, iCloud import |
| Files | package ID, typed file boundary, filtering, chooser input | iCloud materialization, Quick Look, ntfy launch |

## 15. Module dependency matrix

| Module | May depend on | Must not own |
|---|---|---|
| SwiftUI/Core | domain contracts, local stores | ntfy sending, scheduling |
| `agenda_store` | attachment helpers, timing values | network delivery |
| `attachment_store` | filesystem primitives | event lifecycle decisions |
| `weather_store` | HTTP client, location contract | personal event writes |
| astronomy generator | location, Skyfield/JPL | ntfy requests |
| `notification_format` | event/payload values | filesystem mutation |
| `to_phone_store` | attachment store, filesystem | iPhone UI decisions |
| `mailbox_importer` | agenda/attachment stores | notification sending |
| `ntfy_schedule` | pure event/payload values | HTTP side effects |
| `watcher` | all orchestration services | alternate source of truth |
| Shortcut simulators | pure contracts and test fixtures | runtime files, GUI, iCloud |

## 16. Mandatory test matrix

| Area | Required cases |
|---|---|
| Event persistence | create, edit same ID, duplicate, delete, atomic failure recovery |
| Lifecycle | Upcoming, Active, Done, History, idempotent completion |
| Timing | explicit offsets, presets, zero, custom integer, negative/fraction rejection |
| Text | Unicode, emoji, quotes, backslashes, multiline paragraphs |
| Attachments | no file, one file, PDF/image, folder rejection, safe basename |
| CREATE Shortcut | direct input, one Share item, more than one item, `.ready` last |
| DONE Shortcut | valid command, malformed ID, replay, stale command |
| Files Shortcut | exact package, foreign package, missing/duplicate markers, two-file chooser |
| Notifications | metadata, tags, action encoding, dedupe, delayed delivery |
| Weather | due time, cache, failure retry, timezone change |
| Astronomy | schedule horizon, phases, no-event states, location regeneration |
| Runtime | launch agent, heartbeat, sleep gap, restart, locked files |
| Release | focused suite, full Python suite, Swift runner, plist lint, diff check |

## 17. Programmer change rules

Before changing behavior:

1. identify the owning module and contract;
2. preserve the Mac source-of-truth boundary;
3. update the relevant simulator/profile before changing a Shortcut;
4. add or update matrix cases;
5. make the smallest reversible implementation change;
6. verify runtime state and restart only the affected process;
7. update authoritative documentation and create a coherent Git checkpoint.

Never fix a Shortcut symptom by adding a second scheduler, second sender,
hidden cloud state, or unvalidated coercion. Never treat an old notification,
test Shortcut, or stale iCloud snapshot as current canonical state without
checking its identity and delivery status.

## 18. Repository entry points

- `README.md` — quick start and operator commands;
- `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md` — binding current contracts;
- `docs/implementation/BLINK_REMAINING_ROADMAP.md` — delivery roadmap;
- `docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md` — physical Shortcut tree evidence;
- `watcher.py` — runtime orchestration;
- `app/BlinkSwiftUI` — native Mac application package;
- `app/*_shortcut_simulator.py` — Shortcut development harnesses;
- `test_*.py` — executable Python contract tests.
