import unittest

from app.files_shortcut_simulator import simulate_get_file_boundary


class FilesShortcutBoundaryTests(unittest.TestCase):
    package = "blink-files-v1-" + "a" * 32
    files = ("485 Notice.jpeg", "Appointment Scheduled (1).pdf")

    def test_literal_package_path_returns_folder_contents_for_choose(self):
        result = simulate_get_file_boundary(
            base_path="Blink_Acceptance/ToPhoneView",
            package_id=self.package,
            package_files=self.files,
            path_binding="literal-full-package-path",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.object_type, "Folder")
        self.assertEqual(result.contents_type, "List[File]")
        self.assertEqual(result.choose_input, self.files)

    def test_magic_variable_package_path_resolves_to_same_folder(self):
        result = simulate_get_file_boundary(
            base_path="Blink_Acceptance/ToPhoneView",
            package_id=self.package,
            package_files=self.files,
            path_binding="magic-variable",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(result.resolved_path, f"Blink_Acceptance/ToPhoneView/{self.package}/")
        self.assertEqual(result.choose_input, self.files)

    def test_unresolved_package_token_cannot_feed_choose(self):
        result = simulate_get_file_boundary(
            base_path="Blink_Acceptance/ToPhoneView",
            package_id=self.package,
            package_files=self.files,
            path_binding="literal-packageid-token",
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.resolved_path, "Blink_Acceptance/ToPhoneView/PackageID/")
        self.assertIsNone(result.choose_input)


if __name__ == "__main__":
    unittest.main()
