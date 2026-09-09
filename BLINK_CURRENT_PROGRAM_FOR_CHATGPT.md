# Blink current-state handoff

This file is intentionally a short pointer. **Snapshot: 2026-09-09.** The authoritative full description of the current Blink implementation is [BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md](BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md). The short prompt for the next Codex task is [CODEX_NEXT_THREAD_PROMPT.md](CODEX_NEXT_THREAD_PROMPT.md).

The saved stabilization requirements are [docs/contracts/BLINK_STABILIZATION_MASTER_PROMPT_2026-09-08.txt](docs/contracts/BLINK_STABILIZATION_MASTER_PROMPT_2026-09-08.txt).

Current release checks: Python (108 passing, 1 skipped) and SwiftUI tests pass at baseline, the release app bundle was rebuilt, both LaunchAgents are installed, and the watcher heartbeat is running. Astronomy now excludes Eclipses entirely, includes today's Sun/Moon summary in the GUI, and keeps individual event-time pushes separate from the optional briefing. The anti-compact handoff records the current verification gate.
