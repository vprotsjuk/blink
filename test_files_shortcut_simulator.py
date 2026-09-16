import unittest

from app.files_shortcut_simulator import simulate_files, simulate_flat_root_files


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

    def test_flat_root_path_filters_package_markers_and_returns_all_attachments(self):
        result = simulate_flat_root_files(
            f"blink-files-v1|{self.package}",
            root_files=(
                f"{self.package}.ready",
                f"{self.package}.manifest.json",
                f"{self.package}__01__485 Notice.jpeg",
                f"{self.package}__02__Appointment Scheduled (1).pdf",
                "other-package__01__wrong.pdf",
            ),
            selected=f"{self.package}__02__Appointment Scheduled (1).pdf",
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.visible_files, (
            f"{self.package}__01__485 Notice.jpeg",
            f"{self.package}__02__Appointment Scheduled (1).pdf",
        ))
        self.assertEqual(result.selected, f"{self.package}__02__Appointment Scheduled (1).pdf")

    def test_flat_root_path_rejects_missing_or_duplicate_package_markers(self):
        for root_files in (
            (f"{self.package}__01__report.pdf",),
            (f"{self.package}.ready", f"{self.package}.ready", f"{self.package}__01__report.pdf"),
            (f"{self.package}.manifest.json", f"{self.package}.manifest.json", f"{self.package}__01__report.pdf"),
        ):
            with self.subTest(root_files=root_files):
                result = simulate_flat_root_files(
                    f"blink-files-v1|{self.package}", root_files=root_files
                )
                self.assertFalse(result.accepted)


if __name__ == "__main__":
    unittest.main()
