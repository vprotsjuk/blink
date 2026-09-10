import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import watcher
from app import notification_format, weather_store


class WatcherCoreTests(unittest.TestCase):
    def test_remote_reconcile_signature_changes_when_attachment_presence_changes(self):
        event = {
            "id": "attachment-signature",
            "start": "2026-09-12T11:00:00-07:00",
            "enabled": True,
            "done": False,
            "title": "Attachment",
            "description": "",
            "attention_level": "green",
            "reminders_minutes_before": [0],
            "attachments": {"owner_id": "attachment-signature", "count": 1, "has_files": False},
        }
        now = datetime.fromisoformat("2026-09-10T10:00:00-07:00")
        with patch.object(watcher, "_last_remote_reconcile_at", None), patch.object(
            watcher, "_last_remote_reconcile_signature", None
        ):
            self.assertTrue(watcher.remote_reconcile_due([event], now))
            self.assertFalse(watcher.remote_reconcile_due([event], now))
            event["attachments"]["count"] = 2
            self.assertFalse(watcher.remote_reconcile_due([event], now))
            event["attachments"]["has_files"] = True
            self.assertTrue(watcher.remote_reconcile_due([event], now))

    def test_legacy_briefing_config_change_uses_contract_file_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            weather_path = root / "weather_state.json"
            weather_path.write_text(
                '{"version":1,"last_weather_briefing_status":"config_changed"}',
                encoding="utf-8",
            )
            astronomy_path = root / "astronomy_config.json"
            astronomy_path.write_text(
                '{"version":2,"timezone":"America/Los_Angeles","briefing":{"enabled":true,"time":"06:00"}}',
                encoding="utf-8",
            )
            changed_at = datetime.fromisoformat("2026-09-09T16:00:00-07:00")
            timestamp = changed_at.timestamp()
            os.utime(weather_path, (timestamp, timestamp))
            os.utime(astronomy_path, (timestamp, timestamp))

            weather_state = watcher.load_weather_state(weather_path)
            astronomy_settings = watcher.load_astronomy_settings(astronomy_path)

            self.assertEqual(
                weather_state.get("briefing_config_changed_at"),
                "2026-09-09T23:00:00+00:00",
            )
            self.assertEqual(
                astronomy_settings["briefing"].get("config_changed_at"),
                "2026-09-09T23:00:00+00:00",
            )

    def test_valid_config_loads(self):
        config = watcher.validate_config(
            {
                "ntfy_server": "https://ntfy.sh",
                "ntfy_topic": "blink-private-topic-for-tests",
                "poll_interval_seconds": 10,
                "late_delivery_grace_minutes": 180,
                "default_priority": "high",
                "default_tags": ["calendar"],
            }
        )
        self.assertEqual(config["ntfy_topic"], "blink-private-topic-for-tests")
        self.assertEqual(config["late_delivery_grace_minutes"], 180)

    def test_send_ntfy_notification_supports_cyrillic_title(self):
        event = {
            "id": "ru",
            "title": "Тест просто напоминалка",
            "description": "Проверка напоминалки",
            "start": "2026-08-02T11:00:00-07:00",
            "priority": "high",
            "tags": ["calendar"],
        }
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return 200

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("watcher.urllib.request.urlopen", fake_urlopen):
            sent = watcher.send_ntfy_notification(self._notification_config(), event, 5)

        self.assertTrue(sent)
        self.assertEqual(
            captured["request"].full_url,
            "https://ntfy.sh/blink-private-topic-for-tests",
        )
        self.assertEqual(
            captured["request"].data.decode("utf-8"),
            "August 2, 2026 at 11:00\nПроверка напоминалки\n5 min before start",
        )
        self.assertTrue(captured["request"].headers["Title"].startswith("=?utf-8?"))
        self.assertEqual(captured["request"].headers["Content-type"], "text/plain; charset=utf-8")

    def test_ntfy_headers_are_ascii_safe_for_weather_icon_title(self):
        request = watcher.build_ntfy_request(
            config={"ntfy_server": "https://ntfy.sh", "ntfy_topic": "topic"},
            title="🌤️ WEATHER",
            message="Sunnyvale\nTemperature",
            priority="high",
            tags=["weather"],
        )
        self.assertTrue(all(ord(char) < 128 for _, value in request.header_items() for char in value))

    def test_personal_reminder_does_not_send_calendar_tag_to_ntfy(self):
        event = {
            "id": "no-calendar-icon",
            "title": "Visit",
            "description": "Bring tape measure",
            "start": "2026-08-02T11:00:00-07:00",
            "priority": "high",
            "tags": ["calendar"],
        }
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return 200

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse()

        with patch("watcher.urllib.request.urlopen", fake_urlopen):
            self.assertTrue(watcher.send_ntfy_notification(self._notification_config(), event, 0))

        self.assertNotIn("calendar", captured["request"].headers.get("Tags", "").lower())

    def test_placeholder_topic_is_rejected(self):
        with self.assertRaises(watcher.SetupError):
            watcher.validate_config(
                {
                    "ntfy_server": "https://ntfy.sh",
                    "ntfy_topic": "REPLACE_WITH_THE_FULL_PRIVATE_TOPIC",
                    "poll_interval_seconds": 10,
                    "late_delivery_grace_minutes": 180,
                    "default_priority": "high",
                    "default_tags": ["calendar"],
                }
            )

    def test_malformed_config_json_returns_none(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"ntfy_topic": ', encoding="utf-8")
            self.assertIsNone(watcher.load_config(path))

    def test_timezone_naive_event_is_invalid(self):
        event = {
            "id": "event-1",
            "title": "Naive time",
            "start": "2026-08-02T11:00:00",
            "reminders_minutes_before": [0],
            "enabled": True,
        }
        self.assertIsNone(watcher.validate_event(event, set(), 0))

    def test_validated_event_preserves_safe_attachment_manifest(self):
        event = watcher.validate_event(
            {
                "id": "event-1",
                "title": "With files",
                "start": "2026-08-02T11:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "attachments": {"owner_id": "event-1", "count": 2, "has_files": True},
            },
            set(),
            0,
        )
        self.assertEqual(
            event["attachments"],
            {"owner_id": "event-1", "count": 2, "has_files": True},
        )

    def test_malformed_agenda_json_returns_none(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            path = Path(tmp) / "agenda.json"
            path.write_text('{"events": [', encoding="utf-8")
            self.assertIsNone(watcher.load_agenda(path))

    def test_malformed_event_does_not_block_valid_event(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            path = Path(tmp) / "agenda.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "events": [
                            {"id": "bad"},
                            {
                                "id": "good",
                                "title": "Good",
                                "start": "2026-08-02T11:00:00-07:00",
                                "reminders_minutes_before": [0],
                                "enabled": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            events = watcher.load_agenda(path)
            self.assertEqual([event["id"] for event in events], ["good"])

    def test_valid_event_sorts_and_deduplicates_reminders(self):
        event = {
            "id": "event-1",
            "title": "Test",
            "description": "",
            "start": "2026-08-02T11:00:00-07:00",
            "reminders_minutes_before": [0, 5, 5, 15],
            "enabled": True,
        }
        validated = watcher.validate_event(event, set(), 0)
        self.assertIsNotNone(validated)
        self.assertEqual(validated["reminders_minutes_before"], [15, 5, 0])
        self.assertIsNotNone(validated["start_dt"].tzinfo)

    def test_reminder_key_is_deterministic(self):
        key = watcher.build_reminder_key(
            "test-reminder-001", "2026-08-02T11:00:00-07:00", 5
        )
        self.assertEqual(key, "test-reminder-001|2026-08-02T11:00:00-07:00|5")

    def test_due_reminder_inside_grace_is_sent_once(self):
        event = watcher.validate_event(
            {
                "id": "event-1",
                "title": "Test",
                "description": "Body",
                "start": "2026-08-02T11:00:00-07:00",
                "reminders_minutes_before": [5],
                "enabled": True,
            },
            set(),
            0,
        )
        now = datetime.fromisoformat("2026-08-02T10:56:00-07:00")
        state = {"version": 1, "delivered": {}}
        sent = []

        def fake_send(config, current_event, offset):
            sent.append((current_event["id"], offset))
            return True

        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 5},
            events=[event],
            state=state,
            now=now,
            send_func=fake_send,
            state_path=None,
        )
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 5},
            events=[event],
            state=state,
            now=now,
            send_func=fake_send,
            state_path=None,
        )
        self.assertEqual(sent, [("event-1", 5)])

    def test_expired_reminder_is_not_sent(self):
        event = watcher.validate_event(
            {
                "id": "event-1",
                "title": "Test",
                "start": "2026-08-02T11:00:00-07:00",
                "reminders_minutes_before": [15],
                "enabled": True,
            },
            set(),
            0,
        )
        now = datetime.fromisoformat("2026-08-02T11:00:00-07:00")
        state = {"version": 1, "delivered": {}}
        sent = []

        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 5},
            events=[event],
            state=state,
            now=now,
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [])

    def test_unavailable_future_offset_is_not_sent_early(self):
        event = watcher.validate_event(
            {
                "id": "event-1",
                "title": "Test",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [60, 30, 10, 0],
                "enabled": True,
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T18:30:00-07:00"),
            send_func=lambda _config, current_event, offset: sent.append(offset) or True,
            state_path=None,
        )
        self.assertEqual(sent, [30])

    def test_two_personal_events_same_timestamp_both_send(self):
        events = [
            watcher.validate_event(
                {
                    "id": "football",
                    "title": "Football",
                    "start": "2026-09-12T19:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                },
                set(),
                0,
            ),
            watcher.validate_event(
                {
                    "id": "call-robert",
                    "title": "Call Robert",
                    "start": "2026-09-12T19:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                },
                set(),
                1,
            ),
        ]
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=events,
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:00:00-07:00"),
            send_func=lambda _config, event, offset: sent.append((event["id"], offset)) or True,
            state_path=None,
        )
        self.assertEqual(sent, [("football", 0), ("call-robert", 0)])

    def test_multiple_reminders_one_event_send_independently(self):
        event = watcher.validate_event(
            {
                "id": "event-1",
                "title": "Test",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [60, 30],
                "enabled": True,
            },
            set(),
            0,
        )
        sent = []
        state = {"version": 1, "delivered": {}}
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state=state,
            now=datetime.fromisoformat("2026-09-12T18:00:00-07:00"),
            send_func=lambda _config, current_event, offset: sent.append(offset) or True,
            state_path=None,
        )
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state=state,
            now=datetime.fromisoformat("2026-09-12T18:30:00-07:00"),
            send_func=lambda _config, current_event, offset: sent.append(offset) or True,
            state_path=None,
        )
        self.assertEqual(sent, [60, 30])

    def test_edit_start_creates_new_reminder_identity(self):
        old_key = watcher.build_reminder_key("dentist", "2026-09-12T15:00:00-07:00", 30)
        new_key = watcher.build_reminder_key("dentist", "2026-09-12T16:00:00-07:00", 30)
        self.assertNotEqual(old_key, new_key)

    def test_late_delivery_grace_defaults_to_180_minutes(self):
        config = watcher.validate_config(
            {
                "ntfy_server": "https://ntfy.sh",
                "ntfy_topic": "blink-private-topic-for-tests",
                "poll_interval_seconds": 10,
                "default_priority": "high",
                "default_tags": ["calendar"],
            }
        )
        self.assertEqual(config["late_delivery_grace_minutes"], 180)

    def test_late_reminders_inside_180_minutes_send_until_boundary(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
            },
            set(),
            0,
        )
        for now_text in [
            "2026-09-12T19:20:00-07:00",
            "2026-09-12T21:00:00-07:00",
            "2026-09-12T21:59:00-07:00",
        ]:
            sent = []
            watcher.process_due_reminders(
                config={"late_delivery_grace_minutes": 180},
                events=[event],
                state={"version": 1, "delivered": {}},
                now=datetime.fromisoformat(now_text),
                send_func=lambda *_args: sent.append(True) or True,
                state_path=None,
            )
            self.assertEqual(sent, [True], now_text)

    def test_late_reminder_after_180_minutes_does_not_send(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T22:01:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [])

    def test_done_personal_event_skips_reminders(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "requires_done": True,
                "done": True,
                "done_at": "2026-09-12T18:55:00-07:00",
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:00:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [])

    def test_obsolete_deferral_fields_do_not_delay_reminders(self):
        event = watcher.validate_event(
            {
                "id": "snoozed",
                "title": "Snoozed",
                "start": "2026-09-07T10:00:00-07:00",
                "reminders_minutes_before": [30, 10, 0],
                "enabled": True,
                "requires_done": True,
                "done": False,
                "snoozed_until": "2026-09-08T15:00:00-07:00",
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-07T10:00:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [True])
        self.assertEqual(event["start"], "2026-09-07T10:00:00-07:00")

    def test_enabled_nighttime_events_are_allowed_without_quiet_hours(self):
        normal = watcher.validate_event(
            {
                "id": "normal-night",
                "title": "Normal night",
                "start": "2026-09-07T23:10:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "attention_level": "green",
            },
            set(),
            0,
        )
        sent = []
        state = {"version": 1, "delivered": {}}

        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[normal],
            state=state,
            now=datetime.fromisoformat("2026-09-07T23:10:05-07:00"),
            send_func=lambda _config, event, offset: sent.append((event["id"], offset)) or True,
            state_path=None,
        )

        self.assertEqual(sent, [("normal-night", 0)])

    def test_done_personal_event_skips_late_reminder_inside_grace(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "requires_done": True,
                "done": True,
                "done_at": "2026-09-12T19:10:00-07:00",
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:40:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [])

    def test_unfinished_personal_event_late_reminder_inside_grace_still_sends(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
                "requires_done": True,
                "done": False,
            },
            set(),
            0,
        )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:40:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
        )
        self.assertEqual(sent, [True])

    def test_remote_queued_reminder_prevents_awake_direct_duplicate(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
            },
            set(),
            0,
        )
        reminder_key = watcher.build_reminder_key("call", "2026-09-12T19:00:00-07:00", 0)
        remote_state = {
            "version": 1,
            "scheduled": {
                "blink-personal-call-0": {
                    "status": "queued",
                    "reminder_key": reminder_key,
                    "delivery_time": "2026-09-12T19:00:00-07:00",
                }
            },
        }
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:00:00-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
            remote_schedule_state=remote_state,
        )
        self.assertEqual(sent, [])

    def test_remote_assumed_delivered_reminder_prevents_late_direct_duplicate(self):
        event = watcher.validate_event(
            {
                "id": "call",
                "title": "Call",
                "start": "2026-09-12T19:00:00-07:00",
                "reminders_minutes_before": [0],
                "enabled": True,
            },
            set(),
            0,
        )
        reminder_key = watcher.build_reminder_key("call", "2026-09-12T19:00:00-07:00", 0)
        remote_state = {
            "version": 1,
            "scheduled": {},
            "delivered": {
                "blink-personal-call-0": {
                    "status": "assumed_delivered",
                    "reminder_key": reminder_key,
                    "delivery_time": "2026-09-12T19:00:00-07:00",
                }
            },
        }
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=[event],
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:00:02-07:00"),
            send_func=lambda *_args: sent.append(True) or True,
            state_path=None,
            remote_schedule_state=remote_state,
        )
        self.assertEqual(sent, [])

    def test_astronomy_source_with_personal_same_timestamp_both_send(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            tmp_path = Path(tmp)
            agenda_path = tmp_path / "agenda.json"
            astro_path = tmp_path / "astronomy_schedule.json"
            astro_config_path = tmp_path / "astronomy_config.json"
            agenda_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "events": [
                            {
                                "id": "football",
                                "title": "Football",
                                "start": "2026-09-12T19:28:00-07:00",
                                "reminders_minutes_before": [0],
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            astro_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "daily_records": [
                            {
                                "date": "2026-09-12",
                                "timezone": "America/Los_Angeles",
                                "sunset": {
                                    "time": "2026-09-12T19:28:00-07:00",
                                    "civil_twilight_end": "2026-09-12T19:55:00-07:00",
                                    "day_length_minutes": 763,
                                },
                                "moon_status_at_sunset": {
                                    "summary": "waxing, illuminated 63%",
                                    "above_horizon": True,
                                    "moonset": "2026-09-13T01:48:00-07:00",
                                    "next_full_moon": "2026-09-16T20:00:00-07:00",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            astro_config_path.write_text(
                json.dumps(
                    {
                        "notifications": {
                            "sun": {"enabled": True, "events": {"sunset": True}},
                            "moon": {"enabled": True, "events": {"moon_status_at_sunset": True}},
                        }
                    }
                ),
                encoding="utf-8",
            )
            events = watcher.load_notification_events(
                config={"late_delivery_grace_minutes": 180},
                agenda_path=agenda_path,
                astronomy_path=astro_path,
                astronomy_config_path=astro_config_path,
            )
        sent = []
        watcher.process_due_reminders(
            config={"late_delivery_grace_minutes": 180},
            events=events,
            state={"version": 1, "delivered": {}},
            now=datetime.fromisoformat("2026-09-12T19:28:00-07:00"),
            send_func=lambda _config, event, offset: sent.append(event["id"]) or True,
            state_path=None,
        )
        self.assertEqual(sent, ["football", "astro-evening-2026-09-12"])

    def test_moon_notifications_use_one_title_arrow_and_a_countdown(self):
        record = {
            "date": "2026-09-12",
            "timezone": "America/Los_Angeles",
            "moon_phase": 120.0,
            "moon_status_at_sunset": {
                "summary": "75% illuminated",
                "phase_degrees": 120.0,
                "phase_name": "Waxing Gibbous",
                "phase_trend": "waxing",
            },
            "moonrise": "2026-09-12T16:00:00-07:00",
            "next_full_moon": "2026-09-15T18:00:00-07:00",
            "next_new_moon": "2026-09-29T16:00:00-07:00",
        }
        settings = {
            "notifications": {
                "moon": {"enabled": True, "events": {"moonrise": True}},
            },
            "briefing": {"enabled": True, "include_day_night": False},
        }

        events = watcher.normalize_astronomy_record(record, settings, set())
        moonrise = next(event for event in events if event["id"] == "astro-moonrise-2026-09-12")
        briefing = watcher.build_astronomy_briefing_message(
            {"daily_records": [record]}, "2026-09-12", settings
        )

        self.assertEqual(moonrise["notification_icon"], "🌒 ⬆️")
        self.assertEqual(moonrise["description"], "3 days until Full Moon.")
        self.assertIn("🌒 ⬆️ Waxing Moon — 75% illuminated", briefing)
        self.assertTrue(briefing.endswith("3 days until Full Moon."))
        self.assertNotIn("Moon is waxing.", briefing)

    def test_full_moon_notification_switches_to_waning_after_event(self):
        record = {
            "date": "2026-09-12",
            "moon_phase": 180.0,
            "full_moon": {"time": "2026-09-12T10:00:00-07:00"},
            "next_new_moon": "2026-09-26T18:00:00-07:00",
        }

        description = watcher.build_moon_event_description(
            record, "Full Moon.", "2026-09-12T10:00:00-07:00"
        )

        self.assertEqual(description, "14 days until New Moon.")

    def test_astronomy_v2_config_supports_sunrise_and_multiple_offsets(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            tmp_path = Path(tmp)
            astro_path = tmp_path / "astronomy_schedule.json"
            astro_config_path = tmp_path / "astronomy_config.json"
            astro_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "daily_records": [
                            {
                                "date": "2026-09-12",
                                "timezone": "America/Los_Angeles",
                                "sunrise": {"time": "2026-09-12T06:42:00-07:00"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            astro_config_path.write_text(
                json.dumps(
                    {
                        "notifications": {
                            "sun": {
                                "enabled": True,
                                "events": {
                                    "sunrise": {
                                        "enabled": True,
                                        "offsets_minutes_before": [30, 0],
                                    }
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            events = watcher.load_astronomy_events(astro_path, astro_config_path)
        self.assertEqual([event["id"] for event in events], ["astro-sunrise-2026-09-12"])
        self.assertEqual(events[0]["reminders_minutes_before"], [0])

    def test_disabled_astronomy_setting_does_not_send_but_data_remains_loadable(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            tmp_path = Path(tmp)
            astro_path = tmp_path / "astronomy_schedule.json"
            astro_config_path = tmp_path / "astronomy_config.json"
            astro_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "daily_records": [
                            {
                                "date": "2026-09-12",
                                "timezone": "America/Los_Angeles",
                                "sunset": {"time": "2026-09-12T19:28:00-07:00"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            astro_config_path.write_text(
                json.dumps(
                    {"notifications": {"sun": {"enabled": False, "events": {"sunset": True}}}}
                ),
                encoding="utf-8",
            )
            events = watcher.load_astronomy_events(astro_path, astro_config_path)
        self.assertEqual(events, [])

    def test_malformed_astronomy_file_does_not_block_personal_events(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            tmp_path = Path(tmp)
            agenda_path = tmp_path / "agenda.json"
            astro_path = tmp_path / "astronomy_schedule.json"
            agenda_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "events": [
                            {
                                "id": "good",
                                "title": "Good",
                                "start": "2026-09-12T19:00:00-07:00",
                                "reminders_minutes_before": [0],
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            astro_path.write_text('{"daily_records": [', encoding="utf-8")
            events = watcher.load_notification_events(
                config={"late_delivery_grace_minutes": 180},
                agenda_path=agenda_path,
                astronomy_path=astro_path,
                astronomy_config_path=tmp_path / "missing_config.json",
            )
        self.assertEqual([event["id"] for event in events], ["good"])

    def test_weather_due_now_sends_and_marks_delivered(self):
        forecast = self._weather_forecast()
        immediate = []
        scheduled = []

        result = watcher.process_weather_briefing(
            config=self._notification_config(),
            weather_config=weather_store.default_config(),
            weather_state=weather_store.default_state(),
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T07:00:00-07:00"),
            send_now_func=lambda _config, item: immediate.append(item) or True,
            schedule_func=lambda _config, item: scheduled.append(item) or True,
        )

        self.assertEqual(result["last_weather_briefing_date"], "2026-09-07")
        self.assertEqual(result["last_weather_briefing_status"], "direct_sent")
        self.assertEqual(len(immediate), 1)
        self.assertEqual(scheduled, [])
        self.assertEqual(immediate[0]["sequence_id"], "blink-weather-morning-2026-09-07")
        self.assertIn("Sunnyvale", immediate[0]["payload"]["body"])

    def test_weather_after_long_sleep_fetches_now_without_late_cutoff(self):
        sent = []
        fetches = []

        def fetch(_location):
            fetches.append(True)
            return {
                "daily": {
                    "time": ["2026-09-07"],
                    "temperature_2m_max": [68],
                    "temperature_2m_min": [48],
                    "precipitation_probability_max": [0],
                    "rain_sum": [0],
                    "snowfall_sum": [0],
                    "wind_speed_10m_max": [5],
                    "wind_gusts_10m_max": [8],
                },
                "hourly": {
                    "time": ["2026-09-07T10:00"],
                    "relative_humidity_2m": [52],
                    "precipitation_probability": [0],
                    "rain": [0],
                    "snowfall": [0],
                },
            }

        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            weather_dir = Path(tmp) / "weather"
            weather_dir.mkdir()
            result = watcher.update_weather_briefing(
                config=self._notification_config(),
                location=self._location(),
                weather_config=weather_store.default_config(),
                now=datetime.fromisoformat("2026-09-07T10:00:00-07:00"),
                weather_state_path=weather_dir / "weather_state.json",
                weather_cache_path=weather_dir / "weather_cache.json",
                fetch_func=fetch,
                send_now_func=lambda _config, item: sent.append(item) or True,
            )

        self.assertEqual(len(fetches), 1)
        self.assertEqual(len(sent), 1)
        self.assertEqual(result["last_weather_briefing_status"], "direct_sent")
        self.assertRegex(sent[0]["payload"]["body"], r"Updated \d{2}:\d{2}")

    def test_weather_before_briefing_time_does_not_fetch_or_schedule(self):
        sent = []

        result = watcher.process_weather_briefing(
            config=self._notification_config(),
            weather_config=weather_store.default_config(),
            weather_state=weather_store.default_state(),
            forecast=self._weather_forecast(),
            now=datetime.fromisoformat("2026-09-07T05:55:00-07:00"),
            send_now_func=lambda *_args: self.fail("Weather should not send immediately before briefing time"),
            schedule_func=lambda _config, item: sent.append(item) or True,
        )

        self.assertIsNone(result["last_weather_briefing_date"])
        self.assertIsNone(result.get("last_weather_briefing_status"))
        self.assertEqual(sent, [])

    def test_weather_briefing_uses_clean_ntfy_title_and_body(self):
        item = watcher.build_weather_briefing_item(
            self._weather_forecast(),
            "2026-09-07T06:30:00-07:00",
            self._notification_config(),
        )
        self.assertEqual(item["payload"]["title"], "WEATHER")
        self.assertIn("Sunnyvale", item["payload"]["body"])
        self.assertIn("🌤️", item["payload"]["body"])
        self.assertNotIn('"message"', item["payload"]["body"])

    def test_weather_briefing_leaves_astronomy_separate_when_configured(self):
        sent = []
        schedule = {
            "daily_records": [
                {
                    "date": "2026-09-07",
                    "sunrise": {"time": "2026-09-07T06:42:00-07:00"},
                    "sunset": {"time": "2026-09-07T19:25:00-07:00"},
                    "day_length_minutes": 763,
                }
            ]
        }
        settings = {
            "timezone": "America/Los_Angeles",
            "briefing": {
                "enabled": True,
                "time": "11:52",
                "include_day_night": True,
                "include_weather": False,
            },
        }
        watcher.update_weather_briefing(
            config=self._notification_config(),
            location=self._location(),
            weather_config=weather_store.default_config(),
            now=datetime.fromisoformat("2026-09-07T07:00:00-07:00"),
            weather_state_path=Path(tempfile.mkdtemp()) / "weather_state.json",
            weather_cache_path=Path(tempfile.mkdtemp()) / "weather_cache.json",
            fetch_func=lambda _location: {
                "daily": {
                    "time": ["2026-09-07"],
                    "temperature_2m_max": [68],
                    "temperature_2m_min": [48],
                    "precipitation_probability_max": [0],
                    "rain_sum": [0],
                    "snowfall_sum": [0],
                    "wind_speed_10m_max": [5],
                    "wind_gusts_10m_max": [8],
                },
                "hourly": {
                    "time": ["2026-09-07T13:00"],
                    "relative_humidity_2m": [50],
                    "precipitation_probability": [0],
                    "rain": [0],
                    "snowfall": [0],
                },
            },
            send_now_func=lambda _config, item: sent.append(item) or True,
            astronomy_schedule=schedule,
            astronomy_settings=settings,
        )
        self.assertEqual(len(sent), 1)
        self.assertNotIn("ASTRONOMY", sent[0]["payload"]["body"])

    def test_astronomy_briefing_contains_day_and_night_duration(self):
        message = watcher.build_astronomy_briefing_message(
            {
                "daily_records": [
                    {
                        "date": "2026-09-07",
                        "sunrise": {"time": "2026-09-07T06:42:00-07:00"},
                        "sunset": {"time": "2026-09-07T19:25:00-07:00"},
                        "day_length_minutes": 763,
                    }
                ]
            },
            "2026-09-07",
            {"briefing": {"enabled": True, "include_day_night": True}},
        )
        self.assertTrue(message.startswith("ASTRONOMY\n"))
        self.assertIn("☀️ ↑ Sunrise:", message)
        self.assertIn("06:42", message)
        self.assertIn("☀️ ↓ Sunset: 19:25", message)
        self.assertIn("Day length: 12 h 43 min", message)
        self.assertIn("Night length: 11 h 17 min", message)

    def test_astronomy_briefing_marks_rise_and_set_with_thin_arrows(self):
        message = watcher.build_astronomy_briefing_message(
            {
                "daily_records": [
                    {
                        "date": "2026-09-07",
                        "sunrise": {"time": "2026-09-07T06:42:00-07:00"},
                        "sunset": {"time": "2026-09-07T19:25:00-07:00"},
                        "moonrise": "2026-09-07T16:00:00-07:00",
                        "moonset": "2026-09-07T02:00:00-07:00",
                        "moon_status_at_sunset": {
                            "summary": "75% illuminated",
                            "phase_trend": "waxing",
                        },
                    }
                ]
            },
            "2026-09-07",
            {"briefing": {"enabled": True, "include_day_night": False}},
        )
        self.assertIn("☀️ ↑ Sunrise: 06:42", message)
        self.assertIn("☀️ ↓ Sunset: 19:25", message)
        self.assertIn("🌙 ↑ Moonrise: 16:00", message)
        self.assertIn("🌙 ↓ Moonset: 02:00", message)

    def test_individual_astronomy_rise_and_set_titles_use_thin_arrows(self):
        events = [
            {"source": "astronomy", "title": "Sunrise", "tags": ["astronomy", "sunrise"], "start": "2026-09-07T06:42:00-07:00"},
            {"source": "astronomy", "title": "Sunset", "tags": ["astronomy", "sunset"], "start": "2026-09-07T19:25:00-07:00"},
            {"source": "astronomy", "title": "Moonrise", "tags": ["astronomy", "moonrise"], "start": "2026-09-07T16:00:00-07:00"},
            {"source": "astronomy", "title": "Moonset", "tags": ["astronomy", "moonset"], "start": "2026-09-07T02:00:00-07:00"},
        ]
        titles = [notification_format.build_event_notification(event, 0)[0] for event in events]
        self.assertEqual(titles, ["☀️ ↑ Sunrise", "☀️ ↓ Sunset", "🌙 ↑ Moonrise", "🌙 ↓ Moonset"])

    def test_weather_notification_does_not_send_literal_markdown_markers(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getcode(self):
                return 200

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse()

        item = watcher.build_weather_briefing_item(
            self._weather_forecast(),
            "2026-09-07T06:30:00-07:00",
            self._notification_config(),
            body="🌤️ Sunnyvale\n\nASTRONOMY\n2026-09-07",
        )
        with patch("watcher.urllib.request.urlopen", fake_urlopen):
            self.assertTrue(watcher.send_weather_ntfy_notification(self._notification_config(), item))

        self.assertNotIn("Markdown", captured["request"].headers)
        self.assertNotIn("**", captured["request"].data.decode("utf-8"))
        self.assertNotIn("Delay", captured["request"].headers)

    def test_separate_astronomy_briefing_sends_after_its_time_once(self):
        schedule = {
            "daily_records": [
                {
                    "date": "2026-09-09",
                    "timezone": "America/Los_Angeles",
                    "sunrise": {"time": "2026-09-09T06:45:00-07:00"},
                    "sunset": {"time": "2026-09-09T19:24:00-07:00"},
                    "day_length_minutes": 759,
                }
            ]
        }
        settings = {
            "timezone": "America/Los_Angeles",
            "briefing": {
                "enabled": True,
                "time": "11:52",
                "include_day_night": True,
                "include_weather": False,
            },
        }
        state = {"version": 1, "delivered": {}}
        sent = []

        result = watcher.process_astronomy_briefing(
            config=self._notification_config(),
            state=state,
            schedule=schedule,
            settings=settings,
            now=datetime.fromisoformat("2026-09-09T11:53:00-07:00"),
            send_now_func=lambda _config, item: sent.append(item) or True,
        )

        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["payload"]["title"], "ASTRONOMY")
        self.assertNotIn("|", sent[0]["sequence_id"])
        self.assertTrue(sent[0]["payload"]["body"].startswith("2026-09-09\n"))
        self.assertEqual(len(result["delivered"]), 1)

        watcher.process_astronomy_briefing(
            config=self._notification_config(),
            state=result,
            schedule=schedule,
            settings=settings,
            now=datetime.fromisoformat("2026-09-09T12:00:00-07:00"),
            send_now_func=lambda _config, item: sent.append(item) or True,
        )
        self.assertEqual(len(sent), 1)

    def test_astronomy_briefing_saved_after_time_waits_for_next_day(self):
        schedule = {
            "daily_records": [
                {
                    "date": "2026-09-09",
                    "timezone": "America/Los_Angeles",
                    "sunrise": {"time": "2026-09-09T06:45:00-07:00"},
                    "sunset": {"time": "2026-09-09T19:24:00-07:00"},
                    "day_length_minutes": 759,
                },
                {
                    "date": "2026-09-10",
                    "timezone": "America/Los_Angeles",
                    "sunrise": {"time": "2026-09-10T06:45:00-07:00"},
                    "sunset": {"time": "2026-09-10T19:23:00-07:00"},
                    "day_length_minutes": 758,
                },
            ]
        }
        settings = {
            "timezone": "America/Los_Angeles",
            "briefing": {
                "enabled": True,
                "time": "06:00",
                "include_day_night": True,
                "include_weather": False,
                "config_changed_at": "2026-09-09T16:00:00-07:00",
            },
        }
        state = {"version": 1, "delivered": {}}
        sent = []
        send = lambda _config, item: sent.append(item) or True

        result = watcher.process_astronomy_briefing(
            config=self._notification_config(),
            state=state,
            schedule=schedule,
            settings=settings,
            now=datetime.fromisoformat("2026-09-09T16:00:00-07:00"),
            send_now_func=send,
        )
        self.assertEqual(sent, [])
        self.assertEqual(result["delivered"], {})

        result = watcher.process_astronomy_briefing(
            config=self._notification_config(),
            state=result,
            schedule=schedule,
            settings=settings,
            now=datetime.fromisoformat("2026-09-10T06:00:00-07:00"),
            send_now_func=send,
        )
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(result["delivered"]), 1)

    def test_moon_messages_are_compact_and_do_not_repeat_direction_or_event_names(self):
        record = {
            "date": "2026-09-09",
            "sunset": {
                "time": "2026-09-09T19:24:00-07:00",
                "civil_twilight_end": "2026-09-09T19:51:00-07:00",
                "day_length_minutes": 759,
            },
            "moon_status_at_sunset": {
                "phase_degrees": 10,
                "phase_name": "New Moon",
                "phase_trend": "waning",
                "summary": "waning - 1.4% illuminated",
                "above_horizon": False,
                "moonset": "2026-09-09T18:41:00-07:00",
                "moonrise": "2026-09-09T05:06:00-07:00",
            },
            "next_new_moon": "2026-09-10T18:41:00-07:00",
            "moon_phase": 10,
            "moon_phase_trend": "waning",
        }

        grouped = watcher.build_astronomy_briefing_message(
            {"daily_records": [record]},
            "2026-09-09",
            {"briefing": {"enabled": True, "include_day_night": True}},
        )
        evening = watcher.build_evening_astronomy_description(
            record["sunset"], record["moon_status_at_sunset"], record
        )
        moonrise = watcher.build_moon_event_description(record, "Moonrise.", "2026-09-09T05:06:00-07:00")

        for message in (grouped, evening):
            self.assertIn("🌘 ⬇️ Waning Moon — 1.4% illuminated", message)
            self.assertNotIn("Moon: ", message)
            self.assertNotIn("Moon is waning.", message)
        self.assertNotIn("\nSunset.\n", evening)
        self.assertIn("Below horizon", evening)
        self.assertIn("🌙 ↓ Moonset: 18:41", evening)
        self.assertIn("🌙 ↑ Moonrise: 05:06", evening)
        self.assertIn("1 day until New Moon.", grouped)
        self.assertIn("1 day until New Moon.", evening)
        self.assertNotIn("Moonrise.", moonrise)
        self.assertNotIn("Moon is waning.", moonrise)

    def test_exact_moon_phase_day_uses_boundary_name_without_direction_arrow(self):
        record = {
            "date": "2026-09-10",
            "timezone": "America/Los_Angeles",
            "moon_phase": 0.0,
            "new_moon": {"time": "2026-09-10T20:27:00-07:00"},
            "moon_status_at_sunset": {
                "phase_degrees": 0.0,
                "phase_name": "New Moon",
                "phase_trend": "waning",
                "summary": "0% illuminated",
            },
            "next_new_moon": "2026-10-10T08:50:00-07:00",
        }
        message = watcher.build_astronomy_briefing_message(
            {"daily_records": [record]},
            "2026-09-10",
            {"briefing": {"enabled": True, "include_day_night": False}},
        )
        self.assertIn("🌑 New Moon — 0% illuminated", message)
        self.assertNotIn("⬆️", message)
        self.assertNotIn("⬇️", message)

    def test_moon_phase_icon_is_semantic_and_wraps_angles(self):
        self.assertEqual(watcher.moon_phase_icon(0), "🌑")
        self.assertEqual(watcher.moon_phase_icon(180), "🌕")
        self.assertEqual(watcher.moon_phase_icon(360), "🌑")

    def test_weather_fetch_failure_does_not_mark_delivered(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            weather_dir = Path(tmp) / "weather"
            weather_dir.mkdir()

            result = watcher.update_weather_briefing(
                config=self._notification_config(),
                location=self._location(),
                weather_config=weather_store.default_config(),
                now=datetime.fromisoformat("2026-09-07T07:00:00-07:00"),
                weather_state_path=weather_dir / "weather_state.json",
                weather_cache_path=weather_dir / "weather_cache.json",
                fetch_func=lambda _location: (_ for _ in ()).throw(RuntimeError("network down")),
                send_now_func=lambda *_args: True,
                schedule_func=lambda *_args: True,
            )

            self.assertEqual(result["status"], "unavailable")
            self.assertIsNone(result["last_weather_briefing_date"])

    def test_atomic_state_save_and_load(self):
        with tempfile.TemporaryDirectory(dir=watcher.PROJECT_DIR) as tmp:
            path = Path(tmp) / "watcher_state.json"
            state = {
                "version": 1,
                "delivered": {
                    "event|2026-08-02T11:00:00-07:00|0": {
                        "delivered_at": "2026-08-02T11:00:01-07:00"
                    }
                },
            }
            watcher.save_state_atomic(path, state)
            self.assertEqual(json.loads(path.read_text()), state)
            self.assertEqual(watcher.load_state(path), state)

    def _location(self):
        return {
            "version": 1,
            "display_name": "Sunnyvale, California, USA",
            "latitude": 37.3688,
            "longitude": -122.0363,
            "timezone": "America/Los_Angeles",
        }

    def _weather_forecast(self):
        return {
            "version": 1,
            "status": "fresh",
            "location": self._location(),
            "forecast_date": "2026-09-07",
            "high_f": 78,
            "low_f": 59,
            "humidity_min_percent": 40,
            "humidity_max_percent": 70,
            "rain_probability_percent": 0,
            "rain_amount_in": 0,
            "rain_window": None,
            "snow_expected": False,
            "wind_speed_mph": 8,
            "wind_gust_mph": 15,
            "wind_warning": False,
        }

    def _notification_config(self):
        return {
            "ntfy_server": "https://ntfy.sh",
            "ntfy_topic": "blink-private-topic-for-tests",
            "default_priority": "high",
            "default_tags": ["calendar"],
        }


if __name__ == "__main__":
    unittest.main()
