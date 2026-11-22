"""injury-impact-v1 (Issue #1584 CP5): regression cases of the CP2 rules with synthetic rosters (no real players or weeks)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.injury_impact import v1  # noqa: E402
from league_metadata import KNOWN_MODEL_IDS  # noqa: E402
from weekly_lineup_optimizer import StartingSlot  # noqa: E402

SLOTS = [StartingSlot("QB1", frozenset({"QB"})), StartingSlot("RB1", frozenset({"RB"})), StartingSlot("FLEX1", frozenset({"RB", "WR"}))]


def avail(state, available="yes", played=None, report=None):
    return {"State": state, "Available": available, "Played": played, "Report": report}


def player(pid, position, projection, availability):
    return {"CanonicalPlayerID": pid, "Position": position, "Projection": projection, "Availability": availability}


HEALTHY = avail("played", "yes", True)
OUT = avail("not-played-reported", "no", False, [{"Game": "Out"}])


class RegistrationTests(unittest.TestCase):
    def test_model_is_registered_and_selectable_by_data_meta(self) -> None:
        self.assertIs(v1, registry.get_model("injury-impact-v1", "injury-impact"))
        self.assertIn("injury-impact-v1", KNOWN_MODEL_IDS["InjuryImpact"])
        self.assertIn("injury-impact", registry.KINDS)


class RuleTests(unittest.TestCase):
    def compute(self, *players):
        return v1.compute_team_week(SLOTS, list(players))

    def test_no_injury_gives_zero_impact(self) -> None:
        result = self.compute(player("a", "QB", 20.0, HEALTHY), player("b", "RB", 10.0, HEALTHY))
        self.assertEqual(0.0, result["Impact"])
        self.assertEqual(result["ProjectedBest"], result["ProjectedBestHealthy"])
        self.assertFalse(result["IsLowerBound"])

    def test_injured_starter_costs_difference_to_best_replacement(self) -> None:
        result = self.compute(
            player("rb1", "RB", 15.0, OUT), player("rb2", "RB", 9.0, HEALTHY), player("wr1", "WR", 8.0, HEALTHY), player("qb", "QB", 20.0, HEALTHY))
        # A: RB 15, FLEX 9, QB 20 = 44; B: RB 9, FLEX 8, QB 20 = 37
        self.assertEqual(7.0, result["Impact"])
        self.assertEqual(1, result["Counts"]["Injured"])
        self.assertEqual(7.0, result["Injured"][0]["SingleReturnImpact"])
        self.assertEqual(["Out"], result["Injured"][0]["ReportedGameStatus"])

    def test_questionable_who_played_stays_usable_and_out_who_played_too(self) -> None:
        out_but_played = avail("played", "no", True, [{"Game": "Out"}])
        questionable_played = avail("played", "yes", True, [{"Game": "Questionable"}])
        result = self.compute(player("a", "RB", 15.0, out_but_played), player("b", "RB", 9.0, questionable_played))
        self.assertEqual(0.0, result["Impact"])  # E4
        self.assertEqual(0, result["Counts"]["Injured"])

    def test_questionable_who_did_not_play_leaves_pool_b(self) -> None:
        result = self.compute(player("a", "RB", 15.0, avail("not-played-reported", "yes", False, [{"Game": "Questionable"}])))
        self.assertEqual(15.0, result["Impact"])

    def test_healthy_scratch_stays_in_pool_b(self) -> None:
        result = self.compute(player("a", "RB", 15.0, avail("healthy-scratch", "yes", False)))
        self.assertEqual(0.0, result["Impact"])  # E3: not an injury

    def test_reserve_without_report_leaves_pool_b(self) -> None:
        result = self.compute(player("a", "QB", 20.0, avail("not-played-reserve", "no", False)))
        self.assertEqual(20.0, result["Impact"])
        self.assertFalse(result["Injured"][0]["ReportedGameStatus"])

    def test_bye_no_record_and_not_on_active_roster_are_in_neither_pool(self) -> None:
        result = self.compute(
            player("bye", "QB", 25.0, avail("bye", "unknown", None)),
            player("fa", "RB", 12.0, None),
            player("cut", "WR", 11.0, avail("not-on-active-roster", "no", False)))
        self.assertEqual(0.0, result["Impact"])
        self.assertEqual((1, 1, 1), (result["Counts"]["Bye"], result["Counts"]["NoRecord"], result["Counts"]["NotOnActiveRoster"]))
        self.assertEqual(0.0, result["ProjectedBest"])

    def test_bye_week_with_available_bye_is_neutral_not_unknown_not_lower_bound(self) -> None:
        # since the availability product writes Available "bye" (Issue #1616), classification still follows State only
        result = self.compute(
            player("bye", "QB", 25.0, avail("bye", "bye", None)),
            player("ok", "RB", 10.0, HEALTHY))
        self.assertEqual(0.0, result["Impact"])
        self.assertEqual(1, result["Counts"]["Bye"])
        self.assertEqual(0, result["Counts"]["Unknown"])
        self.assertFalse(result["HasUnknownEvidence"])
        self.assertFalse(result["IsLowerBound"])

    def test_taxi_and_ir_players_count_like_anyone_on_the_roster(self) -> None:
        # the roster passed in contains starters, bench, taxi and IR alike; the model has no slot-status input
        result = self.compute(player("starter", "RB", 12.0, OUT), player("ir_or_taxi", "RB", 11.0, HEALTHY))
        # A: RB 12 + FLEX 11 = 23; B: RB 11 = 11
        self.assertEqual(12.0, result["Impact"])

    def test_missing_projection_of_injured_player_makes_a_lower_bound_never_zero_filled(self) -> None:
        result = self.compute(player("a", "RB", None, OUT), player("b", "RB", 9.0, HEALTHY))
        self.assertTrue(result["IsLowerBound"])
        self.assertEqual(1, result["Counts"]["Undeterminable"])
        self.assertEqual(0.0, result["Impact"])
        self.assertIsNone(result["Injured"][0]["SingleReturnImpact"])
        self.assertIsNone(result["Injured"][0]["Projection"])

    def test_missing_projection_of_usable_player_is_neutral_and_counted(self) -> None:
        result = self.compute(player("a", "RB", None, HEALTHY), player("b", "RB", 9.0, OUT))
        self.assertEqual(1, result["Counts"]["NoProjection"])
        self.assertFalse(result["IsLowerBound"])
        self.assertEqual(9.0, result["Impact"])

    def test_unknown_evidence_is_never_healthy(self) -> None:
        result = self.compute(player("a", "QB", 20.0, avail("unknown", "unknown", None)))
        self.assertTrue(result["HasUnknownEvidence"])
        self.assertEqual(20.0, result["Impact"])

    def test_unknown_state_name_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.compute(player("a", "QB", 20.0, avail("something-new")))

    def test_two_injured_starters_single_return_is_not_additive(self) -> None:
        result = self.compute(player("a", "RB", 15.0, OUT), player("b", "RB", 14.0, OUT), player("c", "RB", 5.0, HEALTHY))
        singles = sum(row["SingleReturnImpact"] for row in result["Injured"])
        self.assertEqual(24.0, result["Impact"])  # A: RB 15 + FLEX 14 = 29; B: RB 5
        self.assertEqual({15.0, 14.0}, {row["SingleReturnImpact"] for row in result["Injured"]})
        self.assertNotEqual(result["Impact"], singles)  # 29: the single-return values are not additive

    def test_order_independence_and_deterministic_output(self) -> None:
        roster = [player("a", "RB", 15.0, OUT), player("b", "RB", 9.0, HEALTHY), player("c", "WR", 8.0, HEALTHY), player("d", "WR", 7.0, OUT)]
        self.assertEqual(self.compute(*roster), self.compute(*reversed(roster)))

    def test_duplicate_player_fails(self) -> None:
        with self.assertRaises(ValueError):
            self.compute(player("a", "RB", 1.0, HEALTHY), player("a", "RB", 1.0, HEALTHY))

    def test_impact_never_negative_and_equals_difference_of_pools(self) -> None:
        result = self.compute(player("a", "RB", -3.0, OUT), player("b", "RB", 9.0, HEALTHY))
        self.assertGreaterEqual(result["Impact"], 0.0)
        self.assertAlmostEqual(result["ProjectedBest"] - result["ProjectedBestHealthy"], result["Impact"], places=4)


class SeasonTotalTests(unittest.TestCase):
    def test_totals_equal_the_sum_of_the_weekly_values(self) -> None:
        def week(number, impact, lower=False, injured=()):
            return {"Week": number, "Teams": [{
                "CanonicalLeagueRosterID": "r1", "Impact": impact, "IsLowerBound": lower,
                "Counts": {"Undeterminable": 1 if lower else 0}, "Injured": [{"CanonicalPlayerID": p, "SingleReturnImpact": v} for p, v in injured]}]}
        weeks = [week(1, 10.1111, injured=[("x", 4.0)]), week(2, 0.0), week(3, 5.2222, True, [("x", 1.5), ("y", 7.0)])]
        total = v1.season_totals(weeks, ["r1"])[0]
        self.assertEqual(15.3333, total["Impact"])
        self.assertEqual((3, 2, True, 1), (total["WeeksComputed"], total["WeeksWithImpact"], total["IsLowerBound"], total["Undeterminable"]))
        self.assertEqual({"Week": 1, "Impact": 10.1111}, total["PeakWeek"])
        self.assertEqual([("y", 7.0, 1), ("x", 5.5, 2)], [(p["CanonicalPlayerID"], p["SingleReturnImpact"], p["Weeks"]) for p in total["TopPlayers"]])


if __name__ == "__main__":
    unittest.main()
