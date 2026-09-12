# Blink Mailbox Implementation Report

## Current status

PHASE 1 COMPLETE  
PHASE 2A COMPLETE (parser/state foundation; no agenda mutation or production
mailbox wiring)  
PHASE 2B NOT STARTED

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

## Files changed

- `.gitignore` — ignore the runtime agenda lock file.
- `app/agenda_store.py` — shared Python lock and lock-aware agenda persistence.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AgendaFileLock.swift` — Darwin
  implementation interoperable with Python `flock`.
- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift` — shared lock around
  all Swift agenda read/modify/write and repair paths.
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift` — Swift lock and
  Python interoperability tests.
- `test_agenda_store.py` — Python contention and lost-update regression tests.
- `app/mailbox_importer.py` — Phase 2A parser and local transport state
  primitives.
- `test_mailbox_importer.py` — Phase 2A temporary-root tests.
- `docs/design/BLINK_MAILBOX_IMPORTER_DESIGN.md` — approved-baseline wording
  cleanup only.
- `docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md` — this
  persistent checkpoint.

## Tests

- `.venv/bin/python -m unittest -q` → 153 tests passed.
- `.venv/bin/python -m unittest -q test_mailbox_importer` → 18 tests passed.
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

## Known risks / blockers

- Phase 1 changes are committed, but the existing live watcher/app may need the
  normal LaunchAgent restart cycle after future release deployment.
- Phase 2A intentionally has no canonical event mutation, attachment finalizer
  integration, worker thread, ntfy action, or real iCloud access yet.
- Agenda lock is mandatory for Phase 2B; any newly discovered agenda writer
  must adopt it before importer writes are enabled.

## Open owner decisions

- Numeric transport size/package caps remain to be measured and selected.
- Exact ntfy Actions syntax and iOS Shortcut URL acceptance remain manual
  acceptance items.
- DONE notification acknowledgement UX remains open; `clear=true` is not
  selected.

## Next implementation tasks

1. Review/accept Phase 2A parser/state behavior and begin Phase 2B canonical
   event mutation plus attachment transaction.
2. Keep all mutation tests on temporary roots; do not connect watcher or the
   real iCloud inbox until Phase 2B and recovery tests pass.

## Last checkpoint

2026-09-12. Phase 1 commit: `98753a8 Add shared Blink agenda locking`. Phase
2A commit: `Add Blink mailbox importer core` (current HEAD at checkpoint; see
`git log`).
