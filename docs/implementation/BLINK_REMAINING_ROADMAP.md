# Blink — authoritative roadmap

**Snapshot:** 2026-09-15
**Status:** The three product roles are modeled by a verified non-runtime simulator harness, now used as the primary development/test instrument. The untouched CREATE oracle transport has physically produced a fresh payload; candidate differential debugging remains open. Files multi-file chooser behavior is physically proven on the preserved fixed-path/flat-root fallback with both JPEG and PDF; the simulator now models that flat-root action sequence and its fail-closed marker/prefix checks. The existing canonical `Blink Files` body has been replaced in place with that flat-root tree; iPhone sync and canonical physical acceptance remain open. The gray Mac `Start blinking` regression remains open. Same-ID notification freshness is recorded as an unresolved question and is not being changed yet.
**Authority:** this roadmap, [`BLINK_CURRENT_STATE_CONTRACT.md`](../contracts/BLINK_CURRENT_STATE_CONTRACT.md), and [`BLINK_SHORTCUT_TREES_2026-09-14.md`](BLINK_SHORTCUT_TREES_2026-09-14.md) describe current state. Older reports preserve history only.

Latest Files evidence: the preserved fixed-path/flat-root fallback opens both
JPEG and PDF with the same ntfy package input. The canonical `Blink Files`
body now uses the same flat-root filter path and has been GUI-saved with marker
`FILES-CANONICAL-FLAT-20260916 | GUI-SAVED`; iPhone sync and one canonical
live-banner run remain open. The previously observed yellow Candidate chooser
was from an already-delivered old push containing the test override; current
default generation was verified to target `Blink Files`. Do not treat the
earlier dynamic-path failure as a blanket iOS restriction or proceed to
Production cutover before acceptance.

## Product target

Blink creates and manages personal events on the Mac and sends ntfy actions to
the iPhone. The Mac is the source of truth. The final phone UX is one Home
Screen entry `Blink`; `Share → Blink` creates an event from one shared file.
`Done` and `Files` are separate internal notification actions.

Future capture entry points include Mac Finder right-click creation from a
supported file and creation from a supported clipboard object. Both must feed
the existing CREATE flow and one-optional-attachment contract rather than
introduce another event architecture.

## Complete product scope preserved

The following approved requirements remain part of the product target even
when the active implementation chunk is limited to Files:

- **Mac editor timing:** an existing unfinished event must keep both
  `reminders_minutes_before` and `blinker_minutes_before` editable after its
  lead time has elapsed. Saving updates the same event ID, creates no
  duplicate, persists the new canonical values, and drives future Attention
  from the updated blinker value. This is not currently product-accepted:
  live evidence shows that after an old `1 day before` trigger has elapsed,
  `Start blinking` can be disabled and prevent replacement with a future
  `60 min before`. Final acceptance must reproduce this exact live UI case.
  **Open UI bug (2026-09-16):** the editor currently renders no Blinker control
  at all for an existing event, although the event model and Shortcut contract
  still carry an independent `blinker_minutes_before` value. Do not infer a
  data-loss or transport defect from this screenshot; restore the editor
  control and then re-run the existing timing acceptance case.
  **Open menu-bar question (2026-09-16):** the Mac shows two yellow Blink
  circles near the clock; one remains lit even when the Blink application is
  switched off. Later identify the owner/lifecycle of both indicators and
  determine whether the persistent one is a stale process, a separate helper,
  or intentional status UI. No UI/lifecycle change is authorized from this
  observation alone.
- **Phone/Mac timing parity:** phone CREATE uses the Mac timing semantics:
  integer-minute reminders, multiple reminders, the current presets and
  Custom behavior, plus one independent integer-minute blinker with matching
  options. The phone must not introduce a second timing model.
- **Final phone UX:** only `Blink` is a Home Screen entry and it creates an
  event. `Share → Blink` uses that same production CREATE Shortcut and accepts
  at most one attachment. `Blink DONE` and `Blink Files` remain internal
  notification actions; Test/Stage/Candidate icons are removed after cleanup.
- **Today Morning Briefing:** add an optional persistent enable/disable
  control near Today, sending one short briefing for all applicable events on
  the current local day. Each item includes importance, title, optional short
  description, and scheduled date/time. Use the existing watcher/sender,
  including dedupe, empty-day, wake, timezone, and Weather/Astronomy rules;
  do not add another scheduler or sender. This is deferred beyond the Files
  chunk.
