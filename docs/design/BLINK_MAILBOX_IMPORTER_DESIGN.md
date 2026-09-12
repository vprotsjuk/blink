# Blink production Mac-side mailbox importer — design proposal

**Status:** approved architecture baseline; implementation in progress  
**Date:** 2026-09-12 (revision after architecture review)  
**Scope:** production design for iPhone `DONE` and `CREATE_EVENT` over the
private iCloud Shortcuts mailbox.

This document is deliberately a design artifact. It does not change the
production contracts, Shortcuts, `watcher.py`, SwiftUI, `agenda.json`, runtime
files, LaunchAgents, or the feasibility test folders.

### Review revision summary

The second audit confirmed that SwiftUI already polls `agenda.json` every 30
seconds (`ContentView.onReceive`) and refreshes on appearance, so a new
filesystem observer is not required for the baseline design. It also confirmed
that ntfy currently has no action URL at all; the DONE action is a future
formatter/Shortcut contract, not an existing field. The importer execution
model is therefore revised to a bounded worker thread inside the existing
watcher process, while all agenda mutations remain behind one short shared
lock. `Processed`/`Quarantine` are moved out of iCloud in the recommendation,
and CREATE v1 is reduced to user intent rather than an agenda-shaped payload.

## 1. Current architecture findings from real code

The running architecture is:

```text
SwiftUI GUI -> local Blink JSON and attachment folders -> watcher.py
    -> ntfy and the physical USB blinker
```

The authoritative event metadata is local `agenda.json`; attachment bytes are
under `event_data/attachments/<event-id>/`. ntfy is notification transport and
presentation, not storage. `watcher.py` is the only production scheduler,
sender, and long-running delivery process. The iCloud mailbox must remain a
transport queue and must never become a second event store.

The manually verified iCloud root is the private Apple Shortcuts container:

```text
~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents
```

`Blink_Feasibility/ToMac` and `Blink_Feasibility/ToPhone` are owner-maintained
test paths. They are not automatically production paths.

The real code audit found:

| Concern | Current implementation |
|---|---|
| Event model | `BlinkEvent`/`EditableEvent` in `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`; Python normalization in `watcher.py` and transformations in `app/agenda_store.py`. |
| Python event transforms | `app/agenda_store.py`: `build_personal_event`, `upsert_event`, `complete_event`, `build_next_recurring_event`. |
| Swift persistence | `BlinkStore.save`, `complete`, `setAttentionLevel`, `setEnabled`, `delete`, `addFiles`, and `addJPEG` in `Models.swift`. |
| Attachment ownership | Swift `AttachmentWorkspace` and Python `app/attachment_store.py`; production owner is the event ID, never `series_id`. |
| Watcher | `watcher.py` loads and validates agenda, runs weather/astronomy cycles, reconciles ntfy queue, sends due reminders, and owns the long-running loop. It currently does not write event records or scan iCloud. |
| GUI attention | `BlinkAppState.refreshAttention()` loads the last-good snapshot; `AttentionManager` drives `DockAttentionOutput`. |
| Physical blinker | The watcher’s existing event-output path remains the owner. A completed event is excluded from the next watcher delivery/attention calculation; no importer-specific stop path is needed. |
| Atomic writes | Python uses temp + flush/fsync + `os.replace`; Swift uses a temporary URL and atomic `replaceItem`/move. |
| Locking/versioning | No shared `flock`/`fcntl` lock and no compare-and-swap document revision were found. |

## 2. Exact existing Create path

The current normal Mac Create operation is the SwiftUI event-editor path:

1. `ContentView.swift` creates an `EditableEvent` (`EditableEvent.blank()` for
   a new event) and an optional draft `AttachmentWorkspace`.
2. The Save action calls `store.save(savedEvent,
   attachmentWorkspace:draftID:)`.
3. `BlinkStore.save` reads the current `agenda.json`, rejects a history-frozen
   replacement, converts the editable value with `toDictionary()`, and either
   replaces the matching ID or appends a new event.
4. If a draft exists, `AttachmentWorkspace.finalize(draftID:ownerID:)` copies
   staged bytes into `event_data/attachments/<event.id>/` and returns a manifest.
5. The event plus manifest are written with `saveAgendaObject`, which delegates
   to the Swift atomic JSON writer. The draft is discarded only after the
   metadata write succeeds.
6. `ContentView.reload()` and `BlinkAppState.applySnapshot()` refresh the UI and
   Dock attention state. `watcher.py` observes the same local JSON on its next
   cycle and handles normal notifications/blinker timing.

The Python equivalent is a set of pure transformations, not the GUI entry
point: `build_personal_event()` builds a normalized event and `upsert_event()`
merges it into a document. Neither function persists by itself.

## 3. Exact existing Done path

The GUI Done button is in `ContentView.swift` and calls
`store.complete(eventID:)`.

`BlinkStore.complete`:

1. loads the complete `agenda.json` document;
2. finds the exact event `id`;
3. sets `requires_done=true`, `done=true`, and a local ISO `done_at`;
4. checks for an existing successor with
   `recurrence_parent_id == eventID` and `generation == current + 1`;
5. calls the Swift `buildNextRecurringEvent` at most once and appends the
   successor, which has a new `<series_id>-g<generation>` ID and an empty
   attachment manifest;
6. atomically saves the document.

