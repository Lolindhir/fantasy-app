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
        # Source-owned Cody PFR backfill extends replay observations (#1236).
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
        self.assertEqual(HISTORY_TWO_SEASON, baseline["HistoryVariant"])
        self.assertEqual(0.25, baseline["HistoryDecay"])
        self.assertEqual(0.0, baseline["HistoryK"])
        self.assertEqual(1241, report["PlayerBaselineCalibration"]["ColdStartObservationCount"])
        self.assertEqual(
            {
                "Count": 988,
                "MAE": 4.3707,
                "RMSE": 5.8534,
                "Bias": 1.3326,
                "MeanProjection": 7.5174,
                "MeanActual": 6.1848,
            },
            baseline["HistoryBackedColdStartMetrics"],
        )

        current = report["CurrentSeasonCalibration"]["Selected"]
        self.assertEqual(11298, report["CurrentSeasonCalibration"]["ComparableObservationCount"])
        self.assertEqual(1.0, current["CurrentK"])
        self.assertEqual(
            {
                "Count": 11298,
                "MAE": 4.5415,
                "RMSE": 6.199,
                "Bias": -0.1005,
                "MeanProjection": 8.1682,
                "MeanActual": 8.2687,
            },
            current["Metrics"],
        )

        comparable = report["Holdout"]["Comparable"]
        self.assertEqual(
            {
                "Count": 5731,
                "MAE": 4.5925,
                "RMSE": 6.3145,
                "Bias": -0.0618,
                "MeanProjection": 7.9913,
                "MeanActual": 8.0531,
            },
            comparable["V2"],
        )
        self.assertEqual(
            {
                "Count": 5731,
                "MAE": 4.5431,
                "RMSE": 6.2429,
                "Bias": 0.0197,
                "MeanProjection": 8.0727,
                "MeanActual": 8.0531,
            },
            comparable["V3"],
        )
        self.assertEqual(0.0494, comparable["MAEImprovementPoints"])
        self.assertEqual(1.0757, comparable["MAEImprovementPercent"])
        self.assertEqual(0.0716, comparable["RMSEImprovementPoints"])
        self.assertEqual(1.1339, comparable["RMSEImprovementPercent"])
        self.assertEqual(5.0662, comparable["V2Breakdowns"]["ByWeek"]["2"]["MAE"])
        self.assertEqual(4.7852, comparable["V3Breakdowns"]["ByWeek"]["2"]["MAE"])
        self.assertEqual(4.3334, comparable["V2Breakdowns"]["ByPriorGames"]["1"]["MAE"])
        self.assertEqual(4.086, comparable["V3Breakdowns"]["ByPriorGames"]["1"]["MAE"])

        cold = report["Holdout"]["ColdStart"]
        self.assertEqual(642, cold["V3All"]["Count"])
        self.assertEqual(509, cold["HistoryBackedCount"])
        self.assertEqual(133, cold["NoHistoryCount"])
        self.assertEqual(
            {
                "Count": 509,
                "MAE": 4.1107,
                "RMSE": 5.5436,
                "Bias": 1.1811,
                "MeanProjection": 7.2585,
                "MeanActual": 6.0774,
            },
            cold["V3HistoryBacked"],
        )
        self.assertEqual(1.81, cold["HistoryBackedMAEImprovementPoints"])
        self.assertEqual(
            {
                "Count": 133,
                "MAE": 6.1175,
                "RMSE": 6.9046,
                "Bias": 4.7943,
                "MeanProjection": 8.2106,
                "MeanActual": 3.4162,
            },
            cold["V3NoHistory"],
        )

        # V3 is promoted only because the untouched 2025 holdout beats V2.
        self.assertLess(comparable["V3"]["MAE"], comparable["V2"]["MAE"])
        self.assertLess(comparable["V3"]["RMSE"], comparable["V2"]["RMSE"])


if __name__ == "__main__":
    unittest.main()
