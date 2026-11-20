"""playoff-odds-v1: exact 50/50 enumeration, dynamic league size, tie sharing, strict status (Issue #1588)."""
from __future__ import annotations

import itertools
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models.playoff_odds import v1  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402


def teams(n, records=None):
    records = records or [(0, 0, 0)] * n
    return [{"CanonicalLeagueRosterID": f"r{i}", "TeamID": i + 1, "Wins": w, "Losses": l, "Ties": t,
             "Points": 100.0 + i, "PointsAgainst": 90.0 + i} for i, (w, l, t) in enumerate(records)]


def round_robin(n, weeks):
    ids = [f"r{i}" for i in range(n)]
    games = []
    for week in range(weeks):
        rot = ids[:1] + ids[1:][week % (n - 1):] + ids[1:][:week % (n - 1)]
        games += [(rot[i], rot[n - 1 - i]) for i in range(n // 2)]
    return games


def brute(team_list, games, cut):
    n = len(team_list)
    start = [2 * t["Wins"] + t["Ties"] for t in team_list]
    places = [[Fraction(0)] * n for _ in range(n)]
    total = 2 ** len(games)
    best, worst = [n + 1] * n, [0] * n
    for outcome in itertools.product((0, 1), repeat=len(games)):
        score = list(start)
        for (a, b), o in zip(games, outcome):
            score[int(a[1:]) if o == 0 else int(b[1:])] += 2
        for i in range(n):
            better = sum(s > score[i] for s in score)
            equal = sum(s == score[i] for j, s in enumerate(score) if j != i)
            best[i], worst[i] = min(best[i], better + 1), max(worst[i], better + equal + 1)
            for p in range(better, better + equal + 1):
                places[i][p] += Fraction(1, total * (equal + 1))
    return places, best, worst


class ExactnessTests(unittest.TestCase):
    def check_against_brute_force(self, n, weeks, cut, records=None):
        team_list = teams(n, records)
        games = round_robin(n, weeks)
        result = v1.compute(teams=team_list, open_games=games, playoff_teams=cut, regular_season_complete=False)
        places, best, worst = brute(team_list, games, cut)
        for i, row in enumerate(result["Teams"]):
            for p in range(n):
                self.assertAlmostEqual(float(places[i][p]), row["PlaceProbabilities"][p], places=9)
            self.assertAlmostEqual(float(sum(places[i][:cut])), row["PlayoffProbability"], places=9)
            self.assertAlmostEqual(1.0, row["PlayoffProbability"] + row["EliminationProbability"], places=9)
            expected = "clinched" if worst[i] <= cut else "eliminated" if best[i] > cut else "alive"
            self.assertEqual(expected, row["Status"])
        return result

    def test_matches_brute_force_for_several_league_shapes(self):
        for n, weeks, cut in ((4, 3, 2), (6, 2, 4), (8, 1, 6), (5, 2, 3), (4, 3, 1)):
            with self.subTest(teams=n, weeks=weeks, cut=cut):
                self.check_against_brute_force(n, weeks, cut)

    def test_uneven_records_and_ties_match_brute_force(self):
        self.check_against_brute_force(6, 2, 4, [(3, 0, 0), (2, 1, 0), (2, 0, 1), (1, 2, 0), (0, 3, 0), (1, 1, 1)])

    def test_sums_per_team_and_per_place(self):
        result = v1.compute(teams=teams(6), open_games=round_robin(6, 4), playoff_teams=4, regular_season_complete=False)
        for row in result["Teams"]:
            self.assertEqual(6, len(row["PlaceProbabilities"]))
            self.assertAlmostEqual(1.0, sum(row["PlaceProbabilities"]), places=8)
        for place in range(6):
            self.assertAlmostEqual(1.0, sum(r["PlaceProbabilities"][place] for r in result["Teams"]), places=8)
        self.assertAlmostEqual(4.0, sum(r["PlayoffProbability"] for r in result["Teams"]), places=8)

    def test_symmetric_start_shares_everything_equally(self):
        result = v1.compute(teams=teams(4), open_games=round_robin(4, 3), playoff_teams=2, regular_season_complete=False)
        for row in result["Teams"]:
            self.assertAlmostEqual(0.5, row["PlayoffProbability"], places=9)
            self.assertEqual("alive", row["Status"])


class StatusTests(unittest.TestCase):
    def test_clinched_and_eliminated_are_strict(self):
        # r0 leads by more than the remaining games; r3 cannot catch the cut even with all tiebreaks won.
        result = v1.compute(teams=teams(4, [(5, 0, 0), (2, 3, 0), (2, 3, 0), (0, 5, 0)]),
                            open_games=[("r0", "r1"), ("r2", "r3")], playoff_teams=2, regular_season_complete=False)
        status = {r["CanonicalLeagueRosterID"]: r["Status"] for r in result["Teams"]}
        self.assertEqual("clinched", status["r0"])
        self.assertEqual("eliminated", status["r3"])
        self.assertEqual({"alive"}, {status["r1"], status["r2"]})

    def test_a_possible_tiebreak_loss_prevents_clinching(self):
        # r1 can only miss the cut through a tie with r2 on record: that is not clinched.
        result = v1.compute(teams=teams(3, [(3, 0, 0), (2, 1, 0), (1, 2, 0)]),
                            open_games=[("r1", "r2")], playoff_teams=2, regular_season_complete=False)
        row = {r["CanonicalLeagueRosterID"]: r for r in result["Teams"]}
        self.assertEqual("clinched", row["r0"]["Status"])
        self.assertEqual("alive", row["r1"]["Status"])
        self.assertEqual("alive", row["r2"]["Status"])

    def test_zero_open_games_with_open_season_is_deterministic_without_points(self):
        result = v1.compute(teams=teams(4, [(3, 0, 0), (2, 1, 0), (1, 2, 0), (0, 3, 0)]), open_games=[],
                            playoff_teams=2, regular_season_complete=False)
        self.assertEqual(["clinched", "clinched", "eliminated", "eliminated"], [r["Status"] for r in result["Teams"]])
        self.assertEqual(1, int(result["Provenance"]["OutcomeCount"]))

    def test_playoff_size_covering_everyone_clinches_all(self):
        result = v1.compute(teams=teams(4), open_games=round_robin(4, 2), playoff_teams=9, regular_season_complete=False)
        self.assertEqual({"clinched"}, {r["Status"] for r in result["Teams"]})


class CompleteSeasonTests(unittest.TestCase):
    def test_official_table_decides_with_points_tiebreak(self):
        t = teams(4, [(3, 0, 0), (2, 1, 0), (2, 1, 0), (0, 3, 0)])
        t[1]["Points"], t[2]["Points"] = 50.0, 60.0
        result = v1.compute(teams=t, open_games=[], playoff_teams=2, regular_season_complete=True)
        row = {r["CanonicalLeagueRosterID"]: r for r in result["Teams"]}
        self.assertEqual("clinched", row["r2"]["Status"])
        self.assertEqual("eliminated", row["r1"]["Status"])
        self.assertEqual(1.0, row["r2"]["PlaceProbabilities"][1])
        self.assertEqual(0.0, row["r1"]["PlayoffProbability"])
        self.assertEqual(1.0, row["r1"]["EliminationProbability"])

    def test_complete_season_rejects_open_games(self):
        with self.assertRaises(v1.PlayoffOddsError):
            v1.compute(teams=teams(2), open_games=[("r0", "r1")], playoff_teams=1, regular_season_complete=True)


class FailClosedTests(unittest.TestCase):
    def test_unknown_playoff_size_is_unavailable_not_guessed(self):
        for bad in (None, 0, "4", True):
            result = v1.compute(teams=teams(4), open_games=round_robin(4, 1), playoff_teams=bad, regular_season_complete=False)
            self.assertFalse(result["Available"])
            self.assertIsNone(result["Teams"][0]["PlayoffProbability"])

    def test_state_limit_is_unavailable_never_approximated(self):
        with mock.patch.object(v1, "MAX_STATES", 3):
            result = v1.compute(teams=teams(6), open_games=round_robin(6, 3), playoff_teams=4, regular_season_complete=False)
        self.assertFalse(result["Available"])
        self.assertEqual("state-limit-exceeded", result["Reason"])
        self.assertIsNone(result["Teams"][0]["PlaceProbabilities"])

    def test_malformed_input_raises(self):
        with self.assertRaises(v1.PlayoffOddsError):
            v1.compute(teams=teams(4, [(1, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]), open_games=[], playoff_teams=2,
                       regular_season_complete=False)
        with self.assertRaises(v1.PlayoffOddsError):
            v1.compute(teams=teams(2), open_games=[("r0", "zz")], playoff_teams=1, regular_season_complete=False)

    def test_registered_with_its_kind(self):
        self.assertIs(v1, get_model("playoff-odds-v1", kind="playoff-odds"))


if __name__ == "__main__":
    unittest.main()
