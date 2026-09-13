import os
import unittest
from datetime import datetime
from unittest.mock import patch

from app.notification_format import (
    MAX_NTFY_BODY_BYTES,
    MAX_NTFY_TITLE_BYTES,
    build_event_notification,
    build_done_action,
    build_done_confirmation_payload,
    build_files_action,
    build_event_payload,
    push_tags_for_event,
)


class NotificationFormatTests(unittest.TestCase):
    def personal_event(self, **overrides):
        event = {
            "id": "event-abc_123",
            "title": "Visit",
            "description": "Bring papers",
            "start": "2026-09-14T15:00:00-07:00",
            "source": "personal",
            "requires_done": True,
            "done": False,
            "priority": "default",
            "tags": ["calendar"],
        }
        event.update(overrides)
        return event

    def test_done_action_is_versioned_encoded_and_contains_only_real_event_id(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BLINK_NTFY_DONE_SHORTCUT_NAME", None)
            action = build_done_action(self.personal_event(), enabled=True)
        self.assertIn("shortcuts://run-shortcut?", action)
        self.assertIn("name=Blink%20DONE", action)
        self.assertNotIn("Blink+DONE", action)
        self.assertIn("blink-done-v1%7Cevent-abc_123", action)
        self.assertNotIn("command_id", action)
        self.assertNotIn("occurrence_id", action)
        self.assertNotIn("clear=true", action)
        self.assertEqual(action.split("&text=", 1)[1], "blink-done-v1%7Cevent-abc_123")

    def test_done_action_uses_url_encoded_optional_shortcut_override(self):
        with patch.dict(os.environ, {"BLINK_NTFY_DONE_SHORTCUT_NAME": "Blink DONE Test"}):
            action = build_done_action(self.personal_event(), enabled=True)
        self.assertIn("name=Blink%20DONE%20Test", action)
        self.assertNotIn("Blink+DONE", action)

    def test_empty_or_invalid_shortcut_override_uses_production_default(self):
        for value in ("", "   ", "Blink\nDONE"):
            with self.subTest(value=value), patch.dict(os.environ, {"BLINK_NTFY_DONE_SHORTCUT_NAME": value}):
                action = build_done_action(self.personal_event(), enabled=True)
                self.assertIn("name=Blink%20DONE", action)
                self.assertNotIn("Blink+DONE", action)

    def test_done_action_encodes_reserved_input_for_unusual_valid_event_id(self):
        action = build_done_action(self.personal_event(id="event:abc/123?x=1&y=2"), enabled=True)
        self.assertIn("blink-done-v1%7Cevent%3Aabc%2F123%3Fx%3D1%26y%3D2", action)
        self.assertNotIn("?x=1", action)
        self.assertNotIn("&y=2", action)

    def test_done_action_encodes_query_injection_characters(self):
        action = build_done_action(self.personal_event(id="event-a&evil=b|c"), enabled=True)
        self.assertIn("event-a%26evil%3Db%7Cc", action)
        self.assertNotIn("&evil=b", action)

    def test_done_action_is_only_for_eligible_personal_events(self):
        self.assertIsNone(build_done_action(self.personal_event(done=True), enabled=True))
        self.assertIsNone(build_done_action(self.personal_event(requires_done=False), enabled=True))
        self.assertIsNone(build_done_action(self.personal_event(source="astronomy"), enabled=True))
        self.assertIsNone(build_done_action(self.personal_event(id=""), enabled=True))

    def test_weather_and_astronomy_never_receive_done_action(self):
        self.assertIsNone(
            build_done_action(self.personal_event(source="weather"), enabled=True)
        )
        self.assertIsNone(
            build_done_action(self.personal_event(source="astronomy"), enabled=True)
        )

    def test_done_action_is_disabled_by_default(self):
        self.assertIsNone(build_done_action(self.personal_event()))

    def test_feature_off_payload_has_no_done_action(self):
        payload = build_event_payload(
            {"default_priority": "high", "default_tags": ["calendar"], "done_action_enabled": False},
            self.personal_event(),
            0,
        )
        self.assertNotIn("actions", payload)

    def test_done_confirmation_payload_contains_title_description_and_schedule_without_action(self):
        payload = build_done_confirmation_payload(self.personal_event())
        self.assertEqual(payload["title"], "✓ Done — Visit")
        self.assertEqual(payload["body"], "Bring papers\nScheduled: September 14, 2026 at 15:00")
        self.assertNotIn("actions", payload)

    def test_done_confirmation_payload_omits_empty_description(self):
        payload = build_done_confirmation_payload(self.personal_event(description=""))
        self.assertEqual(payload["body"], "Scheduled: September 14, 2026 at 15:00")

    def test_direct_payload_and_queued_payload_share_action_representation(self):
        payload = build_event_payload(
            {"default_priority": "high", "default_tags": ["calendar"], "done_action_enabled": True},
            self.personal_event(),
            0,
        )
        self.assertEqual(payload["actions"], build_done_action(self.personal_event(), enabled=True))

    def test_files_action_uses_percent20_and_encoded_transport_input(self):
        package = "blink-files-v1-" + "a" * 32
        action = build_files_action(package, shortcut_name="Blink Files")
        self.assertIn("name=Blink%20Files", action)
        self.assertNotIn("Blink+Files", action)
        self.assertIn("blink-files-v1%7C" + package, action)
        self.assertNotIn("clear=true", action)

    def test_files_payload_requires_opt_in_and_package_id(self):
        event = self.personal_event(attachments={"owner_id": "event-abc_123", "count": 1, "has_files": True})
        package = "blink-files-v1-" + "b" * 32
        off = build_event_payload({"default_priority": "high", "default_tags": ["calendar"]}, event, 0, files_package_id=package)
        self.assertNotIn("actions", off)
        on = build_event_payload(
            {"default_priority": "high", "default_tags": ["calendar"], "files_action_enabled": True},
            event,
            0,
            files_package_id=package,
        )
        self.assertIn("actions", on)
        self.assertIn("Files", on["actions"])

    def test_files_action_excludes_weather_astronomy_and_no_files(self):
        for event in (
            self.personal_event(attachments={"owner_id": "event-abc_123", "count": 0, "has_files": False}),
            self.personal_event(source="weather", attachments={"owner_id": "event-abc_123", "count": 1, "has_files": True}),
            self.personal_event(source="astronomy", attachments={"owner_id": "event-abc_123", "count": 1, "has_files": True}),
        ):
            payload = build_event_payload(
                {"default_priority": "high", "default_tags": ["calendar"], "files_action_enabled": True},
                event,
                0,
                files_package_id=None if not event.get("attachments", {}).get("has_files") else "blink-files-v1-" + "c" * 32,
            )
            self.assertNotIn("Files", payload.get("actions", ""))
    def test_event_notification_uses_title_and_readable_description(self):
        event = {
            "title": "Визит ко клиенту",
            "description": "Не забыть взять рулетку",
            "start": "2026-09-14T15:00:00-07:00",
        }

        title, body = build_event_notification(event, 10)

        self.assertEqual(title, "🟢 Визит ко клиенту")
        self.assertEqual(
            body,
            "September 14, 2026 at 15:00\n"
            "Не забыть взять рулетку\n"
            "10 min before start",
        )

    def test_event_notification_has_no_json_or_calendar_metadata(self):
        event = {
            "title": "Test",
            "description": "Description",
            "start": "2026-09-14T15:00:00-07:00",
        }

        _, body = build_event_notification(event, 0)

        self.assertEqual(body, "September 14, 2026 at 15:00\nDescription\nEvent starts now")
        self.assertNotIn("{", body)
        self.assertNotIn("calendar", body.lower())

    def test_event_notification_uses_deferred_start_when_provided(self):
        event = {
            "title": "Визит",
            "description": "Рулетка",
            "start": "2026-09-13T15:00:00-07:00",
        }

        _, body = build_event_notification(event, 30, "2026-09-14T15:00:00-07:00")

        self.assertTrue(body.startswith("September 14, 2026 at 15:00"))

    def test_event_notification_marks_local_attachments_after_attention_icon(self):
        title, _ = build_event_notification(
            {
                "title": "Bring documents",
                "description": "Files are in Blink",
                "start": "2026-09-14T15:00:00-07:00",
                "attachments": {"owner_id": "event-1", "count": 2, "has_files": True},
            },
            0,
        )
        self.assertEqual(title, "🟢 📎 Bring documents")

    def test_event_notification_preserves_paragraphs_and_bounds_utf8_push_projection(self):
        description = "First paragraph\n\n" + ("Очень длинная строка. " * 500)
        title, body = build_event_notification(
            {
                "title": "First line\nSecond line should stay local",
                "description": description,
                "start": "2026-09-14T15:00:00-07:00",
            },
            0,
        )
        self.assertEqual(title, "🟢 First line")
        self.assertLessEqual(len(title.encode("utf-8")), MAX_NTFY_TITLE_BYTES)
        self.assertLessEqual(len(body.encode("utf-8")), MAX_NTFY_BODY_BYTES)
        self.assertIn("First paragraph\n\n", body)
        self.assertIn("Event starts now", body)

    def test_astronomy_title_uses_approved_sun_icons(self):
        cases = (
            ("Sunrise", ["astronomy", "sunrise"], "☀️ ↑ Sunrise"),
            ("Solar noon", ["astronomy", "solar-noon"], "☀️ Solar noon"),
            ("Sunset", ["astronomy", "sunset", "moon"], "☀️ ↓ Sunset"),
            ("Civil twilight ends", ["astronomy", "civil-twilight"], "✨ Civil twilight ends"),
        )

        for title, tags, expected in cases:
            with self.subTest(title=title):
                actual, _ = build_event_notification(
                    {
                        "title": title,
                        "description": title,
                        "start": "2026-09-14T19:00:00-07:00",
                        "source": "astronomy",
                        "tags": tags,
                    },
                    0,
                )
                self.assertEqual(actual, expected)

    def test_lunar_rise_title_uses_thin_rise_arrow(self):
        title, _ = build_event_notification(
            {
                "title": "Moonrise",
                "description": "Moonrise.",
                "start": "2026-09-14T19:00:00-07:00",
                "source": "astronomy",
                "tags": ["astronomy", "moonrise"],
                "moon_phase_icon": "🌗",
                "moon_phase_trend": "waning",
            },
            0,
        )
        self.assertEqual(title, "🌙 ↑ Moonrise")

    def test_exact_new_and_full_moon_titles_omit_direction_arrow(self):
        for title, icon, tags in (
            ("New Moon", "🌑", ["astronomy", "moon", "new-moon"]),
            ("Full Moon", "🌕", ["astronomy", "moon", "full-moon"]),
        ):
            with self.subTest(title=title):
                actual, _ = build_event_notification(
                    {
                        "title": title,
                        "start": "2026-09-14T19:00:00-07:00",
                        "source": "astronomy",
                        "tags": tags,
                        "notification_icon": icon,
                        "moon_phase_trend": "waning",
                    },
                    0,
                )
                self.assertEqual(actual, f"{icon} {title}")

    def test_individual_astronomy_body_removes_duplicate_event_and_start_line(self):
        title, body = build_event_notification(
            {
                "title": "Solar noon",
                "description": "Solar noon. Sun: 57.4° above horizon.",
                "start": "2026-09-10T13:05:00-07:00",
                "source": "astronomy",
                "tags": ["astronomy", "solar-noon"],
            },
            0,
        )
        self.assertEqual(title, "☀️ Solar noon")
        self.assertEqual(
            body,
            "September 10, 2026 at 13:05\nSun altitude: 57.4° above horizon.",
        )
        self.assertNotIn("Solar noon.", body)
        self.assertNotIn("Event starts now", body)

    def test_individual_astronomy_push_has_no_outgoing_ntfy_tags(self):
        self.assertEqual(
            push_tags_for_event(
                {"source": "astronomy", "tags": ["astronomy", "sunset"]},
                ["calendar"],
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