`app/agenda_store.complete_event` implements the same state transition and
successor guard as a Python pure transformation. This is the strongest
currently reusable remote operation, but it is not a shared callable service:
Swift has its own read/modify/write and recurrence implementation.

After GUI completion, reload recalculates `EventSnapshot.attentionState` and
`AttentionManager` drives Dock state to `off` when no eligible event remains.
The watcher skips `done=true` personal events in `process_due_reminders`; its
normal output path therefore stops notification/blinker activity on the next
watcher evaluation. A future importer must invoke the same state transition,
not duplicate those output responsibilities.

## 4. Business-logic reuse point and current blocker

The desired invariant is one Create operation and one Done operation. The
current code does not expose one cross-process implementation:

- Python `agenda_store` has reusable, testable transformations.
- Swift `BlinkStore` owns the GUI persistence and attachment transaction.
- `watcher.py` is Python and cannot call Swift `BlinkStore` directly without
  starting another process or inventing an IPC service.

Therefore the minimum prerequisite before integration is a shared mutation
boundary, not a `remote_create()`/`remote_done()` fork. The recommended
refactor (implementation phase only) is:

1. define one documented event-mutation contract around the existing Python
   transformations and the existing Swift field semantics;
2. add a common advisory lock file and require both Swift and Python writers to
   hold it across read–modify–write and attachment finalization;
3. align the two recurrence/field-normalization implementations with contract
   tests; and
4. expose a small Python importer service that calls the same pure transforms
   and transaction helpers. Swift remains a normal GUI client of the same
   contract; no second remote business logic is introduced.

If review concludes that “shared callable implementation” must literally be
one language implementation, the alternative is to move the mutation service
behind a local API. That would be a materially larger architecture and is not
recommended for this project.

## 4A. External agenda changes and SwiftUI/Dock refresh

**Current fact:** `ContentView` reloads on appearance and on a 30-second
Combine timer. `BlinkAppState` also refreshes its shared snapshot every 30
seconds. There is no filesystem presenter, FSEvents stream, or importer→GUI
IPC. Atomic replacement of `agenda.json` is therefore noticed by polling the
path, not by watching an old inode. With the current code, an externally
completed event can remain visible in an open window for up to roughly 30
seconds (plus read/refresh time); Dock attention follows the same refresh
cycle. The watcher itself skips `done=true` on its next loop independently.

**Risk:** a future importer commit does not synchronously update an already
open SwiftUI process. Adding a file watcher without accounting for atomic
replace could observe a deleted inode or duplicate notifications.

**Recommendation:** keep the existing 30-second polling as the correctness
baseline; it already solves eventual external reload and avoids a new
mechanism. If owner-approved UX requires faster Remote DONE feedback, add a
debounced observation of the `agenda.json` parent directory, then always
re-read the pathname after the event (never the old file descriptor). The
observer is a UI optimization; it must share the same `reload()`/snapshot path
and remain safe when an atomic replace emits multiple filesystem events.

The required end-to-end chain is:

```text
Remote DONE
  -> importer commits agenda.json
  -> existing SwiftUI poll (or optional debounced parent observation)
  -> loadEventResult/reload shared snapshot
  -> AttentionManager.setState(snapshot.attentionState)
  -> DockAttentionOutput and Today tab update
```

**Alternative:** importer-to-GUI notification/IPC would reduce latency but adds
another coupling and failure channel. It is rejected while pathname polling
provides correctness.

## 5. Proposed importer ownership and execution model

**Recommendation:** add a bounded `app/mailbox_importer.py` module and one
mailbox worker thread inside the existing `watcher.py` process. The main loop
starts a worker iteration only when the previous iteration is finished, polls
for a completed result without waiting, and continues weather, astronomy,
queue, notification, and blinker work independently. The worker is a queue
consumer, not a scheduler or sender.

This change from the first proposal is deliberate: Python cannot reliably
interrupt a filesystem `open/read/stat` that happens to wait for an iCloud
placeholder merely because a wall-clock budget expired. A budget still limits
normal work, but the worker boundary prevents such a syscall from blocking the
watcher’s scheduler. The worker must use a bounded package count and avoid all
network/ntfy calls. A stuck worker is logged as `mailbox_worker_stalled`; a
future iteration is not started until the old one exits, preventing thread
accumulation.

The main loop performs only non-blocking state hand-off (for example, a
thread-safe result queue with a zero-timeout poll). It never joins the worker
from the scheduler path. Worker exceptions are captured and converted to
diagnostics so a bad package cannot terminate the watcher.

The exact insertion point and budgets are implementation decisions after
profiling, but the invariant is fixed: a mailbox stall may stop mailbox
progress, never notification scheduling or physical-output updates.

### Alternatives evaluated

- **Filesystem “local bytes” preflight:** resource values and coordinated reads
  can identify some placeholders, but they do not provide a universal,
  documented non-blocking guarantee for every iCloud provider state. Use them
  as a fast hint, not as the safety boundary.
- **Short-lived helper process with a hard timeout:** a process can be killed
  if it blocks, which is technically stronger isolation. It would add process
  lifecycle, IPC, and packaging complexity and is a second background process
  in the normal path. Keep it only as a last-resort recovery tool if real
  measurements prove the in-process worker cannot be made operationally safe;
  it is not the recommendation.

Rejected as the default: a second LaunchAgent/daemon, a SwiftUI polling loop,
or a helper process. Each would add lifecycle races and violate the one
long-running delivery-process boundary.

## 6. Proposed production mailbox location

