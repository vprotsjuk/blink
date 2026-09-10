# Immediate Attachments and Resilient Events Implementation Plan

> **For agentic workers:** This plan is executed inline in the existing Blink workspace. Follow the TDD cycle for every behavior change.

**Goal:** Make row `Paste`/`Add Files` immediate and transactional, include attachment presence in remote queue invalidation, and prevent reload failures from replacing visible events with an empty list.

**Architecture:** Keep `agenda.json` as the single persisted event source and the existing filesystem attachment store. Separate short-lived row operations from editor drafts; row operations copy and verify all files before committing metadata, while editor drafts remain Save/Cancel based. Add an in-memory last-good event snapshot plus explicit load diagnostics; no second database or polling loop.

**Tech Stack:** SwiftUI/AppKit, Swift Foundation JSON/filesystem storage, Python watcher/ntfy queue, existing Swift test runner and Python unittest suite.

## Global Constraints

- Today/Upcoming row `Paste` and `Add Files` attach immediately and never open the editor or require Save.
- Editor attachment changes remain staged until Save and are discarded on Cancel.
- Batch row operations are all-or-nothing; existing attachments are untouched on failure.
- Persisted row counts equal physically finalized files only.
- History remains frozen and has no Paste/Add Files.
- `agenda.json` remains the only authoritative event source.
- Reload failure preserves the last-good snapshot and is distinct from a valid empty agenda.
- Personal attachment files, runtime state, and secrets remain outside Git.

## Task 1: Add failing tests for immediate row attachments and resilient loading

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`
- Modify: `test_ntfy_schedule.py`
- Modify: `watcher.py`

- [x] Add Swift tests for immediate file/image attachment, all-or-nothing copy failure, and load result states (loaded empty vs failed with last-good snapshot).
- [x] Add source-contract assertions that row actions call immediate store methods and editor actions retain draft methods.
- [x] Add Python tests proving `has_files` is included in remote reconcile signature and changes 0→1/1→0 cause replacement while count-only changes do not alter visible payload.
- [x] Run the targeted Swift/Python tests and confirm they fail for the missing behavior.

## Task 2: Implement atomic immediate attachment operations

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttachmentStore.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [x] Add a workspace operation that stages every regular input, verifies staged files, finalizes into the event owner folder, and rolls back only files created by that operation if any copy, verification, manifest, or agenda write fails.
- [x] Make `BlinkStore.addFiles` and `addJPEG` use that operation and reconcile the manifest from disk after success.
- [x] Change row `chooseFiles` and `paste` to call immediate store methods, reload the shared snapshot, and show concise success/error feedback without opening the editor.
- [x] Keep editor `chooseFiles`, editor `paste`, and editor drop on the existing draft workspace path.

## Task 3: Make event loading explicit and last-good

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUI/BlinkApp.swift`

- [x] Add a public load result/status containing loaded/error semantics, event count, source path, last successful load time, and last error.
- [x] Preserve `loadEvents` compatibility for existing callers while adding a result-based load path that never turns malformed/unreadable agenda data into `[]` in the UI.
- [x] Update ContentView and BlinkApp to retain the last-good snapshot on failure and show `Loading events…`/`Couldn’t refresh events` rather than `No events` for an error.
- [x] Add Health diagnostics for event load status, count, source, last-success time, and last error.
- [x] Ensure all tabs continue to read one shared snapshot and successful action reloads replace it atomically.

## Task 4: Include attachment presence in remote queue invalidation

**Files:**
- Modify: `watcher.py`
- Modify: `test_ntfy_schedule.py`

- [x] Add `has_files` to the signature payload used by `remote_reconcile_due`.
- [x] Keep notification payload unchanged for attachment count changes that do not change visible paperclip presence.
- [x] Verify 0→1 and 1→0 cause normal queue reconciliation without duplicate delivery for unchanged payloads.

## Task 5: Update current contracts and handoff

**Files:**
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/HANDOFF.md`
- Modify: `CODEX_NEXT_THREAD_PROMPT.md`

- [x] Replace current claims that row Paste/Add Files use editor drafts with the immediate-action contract.
- [x] Document all-or-nothing rollback, finalized-count invariant, `has_files` queue dependency, and last-good event loading.
- [x] Mark any superseded wording as historical/superseded rather than leaving contradictory current instructions.

## Task 6: Verification, release, and privacy gate

- [x] Run Swift targeted tests, Python unittest suite, Python compile checks, JSON/plist validation, and Swift release build.
- [x] Install/restart `Blink.app`, verify it reads `/Users/vitaliiprotsiuk/Desktop/Blink`, and check watcher/runtime status.
- [x] Perform manual row/editor UI verification; reload-failure behavior is covered by isolated Swift tests and the Health/error contract without mutating live agenda data.
- [x] Run `git status --short`, `git ls-files event_data`, and `git check-ignore -v event_data/attachments/*`; confirm no personal files/runtime state/secrets are tracked.
- [x] Commit and push through the configured normal remote workflow only after all checks pass.

Verification record (2026-09-10): Python `unittest` 130/130 passed; Swift runner passed; Python compile and Swift release build passed; installed Blink relaunched as PID 83557; watcher heartbeat remained fresh; live Upcoming/Astronomy/Weather data and editor attachment preview were verified through the UI. The final commit/push is intentionally left as the last gate after this plan update.
