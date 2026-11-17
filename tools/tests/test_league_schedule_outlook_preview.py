"""Read-only canonical Outlook adapter: pair normalization, as-of ratings and repository smoke tests (#1519 I2)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import league_schedule_outlook_preview as preview  # noqa: E402


def rows():
    return [
        {"CanonicalLeagueMatchupID": "m2", "CanonicalLeagueRosterID": "r3", "Points": 400},
        {"CanonicalLeagueMatchupID": "m1", "CanonicalLeagueRosterID": "r2", "PlayerPoints": [999]},
        {"CanonicalLeagueMatchupID": "m1", "CanonicalLeagueRosterID": "r1", "WinnerCanonicalLeagueRosterID": "r1"},
        {"CanonicalLeagueMatchupID": "m2", "CanonicalLeagueRosterID": "r4", "Starters": [1, 2]},
    ]


class PreviewAdapterTests(unittest.TestCase):
    def test_pairing_normalization_strips_every_future_result_and_is_order_invariant(self):
        selected = preview.normalize_week_pairings(rows(), week=10, canonical_rosters={"r1", "r2", "r3", "r4"})
        self.assertEqual([
            {"CanonicalLeagueMatchupID": "m1", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r2"},
            {"CanonicalLeagueMatchupID": "m2", "Team1CanonicalLeagueRosterID": "r3", "Team2CanonicalLeagueRosterID": "r4"},
        ], selected)
        reversed_rows = list(reversed(rows()))
        reversed_rows[0]["Points"] = 0
        self.assertEqual(selected, preview.normalize_week_pairings(reversed_rows, week=10, canonical_rosters={"r1", "r2", "r3", "r4"}))

    def test_missing_or_duplicate_canonical_participant_fails_closed(self):
        for value in (rows()[:-1], rows() + [rows()[0]]):
            with self.subTest(size=len(value)), self.assertRaises(preview.ScheduleOutlookSourceError):
                preview.normalize_week_pairings(value, week=10, canonical_rosters={"r1", "r2", "r3", "r4"})
        invalid = copy.deepcopy(rows())
        invalid[-1]["CanonicalLeagueMatchupID"] = None
        with self.assertRaises(preview.ScheduleOutlookSourceError):
            preview.normalize_week_pairings(invalid, week=10, canonical_rosters={"r1", "r2", "r3", "r4"})

    def test_malformed_bracket_or_triple_match_fails_closed(self):
        invalid = rows()
        invalid[0]["CanonicalLeagueMatchupID"] = "m1"
        with self.assertRaisesRegex(preview.ScheduleOutlookSourceError, "exactly two"):
            preview.normalize_week_pairings(invalid, week=10, canonical_rosters={"r1", "r2", "r3", "r4"})

    def test_weekly_rating_cutoff_is_explicit_and_joins_by_teamid(self):
        teams = [{"TeamID": 2, "CanonicalLeagueRosterID": "r2"}, {"TeamID": 1, "CanonicalLeagueRosterID": "r1"}]
        stats = {"AsOf": {"CompletedWeeks": 1}, "Weeks": [{"Week": 1, "Teams": [
            {"TeamID": 1, "RelativeScoringStrength": 0.9, "ProjectedBestBallStrength": 120},
            {"TeamID": 2, "RelativeScoringStrength": 1.1, "ProjectedBestBallStrength": None},
        ]}]}
        self.assertEqual({}, preview.ratings_for_week(stats, teams, rating_week=0))
        result = preview.ratings_for_week(stats, teams, rating_week=1)
        self.assertEqual({"RelativeScoringStrength": 1.1, "ProjectedBestBallStrength": None}, result["r2"])
        with self.assertRaisesRegex(preview.ScheduleOutlookSourceError, "not final"):
            preview.ratings_for_week(stats, teams, rating_week=2)
        stats["Weeks"][0]["Teams"].pop()
        with self.assertRaisesRegex(preview.ScheduleOutlookSourceError, "coverage mismatch"):
            preview.ratings_for_week(stats, teams, rating_week=1)

    def test_repository_2025_after_week_6_has_seven_future_games_per_team(self):
        result = preview.preview(TOOLS.parent, "nfl-reise", 2025, 6)
        self.assertTrue(result["PreviewOnly"])
        self.assertEqual({"AfterWeek": 6, "RatingWeek": 6}, result["AsOf"])
        self.assertEqual(21, len(result["RegularSeason"]["UpcomingMatchups"]))
        self.assertEqual(6, len(result["RegularSeason"]["Teams"]))
        self.assertTrue(all(t["RemainingGames"] == 7 for t in result["RegularSeason"]["Teams"]))
        self.assertTrue(all(t["KnownRelativeScoringStrengthGames"] == 7 for t in result["RegularSeason"]["Teams"]))
        self.assertEqual("season-stats-v1", result["Models"]["SeasonStats"])

    def test_repository_2026_after_week_10_has_three_future_games_per_team(self):
        result = preview.preview(TOOLS.parent, "nfl-reise", 2026, 10)
        self.assertEqual(9, len(result["RegularSeason"]["UpcomingMatchups"]))
        self.assertTrue(all(t["RemainingGames"] == 3 for t in result["RegularSeason"]["Teams"]))
        self.assertEqual("schedule-outlook-v1", result["Models"]["ScheduleOutlook"])
        with self.assertRaisesRegex(preview.ScheduleOutlookSourceError, "not LeagueScored final"):
            preview.preview(TOOLS.parent, "nfl-reise", 2026, 11)

    def test_repository_2025_week_0_does_not_need_a_stats_snapshot(self):
        result = preview.preview(TOOLS.parent, "nfl-reise", 2025, 0)
        self.assertEqual(39, len(result["RegularSeason"]["UpcomingMatchups"]))
        self.assertIsNone(result["Models"]["SeasonStats"])
        self.assertTrue(all(t["RemainingSoSRelativeStrength"] is None for t in result["RegularSeason"]["Teams"]))

    def test_repository_2025_playoff_week_has_no_regular_season_opponents(self):
        result = preview.preview(TOOLS.parent, "nfl-reise", 2025, 15)
        self.assertEqual([], result["RegularSeason"]["UpcomingMatchups"])
        self.assertEqual(13, result["RegularSeason"]["RatingWeek"])
        self.assertTrue(all(t["RemainingGames"] == 0 for t in result["RegularSeason"]["Teams"]))


if __name__ == "__main__":
    unittest.main()
