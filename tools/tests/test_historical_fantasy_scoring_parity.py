from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_fantasy_scoring_parity import build_parity_report  # noqa: E402


class HistoricalFantasyScoringParityTests(unittest.TestCase):
    def test_2025_weeks_1_to_17_match_league_points_except_documented_provider_divergence(self) -> None:
        report = build_parity_report(
            ROOT,
            league_id="nfl-reise",
            nfl_season=2025,
            scoring_season=2025,
            first_week=1,
            last_week=17,
        )

        self.assertEqual(2547, report["ComparedPlayerWeeks"])
        self.assertEqual([], report["MissingNonZeroCanonicalStats"])
        self.assertEqual([], report["UnsupportedPlayerWeeks"])
        self.assertEqual(2546, report["ExactPlayerWeeks"])
        self.assertEqual(
            [
                {
                    "CanonicalPlayerID": "NFLP-3c5ddc5072f6fe8f9b77",
                    "PlayerName": "Caleb Williams",
                    "Position": "QB",
                    "Week": 6,
                    "DerivedPoints": 20.38,
                    "LeaguePoints": 19.88,
                    "Difference": 0.5,
                }
            ],
            report["Mismatches"],
        )


if __name__ == "__main__":
    unittest.main()
