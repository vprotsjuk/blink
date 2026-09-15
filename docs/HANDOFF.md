# Blink Work Handoff

**Snapshot:** 2026-09-14
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`
**Authority order:** this handoff for execution state; then
`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`,
`docs/implementation/BLINK_REMAINING_ROADMAP.md`, and
`docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md` for product truth.
Historical reports and old plans do not override those documents.

## Goal (current)

Prepare Blink for the next Codex task and continue the approved rebuild toward
three clean production Shortcuts (`Blink`, `Blink DONE`, `Blink Files`), with
the Mac as source of truth, a mandatory Mac Shortcuts GUI save-touch before
phone acceptance, separate ntfy `Done` and `Files` buttons, and the RGB lamp
only as the final stage.

## Status (what is done / what is broken / what is verified)

Done:

- The current plan and contracts were reconciled on 2026-09-14.
- Authoritative tree inventory and cleanup inventory exist.
- Existing Python suite, Swift contract runner, Swift release build, and
  `git diff --check` are green against the current WIP.
- Acceptance `Blink Files` one-file flow was physically proven on iPhone:
  ntfy green `Files` button → Shortcuts chooser → original PDF filename →
  Quick Look PDF. iPhone Mirroring is observation-only; physical button taps
  must be done on the real phone.
- The prior file-opening failure was caused by a stale/nonexistent Candidate
  Shortcut name and a zero-byte/technical transport object being sent to
  Shortcuts. The accepted path now resolves a package-scoped `ToPhoneView`
  folder and presents real attachment basenames.
- The recurring `{"detail":"Bad Request"}` messages were Codex
  connection/tool failures, not Shortcuts or iCloud evidence.
- The working Mac library still contains historical/test clutter and no clean
  canonical production trio. Do not rename/delete these objects until the
  production replacement passes.
- A new personal Today Morning Briefing WIP is present and its six focused
  tests pass. It is disabled by default and is not yet exposed in SwiftUI.
- The Mac editor timing correction is implemented: existing non-frozen events
  can change old reminder/blinker values after their lead time has elapsed;
  same-ID persistence and Attention-start regression tests pass.

Relevant implementation areas:

- `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift` and
  `Models.swift`: existing-event timing editability contract.
- `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`: regression tests
  for timing editability, same-ID save, and Attention start.
- `BLINK_UNDERSTANDING.md`: Russian-language architecture and current-state
  explanation requested for this project review.
- `app/personal_briefing.py`: pure formatting, local-time due decision,
  dedupe, empty-day behavior, and delivery-state helpers.
- `watcher.py`: loads optional
  `personal_briefing/personal_briefing_config.json`, invokes the briefing,
  sends through the existing ntfy path, and preserves briefing state.
- `test_personal_briefing.py`: focused tests, including watcher integration.

Not complete:

- Clean CREATE, DONE, and Files Shortcut trees have not all been rebuilt and
  physically accepted under canonical production names.
- Acceptance → Production paths and ntfy action targets have not been cut
  over. Production mailbox remains disabled.
- Personal briefing still needs a persistent SwiftUI toggle/time editor and
  its full watcher/UI acceptance matrix.
- Cleanup and RGB lamp connection are intentionally later stages.

## Key decisions (decision -> rationale)

- Mac is the source of truth -> iPhone is a synchronized execution target;
  names alone never prove body synchronization.
- Every Shortcut change requires DB/edit → real harmless Mac Shortcuts GUI
  edit/save → iCloud wait → complete iPhone Edit-tree/build-marker check →
  physical test. `Stop Shortcut` add/remove was diagnostic only.
- `Done` and `Files` are separate ntfy actions. `Done` transports EventID;
  `Files` transports PackageID. Never merge their buttons or use `clear=true`.
- Keep the chooser for now -> it is the physically proven one-file path;
  direct-open optimization is a later isolated change.
- Files must display original attachment basenames in deterministic order;
  technical package names/manifests are never user-facing.
- New native transport IDs use `yyyyMMddHHmmss-<9-digit-random>`; historical
  UUIDv4 packages remain accepted for compatibility.
- Empty reminders are not silently changed back to `[30, 0]`; the UI/import
  boundary must reject or explain an empty selection.
- Production cutover explicitly changes `Blink_Acceptance/ToMac|ToPhone|ToPhoneView`
  to `Blink_Production/...` and changes ntfy targets to `Blink`, `Blink DONE`,
  and `Blink Files`.
- Morning Briefing is optional, disabled by default, uses the existing watcher
  sender, and must not create a second scheduler.
- Cleanup is CRUD-safe: inventory `KEEP / DELETE / WHY` first; delete only
  agent-created or explicitly approved obsolete artifacts. Lamp is last.

## Tried & results (bullets)

- `python3 -m unittest -q test_personal_briefing.py` before implementation ->
  expected RED import failure because the module did not exist.
- Added the minimal pure briefing module -> six focused tests now pass.
- Added watcher integration -> focused tests and `py_compile` pass.
- Existing docs/plan commits: `a1a5b9c`, `b7bd95e`, `b8edc86`; this handoff/WIP
  checkpoint is committed as `d2327f1`.

## Open questions / risks

- The physically accepted Files candidate's Mac/iPhone editor view showed
  `Get contents of File`, while the intended contract says folder contents.
  Before production rebuild, inspect the complete phone body and preserve the
  physically proven behavior; do not infer from a truncated AX label.
- The current Shortcuts library has 17 entries, mostly historical candidates;
  production cleanup needs a fresh inventory before any deletion.
- The personal briefing config path/UI is not yet finalized. Keep it disabled
  until a persistent user-facing control exists and its tests pass.
- No physical user action is currently needed for the handoff. Later, ask the
  user to perform only the explicitly required iPhone acceptance taps.

## Next actions (3-7 concrete steps)

1. Run the full Python suite and Swift runner/release build against the current
   WIP; fix regressions before committing or extending it.
2. Add a persistent `personal_briefing` config model/store and a minimal
   SwiftUI settings control (enabled + valid local `HH:mm`), with empty/invalid
   time safety and focused Swift tests. Keep default disabled.
3. Update README/current contract/roadmap and this handoff to describe the
   briefing only as implemented-but-disabled until UI acceptance is complete.
4. Rebuild/verify clean Acceptance trees for CREATE, DONE, and Files, using
   build markers and the permanent GUI-touch sync gate. Do not ask the user to
   tap anything until a complete phone Edit-tree is confirmed.
5. Perform the representative physical acceptance matrix, then explicit
   Acceptance → Production path/name/URL cutover and Production smoke test.
6. Only after production passes, perform the KEEP/DELETE/WHY cleanup inventory
   and safe cleanup; connect and test the RGB lamp last.

## Files touched (paths)

Current WIP:

- `/Users/vitaliiprotsiuk/Desktop/Blink/app/personal_briefing.py`
- `/Users/vitaliiprotsiuk/Desktop/Blink/watcher.py`
- `/Users/vitaliiprotsiuk/Desktop/Blink/test_personal_briefing.py`

Authoritative documentation:

- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/HANDOFF.md`
- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/superpowers/plans/2026-09-14-blink-production-reconciliation.md`
- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/implementation/BLINK_REMAINING_ROADMAP.md`
- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`
- `/Users/vitaliiprotsiuk/Desktop/Blink/docs/implementation/BLINK_CLEANUP_INVENTORY_2026-09-14.md`

## Commands run (command -> outcome)

- `python3 -m unittest -q test_personal_briefing.py` -> 6 passed after WIP
  implementation.
- `python3 -m unittest -q` -> 225 passed, 1 skipped.
- `swift run -c release BlinkSwiftUITestRunner` -> all Swift contract tests
  passed.
- `swift build -c release` -> release build passed.
- `python3 -m py_compile watcher.py app/personal_briefing.py` -> passed.
- `git diff --check` -> passed after handoff and WIP edits.

## DoD (definition of done for current subtask)

The next Codex task can resume without chat history: the project state,
authoritative documents, current WIP, known risks, exact commands, and
ordered next actions are recorded here. No production Shortcut or user data
was deleted, and the physical lamp remains untouched.
