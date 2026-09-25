from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_fantasy_scoring import (  # noqa: E402
    load_special_teams_fumble_events_for_player,
    score_record,
)


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
                "def_tds": 0,
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

    def test_fum_rec_is_defensive_recovery_not_own_offensive_recovery(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "fumble_recovery_own": 2,
                "fumble_recovery_opp": 0,
                "def_fumbles": 0,
                "fumble_recovery_tds": 0,
            },
        }
        result = score_record(record, {"fum_rec": 2.0})
        self.assertEqual(result["FantasyPoints"], 0.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_individual_defensive_fumble_recovery_can_score_fum_rec(self) -> None:
        record = {
            "Position": "LB",
            "Stats": {"def_fumbles": 1},
        }
        result = score_record(record, {"fum_rec": 2.0})
        self.assertEqual(result["FantasyPoints"], 2.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_rashid_shaheed_special_teams_touchdown_scores_with_offense(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "receptions": 4,
                "receiving_yards": 67,
                "special_teams_tds": 1,
            },
        }
        result = score_record(record, {"rec": 1.0, "rec_yd": 0.1, "st_td": 6.0})
        self.assertEqual(result["FantasyPoints"], 16.7)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_brandon_aubrey_kicker_can_also_score_rushing_yards(self) -> None:
        record = {
            "Position": "K",
            "Stats": {
                "rushing_yards": 6,
                "fg_att": 6,
                "fg_made": 4,
                "fg_made_20_29": 1,
                "fg_made_30_39": 1,
                "fg_made_40_49": 2,
                "fg_made_50_59": 0,
                "fg_made_60_": 0,
                "pat_att": 2,
                "pat_made": 2,
            },
        }
        scoring = {
            "rush_yd": 0.1,
            "fgm_20_29": 3.0,
            "fgm_30_39": 3.0,
            "fgm_40_49": 4.0,
            "fgm_50_59": 5.0,
            "fgm_60p": 6.0,
            "fgmiss": -1.0,
            "xpm": 1.0,
        }
        result = score_record(record, scoring)
        self.assertEqual(result["FantasyPoints"], 14.6)
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

    def test_team_defense_only_settings_are_not_applied_to_player_rows(self) -> None:
        record = {"Position": "WR", "Stats": {"special_teams_tds": 0}}
        scoring = {
            "def_st_td": 6.0,
            "pts_allow_0": 10.0,
            "yds_allow_0_100": 5.0,
        }
        result = score_record(record, scoring)
        self.assertEqual(result["FantasyPoints"], 0.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_special_teams_event_settings_require_explicit_event_evidence(self) -> None:
        record = {"Position": "WR", "Stats": {"special_teams_tds": 0}}
        scoring = {"st_ff": 1.0, "st_fum_rec": 1.0, "st_tkl_solo": 1.0}
        result = score_record(record, scoring)
        self.assertEqual(
            result["UnsupportedNonZeroSettings"],
            ["st_ff", "st_fum_rec", "st_tkl_solo"],
        )

        with_evidence = score_record(
            record,
            scoring,
            special_teams_fumble_events=[],
        )
        self.assertEqual(
            with_evidence["UnsupportedNonZeroSettings"],
            ["st_tkl_solo"],
        )

    def test_kenneth_gainwell_special_teams_forced_fumble_scores_st_ff(self) -> None:
        record = {"Position": "RB", "Stats": {}}
        events = [
            {
                "CanonicalPlayerID": "NFLP-aba4437dc0913f51cede",
                "GameID": "2025_01_PIT_NYJ",
                "PlayID": 2977,
                "EventType": "forced-fumble",
                "SpecialTeams": True,
            }
        ]
        result = score_record(
            record,
            {"st_ff": 1.0},
            special_teams_fumble_events=events,
        )
        self.assertEqual(result["FantasyPoints"], 1.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_ben_skowronek_opponent_recovery_scores_st_fum_rec(self) -> None:
        record = {"Position": "WR", "Stats": {}}
        events = [
            {
                "CanonicalPlayerID": "NFLP-7e70774c5662ba0f4786",
                "GameID": "2025_01_PIT_NYJ",
                "PlayID": 2977,
                "EventType": "fumble-recovery",
                "SpecialTeams": True,
                "RecoveryTeam": "PIT",
                "FumbledTeams": ["NYJ"],
            }
        ]
        result = score_record(
            record,
            {"st_fum_rec": 1.0},
            special_teams_fumble_events=events,
        )
        self.assertEqual(result["FantasyPoints"], 1.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_treveyon_henderson_own_team_recovery_does_not_score_st_fum_rec(self) -> None:
        record = {"Position": "RB", "Stats": {}}
        events = [
            {
                "CanonicalPlayerID": "NFLP-3b1c31dbb09b5b6ff652",
                "GameID": "2025_05_NE_BUF",
                "PlayID": 1,
                "EventType": "fumble-recovery",
                "SpecialTeams": True,
                "RecoveryTeam": "NE",
                "FumbledTeams": ["NE"],
            }
        ]
        result = score_record(
            record,
            {"st_fum_rec": 1.0},
            special_teams_fumble_events=events,
        )
        self.assertEqual(result["FantasyPoints"], 0.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_ambiguous_special_teams_recovery_relation_fails_closed(self) -> None:
        record = {"Position": "WR", "Stats": {}}
        events = [
            {
                "EventType": "fumble-recovery",
                "SpecialTeams": True,
                "RecoveryTeam": "PIT",
                "FumbledTeams": ["PIT", "NYJ"],
            }
        ]
        with self.assertRaisesRegex(ValueError, "ambiguous fumble-team relation"):
            score_record(
                record,
                {"st_fum_rec": 1.0},
                special_teams_fumble_events=events,
            )

    def test_nonfinal_special_teams_partition_cannot_supply_zero_by_absence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source-data/nfl/special-teams-fumble-events/2000/03.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 2,
                        "Season": 2000,
                        "Week": 3,
                        "SourceDataset": "nflverse.special-teams-fumble-events",
                        "Finalized": False,
                        "Records": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not finalized"):
                load_special_teams_fumble_events_for_player(
                    root,
                    2000,
                    3,
                    "NFLP-test",
                )

    def test_unimplemented_distance_specific_miss_scoring_fails_closed(self) -> None:
        record = {"Position": "K", "Stats": {"fg_att": 1, "fg_made": 0}}
        result = score_record(record, {"fgmiss_0_19": -2.0})
        self.assertEqual(result["UnsupportedNonZeroSettings"], ["fgmiss_0_19"])

    def test_missing_applicable_mapping_is_explicit(self) -> None:
        record = {"Position": "WR", "Stats": {"receiving_yards": 100}}
        result = score_record(record, {"bonus_rec_yd_100": 3.0})
        self.assertEqual(result["UnsupportedNonZeroSettings"], ["bonus_rec_yd_100"])

    def test_position_specific_bonus_does_not_block_other_positions(self) -> None:
        record = {"Position": "WR", "Stats": {"receptions": 1}}
        result = score_record(record, {"bonus_rec_te": 0.5, "rec": 1.0})
        self.assertEqual(result["FantasyPoints"], 1.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])


if __name__ == "__main__":
    unittest.main()
