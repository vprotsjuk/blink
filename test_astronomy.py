import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from astronomy import generate_astronomy


class AstronomyGeneratorTests(unittest.TestCase):
    def test_default_config_uses_sunnyvale_and_los_angeles_timezone(self):
        config = generate_astronomy.default_config(generate_astronomy.default_location())
        self.assertEqual(config["location"]["display_name"], "Sunnyvale, California, USA")
        self.assertEqual(config["timezone"], "America/Los_Angeles")
        self.assertIn("latitude", config["location"])
        self.assertIn("longitude", config["location"])

    def test_supported_facts_are_independent_of_notification_toggles(self):
        config = generate_astronomy.default_config(generate_astronomy.default_location())
        config["notifications"]["moon"]["events"]["moonrise"]["enabled"] = False
        self.assertIn("sunrise", generate_astronomy.SUPPORTED_FACTS["sun"])
        self.assertIn("moonrise", generate_astronomy.SUPPORTED_FACTS["moon"])
        self.assertFalse(config["notifications"]["moon"]["events"]["moonrise"]["enabled"])
        self.assertEqual(set(config["notifications"]), {"sun", "moon"})
        self.assertNotIn(
            "offsets_minutes_before",
            config["notifications"]["sun"]["events"]["sunrise"],
        )

    def test_missing_skyfield_reports_dependency_without_fake_schedule(self):
        status = generate_astronomy.dependency_status(importer=lambda _name: (_ for _ in ()).throw(ImportError("nope")))
        self.assertFalse(status["available"])
        self.assertIn("skyfield", status["required"])

    def test_write_default_files_creates_config_and_empty_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate_astronomy.write_default_files(root)
            config = json.loads((root / "astronomy_config.json").read_text())
            schedule = json.loads((root / "astronomy_schedule.json").read_text())
        self.assertEqual(config["timezone"], "America/Los_Angeles")
        self.assertEqual(schedule["daily_records"], [])
        self.assertEqual(schedule["generation_status"], "pending_precise_ephemeris")
        self.assertEqual(schedule["horizon_months"], 24)

    def test_planned_generation_range_is_24_months(self):
        start = date(2026, 9, 7)
        end = generate_astronomy.horizon_end_date(start, months=24)
        self.assertEqual(str(end), "2028-09-07")

    def test_horizon_extension_needed_under_six_months(self):
        schedule = {"generated_through": "2027-02-01"}
        self.assertTrue(
            generate_astronomy.needs_horizon_extension(
                schedule,
                today=date(2026, 9, 7),
                minimum_remaining_months=6,
            )
        )
        schedule["generated_through"] = "2027-05-08"
        self.assertFalse(
            generate_astronomy.needs_horizon_extension(
                schedule,
                today=date(2026, 9, 7),
                minimum_remaining_months=6,
            )
        )

    def test_moonrise_none_is_valid_daily_record(self):
        record = generate_astronomy.empty_daily_record(date(2026, 9, 7), "America/Los_Angeles")
        record["moonrise"] = None
        record["next_moonrise"] = "2026-09-08T00:17:00-07:00"
        generate_astronomy.validate_daily_record_shape(record)

    def test_disabled_astronomy_notification_keeps_raw_data(self):
        config = generate_astronomy.default_config(generate_astronomy.default_location())
        config["notifications"]["sun"]["events"]["sunrise"]["enabled"] = False
        record = generate_astronomy.empty_daily_record(date(2026, 9, 7), "America/Los_Angeles")
        record["sunrise"] = {"time": "2026-09-07T06:42:00-07:00"}
        self.assertEqual(record["sunrise"]["time"], "2026-09-07T06:42:00-07:00")
        self.assertFalse(config["notifications"]["sun"]["events"]["sunrise"]["enabled"])

    def test_moon_phase_name_and_trend(self):
        self.assertEqual(generate_astronomy.moon_phase_name(30), "Waxing Moon")
        self.assertEqual(generate_astronomy.moon_phase_trend(30), "waxing")
        self.assertEqual(generate_astronomy.moon_phase_name(330), "Waning Moon")
        self.assertEqual(generate_astronomy.moon_phase_trend(330), "waning")

    def test_new_and_full_moon_names_require_an_exact_event(self):
        self.assertEqual(generate_astronomy.moon_phase_name(0), "Waning Moon")
        self.assertEqual(generate_astronomy.moon_phase_name(180), "Waning Moon")
        self.assertEqual(
            generate_astronomy.moon_phase_name(346.6, exact_event="New Moon"),
            "New Moon",
        )
        self.assertEqual(
            generate_astronomy.moon_phase_name(179.9, exact_event="Full Moon"),
            "Full Moon",
        )

    def test_astronomy_excludes_eclipses_from_active_model(self):
        config = generate_astronomy.default_config(generate_astronomy.default_location())
        schedule = generate_astronomy.build_empty_schedule(
            generate_astronomy.default_location(), today=date(2026, 9, 7)
        )
        self.assertEqual(set(config["notifications"]), {"sun", "moon"})
        self.assertNotIn("eclipses", config["notifications"])
        self.assertNotIn("eclipse_status", schedule)
        self.assertNotIn("eclipses", schedule)
        self.assertNotIn("eclipses", generate_astronomy.SUPPORTED_FACTS)

    def test_legacy_eclipse_config_is_removed_when_defaults_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "astronomy_config.json").write_text(
                json.dumps(
                    {
                        "notifications": {"eclipses": {"enabled": True}},
                        "reminder_presets_minutes_before": [30, 0],
                    }
                )
            )
            generate_astronomy.write_default_files(root)
            config = json.loads((root / "astronomy_config.json").read_text())
        self.assertNotIn("eclipses", config["notifications"])
        self.assertNotIn("reminder_presets_minutes_before", config)
        self.assertTrue(
            all(
                "offsets_minutes_before" not in event
                for group in config["notifications"].values()
                for event in group.get("events", {}).values()
            )
        )


if __name__ == "__main__":
    unittest.main()
