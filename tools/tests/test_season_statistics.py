"""season-stats-v1 and the season-statistics product (Issue #506). Synthetic weeks for the model; invariants on persisted state for the product."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.season_stats import v1  # noqa: E402
from derived_data_lib.models.team_range import v1 as team_range  # noqa: E402
from derived_data_lib.models.win_prob import v1 as win_prob  # noqa: E402
from derived_data_lib import season_statistics as ss  # noqa: E402

REPO = TOOLS.parent


def game(a, pa, b, pb, chance=None, proj_a=None, proj_b=None):
    return {"Teams": [{"TeamID": a, "Points": pa, "PregameProjection": proj_a}, {"TeamID": b, "Points": pb, "PregameProjection": proj_b}], "WinProbability": chance}


def bb_game(a, b, **values):
    """Game with best-ball inputs: values keyed like ``bb_a``, ``bb_b``, ``eff_a``, ``eff_b``, ``pa``, ``pb``."""
    return {"Teams": [
        {"TeamID": a, "Points": 100, "PregameProjection": values.get("pa"), "ProjectedBestBallPoints": values.get("bb_a"), "LineupEfficiencyActual": values.get("eff_a")},
        {"TeamID": b, "Points": 90, "PregameProjection": values.get("pb"), "ProjectedBestBallPoints": values.get("bb_b"), "LineupEfficiencyActual": values.get("eff_b")},
    ], "WinProbability": None}


def week(number, *games):
    return {"Week": number, "Games": list(games)}


def team(result, team_id):
    return next(t for t in result["Teams"] if t["TeamID"] == team_id)


class BestBallTests(unittest.TestCase):
    def test_efficiencies_means_and_strength(self) -> None:
        weeks = [week(1, bb_game(1, 2, pa=90, bb_a=100, eff_a=80, pb=50, bb_b=100, eff_b=70)),
                 week(2, bb_game(1, 2, pa=80, bb_a=100, eff_a=82, pb=60, bb_b=None, eff_b=None))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertEqual([90.0, 80.0], [g["LineupEfficiencyProjected"] for g in one["GameLog"]])
        self.assertEqual(85.0, one["LineupEfficiencyProjected"])
        self.assertEqual(81.0, one["LineupEfficiencyActual"])
        self.assertEqual(100.0, one["ProjectedBestBallPoints"])
        self.assertEqual(85.0, one["ProjectedBestBallStrength"])
        # unknown best ball (week 2) stays unknown, never zero
        self.assertEqual(1, two["BestBallGames"])
        self.assertIsNone(two["GameLog"][1]["LineupEfficiencyProjected"])
        self.assertIsNone(two["GameLog"][1]["LineupEfficiencyActual"])

    def test_no_best_ball_gives_null_values(self) -> None:
        result = v1.compute([1, 2], [week(1, bb_game(1, 2))])
        self.assertIsNone(team(result, 1)["ProjectedBestBallStrength"])
        self.assertEqual(0, team(result, 1)["BestBallGames"])


class ProjectedBestBallTests(unittest.TestCase):
    PLAYERS = [
        {"PlayerID": "a", "IsStarter": True}, {"PlayerID": "b", "IsStarter": False},
        {"PlayerID": "c", "IsStarter": False}, {"PlayerID": "d", "IsStarter": False},
    ]
    IDENTITY = {"ByPlayer": {k: {"CanonicalPlayerID": k.upper(), "Position": p} for k, p in
                             {"a": "QB", "b": "RB", "c": "RB", "d": "WR"}.items()}, "ByCanonical": {}}

    @staticmethod
    def proj(points):
        return {"Status": "available", "Points": points, "PredictionRanges": [{"Level": 0.9, "Lower": points - 5, "Upper": points + 5}]}

    def slots(self):
        from weekly_lineup_optimizer import StartingSlot
        return [StartingSlot("QB1", frozenset({"QB"})), StartingSlot("RB1", frozenset({"RB"})),
                StartingSlot("FLEX1", frozenset({"RB", "WR"}))]

    def test_flex_takes_the_best_remaining_player(self) -> None:
        projections = {"A": self.proj(20), "B": self.proj(10), "C": self.proj(12), "D": self.proj(8)}
        points, excluded = ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots())
        self.assertEqual((42.0, 0), (points, excluded))  # QB 20 + RB 12 + FLEX RB 10

    def test_bench_player_without_projection_is_excluded_and_counted(self) -> None:
        projections = {"A": self.proj(20), "B": self.proj(10), "C": {"Status": "insufficient-history"}, "D": self.proj(8)}
        points, excluded = ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots())
        self.assertEqual((38.0, 1), (points, excluded))  # QB 20 + RB 10 + FLEX WR 8

    def test_starter_without_projection_makes_it_unknown(self) -> None:
        projections = {"B": self.proj(10), "C": self.proj(12), "D": self.proj(8)}
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots()))

    def test_missing_identity_or_slots_is_unknown(self) -> None:
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, None, {}, team_range, self.slots()))
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, self.IDENTITY, {}, team_range, []))


class AllPlayTests(unittest.TestCase):
    def test_expected_wins_luck_and_all_play_record(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90), game(3, 80, 4, 120)), week(2, game(1, 70, 3, 70), game(2, 60, 4, 50))]
        result = v1.compute([1, 2, 3, 4], weeks)
        # week 1 shares: 4->3/3, 1->2/3, 2->1/3, 3->0 ; week 2: 1 and 3 tie on top (2.5/3... below both 2 teams) -> (2+0.5)/3
        one = team(result, 1)
        self.assertAlmostEqual(2 / 3 + 2.5 / 3, one["ExpectedWins"], places=4)
        self.assertEqual((1, 1), (one["Wins"], one["Ties"]))
        self.assertAlmostEqual(1.5 - one["ExpectedWins"], one["Luck"], places=4)
        self.assertEqual({"Wins": 4, "Losses": 1, "Ties": 1}, one["AllPlay"])

    def test_expected_wins_sum_equals_games_times_half_the_league(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90), game(3, 80, 4, 120)), week(2, game(1, 70, 3, 75), game(2, 60, 4, 50))]
        result = v1.compute([1, 2, 3, 4], weeks)
        self.assertAlmostEqual(2 * 4 / 2, sum(t["ExpectedWins"] for t in result["Teams"]), places=3)
        self.assertAlmostEqual(0.0, sum(t["Luck"] for t in result["Teams"]), places=3)

    def test_progression_has_one_entry_per_week_and_ends_at_the_final_values(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90)), week(2, game(1, 70, 2, 75))]
        result = v1.compute([1, 2], weeks)
        self.assertEqual([1, 2], [w["Week"] for w in result["Weeks"]])
        last = next(t for t in result["Weeks"][-1]["Teams"] if t["TeamID"] == 1)
        self.assertEqual(team(result, 1)["ExpectedWins"], last["ExpectedWins"])
        self.assertEqual(team(result, 1)["Luck"], last["Luck"])

    def test_no_played_week_gives_unknown_values_not_zero(self) -> None:
        result = v1.compute([1, 2], [])
        self.assertIsNone(team(result, 1)["ExpectedWins"])
        self.assertIsNone(team(result, 1)["Luck"])
        self.assertIsNone(result["BiggestUpset"])


class StrengthAndTimingTests(unittest.TestCase):
    def test_strength_schedule_burden_and_timing(self) -> None:
        weeks = [week(1, game(1, 120, 2, 80)), week(2, game(1, 100, 2, 100))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertAlmostEqual(110 / 100, one["RelativeScoringStrength"], places=4)
        self.assertAlmostEqual(0.9, one["StrengthOfSchedule"], places=4)  # opponent strength 90/100
        self.assertAlmostEqual(1.1, two["StrengthOfSchedule"], places=4)
        self.assertAlmostEqual(90 / 100, one["PointsAgainstBurden"], places=4)
        self.assertAlmostEqual((80 - 90 + 100 - 90) / 2, one["OpponentTiming"], places=4)
        self.assertEqual(1, two["AboveAverageOpponents"])

    def test_brick_wall_base_counts_wins_against_above_average_opponents(self) -> None:
        weeks = [week(1, game(1, 120, 2, 80)), week(2, game(1, 60, 2, 100))]
        result = v1.compute([1, 2], weeks)
        # team 2 average 90: team 1 scored 120 (above) in week 1 and 60 (below) in week 2 against team 2's average 90 -> only week 1 counts for team 2
        two = team(result, 2)
        self.assertEqual(1, two["AboveAverageOpponents"])
        self.assertEqual(0, two["AboveAverageOpponentWins"])
        one = team(result, 1)
        self.assertEqual(1, one["AboveAverageOpponents"])  # team 2 scored 100 > 90 in week 2 ... average of team 2 is 90
        self.assertEqual(0, one["AboveAverageOpponentWins"])


class ProjectionTests(unittest.TestCase):
    def test_projection_delta_uses_only_games_with_a_projection(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, proj_a=90, proj_b=None)), week(2, game(1, 80, 2, 70, proj_a=100, proj_b=60))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertAlmostEqual((10 - 20) / 2, one["ProjectionDelta"], places=4)
        self.assertEqual(2, one["ProjectionGames"])
        self.assertEqual(1, two["ProjectionGames"])
        self.assertIsNone(two["GameLog"][0]["ProjectionDelta"])

    def test_no_projection_at_all_is_none(self) -> None:
        result = v1.compute([1, 2], [week(1, game(1, 100, 2, 90))])
        self.assertIsNone(team(result, 1)["ProjectionDelta"])
        self.assertEqual(0, team(result, 1)["ProjectionGames"])


class UpsetTests(unittest.TestCase):
    def test_thresholds_underdog_and_upset_counts(self) -> None:
        weeks = [
            week(1, game(1, 100, 2, 90, chance=0.30)),   # team 1 wins with 30 percent: upset
            week(2, game(1, 100, 2, 90, chance=0.45)),   # team 1 wins with 45 percent: underdog win, no upset
            week(3, game(1, 100, 2, 90, chance=0.60)),   # favorite wins
            week(4, game(1, 80, 2, 90, chance=0.70)),    # team 1 loses as favorite, team 2 won with 30 percent
            week(5, game(1, 80, 2, 90, chance=None)),    # unknown chance counts nowhere
        ]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertEqual((2, 1, 1, 1, 4), (one["UnderdogWins"], one["UpsetWins"], one["FavoriteLosses"], one["UpsetLosses"], one["KnownChanceGames"]))
        self.assertEqual((1, 1, 2, 1), (two["UnderdogWins"], two["UpsetWins"], two["FavoriteLosses"], two["UpsetLosses"]))

    def test_boundaries_are_strict(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, chance=v1.UPSET_THRESHOLD)), week(2, game(1, 100, 2, 90, chance=v1.UNDERDOG_THRESHOLD))]
        one = team(v1.compute([1, 2], weeks), 1)
        self.assertEqual((1, 0), (one["UnderdogWins"], one["UpsetWins"]))

    def test_biggest_upset_lowest_chance_and_none_without_upset(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, chance=0.30)), week(2, game(1, 80, 2, 90, chance=0.90)), week(3, game(1, 100, 2, 90, chance=0.34))]
        upset = v1.compute([1, 2], weeks)["BiggestUpset"]
        self.assertEqual((2, 2, 0.1), (upset["Week"], upset["WinnerTeamID"], upset["WinnerPregameWinProbability"]))
        self.assertIsNone(v1.compute([1, 2], [week(1, game(1, 100, 2, 90, chance=0.50))])["BiggestUpset"])

    def test_tie_in_points_is_no_upset_and_equal_chances_pick_the_earlier_week(self) -> None:
        self.assertIsNone(v1.compute([1, 2], [week(1, game(1, 100, 2, 100, chance=0.2))])["BiggestUpset"])
        weeks = [week(1, game(1, 100, 2, 90, chance=0.2)), week(2, game(1, 100, 2, 90, chance=0.2))]
        self.assertEqual(1, v1.compute([1, 2], weeks)["BiggestUpset"]["Week"])


class WeekGamesTests(unittest.TestCase):
    def test_chance_comes_from_the_team_range_and_win_prob_models_and_is_unknown_without_projection(self) -> None:
        z = team_range.z_for_level(0.9)

        def projection(points, sigma):
            return {"Status": "available", "Points": points, "PredictionRanges": [{"Level": 0.9, "Lower": points - sigma * z, "Upper": points + sigma * z}]}

        def side(team_id, player, score):
            return {"FantasyTeamID": team_id, "FinalScore": score, "Players": [{"PlayerID": player, "IsStarter": True, "CanonicalPlayerID": f"c-{player}"}]}

        facts = [{"FantasyMatchupID": "m1", "Teams": [side("1", "p1", 100.0), side("2", "p2", 90.0)]}]
        games = ss.week_games(facts, None, {"c-p1": projection(120, 10), "c-p2": projection(100, 10)}, team_range, win_prob)
        expected = win_prob.win_probability(120, 10, 100, 10)
        self.assertAlmostEqual(expected, games[0]["WinProbability"], places=9)
        self.assertEqual([120.0, 100.0], [t["PregameProjection"] for t in games[0]["Teams"]])
        missing = ss.week_games(facts, None, {"c-p1": projection(120, 10)}, team_range, win_prob)
        self.assertIsNone(missing[0]["WinProbability"])
        self.assertIsNone(missing[0]["Teams"][1]["PregameProjection"])


class RegistryTests(unittest.TestCase):
    def test_model_is_registered_with_its_kind(self) -> None:
        self.assertIs(v1, registry.get_model("season-stats-v1", "season-stats"))
        self.assertEqual(0.35, v1.PARAMS["UpsetThreshold"])


class PersistedProductTests(unittest.TestCase):
    """Invariants of the persisted documents; no player, team or value is hard-wired."""

    def documents(self):
        root = REPO / "data-derived" / "season-statistics"
        files = sorted(root.glob("*/*.json"))
        self.assertTrue(files, "no persisted season-statistics document")
        return [json.loads(path.read_text(encoding="utf-8")) for path in files]

    def test_documents_are_consistent(self) -> None:
        for doc in self.documents():
            self.assertEqual("season-statistics", doc["Product"])
            teams = doc["Teams"]
            completed = doc["AsOf"]["CompletedWeeks"]
            self.assertEqual(completed, len(doc["Weeks"]))
            if completed:
                self.assertAlmostEqual(completed * len(teams) / 2, sum(t["ExpectedWins"] for t in teams), delta=0.01 * len(teams))
                self.assertAlmostEqual(0.0, sum(t["Luck"] for t in teams), delta=0.01 * len(teams))
            for entry in teams:
                self.assertEqual(entry["Games"], len(entry["GameLog"]))
                self.assertEqual(entry["Wins"] + entry["Losses"] + entry["Ties"], entry["Games"])
                self.assertLessEqual(entry["UpsetWins"], entry["UnderdogWins"])
            upset = doc["BiggestUpset"]
            if upset is not None:
                self.assertLess(upset["WinnerPregameWinProbability"], doc["Thresholds"]["UpsetWinProbability"])

    def test_materialization_is_a_noop_on_unchanged_inputs(self) -> None:
        import derived_data

        out_root = REPO / "data-derived"
        for league in sorted({p.parent.name for p in (out_root / "season-statistics").glob("*/*.json")}):
            summary = derived_data.materialize_season_statistics(REPO, out_root, league, None, True)
            self.assertEqual([], [s["Season"] for s in summary["Seasons"] if s.get("WouldWrite")])


if __name__ == "__main__":
    unittest.main()
