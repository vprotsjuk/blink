import unittest
from datetime import datetime

from app.notification_format import (
    MAX_NTFY_BODY_BYTES,
    MAX_NTFY_TITLE_BYTES,
    build_event_notification,
)


class NotificationFormatTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
