#!/usr/bin/env python3
"""Tests for Checkpoint 6Z.4 population-policy adjudication."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "audit_player_signal_population_policy.py"
SPEC = importlib.util.spec_from_file_location("audit_player_signal_population_policy", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlayerSignalPopulationPolicyAuditTests(unittest.TestCase):
    def test_provider_context_shape_keeps_provider_evidence_distinct(self) -> None:
        self.assertEqual(
            "none",
            MODULE.provider_context_shape(
                canonical_team_present=False, tank01_is_free_agent=True
            ),
        )
        self.assertEqual(
            "sleeper_team_only",
            MODULE.provider_context_shape(
                canonical_team_present=True, tank01_is_free_agent=True
            ),
        )
        self.assertEqual(
            "tank01_not_free_agent_only",
            MODULE.provider_context_shape(
                canonical_team_present=False, tank01_is_free_agent=False
            ),
        )
        self.assertEqual(
            "sleeper_team_and_tank01_not_free_agent",
            MODULE.provider_context_shape(
                canonical_team_present=True, tank01_is_free_agent=False
            ),
        )

    def test_roster_position_normalizes_running_back_variants(self) -> None:
        self.assertEqual("RB", MODULE.roster_fantasy_position("FB"))
        self.assertEqual("RB", MODULE.roster_fantasy_position("HB"))
        self.assertEqual("TE", MODULE.roster_fantasy_position("TE"))
        self.assertIsNone(MODULE.roster_fantasy_position("OL"))

    def test_policy_variants_do_not_promote_previous_or_provider_context_silently(self) -> None:
        row = {
            "baseline_population_reasons": ["has_nfl_team"],
            "latest_weekly_roster_member": False,
            "current_season_canonical_history_member": False,
            "previous_season_canonical_history_member": True,
            "canonical_team": "AAA",
            "tank01_is_free_agent": False,
        }
        result = MODULE.evaluate_policy_variants(row)
        self.assertFalse(result["current_canonical"])
        self.assertTrue(result["current_plus_previous_history"])
        self.assertTrue(result["current_plus_provider_context"])
        self.assertTrue(result["current_plus_previous_and_provider_context"])

    def test_non_bridge_fantasy_relevance_is_preserved_by_every_policy(self) -> None:
        row = {
            "baseline_population_reasons": ["listed_in_external_source"],
            "latest_weekly_roster_member": False,
            "current_season_canonical_history_member": False,
            "previous_season_canonical_history_member": False,
            "canonical_team": None,
            "tank01_is_free_agent": True,
        }
        self.assertTrue(all(MODULE.evaluate_policy_variants(row).values()))

    def test_current_repository_policy_audit_is_structurally_consistent(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        result = MODULE.build(root, config_path)

        self.assertEqual(1, result["schema_version"])
        self.assertEqual(
            "player-signal-population-policy-adjudication", result["audit_id"]
        )
        self.assertEqual("analysis_only_no_population_change", result["runtime_effect"])

        baseline = result["baseline"]
        variants = result["policy_variants"]
        candidate = result["candidate_policy"]
        self.assertEqual("current_canonical", candidate["variant"])

        for name, summary in variants.items():
            self.assertIn(name, MODULE.POLICY_VARIANTS)
            self.assertEqual(
                summary["player_count"],
                baseline["player_count"] + summary["added_count"] - summary["removed_count"],
            )
            self.assertEqual(0, summary["league_owned_removed_count"])
            self.assertEqual(0, summary["managed_roster_players_removed_count"])

        quality = result["canonical_history_quality"]
        self.assertGreater(quality["latest_week"], 0)
        self.assertGreater(quality["current_season_weekly_history"]["partition_count"], 0)
        self.assertGreater(quality["previous_season_weekly_history"]["partition_count"], 0)

        cohorts = result["recommended_removal_cohorts"]
        self.assertEqual(
            variants[candidate["variant"]]["removed_count"],
            sum(cohort["count"] for cohort in cohorts.values()),
        )
        self.assertEqual(
            variants[candidate["variant"]]["kicker_candidates_removed_count"],
            result["removed_kicker_adjudication"]["count"],
        )

        provider_rows = result["provider_context_exceptions"]["players"]
        self.assertEqual(cohorts["provider_context_exception"]["count"], len(provider_rows))
        self.assertTrue(
            all(
                row["canonical_team"] or row["tank01_is_free_agent"] is False
                for row in provider_rows
            )
        )

        current_identity_gap_count = result["current_identity_gap_candidates"]["count"]
        if result["decision_status"] == "blocked_on_current_canonical_identity_coverage":
            self.assertGreater(current_identity_gap_count, 0)
        else:
            self.assertEqual(
                "policy_ready_for_runtime_cutover_design", result["decision_status"]
            )
            self.assertEqual(0, current_identity_gap_count)

        print(
            "6Z4_POPULATION_POLICY_AUDIT="
            + json.dumps(MODULE.compact_summary(result), sort_keys=True),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
