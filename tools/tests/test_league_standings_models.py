"""Tests for the standings-v1 and awards-v1 models (ADR-072, Issue #987 step 2).

Hand-computed constructed leagues pin the PowerShell semantics (tiebreak keys, competition places, .NET rounding,
weekly validation). No real team, owner or season data is wired in.
"""
from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models._common import dotnet_round, ps_text, sequential_sum  # noqa: E402
from derived_data_lib.models.awards import v1 as awards  # noqa: E402
from derived_data_lib.models.standings import v1 as standings  # noqa: E402


def team(team_id, wins, losses, ties, points, against, record, streak="", name=None):
    return {
        "TeamID": team_id, "Owner": f"owner{team_id}", "OwnerAvatarID": f"av{team_id}", "Team": name or f"Team {team_id}",
        "TeamAvatar": None, "Points": points, "PointsAgainst": against, "Wins": wins, "Losses": losses, "Ties": ties,
        "Record": record, "Streak": streak,
    }


def matchup_week(week, *pairs):
    """pairs: ((team_id, points), (team_id, points)) per matchup."""
    entries = []
    for index, (first, second) in enumerate(pairs, start=1):
        entries.append({"TeamID": first[0], "MatchupID": index, "Points": first[1]})
        entries.append({"TeamID": second[0], "MatchupID": index, "Points": second[1]})
    return {"Week": week, "Entries": entries}


class RegistryTests(unittest.TestCase):
    def test_models_are_registered_with_their_kind(self):
        self.assertIs(standings, registry.get_model("standings-v1", kind="standings"))
        self.assertIs(awards, registry.get_model("awards-v1", kind="awards"))
        with self.assertRaises(registry.UnknownModelError):
            registry.get_model("standings-v1", kind="awards")

    def test_params_are_pinned_and_immutable(self):
        self.assertEqual(("WinPercentage desc", "Points desc", "PointsAgainst asc"), standings.PARAMS["RegularSeasonTiebreak"])
        self.assertEqual(0.25, standings.PARAMS["IronWillWinPercentageFactor"])
        self.assertEqual(-999, standings.PARAMS["IronWillFallback"])
        self.assertEqual(0.001, standings.PARAMS["StreakScoreWinWeight"])
        self.assertEqual(0.00001, standings.PARAMS["StreakScorePointWeight"])
        self.assertEqual(("Best Performer", "Streaker", "Overperformer", "Brick Wall", "Clutch Peaker", "Most Improved"), awards.PARAMS["Order"])
        self.assertEqual(0.01, awards.PARAMS["ClutchPeakerPlayoffPlaceWeight"])
        self.assertEqual(-999, awards.PARAMS["ClutchPeakerOutsidePlayoffsScore"])
        self.assertEqual(0.01, awards.PARAMS["MostImprovedPointsPerGameWeight"])
        for module in (standings, awards):
            with self.assertRaises(TypeError):
                module.PARAMS["Injected"] = 1  # type: ignore[index]
        self.assertEqual("standings-v1", standings.MODEL_ID)
        self.assertEqual("awards-v1", awards.MODEL_ID)


class NumericHelperTests(unittest.TestCase):
    def test_dotnet_round_scales_before_rounding_half_to_even(self):
        self.assertEqual(2.68, dotnet_round(2.675, 2))  # Python round() gives 2.67
        self.assertEqual(0.8571, dotnet_round(6 / 7, 4))
        self.assertEqual(-1.0, dotnet_round(-1, 3))
        self.assertEqual(0.12, dotnet_round(0.125, 2))  # exact tie goes to the even digit

    def test_dotnet_round_keeps_the_sign_of_a_negative_zero(self):
        import math
        self.assertEqual(-1.0, math.copysign(1.0, dotnet_round(-0.004, 2)))  # published as -0.0
        self.assertEqual(1.0, math.copysign(1.0, dotnet_round(0.004, 2)))
        self.assertEqual(1.0, math.copysign(1.0, dotnet_round(0.0, 2)))
        with self.assertRaises(ValueError):
            dotnet_round(float("nan"), 2)

    def test_sequential_sum_accumulates_left_to_right(self):
        values = [0.1] * 10
        total = 0.0
        for value in values:
            total += value
        self.assertEqual(total, sequential_sum(values))

    def test_ps_text_prints_whole_doubles_without_decimals(self):
        self.assertEqual("1500", ps_text(1500.0))
        self.assertEqual("1472.9", ps_text(1472.9))
        self.assertEqual("7", ps_text(7))
        self.assertEqual("N/A", ps_text("N/A"))


