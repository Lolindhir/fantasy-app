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

from ci_tier import deep_only  # noqa: E402
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

    @deep_only("full real-source interval calibration (~55 s)")
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

        # Row counts follow the persisted real source and grow when identity or
        # source fixes add player-weeks, so they are checked as invariants and
        # not pinned to a data snapshot.
        self.assertEqual(2024, report["IntervalCalibration"]["Season"])
        calibration_rows = report["IntervalCalibration"]["Rows"]
        holdout_rows = report["Holdout"]["Rows"]
        self.assertGreater(calibration_rows, 1000)
        self.assertGreater(holdout_rows, 1000)
        self.assertEqual(2025, report["Holdout"]["Season"])
        self.assertEqual(64.0, report["PointModel"]["Ridge"])
        self.assertEqual(4.0, report["PointModel"]["Clip"])

        for strategy in STRATEGIES:
            result = report["Strategies"][strategy]
            for level in INTERVAL_LEVELS:
                metrics = result["Levels"][str(int(level * 100))]
                self.assertEqual(holdout_rows, metrics["Count"])
                self.assertGreater(metrics["MeanWidth"], 0.0)
                self.assertGreaterEqual(metrics["CoveragePercent"], 0.0)
                self.assertLessEqual(metrics["CoveragePercent"], 100.0)
                self.assertEqual(
                    holdout_rows,
                    metrics["CoveredCount"]
                    + metrics["LowerMissCount"]
                    + metrics["UpperMissCount"],
                )

            self.assertTrue(result["Coverage90ByPosition"])

        # The projection-aware strategy is the sharpest well-calibrated 90%
        # interval, while the volatility-conditioned strategy trades a small
        # amount of width for player-specific floor/ceiling differentiation.
        projection_aware = report["Strategies"]["position-projection"]["Levels"]
        volatility_strategy = report["Strategies"][
            STRATEGY_POSITION_PROJECTION_VOLATILITY
        ]
        # Calibrated intervals: empirical holdout coverage stays near nominal.
        for strategy_levels in (projection_aware, volatility_strategy["Levels"]):
            for level in INTERVAL_LEVELS:
                nominal = level * 100
                self.assertAlmostEqual(
                    nominal,
                    strategy_levels[str(int(nominal))]["CoveragePercent"],
                    delta=3.0,
                )
        # The projection-aware 90% interval is sharper than the global and
        # position-only strategies at comparable coverage.
        for other in ("global", "position"):
            self.assertLess(
                projection_aware["90"]["MeanWidth"],
                report["Strategies"][other]["Levels"]["90"]["MeanWidth"],
            )
        # Player-specific volatility conditioning yields asymmetric floor/ceiling distances.
        self.assertNotEqual(
            volatility_strategy["Levels"]["90"]["MeanLowerDistance"],
            volatility_strategy["Levels"]["90"]["MeanUpperDistance"],
        )

        volatility = volatility_strategy["Width90ByVolatilityClass"]
        for volatility_class in ("high", "low"):
            self.assertGreater(volatility[volatility_class]["Count"], 0)
            self.assertAlmostEqual(
                90.0, volatility[volatility_class]["CoveragePercent"], delta=3.0,
            )
        self.assertGreater(
            volatility["high"]["MeanWidth"],
            volatility["low"]["MeanWidth"],
        )

        # Players without enough historical games for an individual volatility
        # estimate fall back to broader groups; this early-history subset remains
        # a known weaker calibration pocket and is kept visible rather than hidden.
        self.assertGreater(volatility["unavailable"]["Count"], 0)
        self.assertLess(volatility["unavailable"]["Count"], holdout_rows)
        self.assertLess(
            volatility["unavailable"]["CoveragePercent"],
            volatility["high"]["CoveragePercent"],
        )


if __name__ == "__main__":
    unittest.main()
