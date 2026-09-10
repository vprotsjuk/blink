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

- [ ] Add Swift tests for immediate file/image attachment, all-or-nothing copy failure, and load result states (loaded empty vs failed with last-good snapshot).
- [ ] Add source-contract assertions that row actions call immediate store methods and editor actions retain draft methods.
- [ ] Add Python tests proving `has_files` is included in remote reconcile signature and changes 0→1/1→0 cause replacement while count-only changes do not alter visible payload.
- [ ] Run the targeted Swift/Python tests and confirm they fail for the missing behavior.

## Task 2: Implement atomic immediate attachment operations

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttachmentStore.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`

- [ ] Add a workspace operation that stages every regular input, verifies staged files, finalizes into the event owner folder, and rolls back only files created by that operation if any copy, verification, manifest, or agenda write fails.
- [ ] Make `BlinkStore.addFiles` and `addJPEG` use that operation and reconcile the manifest from disk after success.
- [ ] Change row `chooseFiles` and `paste` to call immediate store methods, reload the shared snapshot, and show concise success/error feedback without opening the editor.
- [ ] Keep editor `chooseFiles`, editor `paste`, and editor drop on the existing draft workspace path.

## Task 3: Make event loading explicit and last-good

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUI/BlinkApp.swift`

- [ ] Add a public load result/status containing `loaded`, `loading`, or `error` semantics, event count, source path, last successful load time, and last error.
- [ ] Preserve `loadEvents` compatibility for existing callers while adding a throwing/result-based load path that never turns malformed/unreadable agenda data into `[]`.
- [ ] Update ContentView and BlinkApp to retain the last-good snapshot on failure and show `Loading events…`/`Couldn’t refresh events` rather than `No events` for an error.
- [ ] Add Health diagnostics for event load status, count, source, last-success time, and last error.
- [ ] Ensure all tabs continue to read one shared snapshot and successful action reloads replace it atomically.

## Task 4: Include attachment presence in remote queue invalidation

**Files:**
- Modify: `watcher.py`
- Modify: `test_ntfy_schedule.py`

- [ ] Add `has_files` to the signature payload used by `remote_reconcile_due`.
- [ ] Keep notification payload unchanged for attachment count changes that do not change visible paperclip presence.
- [ ] Verify 0→1 and 1→0 cause normal queue reconciliation without duplicate delivery for unchanged payloads.

## Task 5: Update current contracts and handoff

**Files:**
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/HANDOFF.md`
- Modify: `CODEX_NEXT_THREAD_PROMPT.md`

- [ ] Replace current claims that row Paste/Add Files use editor drafts with the immediate-action contract.
- [ ] Document all-or-nothing rollback, finalized-count invariant, `has_files` queue dependency, and last-good event loading.
- [ ] Mark any superseded wording as historical/superseded rather than leaving contradictory current instructions.

## Task 6: Verification, release, and privacy gate

- [ ] Run Swift targeted tests, Python unittest suite, Python compile checks, JSON/plist validation, and Swift release build.
- [ ] Install/restart `Blink.app`, verify it reads `/Users/vitaliiprotsiuk/Desktop/Blink`, and check watcher/runtime status.
- [ ] Perform manual row Paste/Add Files, editor Save/Cancel, small-window footer, and reload-failure checks.
- [ ] Run `git status --short`, `git ls-files event_data`, and `git check-ignore -v event_data/attachments/*`; confirm no personal files/runtime state/secrets are tracked.
- [ ] Commit and push through the configured normal remote workflow only after all checks pass.