class RankingTests(unittest.TestCase):
    def test_ordinals(self):
        self.assertEqual(["none", "1st", "2nd", "3rd", "4th", "11th", "21th"], [standings.ordinal(n) for n in (0, 1, 2, 3, 4, 11, 21)])

    def test_win_percentage_counts_ties_as_half_and_marks_no_games(self):
        self.assertEqual(-1, standings.win_percentage(team(1, 0, 0, 0, 0, 0, "")))
        self.assertEqual(0.75, standings.win_percentage(team(1, 3, 1, 0, 0, 0, "")))
        self.assertEqual(0.5, standings.win_percentage(team(1, 1, 1, 2, 0, 0, "")))

    def test_order_is_win_pct_then_points_then_points_against_with_competition_places(self):
        teams = [
            team(1, 2, 1, 0, 300.0, 250.0, "WLW"),
            team(2, 2, 1, 0, 320.0, 260.0, "WWL"),   # same pct, more points -> ahead of team 1
            team(3, 1, 2, 0, 200.0, 280.0, "LWL"),
            team(4, 1, 2, 0, 200.0, 280.0, "LLW"),   # identical key to team 3 -> shared place, input order kept
            team(5, 0, 3, 0, 100.0, 300.0, "LLL"),
        ]
        ranked = standings.rank_teams(teams)
        self.assertEqual([2, 1, 3, 4, 5], [t["TeamID"] for t in ranked])
        self.assertEqual([1, 2, 3, 3, 5], [t["PlaceRegular"] for t in ranked])  # competition: fourth rank is occupied by the tie

    def test_two_or_three_teams_sharing_first_skip_to_third_or_fourth(self):
        for tied_count in (2, 3):
            teams = [team(i, 2, 0, 0, 200.0, 100.0, "WW") for i in range(1, tied_count + 1)]
            teams.append(team(tied_count + 1, 1, 1, 0, 100.0, 150.0, "WL"))
            ranked = standings.rank_teams(teams)
            self.assertEqual([1] * tied_count + [tied_count + 1], [t["PlaceRegular"] for t in ranked])

    def test_lower_points_against_wins_the_last_tiebreak(self):
        ranked = standings.rank_teams([team(1, 1, 1, 0, 100.0, 120.0, "WL"), team(2, 1, 1, 0, 100.0, 90.0, "LW")])
        self.assertEqual([2, 1], [t["TeamID"] for t in ranked])
        self.assertEqual([1, 2], [t["PlaceRegular"] for t in ranked])

    def test_teams_without_games_get_place_zero(self):
        ranked = standings.rank_teams([team(1, 0, 0, 0, 0.0, 0.0, ""), team(2, 0, 0, 0, 0.0, 0.0, "")])
        self.assertEqual([0, 0], [t["PlaceRegular"] for t in ranked])

    def test_ranking_does_not_mutate_the_input(self):
        teams = [team(1, 1, 0, 0, 10.0, 5.0, "W"), team(2, 0, 1, 0, 5.0, 10.0, "L")]
        before = copy.deepcopy(teams)
        standings.rank_teams(teams)
        self.assertEqual(before, teams)