Keep the verified feasibility folders untouched. Reserve a separate explicit
production inbox in the same private Shortcuts container:

```text
~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/
  Blink_Production/ToMac/
```

The production Shortcut is approved to point at this path when production
enablement begins.
The importer must receive the resolved root from a local, Git-ignored Blink
configuration value (with the above path as the reviewed default), verify that
the directory is the expected private-container descendant, and refuse an
unapproved root. `ToMac` is the only iCloud mailbox directory in the revised
recommendation. Processed/quarantine history belongs on the Mac:

```text
<Blink root>/mailbox/
  journal/
  quarantine/
  runtime/
  processed_commands.json
```

After a durable local commit and ledger update, the importer deletes the exact
transport triple from iCloud `ToMac`. For a malformed package, it first copies
the bytes (when safely available) and a reason sidecar to local `mailbox/quarantine/`,
then removes only that exact package. If bytes are still syncing, it remains in
`ToMac` as pending. Keeping history local reduces iCloud churn and leaves
`ToMac` as a true inbox; local quarantine is still diagnostic state, not event
truth.

No files in `Blink_Feasibility`, arbitrary iCloud folders, or ordinary owner
files are implicitly imported.

## 7. Exact proposed production DONE schema

The production command should be strict and versioned:

```json
{
  "version": 1,
  "type": "DONE",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "event-...",
  "created_at": "2026-09-12T18:30:00-07:00"
}
```

Required fields are `version`, `type`, `command_id`, and `event_id`.
`created_at` is recommended audit metadata and is not used for scheduling.
`command_id` is a UUIDv4 transport identity generated by the Shortcut; it is
not the event identity. `event_id` is the exact production occurrence ID shown
in the notification payload/command context.

There is no separate production `occurrence_id` today. `BlinkEvent.id` is the
lifecycle identity of one occurrence. A recurring successor gets a new ID and
stores the prior ID in `recurrence_parent_id`; `series_id` groups the series
but is not an attachment owner and is not sufficient to identify a tapped
occurrence. The feasibility `occurrence_id` field should therefore be removed
from the production Shortcut contract, or accepted only as a deprecated alias
that must equal `event_id` during a transition. Do not persist it merely because
the test Shortcut emitted it.

Semantics:

- existing unfinished `event_id`: apply normal `complete` once;
- already done `event_id`: successful no-op;
- missing/history-frozen/stale `event_id`: safe no-op with an explicit
  `stale_event` result, never a new event or recurrence;
- duplicate `command_id`: successful no-op after the first committed result;
- recurrence successor creation remains guarded by the existing parent/generation
  check, so a retry cannot create a second successor.

## 7A. Real `event_id` propagation through the future DONE action

**Current fact:** `app/notification_format.py` currently returns only a
human-readable title/body. `watcher.build_ntfy_request` sets content metadata,
sequence ID, and delay, but no `Actions` header or Shortcut URL. The rolling
queue in `app/ntfy_schedule.py` hashes title/body/priority/tags and delivery
time; it has no action field. Feasibility’s `EVENT123`/`OCC123` values are not
production identifiers.

**Recommended future path:** one shared formatter used by both direct and
queued personal notifications derives an action from the real event ID:

```text
event.id
  -> notification action builder
  -> URL-encode event_id (and a small protocol/version value)
  -> ntfy Actions metadata
  -> shortcuts://run-shortcut for the approved Blink DONE Shortcut
  -> Shortcut generates a fresh UUID command_id
  -> <command_id>.done.json contains event_id
  -> mailbox importer
```

The URL builder must use a standards-compliant query encoder (not string
concatenation), allow only the expected Shortcut name and `event_id` value, and
reject/control-escape unexpected characters. The Shortcut input should contain
`event_id` plus a small versioned marker (for example `blink-done-v1`) rather
than a serialized agenda record. The Shortcut still generates the command UUID
locally; it must never reuse the event ID as transport identity.

The action URL/value must be included in the common notification payload and
therefore in the queued payload hash/signature. If the action contract changes,
the queue must treat existing queued entries as changed and replace them using
the existing reconciliation path; already delivered notifications cannot be
retroactively changed. Direct and rolling notifications must call the same
formatter so they cannot drift. The exact ntfy action syntax and iOS
`shortcuts://` acceptance remain a manual acceptance check before implementation;
this proposal does not enable an action today.

## 8. Exact proposed production CREATE_EVENT schema

CREATE v1 should carry user intent, not a copy of `agenda.json`. It is
deliberately non-recurring; recurrence can be added as a separately reviewed
v2 contract after the core path is stable:

```json
{
  "version": 1,
  "type": "CREATE_EVENT",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Call the contractor",
  "description": "Optional multiline text",
  "start": "2026-09-13T09:00:00-07:00",
  "reminder_intent": {"offsets_minutes_before": [30, 0]},
  "attention_level": "yellow",
  "blinker_intent": {"minutes_before": 0},
  "created_at": "2026-09-12T18:30:00-07:00",
  "attachment": {
    "basename": "550e8400-e29b-41d4-a716-446655440001.attachment.pdf",
    "original_filename": "contract.pdf"
  }
}
```

`transfer_id` is a UUIDv4 transport identity. The Mac allocates the production
event ID; a remote transfer ID must never become a user-visible event ID. The
attachment object is absent when there is no attachment. The basename is a
transport filename only and must exactly match the package naming rule.

