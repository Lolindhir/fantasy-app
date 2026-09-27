from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_v4_calibration import (  # noqa: E402
    FEATURE_OPPORTUNITY,
    FEATURE_SNAP,
    VARIANT_COMBINED,
    VARIANT_OPPORTUNITY,
    VARIANT_SNAP,
    build_v4_examples,
    build_v4_report,
)


class ProjectionV4CalibrationTests(unittest.TestCase):
    def test_usage_features_are_walk_forward_and_do_not_use_target_week(self) -> None:
        observations = {
            2023: {
                1: [
                    {
                        "Season": 2023,
                        "Week": 1,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 5.0,
                    },
                    {
                        "Season": 2023,
                        "Week": 1,
                        "CanonicalPlayerID": "B",
                        "PlayerName": "Beta",
                        "Position": "WR",
                        "FantasyPoints": 7.0,
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
                        "FantasyPoints": 10.0,
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
                        "FantasyPoints": 99.0,
                    }
                ],
                2: [
                    {
                        "Season": 2025,
                        "Week": 2,
                        "CanonicalPlayerID": "A",
                        "PlayerName": "Alpha",
                        "Position": "WR",
                        "FantasyPoints": 88.0,
                    }
                ],
            },
        }
        usage = {
            2023: {
                1: {
                    "A": {"Position": "WR", "SnapShare": 0.4, "Opportunity": 4.0},
                    "B": {"Position": "WR", "SnapShare": 0.5, "Opportunity": 5.0},
                }
            },
            2024: {
                1: {
                    "A": {"Position": "WR", "SnapShare": 0.5, "Opportunity": 6.0},
                    "B": {"Position": "WR", "SnapShare": 0.6, "Opportunity": 7.0},
                }
            },
            2025: {
                1: {
                    "A": {"Position": "WR", "SnapShare": 0.8, "Opportunity": 9.0},
                },
                2: {
                    # These values are intentionally extreme. They must not enter
                    # the Week-2 feature because target-week evidence is future data.
                    "A": {"Position": "WR", "SnapShare": 0.01, "Opportunity": 100.0},
                },
            },
        }

        examples = build_v4_examples(observations, usage, target_seasons=[2025])
        week_1 = next(row for row in examples if row["Week"] == 1)
        week_2 = next(row for row in examples if row["Week"] == 2)

        self.assertFalse(week_1[f"{FEATURE_SNAP}Available"])
        self.assertFalse(week_1[f"{FEATURE_OPPORTUNITY}Available"])

        # Completed-history baseline:
        # 2024 weight 1.0 plus 2023 weight 0.25.
        expected_snap_baseline = (0.5 + 0.4 * 0.25) / 1.25
        expected_opp_baseline = (6.0 + 4.0 * 0.25) / 1.25

        self.assertAlmostEqual(0.8 - expected_snap_baseline, week_2[FEATURE_SNAP])
        self.assertAlmostEqual(9.0 - expected_opp_baseline, week_2[FEATURE_OPPORTUNITY])
        self.assertEqual(0.8, week_2[f"{FEATURE_SNAP}Recent"])
        self.assertEqual(9.0, week_2[f"{FEATURE_OPPORTUNITY}Recent"])
        self.assertNotEqual(0.01, week_2[f"{FEATURE_SNAP}Recent"])
        self.assertNotEqual(100.0, week_2[f"{FEATURE_OPPORTUNITY}Recent"])

    def test_real_v4_variants_keep_2025_as_untouched_holdout(self) -> None:
        report = build_v4_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            calibration_seasons=[2023, 2024],
            holdout_season=2025,
            first_week=1,
            last_week=18,
        )

        compact = {
            "Calibrations": {
                variant: {
                    "Selected": value["Selected"],
                    "FinalFit": value["FinalFit"],
                }
                for variant, value in report["Calibrations"].items()
            },
            "Holdout": report["Holdout"],
        }
        print("V4_CALIBRATION_SUMMARY=" + json.dumps(compact, sort_keys=True))

        self.assertEqual(2023, report["DevelopmentSeason"])
        self.assertEqual(2024, report["ValidationSeason"])
        self.assertEqual(2025, report["HoldoutSeason"])
        self.assertEqual([2023, 2024], report["CalibrationSeasons"])

        baseline = report["Holdout"]["V3"]
        self.assertEqual(5724, baseline["PredictionCount"])
        self.assertEqual(
            {
                "Count": 5724,
                "MAE": 4.5461,
                "RMSE": 6.2445,
                "Bias": 0.0197,
                "MeanProjection": 8.0868,
                "MeanActual": 8.0671,
            },
            baseline["Metrics"],
        )

        expected = {
            VARIANT_SNAP: {
                "Ridge": 0.0,
                "Clip": 4.0,
                "Metrics": {
                    "Count": 5724,
                    "MAE": 4.5308,
                    "RMSE": 6.2342,
                    "Bias": 0.0222,
                    "MeanProjection": 8.0893,
                    "MeanActual": 8.0671,
                },
                "AdjustedCount": 4910,
                "MAEImprovementPoints": 0.0153,
                "RMSEImprovementPoints": 0.0103,
            },
            VARIANT_OPPORTUNITY: {
                "Ridge": 64.0,
                "Clip": 4.0,
                "Metrics": {
                    "Count": 5724,
                    "MAE": 4.537,
                    "RMSE": 6.2389,
                    "Bias": 0.0149,
                    "MeanProjection": 8.082,
                    "MeanActual": 8.0671,
                },
                "AdjustedCount": 5337,
                "MAEImprovementPoints": 0.0091,
                "RMSEImprovementPoints": 0.0056,
            },
            VARIANT_COMBINED: {
                "Ridge": 64.0,
                "Clip": 4.0,
                "Metrics": {
                    "Count": 5724,
                    "MAE": 4.5335,
                    "RMSE": 6.2294,
                    "Bias": 0.0299,
                    "MeanProjection": 8.0971,
                    "MeanActual": 8.0671,
                },
                "AdjustedCount": 5412,
                "MAEImprovementPoints": 0.0126,
                "RMSEImprovementPoints": 0.0151,
            },
        }

        for variant in (VARIANT_SNAP, VARIANT_OPPORTUNITY, VARIANT_COMBINED):
            calibration = report["Calibrations"][variant]
            holdout = report["Holdout"][variant]
            self.assertEqual(2023, calibration["DevelopmentSeason"])
            self.assertEqual(2024, calibration["ValidationSeason"])
            self.assertEqual([2023, 2024], calibration["CalibrationSeasons"])
            self.assertEqual(expected[variant]["Ridge"], calibration["Selected"]["Ridge"])
            self.assertEqual(expected[variant]["Clip"], calibration["Selected"]["Clip"])
            self.assertEqual(5724, holdout["PredictionCount"])
            self.assertEqual(expected[variant]["Metrics"], holdout["Metrics"])
            self.assertEqual(expected[variant]["AdjustedCount"], holdout["AdjustedCount"])
            self.assertEqual(
                expected[variant]["MAEImprovementPoints"],
                holdout["MAEImprovementPoints"],
            )
            self.assertEqual(
                expected[variant]["RMSEImprovementPoints"],
                holdout["RMSEImprovementPoints"],
            )

        # All three V4 variants improve the untouched holdout on both headline
        # error metrics. Snap trend wins MAE; the combined model wins RMSE.
        for variant in (VARIANT_SNAP, VARIANT_OPPORTUNITY, VARIANT_COMBINED):
            self.assertLess(
                report["Holdout"][variant]["Metrics"]["MAE"],
                baseline["Metrics"]["MAE"],
            )
            self.assertLess(
                report["Holdout"][variant]["Metrics"]["RMSE"],
                baseline["Metrics"]["RMSE"],
            )
        self.assertLess(
            report["Holdout"][VARIANT_SNAP]["Metrics"]["MAE"],
            report["Holdout"][VARIANT_COMBINED]["Metrics"]["MAE"],
        )
        self.assertLess(
            report["Holdout"][VARIANT_COMBINED]["Metrics"]["RMSE"],
            report["Holdout"][VARIANT_SNAP]["Metrics"]["RMSE"],
        )


if __name__ == "__main__":
    unittest.main()
