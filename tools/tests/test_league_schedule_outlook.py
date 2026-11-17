"""Fast regression tests of the read-only schedule-outlook-v1 model (Issue #1519, I1).

The source adapter and playoff routes are deliberately separate follow-up checkpoints.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.schedule_outlook import v1  # noqa: E402


def teams(n=4):
    return [{"TeamID": i, "CanonicalLeagueRosterID": f"r{i}"} for i in range(1, n + 1)]


def weeks():
    return {
        11: [
            {"CanonicalLeagueMatchupID": "m11a", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r2"},
            {"CanonicalLeagueMatchupID": "m11b", "Team1CanonicalLeagueRosterID": "r3", "Team2CanonicalLeagueRosterID": "r4"},
        ],
        12: [
            {"CanonicalLeagueMatchupID": "m12a", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r2"},
            {"CanonicalLeagueMatchupID": "m12b", "Team1CanonicalLeagueRosterID": "r3", "Team2CanonicalLeagueRosterID": "r4"},
        ],
    }


def strengths():
    return {
        f"r{i}": {"RelativeScoringStrength": 0.8 + i * .1,
                 "ProjectedBestBallStrength": 120.0 + i * 10.0}
        for i in range(1, 5)
    }


def compute(after=10, end=12, pairings=None, ratings=None):
    return v1.compute_regular_season(
        teams=teams(), pairings_by_week=weeks() if pairings is None else pairings,
        strengths_by_roster=strengths() if ratings is None and after > 0 else (ratings or {}),
        after_week=after, regular_season_last_week=end,
    )


class ScheduleOutlookV1Tests(unittest.TestCase):
    def test_registered_immutable_model_parameters(self):
        self.assertIs(registry.get_model("schedule-outlook-v1", kind="schedule-outlook"), v1)
        self.assertEqual({"Digits": 4, "RemainingSoS": "arithmetic-mean-per-opponent-game",
                          "Ranking": "competition-ascending-on-complete-coverage",
                          "ZeroRemainingGames": "null"}, dict(v1.PARAMS))
        with self.assertRaises(TypeError):
            v1.PARAMS["Digits"] = 5

    def test_upcoming_games_and_separate_sos_metrics(self):
        result = compute()
        self.assertEqual(4, len(result["UpcomingMatchups"]))
        self.assertEqual({"AfterWeek": 10, "RatingWeek": 10}, {k: result[k] for k in ("AfterWeek", "RatingWeek")})
        one = next(x for x in result["Teams"] if x["TeamID"] == 1)
        two = next(x for x in result["Teams"] if x["TeamID"] == 2)
        self.assertEqual(2, one["RemainingGames"])
        self.assertEqual([11, 12], [x["Week"] for x in one["Upcoming"]])
        self.assertEqual(["r2", "r2"], [x["OpponentCanonicalLeagueRosterID"] for x in one["Upcoming"]])
        self.assertEqual(1.0, one["RemainingSoSRelativeStrength"])
        self.assertEqual(140.0, one["RemainingOpponentBestBallStrength"])
        self.assertEqual(2, one["KnownRelativeScoringStrengthGames"])
        self.assertEqual(2, one["KnownProjectedBestBallStrengthGames"])
        self.assertEqual(2, one["RemainingSoSRelativeStrengthRank"])
        self.assertEqual(1, two["RemainingSoSRelativeStrengthRank"])

    def test_dynamic_team_ids_are_numerically_ordered(self):
        result = v1.compute_regular_season(
            teams=list(reversed(teams(12))),
            pairings_by_week={},
            strengths_by_roster={},
            after_week=1,
            regular_season_last_week=1,
        )
        self.assertEqual(list(range(1, 13)), [x["TeamID"] for x in result["Teams"]])
        invalid = [{"TeamID": "1", "CanonicalLeagueRosterID": "r1"}, teams()[1]]
        with self.assertRaisesRegex(v1.ScheduleOutlookError, "identity"):
            v1.compute_regular_season(
                teams=invalid, pairings_by_week={}, strengths_by_roster={},
                after_week=1, regular_season_last_week=1,
            )

    def test_week_zero_has_pairings_but_no_fake_strength(self):
        full = weeks()
        full.update({
            1: [
                {"CanonicalLeagueMatchupID": "m1", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r3"},
                {"CanonicalLeagueMatchupID": "m2", "Team1CanonicalLeagueRosterID": "r2", "Team2CanonicalLeagueRosterID": "r4"},
            ],
        })
        result = compute(after=0, end=1, pairings=full, ratings={})
        self.assertIsNone(result["RatingWeek"])
        self.assertEqual(2, len(result["UpcomingMatchups"]))
        self.assertTrue(all(x["RemainingSoSRelativeStrength"] is None and x["RemainingSoSRelativeStrengthRank"] is None
                            for x in result["Teams"]))
        with self.assertRaises(v1.ScheduleOutlookError):
            compute(after=0, end=1, pairings=full, ratings=strengths())

    def test_missing_one_rating_invalidates_only_that_metric_and_all_ranks(self):
        values = strengths()
        values["r2"]["ProjectedBestBallStrength"] = None
        result = compute(ratings=values)
        one = next(x for x in result["Teams"] if x["TeamID"] == 1)
        three = next(x for x in result["Teams"] if x["TeamID"] == 3)
        self.assertIsNone(one["RemainingOpponentBestBallStrength"])
        self.assertEqual(0, one["KnownProjectedBestBallStrengthGames"])
        self.assertIsNone(three["RemainingOpponentBestBallStrengthRank"])
        self.assertIsNotNone(one["RemainingSoSRelativeStrength"])
        self.assertIsNotNone(three["RemainingSoSRelativeStrengthRank"])

    def test_zero_remaining_games_is_not_a_zero_difficulty_score(self):
        result = compute(after=12, end=12)
        self.assertEqual([], result["UpcomingMatchups"])
        self.assertTrue(all(x["RemainingGames"] == 0 and x["RemainingSoSRelativeStrength"] is None
                            and x["RemainingSoSRelativeStrengthRank"] is None for x in result["Teams"]))
        self.assertEqual(12, result["RatingWeek"])

    def test_missing_week_fails_closed(self):
        with self.assertRaisesRegex(v1.ScheduleOutlookError, "Week 12"):
            compute(pairings={11: weeks()[11]})

    def test_duplicate_or_unknown_participant_fails_closed(self):
        p = weeks()
        p[11] = [p[11][0], p[11][0]]
        with self.assertRaisesRegex(v1.ScheduleOutlookError, "Duplicate"):
            compute(pairings=p)
        p = weeks()
        p[11] = copy.deepcopy(p[11])
        p[11][0]["Team2CanonicalLeagueRosterID"] = "missing"
        with self.assertRaisesRegex(v1.ScheduleOutlookError, "Invalid"):
            compute(pairings=p)

    def test_future_result_fields_ignored_entirely(self):
        baseline = compute()
        p = copy.deepcopy(weeks())
        p[11][0]["StarterPoints"] = [{"Points": 10000000}]
        p[11][0]["WinnerCanonicalLeagueRosterID"] = "r2"
        p[11][0]["ProjectedFinalScore"] = 777777.0
        self.assertEqual(baseline, compute(pairings=p))

    def test_output_deterministic_across_source_order(self):
        baseline = compute()
        p = {week: list(reversed(rows)) for week, rows in weeks().items()}
        result = compute(pairings=p)
        self.assertEqual(json.dumps(baseline, sort_keys=True), json.dumps(result, sort_keys=True))

    def test_unknown_numeric_data_not_silently_zero(self):
        s = strengths()
        s["r2"]["RelativeScoringStrength"] = float("nan")
        s["r4"]["ProjectedBestBallStrength"] = -1
        result = compute(ratings=s)
        one = next(x for x in result["Teams"] if x["TeamID"] == 1)
        three = next(x for x in result["Teams"] if x["TeamID"] == 3)
        self.assertIsNone(one["RemainingSoSRelativeStrength"])
        self.assertIsNone(three["RemainingOpponentBestBallStrength"])


if __name__ == "__main__":
    unittest.main()
