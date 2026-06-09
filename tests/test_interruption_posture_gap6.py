"""
GAP-6: suppress and escalate postures in _compute_interruption_posture,
and delivery decision recording via _record_interruption_decision.

Tests verify:
- suppress posture fires when watch_status has suppress_interruptions=True
- escalate posture fires when alert_count >= 3 (multi-alert)
- escalate posture fires when watch_status has escalate_interruptions=True
- suppress routes non-critical to "suppress" delivery mode
- suppress lets critical items break through to "deliver_now"
- escalate routes everything to "deliver_now"
- _record_interruption_decision writes a valid JSONL record
- existing postures (household_alert, focus_active, quiet_hours) are unaffected
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


import jarvis.apple_api as apple_api


def _posture(watch_status=None, home_state=None, focus_payload=None):
    return apple_api._compute_interruption_posture(
        watch_status=watch_status or {},
        home_state=home_state or {},
        focus_payload=focus_payload or {},
    )


def _choose(*, default_mode, severity, category, posture):
    return apple_api._choose_delivery_mode(
        default_mode=default_mode,
        severity=severity,
        category=category,
        posture=posture,
    )


class TestSuppressPosture(unittest.TestCase):

    def test_suppress_mode_when_flag_set(self):
        p = _posture(watch_status={"suppress_interruptions": True})
        self.assertEqual(p["mode"], "suppress")
        self.assertTrue(p["suppress_active"])

    def test_suppress_routes_low_severity_to_suppress(self):
        p = _posture(watch_status={"suppress_interruptions": True})
        mode, _ = _choose(default_mode="badge_only", severity="low", category="system", posture=p)
        self.assertEqual(mode, "suppress")

    def test_suppress_routes_medium_severity_to_suppress(self):
        p = _posture(watch_status={"suppress_interruptions": True})
        mode, _ = _choose(default_mode="badge_only", severity="medium", category="household", posture=p)
        self.assertEqual(mode, "suppress")

    def test_suppress_lets_critical_break_through(self):
        p = _posture(watch_status={"suppress_interruptions": True})
        mode, reason = _choose(default_mode="badge_only", severity="critical", category="household", posture=p)
        self.assertEqual(mode, "deliver_now")
        self.assertIn("suppression", reason)

    def test_no_suppress_when_flag_absent(self):
        p = _posture()
        self.assertNotEqual(p["mode"], "suppress")
        self.assertFalse(p["suppress_active"])


class TestEscalatePosture(unittest.TestCase):

    def test_escalate_mode_when_flag_set(self):
        p = _posture(watch_status={"escalate_interruptions": True})
        self.assertEqual(p["mode"], "escalate")
        self.assertTrue(p["escalate_active"])

    def test_escalate_mode_when_three_or_more_alerts(self):
        p = _posture(home_state={"alerts": ["a", "b", "c"]})
        self.assertEqual(p["mode"], "escalate")
        self.assertTrue(p["escalate_active"])

    def test_escalate_routes_everything_to_deliver_now(self):
        p = _posture(watch_status={"escalate_interruptions": True})
        for sev in ("low", "medium", "high", "critical"):
            mode, _ = _choose(default_mode="badge_only", severity=sev, category="system", posture=p)
            self.assertEqual(mode, "deliver_now", f"escalate should deliver_now for severity={sev}")

    def test_no_escalate_with_two_alerts(self):
        p = _posture(home_state={"alerts": ["a", "b"]})
        # two alerts → household_alert, not escalate
        self.assertEqual(p["mode"], "household_alert")
        self.assertFalse(p["escalate_active"])

    def test_escalate_takes_priority_over_suppress(self):
        # If both flags are set, escalate wins (it is checked first)
        p = _posture(watch_status={"suppress_interruptions": True, "escalate_interruptions": True})
        self.assertEqual(p["mode"], "escalate")


class TestExistingPosturesUnaffected(unittest.TestCase):

    def test_household_alert_mode(self):
        p = _posture(home_state={"alerts": ["leak detected"]})
        self.assertEqual(p["mode"], "household_alert")

    def test_focus_active_mode(self):
        p = _posture(focus_payload={"focus_active": True})
        self.assertEqual(p["mode"], "focus_active")

    def test_active_hours_mode(self):
        # No overrides, no quiet hours signal — mode should be active_hours
        with patch.object(apple_api, "_local_hour", return_value=10):
            p = _posture()
        self.assertEqual(p["mode"], "active_hours")


class TestRecordInterruptionDecision(unittest.TestCase):

    def test_record_writes_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "interruption_decisions.jsonl"
            with patch.object(apple_api, "_INTERRUPTION_DECISIONS_PATH", log_path):
                apple_api._record_interruption_decision(
                    item_id="needs:pending",
                    category="approval",
                    severity="high",
                    posture_mode="active_hours",
                    decision="badge_only",
                    decision_reason="Normal household hours.",
                )
            self.assertTrue(log_path.exists())
            lines = [l for l in log_path.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["item_id"], "needs:pending")
            self.assertEqual(record["category"], "approval")
            self.assertEqual(record["decision"], "badge_only")
            self.assertIn("ts", record)

    def test_record_does_not_raise_on_io_error(self):
        with patch.object(apple_api, "_INTERRUPTION_DECISIONS_PATH", Path("/nonexistent/path/decisions.jsonl")):
            # Should not raise — failure is logged at DEBUG level
            apple_api._record_interruption_decision(
                item_id="test",
                category="system",
                severity="low",
                posture_mode="active_hours",
                decision="badge_only",
                decision_reason="test",
            )

    def test_record_accumulates_multiple_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "interruption_decisions.jsonl"
            with patch.object(apple_api, "_INTERRUPTION_DECISIONS_PATH", log_path):
                for i in range(3):
                    apple_api._record_interruption_decision(
                        item_id=f"item:{i}",
                        category="system",
                        severity="low",
                        posture_mode="active_hours",
                        decision="badge_only",
                        decision_reason="test",
                    )
            lines = [l for l in log_path.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 3)
            ids = [json.loads(l)["item_id"] for l in lines]
            self.assertEqual(ids, ["item:0", "item:1", "item:2"])


if __name__ == "__main__":
    unittest.main()
