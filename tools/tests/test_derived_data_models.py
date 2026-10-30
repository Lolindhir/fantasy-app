"""Tests for the central derivation models (ADR-055, #919 step 2).

Hand-computed values pin the formulas, an exact-Fraction oracle checks the float arithmetic, and a
deterministic pseudo-random equivalence test compares every model against the already validated Python
port of the PowerShell behaviour in tools/players_league_scoring_shadow.py. No player or league data
that can change is wired in.
"""
from __future__ import annotations

import importlib.util
import math
import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import players_league_scoring_shadow as shadow  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.grading import v1 as grading_v1  # noqa: E402
from derived_data_lib.models.salary import v1 as salary_v1  # noqa: E402
from derived_data_lib.models.salary_cap import v1 as salary_cap_v1  # noqa: E402
from derived_data_lib.ranking import RANKING_TYPES, RankingInput, compute_rankings  # noqa: E402

Season = salary_v1.SeasonInput


def dollars(points: Fraction) -> Fraction:
    """Exact-arithmetic oracle of the unrounded salary mapping (square up to 20 points, linear above)."""
    normalized = points / 20
    scaled = normalized ** 2 if normalized <= 1 else 1 + (normalized - 1) * 2
    return scaled * 50_000_000


def oracle_salary(p1: str, p2: str, p3: str) -> Fraction:
    """Exact unrounded salary. The float result may land on either side of an exact .5 tie, so tests compare
    with assert_matches_oracle instead of for equality."""
    a, b, c = Fraction(p1), Fraction(p2), Fraction(p3)
    if a == 0 and b == 0:
        return Fraction(0)
    if a >= b and a >= c:
        floor = a * Fraction("0.5")
    elif b >= a and b >= c:
        floor = b * Fraction("0.33")
    else:
        floor = c * Fraction("0.17")
    return dollars((max(a, floor) + max(b, floor) + max(c, floor)) / 3)


class OracleMixin(unittest.TestCase):
    def assert_matches_oracle(self, exact: Fraction, actual: int, msg: str = "") -> None:
        self.assertIsInstance(actual, int)
        self.assertLessEqual(abs(Fraction(actual) - exact), Fraction(1, 2) + Fraction(1, 10**6), msg)


class RegistryTests(unittest.TestCase):
    def test_registered_ids_are_sorted_and_complete(self) -> None:
        self.assertEqual(["awards-v1", "grading-v1", "lifecycle-v1", "repairability-v1", "salary-cap-v1", "salary-v1", "standings-v1", "team-range-v1"], registry.model_ids())

    def test_get_model_returns_the_module_and_checks_the_kind(self) -> None:
        self.assertIs(salary_v1, registry.get_model("salary-v1"))
        self.assertIs(salary_cap_v1, registry.get_model("salary-cap-v1", kind="salary-cap"))
        self.assertIs(grading_v1, registry.get_model("grading-v1", kind="grading"))

    def test_unknown_id_and_wrong_kind_fail(self) -> None:
        for bad in ("salary-v2", "", "Salary-V1", None):
            with self.assertRaises(registry.UnknownModelError, msg=repr(bad)):
                registry.get_model(bad)  # type: ignore[arg-type]
        with self.assertRaises(registry.UnknownModelError):
            registry.get_model("grading-v1", kind="salary")

    def test_every_model_declares_id_kind_and_kind_is_registered(self) -> None:
        for model_id in registry.model_ids():
            module = registry.get_model(model_id)
            self.assertEqual(model_id, module.MODEL_ID)
            self.assertIn(module.KIND, registry.KINDS)
            self.assertTrue(module.__doc__ and len(module.__doc__) > 100)
            description = registry.describe(model_id)
            self.assertEqual(model_id, description["ModelId"])

    def test_params_are_read_only(self) -> None:
        for model_id in registry.model_ids():
            with self.assertRaises(TypeError):
                registry.get_model(model_id).PARAMS["Injected"] = 1  # type: ignore[index]

    def test_params_are_pinned_per_version(self) -> None:
        """Immutability: changing a registered model's parameters needs a new version, not an edit."""
        self.assertEqual(
            {
                "WeightTotal": 0.5, "WeightGame": 0.5, "SourceMin": 0.0, "SourceMax": 20.0, "CurveExponent": 2,
                "TargetMin": 0.0, "TargetMax": 50_000_000.0, "FloorWeights": (0.5, 0.33, 0.17),
                "RampIn": {1: (0.25, 0.75), 2: (0.35, 0.65), 3: (0.5, 0.5), 4: (0.75, 0.25)},
            },
            {key: dict(value) if hasattr(value, "keys") else value for key, value in salary_v1.PARAMS.items()},
        )
        self.assertEqual({"SalaryRelevantTeamSize": 20, "Factor": 0.9}, dict(salary_cap_v1.PARAMS))
        self.assertEqual(
            {"AcquisitionPolicy": "acquisition-waiver-only-v1", "ExternalAcquisitionMode": "waiver-only",
             "ImmediateFreeAgentAddsAllowed": False, "TradeRepairAllowed": False},
            dict(registry.get_model("repairability-v1").PARAMS),
        )
        self.assertEqual((6, 12, 18, 24, 30), grading_v1.PARAMS["Thresholds"])
        self.assertEqual(("A", "B", "C", "D", "E", "F"), grading_v1.PARAMS["Grades"])
        self.assertEqual({"K": 1.0, "RB": 2.0, "WR": 2.0}, dict(grading_v1.PARAMS["PositionMultiplier"]))
        self.assertEqual(1.5, grading_v1.PARAMS["DefaultMultiplier"])