The Mac adds `enabled=true`, `requires_done=true`, `done=false`,
`done_at=null`, canonical `tags:["calendar"]`, `recurrence=null`, and the
attachment manifest. These internal fields are never accepted from the phone.
The Mac also applies the normal title/description normalization and generates
the production event ID.

Validation limits (maximum title/description lengths and transport size caps)
require implementation-time measurements/values. The event
must have an explicit offset in `start`, at least one valid non-negative
reminder offset that is applicable to the start time, and a recognized
`attention_level` (`green`, `yellow`, or `red`).
`reminder_intent.offsets_minutes_before` is the only reminder input in v1.
`blinker_intent.minutes_before` maps directly to
`blinker_minutes_before`. Absolute `blink_at`/`blink_datetime` is not a
production input. Unknown JSON fields may be retained by the normal persistence
layer but are not interpreted by the importer.

## 9. Feasibility-to-production mapping

| Feasibility field | Current production field | Mapping and validation | Mismatch / required Shortcut change |
|---|---|---|---|
| `title` | `title` | Trimmed non-empty user text; preserve Unicode. | Same concept; enforce production length limit. |
| `description` | `description` | Optional multiline string; preserve paragraphs. | Same concept. |
| `event_datetime` | `start` | Parse as ISO-8601 with explicit UTC offset; store canonical aware ISO. | Feasibility name differs; Shortcut should emit `start` or an unambiguous offset-bearing value. |
| `priority` | `attention_level` (and separately ntfy `Priority`) | Map green/yellow/red to `attention_level`; do not confuse with ntfy urgency header. | Rename required; current `priority` event value is not the UI importance contract. |
| `blink_datetime` | — | Not accepted in production CREATE v1. | Feasibility-only field; absolute-time conversion is excluded. |
| `reminder_intent.offsets_minutes_before` | `reminders_minutes_before` | Require a sorted unique non-negative list; values unavailable before `start` are removed by normal logic. | Feasibility omitted this intent; production Shortcut must ask or owner must approve the Mac default. |
| `blinker_intent.minutes_before` | `blinker_minutes_before` | Integer offset, normally `0` (`At event`), validated against start. | Approved native transport form. |
| missing enabled/lifecycle | `enabled`, `requires_done`, `done`, `done_at` | Mac defaults `true`, `true`, `false`, `null`. | These are internal fields and must not be phone inputs. |
| missing done fields | `requires_done`, `done`, `done_at` | Normal Create path sets `true`, `false`, `null`. | Importer must not accept remote lifecycle overrides. |
| recurrence fields | `recurrence`, `series_id` | Not accepted in CREATE v1; Mac writes `recurrence=null`. | Remote recurrence is deferred to a separately reviewed v2. |
| `tags` | `tags` | Not accepted as internal input; Mac writes canonical `['calendar']`. | Prevents remote contract drift and unsafe classifications. |
| `attachment` | `event_data/attachments/<event-id>/` + manifest | Copy only the package attachment basename into the newly allocated owner folder; write manifest from physical files. | Original display filename is metadata; it is not a path. |
| `created_at` | optional audit field | Preserve as transport metadata if contract allows; never use as event start. | Same name but different meaning from `start`. |
| `transfer_id` | no event field; processed ledger key | UUID transport dedupe key. | 9-digit feasibility random number is not sufficient for production. |
| `id` | Mac-generated event `id` | Generate a Blink event ID following existing ID policy under the mutation lock. | Never accept an iPhone-supplied event ID as authoritative. |

## 10. Package state machine

The flat package protocol remains:

```text
<id>.event.json
<id>.attachment.<extension>   (optional)
<id>.ready                     (written last by Shortcut)
```

For DONE, the JSON suffix is `.done.json` and there is a matching `.ready`.
The importer recognizes only strict UUID-based names and exact matching stems.

```text
ABSENT -> DISCOVERED -> READY_SEEN -> VALIDATING
                         |             |
                         |             +--> QUARANTINED (deterministic malformed)
                         |             +--> PENDING_SYNC (bytes unavailable)
                         |
                         +--> APPLIED -> PROCESSED -> ARCHIVED/REMOVED
```

No `.ready` means ignore for now. A ready marker with temporarily unavailable
JSON/attachment is `PENDING_SYNC`, not malformed. `PROCESSED` is recorded only
after the local event/attachment commit succeeds. Transport cleanup is last.

## 11. Idempotency design

Use UUIDv4 `command_id` for DONE and UUIDv4 `transfer_id` for CREATE. Never use
the filename, original display name, or a timestamp as business identity.

Use a small Blink-local operational ledger, for example:

```text
<Blink root>/mailbox/processed_commands.json
```

Each record contains transport ID, type, result (`applied`, `noop_done`,
`stale_event`), event ID if known, timestamps, and a compact error/result code.
This ledger is not an event database: `agenda.json` remains the only event
source of truth. Local quarantine/journal diagnostics may help audit it, but
successful iCloud packages are deleted and are not treated as a durable event
archive.

Before applying CREATE, dedupe by both ledger and a persisted event provenance
field such as `mailbox_transfer_id`. The second check closes the crash window
where `agenda.json` committed but the ledger write did not. DONE additionally
dedupes naturally on the event’s `done` state and recurrence successor guard.
**Recommended retention is indefinite tombstones.** At the expected Blink
volume the JSON remains small: 1,000 records at roughly 250 bytes is ~0.25 MB;
10,000 is ~2.5 MB; 100,000 is ~25 MB before pretty-print overhead. This is
operational dedupe state, not an event database, and avoids the unsafe case of
an old package reappearing after both its ledger record and event provenance
were deleted. If a future volume makes one JSON file unwieldy, compact it only
with an append-only hash/tombstone log plus a separately reviewed snapshot;
never expire IDs silently.

