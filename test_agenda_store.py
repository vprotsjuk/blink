import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app import agenda_store


class AgendaStoreTests(unittest.TestCase):
    def test_upsert_preserves_unknown_document_and_event_fields(self):
        document = {
            "version": 1,
            "future_root_field": "keep-me",
            "events": [
                {
                    "id": "dentist",
                    "title": "Dentist",
                    "start": "2026-09-12T15:00:00-07:00",
                    "reminders_minutes_before": [30],
                    "enabled": True,
                    "future_event_field": "keep-event",
                }
            ],
        }
        updated = agenda_store.upsert_event(
            document,
            {
                "id": "dentist",
                "title": "Dentist moved",
                "start": "2026-09-12T16:00:00-07:00",
                "reminders_minutes_before": [60, 30],
                "enabled": True,
            },
        )
        self.assertEqual(updated["future_root_field"], "keep-me")
        self.assertEqual(updated["events"][0]["future_event_field"], "keep-event")
        self.assertEqual(updated["events"][0]["title"], "Dentist moved")

    def test_build_event_start_is_timezone_aware_los_angeles(self):
        event = agenda_store.build_personal_event(
            event_id="football",
            title="Football",
            local_date="2026-09-12",
            local_time="19:00",
            reminder_offsets=[1440, 300, 30],
            description="Game",
            enabled=True,
        )
        self.assertEqual(event["start"], "2026-09-12T19:00:00-07:00")

    def test_build_event_handles_dst_offset(self):
        event = agenda_store.build_personal_event(
            event_id="winter",
            title="Winter",
            local_date="2026-12-12",
            local_time="19:00",
            reminder_offsets=[0],
        )
        self.assertEqual(event["start"], "2026-12-12T19:00:00-08:00")

    def test_atomic_save_and_load_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agenda.json"
            document = {"version": 1, "events": []}
            agenda_store.save_agenda_document_atomic(path, document)
            self.assertEqual(agenda_store.load_agenda_document(path), document)

    def test_disable_and_delete_event(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "dentist",
                    "title": "Dentist",
                    "start": "2026-09-12T15:00:00-07:00",
                    "reminders_minutes_before": [30],
                    "enabled": True,
                }
            ],
        }
        disabled = agenda_store.set_event_enabled(document, "dentist", False)
        self.assertFalse(disabled["events"][0]["enabled"])
        deleted = agenda_store.delete_event(disabled, "dentist")
        self.assertEqual(deleted["events"], [])

    def test_history_upcoming_split_uses_personal_events_only(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "past",
                    "title": "Past",
                    "start": "2026-09-06T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                },
                {
                    "id": "future",
                    "title": "Future",
                    "start": "2026-09-08T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                },
            ],
        }
        history, upcoming = agenda_store.split_history_upcoming(
            document,
            now=datetime.fromisoformat("2026-09-07T12:00:00-07:00"),
        )
        self.assertEqual([event["id"] for event in history], ["past"])
        self.assertEqual([event["id"] for event in upcoming], ["future"])

    def test_new_event_defaults_to_requires_done_and_green_attention(self):
        event = agenda_store.build_personal_event(
            event_id="new",
            title="New",
            local_date="2026-09-12",
            local_time="19:00",
            reminder_offsets=[0],
        )
        self.assertTrue(event["requires_done"])
        self.assertFalse(event["done"])
        self.assertIsNone(event["done_at"])
        self.assertEqual(event["attention_level"], "green")
        self.assertEqual(
            event["attachments"],
            {"owner_id": "new", "count": 0, "has_files": False},
        )

    def test_personal_lifecycle_future_active_done_history_reload(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "future",
                    "title": "Future",
                    "start": "2026-09-08T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "green",
                },
                {
                    "id": "two-days-old",
                    "title": "Two days old",
                    "start": "2026-09-05T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "yellow",
                },
            ],
        }
        sections = agenda_store.split_personal_event_sections(
            document,
            now=datetime.fromisoformat("2026-09-07T12:00:00-07:00"),
        )
        self.assertEqual([event["id"] for event in sections["upcoming"]], ["future"])
        self.assertEqual([event["id"] for event in sections["active"]], ["two-days-old"])
        self.assertEqual(sections["history"], [])

        completed = agenda_store.complete_event(
            document,
            "two-days-old",
            now=datetime.fromisoformat("2026-09-07T14:32:18-07:00"),
        )
        sections = agenda_store.split_personal_event_sections(
            completed,
            now=datetime.fromisoformat("2026-09-07T14:33:00-07:00"),
        )
        self.assertEqual(sections["active"], [])
        self.assertEqual([event["id"] for event in sections["history"]], ["two-days-old"])
        self.assertEqual(
            sections["history"][0]["done_at"],
            "2026-09-07T14:32:18-07:00",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agenda.json"
            agenda_store.save_agenda_document_atomic(path, completed)
            reloaded = agenda_store.load_agenda_document(path)
        sections = agenda_store.split_personal_event_sections(
            reloaded,
            now=datetime.fromisoformat("2026-09-07T14:34:00-07:00"),
        )
        self.assertEqual([event["id"] for event in sections["history"]], ["two-days-old"])

    def test_attention_highest_active_priority_and_done_transitions(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "green",
                    "title": "Green",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "green",
                },
                {
                    "id": "yellow",
                    "title": "Yellow",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "yellow",
                },
                {
                    "id": "red",
                    "title": "Red",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "red",
                },
            ],
        }
        now = datetime.fromisoformat("2026-09-07T12:00:00-07:00")
        self.assertEqual(agenda_store.compute_attention_state(document, now), "red")
        document = agenda_store.complete_event(document, "red", now)
        self.assertEqual(agenda_store.compute_attention_state(document, now), "yellow")
        document = agenda_store.complete_event(document, "yellow", now)
        self.assertEqual(agenda_store.compute_attention_state(document, now), "green")
        document = agenda_store.complete_event(document, "green", now)
        self.assertEqual(agenda_store.compute_attention_state(document, now), "off")

    def test_exclusions_and_legacy_compatibility_for_active_attention_history(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "legacy-past",
                    "title": "Legacy",
                    "start": "2026-09-01T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "attention_level": "red",
                },
                {
                    "id": "disabled-red",
                    "title": "Disabled",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": False,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "red",
                },
                {
                    "id": "future-red",
                    "title": "Future red",
                    "start": "2026-09-08T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "red",
                },
                {
                    "id": "astro-sunset",
                    "title": "Sunset",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "red",
                    "source": "astronomy",
                },
            ],
        }
        now = datetime.fromisoformat("2026-09-07T12:00:00-07:00")
        sections = agenda_store.split_personal_event_sections(document, now)
        self.assertEqual(sections["active"], [])
        self.assertEqual(
            [event["id"] for event in sections["history"]],
            ["disabled-red", "legacy-past"],
        )
        self.assertEqual([event["id"] for event in sections["upcoming"]], ["future-red"])
        self.assertEqual(agenda_store.compute_attention_state(document, now), "off")

    def test_migration_removes_retired_fields_without_changing_event_meaning(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "legacy",
                    "title": "Legacy",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "red",
                    "snoozed_until": "2026-09-07T12:30:00-07:00",
                    "snoozed_for_minutes": 30,
                    "template_id": "old-template",
                    "future_field": "preserve-me",
                }
            ],
        }
        migrated = agenda_store.migrate_obsolete_fields(document)
        event = migrated["events"][0]
        self.assertNotIn("snoozed_until", event)
        self.assertNotIn("snoozed_for_minutes", event)
        self.assertNotIn("template_id", event)
        self.assertEqual(event["start"], document["events"][0]["start"])
        self.assertEqual(event["future_field"], "preserve-me")

    def test_blinker_offset_starts_active_attention_before_event(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "early",
                    "title": "Early",
                    "start": "2026-09-07T15:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "yellow",
                    "blinker_minutes_before": 300,
                }
            ],
        }
        before = agenda_store.split_personal_event_sections(
            document,
            now=datetime.fromisoformat("2026-09-07T09:59:00-07:00"),
        )
        after = agenda_store.split_personal_event_sections(
            document,
            now=datetime.fromisoformat("2026-09-07T10:00:00-07:00"),
        )
        self.assertEqual(before["active"], [])
        self.assertEqual(after["active"], [])
        self.assertEqual([event["id"] for event in after["upcoming"]], ["early"])
        self.assertEqual(agenda_store.compute_attention_state(document, datetime.fromisoformat("2026-09-07T10:00:00-07:00")), "yellow")

    def test_after_done_days_recurrence_creates_next_event_from_completion_date(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "filter",
                    "title": "Change water filter",
                    "start": "2026-09-01T08:00:00-07:00",
                    "reminders_minutes_before": [1440, 0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "yellow",
                    "recurrence": {"mode": "after_done_days", "days": 90},
                }
            ],
        }
        completed = agenda_store.complete_event(
            document,
            "filter",
            now=datetime.fromisoformat("2026-09-07T14:32:18-07:00"),
        )
        self.assertEqual(len(completed["events"]), 2)
        original, next_event = completed["events"]
        self.assertTrue(original["done"])
        self.assertFalse(next_event["done"])
        self.assertNotEqual(next_event["id"], "filter")
        self.assertEqual(next_event["title"], "Change water filter")
        self.assertEqual(next_event["start"], "2026-12-06T08:00:00-08:00")
        self.assertEqual(next_event["recurrence"], {"mode": "after_done_days", "days": 90})
        self.assertEqual(
            next_event["attachments"],
            {"owner_id": next_event["id"], "count": 0, "has_files": False},
        )

    def test_weekly_fixed_recurrence_creates_next_weekday_time(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "monday",
                    "title": "Every Monday",
                    "start": "2026-09-07T08:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "green",
                    "recurrence": {"mode": "weekly_fixed", "weekday": 1, "time": "08:00"},
                }
            ],
        }
        completed = agenda_store.complete_event(
            document,
            "monday",
            now=datetime.fromisoformat("2026-09-07T09:00:00-07:00"),
        )
        self.assertEqual(completed["events"][1]["start"], "2026-09-14T08:00:00-07:00")
        self.assertEqual(completed["events"][1]["recurrence"]["mode"], "weekly_fixed")

    def test_done_and_attention_writes_preserve_unknown_fields(self):
        document = {
            "version": 1,
            "future_root_field": "keep-root",
            "events": [
                {
                    "id": "event",
                    "title": "Event",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "attention_level": "green",
                    "future_event_field": "keep-event",
                }
            ],
        }
        updated = agenda_store.set_attention_level(document, "event", "red")
        completed = agenda_store.complete_event(
            updated,
            "event",
            now=datetime.fromisoformat("2026-09-07T14:32:18-07:00"),
        )
        event = completed["events"][0]
        self.assertEqual(completed["future_root_field"], "keep-root")
        self.assertEqual(event["future_event_field"], "keep-event")
        self.assertEqual(event["attention_level"], "red")
        self.assertTrue(event["done"])

    def test_editing_done_event_is_rejected(self):
        document = {
            "version": 1,
            "events": [
                {
                    "id": "event",
                    "title": "Done Event",
                    "start": "2026-09-07T10:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": True,
                    "done_at": "2026-09-07T14:32:18-07:00",
                }
            ],
        }
        with self.assertRaises(ValueError):
            agenda_store.upsert_event(
                document,
                {
                    "id": "event",
                    "title": "Renamed",
                    "start": "2026-09-07T11:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": False,
                    "done_at": None,
                    "attention_level": "yellow",
                },
            )

    def test_editing_done_event_to_future_is_rejected(self):
        document = {
            "version": 1,
            "events": [{
                "id": "event",
                "title": "Done Event",
                "start": "2026-09-07T10:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "requires_done": True,
                "done": True,
                "done_at": "2026-09-07T14:32:18-07:00",
            }],
        }
        with self.assertRaises(ValueError):
            agenda_store.upsert_event(
                document,
                {**document["events"][0], "start": "2026-09-10T11:00:00-07:00", "done": False, "done_at": None},
                now=datetime.fromisoformat("2026-09-08T09:00:00-07:00"),
            )

    def test_loading_stale_completed_future_event_repairs_and_moves_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agenda.json"
            path.write_text(json.dumps({
                "version": 1,
                "events": [{
                    "id": "event",
                    "title": "Recovered",
                    "start": "2026-09-10T11:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                    "requires_done": True,
                    "done": True,
                    "done_at": "2026-09-08T09:09:40-07:00",
                }],
            }), encoding="utf-8")
            document = agenda_store.repair_completed_future_events(
                json.loads(path.read_text(encoding="utf-8")),
                now=datetime.fromisoformat("2026-09-08T09:00:00-07:00"),
            )
            event = document["events"][0]
            self.assertFalse(event["done"])
            self.assertIsNone(event["done_at"])
            sections = agenda_store.split_personal_event_sections(
                document, datetime.fromisoformat("2026-09-08T09:00:00-07:00")
            )
            self.assertEqual([item["id"] for item in sections["upcoming"]], ["event"])


if __name__ == "__main__":
    unittest.main()
