"""Tests for awards-v2 (Issue #506, ADR-082): Overperformer and Brick Wall from the season-statistics product.

Constructed teams only; no real team or season data is wired in.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.awards import v1, v2  # noqa: E402


def row(team_id, wins=5, losses=3):
    return {
        "TeamID": team_id, "Owner": f"o{team_id}", "TeamName": f"T{team_id}", "Place": team_id, "PlaceOrdinal": f"{team_id}th",
        "Wins": wins, "Losses": losses, "Ties": 0, "Record": "W" * wins + "L" * losses, "Points": 100.0 + team_id,
        "PointsPerGame": 12.5, "WinStreakScore": team_id, "LongestWinStreak": 2, "EfficiencyScore": 1, "IronWillScore": 1,
        "PointDifference": 3, "PointsAgainstPerGame": 10.0, "PointsAgainstPerGameDiffLeagueAvg": 1.0, "WinPercentage": 0.5,
    }


def stat(team_id, delta, games, wins, opponents):
    return {"TeamID": team_id, "ProjectionDelta": delta, "ProjectionGames": games,
            "AboveAverageOpponentWins": wins, "AboveAverageOpponents": opponents}


def award(awards, name):
    return next((a for a in awards if a["Name"] == name), None)


class AwardsV2Tests(unittest.TestCase):
    def test_registered_and_marked(self):
        self.assertIs(v2, registry.get_model("awards-v2", kind="awards"))
        self.assertTrue(v2.NEEDS_SEASON_STATISTICS)
        self.assertEqual("awards-v2", v2.MODEL_ID)
        self.assertFalse(getattr(v1, "NEEDS_SEASON_STATISTICS", False))

    def test_changed_awards_follow_the_statistics_and_the_rest_equals_v1(self):
        rows = [row(1), row(2), row(3)]
        stats = {"Teams": [stat(1, 1.0, 8, 1, 4), stat(2, 2.5, 8, 2, 4), stat(3, -1.0, 8, 3, 5)]}
        old, old_notes = v1.compute(rows, None, None)
        new, notes = v2.compute(rows, None, None, stats)
        self.assertEqual([a["Name"] for a in old], [a["Name"] for a in new])
        self.assertEqual(old_notes, notes)
        self.assertEqual(2, award(new, "Overperformer")["TeamID"])
        self.assertIn("+2.5", award(new, "Overperformer")["StatDisplay"])
        self.assertEqual(3, award(new, "Brick Wall")["TeamID"])
        self.assertIn("3 of 5", award(new, "Brick Wall")["StatDisplay"])
        for name in ("Best Performer", "Streaker"):
            self.assertEqual(award(old, name), award(new, name))

    def test_brick_wall_tie_goes_to_higher_quota_then_table_order(self):
        rows = [row(1), row(2), row(3)]
        quota = {"Teams": [stat(1, 0.0, 8, 3, 6), stat(2, 0.0, 8, 3, 4), stat(3, 0.0, 8, 3, 4)]}
        self.assertEqual(2, award(v2.compute(rows, None, None, quota)[0], "Brick Wall")["TeamID"])

    def test_overperformer_tie_goes_to_first_in_table_order(self):
        rows = [row(1), row(2)]
        stats = {"Teams": [stat(1, 1.5, 8, 1, 4), stat(2, 1.5, 8, 1, 4)]}
        self.assertEqual(1, award(v2.compute(rows, None, None, stats)[0], "Overperformer")["TeamID"])

    def test_missing_or_ineligible_evidence_omits_the_award(self):
        rows = [row(1), row(2)]
        for stats in (None, {"Teams": []}, {"Teams": [stat(1, None, 0, 0, 0), stat(2, 3.0, 0, 0, 0)]}):
            awards, _ = v2.compute(rows, None, None, stats)
            self.assertIsNone(award(awards, "Overperformer"))
            self.assertIsNone(award(awards, "Brick Wall"))
            self.assertIsNotNone(award(awards, "Best Performer"))

    def test_no_completed_game_gives_no_awards(self):
        self.assertEqual(([], {}), v2.compute([row(1, 0, 0)], None, None, {"Teams": [stat(1, 1.0, 1, 1, 1)]}))


if __name__ == "__main__":
    unittest.main()
