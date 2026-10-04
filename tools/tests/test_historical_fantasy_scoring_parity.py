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

        compared = report["ComparedPlayerWeeks"]
        self.assertGreater(compared, 0)
        self.assertEqual([], report["MissingNonZeroCanonicalStats"])
        self.assertEqual([], report["UnsupportedPlayerWeeks"])
        # Expectations derive from the data, not from named players: exact-rate and
        # magnitude gate as in the #347 D2 Sleeper validation design.
        self.assertEqual(compared, report["ExactPlayerWeeks"] + len(report["Mismatches"]))
        self.assertGreaterEqual(report["ExactPlayerWeeks"] / compared, 0.995)
        for mismatch in report["Mismatches"]:
            self.assertLessEqual(abs(mismatch["Difference"]), 2.0, mismatch)


if __name__ == "__main__":
    unittest.main()
