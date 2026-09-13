# Blink Remaining Roadmap and Compaction Checkpoint

**Status:** authoritative post-Phase-7 roadmap
**Snapshot:** 2026-09-13
**Current stage:** **Stage 2 — iPhone Files acceptance, repaired one-file retest pending**

This file is the single persistent roadmap for work after the completed
original Phase 7. Running code and
[`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](../contracts/BLINK_CURRENT_STATE_CONTRACT.md)
remain the source of truth for implemented behavior. Historical design and
feasibility documents preserve chronology but never override this roadmap.

## Verified completed state

- Original Phases 1–7 are complete, including mailbox parser/transactions,
  opt-in watcher worker, native transport IDs, `%20` URL encoding, Phase 4B
  DONE acceptance, Phase 5 CREATE acceptance, Phase 6 controlled CREATE/DONE
  acceptance, and Phase 7 agenda refresh.
- Early Done is implemented for eligible unfinished personal events in Today
  and Upcoming, including future-start events. It preserves `start`, records
  `done_at`, moves the event to History, clears Attention/blinker eligibility,
  and is idempotent.
- A newly applied remote DONE sends one short confirmation titled
  `✓ Done — <event title>`, with optional description and scheduled time. The
  original notification remains unchanged; there is no action button and no
  `clear=true`. Replays, no-ops, stale, malformed, pending, and failed DONE
  commands are silent.
- Production mailbox remains disabled. `BLINK_MAILBOX_ENABLED` and
  `BLINK_MAILBOX_ROOT` are unset; `Blink_Acceptance/ToMac` is separate and
  empty; `Blink_Production/ToMac` is unused.
- Production default DONE Shortcut name remains `Blink DONE`; the optional
  `BLINK_NTFY_DONE_SHORTCUT_NAME` override is for controlled tests only.
- Current verification before the latest retest change: Python `218/218`,
  focused Python `111/111`, Swift release build PASS, compile PASS,
  `git diff --check` PASS, and healthy watcher. The latest source change adds
  an opt-in Files Shortcut-name override and has its focused regression test
  passing; the full suite is the next repository checkpoint.
- CREATE mailbox transport v2 is implemented at the Mac importer boundary as a
  flat Shortcut-friendly schema; v1 remains backward-compatible and both
  normalize into the same canonical CREATE transaction.

## Core remaining requirements

1. Production event-specific attachment viewing: Mac-owned event attachments
   staged through production `ToPhone`, a `Files/Open attachments` action,
   one-file direct open, multi-file chooser, Quick Look, and safe
   cleanup/retry/idempotency. The feasibility path is proven; production is
   not implemented.
2. Optional personal Today Morning Briefing containing every applicable Today
   event with importance, title, optional description, and scheduled date/time.
   It needs persistent enable/disable, watcher-owned delivery, local-time
   configuration, one-per-date dedupe, wake handling, timezone and empty-day
   rules, and coexistence with Weather/Astronomy.
3. Real USB RGB lamp/device adapter and physical acceptance remain a separate
   hardware task; do not invent a protocol before the device is known.
4. Numeric mailbox/package/worker limits remain a pre-production safety gate.
5. The final production iPhone entry point must be one Home Screen icon
   `Blink` for direct event creation. `Share -> Blink` must use the same
   unified production CREATE flow and support at most one attachment. DONE,
   Files, and Open attachments remain notification actions/internal Shortcuts,
   not separate Home Screen icons. The icon is deferred until Stage 4 after
   the unified production Shortcut is finalized.

## Stages

### Stage 0 — documentation and contract reconciliation — COMPLETE

Synchronize current-state documents with running code and the final DONE
acknowledgement decision; preserve historical chronology; establish this
roadmap and compaction recovery pointer.

### Stage 1 — manual acceptance of latest Done work — COMPLETE

Early Done, remote DONE confirmation, unchanged original notification,
duplicate/no-op silence, and Dock/Attention visual behavior were accepted on
the real installed Mac/iPhone path. Production mailbox remains disabled.

## Owner timing decision — 2026-09-13

Keep the existing Mac timing UI essentially unchanged. Do not introduce a new
timing model, fractional minutes, seconds, or a universal timing control.

- Reminders keep the existing presets, `Custom minutes`, integer minutes, and
  multiple reminder offsets.
- Blinker keeps the existing presets, integer minutes, and one blinker offset;
  it has no Custom value for now because Mac does not currently expose one.
- This decision is recorded only; timing work is not part of the current Files
  acceptance task.

### Simplified remaining roadmap

**[CURRENT] Finish Stage 2 Files acceptance.** The first one-file Files-only
retest explicitly targeted `Blink Files Stage2 WORK` and completed with a
checkmark but no chooser/PDF. The WORK acquisition prefix has since been
repaired to the proven `Get file from Shortcuts at path
Blink_Acceptance/ToPhone` → `Get Contents of File` pattern. Production
mailbox stays disabled; a new one-file physical retest is pending.

**[NEXT] Multi-file Files acceptance.** Only after one-file success, prepare a
2+ file package and perform one physical Files tap proving package isolation.

**[NEXT] Combined Done + Files acceptance.** Verify both ntfy actions are
independent after Files itself passes.

**[NEXT] Today Morning Briefing.** Add the personal briefing flow with the
existing Mac-owned scheduling/source-of-truth rules.

**[NEXT] Final phone setup.** Finalize one Home Screen entry `Blink`, Share →
Blink, and final Shortcut names/paths.

**[REQUIRED AFTER ACCEPTANCE] Cleanup.** Inventory all Blink Shortcuts and
iCloud roots, remove obsolete Test/WORK/proof/acceptance clutter only after
accepted replacements exist, and retain intentional recovery backups until
replacement is proven. Inventory and cleanup of the repository must also be
performed without deleting canonical data, source code, runtime state, or
authoritative documentation.

**[LATER] USB RGB lamp integration.** Keep hardware work separate.

## Compaction recovery

Before any future task, read this file plus the canonical description, current
contract, HANDOFF, implementation report, and next-thread prompt. Check
`git log --oneline -20`, `git status --short`, and `git diff`. If the stage or
production gate is unclear, stop and reconcile documents/source before acting.

Do not implement Stage 2–7 from this roadmap without an explicit owner task.
