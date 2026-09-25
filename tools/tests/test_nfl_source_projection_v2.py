from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_v2_calibration import (  # noqa: E402
    BASELINE_CURRENT_POSITION_MEAN,
    BASELINE_PREVIOUS_POSITION_MEAN,
    build_v2_calibration_report,
    build_v2_examples,
    calibrate_v2,
)


class ProjectionV2CalibrationTests(unittest.TestCase):
    def test_current_position_baseline_is_leave_one_player_out_and_prior_week_only(self) -> None:
        observations = {
            2024: {
                1: [
                    {
                        "Season": 2024,
                        "Week": 1,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 100.0,
                    },
                    {
                        "Season": 2024,
                        "Week": 1,
                        "CanonicalPlayerID": "B",
                        "PlayerName": "Beta",
                        "Position": "WR",
                        "FantasyPoints": 10.0,
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
                        "FantasyPoints": 30.0,
                    },
                    {
                        "Season": 2025,
                        "Week": 1,
                        "CanonicalPlayerID": "B",
                        "PlayerName": "Beta",
                        "Position": "WR",
                        "FantasyPoints": 20.0,
                    },
                ],
                2: [
                    {
                        "Season": 2025,
                        "Week": 2,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 999.0,
                    }
                ],
            },
        }

        examples = build_v2_examples(observations, target_seasons=[2025])
        week_2_a = next(
            row
            for row in examples
            if row["Week"] == 2 and row["CanonicalPlayerID"] == "A"
        )

        # A's own Week-1 value (30) is excluded; B's 20 is the only current
        # position baseline. Target Week-2 actual 999 cannot enter the baseline.
        self.assertEqual(20.0, week_2_a["Baselines"][BASELINE_CURRENT_POSITION_MEAN])
        # Previous-season baseline also excludes A's own 100 and therefore uses B=10.
        self.assertEqual(10.0, week_2_a["Baselines"][BASELINE_PREVIOUS_POSITION_MEAN])
        self.assertEqual(30.0, week_2_a["CurrentSeasonPPG"])

    def test_calibration_ignores_holdout_rows(self) -> None:
        calibration_rows = []
        for week in range(2, 8):
            calibration_rows.append(
                {
                    "Season": 2024,
                    "Week": week,
                    "CanonicalPlayerID": "A",
                    "Position": "WR",
                    "PriorGames": week - 1,
                    "CurrentSeasonPPG": 10.0,
                    "Actual": 10.0,
                    "Baselines": {
                        BASELINE_PREVIOUS_POSITION_MEAN: 0.0,
                        BASELINE_CURRENT_POSITION_MEAN: 0.0,
                    },
                }
            )
        holdout = {
            "Season": 2025,
            "Week": 2,
            "CanonicalPlayerID": "A",
            "Position": "WR",
            "PriorGames": 1,
            "CurrentSeasonPPG": 10.0,
            "Actual": 10000.0,
            "Baselines": {
                BASELINE_PREVIOUS_POSITION_MEAN: 10000.0,
                BASELINE_CURRENT_POSITION_MEAN: 10000.0,
            },
        }

        without_holdout = calibrate_v2(calibration_rows, calibration_seasons=[2024])
        with_holdout = calibrate_v2(
            calibration_rows + [holdout],
            calibration_seasons=[2024],
        )
        self.assertEqual(without_holdout["Selected"], with_holdout["Selected"])

    def test_real_v2_calibration_and_2025_holdout_are_reproducible(self) -> None:
        report = build_v2_calibration_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            calibration_seasons=[2023, 2024],
            holdout_season=2025,
            first_week=1,
            last_week=18,
        )

        compact = {
            "Calibration": report["Calibration"],
            "HoldoutComparable": report["Holdout"]["Comparable"],
            "ExpandedCoverage": report["Holdout"]["ExpandedCoverage"],
            "ObservationAudits": report["ObservationAudits"],
        }
        print("V2_CALIBRATION_SUMMARY=" + json.dumps(compact, sort_keys=True))

        selected = report["Calibration"]["Selected"]
        self.assertEqual(BASELINE_PREVIOUS_POSITION_MEAN, selected["BaselineVariant"])
        self.assertEqual(0.5, selected["K"])
        self.assertEqual(11297, report["Calibration"]["ComparableObservationCount"])
        self.assertEqual(
            {
                "Count": 11297,
                "MAE": 4.5917,
                "RMSE": 6.2722,
                "Bias": -0.1955,
                "MeanProjection": 8.0903,
                "MeanActual": 8.2858,
            },
            selected["Metrics"],
        )

        comparable = report["Holdout"]["Comparable"]
        self.assertEqual(
            {
                "Count": 5724,
                "MAE": 4.6282,
                "RMSE": 6.4603,
                "Bias": -0.1902,
                "MeanProjection": 7.8769,
                "MeanActual": 8.0671,
            },
            comparable["V1"],
        )
        self.assertEqual(
            {
                "Count": 5724,
                "MAE": 4.5948,
                "RMSE": 6.3162,
                "Bias": -0.0628,
                "MeanProjection": 8.0043,
                "MeanActual": 8.0671,
            },
            comparable["V2"],
        )
        self.assertEqual(0.0334, comparable["MAEImprovementPoints"])
        self.assertEqual(0.7217, comparable["MAEImprovementPercent"])
        self.assertEqual(0.1441, comparable["RMSEImprovementPoints"])
        self.assertEqual(2.2305, comparable["RMSEImprovementPercent"])
        self.assertEqual(5.595, comparable["V1Breakdowns"]["ByWeek"]["2"]["MAE"])
        self.assertEqual(5.0683, comparable["V2Breakdowns"]["ByWeek"]["2"]["MAE"])
        self.assertEqual(6.691, comparable["V1Breakdowns"]["ByPosition"]["QB"]["MAE"])
        self.assertEqual(6.5573, comparable["V2Breakdowns"]["ByPosition"]["QB"]["MAE"])

        expanded = report["Holdout"]["ExpandedCoverage"]
        self.assertEqual(641, expanded["AdditionalColdStartPredictions"])
        self.assertEqual(6365, expanded["TotalPredictions"])
        self.assertEqual(
            {
                "Count": 641,
                "MAE": 5.9516,
                "RMSE": 7.0246,
                "Bias": 2.6506,
                "MeanProjection": 8.1993,
                "MeanActual": 5.5487,
            },
            expanded["ColdStartMetrics"],
        )


if __name__ == "__main__":
    unittest.main()