- **Mandatory four-area cleanup after cutover:** inventory and clean Shortcuts,
  iCloud Blink folders, `/Users/vitaliiprotsiuk/Desktop/Blink`, and contracts/
  documentation. Remove obsolete TEST/WORK/Candidate/Diagnostic/Invoke/
  Nested Invoke/Acceptance/BACKUP/proof-only objects only after replacements
  pass; preserve source, useful tests, canonical user data, runtime state, and
  authoritative documentation. After successful Production smoke, the user
  library should contain exactly `Blink`, `Blink DONE`, and `Blink Files` plus
  unrelated/system Shortcuts; rollback history belongs in Git/docs/export
  evidence, not in permanent Test/Stage2/WORK/BACKUP objects.
- **Contract hygiene:** keep one authoritative answer for architecture,
  current state, event/timing, CREATE, DONE, Files, final trees, production
  paths/flags, roadmap, and acceptance state. Do not multiply competing final
  reports.

## Current verified state

- SwiftUI, `agenda.json`, local event attachments, importer, watcher, weather,
  astronomy, lifecycle, Done handling, and ntfy formatting are implemented.
- CREATE/DONE transport is implemented and has controlled Acceptance coverage.
- Files staging is implemented with a flat integrity package and an atomic,
  package-scoped `ToPhoneView` containing only real attachment basenames.
- The Acceptance Files candidate was physically tested on iPhone: green ntfy
  `Files` button → Shortcuts → chooser with the original filename → PDF in
  Quick Look. One-file Acceptance is closed. A live notification carrying the
  controlled two-file JPEG+PDF package was delivered and its `Files` action
  was verified in ntfy, but the multi-file action tap was not yet completed;
  multi-file acceptance remains open.
- `Done` and `Files` are independent ntfy actions. `Done` carries EventID;
  `Files` carries PackageID. No `clear=true` is used.
- Production mailbox and `Blink_Production/ToMac` remain disabled/unused.
- The physical USB RGB lamp is available but intentionally not connected yet.
- Existing-event same-ID persistence and the model/unit regression are green,
  but live running-app evidence contradicts product acceptance: the stale
  `1 day before` Blinker scenario can leave `Start blinking` disabled. This is
  a CURRENT UI gate, not a DONE feature.
- `app/create_shortcut_simulator.py`, `app/done_shortcut_simulator.py`, and
  `app/files_shortcut_simulator.py` are the primary development/test harness,
  never runtime code. Every logical Shortcut change must pass its role/profile
  simulation first; only the minimal corresponding edit is transferred to a
  physical Shortcut, followed by Apple-specific acceptance where required.

The reusable `shortcuts-simulator-first` skill records the mandatory workflow:
official Apple instructions -> complete physical tree/oracle inspection -> role
simulator and failing tests -> focused/full verification -> minimal GUI transfer
-> iCloud/iPhone tree verification -> Apple-specific acceptance. The Files
simulator explicitly models the `Get File -> Folder/File -> Get Contents ->
List[File] -> Choose` typed boundary. Its fixed-path and Magic Variable profiles
resolve to a Folder and `List[File]`; an unresolved literal `PackageID` does not.
This is a diagnostic model, not proof that iOS rejects dynamic paths.

## Working Shortcut contracts

The exact current trees, status, inputs, and sync evidence are in
[`BLINK_SHORTCUT_TREES_2026-09-14.md`](BLINK_SHORTCUT_TREES_2026-09-14.md).

```text
Blink
  direct launch or Share input
  -> validate/normalize fields
  -> build CREATE_EVENT payload
  -> write Acceptance/ToMac (later Production/ToMac)

Blink DONE
  blink-done-v1|<event-id>
  -> write DONE payload to ToMac, .ready last

Blink Files
  blink-files-v1|<package-id>
  -> get package-scoped ToPhoneView folder
  -> Get Contents of Folder
  -> Choose from List
  -> Show Selected Item in Quick Look
```

The canonical `Blink Files` tree now uses the existing flat-root package
filtering implementation (`Blink_Acceptance/ToPhone`) with package-specific
ready/manifest/prefix checks and chooser output. A concrete source-token defect
was found in the iPhone editor (`Get file from PackageID` instead of
`Get file from Shortcuts`); it was corrected on Mac and the complete corrected
body is now visible on iPhone. Representative JPEG+PDF physical acceptance
remains required before cutover.

## Permanent synchronization gate

After any Mac-side Shortcut tree change:

```text
edit/build tree
  -> harmless real edit and Save in Mac Shortcuts GUI
  -> wait for iCloud
  -> open Edit on iPhone and compare the complete action body/build marker
  -> only then run or send an ntfy action
```

