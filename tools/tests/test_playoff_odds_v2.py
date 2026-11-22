"""playoff-odds-v2: seeded strength-based playoff chances with the points tiebreak (Issue #1607).

Only constructed leagues; no real league data and no hard-wired numbers of a real season.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models.playoff_odds import v1, v2  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402
from derived_data_lib.models.schedule_outlook import v2 as outlook_v2  # noqa: E402


def make_teams(n, records=None, points=None):
    records = records or [(0, 0, 0)] * n
    return [{"CanonicalLeagueRosterID": f"r{i}", "TeamID": i + 1, "Wins": w, "Losses": l, "Ties": t,
             "Points": (points or [0.0] * n)[i], "PointsAgainst": 0.0} for i, (w, l, t) in enumerate(records)]


def round_robin(n, weeks):
    ids = [f"r{i}" for i in range(n)]
    games = []
    for week in range(weeks):
        rot = ids[:1] + ids[1:][week % (n - 1):] + ids[1:][:week % (n - 1)]
        games += [(rot[i], rot[n - 1 - i]) for i in range(n // 2)]
    return games


def history(n, weeks, base=100.0, step=10.0):
    """Scored team-games of a constructed league: team i scores around base + step * i, with a small deterministic wobble."""
    return {f"r{i}": [base + step * i + ((w * 7 + i * 3) % 11) - 5 for w in range(weeks)] for i in range(n)}


def run(n=6, weeks_open=3, weeks_played=3, cut=4, strengths=None, records=None, previous=(), points=None):
    hist = history(n, weeks_played)
    teams = make_teams(n, records or [(weeks_played // 2, weeks_played - weeks_played // 2, 0)] * n,
                       [sum(hist[f"r{i}"]) for i in range(n)] if points is None else points)
    games = round_robin(n, weeks_open)
    upcoming = [{"Week": 1 + k // (n // 2), "CanonicalLeagueMatchupID": f"m{k}"} for k, _ in enumerate(games)]
    return v2.compute(teams=teams, open_games=games, playoff_teams=cut, regular_season_complete=False,
                      strength_by_roster=strengths or {}, points_by_roster=hist, previous_points=previous,
                      upcoming_matchups=upcoming)


class DeterminismTests(unittest.TestCase):
    def test_same_inputs_give_byte_identical_output(self):
        strengths = {f"r{i}": 0.8 + 0.08 * i for i in range(6)}
        self.assertEqual(run(strengths=strengths), run(strengths=copy.deepcopy(strengths)))

    def test_registered_and_selectable(self):
        self.assertIs(v2, get_model("playoff-odds-v2", kind="playoff-odds"))
        self.assertTrue(v2.USES_STRENGTH)


class StrengthTests(unittest.TestCase):
    def test_stronger_team_has_better_chances_and_the_value_flows_through(self):
        weak = run(strengths={f"r{i}": 1.0 for i in range(6)})
        strong_r0 = run(strengths={**{f"r{i}": 1.0 for i in range(6)}, "r0": 1.4})
        self.assertGreater(strong_r0["Teams"][0]["PlayoffProbability"], weak["Teams"][0]["PlayoffProbability"])
        self.assertEqual("outlook-strength", strong_r0["Provenance"]["StrengthBasis"])
        # no code or parameter change besides the strength value changed the result
        self.assertNotEqual(weak["Teams"][0]["PlaceProbabilities"], strong_r0["Teams"][0]["PlaceProbabilities"])

    def test_win_probability_follows_the_strength_gap(self):
        result = run(strengths={"r0": 1.3, "r1": 0.7, **{f"r{i}": 1.0 for i in range(2, 6)}})
        game = next(g for g in result["Teams"][0]["Upcoming"] if g["OpponentCanonicalLeagueRosterID"] == "r1")
        mirror = next(g for g in result["Teams"][1]["Upcoming"] if g["OpponentCanonicalLeagueRosterID"] == "r0")
        self.assertGreater(game["WinProbability"], 0.5)
        self.assertAlmostEqual(1.0, game["WinProbability"] + mirror["WinProbability"], places=3)
        self.assertGreater(game["ExpectedMargin"], 0)
        self.assertAlmostEqual(0.0, game["ExpectedMargin"] + mirror["ExpectedMargin"], places=3)

    def test_remaining_schedule_accumulates_the_game_win_chances(self):
        result = run(strengths={"r0": 1.3, "r1": 0.7, **{f"r{i}": 1.0 for i in range(2, 6)}})
        for team in result["Teams"]:
            chances = [g["WinProbability"] for g in team["Upcoming"]]
            self.assertAlmostEqual(sum(chances), team["RemainingExpectedWins"], places=3)
            self.assertAlmostEqual(sum(chances) / len(chances), team["RemainingWinProbability"], places=3)

    def test_unknown_strength_treats_every_team_equal_and_says_so(self):
        result = run(strengths={"r0": 1.2})  # five teams unknown
        self.assertEqual("equal-unknown", result["Provenance"]["StrengthBasis"])
        self.assertEqual("strength-unknown", result["Provenance"]["StrengthReason"])
        for team in result["Teams"]:
            self.assertEqual(0.5, team["Upcoming"][0]["WinProbability"])
            self.assertEqual(0.0, team["Upcoming"][0]["ExpectedMargin"])

    def test_no_scores_anywhere_is_equal_unknown_without_invented_numbers(self):
        teams = make_teams(4)
        result = v2.compute(teams=teams, open_games=round_robin(4, 2), playoff_teams=2, regular_season_complete=False,
                            strength_by_roster={}, points_by_roster={}, previous_points=(), upcoming_matchups=None)
        self.assertEqual("no-scored-games", result["Provenance"]["StrengthReason"])
        self.assertIsNone(result["Scoring"]["LeagueMeanPoints"])
        self.assertIsNone(result["Scoring"]["PointsStdDev"])
        for row in result["Teams"]:
            self.assertAlmostEqual(0.5, row["PlayoffProbability"], delta=0.03)  # symmetric league: 2 of 4 reach the playoffs

    def test_previous_season_supplies_mean_and_spread_before_the_first_game(self):
        previous = [90.0 + (i * 13) % 40 for i in range(48)]
        teams = make_teams(4)
        result = v2.compute(teams=teams, open_games=round_robin(4, 2), playoff_teams=2, regular_season_complete=False,
                            strength_by_roster={f"r{i}": 1.0 + 0.1 * i for i in range(4)}, points_by_roster={},
                            previous_points=previous)
        self.assertEqual("previous-season", result["Scoring"]["MeanSource"])
        self.assertEqual("outlook-strength", result["Provenance"]["StrengthBasis"])
        self.assertGreater(result["Scoring"]["PointsStdDev"], 0)

    def test_mean_and_spread_come_from_the_data_not_from_constants(self):
        low, high = run(strengths={f"r{i}": 1.0 for i in range(6)}), None
        hist = {k: [v * 2 for v in vals] for k, vals in history(6, 3).items()}
        teams = make_teams(6, [(1, 2, 0)] * 6, [sum(hist[f"r{i}"]) for i in range(6)])
        high = v2.compute(teams=teams, open_games=round_robin(6, 3), playoff_teams=4, regular_season_complete=False,
                          strength_by_roster={f"r{i}": 1.0 for i in range(6)}, points_by_roster=hist)
        self.assertAlmostEqual(2 * low["Scoring"]["LeagueMeanPoints"], high["Scoring"]["LeagueMeanPoints"], places=3)
        self.assertAlmostEqual(2 * low["Scoring"]["PointsStdDev"], high["Scoring"]["PointsStdDev"], places=3)


class TiebreakAndStatusTests(unittest.TestCase):
    def test_points_break_equal_records(self):
        """Two teams with the same record: the one with more points reaches the playoffs more often (v1 shared the places)."""
        records = [(2, 1, 0)] * 4
        teams = make_teams(4, records, [400.0, 300.0, 350.0, 250.0])
        hist = {f"r{i}": [100.0] * 3 for i in range(4)}
        result = v2.compute(teams=teams, open_games=[], playoff_teams=2, regular_season_complete=False,
                            strength_by_roster={f"r{i}": 1.0 for i in range(4)}, points_by_roster=hist)
        by = {r["CanonicalLeagueRosterID"]: r for r in result["Teams"]}
        self.assertEqual(1.0, by["r0"]["PlayoffProbability"])
        self.assertEqual(1.0, by["r2"]["PlayoffProbability"])
        self.assertEqual(0.0, by["r1"]["PlayoffProbability"])
        # status stays strictly mathematical: with no game left the records alone tie, so nobody has clinched or is eliminated
        self.assertTrue(all(r["Status"] == "alive" for r in result["Teams"]))
        shared = v1.compute(teams=make_teams(4, records), open_games=[], playoff_teams=2, regular_season_complete=False)
        self.assertAlmostEqual(0.5, shared["Teams"][0]["PlayoffProbability"])

    def test_strict_status_matches_v1_for_every_shape(self):
        for n, weeks, cut in ((4, 3, 2), (6, 2, 4), (8, 1, 6), (5, 2, 3)):
            with self.subTest(teams=n, weeks=weeks, cut=cut):
                records = [(1, 0, 0)] + [(0, 1, 0)] * (n - 1)
                games = round_robin(n, weeks)
                one = v1.compute(teams=[{**t, "Points": 0.0, "PointsAgainst": 0.0} for t in make_teams(n, records)],
                                 open_games=games, playoff_teams=cut, regular_season_complete=False)
                two = v2.compute(teams=make_teams(n, records), open_games=games, playoff_teams=cut, regular_season_complete=False,
                                 strength_by_roster={f"r{i}": 1.0 for i in range(n)}, points_by_roster={f"r{i}": [100.0] for i in range(n)})
                self.assertEqual([t["Status"] for t in one["Teams"]], [t["Status"] for t in two["Teams"]])

    def test_clinched_and_eliminated_are_mathematical_not_probabilistic(self):
        records = [(5, 0, 0), (0, 5, 0), (3, 2, 0), (2, 3, 0)]
        result = v2.compute(teams=make_teams(4, records), open_games=[("r2", "r3")], playoff_teams=2,
                            regular_season_complete=False, strength_by_roster={"r0": 0.1, "r1": 5.0, "r2": 1.0, "r3": 1.0},
                            points_by_roster={f"r{i}": [100.0] for i in range(4)})
        statuses = {r["CanonicalLeagueRosterID"]: r["Status"] for r in result["Teams"]}
        self.assertEqual("clinched", statuses["r0"])  # even a hugely weak team keeps the clinch
        self.assertEqual("eliminated", statuses["r1"])  # even a hugely strong team stays eliminated

    def test_complete_season_uses_the_official_table(self):
        teams = make_teams(4, [(3, 0, 0), (2, 1, 0), (2, 1, 0), (0, 3, 0)], [300.0, 280.0, 310.0, 200.0])
        result = v2.compute(teams=teams, open_games=[], playoff_teams=3, regular_season_complete=True)
        probabilities = {r["CanonicalLeagueRosterID"]: r["PlayoffProbability"] for r in result["Teams"]}
        self.assertEqual({"r0": 1.0, "r1": 1.0, "r2": 1.0, "r3": 0.0}, probabilities)
        self.assertEqual("official-table", result["Provenance"]["Method"])
        self.assertEqual(["clinched"] * 3 + ["eliminated"], [r["Status"] for r in result["Teams"]])


class ShapeTests(unittest.TestCase):
    def test_sums_per_team_and_per_place_and_variable_league_size(self):
        for n, cut in ((4, 2), (6, 4), (8, 6), (5, 3)):
            with self.subTest(teams=n):
                result = run(n=n, cut=cut, strengths={f"r{i}": 0.9 + 0.05 * i for i in range(n)})
                for row in result["Teams"]:
                    self.assertEqual(n, len(row["PlaceProbabilities"]))
                    self.assertAlmostEqual(1.0, sum(row["PlaceProbabilities"]), places=2)
                for place in range(n):
                    self.assertAlmostEqual(1.0, sum(r["PlaceProbabilities"][place] for r in result["Teams"]), places=2)
                self.assertAlmostEqual(cut, sum(r["PlayoffProbability"] for r in result["Teams"]), places=2)

    def test_unknown_playoff_size_is_unavailable(self):
        teams = make_teams(4, [(1, 1, 0)] * 4)
        self.assertFalse(v2.compute(teams=teams, open_games=[], playoff_teams=None, regular_season_complete=False)["Available"])

    def test_invalid_pairing_and_unequal_games_fail_closed(self):
        teams = make_teams(4, [(1, 1, 0)] * 4)
        with self.assertRaises(v2.PlayoffOddsError):
            v2.compute(teams=teams, open_games=[("r0", "zz")], playoff_teams=2, regular_season_complete=False)
        with self.assertRaises(v2.PlayoffOddsError):
            v2.compute(teams=make_teams(4, [(1, 1, 0), (1, 0, 0), (1, 1, 0), (1, 1, 0)]), open_games=[], playoff_teams=2,
                       regular_season_complete=False)


class OutlookContractTests(unittest.TestCase):
    """The odds read RegularSeason.Teams[].Strength.Value; it must stay relative to the league average (1.0 = average)."""

    def test_outlook_v2_strength_is_relative_to_the_league_average(self):
        teams = [{"TeamID": i + 1, "CanonicalLeagueRosterID": f"r{i}"} for i in range(4)]
        pairings = {3: [{"CanonicalLeagueMatchupID": "a", "Team1CanonicalLeagueRosterID": "r0", "Team2CanonicalLeagueRosterID": "r1"},
                        {"CanonicalLeagueMatchupID": "b", "Team1CanonicalLeagueRosterID": "r2", "Team2CanonicalLeagueRosterID": "r3"}]}
        current = {f"r{i}": {"RelativeScoringStrength": value} for i, value in enumerate((1.2, 0.9, 1.0, 0.9))}  # mean 1.0
        previous = {f"r{i}": value for i, value in enumerate((1.1, 0.95, 1.0, 0.95))}  # mean 1.0
        block = outlook_v2.compute_regular_season(
            teams=teams, pairings_by_week=pairings, strengths_by_roster=current, previous_strength_by_roster=previous,
            after_week=2, regular_season_last_week=3)
        values = [t["Strength"]["Value"] for t in block["Teams"]]
        self.assertAlmostEqual(1.0, sum(values) / len(values), places=3)
        # the odds model consumes exactly these values, with no formula of its own
        odds = v2.compute(
            teams=make_teams(4, [(1, 1, 0)] * 4, [200.0] * 4), open_games=[("r0", "r1"), ("r2", "r3")], playoff_teams=2,
            regular_season_complete=False, strength_by_roster={t["CanonicalLeagueRosterID"]: t["Strength"]["Value"] for t in block["Teams"]},
            points_by_roster={f"r{i}": [100.0, 100.0] for i in range(4)}, upcoming_matchups=block["UpcomingMatchups"])
        self.assertEqual("outlook-strength", odds["Provenance"]["StrengthBasis"])


if __name__ == "__main__":
    unittest.main()
