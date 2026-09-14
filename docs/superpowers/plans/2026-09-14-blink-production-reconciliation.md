# Blink Production Reconciliation and Shortcut Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile Blink's contracts and operational documentation, document the proven Shortcut trees, finish representative acceptance of the three production actions, then cut over safely and leave RGB-lamp integration as the final stage.

**Architecture:** Mac SwiftUI and `agenda.json` remain the source of truth. `watcher.py` remains the only sender; iPhone Shortcuts are transport adapters only. Acceptance uses isolated iCloud roots and explicit build/sync gates before Production names and paths are enabled.

**Tech Stack:** Python 3, SwiftUI, Apple Shortcuts, iCloud Drive, ntfy, unittest, Swift Package Manager.

## Global Constraints

- Mac remains the source of truth; iPhone Shortcuts never mutate canonical event state directly.
- `Done` and `Files` are separate ntfy actions; `Done` carries EventID and `Files` carries PackageID.
- CREATE accepts at most one incoming attachment; `Files` may display multiple attachments.
- Production defaults are exactly `Blink`, `Blink DONE`, and `Blink Files`.
- Acceptance paths must not be left in any production Shortcut or production ntfy action.
- Every Shortcut tree change requires a harmless Mac GUI save-touch, full iPhone Edit-tree confirmation, and only then a physical run/push.
- Do not silently restore `[30, 0]` after the user removes all reminders.
- Transport random IDs must contain exactly nine digits and must not be used as event IDs.
- Do not delete user data, canonical source, runtime state, authoritative docs, or the only working fallback before replacement acceptance.
- RGB lamp integration is the last stage and must not become a second sender, scheduler, or source of truth.

---

### Task 1: Reconcile authoritative documentation — COMPLETE

**Files:**
- Modify: `docs/implementation/BLINK_REMAINING_ROADMAP.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `docs/implementation/BLINK_STATUS_REPORT_2026-09-14.md`
- Modify: `docs/HANDOFF.md`
- Create: `docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`

**Interfaces:**
- Produces one current roadmap, one current contract, one report, and one explicit Shortcut-tree inventory.
- Historical reports remain chronology only and must link to the current documents instead of competing with them.

- [x] Step 1: Record the current acceptance boundary: one-file Files passed physically; multi-file, final CREATE/DONE/Files production acceptance, cutover, cleanup, briefing, and lamp remain open.
- [x] Step 2: Record the exact proven Files tree and the required CREATE/DONE tree contracts without claiming unverified physical success.
- [x] Step 3: Record separate ntfy actions and the Production-path migration gate.
- [x] Step 4: Record reminder/blinker timing, empty-reminder behavior, nine-digit transport IDs, filename/order rules, and one-icon UX.
- [x] Step 5: Mark superseded diagnostic instructions as historical and remove contradictory “run the old diagnostic” directions from current handoff guidance.
- [x] Step 6: Run `rg -n "current|NEXT|CURRENT|Stage 2|Production|Blink Files" docs` and resolve every current-state contradiction found in the four authoritative files.
- [x] Step 7: Run `git diff --check`.

### Task 2: Verify and harden software contracts before new Shortcut builds — VERIFIED BASELINE

**Files:**
- Inspect/modify: `app/notification_format.py`
- Inspect/modify: `app/to_phone_store.py`
- Inspect/modify: `app/mailbox_importer.py`
- Inspect/modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `test_notification_format.py`
- Test: `test_to_phone_store.py`
- Test: `test_mailbox_importer.py`
- Test: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- Preserve `build_event_payload`, `build_done_action`, `build_files_action`, `prepare_snapshot`, and importer compatibility.
- Any new validation must return a user-visible validation error rather than silently changing user input.

- [x] Step 1: Add/confirm tests for separate `Done` and `Files` actions and canonical names.
- [x] Step 2: Add/confirm tests for exact nine-digit transport random values where generation exists.
- [x] Step 3: Add/confirm tests for empty reminder selection semantics and independent blinker values.
- [x] Step 4: Add/confirm tests for deterministic attachment order and original safe basenames in `ToPhoneView`.
- [x] Step 5: Run focused Python and Swift tests; stop and investigate any failure before changing implementation.

### Task 3: Build and accept clean Acceptance Shortcuts

**Files:**
- Modify only the installed Mac/iPhone Shortcuts through the Shortcuts UI or the existing project-supported builder.
- Record: `docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`

**Interfaces:**
- `Blink` CREATE: direct launch and Share input, one attachment maximum, all event fields, reminder/blinker timing, canonical CREATE transport.
- `Blink DONE`: input `blink-done-v1|<event-id>`, canonical DONE package, `.ready` last, idempotent Mac application.
- `Blink Files`: input `blink-files-v1|<package-id>`, package-scoped view, real filenames only, chooser, Quick Look.

- [ ] Step 1: Build isolated Acceptance candidates with explicit build markers.
- [ ] Step 2: Perform Mac GUI save-touch after each tree change.
- [ ] Step 3: Confirm full action-body equality in iPhone Edit, not just name synchronization.
- [ ] Step 4: Physically test representative CREATE, DONE, one-file Files, multi-file Files, and combined Done+Files behavior.
- [ ] Step 5: Record evidence and keep production mailbox disabled during Acceptance.

### Task 4: Acceptance-to-Production cutover

**Files:**
- Modify: `app/notification_format.py` only if canonical action names/URLs require a code change.
- Modify: production Shortcut trees and iCloud transport only after Task 3 passes.
- Update: all four authoritative documents.

- [ ] Step 1: Inventory Acceptance and Production paths and confirm no active production reader points at Acceptance.
- [ ] Step 2: Migrate `ToMac`, `ToPhone`, and `ToPhoneView` to the final Production structure.
- [ ] Step 3: Rename/verify targets as `Blink`, `Blink DONE`, and `Blink Files`.
- [ ] Step 4: GUI save-touch, iPhone tree gate, canonical ntfy URL check, and small production smoke tests.
- [ ] Step 5: Enable production controls only after all gates pass.

### Task 5: Today Morning Briefing

**Files:**
- Inspect/modify: `app/ntfy_schedule.py`
- Inspect/modify: `watcher.py`
- Inspect/modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Test: `test_ntfy_schedule.py`
- Test: `test_watcher.py`
- Test: Swift test runner
- Update: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`

