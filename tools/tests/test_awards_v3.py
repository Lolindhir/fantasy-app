"""Tests for awards-v3 (Issue #1460): league-adjusted Overperformer and the richer Overperformer/Brick Wall display.

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
from derived_data_lib.models.awards import v1, v2, v3  # noqa: E402


def row(team_id, wins=5, losses=3, ties=0):
    return {
        "TeamID": team_id, "Owner": f"o{team_id}", "TeamName": f"T{team_id}", "Place": team_id, "PlaceOrdinal": f"{team_id}th",
        "Wins": wins, "Losses": losses, "Ties": ties, "Record": "W" * wins + "L" * losses + "T" * ties, "Points": 100.0 + team_id,
        "PointsPerGame": 12.5, "WinStreakScore": team_id, "LongestWinStreak": 2, "EfficiencyScore": 1, "IronWillScore": 1,
        "PointDifference": 3, "PointsAgainstPerGame": 10.0, "PointsAgainstPerGameDiffLeagueAvg": 1.0, "WinPercentage": 0.5,
    }


def game(delta, result="W", timing=0.0):
    return {"ProjectionDelta": delta, "Result": result, "OpponentTiming": timing}


def stat(team_id, log, wins=0, opponents=0):
    deltas = [g["ProjectionDelta"] for g in log if g["ProjectionDelta"] is not None]
    return {"TeamID": team_id, "ProjectionDelta": sum(deltas) / len(deltas) if deltas else None, "ProjectionGames": len(deltas),
            "AboveAverageOpponentWins": wins, "AboveAverageOpponents": opponents, "GameLog": log}


def award(awards, name):
    return next((a for a in awards if a["Name"] == name), None)


class AwardsV3Tests(unittest.TestCase):
    def test_registered_and_marked(self):
        self.assertIs(v3, registry.get_model("awards-v3", kind="awards"))
        self.assertTrue(v3.NEEDS_SEASON_STATISTICS)
        self.assertEqual("awards-v3", v3.MODEL_ID)

    def test_overperformer_is_league_adjusted_and_never_negative(self):
        # every team below its projection: awards-v2 would show a negative value for the winner
        rows = [row(1), row(2), row(3)]
        stats = {"Teams": [stat(1, [game(-10.0, "L"), game(-6.0)]), stat(2, [game(-2.0), game(4.0, "L")]), stat(3, [game(-9.0), game(-1.0)])]}
        old = award(v2.compute(rows, None, None, stats)[0], "Overperformer")
        new = award(v3.compute(rows, None, None, stats)[0], "Overperformer")
        self.assertEqual(old["TeamID"], new["TeamID"])  # same order as awards-v2
        self.assertEqual(2, new["TeamID"])
        # league mean -4.0, team 2 mean +1.0 -> +5.0
        self.assertEqual("vs. Projection: +5.0 per Game (League-Adjusted) | Beat Projection: 1 of 2 | Record: 5-3", new["StatDisplay"])

    def test_brick_wall_ranking_equals_v2_and_shows_the_surplus(self):
        rows = [row(1), row(2, 4, 3, 1)]
        log2 = [game(None, "W", 12.25), game(None, "W", 3.0), game(None, "L", 20.0), game(None, "W", -5.0)]
        stats = {"Teams": [stat(1, [game(1.0, "W", 1.0)], 1, 3), stat(2, log2, 2, 3)]}
        old = award(v2.compute(rows, None, None, stats)[0], "Brick Wall")
        new = award(v3.compute(rows, None, None, stats)[0], "Brick Wall")
        self.assertEqual(old["TeamID"], new["TeamID"])
        self.assertEqual("Beat Above-Average Opponents: 2 of 3 | Opponent Surplus Withstood: +15.2 Pts | Record: 4-3-1",
                         new["StatDisplay"])

    def test_other_awards_equal_v2(self):
        rows = [row(1), row(2)]
        stats = {"Teams": [stat(1, [game(1.0, "W", 2.0)], 1, 1), stat(2, [game(2.0)], 0, 1)]}
        old, old_notes = v2.compute(rows, None, None, stats)
        new, notes = v3.compute(rows, None, None, stats)
        self.assertEqual([a["Name"] for a in old], [a["Name"] for a in new])
        self.assertEqual(old_notes, notes)
        for name in ("Best Performer", "Streaker"):
            self.assertEqual(award(old, name), award(new, name))

    def test_overperformer_tie_goes_to_first_in_table_order(self):
        rows = [row(1), row(2)]
        stats = {"Teams": [stat(1, [game(1.5)]), stat(2, [game(1.5)])]}
        self.assertEqual(1, award(v3.compute(rows, None, None, stats)[0], "Overperformer")["TeamID"])

    def test_missing_or_ineligible_evidence_omits_the_award(self):
        rows = [row(1), row(2)]
        for stats in (None, {"Teams": []}, {"Teams": [stat(1, [game(None)]), stat(2, [])]}):
            awards, _ = v3.compute(rows, None, None, stats)
            self.assertIsNone(award(awards, "Overperformer"))
            self.assertIsNone(award(awards, "Brick Wall"))
            self.assertIsNotNone(award(awards, "Best Performer"))

    def test_no_completed_game_gives_no_awards(self):
        self.assertEqual(([], {}), v3.compute([row(1, 0, 0)], None, None, {"Teams": [stat(1, [game(1.0)], 1, 1)]}))


if __name__ == "__main__":
    unittest.main()
