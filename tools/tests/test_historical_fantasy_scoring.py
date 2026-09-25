from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_fantasy_scoring import (  # noqa: E402
    historical_parity_summary,
    score_record,
    special_teams_event_index_from_payload,
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

    def test_generic_idp_forced_fumble_does_not_score_offensive_position(self) -> None:
        shipley = {
            "Position": "RB",
            "PositionGroup": "RB",
            "Stats": {
                "receptions": 1,
                "receiving_yards": 3,
                "def_fumbles_forced": 1,
            },
        }
        result = score_record(shipley, {"rec": 1.0, "rec_yd": 0.1, "ff": 1.0})
        self.assertEqual(result["FantasyPoints"], 1.3)
        self.assertNotIn(
            "ff",
            [contribution["ScoringKey"] for contribution in result["Contributions"]],
        )

        linebacker = {
            "Position": "LB",
            "PositionGroup": "LB",
            "Stats": {"def_fumbles_forced": 1},
        }
        result = score_record(linebacker, {"ff": 1.0})
        self.assertEqual(result["FantasyPoints"], 1.0)

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

    def test_special_teams_event_settings_without_event_evidence_fail_closed(self) -> None:
        record = {"Position": "WR", "Stats": {"special_teams_tds": 0}}
        scoring = {"st_ff": 1.0, "st_fum_rec": 1.0, "st_tkl_solo": 1.0}
        result = score_record(record, scoring)
        self.assertEqual(
            result["UnsupportedNonZeroSettings"],
            ["st_ff", "st_fum_rec", "st_tkl_solo"],
        )

    def test_kenneth_gainwell_forced_fumble_scores_st_ff(self) -> None:
        record = {"Position": "RB", "Stats": {}}
        scoring = {"st_ff": 1.0, "st_fum_rec": 1.0}
        result = score_record(
            record,
            scoring,
            special_teams_event_values={"st_ff": 1.0, "st_fum_rec": 0.0},
        )
        self.assertEqual(result["FantasyPoints"], 1.0)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])
        self.assertEqual(
            next(
                contribution
                for contribution in result["Contributions"]
                if contribution["ScoringKey"] == "st_ff"
            )["RawValue"],
            1.0,
        )

    def test_ben_skowronek_opponent_recovery_scores_st_fum_rec(self) -> None:
        payload = {
            "Season": 2025,
            "Week": 1,
            "SourceDataset": "nflverse.special-teams-fumble-events",
            "Finalized": True,
            "Records": [
                {
                    "CanonicalPlayerID": "NFLP-7e70774c5662ba0f4786",
                    "GameID": "2025_01_PIT_NYJ",
                    "PlayID": 2977,
                    "Team": "PIT",
                    "EventType": "fumble-recovery",
                    "SpecialTeams": True,
                    "RecoveryTeam": "PIT",
                    "FumbledTeams": ["NYJ"],
                }
            ],
        }
        event_index = special_teams_event_index_from_payload(
            payload,
            season=2025,
            week=1,
        )
        result = score_record(
            {"Position": "WR", "Stats": {"receptions": 1, "receiving_yards": 22, "receiving_tds": 1}},
            {"rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "st_fum_rec": 1.0},
            special_teams_event_values=event_index["NFLP-7e70774c5662ba0f4786"],
        )
        self.assertEqual(result["FantasyPoints"], 10.2)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_treveyon_henderson_own_recovery_does_not_score_st_fum_rec(self) -> None:
        payload = {
            "Season": 2025,
            "Week": 5,
            "SourceDataset": "nflverse.special-teams-fumble-events",
            "Finalized": True,
            "Records": [
                {
                    "CanonicalPlayerID": "NFLP-henderson-fixture",
                    "GameID": "2025_05_NE_BUF",
                    "PlayID": 100,
                    "Team": "NE",
                    "EventType": "fumble-recovery",
                    "SpecialTeams": True,
                    "RecoveryTeam": "NE",
                    "FumbledTeams": ["NE"],
                }
            ],
        }
        event_index = special_teams_event_index_from_payload(
            payload,
            season=2025,
            week=5,
        )
        result = score_record(
            {"Position": "RB", "Stats": {"rushing_yards": 47}},
            {"rush_yd": 0.1, "st_fum_rec": 1.0},
            special_teams_event_values=event_index["NFLP-henderson-fixture"],
        )
        self.assertEqual(result["FantasyPoints"], 4.7)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_ambiguous_special_teams_recovery_relation_fails_closed(self) -> None:
        payload = {
            "Season": 2025,
            "Week": 1,
            "SourceDataset": "nflverse.special-teams-fumble-events",
            "Finalized": True,
            "Records": [
                {
                    "CanonicalPlayerID": "NFLP-ambiguous",
                    "GameID": "2025_01_AAA_BBB",
                    "PlayID": 1,
                    "Team": "AAA",
                    "EventType": "fumble-recovery",
                    "SpecialTeams": True,
                    "RecoveryTeam": "AAA",
                    "FumbledTeams": ["AAA", "BBB"],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "relation is ambiguous"):
            special_teams_event_index_from_payload(payload, season=2025, week=1)

    def test_nonfinal_special_teams_partition_cannot_supply_zero_by_absence(self) -> None:
        payload = {
            "Season": 2000,
            "Week": 3,
            "SourceDataset": "nflverse.special-teams-fumble-events",
            "Finalized": False,
            "Records": [],
        }
        with self.assertRaisesRegex(ValueError, "not finalized"):
            special_teams_event_index_from_payload(payload, season=2000, week=3)

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


class HistoricalFantasyScoringRepositoryParityTests(unittest.TestCase):
    def test_2025_w1_w17_matches_league_points_except_documented_provider_divergence(self) -> None:
        repo_root = TOOLS.parent
        summary = historical_parity_summary(
            repo_root,
            nfl_season=2025,
            weeks=range(1, 18),
            league_id="nfl-reise",
            scoring_season=2025,
        )
        compact = {
            "TotalLeaguePlayerWeeks": summary["TotalLeaguePlayerWeeks"],
            "ComparedPlayerWeeks": summary["ComparedPlayerWeeks"],
            "ExactMatches": summary["ExactMatches"],
            "MissingCanonicalStatZeroPointPlayerWeekCount": len(
                summary["MissingCanonicalStatZeroPointPlayerWeeks"]
            ),
            "MissingCanonicalStatNonZeroPointPlayerWeeks": summary[
                "MissingCanonicalStatNonZeroPointPlayerWeeks"
            ],
            "UnsupportedPlayerWeeks": summary["UnsupportedPlayerWeeks"],
            "ProviderStatDivergences": summary["ProviderStatDivergences"],
            "ScoringMismatches": summary["ScoringMismatches"],
        }
        print("2025 W1-W17 historical scoring parity:")
        print(json.dumps(compact, indent=2, sort_keys=True))

        self.assertEqual([], summary["MissingCanonicalStatNonZeroPointPlayerWeeks"])
        self.assertEqual([], summary["UnsupportedPlayerWeeks"])
        self.assertEqual([], summary["ScoringMismatches"])
        self.assertEqual(2554, summary["ComparedPlayerWeeks"])
        self.assertEqual(2552, summary["ExactMatches"])
        provider_divergences = [
            {
                key: row[key]
                for key in (
                    "Week",
                    "CanonicalPlayerID",
                    "PlayerName",
                    "DerivedPoints",
                    "LeaguePoints",
                    "ProviderFantasyPointsPPR",
                )
            }
            for row in summary["ProviderStatDivergences"]
        ]
        self.assertEqual(
            [
                {
                    "Week": 6,
                    "CanonicalPlayerID": "NFLP-3c5ddc5072f6fe8f9b77",
                    "PlayerName": "Caleb Williams",
                    "DerivedPoints": 20.38,
                    "LeaguePoints": 19.88,
                    "ProviderFantasyPointsPPR": 20.38,
                },
                {
                    "Week": 9,
                    "CanonicalPlayerID": "NFLP-2137c1a93d09e186f935",
                    "PlayerName": "Josh Downs",
                    "DerivedPoints": 17.7,
                    "LeaguePoints": 15.7,
                    "ProviderFantasyPointsPPR": 17.7,
                },
            ],
            provider_divergences,
        )


if __name__ == "__main__":
    unittest.main()
