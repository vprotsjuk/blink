import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app import location_store, weather_store


class WeatherStoreTests(unittest.TestCase):
    def sample_payload(self):
        return {
            "daily": {
                "time": ["2026-09-07"],
                "temperature_2m_max": [68.0],
                "temperature_2m_min": [48.0],
                "precipitation_probability_max": [70],
                "rain_sum": [0.12],
                "snowfall_sum": [0.0],
                "wind_speed_10m_max": [12.0],
                "wind_gusts_10m_max": [27.0],
            },
            "hourly": {
                "time": [
                    "2026-09-07T06:00",
                    "2026-09-07T13:00",
                    "2026-09-07T14:00",
                    "2026-09-07T15:00",
                    "2026-09-07T18:00",
                    "2026-09-08T06:00",
                ],
                "relative_humidity_2m": [52, 45, 70, 82, 60, 99],
                "precipitation_probability": [10, 10, 70, 65, 15, 0],
                "rain": [0.0, 0.0, 0.05, 0.07, 0.0, 0.0],
                "snowfall": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
        }

    def test_default_weather_config(self):
        config = weather_store.default_config()
        self.assertTrue(config["weather_enabled"])
        self.assertTrue(config["morning_briefing"]["enabled"])
        self.assertEqual(config["morning_briefing"]["time"], "06:30")
        self.assertTrue(config["include"]["temperature"])
        self.assertTrue(config["include"]["humidity"])
        self.assertTrue(config["include"]["wind"])
        self.assertTrue(config["include"]["rain"])
        self.assertTrue(config["include"]["snow"])
        self.assertEqual(config["units"]["temperature"], "fahrenheit")
        self.assertEqual(config["thresholds"]["rain_probability_percent"], 40)
        self.assertEqual(config["thresholds"]["wind_gust_mph"], 25)

    def test_weather_provider_success_normalizes_forecast(self):
        location = location_store.default_location()
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location,
            fetched_at=datetime.fromisoformat("2026-09-07T06:02:00-07:00"),
            config=weather_store.default_config(),
        )
        self.assertEqual(forecast["forecast_date"], "2026-09-07")
        self.assertEqual(forecast["high_f"], 68)
        self.assertEqual(forecast["low_f"], 48)
        self.assertEqual(forecast["humidity_min_percent"], 45)
        self.assertEqual(forecast["humidity_max_percent"], 82)
        self.assertEqual(forecast["humidity_today_min_percent"], 45)
        self.assertEqual(forecast["humidity_today_max_percent"], 82)
        self.assertEqual(forecast["humidity_now_percent"], 52)
        self.assertEqual(forecast["humidity_now_time"], "06:00")
        self.assertEqual(forecast["rain_probability_percent"], 70)
        self.assertEqual(forecast["rain_window"], "14:00-15:00")
        self.assertFalse(forecast["snow_expected"])
        self.assertEqual(forecast["snow_probability_percent"], 0)
        self.assertTrue(forecast["wind_warning"])

    def test_weather_message_respects_include_flags(self):
        config = weather_store.default_config()
        config["include"] = {
            "temperature": True,
            "humidity": False,
            "wind": False,
            "rain": True,
            "snow": False,
        }
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location_store.default_location(),
            fetched_at=datetime.fromisoformat("2026-09-07T06:02:00-07:00"),
            config=config,
        )
        message = weather_store.build_morning_briefing_message(forecast)
        self.assertIn("🌡️ Temperature:", message)
        self.assertIn("☀️ 68°F   🌙 48°F", message)
        self.assertNotIn("Max today", message)
        self.assertIn("🌧️ Rain: probability 70%", message)
        self.assertNotIn("💧 Humidity:", message)
        self.assertNotIn("💨 Wind:", message)

    def test_weather_message_contains_facts_no_clothing_advice(self):
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location_store.default_location(),
            fetched_at=datetime.fromisoformat("2026-09-07T06:02:00-07:00"),
            config=weather_store.default_config(),
        )
        message = weather_store.build_morning_briefing_message(forecast)
        self.assertIn("☀️ 68°F   🌙 48°F", message)
        self.assertNotIn("Max today", message)
        self.assertNotIn("Min tonight", message)
        self.assertIn("🌡️ Temperature:", message)
        self.assertIn("💧 Humidity:", message)
        self.assertIn("Today: 45–82%", message)
        self.assertIn("Now: 52%", message)
        self.assertNotIn("Max: 82%", message)
        self.assertNotIn("Min: 45%", message)
        self.assertIn("🌧️ Rain: probability 70%", message)
        self.assertIn("❄️ Snow: probability", message)
        self.assertIn("💨 Wind: 12 mph", message)
        self.assertNotIn("jacket", message.lower())
        self.assertNotIn("wear", message.lower())

    def test_api_failure_does_not_mark_briefing_delivered(self):
        state = weather_store.default_state()
        updated = weather_store.record_fetch_failure(state, "offline")
        self.assertIsNone(updated.get("last_weather_briefing_date"))
        self.assertEqual(updated["status"], "unavailable")

    def test_wake_after_briefing_time_sends_once(self):
        config = weather_store.default_config()
        location = location_store.default_location()
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location,
            fetched_at=datetime.fromisoformat("2026-09-07T07:15:00-07:00"),
            config=config,
        )
        state = weather_store.default_state()
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=state,
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T07:15:00-07:00"),
        )
        self.assertEqual(decision["action"], "send_now")
        state = weather_store.mark_briefing_delivered(state, forecast, "direct")
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=state,
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T09:00:00-07:00"),
        )
        self.assertEqual(decision["action"], "none")

    def test_before_briefing_time_remains_local_pending(self):
        config = weather_store.default_config()
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location_store.default_location(),
            fetched_at=datetime.fromisoformat("2026-09-07T05:30:00-07:00"),
            config=config,
        )
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=weather_store.default_state(),
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T05:30:00-07:00"),
        )
        self.assertEqual(decision["action"], "none")

    def test_changing_briefing_time_allows_second_same_day_delivery(self):
        config = weather_store.default_config()
        config["morning_briefing"]["time"] = "21:00"
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location_store.default_location(),
            fetched_at=datetime.fromisoformat("2026-09-07T20:55:00-07:00"),
            config=config,
        )
        state = {
            "last_weather_briefing_date": "2026-09-07",
            "last_weather_briefing_key": "2026-09-07|06:30",
        }
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=state,
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T21:00:00-07:00"),
        )
        self.assertEqual(decision["action"], "send_now")

    def test_config_saved_after_briefing_time_defers_until_next_day(self):
        config = weather_store.default_config()
        config["morning_briefing"]["time"] = "06:00"
        forecast = weather_store.normalize_open_meteo_forecast(
            payload=self.sample_payload(),
            location=location_store.default_location(),
            fetched_at=datetime.fromisoformat("2026-09-07T16:00:00-07:00"),
            config=config,
        )
        state = {
            "briefing_config_changed_at": "2026-09-07T16:00:00-07:00",
            "last_weather_briefing_key": None,
        }
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=state,
            forecast=forecast,
            now=datetime.fromisoformat("2026-09-07T16:00:00-07:00"),
        )
        self.assertEqual(decision["action"], "none")

        next_day_forecast = dict(forecast)
        next_day_forecast["forecast_date"] = "2026-09-08"
        decision = weather_store.morning_briefing_decision(
            config=config,
            state=state,
            forecast=next_day_forecast,
            now=datetime.fromisoformat("2026-09-08T06:00:00-07:00"),
        )
        self.assertEqual(decision["action"], "send_now")

    def test_atomic_weather_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weather_cache.json"
            payload = {"version": 1, "status": "fresh"}
            weather_store.save_json_atomic(path, payload)
            self.assertEqual(json.loads(path.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
