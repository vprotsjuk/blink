import unittest
from datetime import datetime
import json
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from app import personal_briefing
import watcher


class PersonalBriefingTests(unittest.TestCase):
    TZ = "America/Los_Angeles"

    def event(self, event_id, title, start, **overrides):
        event = {
            "id": event_id,
            "title": title,
            "description": "",
            "start": start,
            "start_dt": datetime.fromisoformat(start),
            "enabled": True,
            "done": False,
            "source": "personal",
            "attention_level": "green",
        }
        event.update(overrides)
        return event

    def test_build_message_contains_every_today_event_in_local_time_order(self):
        events = [
            self.event(
                "late",
                "Dentist",
                "2026-09-14T14:00:00-07:00",
                description="Bring insurance\ncard",
                attention_level="red",
            ),
            self.event("early", "Call", "2026-09-14T09:30:00-07:00"),
            self.event("tomorrow", "Tomorrow", "2026-09-15T09:00:00-07:00"),
            self.event("disabled", "Off", "2026-09-14T10:00:00-07:00", enabled=False),
            self.event("done", "Done", "2026-09-14T11:00:00-07:00", done=True),
        ]

        body = personal_briefing.build_message(
            events, datetime(2026, 9, 14, 6, 30, tzinfo=ZoneInfo(self.TZ)), self.TZ
        )

        self.assertLess(body.index("09:30"), body.index("14:00"))
        self.assertIn("🟢 09:30 — Call", body)
        self.assertIn("🔴 14:00 — Dentist", body)
        self.assertIn("Bring insurance card", body)
        self.assertNotIn("Tomorrow", body)
        self.assertNotIn("Off", body)
        self.assertNotIn("Done", body)

    def test_due_state_dedupes_by_local_date_and_time(self):
        config = {"enabled": True, "time": "06:30"}
        now = datetime(2026, 9, 14, 6, 31, tzinfo=ZoneInfo(self.TZ))
        events = [self.event("one", "One", "2026-09-14T09:00:00-07:00")]

        first = personal_briefing.decide(config, {}, events, now, self.TZ)
        self.assertEqual(first["action"], "send_now")
        second = personal_briefing.decide(
            config, {"last_sent_key": first["key"]}, events, now, self.TZ
        )
        self.assertEqual(second["action"], "none")

    def test_empty_today_does_not_send_and_is_marked_evaluated(self):
        config = {"enabled": True, "time": "06:30"}
        now = datetime(2026, 9, 14, 7, 0, tzinfo=ZoneInfo(self.TZ))

        decision = personal_briefing.decide(config, {}, [], now, self.TZ)

        self.assertEqual(decision["action"], "none")
        self.assertEqual(decision["reason"], "empty_today")
        self.assertTrue(decision["mark_evaluated"])
        self.assertEqual(decision["key"], "2026-09-14|06:30")

    def test_process_marks_delivered_only_after_send_succeeds(self):
        config = {"enabled": True, "time": "06:30"}
        now = datetime(2026, 9, 14, 7, 0, tzinfo=ZoneInfo(self.TZ))
        events = [self.event("one", "One", "2026-09-14T09:00:00-07:00")]

        state = personal_briefing.process(
            config, {}, events, now, self.TZ, lambda item: True
        )

        self.assertEqual(state["last_sent_key"], "2026-09-14|06:30")
        self.assertEqual(state["last_status"], "sent")

        failed = personal_briefing.process(
            config, {}, events, now, self.TZ, lambda item: False
        )
        self.assertNotEqual(failed.get("last_sent_key"), "2026-09-14|06:30")
        self.assertEqual(failed["last_status"], "send_failed")

    def test_invalid_time_is_disabled_safely(self):
        decision = personal_briefing.decide(
            {"enabled": True, "time": "25:90"},
            {},
            [self.event("one", "One", "2026-09-14T09:00:00-07:00")],
            datetime(2026, 9, 14, 7, 0, tzinfo=ZoneInfo(self.TZ)),
            self.TZ,
        )
        self.assertEqual(decision, {"action": "none", "reason": "invalid_time"})

    def test_watcher_integration_persists_only_after_successful_delivery(self):
        event = self.event("one", "One", "2026-09-14T09:00:00-07:00")
        now = datetime(2026, 9, 14, 7, 0, tzinfo=ZoneInfo(self.TZ))
        location = {"timezone": self.TZ}
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "personal_briefing.json"
            config_path.write_text(json.dumps({"enabled": True, "time": "06:30"}), encoding="utf-8")
            sent = []
            state = watcher.process_personal_briefing(
                {}, {}, [event], now, location,
                briefing_config_path=config_path,
                send_func=lambda _config, item: sent.append(item["message"]) or True,
            )
        self.assertEqual(state["personal_briefing"]["last_status"], "sent")
        self.assertEqual(len(sent), 1)
