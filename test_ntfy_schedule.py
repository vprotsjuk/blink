import unittest
from datetime import datetime

from app import ntfy_schedule


class NtfyScheduleTests(unittest.TestCase):
    def event(self, **overrides):
        base = {
            "id": "dentist",
            "title": "Dentist",
            "description": "",
            "start": "2026-09-12T19:00:00-07:00",
            "start_dt": datetime.fromisoformat("2026-09-12T19:00:00-07:00"),
            "reminders_minutes_before": [60, 30, 0],
            "priority": "default",
            "tags": ["calendar"],
            "enabled": True,
            "source": "personal",
        }
        base.update(overrides)
        return base

    def test_reminder_inside_next_24h_is_scheduled_outside_is_not(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[self.event()],
            now=datetime.fromisoformat("2026-09-11T18:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        reminder_keys = {item["reminder_key"] for item in desired.values()}
        self.assertIn("dentist|2026-09-12T19:00:00-07:00|30", reminder_keys)
        self.assertNotIn("dentist|2026-09-12T19:00:00-07:00|0", reminder_keys)

    def test_remote_queue_allows_enabled_nighttime_event(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[
                self.event(
                    start="2026-09-12T23:30:00-07:00",
                    start_dt=datetime.fromisoformat("2026-09-12T23:30:00-07:00"),
                    reminders_minutes_before=[0],
                    attention_level="green",
                )
            ],
            now=datetime.fromisoformat("2026-09-12T22:00:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )

        self.assertEqual(len(desired), 1)
        item = next(iter(desired.values()))
        self.assertEqual(item["payload"]["title"], "🟢 Dentist")

    def test_remote_personal_reminder_omits_calendar_tag(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[self.event(reminders_minutes_before=[0])],
            now=datetime.fromisoformat("2026-09-12T18:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )

        item = next(iter(desired.values()))
        self.assertNotIn("calendar", item["payload"]["tags"])

    def test_remote_queue_skips_offsets_that_cannot_still_fire(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[self.event(reminders_minutes_before=[60, 30, 10, 0])],
            now=datetime.fromisoformat("2026-09-12T18:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        reminder_keys = {item["reminder_key"] for item in desired.values()}
        self.assertNotIn("dentist|2026-09-12T19:00:00-07:00|60", reminder_keys)
        self.assertIn("dentist|2026-09-12T19:00:00-07:00|30", reminder_keys)
        self.assertIn("dentist|2026-09-12T19:00:00-07:00|10", reminder_keys)
        self.assertIn("dentist|2026-09-12T19:00:00-07:00|0", reminder_keys)

    def test_sequence_id_is_stable_across_personal_time_edit(self):
        first = ntfy_schedule.sequence_id(self.event(), 30)
        second = ntfy_schedule.sequence_id(
            self.event(start="2026-09-12T20:30:00-07:00"),
            30,
        )
        self.assertEqual(first, second)
        self.assertNotIn("topic", first)

    def test_reconcile_schedules_new_and_does_not_mark_delivered(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[self.event()],
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        calls = []
        state = ntfy_schedule.reconcile(
            desired=desired,
            state={"version": 1, "scheduled": {}},
            schedule_func=lambda item: calls.append(item["sequence_id"]) or True,
            cancel_func=lambda _item: True,
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
        )
        self.assertEqual(set(calls), set(desired))
        self.assertEqual(state["delivered"], {})
        self.assertTrue(all(item["status"] == "queued" for item in state["scheduled"].values()))

    def test_edit_time_replaces_same_sequence_without_duplicate(self):
        old_event = self.event(reminders_minutes_before=[30])
        new_event = self.event(
            start="2026-09-12T20:30:00-07:00",
            start_dt=datetime.fromisoformat("2026-09-12T20:30:00-07:00"),
            reminders_minutes_before=[30],
        )
        old_desired = ntfy_schedule.build_desired_queue(
            events=[old_event],
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        seq = ntfy_schedule.sequence_id(old_event, 30)
        state = {"version": 1, "scheduled": {seq: {**old_desired[seq], "status": "queued"}}}
        new_desired = ntfy_schedule.build_desired_queue(
            events=[new_event],
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        calls = []
        state = ntfy_schedule.reconcile(
            desired=new_desired,
            state=state,
            schedule_func=lambda item: calls.append(item["delivery_time"]) or True,
            cancel_func=lambda _item: True,
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
        )
        self.assertEqual(list(state["scheduled"]), [seq])
        self.assertIn("2026-09-12T20:00:00-07:00", calls)

    def test_delete_disable_done_cancels_future_queued(self):
        event = self.event()
        seq = ntfy_schedule.sequence_id(event, 30)
        state = {
            "version": 1,
            "scheduled": {
                seq: {
                    "sequence_id": seq,
                    "source": "personal",
                    "status": "queued",
                    "delivery_time": "2026-09-12T18:30:00-07:00",
                }
            },
        }
        cancelled = []
        state = ntfy_schedule.reconcile(
            desired={},
            state=state,
            schedule_func=lambda _item: True,
            cancel_func=lambda item: cancelled.append(item["sequence_id"]) or True,
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
        )
        self.assertEqual(cancelled, [seq])
        self.assertEqual(state["scheduled"], {})

    def test_failed_schedule_not_marked_queued_and_direct_fallback_allowed(self):
        desired = ntfy_schedule.build_desired_queue(
            events=[self.event()],
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
            window_hours=24,
            config={"default_priority": "high", "default_tags": ["calendar"]},
        )
        state = ntfy_schedule.reconcile(
            desired=desired,
            state={"version": 1, "scheduled": {}},
            schedule_func=lambda _item: False,
            cancel_func=lambda _item: True,
            now=datetime.fromisoformat("2026-09-12T17:30:00-07:00"),
        )
        self.assertTrue(all(item["status"] == "pending_sync" for item in state["scheduled"].values()))
        reminder_key = "dentist|2026-09-12T19:00:00-07:00|0"
        self.assertFalse(ntfy_schedule.is_reminder_owned_by_remote(state, reminder_key))

    def test_matured_queued_remote_reminder_is_assumed_delivered_to_prevent_direct_duplicate(self):
        event = self.event(reminders_minutes_before=[0])
        seq = ntfy_schedule.sequence_id(event, 0)
        reminder_key = "dentist|2026-09-12T19:00:00-07:00|0"
        state = {
            "version": 1,
            "scheduled": {
                seq: {
                    "sequence_id": seq,
                    "source": "personal",
                    "status": "queued",
                    "reminder_key": reminder_key,
                    "delivery_time": "2026-09-12T19:00:00-07:00",
                }
            },
            "delivered": {},
        }

        state = ntfy_schedule.reconcile(
            desired={},
            state=state,
            schedule_func=lambda _item: True,
            cancel_func=lambda _item: True,
            now=datetime.fromisoformat("2026-09-12T19:00:02-07:00"),
        )

        self.assertEqual(state["scheduled"], {})
        self.assertIn(seq, state["delivered"])
        self.assertEqual(state["delivered"][seq]["status"], "assumed_sent")
        self.assertTrue(ntfy_schedule.is_reminder_owned_by_remote(state, reminder_key))


if __name__ == "__main__":
    unittest.main()
