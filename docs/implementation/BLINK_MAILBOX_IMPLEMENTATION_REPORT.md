# Blink Mailbox Implementation Report

## Current status

PHASE 1 COMPLETE  
PHASE 2A COMPLETE (parser/state foundation)
PHASE 2B COMPLETE (temporary-root canonical mutation/recovery)
PHASE 3 COMPLETE (opt-in in-process watcher worker; production mailbox remains disabled)
PHASE 4A COMPLETE (Mac ntfy DONE action support; disabled by default)
PHASE 4B COMPLETE (real iPhone ntfy DONE action accepted)
PHASE 5 COMPLETE (manual `Blink Create Test` migration and acceptance passed)
PHASE 6 COMPLETE (controlled acceptance passed; production mailbox remains disabled)
PHASE 7 COMPLETE (debounced external agenda refresh; 30-second polling retained)

The authoritative post-Phase-7 roadmap is
[`BLINK_REMAINING_ROADMAP.md`](BLINK_REMAINING_ROADMAP.md). Stage 0
documentation/contract reconciliation is complete; Stage 1 manual acceptance
of the latest Done work is complete. Production attachment viewing is now the
current gated stage; personal
Today Morning Briefing, the physical USB adapter, numeric limits, production
cutover, and production soak remain future gates.

### Stage 1 Early Done acceptance — initial observation and retest

The first owner-reported Early Done attempt for the temporary event
`stage1-early-done-20260912` appeared to flash the UI and remove the row from
Upcoming, but the persisted record remained `done: false` with
`done_at: null`. Its original future `start` was unchanged. Inspection of the
actual agenda and the Swift `EventSnapshot`/History filter found no exclusion
for completed future-start events; the completion path and existing regression
coverage already route `done == true` records directly to History. The
observed failure therefore represented an action that was not applied to that
event (a transient/stale UI interaction), not a persistence or History-model
defect. No production code change was required.

Codex then created and completed the new temporary event
`stage1-early-done-persist-20260912` through the real installed Blink UI. The
row disappeared from Upcoming, appeared immediately in History, persisted
`done: true`, recorded `done_at: 2026-09-12T23:46:34-07:00`, and preserved its
future `start: 2026-09-15T12:00:00-07:00`. The result remained correct after
reload, confirming the contract and ruling out a stale-snapshot persistence
bug. The temporary Codex-created acceptance records are not production data.

### Stage 1 remote DONE acceptance — controlled result

After the Mac retest, Codex sent exactly one real ntfy notification with
`BLINK_NTFY_DONE_ACTION_ENABLED=1` and the temporary target
`BLINK_NTFY_DONE_SHORTCUT_NAME="Blink DONE Test"`. The action carried
`blink-done-v1|event-3b6bfc08-f47a-43e8-9d1a-fd7a7dee1c35`; ntfy accepted the
request with HTTP 200 and no `clear=true`. The owner tapped the iPhone action
once, producing
`20260912234913-449637111.done.json` plus its matching `.ready` in the
acceptance inbox. Codex processed that package once against
`Blink_Acceptance/ToMac` without enabling the watcher mailbox flags: result
`applied`, one confirmation delivery succeeded, and the exact package was
removed only after the agenda commit. The event now persists
`done: true` with `done_at: 2026-09-12T23:49:47.778110-07:00`; its original
scheduled start remains unchanged. The acceptance inbox is empty, production
mailbox flags remain OFF, and `Blink_Production/ToMac` remains unused.

The original ntfy notification was not cleared or modified. Duplicate/no-op
silence and the one-confirmation rule remain covered by the existing focused
mailbox/notification tests; no second iPhone action was generated.

### Stage 1 Dock / Attention visual acceptance — PASS

Codex created three temporary past-start active events with green, yellow, and
red attention levels and inspected the installed Blink UI. The Today tab and
active rows showed the highest-priority state (red, then yellow after red was
completed, then green after yellow was completed). Completing each event via
the real row `Done` control removed its contribution immediately; after the
last completion Today showed no active events and the tab/Dock attention
presentation returned to neutral. Persisted `done_at` values were recorded for
all three, and the completed future-event retest confirmed that a future
completion does not reactivate attention after reload. The temporary
Codex-created records were removed after verification; no production UI or
device protocol was changed.

