"""Exact W/T/L place-mass regression tests for Issue #1693."""
from __future__ import annotations

import itertools
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from derived_data_lib.models.playoff_odds.exact_v1 import (  # noqa: E402
    EnumerationLimit, enumerate_places,
)


def oracle(starts, pairs, weights):
    """Independent exhaustive path AND tied-order oracle on tiny fixtures."""
    n = len(starts)
    result = [[Fraction() for _ in starts] for _ in starts]
    for outcomes in itertools.product(range(3), repeat=len(pairs)):
        final = list(starts)
        probability = Fraction(1)
        for (a, b), outcome in zip(pairs, outcomes):
            final[a] += outcome
            final[b] += 2 - outcome
            probability *= Fraction(weights[outcome], sum(weights))
        orders = [
            order for order in itertools.permutations(range(n))
            if all(final[a] >= final[b] for a, b in zip(order, order[1:]))
        ]
        for order in orders:
            for place, team in enumerate(order):
                result[team][place] += probability / len(orders)
    return result


def run(starts, pairs, weights=(1, 1, 1), **kwargs):
    return enumerate_places(starts, pairs, weights, **{
        "max_states": 10000, "max_transitions": 100000, **kwargs,
    })


class ExactPlacesTests(unittest.TestCase):
    def test_both_weightings_match_independent_oracle(self):
        for starts, pairs in (
            ((2, 2), ((0, 1),)),
            ((4, 2, 1, 1), ((0, 1), (2, 3), (0, 2), (1, 3))),
            ((3, 3, 2, 0), ((0, 1), (2, 3), (1, 0), (3, 2))),
            ((2, 2, 2, 2), ()),
        ):
            for weights in ((1, 1, 1), (99, 2, 99)):
                with self.subTest(starts=starts, pairs=pairs, weights=weights):
                    result = run(starts, pairs, weights)
                    actual = [[Fraction(m, result.denominator) for m in row]
                              for row in result.numerators]
                    self.assertEqual(oracle(starts, pairs, weights), actual)
                    self.assertTrue(all(sum(row) == 1 for row in actual))
                    self.assertTrue(all(sum(col) == 1 for col in zip(*actual)))
                    self.assertEqual(2, sum(sum(row[:2]) for row in actual)
                                     if len(starts) >= 2 else 0)

    def test_tie_weight_and_tie_only_path_are_preserved(self):
        # Team 0 begins one half-win behind. A tie leaves it behind;
        # winning the match puts it ahead. In a second fixture, a tie
        # at the final record comes only from a future match tie.
        for weights in ((1, 1, 1), (99, 2, 99)):
            result = run((0, 1), ((0, 1),), weights)
            self.assertEqual(Fraction(weights[2], sum(weights)),
                             Fraction(result.numerators[0][0], result.denominator))
            tied = run((0, 0), ((0, 1),), weights)
            self.assertEqual(Fraction(1, 2),
                             Fraction(tied.numerators[0][0], tied.denominator))
        # A 1/3 tie-only route to the middle place for the first team.
        a1 = run((2, 2, 2, 2), ((0, 1), (2, 3)))
        a2 = run((2, 2, 2, 2), ((0, 1), (2, 3)), (99, 2, 99))
        self.assertEqual(
            [[x > 0 for x in row] for row in a1.numerators],
            [[x > 0 for x in row] for row in a2.numerators],
        )

    def test_small_positive_masses_never_round_to_zero(self):
        result = run((0, 40), ((0, 1),) * 20, (99, 2, 99))
        self.assertGreater(result.numerators[0][0], 0)
        self.assertEqual(Fraction(99, 200) ** 20 / 2,
                         Fraction(result.numerators[0][0], result.denominator))

    def test_limits_fail_closed(self):
        for limits in ({"max_states": 2}, {"max_transitions": 2}):
            with self.assertRaises(EnumerationLimit):
                run((0, 0), ((0, 1),), **limits)

    def test_repeated_pairing_compresses_paths(self):
        result = run((0, 0), ((0, 1),) * 4)
        self.assertEqual(9, result.state_count)
        self.assertLess(result.state_count, 3 ** 4)

    def test_bad_inputs_rejected(self):
        for starts, pairs, weights in (
            ((0,), (), (1, 1, 1)),
            ((0, 0), ((0, 0),), (1, 1, 1)),
            ((0, 0), ((0, 2),), (1, 1, 1)),
            ((0, 0), (), (1, 0, 1)),
        ):
            with self.assertRaises(ValueError):
                run(starts, pairs, weights)


if __name__ == "__main__":
    unittest.main()
