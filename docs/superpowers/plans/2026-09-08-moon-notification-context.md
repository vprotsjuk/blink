# Moon Notification Context - Completed

## User-visible rule

Every Moon-related Astronomy notification ends with these two lines:

1. `Moon is waxing.` or `Moon is waning.`
2. `<N> days until Full Moon.` or `<N> days until New Moon.`

This applies to the daily/group Astronomy briefing and individual Moonrise,
Moonset, Full Moon, New Moon, and sunset-with-moon-status notifications.

## Architecture decision

`astronomy/generate_astronomy.py` remains the sole astronomy calculator. It
persists Skyfield schedule facts, including exact Full/New Moon instants and
the next phase instants. `watcher.py` only formats those stored facts through
`moon_notification_tail()`. Do not add a second approximate lunar calculator
to the delivery layer.

## Edge rule

On a Full/New Moon date, the exact phase timestamp decides whether an event
immediately after that instant is waning or waxing and which next phase is
counted down to. Countdown is calendar-day based in the configured location.

## Verification

- `python3 -m unittest -q`: 105 tests passed, 1 expected skip.
- `swift run BlinkSwiftUITestRunner`: passed.
- Real generated record on 2026-09-08: individual Moonset and group briefing
  both ended with `Moon is waning.` and `2 days until New Moon.`
- Watcher LaunchAgent restarted; fresh heartbeat confirmed.
