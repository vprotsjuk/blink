import unittest

from app.done_shortcut_simulator import simulate_done


class DoneShortcutSimulatorTests(unittest.TestCase):
    def test_valid_done_command_matches_phone_shortcut_blocks(self):
        result = simulate_done(
            "blink-done-v1|event-123",
            command_id="20260915030000-123456789",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.event_id, "event-123")
        self.assertEqual(result.output_names, (
            "20260915030000-123456789.done.json",
            "20260915030000-123456789.ready",
        ))
        self.assertEqual(result.payload, {
            "version": 1,
            "type": "DONE",
            "command_id": "20260915030000-123456789",
            "event_id": "event-123",
        })
        self.assertEqual(result.trace, (
            "Receive Shortcut Input",
            "Validate literal blink-done-v1|<event-id>",
            "Current Date -> Format -> Random -> command_id",
            "JSON Text -> Save .done.json -> Save .ready last",
        ))

    def test_malformed_done_input_does_not_create_payload(self):
        result = simulate_done("blink-done-v1|")

        self.assertFalse(result.accepted)
        self.assertIsNone(result.payload)
        self.assertEqual(result.output_names, ())


if __name__ == "__main__":
    unittest.main()