Name synchronization alone is not evidence of body synchronization. Adding
and removing `Stop Shortcut` proved the mechanism but is not a production
procedure. The recurring `{"detail":"Bad Request"}` messages were Codex
connection/tool failures, not evidence of a Shortcuts or file failure.

## Staged execution plan

### Stage 0 — documentation reconciliation — COMPLETE

Keep the roadmap, current contract, status report, and tree inventory aligned.
Mark diagnostic and candidate chronology as historical. Keep the plan at
`docs/superpowers/plans/2026-09-14-blink-production-reconciliation.md`.

### Stage 1 — software contract gate — BASELINE VERIFIED

- Separate `Done`/`Files` action formatting and canonical defaults are covered
  by the existing tests.
- CREATE validation is a protected product contract: required non-blank Title,
  lossless optional Description, integer-only reminder and blinker inputs,
  explicit-offset Date/Time, supported direct/Share attachment semantics, and
  exact native transport-ID shape. The detailed case matrix lives in
  [`BLINK_SHORTCUT_TREES_2026-09-14.md`](BLINK_SHORTCUT_TREES_2026-09-14.md).
- Reminder presets `1440, 720, 300, 60, 30, 10, 5, 0`, multiple
  reminders, non-negative integer custom values, and independent blinker.
- Existing non-frozen events may change an old or newly selected timing value;
  new/duplicate events still enforce the available lead-time constraint.
- Do not silently restore `[30, 0]` after the user clears reminders.
- Verify transport IDs have exactly nine random digits and are never event IDs.
- Verify deterministic `__01__`, `__02__` attachment ordering and safe original
  basenames.
- CREATE Gate A is implemented in the active candidate and verified
  after Mac save/re-open: reject Share `Count > 1` before `First Item`.
  Gate B is now physically present in the active candidate: native Round-to-
  Integer followed by exact equality and an explicit Stop branch. iPhone
  acceptance passed for Blinker `0` and `17` (fresh payload pairs) and for
  rejection of `1.5` and `-1` (no fresh payload).

### Stage 2 — synchronize and physically accept frozen candidates

The current candidates are frozen for acceptance: `Blink Create Stage2 WORK`
(104 actions, Gates A+B), `Blink Files Stage2 VIEW TEST` (14 actions), and the accepted
DONE source/candidate. Verify the CREATE tree/body on iPhone after iCloud sync,
then physically test direct CREATE, one shared attachment, Share `>1` rejection,
fractional Blinker rejection, representative text preservation, DONE, the
prepared JPEG+PDF Files package, and one event with both independent buttons.
Do not create a new generation or remove fallbacks during this stage. If the
CREATE candidate has no quickly identifiable reachable defect compared with
the untouched oracle, restore it from that known-good baseline and apply only
the required Acceptance path, Gate A, and Gate B deltas.

### Stage 3 — Combined acceptance and Mac editor gate

Close representative CREATE, DONE, and Files acceptance, then run the
combined event case with independent Done and Files actions. Separately fix
and live-verify the gray Mac `Start blinking` case: an elapsed old `1 day
before` value must be replaceable by a future `60 min before`, preserving the
same Event ID and creating no duplicate.

### Stage 4 — Same-ID freshness investigation

Before Production, investigate and document what happens when an event is
edited in place while the Mac may sleep: whether already queued ntfy messages
from the old snapshot may legitimately continue alongside new pushes for the
same Event ID, or whether future delivery must resolve only the current
canonical state. This is deliberately unresolved. Do not change the scheduler
or queue until the semantic decision is made and evidenced.

### Stage 5 — Acceptance → Production cutover

Do not merely rename candidates. Explicitly migrate and verify `ToMac`, `ToPhone`
and `ToPhoneView` paths, replace candidate names/URLs with `Blink`, `Blink DONE`
and `Blink Files`, GUI-save-touch, confirm complete iPhone trees, and run a
small Production smoke test. Enable production controls only after all three
canonical trees pass.

### Stage 6 — final phone UX

Place only `Blink` on the Home Screen. Keep `Blink DONE` and `Blink Files` as
notification/internal actions. The intermediate Shortcuts screen is accepted
for now because the proven private `shortcuts://run-shortcut` path opens it;
removing it is a later optional optimization.

### Stage 7 — Today Morning Briefing

Add an optional daily briefing for every applicable Today event, with
importance, title, optional description, scheduled date/time, local-time
rules, dedupe, empty-day behavior, wake handling, and Weather/Astronomy
coexistence. It must use the existing watcher sender and have a persistent
enable/disable control. Do not add a second scheduler or sender.