class RegularSeasonRowTests(unittest.TestCase):
    def setUp(self):
        self.teams = [
            team(1, 2, 1, 0, 300.5, 250.25, "WLW", "1W"),
            team(2, 1, 1, 1, 280.0, 290.0, "WTL", "1L"),
            team(3, 0, 2, 1, 150.0, 190.25, "LLT", "1T"),
        ]
        self.rows = standings.regular_season_rows(self.teams, 3)

    def test_rows_follow_the_rank_order_with_hand_computed_values(self):
        first = self.rows[0]
        self.assertEqual([1, 2, 3], [r["Place"] for r in self.rows])
        self.assertEqual([1, 2, 3], [r["TeamID"] for r in self.rows])
        self.assertEqual("1st", first["PlaceOrdinal"])
        self.assertEqual(0.6667, first["WinPercentage"])
        self.assertEqual(".667", first["WinPercentageDisplay"])
        self.assertEqual([1.0, 0.5, 0.6667], first["WinPercentageHistory"])
        self.assertEqual(50.25, first["PointDifference"] + 0)  # 300.5 - 250.25
        self.assertEqual(100.17, first["PointsPerGame"])
        self.assertEqual(83.42, first["PointsAgainstPerGame"])
        self.assertEqual(1, first["LongestWinStreak"])
        self.assertEqual(1, first["LongestLossStreak"])
        self.assertEqual(3, first["NumberOfGames"])
        self.assertEqual("WLW", first["Record"])

    def test_league_average_values_use_the_regular_season_game_count(self):
        # league points 730.5 / (3 teams * 3 games) = 81.1667; team 1 PPG 100.1667 -> diff 19.0
        self.assertEqual(19.0, self.rows[0]["PointsPerGameDiffLeagueAvg"])
        # league win pct average: (0.6667 + 0.5 + 0.1667) / 3
        self.assertEqual(0.22, self.rows[0]["WinPercentageDiffLeagueAvg"])

    def test_streak_and_efficiency_scores(self):
        first = self.rows[0]
        self.assertEqual(round(1 + 2 * 0.001 + 300.5 * 0.00001, 4), first["WinStreakScore"])
        self.assertEqual(round(1 + 1 * 0.001 + 250.25 * 0.00001, 4), first["LossStreakScore"])
        self.assertGreater(first["EfficiencyScore"], self.rows[2]["EfficiencyScore"])

    def test_movement_fields_default_to_null_and_empty(self):
        self.assertTrue(all(r["PreviousWeekPlace"] is None and r["PlaceDelta"] is None and r["WeeklyMovements"] == [] for r in self.rows))

    def test_movement_fields_are_filled_from_the_inputs(self):
        rows = standings.regular_season_rows(self.teams, 3, {1: 2, 2: 1, 3: 3}, {1: [{"Week": 2, "Place": 1}]})
        by_id = {r["TeamID"]: r for r in rows}
        self.assertEqual((2, 1), (by_id[1]["PreviousWeekPlace"], by_id[1]["PlaceDelta"]))  # moved up one place
        self.assertEqual((1, -1), (by_id[2]["PreviousWeekPlace"], by_id[2]["PlaceDelta"]))  # moved down one place
        self.assertEqual([{"Week": 2, "Place": 1}], by_id[1]["WeeklyMovements"])

    def test_without_completed_games_the_iron_will_score_falls_back(self):
        rows = standings.regular_season_rows([team(1, 0, 0, 0, 0.0, 0.0, ""), team(2, 0, 0, 0, 0.0, 0.0, "")], 13)
        self.assertTrue(all(r["IronWillScore"] == -999 for r in rows))
        self.assertTrue(all(r["WinPercentageDisplay"] == "1.000" for r in rows))  # -1 renders like the PowerShell Substring(1) quirk

    def test_a_perfect_record_displays_1_000(self):
        row = standings.regular_season_rows([team(1, 2, 0, 0, 10.0, 5.0, "WW"), team(2, 0, 2, 0, 5.0, 10.0, "LL")], 2)[0]
        self.assertEqual("1.000", row["WinPercentageDisplay"])

    def test_invalid_game_count_fails(self):
        with self.assertRaises(ValueError):
            standings.regular_season_rows(self.teams, 0)