## Approved architecture

The approved baseline is recorded in
[`docs/design/BLINK_MAILBOX_IMPORTER_DESIGN.md`](../design/BLINK_MAILBOX_IMPORTER_DESIGN.md):
one existing watcher process, one in-process mailbox worker thread, a shared
short Swift/Python POSIX `flock`, iCloud inbox only at
`Blink_Production/ToMac`, local journal/quarantine/runtime/indefinite dedupe
ledger, Mac-generated event IDs, DONE `event_id` only, non-recurring CREATE v1,
and the existing local attachment contract.

## Completed work

### Phase 1 — persistence safety

- Added stable `<Blink root>/agenda.lock` protocol.
- Added Python `app.agenda_store.agenda_lock()` using `fcntl.flock`.
- Made Python agenda load-time repairs and atomic saves lock-aware.
- Added Swift `AgendaFileLock` using Darwin `flock`.
- Wrapped every audited Swift agenda writer: save, complete, attention,
  enabled, delete, add files, add JPEG, and load-time repair.
- Preserved atomic temp-write/replace behavior.
- Added Python concurrent-writer regression and Swift/Python interoperability
  test.
- Added `agenda.lock` to `.gitignore`.

### Phase 2A — importer core

- Added `app/mailbox_importer.py` with strict native/UUID-compatible transport-ID package discovery,
  `.ready` semantics, DONE/CREATE v1 parsing, and pending-sync vs malformed
  classification.
- CREATE v1 parser accepts user intent only: non-recurring, explicit timezone,
  reminder intent, attention level, and `blinker_intent.minutes_before`.
- Added regular-file/symlink/path/basename safety checks, multiple-attachment
  rejection, and unrelated-file isolation.
- Added local journal records, restart-readable pending journal state, atomic
  indefinite processed transport-ID tombstones, local staging, and exact-package local
  quarantine primitives.
- No watcher call, iCloud production root, agenda mutation, ntfy action, or
  Shortcut change was added.

### Phase 2B — canonical event transactions

- DONE applies `agenda_store.complete_event` under the shared lock, with safe
  `noop_done` and `stale_event` results and the existing successor guard.
- CREATE reuses `build_personal_event`/`upsert_event`, generates a Mac
  `event-<UUID>` ID, persists `mailbox_transfer_id`, and keeps recurrence
  disabled for v1.
- Attachments are staged and fsynced outside the lock, copied into the
  event-ID owner folder inside the lock, and represented by the physical-file
  manifest. Journal recovery repairs a missing ledger and removes safe orphan
  staging/finalization folders.
- Processed transport-ID tombstones retain durable result/event metadata indefinitely.

### Phase 3 — watcher worker integration

- Added one daemon mailbox worker thread to the existing watcher loop. The
  scheduler never joins or waits for it; an in-flight worker prevents a second
  iteration and reports stalled state.
- Worker exceptions are isolated, diagnostics are best-effort, and later
  iterations retry. Production remains disabled unless both explicit
  `BLINK_MAILBOX_ENABLED` and `BLINK_MAILBOX_ROOT` environment settings are
  supplied; no real iCloud root is configured.
- Bounded scans call the Phase 2B transaction path and remove exact transport
  files only after local commit.
- macOS iCloud placeholder reads that return `Errno 11 (Resource deadlock
  avoided)` are classified as `PENDING_SYNC`; the worker leaves the exact
  package in place and retries after the bytes become local instead of
  quarantining it as malformed. Attachment staging and transport cleanup use
  the same boundary.

### Phase 4A — Mac ntfy DONE action support

- Added one canonical `build_done_action`/`build_event_payload` path reused by
  direct delivery and rolling queue scheduling.
- Eligible personal events use the versioned text input
  `blink-done-v1|<event_id>` and the production Shortcut name `Blink DONE`;
  URL/query components are encoded with the standard query encoder.
