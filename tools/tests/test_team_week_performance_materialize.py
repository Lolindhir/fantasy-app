"""Focused parity and safe-publication guard tests for TeamWeekPerformance #355."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from team_week_performance_materialize import verify_pwf_actual_parity  # noqa: E402
from data_roots import DATA_DERIVED_ROOT  # noqa: E402


class MaterializerParityTests(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.model = {
            "CanonicalLeagueID": "nfl-reise",
            "Season": 2026,
            "Week": 5,
            "ScoringProfile": {"SettingsHash": "sha256:abc"},
        }
        self.matchups = [{"PlayerPoints": [
            {"Player": {"CanonicalPlayerID": "a"}, "Points": 9.5},
            {"Player": {"CanonicalPlayerID": "b"}, "Points": 0},
            {"Player": {"CanonicalPlayerID": "c"}, "Points": -2.25},
        ]}]
        self.path = (self.root / DATA_DERIVED_ROOT / "player-week-fantasy"
                     / "nfl-reise/2026/05.json")
        self.path.parent.mkdir(parents=True)

    def write_pwf(self, records: list[dict], *, fingerprint: str = "sha256:abc") -> None:
        self.path.write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Season": 2026, "Week": 5,
            "ScoringProfile": {"SettingsHash": fingerprint},
            "Records": records,
        }), encoding="utf-8")

    @staticmethod
    def actual(player_id: str, score: float, state: str = "final") -> dict:
        return {"CanonicalPlayerID": player_id,
                "Actual": {"State": state, "Points": score}}

    def test_missing_pwf_can_be_optional_or_explicitly_required(self) -> None:
        self.assertEqual(
            verify_pwf_actual_parity(self.root, self.model, self.matchups)["State"],
            "not-available",
        )
        with self.assertRaisesRegex(ValueError, "Required PlayerWeekFantasy"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups, require_pwf=True)

    def test_valid_snapshot_keeps_zero_missing_and_negative_scores(self) -> None:
        self.write_pwf([self.actual("a", 9.5), self.actual("c", -2.25)])
        self.assertEqual(
            verify_pwf_actual_parity(self.root, self.model, self.matchups, require_pwf=True),
            {"State": "verified", "Compared": 2, "MissingZeroPoints": 1},
        )

    def test_missing_nonzero_cannot_be_called_zero(self) -> None:
        self.write_pwf([self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "missing nonzero scorer a"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_stale_final_zero_and_nonfinal_actual_fail(self) -> None:
        self.write_pwf([self.actual("a", 0), self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "scoring mismatch"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)
        self.write_pwf([self.actual("a", 9.5, state="pending"),
                        self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "not final"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_stale_fingerprint_and_duplicate_identity_fail(self) -> None:
        self.write_pwf([self.actual("a", 9.5)], fingerprint="sha256:other")
        with self.assertRaisesRegex(ValueError, "scoring fingerprint mismatch"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)
        self.write_pwf([self.actual("a", 9.5), self.actual("a", 9.5)])
        with self.assertRaisesRegex(ValueError, "duplicate PlayerWeekFantasy"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_duplicate_canonical_player_points_rejected(self) -> None:
        self.write_pwf([self.actual("a", 9.5), self.actual("c", -2.25)])
        self.matchups[0]["PlayerPoints"].append(
            {"Player": {"CanonicalPlayerID": "a"}, "Points": 9.5}
        )
        with self.assertRaisesRegex(ValueError, "duplicate canonical matchup"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)


if __name__ == "__main__":
    unittest.main()