Ledger updates use the same mutation lock and atomic replace. On restart, an
unprocessed package is retried; a committed event with a missing ledger entry
is recognized by provenance and the ledger is repaired without creating another
event.

## 12. Concurrency and `agenda.json` writer analysis

Current writers are:

- Swift `BlinkStore.save` (new/edit event) in `Models.swift`;
- Swift `BlinkStore.complete` (Done and recurrence successor);
- Swift `setAttentionLevel`, `setEnabled`, and `delete`;
- Swift `addFiles` and `addJPEG` (attachment manifest updates);
- Swift `loadEventResult` when it repairs future `done=true` records or
  attachment manifests;
- Python `app/agenda_store.load_agenda_document` when it persists migration,
  stale-record repair, or manifest reconciliation.

`watcher.py` normally reads agenda and does not write event records. There is
no shared lock or version check.

Atomic rename protects readers from a torn file, but not this lost-update race:

```text
Swift reads A       importer reads A
Swift writes A+S    importer writes A+I  -> S is lost
```

Before enabling an importer writer, add a single advisory lock file below the
Blink root (for example `agenda.lock`) using POSIX `flock(2)` on macOS. Python
`fcntl.flock` and Swift `Darwin.flock` can interoperate on the same lock file;
the protocol must specify `LOCK_EX`, close/unlock behavior, and a non-blocking
try-lock path. Every writer listed above, including load-time repair/migration,
must adopt it.

The lock scope is intentionally short. **Outside the lock:** validate transport
metadata, wait for iCloud bytes, copy the attachment to Blink-local staging,
fsync and verify it, and write the journal. **Inside the lock:** reread the
latest agenda, recheck provenance/idempotency, allocate/confirm the Mac event
ID, move local staging to the final owner folder, build the manifest, apply the
canonical Create/Done transform, atomically write agenda, and commit the local
transaction marker. **After unlock:** ledger housekeeping, local diagnostics,
and exact transport cleanup.

The importer should use a non-blocking try-lock (or a very short bounded wait)
and return `busy` for a later worker iteration when SwiftUI is saving. A
monotonic document revision is a useful diagnostic/compare-and-swap backstop,
but cannot replace the lock while writers replace the full document. The
importer must reread under the lock immediately before mutation; it must never
mutate a stale snapshot loaded before waiting.

This is a required pre-integration refactor, not an implementation detail that
can be postponed safely.

## 13. Crash-consistency sequence

Recommended journaled transaction for CREATE:

**A. Without the agenda lock:**

1. Discover and validate the ready package without mutating it.
2. Wait for iCloud bytes to be locally available; copy any attachment from
   iCloud into Blink-local staging.
3. `fsync` and verify staged size, regular-file type, and bytes.
4. Write the journal transport state. A Mac event ID may be allocated in the
   journal at this point only if the chosen ID policy makes abandoned IDs safe.

**B. Under the short shared agenda lock:**

5. Reread the latest `agenda.json` and recheck idempotency/provenance.
6. Allocate/confirm the Mac event ID, move local staging to the final
   event-ID attachment folder, and build the manifest.
7. Apply the canonical Create/Done mutation and atomically write `agenda.json`.
8. Commit the local transaction marker (`agenda_committed`).

**C. Release the agenda lock.** No iCloud read, wait, or copy is performed
while this lock is held.

**D. After unlock:** update the ledger/runtime diagnostics as appropriate, then
delete the exact successful JSON, attachment, and ready files from iCloud
`ToMac`. A busy GUI writer causes a try-lock failure and a later retry.

On restart, recovery scans journals: an `attachment_staged` journal either
finishes the agenda commit if all validated bytes remain, or removes only the
new staging owner; an `agenda_committed` journal repairs the ledger and then
cleans transport files. A crash before step 5 leaves the original package
untouched. A crash after step 5 cannot create a duplicate because provenance
and the ledger check are both idempotent. A crash never deletes a package before
the local commit.

DONE uses the same A/B/C/D ordering but has no attachment phase. The
existing recurrence parent/generation check remains the duplicate-successor
barrier.

## 14. Attachment transaction

Remote attachments must end as ordinary Blink-owned files, not mailbox links.
Reuse `app/attachment_store.py` rules and Swift `AttachmentWorkspace` naming,
collision, manifest, and owner-ID semantics; do not create a second attachment
architecture.

The importer must reuse the local acceptance contract: regular files are
accepted without a PDF/JPEG-only allowlist; directories are rejected; symlinks
and missing bytes are rejected; and the basename must exactly match
`<transfer_id>.attachment.<extension>`. Local Swift `AttachmentWorkspace` and
Python `attachment_store` both use visible regular files, basename-based
collision-free naming, and manifests derived from physical files. The remote
path may add a package/file size cap for mailbox protection, but must not narrow
file types merely because the transport was iCloud. The original filename is
display metadata only. The production event’s owner is the Mac-generated event
ID.

The local staging/journal step is needed because the current Swift draft
finalizer is not callable from Python. The implementation should extract a
small shared transaction helper or make the Python helper conform to the same
contract, then add cross-language contract tests. Do not silently copy bytes
directly into a final owner folder without a recovery record.