- The ntfy `Actions` header is emitted only when
  `BLINK_NTFY_DONE_ACTION_ENABLED=1` (or equivalent true value) is explicitly
  set. It is independent of mailbox enablement and defaults off.
- Queue payload hashes and watcher reconciliation signatures include action
  metadata. Weather, Astronomy, system, completed, and non-personal events do
  not receive the action. No `clear=true`, command ID, or `occurrence_id` is
  generated.

### Phase 4B preparation — controlled Shortcut-name override

- Production/default Shortcut name remains `Blink DONE`.
- For controlled manual acceptance only, `BLINK_NTFY_DONE_SHORTCUT_NAME` may
  temporarily provide a non-empty printable name such as `Blink DONE Test`.
  Missing, empty, whitespace-only, control-character, or overlong values fall
  back to `Blink DONE`.
- `BLINK_NTFY_DONE_ACTION_ENABLED` remains a separate opt-in flag and still
  defaults off. The input contract remains `blink-done-v1|<event_id>` and the
  canonical direct/queued action builder is unchanged.

### Phase 4B manual acceptance finding — Shortcuts URL encoding

- Real iPhone acceptance showed that form-style query encoding is incorrect for
  the custom `shortcuts://` scheme: `Blink+DONE+Test` was treated literally as
  a shortcut name, so iOS could not find `Blink DONE Test`.
- The canonical builder now uses standards-compliant percent encoding with
  spaces as `%20`, producing `name=Blink%20DONE%20Test` (and
  `name=Blink%20DONE` for the production default). Reserved characters in the
  `blink-done-v1|<event_id>` input remain percent-encoded; no values are
  concatenated unescaped. Direct and queued payloads continue to share this
  builder, and `clear=true` remains absent.

### Phase 4B completion — real iPhone acceptance

- One controlled Mac notification was sent with temporary
  `BLINK_NTFY_DONE_ACTION_ENABLED=1` and
  `BLINK_NTFY_DONE_SHORTCUT_NAME="Blink DONE Test"`.
- The real iPhone displayed the green `Done` button. The user tapped it, and
  the existing `Blink DONE Test` Shortcut ran successfully with
  `blink-done-v1|EVENT123`.
- The feasibility inbox received the exact pair
  `20260912163022-101411924.done.json` and
  `20260912163022-101411924.ready`. The JSON contained version `1`, type
  `DONE`, command ID `20260912163022-101411924`, and event ID `EVENT123`.
- This proves the controlled chain Mac ntfy action → iPhone tap →
  `shortcuts://` URL → Shortcut → native timestamp-random command ID → DONE
  package + `.ready`. The importer was not enabled and no feasibility files
  were consumed or deleted.

### Phase 4B preparation — Shortcuts-native transport IDs

- Real Apple Shortcuts does not provide a native Generate UUID action, so the
  production phone-generated transport ID is
  `<yyyyMMddHHmmss>-<9-digit-random>`, for example
  `20260912154532-482193775`.
- This combined value is transport/dedupe identity only; it is neither an
  event ID nor the event start time. The same strict policy applies to
  `command_id`, `transfer_id`, package stems, attachments, `.ready`, journal,
  ledger, and quarantine ownership. UUIDv4 remains accepted for backward
  compatibility.
- DONE ntfy input remains `blink-done-v1|<event_id>`.

### Phase 7 — fast external agenda refresh

- Added `AgendaDirectoryObserver`, a macOS-native `DispatchSource` watcher for
  the parent directory containing `agenda.json`; it never holds the old file
  inode or descriptor.
- Directory events are debounced and filtered by the current agenda inode,
  size, and modification-time signature before invoking the existing SwiftUI
  `reload()` path. Unrelated files do not trigger a reload.
- The existing 30-second polling timers remain enabled as the correctness
  fallback. If the observer cannot open its parent directory, it reports a
  non-fatal failure and polling continues. The observer performs no writes and
  introduces no importer-to-GUI IPC.
- External atomic replacement therefore refreshes Today/Upcoming/History and
  Search through the normal snapshot path, including Attention and Dock
  outputs. Ordinary GUI saves produce at most one debounced refresh and do not
  recurse.

