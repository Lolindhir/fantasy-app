"""win-prob-v1 and its use in MatchupProjections and WeeklyRecaps (Issue #1443). Synthetic inputs only; no real league or player data."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from statistics import NormalDist

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import weekly_recaps as wr  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.team_range import v1 as team_range  # noqa: E402
from derived_data_lib.models.win_prob import v1 as win_prob  # noqa: E402


def projection(points, sigma):
    z = team_range.z_for_level(0.9)
    return {"Status": "available", "Points": points, "PredictionRanges": [{"Level": 0.9, "Lower": points - sigma * z, "Upper": points + sigma * z}]}


class FormulaTests(unittest.TestCase):
    def test_probability_is_the_normal_cdf_of_the_standardized_difference_without_a_factor(self) -> None:
        expected = NormalDist().cdf((120 - 100) / math.sqrt(15 ** 2 + 20 ** 2))
        self.assertAlmostEqual(expected, win_prob.win_probability(120, 15, 100, 20), places=12)
        self.assertEqual((79, 21), win_prob.percent_pair(win_prob.win_probability(120, 15, 100, 20)))

    def test_symmetry_and_sum_of_100(self) -> None:
        for a, b in ((100, 100), (130.5, 99.2), (80, 140), (101.234, 101.0)):
            first = win_prob.win_probability(a, 12, b, 17)
            second = win_prob.win_probability(b, 17, a, 12)
            self.assertAlmostEqual(1.0, first + second, places=12)
            pair = win_prob.percent_pair(first)
            self.assertEqual(100, sum(pair))
        self.assertEqual((50, 50), win_prob.percent_pair(win_prob.win_probability(100, 10, 100, 10)))

    def test_half_percent_ties_still_add_up_to_100(self) -> None:
        self.assertEqual((65, 35), win_prob.percent_pair(0.65))
        self.assertEqual(100, sum(win_prob.percent_pair(0.345)))

    def test_missing_input_is_unknown_not_50(self) -> None:
        self.assertIsNone(win_prob.win_probability(None, 10, 100, 10))
        self.assertIsNone(win_prob.win_probability(100, None, 100, 10))
        self.assertIsNone(win_prob.win_probability(float("nan"), 10, 100, 10))
        self.assertIsNone(win_prob.win_probability(100, -1, 100, 10))
        self.assertIsNone(win_prob.percent_pair(None))
        available = {"State": "available", "ProjectedFinalScore": 100, "StandardDeviation": 10}
        self.assertIsNone(win_prob.matchup_percentages(available, {"State": "partial", "ProjectedFinalScore": None, "StandardDeviation": None}))
        self.assertIsNotNone(win_prob.matchup_percentages(available, available))

    def test_decided_matchup_without_variance(self) -> None:
        self.assertEqual((100, 0), win_prob.percent_pair(win_prob.win_probability(101, 0, 99, 0)))
        self.assertEqual((50, 50), win_prob.percent_pair(win_prob.win_probability(99, 0, 99, 0)))

    def test_upset_boundary_is_below_35_percent(self) -> None:
        self.assertTrue(win_prob.is_upset(0.3499))
        self.assertFalse(win_prob.is_upset(0.35))
        self.assertFalse(win_prob.is_upset(0.8))
        self.assertIsNone(win_prob.is_upset(None))

    def test_upset_level_boundaries(self) -> None:
        self.assertEqual("upset", win_prob.upset_level(0.3499))
        self.assertEqual("underdog", win_prob.upset_level(0.35))
        self.assertEqual("underdog", win_prob.upset_level(0.4999))
        self.assertIsNone(win_prob.upset_level(0.5))
        self.assertIsNone(win_prob.upset_level(0.9))
        self.assertIsNone(win_prob.upset_level(None))

    def test_model_is_registered_pinned_and_pure(self) -> None:
        self.assertIs(win_prob, registry.get_model("win-prob-v1", "win-prob"))
        self.assertEqual({"Distribution": "normal-difference", "Calibration": "none", "Unit": "whole-percent", "UpsetThreshold": 0.35, "UnderdogThreshold": 0.5}, dict(win_prob.PARAMS))
        source = Path(win_prob.__file__).read_text(encoding="utf-8")
        for forbidden in ("open(", "read_text", "datetime", "time.", "environ"):
            self.assertNotIn(forbidden, source)


class MatchupProjectionsTests(unittest.TestCase):
    def test_published_chance_equals_the_formula_of_the_published_projection(self) -> None:
        import matchup_projection as mp

        context = {
            "Season": 2026, "Week": 3,
            "FantasyMatchups": [{"FantasyMatchupID": "m1", "TeamIDs": ["1", "2"]}],
            "Games": [{"Status": "Scheduled", "FantasyTeams": [
                {"FantasyMatchupID": "m1", "FantasyTeamID": "1", "Players": [{"PlayerID": "a", "IsStarter": True, "Points": None}, {"PlayerID": "b", "IsStarter": True, "Points": None}]},
                {"FantasyMatchupID": "m1", "FantasyTeamID": "2", "Players": [{"PlayerID": "c", "IsStarter": True, "Points": None}]},
            ]}],
            "NonGameAssociations": [],
        }
        model = {"Season": 2026, "Week": 3, "CanonicalLeagueID": "x", "Records": [
            {"PlayerID": "a", "Projection": projection(20, 5)},
            {"PlayerID": "b", "Projection": projection(15, 4)},
            {"PlayerID": "c", "Projection": projection(30, 6)},
        ]}
        payload = mp.build_matchup_projections(context, model)
        teams = payload["Matchups"][0]["Teams"]
        expected = win_prob.win_probability(teams[0]["ProjectedFinalScore"], teams[0]["StandardDeviation"], teams[1]["ProjectedFinalScore"], teams[1]["StandardDeviation"])
        self.assertEqual(win_prob.percent_pair(expected), (teams[0]["WinProbability"], teams[1]["WinProbability"]))
        self.assertEqual(100, teams[0]["WinProbability"] + teams[1]["WinProbability"])
        self.assertEqual("win-prob-v1", payload["WinProbabilityModel"])

        del model["Records"][2]  # a starter without a projection: the team is not available
        payload = mp.build_matchup_projections(context, model)
        self.assertTrue(all(team["WinProbability"] is None for team in payload["Matchups"][0]["Teams"]))


class PregameTests(unittest.TestCase):
    @staticmethod
    def _facts(score_a, score_b):
        def p(pid, cid):
            return {"PlayerID": pid, "CanonicalPlayerID": cid, "IsStarter": True, "HasPoints": True, "Points": 1}
        return [{"FantasyMatchupID": "m1", "Teams": [
            {"FantasyTeamID": "1", "Players": [p("a", "ca")], "FinalScore": score_a},
            {"FantasyTeamID": "2", "Players": [p("b", "cb")], "FinalScore": score_b}]}]

    def _run(self, facts, projections):
        identity = {"ByCanonical": {}, "ByPlayer": {}}
        return wr.pregame_win_probabilities(facts, {"1": 1, "2": 2}, identity, projections, team_range, win_prob)

    def test_favorite_loses_is_an_upset_and_counts_for_the_winner(self) -> None:
        result = self._run(self._facts(80, 100), {"ca": projection(120, 20), "cb": projection(90, 20)})
        matchup = result[0]
        self.assertGreater(matchup["Teams"][0]["PregameWinProbability"], 65)
        self.assertEqual(100, sum(t["PregameWinProbability"] for t in matchup["Teams"]))
        self.assertTrue(matchup["Upset"])
        self.assertEqual("upset", matchup["UpsetLevel"])
        self.assertEqual(2, matchup["UnderdogWinnerFantasyTeamID"])
        self.assertEqual(2, matchup["UpsetWinnerFantasyTeamID"])
        counts = wr.upset_counts([{"WinProbabilities": result}])
        self.assertEqual([{"FantasyTeamID": 1, "Upsets": 0, "Weeks": 1}, {"FantasyTeamID": 2, "Upsets": 1, "Weeks": 1}], counts)

    def test_favorite_wins_is_no_upset(self) -> None:
        matchup = self._run(self._facts(110, 90), {"ca": projection(120, 20), "cb": projection(90, 20)})[0]
        self.assertFalse(matchup["Upset"])
        self.assertIsNone(matchup["UpsetWinnerFantasyTeamID"])
        self.assertIsNone(matchup["UpsetLevel"])
        self.assertIsNone(matchup["UnderdogWinnerFantasyTeamID"])

    def test_underdog_win_between_35_and_50_percent_is_marked_but_no_upset(self) -> None:
        # Team 1 is a slight favorite (about 60 percent) and loses: the winner had about 40 percent.
        matchup = self._run(self._facts(80, 100), {"ca": projection(100, 20), "cb": projection(90, 20)})[0]
        winner_chance = matchup["Teams"][1]["PregameWinProbability"]
        self.assertTrue(35 <= winner_chance < 50)
        self.assertFalse(matchup["Upset"])
        self.assertEqual("underdog", matchup["UpsetLevel"])
        self.assertEqual(2, matchup["UnderdogWinnerFantasyTeamID"])
        self.assertEqual([{"FantasyTeamID": 1, "Upsets": 0, "Weeks": 1}, {"FantasyTeamID": 2, "Upsets": 0, "Weeks": 1}], wr.upset_counts([{"WinProbabilities": [matchup]}]))

    def test_missing_projection_or_tie_gives_unknown_or_no_upset(self) -> None:
        matchup = self._run(self._facts(110, 90), {"ca": projection(120, 20)})[0]
        self.assertTrue(all(t["PregameWinProbability"] is None for t in matchup["Teams"]))
        self.assertIsNone(matchup["Upset"])
        self.assertIsNone(matchup["UpsetLevel"])
        tie = self._run(self._facts(100, 100), {"ca": projection(120, 20), "cb": projection(90, 20)})[0]
        self.assertFalse(tie["Upset"] is True)
        self.assertIsNone(tie["UpsetLevel"])
        self.assertIsNone(tie["UnderdogWinnerFantasyTeamID"])
        self.assertEqual([], wr.upset_counts([{"WinProbabilities": [matchup]}]))


if __name__ == "__main__":
    unittest.main()
