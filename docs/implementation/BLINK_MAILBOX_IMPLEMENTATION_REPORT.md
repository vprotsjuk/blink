# Blink Mailbox Implementation Report

## Current status

PHASE 1 COMPLETE  
PHASE 2A COMPLETE (parser/state foundation)
PHASE 2B COMPLETE (temporary-root canonical mutation/recovery)
PHASE 3 COMPLETE (opt-in in-process watcher worker; production mailbox remains disabled)
PHASE 4A COMPLETE (Mac ntfy DONE action support; disabled pending manual iOS acceptance)
PHASE 4B PENDING (manual iPhone acceptance)
PHASE 5 NOT STARTED

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

- Added `app/mailbox_importer.py` with strict UUIDv4 package discovery,
  `.ready` semantics, DONE/CREATE v1 parsing, and pending-sync vs malformed
  classification.
- CREATE v1 parser accepts user intent only: non-recurring, explicit timezone,
  reminder intent, attention level, and `blinker_intent.minutes_before`.
- Added regular-file/symlink/path/basename safety checks, multiple-attachment
  rejection, and unrelated-file isolation.
- Added local journal records, restart-readable pending journal state, atomic
  indefinite processed UUID tombstones, local staging, and exact-package local
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
- Processed UUID tombstones retain durable result/event metadata indefinitely.

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

## Files changed

- `.gitignore` — ignore agenda lock and mailbox runtime state.
- `app/agenda_store.py` — shared Python lock and lock-aware agenda persistence.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AgendaFileLock.swift` — Darwin
  implementation interoperable with Python `flock`.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift` — shared lock around
  all Swift agenda read/modify/write and repair paths.
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift` — Swift lock and
  Python interoperability tests.
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
  `docs/HANDOFF.md`, `CODEX_NEXT_THREAD_PROMPT.md` — synchronized implementation
  status; feasibility contracts unchanged.

## Tests

- `.venv/bin/python -m unittest -q` → 176 tests passed.
- `.venv/bin/python -m unittest -q test_notification_format test_ntfy_schedule test_watcher` → 88 tests passed.
- `swift run BlinkSwiftUITestRunner` → all Swift store/UI tests passed,
  including Python `flock` interoperability.
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
- Manual iPhone acceptance is still required before enabling
  `BLINK_NTFY_DONE_ACTION_ENABLED` in any real deployment. The expected
  inspection chain is: `event-abc_123` →
  `blink-done-v1|event-abc_123` →
  `shortcuts://run-shortcut?name=Blink+DONE&input=text&text=blink-done-v1%7Cevent-abc_123` →
  `view, Done, <encoded-shortcut-url>`.
- Phase 4B manual acceptance will temporarily set
  `BLINK_NTFY_DONE_SHORTCUT_NAME="Blink DONE Test"`; production default stays
  `Blink DONE`.

## Known risks / blockers

- Phase 1 changes are committed, but the existing live watcher/app may need the
  normal LaunchAgent restart cycle after future release deployment.
- Real iCloud access, ntfy actions, and Shortcut changes remain intentionally
  disabled. The Mac-side DONE action is implemented but remains opt-in and
  requires manual iPhone acceptance; production mailbox enablement still
  requires a separate approved pass.

## Open owner decisions

- Numeric transport size/package caps remain to be measured and selected.
- Exact ntfy Actions syntax and iOS Shortcut URL acceptance remain manual
  acceptance items.
- DONE notification acknowledgement UX remains open; `clear=true` is not
  selected.

## Next implementation tasks

1. Manually accept the ntfy DONE action on iPhone (Phase 4B), with the feature
   flag enabled only in a controlled test.
2. Then implement the production CREATE Shortcut path (Phase 5) only after
   the remaining transport/acknowledgement decisions are approved.

## Last checkpoint

2026-09-12. Phase 1 commit: `98753a8 Add shared Blink agenda locking`. Phase
2A commit: `421963d Add Blink mailbox importer core`. Phase 2B commit:
`aa50f96 Implement Blink mailbox event transactions`. Phase 3 commit:
`df50af7 Integrate Blink mailbox worker with watcher`. Additional Phase 2B
coverage: `5cc53de Add mailbox iteration coverage`. Worker diagnostics:
`47a381b Expand mailbox worker diagnostics`. Phase 4A:
`a8c682b Add Blink ntfy DONE action support`. Phase 4B preparation:
`cf75720 Prepare configurable Blink DONE shortcut name`. Verification fixture:
`05c6b3f Stabilize Swift history test fixture`.
