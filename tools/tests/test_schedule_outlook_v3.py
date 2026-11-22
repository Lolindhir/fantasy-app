"""Fast tests of schedule-outlook-v3 (Issue #1607): linear fade of the previous season.

Constructed leagues only; no hard-wired real teams or seasons.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.schedule_outlook import v1, v3  # noqa: E402

R = ["r1", "r2", "r3", "r4"]
TEAMS = [{"TeamID": i + 1, "CanonicalLeagueRosterID": r} for i, r in enumerate(R)]


def game(i, a, b):
    return {"CanonicalLeagueMatchupID": f"m{i}", "Team1CanonicalLeagueRosterID": a, "Team2CanonicalLeagueRosterID": b}


def pairings(weeks):
    out = {}
    for w in range(1, weeks + 1):
        out[w] = [game(w * 10, "r1", "r2"), game(w * 10 + 1, "r3", "r4")] if w % 2 else \
                 [game(w * 10, "r1", "r3"), game(w * 10 + 1, "r2", "r4")]
    return out


def run(after_week, weeks, current=None, previous=None):
    cur = {r: {"RelativeScoringStrength": v} for r, v in (current or {}).items()}
    return v3.compute_regular_season(
        teams=TEAMS, pairings_by_week={w: g for w, g in pairings(weeks).items() if w > after_week},
        strengths_by_roster=cur, previous_strength_by_roster=previous or {},
        after_week=after_week, regular_season_last_week=weeks)


def strength(result, rid="r1"):
    return next(t for t in result["Teams"] if t["CanonicalLeagueRosterID"] == rid)["Strength"]


CUR = {r: 0.8 for r in R}
PREV = {r: 1.2 for r in R}


class FadeTests(unittest.TestCase):
    def test_registered_with_v1_playoff_semantics(self):
        self.assertIs(registry.get_model("schedule-outlook-v3", kind="schedule-outlook"), v3)
        self.assertIs(v3.compute_playoff_paths, v1.compute_playoff_paths)

    def test_weight_is_linear_and_reaches_one_at_half_the_regular_season(self):
        self.assertEqual(0.0, v3.current_weight(0, 12))
        self.assertAlmostEqual(0.5, v3.current_weight(3, 12))
        self.assertEqual(1.0, v3.current_weight(6, 12))
        self.assertEqual(1.0, v3.current_weight(9, 12))

    def test_half_is_dynamic_in_the_regular_season_length(self):
        self.assertEqual(1.0, v3.current_weight(7, 14))
        self.assertLess(v3.current_weight(6, 14), 1.0)
        self.assertEqual(1.0, v3.current_weight(5, 10))

    def test_week_zero_is_the_previous_season_only(self):
        s = strength(run(0, 12, previous=PREV))
        self.assertEqual((1.2, 0.0), (s["Value"], s["CurrentWeight"]))

    def test_blend_in_between(self):
        s = strength(run(3, 12, current=CUR, previous=PREV))
        self.assertEqual(0.5, s["CurrentWeight"])
        self.assertAlmostEqual(1.0, s["Value"])

    def test_after_half_only_the_current_season_counts(self):
        s = strength(run(6, 12, current=CUR, previous=PREV))
        self.assertEqual((0.8, 1.0), (s["Value"], s["CurrentWeight"]))
        s = strength(run(7, 14, current=CUR, previous=PREV))
        self.assertEqual(0.8, s["Value"])
        self.assertLess(strength(run(6, 14, current=CUR, previous=PREV))["CurrentWeight"], 1.0)

    def test_no_previous_season_uses_current_alone_and_is_unknown_at_week_zero(self):
        self.assertEqual(0.8, strength(run(2, 12, current=CUR))["Value"])
        self.assertIsNone(strength(run(0, 12))["Value"])

    def test_params_are_reported(self):
        self.assertEqual(0.5, run(2, 12, current=CUR)["StrengthParams"]["FadeFraction"])


if __name__ == "__main__":
    unittest.main()