### Stage 8 — cleanup

Before deletion inventory Shortcuts, iCloud roots, and project/runtime paths as
`KEEP / DELETE / WHY`. Remove obsolete tests, backups, diagnostics, and
acceptance clutter only after Production replacement passes. Never remove user
attachments, source, tests, runtime state, authoritative docs, or the only
working fallback prematurely.

### Stage 9 — RGB lamp, last

The lamp is already identified as a WiZ Mobile Portable Light 400 lm. Verify
its local Wi-Fi/LAN control interface and add a separate fail-safe adapter for
`green/yellow/red/off`; connect it only to accepted Blink/Attention state, run
a separate hardware smoke test, and document rollback. It must not become a
second sender, scheduler, or source of truth.

## Verification gate

Run focused tests for touched modules, then the full Python suite, Swift
compile/tests/release build, and `git diff --check`. For each Shortcut change
retain the iPhone Edit-tree evidence and physical result in the tree inventory.

## Checkpoint status

### DONE

- Mac core / lifecycle / persistence
- Attachments; Weather / Astronomy / Location / Attention
- Early Done
- CREATE baseline and DONE baseline
- Files one-file Acceptance
- Files Mac-side ToPhoneView
- CREATE validation contract and permanent Shortcut sync rule
- Unreachable CREATE diagnostic block removed
- Share `>1` rejection implemented and programmatically verified
- Integer Blinker validation implemented and programmatically verified
- Fractional Blinker `1.5` physically rejected on iPhone with no new Acceptance
  payload or `.ready`
- Documentation/contract checkpoint committed and pushed as `bef8fb5`
- Gray Mac `Start blinking` fixed and live-verified in the fresh release
  executable: an existing event remains editable when its old `1 day before`
  lead is no longer available, and `60 min before` can be selected. The test
  draft was cancelled without changing the user's event.

### CURRENT

- CREATE logic simulator harness is now available for fast, non-Apple
  validation and serialization checks. It is a test oracle only; real
  Shortcut/iPhone/iCloud acceptance remains authoritative for Apple-specific
  behavior.
- The simulator now covers exactly the three product roles: `Blink` CREATE,
  `Blink DONE`, and `Blink Files`. Existing Test/Stage2/WORK/Candidate/BACKUP
  objects are comparison profiles, not additional product architecture.

- Known-good CREATE transport restored physically through untouched
  `Blink Create Test`: fresh `.event.json` + `.ready` materialized in the
  exact Acceptance/ToMac mailbox. The remaining failure is candidate-only:
  `Blink Create Stage2 WORK` returns to the library without a fresh pair.
  Differential debugging is limited to the candidate's reachable path.
- CREATE candidate restored from untouched `Blink Create Test` in-place; source
  remains 93 actions and untouched. Gate A is now reapplied and saved in the
  candidate at 104 actions. Gate B is applied and must now be physically
  save/sync-verified
  verification.
- A live process snapshot on 2026-09-19 showed one `watcher.py` process and
  one `Blink.app` process, with one loaded watcher LaunchAgent. No duplicate
  instance is proven at this snapshot; however, singleton protection currently
  lives in launch/start scripts rather than an in-process watcher lock, so a
  direct second watcher launch remains an open lifecycle risk.
- iCloud sync/tree verification of the frozen CREATE candidate
- Remaining physical CREATE acceptance: fresh direct valid CREATE correlated
  to a new payload, one attachment,
  Share `>1` rejection, and representative text preservation
- canonical Files live-banner JPEG+PDF multi-file Acceptance (fallback boundary accepted; canonical dynamic path remains open)
- Combined Done + Files acceptance
- Same-ID freshness investigation and explicit semantic decision before
  Production (no implementation change until decided)
- Coherent Git commit/push after each accepted block; mandatory checkpoints
  before Production cutover and before destructive cleanup

### REMAINING

- Final CREATE/DONE/Files acceptance as needed
- Combined Done + Files acceptance
- Same-ID freshness investigation/decision before Production; implementation is
  intentionally deferred until the semantics are decided
- Acceptance → Production cutover
- Production smoke test
- One-icon Blink phone UX
- Final four-area cleanup
- Today Morning Briefing
- RGB lamp
- Bounded transport hardening

## Recovery after compact

Read this roadmap, the current contract, the tree inventory, the current status
report, and the active implementation plan. Check `git status --short`, recent
commits, and document contradictions before acting. Do not resume old “run the
32-action diagnostic” instructions; those are historical.