class WeeklyTableTests(unittest.TestCase):
    def setUp(self):
        # four teams, two completed weeks: week 1 1v2 (120-100) and 3v4 (90-110); week 2 1v3 (80-95) and 2v4 (130-60)
        self.teams = [
            team(1, 1, 1, 0, 200.0, 195.0, "WL"), team(2, 1, 1, 0, 230.0, 160.0, "LW"),
            team(3, 1, 1, 0, 185.0, 170.0, "LW"), team(4, 1, 1, 0, 170.0, 200.0, "WL"),
        ]
        self.weeks = [
            matchup_week(1, ((1, 120.0), (2, 100.0)), ((3, 90.0), (4, 110.0))),
            matchup_week(2, ((1, 80.0), (3, 95.0)), ((2, 130.0), (4, 60.0))),
        ]

    def test_tables_are_rebuilt_from_the_matchups_with_the_season_tiebreak(self):
        tables = standings.weekly_tables(self.teams, self.weeks, 2)
        self.assertEqual([1, 2], [t["Week"] for t in tables])
        first = {e["TeamID"]: e for e in tables[0]["Teams"]}
        self.assertEqual((1, 1, 0, 0, 120.0, 100.0), (first[1]["Place"], first[1]["Wins"], first[1]["Losses"], first[1]["Ties"], first[1]["Points"], first[1]["PointsAgainst"]))
        self.assertEqual([1, 2, 3, 4], [e["TeamID"] for e in tables[0]["Teams"]])  # ordered by TeamID
        # winners are team 1 (120 points) and team 4 (110); the losers follow by points: team 2 (100) before team 3 (90)
        self.assertEqual({1: 1, 4: 2, 2: 3, 3: 4}, {tid: e["Place"] for tid, e in first.items()})
        second = {e["TeamID"]: e for e in tables[1]["Teams"]}
        # all four teams are 1-1, so the points decide: 230, 200, 185, 170
        self.assertEqual({2: 1, 1: 2, 3: 3, 4: 4}, {tid: e["Place"] for tid, e in second.items()})
        self.assertEqual(230.0, second[2]["Points"])

    def test_weekly_movements_and_previous_week_places(self):
        tables = standings.weekly_tables(self.teams, self.weeks, 2)
        self.assertEqual({1: 1, 4: 2, 2: 3, 3: 4}, standings.previous_week_places(tables, 2))
        movements = standings.weekly_movements(tables, [1, 2, 3, 4])
        self.assertEqual([{"Week": 2, "Place": 2, "PreviousWeekPlace": 1, "PlaceDelta": -1}], movements[1])  # week 1 has no previous week
        self.assertEqual({"Week": 2, "Place": 1, "PreviousWeekPlace": 3, "PlaceDelta": 2}, movements[2][0])

    def test_no_comparison_before_two_completed_weeks(self):
        tables = standings.weekly_tables(self.teams, self.weeks, 1)
        self.assertEqual(1, len(tables))
        self.assertIsNone(standings.previous_week_places(tables, 1))
        self.assertEqual([], standings.weekly_tables(self.teams, self.weeks, 0))
        self.assertEqual([], standings.weekly_tables([], self.weeks, 2))

    def test_a_missing_week_ends_the_history(self):
        tables = standings.weekly_tables(self.teams, [self.weeks[0]], 2)
        self.assertEqual([1], [t["Week"] for t in tables])
        self.assertIsNotNone(standings.previous_week_places(tables, 2))  # week 1 is validated
        self.assertIsNone(standings.previous_week_places(tables, 3))  # week 2 is not
        self.assertTrue(all(history == [] for history in standings.weekly_movements(tables, [1, 2, 3, 4]).values()))

    def test_a_result_that_contradicts_the_record_ends_the_history(self):
        wrong = copy.deepcopy(self.teams)
        wrong[0]["Record"] = "LL"  # team 1 won week 1 according to the matchups
        self.assertEqual([], standings.weekly_tables(wrong, self.weeks, 2))
        wrong = copy.deepcopy(self.teams)
        wrong[0]["Record"] = "W"  # no entry for week 2
        self.assertEqual([1], [t["Week"] for t in standings.weekly_tables(wrong, self.weeks, 2)])

    def test_malformed_weeks_are_rejected_instead_of_inferred(self):
        broken_cases = {
            "missing points": matchup_week(1, ((1, None), (2, 100.0)), ((3, 90.0), (4, 110.0))),
            "unknown team": matchup_week(1, ((1, 120.0), (9, 100.0)), ((3, 90.0), (4, 110.0))),
        }
        for label, week in broken_cases.items():
            with self.subTest(label):
                self.assertEqual([], standings.weekly_tables(self.teams, [week, self.weeks[1]], 2))
        three = {"Week": 1, "Entries": [
            {"TeamID": 1, "MatchupID": 1, "Points": 1.0}, {"TeamID": 2, "MatchupID": 1, "Points": 2.0},
            {"TeamID": 3, "MatchupID": 1, "Points": 3.0}, {"TeamID": 4, "MatchupID": 2, "Points": 4.0}]}
        self.assertEqual([], standings.weekly_tables(self.teams, [three], 1))
        short = {"Week": 1, "Entries": self.weeks[0]["Entries"][:3]}
        self.assertEqual([], standings.weekly_tables(self.teams, [short], 1))

    def test_a_tied_game_counts_as_a_tie_for_both_teams(self):
        teams = [team(1, 0, 0, 1, 100.0, 100.0, "T"), team(2, 0, 0, 1, 100.0, 100.0, "T")]
        tables = standings.weekly_tables(teams, [matchup_week(1, ((1, 100.0), (2, 100.0)))], 1)
        self.assertEqual([1, 1], [e["Ties"] for e in tables[0]["Teams"]])
        self.assertEqual([1, 1], [e["Place"] for e in tables[0]["Teams"]])  # identical key shares the place


