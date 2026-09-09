# Blink Work Handoff

**Snapshot:** 2026-09-09  
**Full technical description:** [`BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`](../BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md)  
**Next Codex prompt:** [`CODEX_NEXT_THREAD_PROMPT.md`](../CODEX_NEXT_THREAD_PROMPT.md)

## Goal (current)
Keep Blink's independent runtime architecture stable while fixing personal-event visibility and making event attention state clear in the app and phone notifications.

The canonical current-state contract for future agents is [`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](contracts/BLINK_CURRENT_STATE_CONTRACT.md). Update it together with this handoff whenever a boundary or user-visible contract changes.

## Status (what is done / what is broken / what is verified)
Checkpoint and source prompt saved. Python verification: 115 passing, 1 skipped. Swift test runner passes from `app/BlinkSwiftUI`. Disabled past unfinished events now remain in History, new GUI events default the blinker to `At time`, personal push titles include the event attention color icon, editing a completed event into the future reopens it, and stale completed records with future starts are repaired on load. Enabled overdue unfinished events now pulse in the app until `Done`; Blink's app-owned `Today` tab alternates between normal text and the highest active priority color from every tab. It is app-owned because macOS `TabView.tabItem` ignores dynamic label color. This is UI-only and does not change lifecycle or sending. Event toggle labels are `On`/`Off`, with disabled row text dimmed but its priority dot retained. Astronomy now uses `☀️` for all Sun events and never emits `🌅`. Moon-related messages use `Waxing Moon`/`Waning Moon` on ordinary days and reserve `New Moon`/`Full Moon` for the exact event day; one large `⬆️`/`⬇️` phase arrow appears on ordinary days only, with one countdown, no textual `Moon is …` line, and no repeated Sunset or standalone Moon event name in the body. Thin `↑`/`↓` UI arrows now mean only rise/set; large arrows mean only waxing/waning. The watcher owns the shared formatter; SwiftUI mirrors the approved icon language only. Astronomy also presents a scrollable Weather-style settings surface plus today's Sun/Moon summary. Its upper settings and lower summaries share the same two columns, so Sun and Moon remain vertically aligned. Weather now uses day/night icons for compact temperature and humidity lines; the Astronomy briefing respects `Use Weather briefing time` by either appending to Weather or sending a separate ntfy briefing. The app reads live JSON from `/Users/vitaliiprotsiuk/Desktop/Blink`; an empty UI after a build is an app-process restart issue, not a data-loss state. Watcher remains the only sender.

## Key decisions (decision -> rationale)
- The `Use Weather briefing time` switch controls delivery mode -> enabled appends a plain `ASTRONOMY` section to Weather, disabled sends a separate native ntfy `ASTRONOMY` title; Markdown markers are not sent because the phone displays them literally.
- Astronomy individual notifications use event time only -> no redundant offset configuration.
- Eclipses are removed completely -> feature is not supported and must not appear as a stale blocker.
- Legacy eclipse keys are ignored on load -> existing user files remain safe.
- Disabled past events remain inspectable in History -> On/Off never behaves as Delete.
- Editing a completed event to a future date/time clears completion and returns it to `Today`/`Upcoming`; editing text or keeping a past date preserves completion.
- Existing stale records with `done=true` and a future start are repaired during app load, persisted with `done=false`, and therefore physically move out of `History` without requiring another edit.
- New event default blinker is `At time` -> the last reminder row is the default blinker start point.
- Personal push titles use `🟢/🟡/🔴` -> color is visible on iPhone while ntfy priority headers remain independent.
- Remote queue signature includes title, description, and attention level -> queued payloads are rebuilt when their visible content or color changes.
- Active-event row and `Today` tab pulsing are presentation-only -> `EventSnapshot.active` remains the single lifecycle source and `AttentionManager` remains the single global-output owner.
- `On`/`Off` replaces `Enabled`/`Disabled` -> user sees state without confusing the toggle with `Done`; Off rows dim only non-priority text.
- Shared lunar phase and countdown formatters serve grouped and individual Astronomy pushes -> one large direction arrow appears exactly once, phase-boundary events omit it, and daily/event-time messages cannot drift.

## Tried & results (bullets)
- Python verification -> `Ran 112 tests ... OK (skipped=1)`.
- Swift verification -> `Swift Blink store tests passed.` and release build completed.
- Astronomy regeneration -> 732 day records generated.
- Open-Meteo geocoding matrix -> 20/20 cities returned coordinates and IANA timezone.
- `./status_watcher.command` -> watcher running with fresh heartbeat.
- Release executable -> copied from SwiftPM release output into `Blink.app/Contents/MacOS/Blink`.
- Regression coverage -> Python and Swift tests cover disabled-past History behavior, future reactivation of completed events, stale-record repair, and the new-event blinker default; notification smoke output verified all three color icons.
- Watcher reload -> LaunchAgent was restarted after the formatter change; fresh PID/heartbeat confirmed.

## Open questions / risks
- Manual visual walkthrough remains the only non-automated verification item.

## Next actions (3-7 concrete steps)
1. Preserve the anti-compact documents as the source of truth.
2. Run the manual visual walkthrough on the installed app, including disabling a past event and creating a new event.
3. Re-run the release gate after any further code change.

## Files touched (paths)
`watcher.py`, `test_watcher.py`, `app/agenda_store.py`, `app/notification_format.py`, `test_agenda_store.py`, `test_notification_format.py`, `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`, `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`, `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`, `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `CODEX_NEXT_THREAD_PROMPT.md`, `docs/superpowers/plans/2026-09-09-astronomy-push-format.md`.

## Commands run (command -> outcome)
- `.venv/bin/python -m unittest -q` -> 112 tests passed, 1 expected skip.
- `.venv/bin/python -m py_compile watcher.py app/*.py` -> passed.
- `swift run BlinkSwiftUITestRunner` -> all Swift store/UI contract tests passed, including active-attention UI contracts.
- `swift build -c release` -> release build passed.
- `.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py` -> passed.
- `jq` active Astronomy contract checks -> passed; 732 records and no Eclipse/advance-offset keys.
- `.venv/bin/python astronomy/generate_astronomy.py` -> 732 days generated.

## DoD (definition of done for current subtask)
Anti-compact document saved, stale Eclipse/offset behavior removed from active implementation/config, tests/build/runtime/geocoding status recorded, and the only remaining item is manual visual walkthrough.
