from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_team_range_backtest import (  # noqa: E402
    build_report,
    build_team_week_row,
    calibration_scale,
    coverage,
    last_fantasy_week,
)
from matchup_projection import z_for_level  # noqa: E402

Z90 = z_for_level(0.9)


def projection(points: float, sigma: float, status: str = "available") -> dict:
    if status != "available":
        return {"Status": status, "Points": None, "PredictionRanges": []}
    return {
        "Status": "available",
        "Points": points,
        "PredictionRanges": [
            {"Level": 0.9, "Lower": points - Z90 * sigma, "Upper": points + Z90 * sigma}
        ],
    }


def row(actual: float, mean: float = 100.0, variance: float = 100.0, season: int = 2024) -> dict:
    return {"Season": season, "Week": 1, "Roster": "r", "Mean": mean, "Variance": variance, "Actual": actual, "ByeStarters": 0}


class TeamWeekRowTests(unittest.TestCase):
    def test_team_week_adds_player_variances_and_counts_byes_as_zero(self) -> None:
        projections = {
            "a": projection(10.0, 6.0),
            "b": projection(20.0, 8.0),
            "c": {"Status": "no-game", "Points": None, "PredictionRanges": []},
        }

        result, reason = build_team_week_row(["a", "b", "c"], projections, actual=33.0)

        self.assertIsNone(reason)
        self.assertEqual(result["Mean"], 30.0)
        self.assertAlmostEqual(result["Variance"], 100.0, places=6)
        self.assertEqual(result["ByeStarters"], 1)
        self.assertEqual(result["Actual"], 33.0)

    def test_unprojectable_or_missing_starters_skip_the_team_week(self) -> None:
        projections = {"a": projection(10.0, 6.0), "b": projection(0, 0, status="insufficient-history")}

        self.assertEqual(build_team_week_row(["a", "b"], projections, actual=1.0), (None, "insufficient-history"))
        self.assertEqual(build_team_week_row(["a", "zzz"], projections, actual=1.0), (None, "missing-record"))


class CoverageTests(unittest.TestCase):
    def test_coverage_counts_hits_and_tail_misses_per_level(self) -> None:
        # sigma = 10: the 90% range is 100 +/- 16.4485.
        rows = [row(100.0), row(115.0), row(60.0), row(140.0), row(84.0)]

        result = coverage(rows, levels=(0.9,))

        self.assertEqual(result["Count"], 5)
        self.assertEqual(result["Coverage"]["0.9"], 0.6)
        self.assertEqual(result["LowMisses"]["0.9"], 1)
        self.assertEqual(result["HighMisses"]["0.9"], 1)
        self.assertAlmostEqual(result["MeanPredictedStd"], 10.0, places=3)

    def test_wider_scale_turns_a_miss_into_a_hit(self) -> None:
        rows = [row(125.0)]

        self.assertEqual(coverage(rows, levels=(0.9,))["Coverage"]["0.9"], 0.0)
        self.assertEqual(coverage(rows, levels=(0.9,), scale=1.6)["Coverage"]["0.9"], 1.0)

    def test_empty_input_is_reported_without_statistics(self) -> None:
        self.assertEqual(coverage([]), {"Count": 0})


class CalibrationTests(unittest.TestCase):
    def test_scale_is_the_level_quantile_of_standardized_errors(self) -> None:
        # Ten rows with |z| = 0.1 .. 1.0 times sigma 10: the 90th percentile is |z| = 0.9.
        rows = [row(100.0 + 10.0 * z) for z in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]

        self.assertAlmostEqual(calibration_scale(rows), 0.9 / Z90, places=6)

    def test_scale_needs_rows_with_variance(self) -> None:
        with self.assertRaises(ValueError):
            calibration_scale([row(100.0, variance=0.0)])

    def test_report_calibrates_on_one_season_and_evaluates_the_other(self) -> None:
        rows = [row(100.0 + 10.0 * z, season=2024) for z in (0.5, 1.0, 1.5, 2.0)]
        rows += [row(100.0 + 10.0 * z, season=2025) for z in (0.5, 1.0, 1.5, 2.0)]
        report = build_report({"Rows": rows, "Skipped": [], "FailedWeeks": []}, calibration_season=2024)

        self.assertEqual(sorted(report["Seasons"]), ["2024", "2025"])
        self.assertEqual(report["AllSeasons"]["Count"], 8)
        self.assertEqual(report["Calibration"]["CalibrationSeason"], 2024)
        self.assertEqual(report["Calibration"]["HoldoutRaw"]["Count"], 4)
        self.assertGreater(
            report["Calibration"]["HoldoutScaled"]["Coverage"]["0.9"],
            report["Calibration"]["HoldoutRaw"]["Coverage"]["0.9"] - 1e-9,
        )
        self.assertTrue(math.isfinite(report["Calibration"]["Scale"]))


class LastFantasyWeekTests(unittest.TestCase):
    def _league(self, structure: dict) -> Path:
        root = Path(tempfile.mkdtemp())
        path = root / "source-data/leagues/league-a/seasons/2025/league.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"WeekStructure": structure}), encoding="utf-8")
        return root

    def test_final_league_week_excludes_the_unused_nfl_week_18(self) -> None:
        root = self._league({"FinalLeagueWeek": 17, "ExpectedLastLeagueWeek": 17, "HighestNonEmptyMatchupWeek": 18})

        self.assertEqual(last_fantasy_week(root, "league-a", 2025), 17)

    def test_expected_last_week_is_the_fallback_for_a_running_season(self) -> None:
        root = self._league({"FinalLeagueWeek": None, "ExpectedLastLeagueWeek": 17})

        self.assertEqual(last_fantasy_week(root, "league-a", 2025), 17)

    def test_missing_week_structure_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            last_fantasy_week(self._league({}), "league-a", 2025)


if __name__ == "__main__":
    unittest.main()