### Phase 5 Mac-side arbitrary-minute support

- The importer contract already accepts any non-negative integer reminder list
  and one non-negative integer blinker value; duplicate reminders are
  canonicalized and phone-owned lifecycle fields remain rejected.
- SwiftUI now preserves every valid reminder offset during save instead of
  dropping values merely because they do not match a preset. Existing presets
  remain available, while custom reminder rows and custom blinker values can
  be entered as whole minutes. `0` remains `At time` and is never duplicated
  as a custom row.
- Swift round-trip coverage includes imported `[3, 0]`, custom reminder `17`,
  custom blinker `3`/`240`, and the existing observer save-loop contract.

## Phase 5 — iPhone `Blink Create Test` manual acceptance

- The owner migrated the existing `Blink Create Test`; no new production
  Shortcut was created. `Blink Create Test BACKUP` remains untouched.
- The active Shortcut targets
  `/Users/vitaliiprotsiuk/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/ToMac`.
- Manual acceptance passed for CREATE without attachment, with image, and with
  PDF. The observed packages were:
  `20260912192619-650719048.event.json` + `.ready` (no attachment),
  `20260912194513-228316619.event.json` + matching
  `.attachment.jpeg` + `.ready`, and
  `20260912194754-657491603.event.json` + matching
  `.attachment.pdf` + `.ready`.
- Arbitrary integer reminders and blinker values passed, including
  `reminder_intent.offsets_minutes_before: [3, 0]`, `17`, and `240`, with
  `blinker_intent.minutes_before: 0`, `3`, and `240`. Empty Description was
  accepted; whitespace-only Title and invalid reminder input were rejected on
  the phone and are independently rejected by the Mac importer.
- `.ready` remained the final marker. A deliberately past event package was
  created successfully; its post-import lifecycle remains a Phase 6 check.

## Phase 6 preparation — clean acceptance inbox

- Historical Phase 5 artifacts were moved reversibly (25 entries, filenames
  preserved) to `/Users/vitaliiprotsiuk/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/Archive/Phase5-20260912211629`.
- `Blink_Acceptance/ToMac` is now empty and remains the active Shortcut target.
- Production mailbox remains disabled: `BLINK_MAILBOX_ENABLED` and the
  mailbox root are not configured; `Blink_Production/ToMac` is unused.

### Phase 6 controlled enable/disable procedure (prepared, not executed)

1. Confirm `Blink_Acceptance/ToMac` is empty and keep the existing watcher as
   the only scheduler.
2. After explicit owner authorization, set the per-user LaunchAgent
   environment for one controlled run and restart that same watcher:
   `launchctl setenv BLINK_MAILBOX_ENABLED 1`,
   `launchctl setenv BLINK_MAILBOX_ROOT "/Users/vitaliiprotsiuk/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/ToMac"`,
   then `launchctl kickstart -k gui/$(id -u)/com.vitalii.blink.watcher`.
3. After the acceptance window, immediately run
   `launchctl unsetenv BLINK_MAILBOX_ENABLED`,
   `launchctl unsetenv BLINK_MAILBOX_ROOT`, and kickstart the same label again
   so the worker returns to its disabled default. Verify with
   `./status_watcher.command` and a final empty-inbox check.

This procedure is documented for the future controlled test only; none of its
enable commands were run in this checkpoint.

## Phase 6 controlled acceptance — result

- **Phase 6A CREATE without attachment — PASS.** With the one-shot worker
  pointed only at `Blink_Acceptance/ToMac`, the native package
  `20260912214025-961934815.event.json` plus `.ready` was consumed. Blink
  created event `event-3b6bfc08-f47a-43e8-9d1a-fd7a7dee1c35` with the exact
  title/description/start, reminders `[3, 0]`, yellow attention, blinker `3`,
  `enabled=true`, `requires_done=true`, `done=false`, `recurrence=null`,
  Mac-owned tags/defaults, and preserved `mailbox_transfer_id`. The open Blink
  GUI showed the event in Upcoming without an app restart.
