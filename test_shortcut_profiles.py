import unittest

from app.shortcut_profiles import SHORTCUT_PROFILES, product_roles


class ShortcutProfileTests(unittest.TestCase):
    def test_simulation_has_exactly_three_product_roles(self):
        self.assertEqual(product_roles(), ("CREATE", "DONE", "FILES"))

    def test_variants_are_comparison_profiles_not_product_roles(self):
        self.assertEqual(SHORTCUT_PROFILES["CREATE"]["target"], "Blink")
        self.assertEqual(SHORTCUT_PROFILES["DONE"]["target"], "Blink DONE")
        self.assertEqual(SHORTCUT_PROFILES["FILES"]["target"], "Blink Files")


if __name__ == "__main__":
    unittest.main()
