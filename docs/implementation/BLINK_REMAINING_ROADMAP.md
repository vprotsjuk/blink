# Blink — authoritative roadmap

**Snapshot:** 2026-09-14
**Status:** Acceptance Files one-file flow passed physically; production cutover is not yet complete.
**Authority:** this roadmap, [`BLINK_CURRENT_STATE_CONTRACT.md`](../contracts/BLINK_CURRENT_STATE_CONTRACT.md), and [`BLINK_SHORTCUT_TREES_2026-09-14.md`](BLINK_SHORTCUT_TREES_2026-09-14.md) describe current state. Older reports preserve history only.

## Product target

Blink creates and manages personal events on the Mac and sends ntfy actions to
the iPhone. The Mac is the source of truth. The final phone UX is one Home
Screen entry `Blink`; `Share → Blink` creates an event from one shared file.
`Done` and `Files` are separate internal notification actions.

## Current verified state

- SwiftUI, `agenda.json`, local event attachments, importer, watcher, weather,
  astronomy, lifecycle, Done handling, and ntfy formatting are implemented.
- CREATE/DONE transport is implemented and has controlled Acceptance coverage.
- Files staging is implemented with a flat integrity package and an atomic,
  package-scoped `ToPhoneView` containing only real attachment basenames.
- The Acceptance Files candidate was physically tested on iPhone: green ntfy
  `Files` button → Shortcuts → chooser with the original filename → PDF in
  Quick Look. A one-file result is accepted; multi-file acceptance is open.
- `Done` and `Files` are independent ntfy actions. `Done` carries EventID;
  `Files` carries PackageID. No `clear=true` is used.
- Production mailbox and `Blink_Production/ToMac` remain disabled/unused.
- The physical USB RGB lamp is available but intentionally not connected yet.

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

The last tree is the physically proven one-file path. The first two still
require final clean-tree verification and representative physical acceptance
under their canonical Production names before cutover.

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
- Reminder presets `1440, 720, 300, 60, 30, 10, 5, 0`, multiple
  reminders, non-negative integer custom values, and independent blinker.
- Do not silently restore `[30, 0]` after the user clears reminders.
- Verify transport IDs have exactly nine random digits and are never event IDs.
- Verify deterministic `__01__`, `__02__` attachment ordering and safe original
  basenames.

### Stage 2 — clean Acceptance Shortcut trees

Build isolated, marked candidates for `Blink`, `Blink DONE`, and `Blink Files`.
After every change use the permanent synchronization gate. Keep the production
mailbox off. Physically test representative direct CREATE, Share CREATE, DONE,
one-file Files, multi-file Files, and one event with both independent buttons.

### Stage 3 — Acceptance → Production cutover

Do not merely rename candidates. Explicitly migrate and verify `ToMac`, `ToPhone`
and `ToPhoneView` paths, replace candidate names/URLs with `Blink`, `Blink DONE`
and `Blink Files`, GUI-save-touch, confirm complete iPhone trees, and run a
small Production smoke test. Enable production controls only after all three
canonical trees pass.

### Stage 4 — final phone UX

Place only `Blink` on the Home Screen. Keep `Blink DONE` and `Blink Files` as
notification/internal actions. The intermediate Shortcuts screen is accepted
for now because the proven private `shortcuts://run-shortcut` path opens it;
removing it is a later optional optimization.

### Stage 5 — Today Morning Briefing

Add an optional daily briefing for every applicable Today event, with
importance, title, optional description, scheduled date/time, local-time
rules, dedupe, empty-day behavior, wake handling, and Weather/Astronomy
coexistence. It must use the existing watcher sender and have a persistent
enable/disable control. Do not add a second scheduler or sender.

### Stage 6 — cleanup

Before deletion inventory Shortcuts, iCloud roots, and project/runtime paths as
`KEEP / DELETE / WHY`. Remove obsolete tests, backups, diagnostics, and
acceptance clutter only after Production replacement passes. Never remove user
attachments, source, tests, runtime state, authoritative docs, or the only
working fallback prematurely.

### Stage 7 — RGB lamp, last

Identify the lamp's exact model, power, and control interface; add a separate
fail-safe adapter; connect it only to accepted Blink/Attention state; run a
separate hardware smoke test and document rollback. It must not become a second
sender, scheduler, or source of truth.

## Verification gate

Run focused tests for touched modules, then the full Python suite, Swift
compile/tests/release build, and `git diff --check`. For each Shortcut change
retain the iPhone Edit-tree evidence and physical result in the tree inventory.

## Recovery after compact

Read this roadmap, the current contract, the tree inventory, the current status
report, and the active implementation plan. Check `git status --short`, recent
commits, and document contradictions before acting. Do not resume old “run the
32-action diagnostic” instructions; those are historical.
