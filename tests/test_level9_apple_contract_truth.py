import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_TRACKER_ROOT = ROOT / "docs/archive/2026-06-life-operating-officer-reset"


def _read_tracker(name: str) -> str:
    candidates = [
        ROOT / "docs" / name,
        ARCHIVED_TRACKER_ROOT / name,
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise AssertionError(
        f"Could not find tracker {name} in current or archived repo-truth locations."
    )


class Level9AppleContractTruthTests(unittest.TestCase):
    def test_trackers_promote_full_duplex_phone_voice_loop_from_blocker_to_done_story(self) -> None:
        build = _read_tracker("jarvis_build_tracker.csv")
        master = _read_tracker("jarvis_master_tracker.csv")

        self.assertIn("story,S2.8,E2,Close full-duplex speech session loop on phone,done,100,P0,voice,S2.6", build)
        self.assertNotIn("blocker,BL-005,E2,Production speech-to-speech streaming and interruption are not implemented yet", build)
        self.assertIn("story,S2.14,E2,Close full-duplex speech session loop on phone,done,100,P0,voice,S2.7|S2.11", master)
        self.assertNotIn("blocker,BL-005,E2,Production speech-to-speech streaming and interruption are not implemented yet", master)

    def test_apple_contract_verifier_covers_voice_while_away_and_admin_surfaces(self) -> None:
        text = (ROOT / "scripts/verify_apple_contracts.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("/api/apple/voice/greeting?actor=chris", text)
        self.assertIn("/api/apple/voice/state?actor=chris&conversation_id=", text)
        self.assertIn("/api/apple/while-you-were-away?actor=chris", text)
        self.assertIn("/api/apple/systems/admin-summary", text)
        self.assertIn("/api/apple/navigation/stops?", text)
        self.assertIn("verify_while_you_were_away", text)
        self.assertIn("ACTION_ENDPOINTS", text)


if __name__ == "__main__":
    unittest.main()
