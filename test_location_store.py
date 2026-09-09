import json
import tempfile
import unittest
from pathlib import Path

from app import location_store


class LocationStoreTests(unittest.TestCase):
    def test_default_location_loads_sunnyvale(self):
        location = location_store.default_location()
        self.assertEqual(location["display_name"], "Sunnyvale, California, USA")
        self.assertAlmostEqual(location["latitude"], 37.3688, places=4)
        self.assertAlmostEqual(location["longitude"], -122.0363, places=4)
        self.assertEqual(location["timezone"], "America/Los_Angeles")

    def test_city_geocoder_result_saves_canonical_location(self):
        result = {
            "name": "Sunnyvale",
            "admin1": "California",
            "country": "United States",
            "country_code": "US",
            "latitude": 37.3688,
            "longitude": -122.0363,
            "timezone": "America/Los_Angeles",
        }
        location = location_store.location_from_geocoder_result(result)
        self.assertEqual(location["display_name"], "Sunnyvale, California, United States")
        self.assertEqual(location["latitude"], 37.3688)
        self.assertEqual(location["longitude"], -122.0363)
        self.assertEqual(location["timezone"], "America/Los_Angeles")

    def test_geocoder_url_response_normalizes_results(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({
                    "results": [{
                        "name": "Kyiv",
                        "admin1": "Kyiv City",
                        "country": "Ukraine",
                        "latitude": 50.45,
                        "longitude": 30.52,
                        "timezone": "Europe/Kyiv",
                    }]
                }).encode("utf-8")

        results = location_store.search_city_from_url(
            "https://example.test/geocode",
            opener=lambda _url, timeout: FakeResponse(),
        )
        self.assertEqual(results[0]["display_name"], "Kyiv, Kyiv City, Ukraine")
        self.assertEqual(results[0]["timezone"], "Europe/Kyiv")

    def test_manual_coordinates_are_validated(self):
        location = location_store.build_manual_location(
            display_name="Manual",
            latitude="37.3",
            longitude="-122.0",
            timezone_name="America/Los_Angeles",
        )
        self.assertEqual(location["latitude"], 37.3)
        self.assertEqual(location["longitude"], -122.0)
        with self.assertRaises(ValueError):
            location_store.build_manual_location(
                display_name="Bad",
                latitude="120",
                longitude="-122",
                timezone_name="America/Los_Angeles",
            )

    def test_manual_coordinates_without_timezone_are_not_guessed(self):
        with self.assertRaises(ValueError):
            location_store.build_manual_location(
                display_name="Manual",
                latitude="37.3",
                longitude="-122.0",
                timezone_name="",
            )

    @unittest.skipUnless(location_store._TIMEZONE_FINDER is not None, "timezone map is installed")
    def test_manual_coordinates_reject_mismatched_timezone(self):
        with self.assertRaisesRegex(ValueError, "does not match coordinates"):
            location_store.build_manual_location(
                display_name="Sunnyvale with wrong zone",
                latitude="37.3688",
                longitude="-122.0363",
                timezone_name="Europe/Kyiv",
            )

    def test_location_change_preserves_personal_and_invalidates_dependents(self):
        old_location = location_store.default_location()
        new_location = location_store.build_manual_location(
            display_name="Warsaw, Poland",
            latitude="52.2297",
            longitude="21.0122",
            timezone_name="Europe/Warsaw",
        )
        agenda = {
            "version": 1,
            "events": [
                {
                    "id": "dentist",
                    "title": "Dentist",
                    "start": "2026-09-12T19:00:00-07:00",
                    "reminders_minutes_before": [0],
                    "enabled": True,
                }
            ],
        }
        astronomy = {
            "version": 1,
            "location_fingerprint": location_store.location_fingerprint(old_location),
            "daily_records": [{"date": "2026-09-12"}],
        }
        weather_cache = {
            "version": 1,
            "location_fingerprint": location_store.location_fingerprint(old_location),
            "forecast_date": "2026-09-12",
        }
        schedule_state = {
            "version": 1,
            "scheduled": {
                "astro-sunset-2026-09-12-0": {
                    "source": "astronomy",
                    "status": "queued",
                    "location_fingerprint": location_store.location_fingerprint(old_location),
                },
                "personal-dentist-0": {
                    "source": "personal",
                    "status": "queued",
                    "location_fingerprint": location_store.location_fingerprint(old_location),
                },
            },
        }

        changed = location_store.apply_location_change(
            agenda=agenda,
            astronomy_schedule=astronomy,
            weather_cache=weather_cache,
            remote_schedule_state=schedule_state,
            new_location=new_location,
        )

        self.assertEqual(changed["agenda"], agenda)
        self.assertEqual(changed["astronomy_schedule"]["daily_records"], [])
        self.assertEqual(changed["astronomy_schedule"]["generation_status"], "needs_regeneration")
        self.assertEqual(changed["weather_cache"]["status"], "stale_location_changed")
        self.assertEqual(
            changed["remote_schedule_state"]["scheduled"]["astro-sunset-2026-09-12-0"]["status"],
            "pending_cancel",
        )
        self.assertEqual(
            changed["remote_schedule_state"]["scheduled"]["personal-dentist-0"]["status"],
            "queued",
        )

    def test_atomic_location_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "location.json"
            location_store.save_location_atomic(path, location_store.default_location())
            loaded = location_store.load_location(path)
        self.assertEqual(loaded["timezone"], "America/Los_Angeles")


if __name__ == "__main__":
    unittest.main()
