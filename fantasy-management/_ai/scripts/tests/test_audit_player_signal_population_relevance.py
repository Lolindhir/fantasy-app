#!/usr/bin/env python3
"""Tests for the Checkpoint 6Z.2 player population-relevance audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "audit_player_signal_population_relevance.py"
)
SPEC = importlib.util.spec_from_file_location(
    "audit_player_signal_population_relevance",
    SCRIPT_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlayerSignalPopulationRelevanceAuditTests(unittest.TestCase):
    def test_boolean_bucket_preserves_unknown(self) -> None:
        self.assertEqual("true", MODULE.boolean_bucket(True))
        self.assertEqual("false", MODULE.boolean_bucket(False))
        self.assertEqual("null", MODULE.boolean_bucket(None))

    def test_policy_preserves_non_bridge_relevance(self) -> None:
        candidates = {
            "1": {
                "non_bridge_reasons": ["league_owned"],
                "member": False,
            },
            "2": {
                "non_bridge_reasons": [],
                "member": True,
            },
            "3": {
                "non_bridge_reasons": [],
                "member": False,
            },
        }
        result = MODULE.evaluate_policy(
            candidates,
            {"1", "3"},
            lambda candidate: candidate["member"],
        )

        self.assertEqual(2, result["player_count"])
        self.assertEqual(0, result["delta"])
        self.assertEqual(["3"], result["removed_player_ids"])
        self.assertEqual(["2"], result["added_player_ids"])

    def test_current_repository_audit_is_structurally_consistent(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = (
            root / "fantasy-management/automation/player-signal-materialization.json"
        )
        result = MODULE.build(root, config_path)

        self.assertEqual(1, result["schema_version"])
        self.assertEqual("player-signal-population-relevance", result["audit_id"])

        baseline = result["baseline"]
        summary = result["summary"]
        self.assertGreater(baseline["player_count"], 100)
        self.assertEqual(
            baseline["exact_reason_sets"].get("has_nfl_team", 0),
            summary["bridge_only_count"],
        )

        sources = result["canonical_nfl_roster_sources"]
        self.assertGreater(sources["current_season"]["resolved_player_count"], 500)
        self.assertGreater(sources["latest_weekly"]["resolved_player_count"], 500)
        self.assertGreater(sources["latest_weekly"]["week"], 0)
        self.assertGreater(sources["previous_season"]["resolved_player_count"], 500)

        policies = summary["policies"]
        expected_policies = {
            "canonical_sleeper_team",
            "latest_weekly_nfl_membership",
            "current_season_nfl_history",
            "current_plus_previous_season_nfl_history",
            "current_season_or_tank01_not_free_agent",
        }
        self.assertEqual(expected_policies, set(policies))

        for policy in policies.values():
            self.assertEqual(
                baseline["player_count"] + policy["delta"],
                policy["player_count"],
            )
            self.assertEqual(
                policy["removed_count"],
                len(policy["removed_player_ids"]),
            )
            self.assertEqual(
                policy["added_count"],
                len(policy["added_player_ids"]),
            )
            self.assertFalse(
                set(policy["removed_player_ids"])
                & set(policy["added_player_ids"])
            )
            for impact in policy["downstream"].values():
                self.assertEqual(
                    impact["current_player_count"] - impact["removed_count"],
                    impact["projected_player_count_after_removals"],
                )

        current_season = policies["current_season_nfl_history"]
        recent_history = policies["current_plus_previous_season_nfl_history"]
        self.assertLessEqual(
            recent_history["removed_count"],
            current_season["removed_count"],
        )

        signal_roles = result["signal_roles"]
        self.assertEqual(
            "current_nfl_membership",
            signal_roles["canonical_weekly_nfl_roster"]["population_role"],
        )
        self.assertEqual(
            "recent_nfl_history",
            signal_roles["canonical_season_nfl_roster"]["population_role"],
        )
        self.assertEqual(
            "diagnostic_secondary_evidence",
            signal_roles["tank01_is_free_agent"]["population_role"],
        )
        self.assertEqual(
            "context_only",
            signal_roles["canonical_sleeper_team"]["population_role"],
        )
        self.assertEqual(
            "unavailable",
            signal_roles["nfl_contracts"]["population_role"],
        )


if __name__ == "__main__":
    unittest.main()
