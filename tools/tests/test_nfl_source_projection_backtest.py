from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_backtest import (  # noqa: E402
    _played,
    build_v1_backtest_report,
    walk_forward_v1,
)


class ProjectionWalkForwardContractTests(unittest.TestCase):
    def test_v1_never_uses_target_week_outcome_in_its_projection(self) -> None:
        observations = {
            1: [
                {
                    "Season": 2025,
                    "Week": 1,
                    "CanonicalPlayerID": "A",
                    "PlayerName": "Alpha",
                    "Position": "WR",
                    "FantasyPoints": 10.0,
                },
                {
                    "Season": 2025,
                    "Week": 1,
                    "CanonicalPlayerID": "B",
                    "PlayerName": "Beta",
                    "Position": "RB",
                    "FantasyPoints": 5.0,
                },
            ],
            2: [
                {
                    "Season": 2025,
                    "Week": 2,
                    "CanonicalPlayerID": "A",
                    "PlayerName": "Alpha",
                    "Position": "WR",
                    "FantasyPoints": 20.0,
                },
                {
                    "Season": 2025,
                    "Week": 2,
                    "CanonicalPlayerID": "C",
                    "PlayerName": "Gamma",
                    "Position": "TE",
                    "FantasyPoints": 7.0,
                },
            ],
            3: [
                {
                    "Season": 2025,
                    "Week": 3,
                    "CanonicalPlayerID": "A",
                    "PlayerName": "Alpha",
                    "Position": "WR",
                    "FantasyPoints": 30.0,
                }
            ],
        }

        report = walk_forward_v1(observations)

        self.assertEqual(2, report["PredictionCount"])
        self.assertEqual(3, report["ColdStartCount"])
        self.assertEqual(12.5, report["Metrics"]["MAE"])
        self.assertEqual(-12.5, report["Metrics"]["Bias"])
        self.assertEqual(
            [10.0, 15.0],
            [
                round(row["Projection"], 4)
                for row in sorted(
                    report["LargestAbsoluteErrors"],
                    key=lambda row: row["Week"],
                )
            ],
        )

    def test_position_specific_participation_rule_matches_v1_contract(self) -> None:
        self.assertTrue(_played("WR", {"OffenseSnaps": 1.0, "SpecialTeamsSnaps": 0.0}))
        self.assertFalse(_played("WR", {"OffenseSnaps": 0.0, "SpecialTeamsSnaps": 20.0}))
        self.assertTrue(_played("K", {"OffenseSnaps": 0.0, "SpecialTeamsSnaps": 1.0}))
        self.assertFalse(_played("K", {"OffenseSnaps": 1.0, "SpecialTeamsSnaps": 0.0}))

    def test_real_2024_2025_v1_backtest_is_reproducible(self) -> None:
        report = build_v1_backtest_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            seasons=[2024, 2025],
            first_week=1,
            last_week=18,
        )

        summary = {
            "Combined": report["Combined"],
            "Seasons": [
                {
                    "Season": row["Season"],
                    "ObservationAudit": row["ObservationAudit"],
                    "PredictionCount": row["PredictionCount"],
                    "ColdStartCount": row["ColdStartCount"],
                    "Metrics": row["Metrics"],
                    "ByPosition": row["ByPosition"],
                    "ByWeek": row["ByWeek"],
                    "ByPriorGames": row["ByPriorGames"],
                }
                for row in report["SeasonReports"]
            ],
        }
        print("V1_BACKTEST_SUMMARY=" + json.dumps(summary, sort_keys=True))

        self.assertEqual([2024, 2025], report["Seasons"])
        self.assertEqual(
            {
                "Count": 11361,
                "MAE": 4.6471,
                "RMSE": 6.4724,
                "Bias": -0.2951,
                "MeanProjection": 7.9338,
                "MeanActual": 8.2289,
            },
            report["Combined"]["Metrics"],
        )
        self.assertEqual(11361, report["Combined"]["PredictionCount"])
        self.assertEqual(
            "projection for week W uses only confirmed played-game outcomes from weeks < W",
            report["SeasonReports"][0]["LeakageRule"],
        )

        season_2024, season_2025 = report["SeasonReports"]
        self.assertEqual(5637, season_2024["PredictionCount"])
        self.assertEqual(629, season_2024["ColdStartCount"])
        self.assertEqual(6, season_2024["ObservationAudit"]["MissingParticipationEvidenceCount"])
        self.assertEqual(
            {
                "Count": 5637,
                "MAE": 4.6664,
                "RMSE": 6.4847,
                "Bias": -0.4016,
                "MeanProjection": 7.9915,
                "MeanActual": 8.3931,
            },
            season_2024["Metrics"],
        )

        self.assertEqual(5724, season_2025["PredictionCount"])
        self.assertEqual(641, season_2025["ColdStartCount"])
        self.assertEqual(13, season_2025["ObservationAudit"]["MissingParticipationEvidenceCount"])
        self.assertEqual(
            {
                "Count": 5724,
                "MAE": 4.6282,
                "RMSE": 6.4603,
                "Bias": -0.1902,
                "MeanProjection": 7.8769,
                "MeanActual": 8.0671,
            },
            season_2025["Metrics"],
        )

        self.assertEqual(5.5087, report["Combined"]["ByWeek"]["2"]["MAE"])
        self.assertEqual(4.4089, report["Combined"]["ByWeek"]["9"]["MAE"])
        self.assertEqual(6.4903, report["Combined"]["ByPosition"]["QB"]["MAE"])
        self.assertEqual(3.7171, report["Combined"]["ByPosition"]["TE"]["MAE"])


if __name__ == "__main__":
    unittest.main()