class PlayoffTests(unittest.TestCase):
    def setUp(self):
        self.teams = [{"TeamID": i, "Owner": f"o{i}", "OwnerAvatarID": f"a{i}", "Team": f"T{i}", "TeamAvatar": f"t{i}"} for i in range(1, 7)]

    @staticmethod
    def match(place, winner, loser):
        return {"r": 2, "m": 1, "t1": winner, "t2": loser, "w": winner, "l": loser, "p": place}

    def test_winners_bracket_then_losers_bracket(self):
        winners = [self.match(1, 1, 2), self.match(3, 3, 4), {"r": 1, "m": 1, "t1": 1, "t2": 2, "w": 1, "l": 2, "p": None}]
        losers = [self.match(1, 5, 6)]
        rows = standings.playoff_standings(winners, losers, self.teams)
        self.assertEqual([1, 2, 3, 4, 5, 6], [r["Place"] for r in rows])
        self.assertEqual([1, 2, 3, 4, 5, 6], [r["TeamID"] for r in rows])
        self.assertEqual(["Winner"] * 4 + ["Loser"] * 2, [r["PlaceType"] for r in rows])
        self.assertEqual(["1st", "2nd", "3rd", "4th", "5th", "6th"], [r["PlaceOrdinal"] for r in rows])
        self.assertEqual("a1", rows[0]["OwnerAvatarID"])

    def test_empty_while_no_placement_match_is_decided(self):
        undecided = [{"r": 1, "m": 1, "t1": 1, "t2": 2, "w": None, "l": None, "p": 1}]
        self.assertEqual([], standings.playoff_standings(undecided, [], self.teams))
        self.assertEqual([], standings.playoff_standings([], [], self.teams))
        self.assertEqual([], standings.playoff_standings(None, None, self.teams))

    def test_losers_bracket_may_be_missing(self):
        rows = standings.playoff_standings([self.match(1, 1, 2)], None, self.teams)
        self.assertEqual([1, 2], [r["Place"] for r in rows])

    def test_unknown_team_gets_a_placeholder_row(self):
        rows = standings.playoff_standings([self.match(1, 1, 99)], [], self.teams)
        self.assertEqual("Unknown Owner", rows[1]["Owner"])
        self.assertEqual("Unknown Team (ID: 99)", rows[1]["TeamName"])
        self.assertIsNone(rows[1]["OwnerAvatarID"])


