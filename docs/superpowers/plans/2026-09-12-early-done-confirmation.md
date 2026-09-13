# Early Done and Remote Confirmation Implementation Plan

> **For agentic workers:** Execute this plan inline with TDD and keep the production mailbox disabled.

**Goal:** Expose canonical Done for eligible unfinished personal events in Upcoming and send one short confirmation push only after a remote DONE is applied.

**Architecture:** Reuse `BlinkStore.complete`, `agenda_store.complete_event`, and the existing mailbox worker transaction. Add no alternate completion path or scheduler. The mailbox worker will call a small confirmation sender only for an `applied` remote DONE result; duplicate/no-op/stale results remain silent.

**Tech Stack:** SwiftUI/Swift Package Manager, Python 3, unittest, ntfy HTTP headers.

## Global Constraints

- Production mailbox remains disabled and `Blink_Production/ToMac` remains unused.
- Do not modify iPhone Shortcuts or add `clear=true`.
- Preserve original event `start`; completion records `done=true` and actual `done_at`.
- Today, Upcoming, context-menu Done, and remote DONE converge on existing canonical semantics.
- Attachments, recurrence behavior, weather, astronomy, and system notifications remain unchanged.

---

### Task 1: Audit and test Upcoming Done visibility

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [x] Add a source-contract test proving `EventListView` passes `showsDone: true`.
- [x] Run the Swift runner and confirm the new test fails before the UI change.
- [x] Pass `showsDone: true` in `EventListView` and rerun the focused runner.
- [x] Add model tests for future completion preserving `start`, recording `done_at`, moving to History, and removing attention eligibility.

### Task 2: Add canonical remote DONE confirmation

**Files:**
- Modify: `app/mailbox_importer.py`, `watcher.py`
- Test: `test_mailbox_importer.py`, `test_watcher.py`, `test_notification_format.py`

- [x] Add failing tests for one confirmation on `applied`, no confirmation on `noop_done`/`stale_event`, title/description/scheduled time formatting, no action button, and failure without rollback.
- [x] Implement a bounded confirmation callback from the mailbox worker using existing ntfy request/sender primitives.
- [x] Keep notification failure diagnostic-only after `done=true` is committed.
- [x] Run focused Python tests, then the full suite.

### Task 3: Documentation and verification

**Files:**
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`, `docs/HANDOFF.md`, `CODEX_NEXT_THREAD_PROMPT.md`, `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`

- [x] Record Done semantics, future-event History behavior, idempotency, remote confirmation format, and production-off status.
- [x] Run Python tests/compile, Swift runner/release build, plist lint, `git diff --check`, and `./status_watcher.command`.
- [x] Keep acceptance mailbox OFF and confirm `git status --short` and recent log.
