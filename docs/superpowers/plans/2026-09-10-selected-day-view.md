# Selected Day View — implementation plan

## Scope

Add a temporary selected-day mode driven by the existing shared event snapshot. The first tab becomes a compact local-date label while a day is selected; no second store, persistence, or new calendar database is introduced.

## Work items

- [x] Add timezone-safe local-day normalization, deterministic selected-day filtering/sorting, and compact tab/date labels.
- [x] Add selected-day state to `ContentView`; clear search on entry, preserve the mode across other tabs, and implement `Exit` back to Today.
- [x] Wire calendar double-click to selected-day navigation while preserving single-click date selection; protect dirty editor drafts from accidental loss.
- [x] Add selected-day page/header/empty state/new-event prefill and reuse existing `EventRows`/`EventRowActions` with per-event frozen/history policy.
- [x] Ensure selected-day edits, deletes, Done/Off, recurrence, and attachment actions use existing store behavior; show date-move feedback.
- [x] Keep load-error last-good snapshot behavior and suppress Today attention pulse on the dynamic selected-day tab.
- [x] Add focused Swift tests for local-date boundaries, sorting, lifecycle inclusion, navigation/source contracts, and calendar gesture wiring.
- [x] Update `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`, `docs/HANDOFF.md`, and `CODEX_NEXT_THREAD_PROMPT.md`.
- [x] Run Swift/Python tests, release build, diff checks, deploy the app bundle, and restart the Blink LaunchAgent.
- [ ] Complete a manual UI pass for double-click, tab persistence, Exit, empty day, and editor safety after the Mac is unlocked.

## Verification checklist

- [ ] No persistence changes for selected-day mode; relaunch returns to Today.
- [ ] Today/Upcoming/History behavior remains unchanged outside selected-day rendering.
- [ ] No runtime data, secrets, or user attachments are committed.
