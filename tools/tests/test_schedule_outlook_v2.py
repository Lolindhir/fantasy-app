"""Fast tests of schedule-outlook-v2 (Issue #1589): fact-based strength blend and remaining schedule.

Constructed leagues only; no hard-wired real teams or seasons.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.schedule_outlook import v1, v2  # noqa: E402

R = ["r1", "r2", "r3", "r4"]
TEAMS = [{"TeamID": i + 1, "CanonicalLeagueRosterID": r} for i, r in enumerate(R)]


def game(i, a, b):
    return {"CanonicalLeagueMatchupID": f"m{i}", "Team1CanonicalLeagueRosterID": a, "Team2CanonicalLeagueRosterID": b}


PAIRINGS = {
    1: [game(1, "r1", "r2"), game(2, "r3", "r4")],
    2: [game(3, "r1", "r3"), game(4, "r2", "r4")],
    3: [game(5, "r1", "r4"), game(6, "r2", "r3")],
}


def run(after_week, current=None, previous=None, k=None):
    cur = {r: {"RelativeScoringStrength": v} for r, v in (current or {}).items()}
    return v2.compute_regular_season(
        teams=TEAMS, pairings_by_week=PAIRINGS, strengths_by_roster=cur,
        previous_strength_by_roster=previous or {}, after_week=after_week, regular_season_last_week=3, k=k)


def team(result, rid):
    return next(t for t in result["Teams"] if t["CanonicalLeagueRosterID"] == rid)


PREV = {"r1": 1.2, "r2": 1.0, "r3": 0.9, "r4": 0.9}


class RegistryTests(unittest.TestCase):
    def test_registered_and_playoff_paths_are_v1_semantics(self):
        self.assertIs(registry.get_model("schedule-outlook-v2", kind="schedule-outlook"), v2)
        self.assertIs(v2.compute_playoff_paths, v1.compute_playoff_paths)
        self.assertEqual(3, v2.PARAMS["CurrentSeasonWeightK"])


class BlendTests(unittest.TestCase):
    def test_week_zero_uses_only_the_previous_season(self):
        t = team(run(0, previous=PREV), "r1")
        self.assertEqual(1.2, t["Strength"]["Value"])
        self.assertEqual(0.0, t["Strength"]["CurrentWeight"])
        self.assertIsNone(t["Strength"]["CurrentRelative"])

    def test_week_zero_without_previous_season_is_unknown_not_one(self):
        result = run(0)
        for t in result["Teams"]:
            self.assertIsNone(t["Strength"]["Value"])
            self.assertIsNone(t["RemainingSoS"])
            self.assertIsNone(t["RemainingSoSClass"])
            self.assertTrue(all(g["OpponentStrength"] is None and g["OpponentClass"] is None for g in t["Upcoming"]))

    def test_blend_weight_is_g_over_g_plus_k(self):
        current = {"r1": 1.5, "r2": 1.0, "r3": 0.8, "r4": 0.7}
        t = team(run(1, current=current, previous=PREV), "r1")
        self.assertEqual(0.25, t["Strength"]["CurrentWeight"])
        self.assertAlmostEqual(0.25 * 1.5 + 0.75 * 1.2, t["Strength"]["Value"], places=4)
        t3 = team(run(3, current=current, previous=PREV), "r1")  # g = 3 = k -> half and half
        self.assertEqual(0.5, t3["Strength"]["CurrentWeight"])
        self.assertAlmostEqual(1.35, t3["Strength"]["Value"], places=4)

    def test_k_is_a_parameter(self):
        current = {r: 1.0 for r in R}
        t = team(run(1, current=current, previous=PREV, k=1), "r1")
        self.assertEqual(0.5, t["Strength"]["CurrentWeight"])
        with self.assertRaises(v1.ScheduleOutlookError):
            run(1, current=current, previous=PREV, k=0)

    def test_without_previous_season_current_counts_alone_from_game_one(self):
        current = {"r1": 1.4, "r2": 1.0, "r3": 0.8, "r4": 0.8}
        t = team(run(1, current=current), "r1")
        self.assertEqual(1.4, t["Strength"]["Value"])
        self.assertEqual(1.0, t["Strength"]["CurrentWeight"])

    def test_team_new_in_the_league_has_only_current_strength(self):
        prev = {k: v for k, v in PREV.items() if k != "r4"}
        current = {r: 1.0 for r in R}
        self.assertEqual(1.0, team(run(1, current=current, previous=prev), "r4")["Strength"]["Value"])
        # at week 0 that team is unknown, which makes every remaining-schedule value unknown (fail closed)
        zero = run(0, previous=prev)
        self.assertIsNone(team(zero, "r4")["Strength"]["Value"])
        self.assertTrue(all(t["RemainingSoS"] is None for t in zero["Teams"]))


class RemainingScheduleTests(unittest.TestCase):
    def test_self_exclusion_uses_the_mean_of_the_other_teams(self):
        # strengths 1.2 / 1.0 / 0.9 / 0.9, week 0 (previous season only)
        result = run(0, previous=PREV)
        r1 = team(result, "r1")  # plays r2, r3, r4 = 1.0, 0.9, 0.9 -> mean 0.9333 against others mean 0.9333
        self.assertEqual(1.0, r1["RemainingSoS"])
        self.assertEqual("average", r1["RemainingSoSClass"])
        r4 = team(result, "r4")  # plays r3, r2, r1 = 0.9, 1.0, 1.2 -> 1.0333 against (1.2+1.0+0.9)/3 = 1.0333
        self.assertEqual(1.0, r4["RemainingSoS"])

    def test_double_round_robin_is_neutral_for_every_team(self):
        # in a full single round robin every team meets every other team once: always exactly 1.0
        for t in run(0, previous={"r1": 1.7, "r2": 0.4, "r3": 1.0, "r4": 0.9})["Teams"]:
            self.assertEqual(1.0, t["RemainingSoS"])

    def test_partial_schedule_and_classes(self):
        current = {"r1": 1.0, "r2": 1.3, "r3": 0.7, "r4": 1.0}
        result = run(1, current=current, previous={r: 1.0 for r in R}, k=1)  # weight 0.5
        # strengths: r1 1.0, r2 1.15, r3 0.85, r4 1.0
        r1 = team(result, "r1")  # remaining r3 (0.85), r4 (1.0)
        self.assertEqual("weaker", r1["Upcoming"][0]["OpponentClass"])  # 0.85
        self.assertEqual("similar", r1["Upcoming"][1]["OpponentClass"])  # 1.0
        others = (1.15 + 0.85 + 1.0) / 3
        self.assertAlmostEqual(round(((0.85 + 1.0) / 2) / others, 4), r1["RemainingSoS"], places=4)
        self.assertEqual("easier", r1["RemainingSoSClass"])

    def test_missing_opponent_strength_never_becomes_league_average(self):
        prev = {"r1": 1.0, "r2": 1.0, "r3": 1.0}  # r4 unknown at week 0
        result = run(0, previous=prev)
        for t in result["Teams"]:
            self.assertIsNone(t["RemainingSoS"])
        self.assertEqual(3, team(result, "r1")["RemainingGames"])

    def test_no_remaining_games_gives_null(self):
        result = run(3, current={r: 1.0 for r in R}, previous=PREV)
        for t in result["Teams"]:
            self.assertEqual(0, t["RemainingGames"])
            self.assertIsNone(t["RemainingSoS"])
            self.assertIsNotNone(t["Strength"]["Value"])

    def test_unknown_roster_in_strengths_fails_closed(self):
        with self.assertRaises(v1.ScheduleOutlookError):
            run(1, current={"zz": 1.0})
        with self.assertRaises(v1.ScheduleOutlookError):
            run(1, current={r: 1.0 for r in R}, previous={"zz": 1.0})

    def test_no_projection_inputs_are_read(self):
        current = {r: {"RelativeScoringStrength": 1.0, "ProjectedBestBallStrength": 999.0} for r in R}
        a = v2.compute_regular_season(teams=TEAMS, pairings_by_week=PAIRINGS, strengths_by_roster=current,
                                      previous_strength_by_roster=PREV, after_week=1, regular_season_last_week=3)
        b = run(1, current={r: 1.0 for r in R}, previous=PREV)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
