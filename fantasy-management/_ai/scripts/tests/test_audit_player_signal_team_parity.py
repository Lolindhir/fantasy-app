#!/usr/bin/env python3
"""Tests for the Checkpoint 6Z player-signal team shadow/parity audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "audit_player_signal_team_parity.py"
SPEC = importlib.util.spec_from_file_location("audit_player_signal_team_parity", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlayerSignalTeamShadowParityTests(unittest.TestCase):
    def test_classifies_team_presence_deltas(self) -> None:
        self.assertEqual("equal", MODULE.classify_team_delta("NYG", "NYG"))
        self.assertEqual(
            "both_present_different",
            MODULE.classify_team_delta("WSH", "WAS"),
        )
        self.assertEqual(
            "legacy_present_canonical_empty",
            MODULE.classify_team_delta("NYG", None),
        )
        self.assertEqual(
            "legacy_empty_canonical_present",
            MODULE.classify_team_delta(None, "NYG"),
        )

    def test_shadow_population_reasons_only_changes_team_and_external_listing(self) -> None:
        baseline = ["has_nfl_team", "league_owned", "listed_in_external_source"]
        result = MODULE.shadow_population_reasons(
            baseline,
            canonical_team=None,
            any_external_source_listed=False,
        )
        self.assertEqual(["league_owned"], result)

        result = MODULE.shadow_population_reasons(
            ["present_in_external_signal"],
            canonical_team="NYG",
            any_external_source_listed=True,
        )
        self.assertEqual(
            ["has_nfl_team", "listed_in_external_source", "present_in_external_signal"],
            result,
        )

    def test_current_repository_audit_is_structurally_consistent(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        result = MODULE.build(root, config_path)

        self.assertEqual(1, result["schema_version"])
        self.assertEqual("player-signal-team-shadow-parity", result["audit_id"])
        summary = result["summary"]
        self.assertGreater(summary["eligible_player_count"], 100)
        self.assertEqual(
            summary["team_delta_count"],
            sum(summary["team_delta_classes"].values()),
        )
        population = summary["population"]
        self.assertEqual(
            population["shadow_count"],
            population["baseline_count"]
            + population["added_count"]
            - population["removed_count"],
        )
        source_joins = summary["external_source_joins"]
        self.assertEqual(
            source_joins["changed_result_count"],
            sum(source_joins["by_source"].values()),
        )


if __name__ == "__main__":
    unittest.main()
