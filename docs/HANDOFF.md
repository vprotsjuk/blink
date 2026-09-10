# Blink Work Handoff

**Snapshot:** 2026-09-09  
**Full technical description:** [`BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`](../BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md)  
**Next Codex prompt:** [`CODEX_NEXT_THREAD_PROMPT.md`](../CODEX_NEXT_THREAD_PROMPT.md)

## Goal (current)
Keep Blink's independent runtime architecture stable while fixing personal-event visibility and making event attention state clear in the app and phone notifications.

The canonical current-state contract for future agents is [`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](contracts/BLINK_CURRENT_STATE_CONTRACT.md). Update it together with this handoff whenever a boundary or user-visible contract changes.

## Pre-change reconciliation checkpoint (2026-09-10)

This checkpoint is an audit only; no source code was changed for it.

- **Snooze origin:** the old behavior came from `docs/superpowers/plans/2026-09-07-blink-next-core-architecture.md`, which was created in the initial project snapshot (`81c734f`) and explicitly planned Snooze state, timing, and reminder recalculation. The old `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md` also documented Snooze as a current feature. The current Python and Swift runtime do not implement Snooze behavior or UI; they only remove legacy `snoozed_until`/`snoozed_for_minutes` fields during migration. Therefore the observed conflict is stale TЗ/documentation, not a new runtime implementation restored by this thread. Handoff was unreliable because the full description and one historical plan were allowed to contradict the later owner decision and current code.
- **Recurring attachment risk:** the current implementation still resolves recurring attachment ownership through one stable `series_id` folder. The new owner decision is stricter: every occurrence must own its own folder and a recurring successor must start without attachments. Before changing that rule, audit `agenda.json`, every `event_data/attachments/*` folder, recurrence tests, and all Swift/Python owner-resolution paths. Migration must copy shared files to each occurrence, update manifests only after verified copies, preserve the source until verification succeeds, and never delete or overwrite user files implicitly. The audit found no live `series_id` events in the current `agenda.json`; the existing live attachment is under a non-recurring event ID, but this does not replace the required code/test migration audit.
- **Git boundary:** `.gitignore` excludes `agenda.json`, local settings/state, `event_data/` (attachments and drafts), `Blink.app/`, build products, backups, and virtualenvs. Source code, contracts, plans, and documentation remain trackable. `git status` is clean and the existing live PDF under `event_data/attachments/` is ignored, not tracked. Before the next commit, repeat `git status --short`, `git ls-files event_data`, and `git check-ignore -v event_data/attachments/*` so no real PDF/JPG/DWG/Excel can enter the public repository.
- **Current gate:** reconciliation is accepted by the owner. Implementation now follows the current contract: no product Snooze, independent Blinker, per-occurrence attachment ownership, unified Paste, editor-only Drop, and frozen History.

## Status (what is done / what is broken / what is verified)
Checkpoint and source prompt saved. The briefing timing regression is covered: saving Weather or Astronomy after today's configured local time records the change instant and defers that newly configured briefing to the next local day instead of sending immediately; saving before the target still sends today, and ordinary missed targets retain late catch-up. Python verification: 120 passing. Swift test runner and release build pass. The live watcher was restarted with the fix and did not emit another Weather/Astronomy briefing for today's already-past saved targets. Astronomy push rise/set labels now use thin arrows after the matching icon (`☀️ ↑/↓`, `🌙 ↑/↓`) in grouped lines and individual titles; large arrows remain phase-only. Disabled past unfinished events now remain in History, new GUI events default the blinker to `At time`, personal push titles include the event attention color icon, editing a completed event into the future reopens it, and stale completed records with future starts are repaired on load. Enabled overdue unfinished events now pulse in the app until `Done`; Blink's app-owned `Today` tab alternates between normal text and the highest active priority color from every tab. It is app-owned because macOS `TabView.tabItem` ignores dynamic label color. This is UI-only and does not change lifecycle or sending. Event toggle labels are `On`/`Off`, with disabled row text dimmed but its priority dot retained. Astronomy now uses `☀️` for all Sun events and never emits `🌅`. Moon-related messages use `Waxing Moon`/`Waning Moon` on ordinary days and reserve `New Moon`/`Full Moon` for the exact event day; one large `⬆️`/`⬇️` phase arrow appears on ordinary days only, with one countdown, no textual `Moon is …` line, and no repeated Sunset or standalone Moon event name in the body. Thin `↑`/`↓` UI arrows now mean only rise/set; large arrows mean only waxing/waning. The watcher owns the shared formatter; SwiftUI mirrors the approved icon language only. Astronomy also presents a scrollable Weather-style settings surface plus today's Sun/Moon summary. Its upper settings and lower summaries share the same two columns, so Sun and Moon remain vertically aligned. Weather now uses day/night icons for compact temperature and humidity lines; the Astronomy briefing respects `Use Weather briefing time` by either appending to Weather or sending a separate ntfy briefing. The app reads live JSON from `/Users/vitaliiprotsiuk/Desktop/Blink`; an empty UI after a build is an app-process restart issue, not a data-loss state. Watcher remains the only sender.

The Blink-local event attachments feature is implemented. It keeps multiline event text, draft/permanent attachment folders under `event_data/`, unified clipboard paste (file URLs first, otherwise image-to-JPEG), paperclip-only personal pushes, frozen History, double-click editing in Today/Upcoming, compact paperclip/count rows with a filename/type popover, folder buttons, and tab-aware context actions. Every occurrence owns an event-ID folder; the editor has one unified attachment panel and Paste action, with editor-only file drop. The Today header owns a round blue `+` action for New Event, and every navigation tab has a subtle pointer-hover state. The editor modal now uses a window-safe height with a top-aligned scroll view, so Title/Description, attachments, reminders, Blinker, and Cancel/Save remain reachable on shorter windows. The historical design/plan files are retained for traceability and marked `HISTORICAL / SUPERSEDED`; the current contract and full description are authoritative.

## Key decisions (decision -> rationale)
- The `Use Weather briefing time` switch controls delivery mode -> enabled appends a plain `ASTRONOMY` section to Weather, disabled sends a separate native ntfy `ASTRONOMY` title; Markdown markers are not sent because the phone displays them literally.
- Astronomy individual notifications use event time only -> no redundant offset configuration.
- Eclipses are removed completely -> feature is not supported and must not appear as a stale blocker.
- Legacy eclipse keys are ignored on load -> existing user files remain safe.
- Disabled past events remain inspectable in History -> On/Off never behaves as Delete.
- The installed build now freezes History; reuse is available through `Duplicate as new event`, which creates a new event ID and attachment owner.
- Existing stale records with `done=true` and a future start are repaired during app load, persisted with `done=false`, and therefore physically move out of `History` without requiring another edit.
- New event default blinker is independent `At event` (`blinker_minutes_before = 0`); it is not attached to a reminder row.
- Personal push titles use `🟢/🟡/🔴` -> color is visible on iPhone while ntfy priority headers remain independent.
- Remote queue signature includes title, description, and attention level -> queued payloads are rebuilt when their visible content or color changes.
- Active-event row and `Today` tab pulsing are presentation-only -> `EventSnapshot.active` remains the single lifecycle source and `AttentionManager` remains the single global-output owner.
- `On`/`Off` replaces `Enabled`/`Disabled` -> user sees state without confusing the toggle with `Done`; Off rows dim only non-priority text.
- Shared lunar phase and countdown formatters serve grouped and individual Astronomy pushes -> one large direction arrow appears exactly once, phase-boundary events omit it, and daily/event-time messages cannot drift.
- Saving a briefing after today's target defers that newly configured Weather/Astronomy briefing to the next local day -> the Save action never acts as an immediate late catch-up for the new time, while ordinary missed targets still retain late catch-up.
- History is frozen -> past events can only be duplicated as new events or deleted; ordinary Edit remains available only in Today/Upcoming.
- Attachments stay under the Blink root in `event_data/` -> local files are staged before Save, never sent through ntfy, and excluded from GitHub.

## Tried & results (bullets)
- Python verification -> `Ran 118 tests ... OK`.
- Swift verification -> `Swift Blink store tests passed.` and release build completed, including briefing-change persistence coverage.
- Astronomy regeneration -> 732 day records generated.
- Open-Meteo geocoding matrix -> 20/20 cities returned coordinates and IANA timezone.
- `./status_watcher.command` -> watcher running with fresh heartbeat.
- Release executable -> copied from SwiftPM release output into `Blink.app/Contents/MacOS/Blink`.
- Regression coverage -> Python and Swift tests cover disabled-past History behavior, frozen-event rejection, attachment manifest migration, multiline round-trip, draft cleanup, JPEG naming, attachment finalization, paperclip push projection, duplicate IDs, the new-event blinker default, briefing saves after today's target, legacy saved-state migration, and thin rise/set push arrows.
- Watcher reload -> LaunchAgent was restarted after the formatter change; fresh PID/heartbeat confirmed.

## Verification and resolved risks
- Manual visual walkthrough covered the installed Today/New Event surface after release deployment; the editor shows multiline fields, attachment controls, colored importance, reminders, and visible Cancel/Save actions without clipping. History action gating is covered by Swift UI-contract tests.
- Clipboard policy has one `Paste` action: file URLs are imported as files; otherwise image data becomes a JPEG; text/emoji/unsupported data has no attachment action. Drag/drop is supported only in the editor attachment panel and rejects directories.
- Active/Upcoming events can always open or create an empty event-ID attachment folder; History can only reveal an existing folder. The editor previews image thumbnails and file-type icons, and saved-file removal is transactional until Save.
- Search should include attachment filenames/extensions by scanning the local owner folder, while keeping JSON and folders canonical; do not add SQLite unless a later scale test demonstrates a need for a rebuildable index.
- Legacy shared-series attachment folders are handled only by an idempotent copy migration. Sources are preserved and deterministic collisions are renamed; no live recurring data currently requires migration.
- Git privacy is verified before commit: `event_data/`, `agenda.json`, app bundles, and build products remain ignored, while source/contracts/tests/docs are tracked.
- Editor layout regression is covered by a Swift UI-contract test and release build; the installed app was restarted after deployment.

## Resolved interaction decisions to preserve across compaction

- Should `Paste Screenshot` accept any clipboard image, not only screenshots? **Implemented:** yes; accept TIFF/PNG image data and convert it to a timestamped JPEG without relying on a source filename, unless file URLs are also present.
- If the clipboard contains an Excel/PDF file URL, should `Paste` import it? **Implemented:** yes; file URLs take precedence over image data.
- If the clipboard contains Finder folder contents or a directory, should Blink recursively copy them? **Recommended:** no; reject directories to avoid hidden/service files, large trees, and surprising copies.
- Should drag-and-drop be added to event rows? **No:** rows remain inert; drop is accepted only inside the open editor attachment panel and reuses the shared staging path.
- Should drag/drop be disabled for History? **Recommended:** yes; History is frozen and only duplication creates a writable new event.
- Should a drop show staged attachment count before Save? **Recommended:** yes, reusing the existing paperclip/count presentation; Cancel removes only the draft staging folder.

## Next actions (3-7 concrete steps)
1. Run the final Python/Swift/release/runtime/visual verification gate.
2. Verify Git privacy and inspect the final diff for stale current-contract language.
3. Commit and push the reconciled implementation and current documentation.

## Files touched (paths)
`watcher.py`, `app/attachment_store.py`, `app/weather_store.py`, `test_watcher.py`, `test_weather_store.py`, `app/agenda_store.py`, `app/notification_format.py`, `test_agenda_store.py`, `test_notification_format.py`, `test_attachment_store.py`, `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`, `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttachmentStore.swift`, `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`, `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`, `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `CODEX_NEXT_THREAD_PROMPT.md`, `docs/superpowers/plans/2026-09-09-astronomy-push-format.md`, `docs/superpowers/plans/2026-09-09-event-attachments-and-history-freeze.md`.

## Commands run (command -> outcome)
- `.venv/bin/python -m unittest -q` -> 128 tests passed.
- `.venv/bin/python -m py_compile watcher.py app/attachment_store.py app/agenda_store.py app/notification_format.py` -> passed.
- `swift run BlinkSwiftUITestRunner` -> all Swift store/UI contract tests passed, including attachment/history/UI contracts.
- `swift build -c release` -> release build passed and was installed in `Blink.app/Contents/MacOS/Blink`.
- `.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py` -> passed.
- `jq` active Astronomy contract checks -> passed; 732 records and no Eclipse/advance-offset keys.
- `.venv/bin/python astronomy/generate_astronomy.py` -> 732 days generated.

## DoD (definition of done for current subtask)
Anti-compact document and current-state contracts are saved, local event attachments/multiline text/frozen History are implemented without a second scheduler or sender, tests/build/runtime/manual UI checks are recorded, and the installed Blink app plus watcher are running from the Blink root.
