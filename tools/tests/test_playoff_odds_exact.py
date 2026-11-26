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


class ExactRecordModelTests(unittest.TestCase):
    @staticmethod
    def teams(records, points=None):
        return [
            {"TeamID": i + 1, "CanonicalLeagueRosterID": f"r{i}", "Wins": w,
             "Losses": l, "Ties": t, "Points": (points or [0] * len(records))[i],
             "PointsAgainst": 0}
            for i, (w, l, t) in enumerate(records)
        ]

    @staticmethod
    def models():
        from derived_data_lib.models.playoff_odds import v3, v4
        return v3, v4

    def test_global_parameters_are_pinned(self):
        for model, weights in zip(self.models(), ((1, 1, 1), (99, 2, 99))):
            self.assertEqual(dict(model.PARAMS), {
                "OutcomeWeights": weights, "MinPlayedFraction": (2, 5),
                "MaxStates": 750_000, "MaxTransitions": 8_000_000,
                "EqualRecordTieRule": "equal-record-teams-share-places",
            })
            with self.assertRaises(TypeError):
                model.PARAMS["OutcomeWeights"] = (1, 0, 1)

    def test_exact_mass_matches_oracle_and_ignores_points(self):
        records = [(2, 0, 0), (0, 2, 0), (1, 1, 0), (1, 1, 0)]
        pairs = ((0, 1), (2, 3), (0, 2), (1, 3))
        games = [(f"r{a}", f"r{b}") for a, b in pairs]
        supports = []
        for model in self.models():
            kwargs = dict(open_games=games, playoff_teams=2, regular_season_complete=False)
            result = model.compute(teams=self.teams(records), **kwargs)
            self.assertTrue(result["Available"])
            self.assertEqual(result, model.compute(teams=self.teams(records, [900, 100, 500, 600]), **kwargs))
            denominator = int(result["Provenance"]["PlaceMassDenominator"])
            masses = [[int(x) for x in team["PlaceMassNumerators"]] for team in result["Teams"]]
            actual = [[Fraction(x, denominator) for x in row] for row in masses]
            self.assertEqual(actual, oracle(tuple(2*w+t for w, _, t in records), pairs,
                                            model.PARAMS["OutcomeWeights"]))
            self.assertTrue(all(sum(row) == denominator for row in masses))
            self.assertTrue(all(sum(col) == denominator for col in zip(*masses)))
            self.assertEqual(sum(sum(row[:2]) for row in masses), 2 * denominator)
            for team, row in zip(result["Teams"], masses):
                self.assertEqual(team["PossiblePlaces"], [i + 1 for i, x in enumerate(row) if x])
                self.assertEqual(team["Status"], "clinched" if sum(row[:2]) == denominator
                                 else "eliminated" if not sum(row[:2]) else "alive")
            supports.append([team["PossiblePlaces"] for team in result["Teams"]])
        self.assertEqual(*supports)

    def test_progress_gate_is_dynamic(self):
        from unittest.mock import patch
        for model in self.models():
            kwargs = dict(open_games=[("r0", "r1")] * 3, playoff_teams=1, regular_season_complete=False)
            with patch("derived_data_lib.models.playoff_odds.record_model_v1.enumerate_places",
                       side_effect=AssertionError("must not enumerate before the gate")):
                early = model.compute(teams=self.teams([(1, 0, 0), (0, 1, 0)]), **kwargs)
            self.assertFalse(early["Available"])
            self.assertEqual(early["Reason"], "season-progress-too-low")
            self.assertIsNone(early["Teams"][0]["PlaceProbabilities"])
            self.assertTrue(model.compute(teams=self.teams([(1, 1, 0)] * 2), **kwargs)["Available"])

    def test_exact_tail_survives_float_rounding(self):
        _, model = self.models()
        result = model.compute(teams=self.teams([(60, 0, 0), (0, 60, 0)]),
                               open_games=[("r0", "r1")] * 60,
                               playoff_teams=1, regular_season_complete=False)
        favorite, underdog = result["Teams"]
        self.assertEqual(favorite["Status"], "alive")
        self.assertEqual(underdog["Status"], "alive")
        self.assertEqual(favorite["PossiblePlaces"], [1, 2])
        self.assertEqual(underdog["PossiblePlaces"], [1, 2])
        denominator = int(result["Provenance"]["PlaceMassDenominator"])
        self.assertEqual(Fraction(int(underdog["PlaceMassNumerators"][0]), denominator),
                         Fraction(99, 200) ** 60 / 2)
        self.assertGreater(favorite["EliminationProbability"], 0)

    def test_unequal_future_schedule_is_explicitly_unavailable(self):
        for model in self.models():
            result = model.compute(teams=self.teams([(2, 2, 0)] * 4),
                                   open_games=[("r0", "r1")], playoff_teams=2,
                                   regular_season_complete=False)
            self.assertEqual(result["Reason"], "unequal-final-game-count")
            self.assertFalse(result["Available"])

    def test_limit_is_not_a_partial_probability(self):
        from derived_data_lib.models.playoff_odds.record_model_v1 import compute_record_odds
        model, _ = self.models()
        result = compute_record_odds(model_id=model.MODEL_ID, params={**model.PARAMS, "MaxStates": 1},
                                     teams=self.teams([(1, 1, 0)] * 2), open_games=[("r0", "r1")],
                                     playoff_teams=1, regular_season_complete=False)
        self.assertEqual(result["Reason"], "state-limit-exceeded")
        self.assertFalse(result["Available"])
        self.assertTrue(all(t["Status"] is None for t in result["Teams"]))

    def test_official_final_uses_points_and_points_against(self):
        teams = self.teams([(2, 1, 0)] * 4, [300, 290, 300, 280])
        teams[0]["PointsAgainst"] = 100
        teams[2]["PointsAgainst"] = 90
        for model in self.models():
            result = model.compute(teams=teams, open_games=[], playoff_teams=2, regular_season_complete=True)
            self.assertEqual(result["Provenance"]["Method"], "official-table")
            self.assertEqual([t["PossiblePlaces"] for t in result["Teams"]], [[2], [3], [1], [4]])
            self.assertEqual([t["PlayoffProbability"] for t in result["Teams"]], [1, 0, 1, 0])

    def test_final_shared_rank_at_boundary_is_not_invented(self):
        for model in self.models():
            result = model.compute(teams=self.teams([(2, 1, 0)] * 4, [300, 300, 300, 280]),
                                   open_games=[], playoff_teams=2, regular_season_complete=True)
            self.assertFalse(result["Available"])
            self.assertEqual(result["Reason"], "ambiguous-final-playoff-boundary")


if __name__ == "__main__":
    unittest.main()
