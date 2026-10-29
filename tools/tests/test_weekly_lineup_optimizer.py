from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from weekly_lineup_optimizer import (  # noqa: E402
    ScoredPlayer,
    StartingSlot,
    maximize_lineup,
)


def slot(name: str, *positions: str) -> StartingSlot:
    return StartingSlot(name, frozenset(positions))


def player(name: str, position: str, score: str) -> ScoredPlayer:
    return ScoredPlayer(name, position, score)


class WeeklyLineupOptimizerTests(unittest.TestCase):
    def test_overlapping_2024_flex_requires_global_optimum(self) -> None:
        slots = [slot("FLEX-1", "RB", "WR", "TE"), slot("REC_FLEX-1", "WR", "TE")]
        roster = [player("rb", "RB", "30"), player("wr", "WR", "25"), player("te", "TE", "10")]
        result = maximize_lineup(slots, roster)
        self.assertEqual(result.points, Decimal("55"))
        self.assertEqual({x.slot_id: x.player_id for x in result.assignments}, {"FLEX-1": "rb", "REC_FLEX-1": "wr"})

    def test_2026_four_flex_and_fixed_position_and_no_double_use(self) -> None:
        slots = [slot("RB-1", "RB"), slot("RB-2", "RB"), slot("TE-1", "TE"), slot("FLEX-1", "RB", "WR", "TE"), slot("FLEX-2", "RB", "WR", "TE"), slot("FLEX-3", "RB", "WR", "TE"), slot("FLEX-4", "RB", "WR", "TE")]
        roster = [player("rb1", "RB", "30"), player("rb2", "RB", "20"), player("wr1", "WR", "40"), player("wr2", "WR", "35"), player("wr3", "WR", "25"), player("te1", "TE", "10"), player("te2", "TE", "9"), player("rb3", "RB", "18")]
        result = maximize_lineup(slots, roster)
        self.assertEqual(result.points, Decimal(178))
        self.assertEqual(len(result.assignments), 7)
        self.assertEqual(len({x.player_id for x in result.assignments}), 7)
        self.assertEqual(len(result.unfilled_slot_ids), 0)

    def test_taxi_and_reserve_are_ordinary_pool_inputs(self) -> None:
        result = maximize_lineup([slot("WR-1", "WR")], [player("starter", "WR", "8.1"), player("taxi", "WR", "15.25"), player("ir", "WR", "16.5")])
        self.assertEqual(result.points, Decimal("16.5"))
        self.assertEqual(result.assignments[0].player_id, "ir")

    def test_negative_score_can_be_omitted_for_theoretical_maximum(self) -> None:
        result = maximize_lineup([slot("QB-1", "QB"), slot("K-1", "K")], [player("qb", "QB", "-2"), player("k", "K", "5")])
        self.assertEqual(result.points, Decimal(5))
        self.assertEqual(result.unfilled_slot_ids, ("QB-1",))

    def test_results_are_independent_of_player_input_order(self) -> None:
        slots = [slot("RB-1", "RB"), slot("FLEX-1", "RB", "WR", "TE")]
        players = [player("z", "WR", "8.02"), player("a", "RB", "8.02"), player("b", "RB", "8.02")]
        first = maximize_lineup(slots, players)
        second = maximize_lineup(slots, list(reversed(players)))
        self.assertEqual(first, second)
        self.assertEqual(first.points, Decimal("16.04"))

    def test_cannot_reuse_player_for_multiple_slots(self) -> None:
        result = maximize_lineup([slot("WR-1", "WR"), slot("WR-2", "WR")], [player("only", "WR", "12")])
        self.assertEqual(result.points, Decimal(12))
        self.assertEqual(result.unfilled_slot_ids, ("WR-2",))

    def test_unknown_position_and_invalid_scores_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            maximize_lineup([slot("WR-1", "WR")], [player("unknown", "", "10")])
        with self.assertRaises(ValueError):
            maximize_lineup([slot("WR-1", "WR")], [player("bad", "WR", "nan")])
        with self.assertRaises(ValueError):
            maximize_lineup([slot("WR-1", "WR")], [player("dup", "WR", "3"), player("dup", "WR", "8")])

    def test_zero_slots(self) -> None:
        self.assertEqual(maximize_lineup([], []).points, Decimal(0))


if __name__ == "__main__":
    unittest.main()
