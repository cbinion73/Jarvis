from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from jarvis.models import SecurityIncident, WeatherAdvisory
from jarvis.security import SecurityStore


class SecurityStoreTests(unittest.TestCase):
    def test_replays_incidents_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SecurityStore(root)
            incident = SecurityIncident(
                incident_id="incident-1",
                category="package",
                severity="watch",
                source="front-door",
                headline="Package activity noted at front door",
                detail="Package detected.",
                recommended_action="Check the delivery zone.",
                needs_ack=False,
                timestamp="2026-06-02T00:00:00+00:00",
            )

            store.add_incident(incident)
            store.incidents_path.write_text("", encoding="utf-8")

            self.assertEqual(store.list_incidents(), [asdict(incident)])

    def test_replays_weather_from_append_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SecurityStore(root)
            advisory = WeatherAdvisory(
                advisory_id="weather-1",
                actor="Chris",
                context="School pickup",
                current_weather="Thunderstorm watch",
                risk_level="watch",
                safe_timing="Wait 20 minutes",
                recommendation="Delay departure.",
                follow_ups=["Recheck radar"],
                timestamp="2026-06-02T00:00:00+00:00",
            )

            store.add_weather(advisory)
            store.weather_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.list_weather(), [asdict(advisory)])


if __name__ == "__main__":
    unittest.main()