class AllTimeTests(unittest.TestCase):
    @staticmethod
    def season(rows, playoffs):
        return {
            "RegularSeason": [{"TeamID": t, "Place": p, "Owner": f"o{t}", "TeamName": f"T{t}-{label}", "Wins": w, "Losses": l, "Ties": 0,
                               "Points": pts, "PointsAgainst": pa} for (t, p, w, l, pts, pa, label) in rows],
            "Playoffs": [{"TeamID": t, "Place": p, "Owner": f"o{t}", "TeamName": f"T{t}-{label}"} for (t, p, label) in playoffs],
        }

    def test_accumulates_newest_first_and_ranks_by_regular_season_wins_then_pct(self):
        new = self.season([(1, 1, 8, 5, 1000.1, 900.0, "new"), (2, 2, 5, 8, 800.0, 950.0, "new")], [(2, 1, "new"), (1, 2, "new")])
        old = self.season([(1, 2, 6, 7, 900.2, 910.0, "old"), (2, 1, 9, 4, 1100.0, 800.0, "old")], [(2, 1, "old"), (1, 2, "old")])
        result = standings.all_time_standings([new, old])
        regular = {r["TeamID"]: r for r in result["RegularSeason"]}
        self.assertEqual(14, regular[1]["Wins"])
        self.assertEqual(1900.3, regular[1]["Points"])  # rounded to two decimals at the end
        self.assertEqual("T1-new", regular[1]["TeamName"])  # newest season names win
        self.assertEqual(1, regular[1]["RegularSeasonWins"])
        self.assertEqual([1, 2], [r["Place"] for r in result["RegularSeason"]])
        self.assertEqual(round(14 / 26, 4), regular[1]["WinPercentage"])
        playoffs = result["Playoffs"]
        self.assertEqual([2, 1], [r["TeamID"] for r in playoffs])
        self.assertEqual([1, 2], [r["Place"] for r in playoffs])
        self.assertEqual({"Championships": 2, "RunnerUps": 0, "Thirds": 0, "PlaceCumulative": 2, "PlaceAverage": 1.0, "Placements": [1, 1]},
                         {k: playoffs[0][k] for k in ("Championships", "RunnerUps", "Thirds", "PlaceCumulative", "PlaceAverage", "Placements")})

    def test_all_time_regular_season_competition_places_skip_after_exact_tie(self):
        season = self.season([
            (1, 1, 5, 1, 600.0, 500.0, "a"),
            (2, 1, 5, 1, 600.0, 500.0, "b"),
            (3, 3, 3, 3, 450.0, 550.0, "c"),
        ], [])
        regular = standings.all_time_standings([season])["RegularSeason"]
        self.assertEqual([1, 1, 3], [row["Place"] for row in regular])

    def test_place_average_divides_by_the_number_of_seasons(self):
        one = self.season([(1, 1, 1, 0, 10.0, 5.0, "x"), (2, 2, 0, 1, 5.0, 10.0, "x")], [(1, 3, "x")])
        two = self.season([(1, 1, 1, 0, 10.0, 5.0, "y"), (2, 2, 0, 1, 5.0, 10.0, "y")], [])
        row = standings.all_time_standings([two, one])["Playoffs"][0]
        self.assertEqual(1.5, row["PlaceAverage"])  # 3 / 2 seasons, also for a team that placed once

    def test_playoff_ties_use_regular_season_wins_then_average_then_regular_place(self):
        a = self.season([(1, 2, 1, 0, 10.0, 5.0, "a"), (2, 1, 1, 0, 11.0, 5.0, "a")], [(1, 1, "a"), (2, 1, "a")])
        result = standings.all_time_standings([a])
        self.assertEqual([2, 1], [r["TeamID"] for r in result["Playoffs"]])  # team 2 holds the regular-season win

    def test_no_seasons_give_empty_standings(self):
        self.assertEqual({"Playoffs": [], "RegularSeason": []}, standings.all_time_standings([]))


