import unittest

from app.files_shortcut_simulator import simulate_files


class FilesShortcutSimulatorTests(unittest.TestCase):
    package = "blink-files-v1-" + "a" * 32

    def test_multi_file_view_uses_folder_contents_chooser_and_quick_look(self):
        result = simulate_files(
            f"blink-files-v1|{self.package}",
            view_files=("485 Notice.jpeg", "Appointment Scheduled (1).pdf"),
            selected="Appointment Scheduled (1).pdf",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.selected, "Appointment Scheduled (1).pdf")
        self.assertEqual(result.trace, (
            "Receive Apps and 18 more from Nowhere (Continue if no input)",
            "Get text from Shortcut Input",
            "Comment (build marker)",
            "Match blink-files-v1|<32-hex-package-id>",
            "If match is empty -> Stop this shortcut",
            "Split Text by |",
            "Get Item at Index 2",
            "Set PackageID",
            "Get file from Shortcuts at Blink_Acceptance/ToPhoneView/<PackageID>/",
            "Get contents of File",
            "Set AllFiles to Folder Contents",
            "Choose from AllFiles",
            "Show Selected Item in Quick Look",
            "Stop and output Quick Look",
        ))

    def test_single_file_view_is_still_chooser_backed(self):
        result = simulate_files(
            f"blink-files-v1|{self.package}",
            view_files=("report.pdf",),
            selected="report.pdf",
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.selected, "report.pdf")

    def test_invalid_or_unrelated_input_fails_closed(self):
        for value in ("blink-files-v1|bad", "blink-done-v1|event", ""):
            with self.subTest(value=value):
                result = simulate_files(value, view_files=("report.pdf",))
                self.assertFalse(result.accepted)
                self.assertIsNone(result.payload)

    def test_phone_simulator_does_not_model_manifest_or_ready_files(self):
        result = simulate_files(
            f"blink-files-v1|{self.package}",
            view_files=("report.pdf", ".ready", "other.manifest.json"),
            selected="report.pdf",
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.visible_files, ("report.pdf",))


if __name__ == "__main__":
    unittest.main()
