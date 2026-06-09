from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jarvis import data_connectors


def _make_config(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        google_token_path=root / "google_token.json",
        home_assistant_url="",
        home_assistant_token="",
    )


class ConnectorTruthfulnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.config = _make_config(self.root)
        for key in (
            "weather_current",
            "weather_forecast_24",
            "ha_house_state",
            "news_headlines_3",
        ):
            data_connectors._cache.invalidate(key)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_google_calendar_unavailable_never_returns_mock_events(self) -> None:
        connector = data_connectors.GoogleCalendarConnector(self.config)
        today = connector.get_today_events(actor_id="truth-test-today")
        upcoming = connector.get_upcoming_events(actor_id="truth-test-upcoming")

        for payload in (today, upcoming):
            self.assertFalse(payload["available"])
            self.assertEqual(payload["source"], "unavailable")
            self.assertEqual(payload["events"], [])
            self.assertEqual(payload["count"], 0)
            self.assertIn("unavailable", payload["error"].lower())

    def test_gmail_unavailable_never_returns_mock_messages(self) -> None:
        connector = data_connectors.GmailConnector(self.config)
        payload = connector.get_inbox_summary(actor_id="truth-test-gmail")

        self.assertFalse(payload["available"])
        self.assertEqual(payload["source"], "unavailable")
        self.assertEqual(payload["unread_count"], 0)
        self.assertEqual(payload["flagged_count"], 0)
        self.assertEqual(payload["action_items"], [])
        self.assertEqual(payload["newsletters"], 0)
        self.assertIn("unavailable", payload["error"].lower())

    def test_home_assistant_unavailable_never_returns_mock_house_state(self) -> None:
        connector = data_connectors.HomeAssistantConnector(self.config)
        payload = connector.get_house_state()
        sensor = connector.get_sensor("light.kitchen")

        self.assertFalse(payload["available"])
        self.assertEqual(payload["source"], "unavailable")
        self.assertEqual(payload["present_members"], [])
        self.assertEqual(payload["lights_on"], [])
        self.assertEqual(payload["alerts"], [])
        self.assertIn("not configured", payload["error"].lower())

        self.assertFalse(sensor["available"])
        self.assertEqual(sensor["source"], "unavailable")
        self.assertEqual(sensor["state"], "unknown")
        self.assertEqual(sensor["attributes"], {})

    @patch.object(data_connectors.WeatherConnector, "_is_configured", return_value=False)
    def test_weather_unavailable_never_returns_mock_conditions(self, _mock_configured) -> None:
        connector = data_connectors.WeatherConnector(self.config)
        current = connector.get_current()
        forecast = connector.get_forecast()

        self.assertFalse(current["available"])
        self.assertEqual(current["source"], "unavailable")
        self.assertEqual(current["condition"], "Unavailable")
        self.assertEqual(current["alerts"], [])
        self.assertIn("not configured", current["error"].lower())

        self.assertFalse(forecast["available"])
        self.assertEqual(forecast["source"], "unavailable")
        self.assertEqual(forecast["hourly"], [])
        self.assertEqual(forecast["daily_high_f"], 0.0)
        self.assertEqual(forecast["daily_low_f"], 0.0)

    @patch("jarvis.data_connectors._safe_http_get", return_value=None)
    def test_news_unavailable_never_returns_mock_headlines(self, _mock_http_get) -> None:
        connector = data_connectors.NewsConnector(self.config)
        payload = connector.get_headlines()

        self.assertFalse(payload["available"])
        self.assertEqual(payload["source"], "unavailable")
        self.assertEqual(payload["headlines"], [])
        self.assertEqual(payload["total"], 0)
        self.assertIn("could not be loaded", payload["error"].lower())


if __name__ == "__main__":
    unittest.main()