## 15. iCloud incomplete-vs-malformed handling

The `.ready` marker is a commit hint from the phone, not proof that iCloud has
downloaded every byte to the Mac.

- No `.ready`: ignore; do not touch the package.
- `.ready` plus missing JSON/attachment or an iCloud placeholder: classify as
  `PENDING_SYNC`; retry with bounded exponential backoff and an owner-approved
  maximum age. Exact delays, package count, and wall-clock budgets are selected
  after profiling/manual iCloud testing.
- Bytes present but JSON invalid, schema-invalid, mismatched, unsafe, or
  unsupported: deterministic `QUARANTINED`; continue with later packages.
- Maximum pending age exceeded: quarantine as `sync_timeout`, preserving the
  package for diagnosis rather than calling it malformed.

Each scan must process independent package IDs separately. One pending or bad
package cannot block a valid later package.

## 16. Security and path validation

The importer accepts only a configured, canonical mailbox root. Before use it
must resolve real paths, reject a root that is a symlink or outside the approved
private-container subtree, and refuse symlink traversal in package entries.

Filename validation is strict: UUID stem, exact `.event.json`/`.done.json` and
`.ready` suffixes, and an optional attachment whose basename contains the same
UUID. JSON must not contain absolute paths, `..`, slashes, NULs, shell syntax,
or commands. The importer reads bytes only from the package directory and
never follows a path supplied by JSON.

Apply an owner-approved per-file/package size cap. Reuse local Blink’s regular
file policy rather than inventing an extension/MIME allowlist; unsupported
means a type rejected by the existing local attachment path, not “not PDF or
JPEG”. Oversized, non-regular, symlinked, or multiple-attachment packages are
quarantined with a reason code. Ordinary
owner files in `ToMac` are ignored and never renamed, moved, deleted, or
interpreted.

## 17. Failure and quarantine behavior

Use local `<Blink root>/mailbox/quarantine/` for packages that are
deterministically unsafe or malformed. When bytes are safely available, copy
the exact package triple and a reason sidecar locally, then remove only those
transport files from iCloud `ToMac`; never glob or clean the directory. If
moving/copying is unsafe because iCloud is still syncing, leave the files in
place and record the retry state.

Successful packages are deleted from `ToMac` only after the
agenda/attachment/ledger commit. Failed local writes remain pending and are
retried; they are not acknowledged as applied. Local quarantine is transport
diagnostic history, not event truth.

## 18. Ntfy DONE acknowledgement remains open

The originating iOS ntfy notification lifecycle is intentionally unresolved:

- clear immediately;
- keep until Mac acknowledges successful receipt/application; or
- another acknowledgement UX.

`clear=true` is not selected. The importer design must not depend on remotely
deleting an already delivered iOS notification. After a successful apply it
can expose a local result (`applied`/`noop`/`stale`) and, if a future approved
transport supports it, emit an acknowledgement signal. That signal and the
actual iOS notification mutation require a separate feasibility and owner
decision.

The reliable signal available to a future acknowledgement layer is local and
durable: a journal record reaches `agenda_committed`, the processed ledger
contains the transport UUID and result, and `mailbox_runtime.json` records the
last result. The signal is therefore observable even if iCloud cleanup or an
iOS notification update fails; acknowledgement UX must not be coupled to
deleting the source notification.

## 19. Observability and Health proposal

Add a small Git-ignored runtime JSON, for example:

```text
<Blink root>/mailbox/mailbox_runtime.json
```

Suggested fields: `last_scan_at`, `last_success_at`, `pending_count`,
`last_error`, `last_error_at`, `last_command_id`, `last_result`, retry count,
`worker_started_at`, `worker_finished_at`, `worker_in_flight`,
`worker_stalled_since`, and cumulative quarantined count. Writes must be atomic
and failure to write this diagnostic file must never block event processing.

The existing Health view may display mailbox enabled/root status, last scan,
pending count, last success, last error, and a clearly labelled “worker
stalled/in flight” state without exposing ntfy secrets or full private
filenames. A stalled worker means mailbox progress is paused; it must not be
reported as a scheduler failure while the watcher heartbeat and notification
cycles remain healthy. This is operational state only, not a database or source
of truth.

## 20. Test strategy

Before production integration, add isolated tests using temporary roots:

- strict DONE/CREATE schema and filename parsing;
- timezone/offset, reminders, priority, and `blinker_intent` validation;
- symlink/path traversal, malformed JSON, unsupported/oversized attachment;
- `.ready` ordering and incomplete-sync retry/backoff/timeout;
- first DONE, duplicate DONE, stale DONE, and recurrence successor no-dup;
- duplicate CREATE after restart and provenance/ledger repair;
- attachment all-or-nothing commit and journal recovery at every crash point;
- two concurrent agenda writers proving the shared lock prevents lost updates;
- bounded watcher-loop budget and isolation from notification delivery;
- quarantine/processed cleanup that leaves unrelated owner files untouched.

Do not use the owner’s real iCloud folders in CI. A manual acceptance pass may
use a separately approved production-like test root after the contract is
implemented.

## 21. Recommended implementation phases

1. **Persistence safety refactor:** add the shared agenda lock (and optional
   revision), align Swift/Python transforms, and add contract tests. No mailbox
   scanning yet.
2. **Importer core:** implement parser, state machine, journal, ledger,
   quarantine, and attachment transaction against temporary roots.
