# Blink Mailbox Implementation Report

## Current status

PHASE 1 COMPLETE  
PHASE 2A COMPLETE (parser/state foundation)
PHASE 2B COMPLETE (temporary-root canonical mutation/recovery)
PHASE 3 COMPLETE (opt-in in-process watcher worker; production mailbox remains disabled)
PHASE 4A COMPLETE (Mac ntfy DONE action support; disabled by default)
PHASE 4B COMPLETE (real iPhone ntfy DONE action accepted)
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

- `.venv/bin/python -m unittest -q` → 181 tests passed.
- `.venv/bin/python -m unittest -q test_mailbox_importer` → 29 tests passed.
- `.venv/bin/python -m unittest -q test_notification_format test_ntfy_schedule test_watcher`
  → 89 tests passed.
- Previous Phase 4 notification/watcher focused suite remains covered by the
  full run; its prior checkpoint was 88 passing tests.
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
- Phase 4B manual iPhone acceptance passed. The verified chain is:
  `EVENT123` → `blink-done-v1|EVENT123` →
  `shortcuts://run-shortcut?name=Blink%20DONE%20Test&input=text&text=blink-done-v1%7CEVENT123` →
  `view, Done, <encoded-shortcut-url>` →
  `20260912163022-101411924.done.json` + `.ready`.
- The controlled flags were one-shot only; production default remains
  `Blink DONE`, and `BLINK_NTFY_DONE_ACTION_ENABLED` remains off by default.

## Known risks / blockers

- Phase 1 changes are committed, but the existing live watcher/app may need the
  normal LaunchAgent restart cycle after future release deployment.
- Real production iCloud access and mailbox processing remain intentionally
  disabled. The Mac-side DONE action remains opt-in by default; no Shortcut
  or feasibility package was modified by the Mac test.

## Open owner decisions

- Numeric transport size/package caps remain to be measured and selected.
- Exact ntfy Actions syntax and iOS Shortcut URL acceptance remain manual
  acceptance items.
- DONE notification acknowledgement UX remains open; `clear=true` is not
  selected.

## Next implementation tasks

1. Prepare the exact Phase 5 `Blink Create Test` migration checklist without
   changing the Shortcut or enabling production mailbox processing.
2. Perform controlled Phase 6 mailbox acceptance only in a clean inbox, never
   by pointing the importer at the historical feasibility inbox.

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
passed with native DONE package `20260912163022-101411924`.