- **Phase 6B CREATE with PDF — PASS.** The package
  `20260912214413-360011007.event.json` plus matching
  `20260912214413-360011007.attachment.pdf` and `.ready` was initially held
  as `PENDING_SYNC` while the iCloud files were `dataless`. After the PDF was
  opened once in Preview and became local, the worker committed event
  `event-8acec3e8-352e-4300-813c-5a31efdaa0d7`, moved the 262,885-byte file
  into its event-ID owner folder, preserved the original display name
  `234896478`, set the physical-file manifest to `count=1/has_files=true`,
  and removed the mailbox package only after commit. The GUI showed the event
  in Today/Active with `📎 1` and no restart.
- **Phase 6C past-event behavior — OBSERVED.** The PDF event had start
  `2026-09-12T21:44:00-07:00`, already in the past when loaded. Because it was
  enabled, unfinished, and `requires_done=true`, Blink classified it as
  `Today → Active` (not History), retained yellow Attention, and kept the
  configured 5-minute blinker lead. This is the current lifecycle behavior;
  no redesign was introduced.
- **Real DONE acceptance — PASS.** The controlled ntfy request for event
  `event-8acec3e8-352e-4300-813c-5a31efdaa0d7` was accepted with the encoded
  `Blink DONE Test` action and no `clear=true`. After the owner tapped `Done`,
  package `20260912221340-109486748.done.json` plus `.ready` arrived in the
  acceptance inbox. The worker applied it under the agenda lock, recorded
  `result=applied` in the journal/processed ledger, removed the exact package
  after commit, and persisted the event as `done=true`. The acceptance inbox
  is empty again; historical feasibility files remain untouched.
- **Early Done — COMPLETE.** Today (including its future same-day section) and
  Upcoming rows expose the existing physical/context-menu `Done` action for
  eligible unfinished personal events. Future-start completion preserves the
  original `start`, records the actual local `done_at`, clears attention, and
  classifies the event directly into History. Swift and Python completion are
  idempotent; repeated local or remote DONE is a no-op and does not create a
  second recurrence successor.
- **Remote DONE confirmation — COMPLETE.** After a newly applied remote DONE
  commits under the agenda lock, the mailbox worker sends one short ntfy
  confirmation titled `✓ Done — <event title>`, with optional description and
  `Scheduled: <local date/time>` in the body. It has no action button and never
  adds `clear=true`. Ledger replays, `noop_done`, `stale_event`, malformed,
  pending, and failed commands remain silent. A confirmation HTTP/network
  failure is diagnostic-only and never rolls back the committed completion;
  package cleanup still follows the normal post-commit boundary.
- The controlled mailbox was returned to **OFF** immediately after the DONE
  acceptance. `Blink_Production/ToMac` remains unused and the acceptance inbox
  is empty.

## Phase 5 — historical iPhone `Blink Create Test` migration checklist

This is the original preparation checklist retained for traceability. It does
not describe pending work; the actual manual implementation and acceptance
above supersede it where details differ. It does not enable the importer or
authorize production `Blink_Production/ToMac`.

### Phase 5 preparation — clean acceptance inbox

- Acceptance inbox: `/Users/vitaliiprotsiuk/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/ToMac`
- The folder is inside the verified private Apple Shortcuts iCloud container;
  it was verified empty before migration and is empty again after archival.
- `BLINK_MAILBOX_ENABLED` and the mailbox/importer root remain unset; the
  historical feasibility inbox is untouched and `Blink_Production/ToMac`
  remains unused.

### Existing blocks that remain unchanged

1. Keep the existing `Shortcut Input` entry path so direct launch remains
   valid.
2. Keep the Share Sheet input types limited to `Images`, `PDFs`, and `Files`.
3. Keep `Ask Where To Save = OFF` and use the clean acceptance destination
   `Blink_Acceptance/ToMac`.
4. Keep the final stop/return behavior after the package is completely written.

### Blocks to delete

1. Delete the old random-only ID block and every use of its bare 9-digit value
   as a filename stem.
2. Delete feasibility-only JSON keys `event_datetime`, `priority`,
   `blink_datetime`, `occurrence_id`, and every Mac-owned lifecycle field.
