from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy import (  # noqa: E402
    build_player_week_fantasy_contract,
    build_player_week_fantasy_record,
    build_scoring_profile_identity,
    canonical_scoring_settings,
    derive_actual_points,
    scoring_settings_fingerprint,
)


class PlayerWeekFantasyContractTests(unittest.TestCase):
    def test_scoring_fingerprint_is_semantic_and_deterministic(self) -> None:
        first = {
            "rec": 1.0,
            "rec_yd": 0.1,
            "pass_td": 4,
            "unused": 0.0,
        }
        reordered = {
            "unused": -0.0,
            "pass_td": "4.000",
            "rec_yd": "0.1000",
            "rec": 1,
        }

        self.assertEqual(
            canonical_scoring_settings(first),
            {"pass_td": "4", "rec": "1", "rec_yd": "0.1"},
        )
        self.assertEqual(
            scoring_settings_fingerprint(first),
            "sha256:f2839612ddd466910a27aa5c73b0f6a92156a84c042ce8dfe5b7243bc176377b",
        )
        self.assertEqual(
            scoring_settings_fingerprint(first),
            scoring_settings_fingerprint(reordered),
        )

    def test_active_scoring_change_invalidates_fingerprint(self) -> None:
        ppr = {"rec": 1.0, "rec_yd": 0.1}
        half_ppr = {"rec": 0.5, "rec_yd": 0.1}
        self.assertNotEqual(
            scoring_settings_fingerprint(ppr),
            scoring_settings_fingerprint(half_ppr),
        )

    def test_same_settings_can_back_multiple_league_identities(self) -> None:
        settings = {"rec": 1.0, "rec_yd": 0.1}
        league_a = build_scoring_profile_identity("league-a", 2026, settings)
        league_b = build_scoring_profile_identity("league-b", 2026, settings)

        self.assertEqual(league_a["SettingsHash"], league_b["SettingsHash"])
        self.assertNotEqual(league_a["CanonicalLeagueID"], league_b["CanonicalLeagueID"])

    def test_actual_derivation_reuses_settings_driven_canonical_scorer(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "receptions": 10,
                "receiving_yards": 100,
            },
        }
        self.assertEqual(
            derive_actual_points(record, {"rec": 1.0, "rec_yd": 0.1}),
            20.0,
        )
        self.assertEqual(
            derive_actual_points(record, {"rec": 0.5, "rec_yd": 0.1}),
            15.0,
        )

    def test_available_projection_and_final_zero_actual_are_valid(self) -> None:
        record = build_player_week_fantasy_record(
            "NFLP-test",
            projection={
                "Status": "available",
                "Points": 16.8,
                "PredictionRange": {"Level": 0.90, "Lower": 8.4, "Upper": 29.7},
                "RangeQuality": "player-volatility",
                "HistoryGames": 27,
                "ParticipationCondition": "conditional-on-participation",
                "AvailabilityAdjustmentApplied": False,
                "PointModel": "V4-C",
                "IntervalModel": "V4-C-PI1",
            },
            actual={"Points": 0, "State": "final"},
        )
        self.assertEqual(record["Actual"], {"Points": 0.0, "State": "final"})
        self.assertEqual(record["Projection"]["Points"], 16.8)

    def test_unavailable_projection_cannot_hide_numeric_points(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be null"):
            build_player_week_fantasy_record(
                "NFLP-test",
                projection={
                    "Status": "insufficient-history",
                    "Points": 3.0,
                    "PredictionRange": None,
                    "RangeQuality": "unavailable",
                    "HistoryGames": 0,
                    "ParticipationCondition": "conditional-on-participation",
                    "AvailabilityAdjustmentApplied": False,
                    "PointModel": "V4-C",
                    "IntervalModel": "V4-C-PI1",
                },
                actual={"Points": None, "State": "pending"},
            )

    def test_prediction_range_must_be_ordered(self) -> None:
        with self.assertRaisesRegex(ValueError, "Lower must not exceed Upper"):
            build_player_week_fantasy_record(
                "NFLP-test",
                projection={
                    "Status": "available",
                    "Points": 16.8,
                    "PredictionRange": {"Level": 0.90, "Lower": 30.0, "Upper": 10.0},
                    "RangeQuality": "player-volatility",
                    "HistoryGames": 27,
                    "ParticipationCondition": "conditional-on-participation",
                    "AvailabilityAdjustmentApplied": False,
                    "PointModel": "V4-C",
                    "IntervalModel": "V4-C-PI1",
                },
                actual={"Points": None, "State": "pending"},
            )

    def test_contract_sorts_records_and_rejects_duplicates(self) -> None:
        scoring_profile = build_scoring_profile_identity(
            "league-a",
            2026,
            {"rec": 1.0},
        )

        def unavailable(player_id: str) -> dict:
            return build_player_week_fantasy_record(
                player_id,
                projection={
                    "Status": "no-game",
                    "Points": None,
                    "PredictionRange": None,
                    "RangeQuality": "unavailable",
                    "HistoryGames": 3,
                    "ParticipationCondition": "conditional-on-participation",
                    "AvailabilityAdjustmentApplied": False,
                    "PointModel": "V4-C",
                    "IntervalModel": "V4-C-PI1",
                },
                actual={"Points": None, "State": "pending"},
            )

        contract = build_player_week_fantasy_contract(
            canonical_league_id="league-a",
            season=2026,
            week=4,
            scoring_profile=scoring_profile,
            records=[unavailable("NFLP-z"), unavailable("NFLP-a")],
        )
        self.assertEqual(
            [record["CanonicalPlayerID"] for record in contract["Records"]],
            ["NFLP-a", "NFLP-z"],
        )

        with self.assertRaisesRegex(ValueError, "Duplicate CanonicalPlayerID"):
            build_player_week_fantasy_contract(
                canonical_league_id="league-a",
                season=2026,
                week=4,
                scoring_profile=scoring_profile,
                records=[unavailable("NFLP-a"), unavailable("NFLP-a")],
            )


if __name__ == "__main__":
    unittest.main()
