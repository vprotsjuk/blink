# Blink Astronomy

Astronomy data is separate from notification settings and from the SwiftUI presentation layer.

- `astronomy_config.json` stores location, timezone, and push enable/disable preferences.
- `astronomy_schedule.json` stores the rolling 24-month calculated astronomy facts/events and today's summary fields.
- `generate_astronomy.py` prepares the files and reports whether the precise Skyfield/JPL dependency is available.

Disabling a checkbox must not delete calculated astronomy data. Watcher decides which calculated facts become push notifications at send time.

The active location can be a globally geocoded city or custom coordinates, paired with an explicit IANA timezone. The current example is Sunnyvale, California, using `America/Los_Angeles`.

Precise generation uses Skyfield, the local JPL `de440s.bsp` ephemeris, NumPy, topocentric coordinates, and the IANA timezone attached to the canonical location tuple. City search supplies a matched coordinate/timezone pair. Custom coordinates require an explicit timezone; validation rejects a known mismatch instead of generating misleading local times. Solar and lunar event-time notifications are independent Sun/Moon selections; the daily/group briefing is a separate optional channel. Moon-related messages share one watcher formatter for trend and next-phase countdown lines. `New Moon` and `Full Moon` labels are reserved for the calendar day containing their exact phase event; other days use only `Waxing Moon` or `Waning Moon`.

The Astronomy tab reads the generated schedule, uses the same scrollable Weather-style layout, and shows a today's Sun/Moon summary below the settings. It must not introduce a second astronomy calculation path.