3. Delete any branch that tests whether an empty direct-launch Text “has any
   value” as an attachment; it created the historical zero-byte artifact.

### Blocks to modify

1. Modify the input/attachment branch to use the Shortcuts boolean
   `HasAttachment is true`. Direct launch must take the no-attachment branch;
   Share Sheet launch may take the one-attachment branch.
2. Replace old prompts with the exact prompts below and map their outputs to
   the production v1 field names.
3. Change the date formatter to emit an offset-bearing ISO-8601 `start` value
   and an equivalent `created_at` value.
4. Change the JSON construction, attachment basename, and `.ready` marker to
   the exact shapes and write order below.

### New blocks to insert, in this order

1. **Current Date** → **Format Date** with custom format
   `yyyyMMddHHmmss` (device local time).
2. **Random Number** between `100000000` and `999999999`.
3. **Text** combine the formatted timestamp, a literal `-`, and the random
   number: `yyyyMMddHHmmss-<9-digit-random>`. Store it as `transfer_id` and
   never use only one component as identity.
4. **Ask for Input — Text** with prompt `Title` (required; stop if empty).
5. **Ask for Input — Text** with prompt `Description (optional)`; preserve
   multiline text and use an empty string when omitted.
6. **Ask for Input — Date** with prompt `Event start date and time`.
7. **Format Date** for that date using custom format
   `yyyy-MM-dd'T'HH:mm:ssXXX`, 24-hour time, and the device’s current time
   zone. This is the explicit-offset `start` string; `XXX` yields values such
   as `-07:00`.
8. **Choose from Menu — Attention level** with exact values `green`,
   `yellow`, and `red`; default to `green`. Store the selected lower-case value
   as `attention_level`.
9. **Ask for Input — Text** with prompt
   `Reminder offsets in minutes before start (comma-separated, e.g. 30,0)`.
   Split on commas, trim each token, convert to integers, reject negatives or
   an empty list, remove duplicates, and emit
   `reminder_intent.offsets_minutes_before`.
10. **Ask for Input — Number** with prompt
    `Blinker lead time in minutes before start (default 0)`. Reject negatives
    and emit `blinker_intent.minutes_before`; `0` is the canonical `At event`
    default.
11. **Current Date** → **Format Date** with the same
    `yyyy-MM-dd'T'HH:mm:ssXXX` format for `created_at`.
12. Build the JSON object shown below, without adding Mac-owned fields.
13. If `HasAttachment is true`, require exactly one regular file, derive its
    non-empty extension, create the attachment object, and write the matching
    attachment file. If there is no attachment, omit the attachment object.
14. Write the JSON file, then the optional attachment file, then the `.ready`
    marker last. Do not write `.ready` before all preceding files are complete.

### Exact final prompts and JSON

The user-facing prompts are exactly: `Title`; `Description (optional)`;
`Event start date and time`; `Reminder offsets in minutes before start
(comma-separated, e.g. 30,0)`; `Blinker lead time in minutes before start
(default 0)`. Attention is selected from the exact green/yellow/red menu.

The final no-attachment JSON is:

```json
{
  "version": 1,
  "type": "CREATE_EVENT",
  "transfer_id": "20260912154532-482193775",
  "title": "Call the contractor",
  "description": "Optional multiline text",
  "start": "2026-09-13T09:00:00-07:00",
  "reminder_intent": {"offsets_minutes_before": [30, 0]},
  "attention_level": "green",
  "blinker_intent": {"minutes_before": 0},
  "created_at": "2026-09-12T18:30:00-07:00"
}
```

With one attachment, add exactly:

```json
"attachment": {
  "basename": "20260912154532-482193775.attachment.pdf",
  "original_filename": "contract.pdf"
}
```

The native transport ID is exactly `yyyyMMddHHmmss-<9-digit-random>` where the
random value is inclusive from `100000000` through `999999999`. Filenames are
exactly `<transfer_id>.event.json`, optional
`<transfer_id>.attachment.<extension>`, and `<transfer_id>.ready`; `.ready` is
always last. The combined ID is transport/dedupe identity only, never the
event ID or event start time.

