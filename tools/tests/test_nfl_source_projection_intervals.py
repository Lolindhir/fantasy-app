from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_interval_calibration import (  # noqa: E402
    INTERVAL_LEVELS,
    STRATEGIES,
    STRATEGY_POSITION_PROJECTION_VOLATILITY,
    build_interval_report,
    build_prior_score_volatility,
)


class ProjectionIntervalCalibrationTests(unittest.TestCase):
    def test_prior_score_volatility_is_pregame_and_excludes_target_week(self) -> None:
        observations = {
            2023: {
                1: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 1.0,
                    },
                    {
                        "CanonicalPlayerID": "B",
                        "FantasyPoints": 5.0,
                    },
                ],
                2: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 3.0,
                    }
                ],
            },
            2024: {
                1: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 5.0,
                    }
                ],
                2: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 7.0,
                    }
                ],
            },
            2025: {
                1: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 100.0,
                    }
                ],
                2: [
                    {
                        "CanonicalPlayerID": "A",
                        "FantasyPoints": 10.0,
                    }
                ],
            },
        }

        result = build_prior_score_volatility(
            observations,
            target_seasons=[2025],
        )

        historical = [1.0, 3.0, 5.0, 7.0]
        mean = sum(historical) / len(historical)
        expected_week_1 = math.sqrt(
            sum((value - mean) ** 2 for value in historical) / len(historical)
        )
        self.assertAlmostEqual(expected_week_1, result[(2025, 1, "A")])

        # Week 2 may use Week 1's completed 100-point outcome.
        with_week_1 = historical + [100.0]
        mean_2 = sum(with_week_1) / len(with_week_1)
        expected_week_2 = math.sqrt(
            sum((value - mean_2) ** 2 for value in with_week_1) / len(with_week_1)
        )
        self.assertAlmostEqual(expected_week_2, result[(2025, 2, "A")])
        self.assertNotEqual(result[(2025, 1, "A")], result[(2025, 2, "A")])

    def test_real_interval_calibration_and_2025_holdout_are_reproducible(self) -> None:
        report = build_interval_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            first_week=1,
            last_week=18,
        )

        compact = {
            "PointModel": report["PointModel"],
            "IntervalCalibration": report["IntervalCalibration"],
            "Holdout": report["Holdout"],
            "Strategies": report["Strategies"],
        }
        print("V4_INTERVAL_SUMMARY=" + json.dumps(compact, sort_keys=True))

        self.assertEqual(2024, report["IntervalCalibration"]["Season"])
        self.assertEqual(5637, report["IntervalCalibration"]["Rows"])
        self.assertEqual(2025, report["Holdout"]["Season"])
        self.assertEqual(5724, report["Holdout"]["Rows"])
        self.assertEqual(64.0, report["PointModel"]["Ridge"])
        self.assertEqual(4.0, report["PointModel"]["Clip"])

        for strategy in STRATEGIES:
            result = report["Strategies"][strategy]
            for level in INTERVAL_LEVELS:
                metrics = result["Levels"][str(int(level * 100))]
                self.assertEqual(5724, metrics["Count"])
                self.assertGreater(metrics["MeanWidth"], 0.0)
                self.assertGreaterEqual(metrics["CoveragePercent"], 0.0)
                self.assertLessEqual(metrics["CoveragePercent"], 100.0)
                self.assertEqual(
                    5724,
                    metrics["CoveredCount"]
                    + metrics["LowerMissCount"]
                    + metrics["UpperMissCount"],
                )

            self.assertTrue(result["Coverage90ByPosition"])

        volatility = report["Strategies"][
            STRATEGY_POSITION_PROJECTION_VOLATILITY
        ]["Width90ByVolatilityClass"]
        self.assertIn("low", volatility)
        self.assertIn("high", volatility)
        self.assertGreater(volatility["low"]["Count"], 0)
        self.assertGreater(volatility["high"]["Count"], 0)


if __name__ == "__main__":
    unittest.main()
