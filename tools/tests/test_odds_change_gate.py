from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from odds_change_gate import OddsGateConfig, evaluate_game, evaluate_games, next_pending_since


NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
BASE = {"SpreadLine": 3.5, "TotalLine": 44.5, "HomeMoneyline": -180, "OverOdds": -110}
GAME = "2026_06_HOU_JAX"


def decision(observed: dict, *, previous: dict | None = None, minutes: int = 10,
             kickoff: datetime | None = None, pending_minutes: int | None = None):
    return evaluate_game(
        GAME, published=BASE if previous is None else previous,
        observed=observed, observed_at=NOW,
        published_at=NOW - timedelta(minutes=minutes),
        pending_since=(NOW - timedelta(minutes=pending_minutes)) if pending_minutes is not None else None,
        kickoff_at=kickoff,
    )


class SemanticOddsGateTests(unittest.TestCase):
    def test_price_only_changes_do_not_publish_even_after_hour(self):
        observed = {**BASE, "HomeMoneyline": -240, "OverOdds": -130}
        result = decision(observed, minutes=180)
        self.assertFalse(result.publish)
        self.assertEqual(result.reason, "no_relevant_change")

    def test_spread_half_point_is_debounced(self):
        result = decision({**BASE, "SpreadLine": 4.0})
        self.assertFalse(result.publish)
        self.assertEqual(result.spread_delta, Decimal("0.5"))

    def test_total_one_point_is_debounced(self):
        result = decision({**BASE, "TotalLine": 45.5})
        self.assertFalse(result.publish)
        self.assertEqual(result.total_delta, Decimal("1.0"))

    def test_cumulative_change_against_published_not_previous_poll(self):
        # Multiple 0.5 point changes since last publication add up to 1 point.
        self.assertTrue(decision({**BASE, "SpreadLine": 4.5}).publish)
        self.assertEqual(decision({**BASE, "SpreadLine": 4.5}).reason,
                         "large_cumulative_change")

    def test_reversed_change_causes_no_commit(self):
        # An intermediate 4.0 line is irrelevant when back at published 3.5.
        self.assertFalse(decision({**BASE, "SpreadLine": 3.5}).publish)

    def test_total_two_point_cumulative_change_publishes(self):
        self.assertTrue(decision({**BASE, "TotalLine": 46.5}).publish)

    def test_time_gates_only_when_actual_difference_remains(self):
        self.assertFalse(decision({**BASE, "SpreadLine": 4.0}, minutes=180, pending_minutes=59).publish)
        result = decision({**BASE, "SpreadLine": 4.0}, minutes=180, pending_minutes=60)
        self.assertTrue(result.publish)
        self.assertEqual(result.reason, "maximum_age_with_pending_change")
        self.assertFalse(decision(BASE, minutes=120).publish)
        self.assertFalse(decision({**BASE, "SpreadLine": 4.0}, minutes=180).publish)
        self.assertFalse(decision({**BASE, "SpreadLine": 4.0}, minutes=180, pending_minutes=2).publish)

    def test_missing_to_known_and_known_to_missing_are_immediate(self):
        result = decision({**BASE, "SpreadLine": None})
        self.assertTrue(result.publish)
        self.assertEqual(result.reason, "line_availability_changed")
        self.assertTrue(decision(BASE, previous={**BASE, "TotalLine": None}).publish)

    def test_pre_kickoff_flush(self):
        kickoff = NOW + timedelta(minutes=14)
        result = decision({**BASE, "SpreadLine": 4.0}, kickoff=kickoff)
        self.assertTrue(result.publish)
        self.assertEqual(result.reason, "pregame_last_flush")
        later_kickoff = NOW + timedelta(minutes=17)
        self.assertFalse(decision({**BASE, "SpreadLine": 4.0},
                                  kickoff=later_kickoff).publish)

    def test_first_observation_is_publishable(self):
        res = evaluate_game(GAME, published=None, observed=BASE,
                            published_at=None, observed_at=NOW)
        self.assertTrue(res.publish)
        self.assertEqual(res.reason, "first_observation")

    def test_per_game_clock_prevents_starvation(self):
        same = {**BASE, "SpreadLine": 4.0}
        result = evaluate_games(
            published={GAME: BASE, "2026_06_CAR_PHI": BASE},
            observed={GAME: same, "2026_06_CAR_PHI": same},
            published_at_by_game={
                GAME: NOW - timedelta(minutes=61),
                "2026_06_CAR_PHI": NOW - timedelta(minutes=70),
            },
            observed_at=NOW,
            pending_since_by_game={GAME: NOW - timedelta(minutes=61), "2026_06_CAR_PHI": NOW - timedelta(minutes=2)},
        )
        self.assertEqual([x.publish for x in result], [False, True])
        self.assertEqual(result[1].reason, "maximum_age_with_pending_change")

    def test_pending_buffer_starts_on_first_net_change_and_resets_on_reversion(self):
        first = NOW - timedelta(minutes=50)
        observed = {**BASE, "SpreadLine": 4.0}
        pending = next_pending_since(
            published=BASE, observed=observed,
            previous_pending_since=None, observed_at=first,
        )
        self.assertEqual(pending, first)
        pending = next_pending_since(
            published=BASE, observed={**BASE, "SpreadLine": 4.5},
            previous_pending_since=pending, observed_at=NOW,
        )
        self.assertEqual(pending, first)
        self.assertFalse(decision({**BASE, "SpreadLine": 4.0},
                                  minutes=180, pending_minutes=50).publish)
        self.assertIsNone(next_pending_since(
            published=BASE, observed={**BASE, "HomeMoneyline": -999},
            previous_pending_since=pending, observed_at=NOW,
        ))
        again = next_pending_since(
            published=BASE, observed=observed,
            previous_pending_since=None, observed_at=NOW,
        )
        self.assertEqual(again, NOW)
        self.assertFalse(decision(observed, minutes=180, pending_minutes=0).publish)

    def test_pending_buffer_price_changes_never_start_clock(self):
        self.assertIsNone(next_pending_since(
            published=BASE, observed={**BASE, "OverOdds": -120},
            previous_pending_since=None, observed_at=NOW,
        ))

    def test_invalid_data_fail_closed(self):
        for value in (float("nan"), float("inf"), "3.5", True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decision({**BASE, "SpreadLine": value})
        with self.assertRaises(ValueError):
            evaluate_game(GAME, published=BASE, observed=BASE,
                          published_at=NOW.replace(tzinfo=None), observed_at=NOW)
        with self.assertRaises(ValueError):
            OddsGateConfig(major_spread_points=Decimal("0"))
        with self.assertRaises(ValueError):
            evaluate_games(
                published={GAME: BASE}, observed={}, published_at_by_game={GAME: NOW},
                observed_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