### Mapping and Mac-owned fields

| Shortcut value | Production v1 field | Rule |
|---|---|---|
| Title | `title` | Required, trimmed, non-empty. |
| Description | `description` | Optional string; preserve newlines. |
| Event start date and time | `start` | ISO-8601 with explicit device UTC offset. |
| Reminder offsets | `reminder_intent.offsets_minutes_before` | Non-empty, non-negative integer list; parser sorts unique values. |
| Attention menu | `attention_level` | Exactly `green`, `yellow`, or `red`. |
| Blinker lead time | `blinker_intent.minutes_before` | Non-negative integer; canonical default `0`. |
| Current Date | `created_at` | Audit metadata only; never scheduling time. |
| Optional file | `attachment` | `basename` plus display-only `original_filename`; no bytes in JSON. |

The Mac supplies `id` (`event-<UUID>`), `enabled=true`, `requires_done=true`,
`done=false`, `done_at=null`, `tags:["calendar"]`, `priority:"default"`,
`recurrence=null`, `mailbox_transfer_id`, and the physical attachment manifest.
The phone MUST NOT send or override those fields, nor send `event_id`,
`reminders_minutes_before`, `blinker_minutes_before`, recurrence, tags, or
absolute `blink_datetime`.

### Direct launch, Share Sheet, and zero-byte protection

Direct launch has no attachment and must write only the JSON plus final `.ready`.
Share Sheet launch accepts one image, PDF, or regular file and writes one
matching attachment. More than one attachment must stop without writing a
package; a file without a usable extension must also stop. The attachment
branch must be guarded by `HasAttachment is true`, so an empty direct-launch
Text can never create `<id>.attachment.` or any zero-byte attachment.

## Files changed

- `.gitignore` — ignore agenda lock and mailbox runtime state.
- `app/agenda_store.py` — shared Python lock and lock-aware agenda persistence.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AgendaFileLock.swift` — Darwin
  implementation interoperable with Python `flock`.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift` — shared lock around
  all Swift agenda read/modify/write and repair paths plus lossless arbitrary
  reminder-minute normalization.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift` — custom
  whole-minute reminder/blinker controls while preserving presets.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AgendaDirectoryObserver.swift` —
  parent-directory DispatchSource observer with signature filtering and debounce.
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift` — Swift lock,
  Python interoperability, and custom-minute round-trip tests.
- `test_agenda_store.py` — Python contention and lost-update regression tests.
- `app/mailbox_importer.py` — Phase 2A parser and local transport state
  primitives plus Phase 2B transactions/recovery and bounded scans.
- `app/attachment_store.py` — staged-file finalization helper using the local
  attachment contract.
- `watcher.py` — opt-in single mailbox worker and non-blocking loop handoff.
- `app/notification_format.py` — canonical DONE action and notification payload.
- `app/ntfy_schedule.py` — queued payload reuse with action metadata.
- `test_mailbox_importer.py` — Phase 2A/2B temporary-root tests.
- `test_watcher.py` — worker stall, single-flight, exception, and retry tests.
- `test_notification_format.py`, `test_ntfy_schedule.py` — action, encoding,
  eligibility, and queue-signature coverage.
- `docs/design/BLINK_MAILBOX_IMPORTER_DESIGN.md` — approved-baseline wording
  cleanup only.
- `docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md` — this
  persistent checkpoint.
- `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`,
  `docs/HANDOFF.md`, `CODEX_NEXT_THREAD_PROMPT.md`,
  `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md` — synchronized
  implementation status and Phase 5/6 mailbox contract.

## Tests

- `.venv/bin/python -m unittest -q` → 195 tests passed.
- `.venv/bin/python -m unittest -q test_agenda_store test_mailbox_importer
  test_notification_format test_watcher test_ntfy_schedule` → 152 tests passed,
  including iCloud placeholder `PENDING_SYNC` and remote confirmation
  regressions.
- Previous Phase 4 notification/watcher focused suite remains covered by the
  full run; its prior checkpoint was 88 passing tests.
- `swift run BlinkSwiftUITestRunner` → all Swift store/UI tests passed,
  including Python `flock` interoperability and the Phase 7 atomic-replace,
  debounce, unrelated-write, save-loop, and observer-failure regressions.
- `swift build -c release` → build completed.
- `.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py`
  → passed.
- `git diff --check` → passed at checkpoint.

## Runtime/manual verification

- `./status_watcher.command` → existing watcher healthy with fresh heartbeat;
  no mailbox integration was enabled.
- Release Swift executable was rebuilt, copied to `Blink.app`, and the app was
  relaunched after the lock change.
- Phase 2A tests use only temporary mailbox/Blink roots.
- Phase 4B manual iPhone acceptance passed. The verified chain is:
  `EVENT123` → `blink-done-v1|EVENT123` →
  `shortcuts://run-shortcut?name=Blink%20DONE%20Test&input=text&text=blink-done-v1%7CEVENT123` →
  `view, Done, <encoded-shortcut-url>` →
  `20260912163022-101411924.done.json` + `.ready`.
