from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_v3_calibration import (  # noqa: E402
    HISTORY_PREVIOUS_ONLY,
    HISTORY_TWO_SEASON,
    _baseline_for,
    build_v3_calibration_report,
    build_v3_examples,
)


class ProjectionV3CalibrationTests(unittest.TestCase):
    def test_player_history_uses_completed_seasons_only_and_position_prior_is_leave_one_out(self) -> None:
        observations = {
            2023: {
                1: [
                    {
                        "Season": 2023,
                        "Week": 1,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 4.0,
                    },
                    {
                        "Season": 2023,
                        "Week": 1,
                        "CanonicalPlayerID": "B",
                        "PlayerName": "Beta",
                        "Position": "WR",
                        "FantasyPoints": 10.0,
                    },
                ]
            },
            2024: {
                1: [
                    {
                        "Season": 2024,
                        "Week": 1,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 20.0,
                    },
                    {
                        "Season": 2024,
                        "Week": 1,
                        "CanonicalPlayerID": "B",
                        "PlayerName": "Beta",
                        "Position": "WR",
                        "FantasyPoints": 8.0,
                    },
                ]
            },
            2025: {
                1: [
                    {
                        "Season": 2025,
                        "Week": 1,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 999.0,
                    }
                ],
                2: [
                    {
                        "Season": 2025,
                        "Week": 2,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 777.0,
                    }
                ],
            },
        }

        examples = build_v3_examples(observations, target_seasons=[2025])
        week_1 = next(row for row in examples if row["Week"] == 1)
        week_2 = next(row for row in examples if row["Week"] == 2)

        # Previous-season position prior excludes A's own 20 and therefore uses B=8.
        self.assertEqual(8.0, week_1["PositionPrior"])
        # Previous-season player history is A=20. The target season's 999/777
        # can never enter the completed-history baseline.
        previous = week_1["HistoryCandidates"][HISTORY_PREVIOUS_ONLY]
        self.assertEqual(20.0, previous["HistoryPPG"])
        self.assertEqual(1.0, previous["EffectiveHistoryGames"])

        two_season = week_1["HistoryCandidates"][f"{HISTORY_TWO_SEASON}:0.5"]
        self.assertAlmostEqual((20.0 + 4.0 * 0.5) / 1.5, two_season["HistoryPPG"])
        self.assertEqual(1.5, two_season["EffectiveHistoryGames"])

        # Current-season state appears only from prior weeks.
        self.assertIsNone(week_1["CurrentSeasonPPG"])
        self.assertEqual(999.0, week_2["CurrentSeasonPPG"])

        baseline, history_backed = _baseline_for(
            week_1,
            variant=HISTORY_PREVIOUS_ONLY,
            decay=0.0,
            history_k=1.0,
        )
        self.assertTrue(history_backed)
        self.assertEqual(14.0, baseline)

    def test_real_v3_calibration_and_2025_holdout_are_reproducible(self) -> None:
        report = build_v3_calibration_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            calibration_seasons=[2023, 2024],
            holdout_season=2025,
            first_week=1,
            last_week=18,
        )

        compact = {
            "PlayerBaselineCalibration": report["PlayerBaselineCalibration"],
            "CurrentSeasonCalibration": report["CurrentSeasonCalibration"],
            "Holdout": report["Holdout"],
            "ObservationAudits": report["ObservationAudits"],
        }
        print("V3_CALIBRATION_SUMMARY=" + json.dumps(compact, sort_keys=True))

        baseline = report["PlayerBaselineCalibration"]["Selected"]
        self.assertIn(
            baseline["HistoryVariant"],
            [HISTORY_PREVIOUS_ONLY, HISTORY_TWO_SEASON],
        )
        self.assertGreater(
            baseline["HistoryBackedColdStartMetrics"]["Count"],
            500,
        )

        current = report["CurrentSeasonCalibration"]["Selected"]
        self.assertGreater(
            report["CurrentSeasonCalibration"]["ComparableObservationCount"],
            10000,
        )
        self.assertGreaterEqual(current["CurrentK"], 0.0)

        comparable = report["Holdout"]["Comparable"]
        self.assertEqual(5724, comparable["V2"]["Count"])
        self.assertEqual(5724, comparable["V3"]["Count"])

        cold = report["Holdout"]["ColdStart"]
        self.assertEqual(641, cold["V3All"]["Count"])
        self.assertEqual(
            641,
            cold["HistoryBackedCount"] + cold["NoHistoryCount"],
        )


if __name__ == "__main__":
    unittest.main()
