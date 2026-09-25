#!/usr/bin/env python3
"""Tests for Checkpoint 6Z.2 population relevance audit."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "audit_player_signal_population_relevance.py"
SPEC = importlib.util.spec_from_file_location("audit_player_signal_population_relevance", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlayerSignalPopulationRelevanceAuditTests(unittest.TestCase):
    def test_candidate_contracts_keep_fantasy_relevance_independent(self) -> None:
        result = MODULE.evaluate_contracts(
            non_bridge_relevant=True,
            canonical_team_present=False,
            tank01_is_free_agent=True,
            latest_weekly_roster_member=False,
            season_roster_member=False,
        )
        self.assertTrue(all(result.values()))

    def test_candidate_contracts_keep_signals_separate(self) -> None:
        result = MODULE.evaluate_contracts(
            non_bridge_relevant=False,
            canonical_team_present=False,
            tank01_is_free_agent=False,
            latest_weekly_roster_member=True,
            season_roster_member=False,
        )
        self.assertFalse(result["canonical_sleeper_team_or_fantasy_relevance"])
        self.assertTrue(result["tank01_not_free_agent_or_fantasy_relevance"])
        self.assertTrue(result["latest_weekly_roster_or_fantasy_relevance"])
        self.assertFalse(result["season_roster_or_fantasy_relevance"])
        self.assertTrue(result["weekly_or_season_roster_or_fantasy_relevance"])
        self.assertTrue(result["structured_union_or_fantasy_relevance"])

    def test_roster_membership_can_resolve_by_sleeper_or_canonical_id(self) -> None:
        identities = {
            "p1": {"CanonicalPlayerID": "c1"},
            "p2": {"CanonicalPlayerID": "c2"},
        }
        document = {
            "Records": [
                {
                    "CanonicalPlayerID": "c1",
                    "SourceIDs": {"Sleeper": "p1"},
                },
                {
                    "CanonicalPlayerID": "c2",
                    "SourceIDs": {},
                },
            ]
        }
        membership = MODULE.build_roster_membership_index(
            document,
            identities,
            source_name="fixture",
        )
        self.assertTrue(MODULE.in_roster_membership("p1", identities["p1"], membership))
        self.assertTrue(MODULE.in_roster_membership("p2", identities["p2"], membership))

    def test_roster_membership_keeps_canonical_id_sticky_across_sleeper_mapping_drift(self) -> None:
        identity = {"CanonicalPlayerID": "c1"}
        membership = MODULE.build_roster_membership_index(
            {
                "Records": [
                    {
                        "CanonicalPlayerID": "historical-canonical-id",
                        "SourceIDs": {"Sleeper": "p1"},
                    }
                ]
            },
            {"p1": identity},
            source_name="fixture",
        )
        self.assertFalse(MODULE.in_roster_membership("p1", identity, membership))
        self.assertEqual(1, membership["current_sleeper_mapping_mismatch_count"])
        self.assertIn("historical-canonical-id", membership["canonical_ids"])

    def test_current_repository_population_audit_is_structurally_consistent(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        result = MODULE.build(root, config_path)

        self.assertEqual(1, result["schema_version"])
        self.assertEqual("player-signal-population-relevance", result["audit_id"])

        baseline = result["baseline"]
        self.assertGreater(baseline["player_count"], 100)
        self.assertGreater(baseline["exclusive_has_nfl_team_count"], 0)
        self.assertEqual(
            baseline["player_count"],
            baseline["free_agent_count"] + baseline["league_owned_count"],
        )

        bridge = result["exclusive_legacy_bridge"]
        self.assertEqual(baseline["exclusive_has_nfl_team_count"], bridge["count"])
        self.assertEqual(bridge["count"], sum(bridge["tank01_is_free_agent"].values()))
        self.assertEqual(bridge["count"], sum(bridge["sleeper_status"].values()))
        self.assertEqual(bridge["count"], sum(bridge["latest_weekly_roster_member"].values()))
        self.assertEqual(bridge["count"], sum(bridge["season_roster_member"].values()))

        for name, summary in result["candidate_contracts"].items():
            self.assertIn(name, MODULE.CANDIDATE_CONTRACTS)
            self.assertEqual(
                summary["player_count"],
                baseline["player_count"] + summary["added_count"] - summary["removed_count"],
            )
            self.assertEqual(
                summary["free_agent_count"],
                baseline["free_agent_count"]
                + summary["free_agent_added_count"]
                - summary["free_agent_removed_count"],
            )
            self.assertEqual(
                0,
                summary["league_owned_removed_count"],
                f"{name} must preserve all current fantasy-owned players",
            )
            self.assertEqual(
                0,
                summary["managed_roster_players_removed_count"],
                f"{name} must preserve the current managed roster",
            )

        print(
            "6Z2_POPULATION_RELEVANCE_AUDIT="
            + json.dumps(MODULE.compact_summary(result), sort_keys=True),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
