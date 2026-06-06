import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Level9CanonAlignmentDocsTests(unittest.TestCase):
    def test_roadmap_centers_always_on_household_governance_frame(self) -> None:
        text = (
            ROOT / "docs/JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md"
        ).read_text(encoding="utf-8")
        self.assertIn("It exists to answer five questions clearly:", text)
        self.assertIn("JARVIS is not a chat interface, dashboard, or smart-home wrapper.", text)
        self.assertIn("The deepest promise is:", text)
        self.assertIn("you're not carrying this alone", text)
        self.assertIn("Event truth beats opaque mutable state", text)
        self.assertIn("The promotion engine is a core civilization primitive.", text)

    def test_canonical_model_commits_to_household_operability_and_event_grounding(self) -> None:
        text = (ROOT / "docs/jarvis-canonical-operating-model.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("composed of around 60 specialized agents", text)
        self.assertIn("reduce the gap between a household's", text)
        self.assertIn("stated values and its lived daily reality", text)
        self.assertIn("durable event history,", text)
        self.assertIn("replayability, auditability, and explanation", text)
        self.assertIn("JARVIS must become operable by the household, not only by one builder", text)
        self.assertIn("Does this make JARVIS more household-operable instead of more builder-dependent?", text)

    def test_backend_blueprint_elevates_event_ground_truth_and_earned_authority(self) -> None:
        text = (ROOT / "docs/always-on-agent-backend-blueprint.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("This is the core product shape, not a future embellishment.", text)
        self.assertIn("event-grounded state derivation,", text)
        self.assertIn("replay, and explanation", text)
        self.assertIn("The event log should be treated as the system ground truth", text)
        self.assertIn("earned authority progression", text)
        self.assertIn("The promotion engine is the key mechanism that converts track record into", text)
        self.assertIn("authority. Sandbox execution, review, and supervision should all feed this", text)
        self.assertIn("household operation should become less builder-dependent over time", text)

    def test_maturity_model_adds_background_and_memory_compounding_signals(self) -> None:
        text = (ROOT / "docs/JARVIS-MATURITY-MODEL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("background agent work is becoming real, even if still narrow and uneven", text)
        self.assertIn("durable multi-agent background work with inspectable oversight", text)
        self.assertIn("foreground and background agent focus shift cleanly based on engagement", text)
        self.assertIn("long-running agents work from institutional memory, not just local session state", text)


if __name__ == "__main__":
    unittest.main()