3. **Watcher integration:** add the in-process worker/thread hand-off, add
   runtime diagnostics, and prove notification latency remains within budget.
4. **External GUI refresh:** rely first on the already existing 30-second
   SwiftUI reload; if owner-approved UX requires sub-30-second updates, add a
   debounced parent-directory observation that re-reads the path after atomic
   replacement (never an importer→GUI IPC channel).
5. **Manual iPhone acceptance:** point a new approved Shortcut at
   `Blink_Production/ToMac`; test DONE and CREATE with no attachment, image,
   and PDF; verify duplicate/restart/retry behavior.
6. **Separate acknowledgement decision:** only then decide the ntfy/iOS
   notification lifecycle and any optional acknowledgement signal.

## 22. Exact files that WOULD change during implementation

No file in this list is changed by this proposal. A future implementation may
need:

- `app/mailbox_importer.py` — parser, state machine, journal, ledger, and
  bounded processing API;
- `app/agenda_store.py` — shared mutation/lock helpers and remote provenance
  mapping, preserving unknown fields;
- `app/attachment_store.py` — reusable staged import/finalization transaction;
- `watcher.py` — one bounded call plus runtime error isolation/metrics;
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift` — same lock and
  persistence contract for GUI writers;
- optionally `ContentView.swift`/Health model — mailbox diagnostics only;
- root-level Python tests and `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner`
  — parser, concurrency, crash, and cross-language contract coverage;
- a Git-ignored local mailbox configuration/runtime path, not an authoritative
  contract document until design approval.

`watcher.py` remains the only long-running process; no LaunchAgent is added.

## 23. Risks and remaining open questions

Risks:

- Without a shared lock, importer writes can lose simultaneous SwiftUI edits.
- A stuck iCloud filesystem syscall may stall the mailbox worker; the watcher
  main scheduling/output loop remains independent. Worker budgets and retry
  design must be measured on real iCloud placeholders.
- Moving attachments and agenda metadata is a two-resource transaction and
  requires journal recovery, not atomic JSON alone.
- Feasibility’s absolute `blink_datetime`, missing reminders, and separate
  `occurrence_id` do not match the current production model.
- A user can tap DONE after an event has been edited/deleted; stale handling
  must be visible in diagnostics without resurrecting data.

Owner-approved baseline decisions:

1. Production root is `Blink_Production/ToMac` inside the verified private
   Apple Shortcuts container. iCloud is inbox-only; no production `Processed/`
   or `Quarantine/` directories are created there.
2. Local operational paths are `mailbox/journal/`, `mailbox/quarantine/`,
   `mailbox/runtime/`, and `mailbox/processed_commands.json`.
3. DONE uses UUIDv4 `command_id`; CREATE uses UUIDv4 `transfer_id`.
4. Production event IDs are created only on the Mac. DONE carries real
   `event_id` only; `occurrence_id` is not needed. Missing/already-stale/deleted
   DONE is a safe `stale_event` NO-OP and never quarantined or resurrected.
5. CREATE_EVENT v1 is non-recurring and carries user intent only. The Mac sets
   `enabled=true`, `requires_done=true`, `done=false`, `done_at=null`, canonical
   tags/defaults, `recurrence=null`, the production ID, and the attachment
   manifest.
6. `blinker_intent.minutes_before` is the transport form; no absolute
   `blink_datetime` conversion is required. Attachment type acceptance reuses
   local Blink; only transport size/package caps may be added. The numeric
   attachment limit remains an open owner value. UUID tombstones are retained
   indefinitely by default and never expire silently.
7. A shared short POSIX `flock` between Swift and Python is mandatory before
   importer integration. iCloud work stays outside that lock; the importer
   uses try-lock/retry-later when a GUI writer is busy.
8. One mailbox worker thread runs inside the existing watcher process. The main
   watcher never joins or waits for iCloud/blocking worker I/O; only one worker
   iteration may be active, stalled state is observable, and numeric scan/
   package/time budgets are selected after profiling/manual iCloud testing.
9. Existing SwiftUI 30-second polling remains the correctness fallback. A
   debounced parent-directory observer is approved as a UX optimization; it
   rereads `agenda.json` by pathname after atomic replacement and uses the
   existing reload/shared snapshot path.
10. The ntfy DONE acknowledgement lifecycle remains OPEN (clear immediately,
    wait for Mac acknowledgement, or another UX). `clear=true` is not selected;
    exact ntfy Actions syntax and iOS Shortcut URL acceptance remain a manual
    acceptance item.

## 24. Why this does not create a second scheduler, sender, database, or source of truth

The proposed importer is a bounded worker function called inside the existing
`watcher.py` process. It does not schedule reminders, publish ntfy messages,
drive the USB blinker, or own a second LaunchAgent. A stuck worker thread may
pause mailbox progress, but the main watcher loop continues independently. All event lifecycle and
recurrence effects are committed to the existing local `agenda.json`; all
attachment bytes end in existing event-ID folders. The ledger, journal,
quarantine, and runtime JSON are operational transport state only and cannot
answer “what events exist” without `agenda.json`.

The iPhone and iCloud mailbox provide commands and bytes only. Normal watcher,
Attention, Dock, notification, and blinker behavior continue to consume the
Mac-local event contract. SwiftUI already detects external commits by its
30-second pathname polling (with optional future parent-directory observation
for latency); no importer→GUI IPC is required for correctness. There is no
cloud database, SQLite source, reverse HTTP channel, or parallel remote
business logic.

## Sequence diagram A — Remote DONE

```text
iPhone Shortcut
    | write <uuid>.done.json
    | write <uuid>.ready last
    v