- The controlled flags were one-shot only; production default remains
  `Blink DONE`, and `BLINK_NTFY_DONE_ACTION_ENABLED` remains off by default.
- Manual UI check after the release deploy opened New Event, added reminder
  `17`, and set Blinker `3`; the editor visibly showed `Custom — 17 min before`
  and `Custom — 3 min before`. The draft was not saved.

## Known risks / blockers

- Phase 1 changes are committed, but the existing live watcher/app may need the
  normal LaunchAgent restart cycle after future release deployment.
- Real production iCloud access and mailbox processing remain intentionally
  disabled. The Mac-side DONE action remains opt-in by default; no Shortcut
  or feasibility package was modified by the Mac test.

## Open owner decisions / gates

- Numeric transport size/package caps remain to be measured and selected.
- The DONE acknowledgement decision is final: the originating notification
  remains unchanged; a newly applied remote DONE emits one separate short
  confirmation without an action button or `clear=true`; repeats/no-ops,
  stale, malformed, pending, and failed commands are silent.

## Next implementation tasks

1. Keep the production mailbox disabled and never point the importer at the
   archived or historical feasibility inbox.
2. Stage 1 of `BLINK_REMAINING_ROADMAP.md` is current: perform owner-controlled
   manual acceptance of Early Done, remote confirmation, and Dock/Attention;
   stop before Stage 2.
3. Keep the numeric package/worker limits as a pre-production gate.

## Last checkpoint

2026-09-12. Phase 1 commit: `98753a8 Add shared Blink agenda locking`. Phase
2A commit: `421963d Add Blink mailbox importer core`. Phase 2B commit:
`aa50f96 Implement Blink mailbox event transactions`. Phase 3 commit:
`df50af7 Integrate Blink mailbox worker with watcher`. Additional Phase 2B
coverage: `5cc53de Add mailbox iteration coverage`. Worker diagnostics:
`47a381b Expand mailbox worker diagnostics`. Phase 4A:
`a8c682b Add Blink ntfy DONE action support`. Phase 4B preparation:
`cf75720 Prepare configurable Blink DONE shortcut name`. Verification fixture:
`05c6b3f Stabilize Swift history test fixture`. Phase 4B URL fix:
`49eaf30 Fix Shortcuts action URL space encoding`. Phase 4B manual acceptance
passed with native DONE package `20260912163022-101411924`. Phase 4B closeout:
`0e19104 Close Phase 4B manual acceptance`. Phase 7:
`16bdf7b Add fast external agenda refresh`. Phase 5 checklist:
`e7037e5 Prepare Phase 5 Create Shortcut checklist`. Phase 5 arbitrary-minute
support and contract tests: `0935e73 Preserve arbitrary mailbox minute values`.
Phase 5 acceptance closeout and Phase 6 inbox preparation:
`04ce992 Close Phase 5 and prepare acceptance inbox`.
Manual custom-minute UI acceptance: `02e1013 Record custom minute UI acceptance`.
Early Done and remote confirmation implementation: `92606d2 Implement Early
Done and remote confirmation`. Documentation sync: `b1b50d3 Document Early Done
confirmation contract`.