class AwardsTests(unittest.TestCase):
    def rows(self):
        teams = [
            team(1, 2, 1, 0, 300.5, 250.25, "WLW", "1W"),
            team(2, 1, 1, 1, 280.0, 290.0, "WTL", "1L"),
            team(3, 0, 2, 1, 150.0, 190.25, "LLT", "1T"),
        ]
        return standings.regular_season_rows(teams, 3)

    def test_no_award_without_a_completed_game(self):
        rows = standings.regular_season_rows([team(1, 0, 0, 0, 0.0, 0.0, ""), team(2, 0, 0, 0, 0.0, 0.0, "")], 3)
        self.assertEqual(([], {}), awards.compute(rows, [], None))
        self.assertEqual(([], {}), awards.compute([], [], None))
        self.assertEqual(([], {}), awards.compute(None, [], None))

    def test_regular_season_awards_in_order_with_text(self):
        result, annotations = awards.compute(self.rows(), [], None)
        self.assertEqual(["Best Performer", "Streaker", "Overperformer", "Brick Wall"], [a["Name"] for a in result])
        self.assertEqual({}, annotations)
        self.assertEqual("Points: 300.5 | Points per Game: 100.17", result[0]["StatDisplay"])
        self.assertEqual("Longest Streak: 1 Wins | Record: WLW", result[1]["StatDisplay"])
        self.assertRegex(result[3]["StatDisplay"], r"^Points Against per Game: .+ \| League Difference: .+ \| Wins: \d+\)$")  # v1 keeps the closing parenthesis
        self.assertEqual({"Name": "RegularSeason", "DisplayText": "Regular Season", "Order": 2}, result[0]["Type"])
        self.assertEqual("1F525", result[0]["IconUnicode"])

    def test_the_first_team_in_table_order_wins_an_exact_tie(self):
        rows = self.rows()
        for row in rows:
            row["Points"] = 100.0
        self.assertEqual(rows[0]["TeamID"], awards.compute(rows, [], None)[0][0]["TeamID"])

    def test_clutch_peaker_needs_playoffs_and_scores_the_place_gain(self):
        rows = self.rows()
        playoffs = [{"TeamID": 3, "Place": 1, "PlaceOrdinal": "1st"}, {"TeamID": 1, "Place": 2, "PlaceOrdinal": "2nd"}]
        result, annotations = awards.compute(rows, playoffs, None)
        clutch = next(a for a in result if a["Name"] == "Clutch Peaker")
        self.assertEqual("Special", clutch["Type"]["Name"])
        self.assertEqual(3, clutch["TeamID"])
        self.assertEqual("Regular Season: 3rd | Playoffs: 1st", clutch["StatDisplay"])
        self.assertEqual(2 - 0.01, annotations[3]["ClutchPeakerScore"])  # +2 places, minus 0.01 * playoff place
        self.assertEqual(-999, annotations[2]["ClutchPeakerScore"])  # outside the playoffs

    def test_most_improved_needs_the_previous_season(self):
        rows = self.rows()
        previous = {"RegularSeason": [
            {"TeamID": 1, "WinPercentage": 0.6667, "PointsPerGame": 100.17, "Wins": 2, "Points": 300.5},
            {"TeamID": 2, "WinPercentage": 0.9, "PointsPerGame": 90.0, "Wins": 5, "Points": 800.0},
        ]}
        result, annotations = awards.compute(rows, [], previous)
        improved = result[-1]
        self.assertEqual("Most Improved", improved["Name"])
        # team 1 repeats its previous values (score 0.0), team 3 has no previous row (score 0): the first team in table order wins
        self.assertEqual(1, improved["TeamID"])
        self.assertEqual("Wins: 2 to 2 | Points: 300.5 to 300.5", improved["StatDisplay"])
        self.assertEqual(0, annotations[3]["ImprovementScore"])
        self.assertEqual(-0.3667, annotations[2]["ImprovementScore"])  # (0.5 - 0.9) + (93.33 - 90.0) * 0.01

    def test_previous_season_teams_are_matched_by_string_key(self):
        rows = self.rows()
        previous = {"RegularSeason": [{"TeamID": "1", "WinPercentage": 0.0, "PointsPerGame": 0.0, "Wins": 0, "Points": 0.0}]}
        result, annotations = awards.compute(rows, [], previous)
        self.assertEqual(1, result[-1]["TeamID"])
        self.assertGreater(annotations[1]["ImprovementScore"], 0)

    def test_inputs_are_not_mutated(self):
        rows = self.rows()
        before = copy.deepcopy(rows)
        awards.compute(rows, [{"TeamID": 1, "Place": 1, "PlaceOrdinal": "1st"}], {"RegularSeason": []})
        self.assertEqual(before, rows)


class StandingsOwnershipGuardTests(unittest.TestCase):
    """#1263: retired PowerShell standings models must not return as parallel production owners."""

    DEFINITION = re.compile(r"(?im)^\s*function\s+(Get-(?:WinPct|RankedRegularSeasonStandings|OutputStandingsForAllTime))\b")
    CALL = re.compile(r"(?i)\b(Get-(?:WinPct|RankedRegularSeasonStandings|OutputStandingsForAllTime))\b")

    @classmethod
    def find_legacy_references(cls, source: str) -> list[str]:
        return cls.CALL.findall("\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        ))

    def test_production_powershell_contains_no_retired_standings_models_or_calls(self):
        root = TOOLS.parent / "public" / "requests"
        offenders = []
        for extension in ("*.ps1", "*.psm1"):
            for path in root.rglob(extension):
                references = self.find_legacy_references(path.read_text(encoding="utf-8-sig"))
                if references:
                    offenders.append(f"{path.relative_to(TOOLS.parent)}: {references}")
        self.assertEqual([], offenders, "\n".join(offenders))

    def test_guard_detects_a_reintroduced_function_and_call(self):
        injected = "function Get-RankedRegularSeasonStandings { }\nGet-OutputStandingsForAllTime\n"
        self.assertEqual(
            ["Get-RankedRegularSeasonStandings", "Get-OutputStandingsForAllTime"],
            self.find_legacy_references(injected),
        )
        self.assertEqual(["Get-RankedRegularSeasonStandings"], self.DEFINITION.findall(injected))


if __name__ == "__main__":
    unittest.main()
