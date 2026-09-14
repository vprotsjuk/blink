# Blink — next Codex task bootstrap

Read first, in this order:

1. `/Users/vitaliiprotsiuk/Desktop/Blink/docs/HANDOFF.md`
2. `/Users/vitaliiprotsiuk/Desktop/Blink/docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
3. `/Users/vitaliiprotsiuk/Desktop/Blink/docs/implementation/BLINK_REMAINING_ROADMAP.md`
4. `/Users/vitaliiprotsiuk/Desktop/Blink/docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`
5. `/Users/vitaliiprotsiuk/Desktop/Blink/docs/superpowers/plans/2026-09-14-blink-production-reconciliation.md`

Continue from `docs/HANDOFF.md` and its `Next actions`; do not restart the
project or follow older diagnostic instructions. The Mac is the source of
truth. SwiftUI edits local JSON, `watcher.py` is the only production sender,
scheduler, and future lamp owner, and iPhone Shortcuts are transport adapters.

Current uncommitted WIP adds an optional, disabled-by-default personal Today
Morning Briefing in `app/personal_briefing.py` and `watcher.py`, with focused
tests in `test_personal_briefing.py`. First run the full regression and Swift
checks, then add the persistent SwiftUI enable/time control before enabling it.

The main remaining product work is clean Acceptance rebuild and physical
acceptance of `Blink`, `Blink DONE`, and `Blink Files`, followed by an explicit
Acceptance → Production cutover. After every Mac Shortcut change:

```text
edit/build → harmless real Mac Shortcuts GUI edit/save → iCloud wait
→ full iPhone Edit-tree/build-marker confirmation → physical test
```

Do not treat name sync as body sync. Do not use iPhone Mirroring for physical
ntfy taps. Keep `Done` and `Files` as separate buttons, use original filenames
in Files, keep the chooser for now, retain legacy UUIDv4 importer compatibility,
and never silently restore cleared reminders to `[30, 0]`. Production paths
must be explicitly changed from `Blink_Acceptance/*` to `Blink_Production/*`
before production smoke testing. Cleanup is after production acceptance;
connect the RGB lamp last.

When a physical iPhone action is required, ask the user for that one action;
otherwise keep working without pausing for a progress report. Update
`docs/HANDOFF.md` after every meaningful step and before any further compact.
