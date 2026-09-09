import unittest
from datetime import datetime

from app.event_timing import effective_event_start


class EventTimingTests(unittest.TestCase):
    def test_obsolete_deferral_fields_do_not_change_event_start(self):
        event = {
            "start": "2026-09-07T15:00:00-07:00",
            "snoozed_until": "2026-09-08T15:00:00-07:00",
        }

        self.assertEqual(
            effective_event_start(event),
            datetime.fromisoformat("2026-09-07T15:00:00-07:00"),
        )

    def test_missing_start_returns_none(self):
        event = {
            "snoozed_until": "2026-09-07T14:00:00-07:00",
        }
        self.assertIsNone(effective_event_start(event))


if __name__ == "__main__":
    unittest.main()
