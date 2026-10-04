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

        # The projection-aware strategy is the sharpest well-calibrated 90%
        # interval, while the volatility-conditioned strategy trades a small
        # amount of width for player-specific floor/ceiling differentiation.
        projection_aware = report["Strategies"]["position-projection"]["Levels"]
        self.assertEqual(51.7296, projection_aware["50"]["CoveragePercent"])
        self.assertEqual(79.8043, projection_aware["80"]["CoveragePercent"])
        self.assertEqual(90.3739, projection_aware["90"]["CoveragePercent"])
        self.assertEqual(95.1258, projection_aware["95"]["CoveragePercent"])
        self.assertEqual(19.2163, projection_aware["90"]["MeanWidth"])

        volatility_strategy = report["Strategies"][
            STRATEGY_POSITION_PROJECTION_VOLATILITY
        ]
        expected_volatility_levels = {
            "50": (51.6247, 7.4161),
            "80": (80.2236, 14.7934),
            "90": (90.601, 19.6548),
            "95": (95.283, 24.0524),
        }
        for level, (coverage, width) in expected_volatility_levels.items():
            self.assertEqual(
                coverage,
                volatility_strategy["Levels"][level]["CoveragePercent"],
            )
            self.assertEqual(
                width,
                volatility_strategy["Levels"][level]["MeanWidth"],
            )

        self.assertEqual(
            7.6222,
            volatility_strategy["Levels"]["90"]["MeanLowerDistance"],
        )
        self.assertEqual(
            12.0325,
            volatility_strategy["Levels"]["90"]["MeanUpperDistance"],
        )

        volatility = volatility_strategy["Width90ByVolatilityClass"]
        self.assertEqual(2652, volatility["high"]["Count"])
        self.assertEqual(2719, volatility["low"]["Count"])
        self.assertEqual(90.8371, volatility["high"]["CoveragePercent"])
        self.assertEqual(90.879, volatility["low"]["CoveragePercent"])
        self.assertEqual(21.064, volatility["high"]["MeanWidth"])
        self.assertEqual(18.6309, volatility["low"]["MeanWidth"])
        self.assertGreater(
            volatility["high"]["MeanWidth"],
            volatility["low"]["MeanWidth"],
        )

        # Players without enough historical games for an individual volatility
        # estimate fall back to broader groups; this early-history subset remains
        # a known weaker calibration pocket and is kept visible rather than hidden.
        self.assertEqual(353, volatility["unavailable"]["Count"])
        self.assertEqual(86.6856, volatility["unavailable"]["CoveragePercent"])


if __name__ == "__main__":
    unittest.main()