- [ ] Step 1: Define the persistent enable/disable and local-time contract.
- [ ] Step 2: Add failing tests for every Today event, importance, optional description, local-date dedupe, empty-day, wake, and Weather/Astronomy coexistence.
- [ ] Step 3: Implement through the existing watcher sender only.
- [ ] Step 4: Run focused tests and one full regression suite.

### Task 6: Final cleanup and RGB lamp integration

**Files:**
- Create/update: `docs/implementation/BLINK_CLEANUP_INVENTORY_2026-09-14.md`
- Modify only explicitly approved or agent-created obsolete artifacts after final acceptance.
- Add lamp adapter files only after the software production gate is complete.

- [ ] Step 1: Inventory Shortcuts, iCloud roots, and project/runtime paths as KEEP/DELETE/WHY.
- [ ] Step 2: Preserve fallback, canonical user attachments, source, tests, runtime state, and authoritative docs.
- [ ] Step 3: Remove only safe obsolete test/diagnostic artifacts after replacement acceptance.
- [ ] Step 4: Identify the lamp model, power, interface, and local control path.
- [ ] Step 5: Implement a fail-safe adapter with no second scheduler/sender.
- [ ] Step 6: Perform a separate lamp smoke test and document rollback/disconnect.

## Verification Matrix

| Area | Required check |
|---|---|
| Python contracts | `python3 -m unittest -q test_notification_format.py test_to_phone_store.py test_mailbox_importer.py test_ntfy_schedule.py` |
| Full Python regression | `python3 -m unittest -q` |
| Swift | package compile, test runner, release build |
| Docs | `git diff --check`; authoritative docs contain no contradictory current instructions |
| Shortcut sync | Mac GUI save-touch + full iPhone Edit-tree comparison |
| Physical acceptance | CREATE, DONE, one/multi-file Files, combined independent buttons |
| Production | canonical names/URLs/paths and production smoke test before enablement |
