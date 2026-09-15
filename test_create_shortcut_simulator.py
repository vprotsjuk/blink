import unittest

from app.create_shortcut_simulator import AttachmentInput, CreateInput, simulate_create


class CreateShortcutSimulatorTests(unittest.TestCase):
    def make_input(self, **overrides):
        values = {
            "title": "Test event",
            "description": "Line one\nLine two — 🚦",
            "start": "2026-09-23T02:06:00-07:00",
            "reminders": "17, 0",
            "blinker": "17",
            "attention_level": "green",
            "transport_id": "20260915021144-935344778",
            "attachments": (),
            "created_at": "2026-09-15T02:11:44-07:00",
        }
        values.update(overrides)
        return CreateInput(**values)

    def test_valid_direct_payload_preserves_text_and_names(self):
        result = simulate_create(self.make_input())

        self.assertTrue(result.accepted)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.output_names, (
            "20260915021144-935344778.event.json",
            "20260915021144-935344778.ready",
        ))
        self.assertEqual(result.payload["title"], "Test event")
        self.assertEqual(result.payload["description"], "Line one\nLine two — 🚦")
        self.assertEqual(result.payload["reminder_intent"]["offsets_minutes_before"], [17, 0])
        self.assertEqual(result.payload["blinker_intent"]["minutes_before"], 17)
        self.assertEqual(result.payload["start"], "2026-09-23T02:06:00-07:00")
        self.assertEqual(result.payload["created_at"], "2026-09-15T02:11:44-07:00")
        self.assertEqual(result.trace, (
            "Receive Shortcut Input",
            "Title: Ask for Text -> Match \\S -> Stop on empty",
            "Description: Ask for optional Text -> Set variable",
            "Start: Ask for Date and Time -> Set variable",
            "Importance: Choose from Menu -> Menu Result",
            "Reminders: Split -> Repeat -> Match -> Get Numbers -> >= 0 -> Add",
            "Blinker: Ask for Number -> native integer validation",
            "Transport: Current Date -> Format -> Random -> TransferID",
            "Serialization: JSON Text -> Save event.json -> optional attachment -> Save .ready last",
        ))

    def test_valid_single_pdf_adds_attachment_name_and_metadata(self):
        result = simulate_create(self.make_input(
            attachments=(AttachmentInput("Appointment Scheduled (1).pdf"),),
        ))

        self.assertTrue(result.accepted)
        self.assertEqual(result.output_names, (
            "20260915021144-935344778.event.json",
            "20260915021144-935344778.attachment.pdf",
            "20260915021144-935344778.ready",
        ))
        self.assertEqual(result.payload["attachment"], {
            "basename": "20260915021144-935344778.attachment.pdf",
            "original_filename": "Appointment Scheduled (1).pdf",
        })

    def test_invalid_title_is_rejected_without_payload(self):
        for title in ("", "   ", "\n\t"):
            with self.subTest(title=repr(title)):
                result = simulate_create(self.make_input(title=title))
                self.assertFalse(result.accepted)
                self.assertIsNone(result.payload)

    def test_invalid_numeric_values_are_rejected_without_coercion(self):
        for field in ("reminders", "blinker"):
            for value in ("-1", "17.5", "abc", "17x", "1,abc"):
                with self.subTest(field=field, value=value):
                    kwargs = {field: value}
                    result = simulate_create(self.make_input(**kwargs))
                    self.assertFalse(result.accepted)
                    self.assertIsNone(result.payload)

    def test_zero_values_are_valid(self):
        result = simulate_create(self.make_input(reminders="0", blinker="0"))

        self.assertTrue(result.accepted)
        self.assertEqual(result.payload["reminder_intent"]["offsets_minutes_before"], [0])
        self.assertEqual(result.payload["blinker_intent"]["minutes_before"], 0)

    def test_more_than_one_attachment_is_rejected_before_first_item(self):
        result = simulate_create(self.make_input(attachments=(
            AttachmentInput("one.pdf"),
            AttachmentInput("two.jpg"),
        )))

        self.assertFalse(result.accepted)
        self.assertIn("at most one attachment", result.errors[0])
        self.assertIsNone(result.payload)

    def test_transport_id_requires_nine_digit_random_suffix(self):
        for transport_id in (
            "20260915021144-12345678",
            "20260915021144-1234567890",
            "20260915021144-r12345678",
        ):
            with self.subTest(transport_id=transport_id):
                result = simulate_create(self.make_input(transport_id=transport_id))
                self.assertFalse(result.accepted)
                self.assertIsNone(result.payload)


if __name__ == "__main__":
    unittest.main()
