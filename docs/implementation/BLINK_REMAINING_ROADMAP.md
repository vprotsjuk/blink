# Blink Remaining Roadmap and Compaction Checkpoint

**Status:** authoritative post-Phase-7 roadmap
**Snapshot:** 2026-09-12
**Current stage:** **Stage 2 — production iPhone attachment viewing**

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
- Current verification: Python `195/195`, focused Python `152/152`, Swift
  runner PASS, release build PASS, compile PASS, plist lint PASS,
  `git diff --check` PASS, and healthy watcher.
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

### Simplified remaining roadmap

**[CURRENT] Finish simple iPhone Shortcuts.** Reuse the single
`Blink Create Stage2 WORK` candidate, keep CREATE flat/v2 and minimal, and
retain the already prepared DONE and Files candidates. Production mailbox stays
disabled.

**[NEXT] One real iPhone acceptance pass.** Prove CREATE, CREATE with one
attachment, DONE, and Files/Open attachments on the owner’s phone.

**[NEXT] Today Morning Briefing.** Add the personal briefing flow with the
existing Mac-owned scheduling/source-of-truth rules.

**[NEXT] Final phone setup.** Finalize one Home Screen entry `Blink`, Share →
Blink, and final Shortcut names/paths.

**[NEXT] Cleanup.** Remove obsolete Test/WORK/proof Shortcuts and temporary
files only after accepted replacements exist; retain intentional backups.

**[LATER] USB RGB lamp integration.** Keep hardware work separate.

## Compaction recovery

Before any future task, read this file plus the canonical description, current
contract, HANDOFF, implementation report, and next-thread prompt. Check
`git log --oneline -20`, `git status --short`, and `git diff`. If the stage or
production gate is unclear, stop and reconcile documents/source before acting.

Do not implement Stage 2–7 from this roadmap without an explicit owner task.