private iCloud Blink_Production/ToMac
    | file becomes locally available
    v
existing watcher.py loop -> start mailbox worker (non-blocking hand-off)
    | worker validates + lock + idempotency check
    v
existing Blink Done mutation (agenda_store contract / aligned BlinkStore semantics)
    | done=true, done_at; successor guard
    v
agenda.json commit -> SwiftUI 30s poll/reload -> Attention off; watcher skips reminder/blinker
    | ledger/journal success, then delete exact transport files from ToMac
    v
local applied/no-op result (optional future acknowledgement signal)
```

## Sequence diagram B — Remote CREATE_EVENT

```text
iPhone Shortcut
    | write <uuid>.event.json
    | write optional <uuid>.attachment.ext
    | write <uuid>.ready last
    v
private iCloud Blink_Production/ToMac
    | file becomes locally available
    v
existing watcher.py loop -> start mailbox worker (non-blocking hand-off)
    | worker validates schema, paths, bytes, and transfer id
    v
existing Blink Create mutation (normal event fields and recurrence defaults)
    | lock + allocate Mac event id
    | stage/finalize attachment into event_data/attachments/<event-id>/
    v
agenda.json + attachment manifest commit
    | provenance/ledger/journal commit
    v
delete exact transport files from ToMac; normal watcher schedules/pushes the new event
```

For either sequence, a deterministic malformed package is first copied with a
reason sidecar to local `mailbox/quarantine/`, then only its exact transport
files are removed from `ToMac` when safe. There is no iCloud `Processed/`
archive.

## Recommendation and rejected alternatives

**Recommendation:** use the owner-approved baseline below for implementation
planning. Implementation still waits for the remaining numeric limits and
manual ntfy/iOS action acceptance; this document does not authorize code
changes.

Rejected alternatives:

- **Second LaunchAgent/daemon:** adds another long-running process and creates
  competing lifecycle/error handling; violates the current boundary.
- **SwiftUI polling:** fails when the app is not running and would duplicate
  persistence/attention responsibilities.
- **Using iCloud as synchronized agenda:** makes a transport folder a second
  source of truth and creates conflict semantics the project explicitly rejects.
- **Using transfer ID as event ID:** couples transport identity to lifecycle,
  leaks remote naming into UI, and complicates retries/recurrence.
- **A separate `remote_done_logic`/`remote_create_logic`:** would drift from
  frozen-history, attachment, and recurrence rules; the shared mutation/lock
  prerequisite is safer.
- **ntfy reverse channel, public links, or a cloud DB:** outside the approved
  private file transport and materially expands security and ownership scope.

## Review question disposition (seven-plus-one findings)

| Review question | Current fact | Disposition |
|---|---|---|
| External agenda refresh | Already covered by SwiftUI 30-second polling and appearance reload; no filesystem observer. | Keep polling for correctness; optional debounced parent observation only for latency. |
| iCloud blocking | A filesystem syscall can outlive a Python wall-clock budget. | Use one worker thread inside watcher; main loop never waits. Helper process is last resort, not default. |
| Shared agenda lock | All listed Swift/Python repair and mutation paths currently lack a common lock. | Add interoperable POSIX `flock`; keep iCloud I/O outside and local commit inside a short scope; try-lock when busy. |
| DONE identity/action | Current ntfy formatter has no action; production model has only event `id` per occurrence. | Future shared action formatter carries URL-encoded `event_id`; queue hash includes it; no `occurrence_id`. |
| CREATE payload | Feasibility shape includes internal agenda fields and omits reminder intent. | Simplify v1 to non-recurring user intent; Mac supplies lifecycle/defaults/manifest/ID. |
| Attachment policy | Local Swift/Python paths accept regular files by physical-file rules, not PDF/JPEG-only. | Reuse that contract; remote adds only size/package limits. |
| Ledger retention | Deleting old IDs can permit replay after event/provenance deletion. | Keep UUID tombstones indefinitely by default; size estimates are operationally small. |
| Processed/quarantine location | iCloud is a transport inbox, not a durable history store. | Keep only `ToMac` in iCloud; delete exact successful packages and store local diagnostics/quarantine. |

## Owner-approved architecture baseline

This baseline is approved for implementation planning, but production
implementation has not started:

- one existing `watcher.py` process;
- one mailbox worker thread inside it;
- one short shared Swift/Python POSIX `flock`;
- iCloud only at `Blink_Production/ToMac`;
- local `mailbox/journal/`, `mailbox/quarantine/`, `mailbox/runtime/`, and an
  indefinite dedupe ledger;
- UUIDv4 transport IDs and Mac-generated production event IDs;
- DONE uses `event_id` only; stale DONE is a safe NO-OP;
- CREATE v1 is non-recurring and user-intent only; Mac supplies lifecycle and
  default fields;
- local Blink attachment acceptance contract is reused, with only a future
  transport size cap as an additional guard;
- all iCloud wait/read/copy work occurs outside the agenda lock;
- existing 30-second SwiftUI polling is the correctness fallback;
- a debounced parent-directory observer is approved as a faster UX path;
- ntfy acknowledgement lifecycle remains OPEN, and `clear=true` is not chosen.
