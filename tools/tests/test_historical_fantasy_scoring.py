from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_fantasy_scoring import score_record  # noqa: E402


class HistoricalFantasyScoringTests(unittest.TestCase):
    def test_skill_player_can_be_rescored_with_explicit_profile(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "receptions": 8,
                "receiving_yards": 125,
                "receiving_tds": 1,
                "rushing_yards": 4,
                "rushing_tds": 0,
                "fumbles_lost_total": 0,
            },
        }
        scoring = {
            "rec": 1.0,
            "rec_yd": 0.1,
            "rec_td": 6.0,
            "rush_yd": 0.1,
            "rush_td": 6.0,
            "fum_lost": -2.0,
            "def_td": 6.0,
        }
        result = score_record(record, scoring)
        self.assertAlmostEqual(result["FantasyPoints"], 26.9)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_profile_change_recalculates_without_changing_raw_facts(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {"receptions": 10, "receiving_yards": 100, "receiving_tds": 0},
        }
        ppr = score_record(record, {"rec": 1.0, "rec_yd": 0.1})
        half_ppr = score_record(record, {"rec": 0.5, "rec_yd": 0.1})
        self.assertEqual(ppr["FantasyPoints"], 20.0)
        self.assertEqual(half_ppr["FantasyPoints"], 15.0)
        self.assertEqual(record["Stats"]["receptions"], 10)

    def test_current_nflverse_passing_interception_field_is_used(self) -> None:
        record = {
            "Position": "QB",
            "Stats": {
                "passing_yards": 250,
                "passing_tds": 2,
                "passing_interceptions": 1,
            },
        }
        result = score_record(record, {"pass_yd": 0.04, "pass_td": 4.0, "pass_int": -1.0})
        self.assertEqual(result["FantasyPoints"], 17.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_fumble_recovery_profile_uses_current_nflverse_aggregate_fields(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "fumbles_total": 0,
                "fumbles_lost_total": 0,
                "fumble_recovery_own": 1,
                "fumble_recovery_opp": 0,
                "fumble_recovery_tds": 1,
            },
        }
        result = score_record(record, {"fum_rec": 2.0, "fum_rec_td": 6.0})
        self.assertEqual(result["FantasyPoints"], 8.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_kicker_profile_uses_distance_buckets_and_blocked_kicks_count_as_misses(self) -> None:
        record = {
            "Position": "K",
            "Stats": {
                "fg_att": 4,
                "fg_made": 3,
                "fg_made_0_19": 0,
                "fg_made_20_29": 0,
                "fg_made_30_39": 1,
                "fg_made_40_49": 1,
                "fg_made_50_59": 0,
                "fg_made_60_": 1,
                "pat_att": 3,
                "pat_made": 2,
            },
        }
        scoring = {
            "fgm_0_19": 3.0,
            "fgm_20_29": 3.0,
            "fgm_30_39": 3.0,
            "fgm_40_49": 4.0,
            "fgm_50_59": 5.0,
            "fgm_60p": 6.0,
            "fgmiss": -1.0,
            "xpm": 1.0,
            "xpmiss": -1.0,
        }
        result = score_record(record, scoring)
        self.assertEqual(result["FantasyPoints"], 13.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_unimplemented_distance_specific_miss_scoring_fails_closed(self) -> None:
        record = {"Position": "K", "Stats": {"fg_att": 1, "fg_made": 0}}
        result = score_record(record, {"fgmiss_0_19": -2.0})
        self.assertEqual(result["UnsupportedNonZeroSettings"], ["fgmiss_0_19"])

    def test_missing_applicable_mapping_is_explicit(self) -> None:
        record = {"Position": "WR", "Stats": {"receiving_yards": 100}}
        result = score_record(record, {"bonus_rec_yd_100": 3.0})
        self.assertEqual(result["UnsupportedNonZeroSettings"], ["bonus_rec_yd_100"])


if __name__ == "__main__":
    unittest.main()
