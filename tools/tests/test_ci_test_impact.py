"""CP1 classifier regression fixtures; no production CI routing is changed."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import ci_test_impact as ci


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {"tests": [
            {"path": "tools/tests/test_nfl_source_historical_identity_replay.py",
             "tier": "deep", "deepGroups": ["nfl-identity-replay"],
             "currentPrCoverage": "build"},
            {"path": "tools/tests/test_market_observations_full_restore.py",
             "tier": "deep", "deepGroups": ["market-restore"],
             "currentPrCoverage": "build"},
            {"path": "tools/tests/test_ci_test_impact.py",
             "tier": "fast", "deepGroups": [], "currentPrCoverage": "shadow"},
        ]}

    def choose(self, *paths):
        return ci.select([{"filename": p, "status": "modified"} for p in paths], self.inventory)

    def test_docs_and_angular_are_fast_only(self):
        self.assertEqual([], self.choose("docs/contributing.md")["selected"])
        self.assertEqual([], self.choose("src/app/app.component.ts")["selected"])

    def test_historical_replay_test_edits_select_its_deep_group(self):
        result = self.choose("tools/tests/test_nfl_source_historical_identity_replay.py")
        self.assertEqual(["nfl-identity-replay"], result["selected"])
        self.assertFalse(result["uncertain"])

    def test_identity_mapping_selects_full_cross_provider_closure(self):
        self.assertEqual(set(ci.GROUPS), set(self.choose(
            "data-source/nfl/identities/provider-mappings.json")["selected"]))

    def test_nfl_source_code_changes_select_affected_deep(self):
        self.assertEqual(set(ci.GROUPS), set(self.choose(
            "tools/nfl_source_data_lib/phase1.py")["selected"]))

    def test_scoring_changes_include_identity_and_twp_parity(self):
        groups = self.choose("tools/player_week_fantasy_materialize.py")["selected"]
        self.assertIn("nfl-identity-replay", groups)
        self.assertIn("league-pwf-twp", groups)

    def test_market_changes_require_market_restore(self):
        groups = self.choose("tools/external_source/market_observations.py")["selected"]
        self.assertEqual({"market-restore", "consumer-restore"}, set(groups))

    def test_union_for_multicomponent_changes(self):
        groups = self.choose("data-source/market/provider/sample.json",
                             "data-source/leagues/nfl-reise/seasons/2026/league.json")["selected"]
        self.assertEqual({"market-restore", "consumer-restore", "league-pwf-twp"}, set(groups))

    def test_workflow_timeout_only_is_still_full_deep_in_cp1(self):
        result = self.choose(".github/workflows/sync-nfl-source-data.yml")
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))
        self.assertTrue(result["uncertain"])  # CP3 semantic diff exception needs proof first

    def test_unclassified_new_test_requires_all_deep(self):
        result = self.choose("tools/tests/test_new_file.py")
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))
        self.assertTrue(result["uncertain"])

    def test_renames_deletions_and_invalid_status_fail_closed(self):
        for status in ("removed", "renamed", "copied", "unrecognized"):
            result = ci.select([{"filename": "src/app/app.spec.ts", "status": status}], self.inventory)
            self.assertEqual(set(ci.GROUPS), set(result["selected"]))
            self.assertTrue(result["uncertain"])

    def test_empty_or_missing_diff_fails_closed(self):
        result = ci.select([], self.inventory)
        self.assertTrue(result["uncertain"])
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))

    def test_policy_manifest_and_selector_changes_force_deep(self):
        for path in (".github/ci-test-inventory.json",
                     "tools/ci_test_impact.py",
                     ".ai-context/manual/workflow-monitoring.yaml"):
            self.assertEqual(set(ci.GROUPS), set(self.choose(path)["selected"]))

    def test_unknown_non_doc_code_force_deep(self):
        result = self.choose("scripts/surprise_pipeline.js")
        self.assertTrue(result["uncertain"])
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))


class InventoryTests(unittest.TestCase):
    def test_current_repository_has_exact_test_coverage(self):
        # Run against the checked-out PR revision, not an environment-side copy.
        data = ci.read_inventory()
        result = ci.validate(ci.ROOT, data)
        self.assertGreater(result["total"], 200)
        self.assertGreater(result["currentlyInPr"], 100)

    def test_missing_registration_is_rejected(self):
        data = ci.read_inventory()
        missing = data["tests"].pop()
        with self.assertRaisesRegex(ValueError, "Inventory drift"):
            ci.validate(ci.ROOT, data)
        self.assertTrue(missing["path"])

    def test_corrupt_classification_is_rejected(self):
        data = ci.read_inventory()
        data["tests"][0]["tier"] = "deep"
        data["tests"][0]["deepGroups"] = []
        with self.assertRaisesRegex(ValueError, "Deep tests require"):
            ci.validate(ci.ROOT, data)


if __name__ == "__main__":
    unittest.main()
