# Blink

Blink is a local macOS reminder utility. The native SwiftUI app edits local JSON; `watcher.py` is the only ntfy sender; ntfy delivers to the iPhone.

The current implementation contract for future agents is [docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md](docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md). Read it before changing architecture, runtime boundaries, notification behavior, or shared UI rules.

## Run

```bash
cd "/Users/vitaliiprotsiuk/Desktop/Blink"
./install_launch_agent.command
./status_watcher.command
./test_push.command
```

The LaunchAgents start both the watcher and `Blink.app` at login. The watcher uses `/Users/vitaliiprotsiuk/Desktop/Blink/.venv/bin/python`. Keep the Mac awake for direct sends and weather refreshes.

## Main data

- `agenda.json`: personal events and lifecycle state.
- `location.json`: canonical city/custom coordinates and IANA timezone.
- `config.json`: private ntfy configuration.
- `watcher_state.json`: direct-send deduplication.
- `watcher_runtime.json`: heartbeat and status.
- `ntfy_schedule_state.json`: rolling 24-hour personal/astronomy queue.
- `weather/`: weather settings, cache, and delivery state.
- `astronomy/`: Skyfield/JPL schedule and notification settings.

## Event lifecycle

```text
Upcoming -> Active -> Done -> History
```

`start` must contain an explicit UTC offset. `On/Off` controls notification eligibility. `Done` completes a personal event and writes `done_at`; `Delete` removes it. Visual attention starts at `start - blinker_minutes_before` but never changes lifecycle state. Recurring events support weekly fixed schedules and days-after-Done schedules with idempotent successors.

## Weather and astronomy

Weather is fetched only when its configured local briefing time is due, then sent directly with a fresh forecast. It is not placed in the remote queue. Failed fetches remain undelivered and retry no faster than every 15 minutes.

Astronomy uses local Skyfield/JPL DE440s calculations for a rolling 24-month schedule. It includes Sun events, Moon rise/set, exact Full/New Moon timestamps, phase/trend, day/night duration, and explicit no-event states. Individual astronomy notifications are independent and fire at the astronomical event time; the optional briefing has its own time.

The Location editor supports global Open-Meteo city search and validated custom coordinates. Saving a changed location invalidates derived data; the watcher regenerates astronomy automatically before loading astronomy notifications.

## Push format

ntfy metadata is sent in headers. The phone receives plain readable text with a title and body, never a JSON envelope. Weather and astronomy messages begin with their block name, location/date, and relevant facts. The combined daily briefing keeps `WEATHER` as the ntfy title and renders the in-body `**ASTRONOMY**` section heading bold through ntfy Markdown, so all top-level message headings share one visual style.

## Public repository hygiene

The public source repository intentionally excludes local runtime data and build artifacts. Do not commit `config.json`, `agenda.json`, `location.json`, weather/astronomy state, watcher state, the local app bundle, `.venv`, backups, or the JPL ephemeris cache. Start from [`config.example.json`](config.example.json), then create the private runtime files locally before launching Blink.

## Diagnostics and tests

Open the `Health` tab for watcher heartbeat, weather, astronomy, queue, and location state. Full architecture and contracts are in [BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md](BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md). The saved stabilization prompt is [docs/contracts/BLINK_STABILIZATION_MASTER_PROMPT_2026-09-08.txt](docs/contracts/BLINK_STABILIZATION_MASTER_PROMPT_2026-09-08.txt).

Run the checks sequentially:

```bash
.venv/bin/python -m unittest -q
cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner
```

Eclipses are intentionally not supported and are not part of the active UI, configuration, schedule, or notification pipeline. Legacy eclipse keys are ignored safely during loading.