class SalaryV1Tests(OracleMixin):
    def test_hand_computed_mapping(self) -> None:
        self.assertEqual(0, salary_v1.map_points_to_dollars(0.0))
        self.assertEqual(12_500_000, salary_v1.map_points_to_dollars(10.0))  # (10/20)^2 * 50M
        self.assertEqual(50_000_000, salary_v1.map_points_to_dollars(20.0))
        self.assertEqual(70_000_000, salary_v1.map_points_to_dollars(24.0))  # 1 + 0.2 * 2 = 1.4
        self.assertEqual(0, salary_v1.map_points_to_dollars(-3.0))  # negatives clamp to 0 before squaring

    def test_hand_computed_floor_salaries(self) -> None:
        # newest holds the maximum 10, floor 5: values 10, 6, 5 -> mean 7 -> (7/20)^2 * 50M
        self.assertEqual(6_125_000, salary_v1.salary_from_points(10, 6, 2))
        # 10, 0, 0 -> floor 5 -> 10, 5, 5 -> mean 20/3
        self.assertEqual(5_555_556, salary_v1.salary_from_points(10, 0, 0))
        self.assertEqual(50_000_000, salary_v1.salary_from_points(20, 20, 20))

    def test_unrounded_curve_and_floor_average_back_the_rounded_salary(self) -> None:
        self.assertEqual(12_500_000.0, salary_v1.curve_dollars(10.0))
        self.assertEqual(50_000_000.0 * 0.5 ** 3, salary_v1.curve_dollars(10.0, 3))  # exponent override
        self.assertEqual(70_000_000.0, salary_v1.curve_dollars(24.0, 2))
        self.assertEqual(0.0, salary_v1.floored_average(0, 0, 12.0))
        self.assertEqual(20 / 3, salary_v1.floored_average(10, 0, 0))
        rng = random.Random(7)
        for _ in range(200):
            p = [rng.uniform(0, 30) for _ in range(3)]
            self.assertEqual(salary_v1.salary_from_points(*p),
                             salary_v1.map_points_to_dollars(salary_v1.floored_average(*p)))
            self.assertEqual(salary_v1.map_points_to_dollars(p[0]), round(salary_v1.curve_dollars(p[0])))

    def test_two_newest_seasons_zero_gives_zero(self) -> None:
        self.assertEqual(0, salary_v1.salary_from_points(0, 0, 12.0))
        self.assertNotEqual(0, salary_v1.salary_from_points(0, 5, 0))

    def test_floor_weight_depends_on_which_season_holds_the_maximum(self) -> None:
        self.assert_matches_oracle(oracle_salary("2", "9", "3"), salary_v1.salary_from_points(2, 9, 3))  # middle: 0.33
        self.assert_matches_oracle(oracle_salary("1", "3", "9"), salary_v1.salary_from_points(1, 3, 9))  # oldest: 0.17
        self.assert_matches_oracle(oracle_salary("9", "9", "9"), salary_v1.salary_from_points(9, 9, 9))  # tie: newest wins

    def test_season_points_weights_both_averages(self) -> None:
        self.assertEqual(6.0, salary_v1.season_points(Season(avg_potential_game=4.0, avg_game=8.0)))

    def test_ramp_in_of_the_projected_salary(self) -> None:
        current, p1, p2, p3 = Season(4, 4), Season(10, 10), Season(6, 6), Season(2, 2)
        self.assertEqual(6_125_000, salary_v1.compute(current, p1, p2, p3, 3).salary)
        self.assertEqual(8.5, salary_v1.current_season_points(4.0, 10.0, 1))
        self.assertEqual(10.0, salary_v1.current_season_points(4.0, 10.0, 0))  # previous season only
        self.assertEqual(7.0, salary_v1.current_season_points(4.0, 10.0, 3))
        self.assertEqual(4.0, salary_v1.current_season_points(4.0, 10.0, 5))  # no blend from week 5
        self.assertEqual(4.0, salary_v1.current_season_points(4.0, 10.0, 18))
        for week, blended in ((0, "10"), (1, "8.5"), (2, "7.9"), (3, "7"), (4, "5.5"), (5, "4"), (9, "4")):
            projected = salary_v1.compute(current, p1, p2, p3, week).salary_projected
            self.assert_matches_oracle(oracle_salary(blended, "10", "6"), projected, f"week {week}")

    def test_negative_or_non_integer_week_and_non_finite_values_fail(self) -> None:
        for bad in (-1, 1.5, True, None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                salary_v1.current_season_points(1.0, 1.0, bad)  # type: ignore[arg-type]
        for bad in (math.nan, math.inf, None, "1"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                salary_v1.salary_from_points(bad, 1.0, 1.0)  # type: ignore[arg-type]

    def test_float_arithmetic_matches_the_exact_oracle(self) -> None:
        rng = random.Random(20261014)
        for _ in range(500):
            values = [Fraction(rng.randint(0, 3200), 100) for _ in range(3)]
            expected = oracle_salary(*(str(float(v)) for v in values))
            actual = salary_v1.salary_from_points(*(float(v) for v in values))
            self.assert_matches_oracle(expected, actual, str(values))


class SalaryCapV1Tests(unittest.TestCase):
    def test_hand_computed_cap(self) -> None:
        result = salary_cap_v1.compute(range(1, 26), team_count=1)  # top 20: 25..6, sum 310, mean 15.5
        self.assertEqual((279, 20, 20), (result.cap, result.top_n, result.players_considered))

    def test_raw_cap_is_the_unrounded_value_behind_compute(self) -> None:
        self.assertEqual(279.0, salary_cap_v1.raw_cap(range(25, 5, -1)))
        self.assertEqual(27.0, salary_cap_v1.raw_cap([20, 10], relevant_team_size=2))  # mean 15 * 2 * 0.9
        rng = random.Random(11)
        for _ in range(100):
            values = sorted((rng.uniform(1, 5e7) for _ in range(30)), reverse=True)
            self.assertEqual(salary_cap_v1.compute(values, 1).cap, round(salary_cap_v1.raw_cap(values[:20])))

    def test_fewer_players_than_top_n_use_all_players(self) -> None:
        result = salary_cap_v1.compute([100] * 5, team_count=12)
        self.assertEqual((1800, 240, 5), (result.cap, result.top_n, result.players_considered))

    def test_rounding_is_half_to_even(self) -> None:
        self.assertEqual(4, salary_cap_v1.compute([1] * 5 + [0] * 15, team_count=1).cap)  # 5 / 20 * 20 * 0.9 = 4.5 -> 4
        self.assertEqual(14, salary_cap_v1.compute([1] * 15 + [0] * 5, team_count=1).cap)  # 13.5 -> 14

    def test_top_n_scales_with_team_count_and_ignores_input_order(self) -> None:
        salaries = [float(value) for value in range(100)]
        shuffled = salaries[:]
        random.Random(1).shuffle(shuffled)
        a = salary_cap_v1.compute(salaries, team_count=2)
        b = salary_cap_v1.compute(shuffled, team_count=2)
        self.assertEqual(a, b)
        self.assertEqual(40, a.top_n)

    def test_invalid_input_fails(self) -> None:
        for team_count in (0, -1, 1.5, True, None):
            with self.assertRaises(ValueError, msg=repr(team_count)):
                salary_cap_v1.compute([1.0], team_count)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            salary_cap_v1.compute([], 12)
        with self.assertRaises(ValueError):
            salary_cap_v1.compute([1.0, math.nan], 12)


class GradingV1Tests(unittest.TestCase):
    def test_hand_computed_boundaries_by_position(self) -> None:
        cases = {
            "K": {6: "A", 7: "B", 12: "B", 13: "C", 18: "C", 19: "D", 24: "D", 25: "E", 30: "E", 31: "F"},
            "WR": {12: "A", 13: "B", 24: "B", 25: "C", 36: "C", 37: "D", 48: "D", 49: "E", 60: "E", 61: "F"},
            "RB": {12: "A", 13: "B", 61: "F"},
            "QB": {9: "A", 10: "B", 18: "B", 19: "C", 27: "C", 28: "D", 36: "D", 37: "E", 45: "E", 46: "F"},
            "TE": {9: "A", 10: "B", 46: "F"},
        }
        for position, ranks in cases.items():
            for rank, grade in ranks.items():
                self.assertEqual(grade, grading_v1.letter_grade(rank, position), msg=f"{position} {rank}")

    def test_unranked_player_gets_no_grade(self) -> None:
        self.assertIsNone(grading_v1.letter_grade(None, "QB"))
        self.assertEqual({"Type": "Rank", "Value": None, "Rank": None, "Grade": None}, grading_v1.rank_row(None, "WR"))

    def test_rank_row_shape_and_position_case(self) -> None:
        self.assertEqual({"Type": "Rank", "Value": 7, "Rank": 7, "Grade": "B"}, grading_v1.rank_row(7, "k"))
        self.assertEqual("B", grading_v1.letter_grade(18, None))  # unknown position: multiplier 1.5
        self.assertEqual("C", grading_v1.letter_grade(19, None))

    def test_non_finite_rank_fails(self) -> None:
        with self.assertRaises(ValueError):
            grading_v1.letter_grade(math.nan, "QB")


class RankingTests(unittest.TestCase):
    @staticmethod
    def by_type(rows: list[dict]) -> dict[str, int]:
        return {row["Type"]: row["Value"] for row in rows}

    def test_hand_computed_field_with_ties_and_positions(self) -> None:
        players = [
            RankingInput("a", "WR", 10, 10, 8, 8),
            RankingInput("b", "WR", 10, 9, 8, 9),
            RankingInput("c", "QB", 5, 12),
            RankingInput("d", "WR", 0, 3),
        ]
        ranks = {key: self.by_type(rows) for key, rows in compute_rankings(players).items()}
        # Total (AvgPotentialGame): a=10, b=10, c=5 -> 1, 1, 3; d inactive
        # PerGame (AvgGame): c=12, a=10, b=9 -> a=2, b=3, c=1
        # Combined values: a 1.5, b 2.0, c 2.0 -> a=1, b and c share 2
        # Previous season (a 8/8, b 8/9): total ranks 1, 1; per game b=1, a=2 -> combined a 1.5, b 1.0 -> b=1, a=2
        self.assertEqual(
            {"Total": 1, "PerGame": 2, "Combined": 1, "Total_Pos": 1, "PerGame_Pos": 1, "Combined_Pos": 1,
             "Combined_Previous": 2},
            ranks["a"])
        self.assertEqual(
            {"Total": 1, "PerGame": 3, "Combined": 2, "Total_Pos": 1, "PerGame_Pos": 2, "Combined_Pos": 2,
             "Combined_Previous": 1},
            ranks["b"])
        self.assertEqual(
            {"Total": 3, "PerGame": 1, "Combined": 2, "Total_Pos": 1, "PerGame_Pos": 1, "Combined_Pos": 1},
            ranks["c"])
        self.assertEqual({}, ranks["d"])

    def test_rows_follow_the_documented_type_order(self) -> None:
        rows = compute_rankings([RankingInput("a", "QB", 4, 4, 3, 3), RankingInput("b", "QB", 2, 2, 2, 2)])
        for player_rows in rows.values():
            self.assertEqual(list(RANKING_TYPES), [row["Type"] for row in player_rows])

    def test_equal_values_share_a_rank_and_the_next_rank_skips(self) -> None:
        players = [RankingInput(key, "TE", 6, 6) for key in "abc"] + [RankingInput("d", "TE", 5, 5)]
        total = {key: self.by_type(rows)["Total"] for key, rows in compute_rankings(players).items()}
        self.assertEqual({"a": 1, "b": 1, "c": 1, "d": 4}, total)

    def test_combined_previous_uses_only_players_with_previous_history(self) -> None:
        players = [
            RankingInput("a", "QB", 4, 4, 9, 9),
            RankingInput("b", "QB", 4, 4, 3, 3),
            RankingInput("c", "QB", 4, 4),
            RankingInput("d", "QB", 4, 4, 0, 5),
        ]
        ranks = compute_rankings(players)
        previous = {key: self.by_type(rows).get("Combined_Previous") for key, rows in ranks.items()}
        self.assertEqual({"a": 1, "b": 2, "c": None, "d": None}, previous)

    def test_inactive_player_without_position_is_allowed_but_active_is_not(self) -> None:
        self.assertEqual({"x": []}, compute_rankings([RankingInput("x", "", 0, 0)]))
        with self.assertRaises(ValueError):
            compute_rankings([RankingInput("x", "", 1, 1)])

    def test_duplicate_keys_and_non_finite_values_fail(self) -> None:
        with self.assertRaises(ValueError):
            compute_rankings([RankingInput("a", "QB", 1, 1), RankingInput("a", "QB", 2, 2)])
        with self.assertRaises(ValueError):
            compute_rankings([RankingInput("a", "QB", math.nan, 1)])

    def test_result_is_independent_of_input_order(self) -> None:
        rng = random.Random(7)
        players = [
            RankingInput(f"p{i}", rng.choice(["QB", "RB", "WR", "TE", "K"]), rng.randint(0, 12) / 2,
                         rng.randint(0, 12) / 2, rng.randint(0, 6) / 2, rng.randint(0, 6) / 2)
            for i in range(80)
        ]
        shuffled = players[:]
        rng.shuffle(shuffled)
        self.assertEqual(compute_rankings(players), compute_rankings(shuffled))


class ParityWithValidatedPortTests(unittest.TestCase):
    """The models equal the PowerShell behaviour as ported and validated in the Players shadow (D3)."""

    POSITIONS = ("QB", "RB", "WR", "TE", "K")

    def _population(self, seed: int, size: int) -> list[dict]:
        rng = random.Random(seed)

        def points() -> float:
            return rng.choice([0, 0, rng.randint(0, 3000) / 100, rng.randint(0, 40) / 4])  # zeros and ties

        players = []
        for index in range(size):
            history = {
                key: {"AvgPotentialGame": points(), "AvgGame": points()}
                for key in ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")
            }
            players.append({
                "ID": f"p{index:04d}",
                "Position": rng.choice(self.POSITIONS),
                "FantasyPointsAvgPotentialGame": points(),
                "FantasyPointsAvgGame": points(),
                "PointHistory": history,
            })
        return players

    def test_salary_and_salary_projected(self) -> None:
        for seed in (1, 2, 3):
            for player in self._population(seed, 150):
                history = player["PointHistory"]
                for final_week in range(0, 9):
                    expected = shadow.salaries(
                        player["FantasyPointsAvgPotentialGame"], player["FantasyPointsAvgGame"], history,
                        final_week=final_week, weight_total=0.5, weight_game=0.5)
                    inputs = [Season(history[key]["AvgPotentialGame"], history[key]["AvgGame"])
                              for key in ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")]
                    result = salary_v1.compute(
                        Season(player["FantasyPointsAvgPotentialGame"], player["FantasyPointsAvgGame"]),
                        *inputs, final_week)
                    self.assertEqual(expected, (result.salary, result.salary_projected),
                                     msg=f"seed {seed} {player['ID']} week {final_week}")

    def test_rankings(self) -> None:
        for seed in (11, 12, 13):
            players = self._population(seed, 300)
            expected = shadow.compute_rankings(players, 0.5, 0.5)
            inputs = [
                RankingInput(
                    p["ID"], p["Position"], p["FantasyPointsAvgPotentialGame"], p["FantasyPointsAvgGame"],
                    p["PointHistory"]["SeasonMinus1"]["AvgPotentialGame"], p["PointHistory"]["SeasonMinus1"]["AvgGame"])
                for p in players
            ]
            self.assertEqual(expected, compute_rankings(inputs), msg=f"seed {seed}")

    def test_grading(self) -> None:
        for position in (*self.POSITIONS, "XX"):
            for rank in range(0, 70):
                self.assertEqual(shadow.letter_grade(rank, position), grading_v1.letter_grade(rank, position))
            # the legacy port grades a missing rank as 0 (A); grading-v1 deliberately gives no grade (2026-10-15)
            self.assertEqual("A", shadow.letter_grade(None, position))
            self.assertIsNone(grading_v1.letter_grade(None, position))

    def test_salary_cap(self) -> None:
        rng = random.Random(99)
        for team_count in (1, 8, 12):
            salaries = [float(rng.randint(0, 60_000_000)) for _ in range(rng.randint(30, 500))]
            expected = shadow.compute_salary_cap(salaries, 20, team_count)
            self.assertEqual(expected, salary_cap_v1.compute(salaries, team_count).cap)


SIM_SCRIPT = (Path(__file__).resolve().parents[2] / "fantasy-management" / "league-economy" / "salary"
              / "simulation" / "salary_simulation.py")


def load_simulation():
    spec = importlib.util.spec_from_file_location("salary_simulation_under_test", SIM_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# FM salary simulation takes curve, floor and cap from the central models (ADR-055, #919 step 7).
class SalarySimulationUsesRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sim = load_simulation()
        cls.salary = cls.sim.SALARY_MODEL
        cls.cap = cls.sim.SALARY_CAP_MODEL

    def test_models_are_the_registered_modules(self) -> None:
        # The simulation imports the package as tools.derived_data_lib; this module as derived_data_lib.
        self.assertEqual("salary-v1", self.salary.MODEL_ID)
        self.assertEqual("salary-cap-v1", self.cap.MODEL_ID)
        self.assertEqual(registry.describe("salary-v1")["Params"], dict(self.salary.PARAMS))
        self.assertEqual(registry.describe("salary-cap-v1")["Params"], dict(self.cap.PARAMS))

    def test_no_local_copy_of_the_formula_constants(self) -> None:
        for name in ("REF_SIGNAL", "REF_SALARY", "CAP_FACTOR"):
            self.assertFalse(hasattr(self.sim, name), f"{name} is a copy of a model parameter")
        source = SIM_SCRIPT.read_text(encoding="utf-8")
        for literal in ("0.33", "0.17", "50_000_000", "0.9"):
            self.assertNotIn(literal, source.replace("MIN_PCT_BY_YEAR", ""), f"literal {literal} duplicates a model parameter")

    def test_helpers_equal_the_model_functions(self) -> None:
        for points in (0.0, 4.5, 10.0, 20.0, 27.3):
            self.assertEqual(self.salary.curve_dollars(points, 2.0), self.sim.map_salary(points, 2.0))
            self.assertEqual(self.salary.curve_dollars(points, 1.5), self.sim.map_salary(points, 1.5))
        for triple in ((10, 6, 2), (10, 0, 0), (0, 0, 12), (3, 9, 4), (3, 4, 9)):
            self.assertEqual(self.salary.floored_average(*triple), self.sim.floored_three_year(*triple))
        entry = {"AvgPotentialGame": 12.4, "AvgGame": 9.6}
        self.assertEqual(self.salary.season_points(self.salary.SeasonInput(12.4, 9.6)), self.sim.season_performance(entry))
        salaries = [float(v) for v in range(1, 60)]
        self.assertEqual(self.cap.raw_cap(sorted(salaries, reverse=True)[:20]), self.sim.top_n_cap(salaries, 20, 20))


if __name__ == "__main__":
    unittest.main()
