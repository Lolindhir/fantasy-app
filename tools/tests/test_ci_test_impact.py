"""Regression contracts for CP1 inventory, CP2 Fast and CP3 fail-closed Deep."""
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

    def test_new_python_typescript_javascript_powershell_tests_are_discoverable(self):
        for path in ("tools/tests/feature_test.py", "src/app/new.test.ts",
                     "src/app/new.spec.js", "tools/tests/runner.test.mjs",
                     "public/requests/IdentityBoundaryTest.ps1"):
            with self.subTest(path=path):
                self.assertTrue(ci.is_test(path))
                result = self.choose(path)
                self.assertEqual(set(ci.GROUPS), set(result["selected"]))
                self.assertTrue(result["uncertain"])

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


class FastLaneContractTests(unittest.TestCase):
    """CP3: all Fast lanes obligatory; full legacy only for full Deep cases."""

    @classmethod
    def setUpClass(cls):
        import yaml
        cls.workflow = yaml.safe_load((ci.ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"))
        cls.jobs = cls.workflow["jobs"]

    def test_cp41_display_names_do_not_change_required_job_checks(self):
        self.assertEqual("CI • Repository Validation", self.workflow["name"])
        self.assertEqual(
            "${{ github.event_name == 'pull_request' && 'CI • Repository Validation' || 'CI • Full Repository Audit' }}",
            self.workflow["run-name"],
        )
        # Required check uses an independent, stable job name, never a
        # workflow-display label.
        self.assertEqual("CI / Merge Gate", self.jobs["merge-gate"]["name"])
        self.assertIn("always()", self.jobs["merge-gate"]["if"])

    def test_all_fast_lanes_are_unconditionally_present_and_read_only(self):
        names = ("fast-contracts", "fast-source", "fast-scheduler",
                 "fast-angular", "fast-python")
        for name in names:
            with self.subTest(job=name):
                self.assertIn(name, self.jobs)
                job = self.jobs[name]
                self.assertNotIn("needs", job)
                self.assertNotIn("if", job)
                self.assertNotIn("continue-on-error", job)
                self.assertEqual({"contents": "read"}, job["permissions"])
                self.assertLessEqual(job["timeout-minutes"], 15)

    def test_historical_legacy_build_remains_complete_manual_audit_only(self):
        job = self.jobs["build"]
        self.assertEqual("selector", job["needs"])
        self.assertIn("github.event_name == 'workflow_dispatch'", job["if"])
        self.assertIn("github.event.action == 'scheduler-ci-full-audit'", job["if"])
        self.assertNotIn("needs.selector.outputs.full", job["if"])
        self.assertNotIn("continue-on-error", job)
        all_commands = "\n".join(str(step.get("run", "")) for step in job["steps"])
        for required in (
            'test_nfl_source*.py', 'test_league_source*.py',
            "test_market_observations_full_restore",
            "test_workflow_publication_contracts",
            "test_consumer_read_classification",
            "test_player_scoring_reconciliation",
            "node --test tools/tests/run-workflow-scheduler*.test.cjs",
            "npx ng test --watch=false --browsers=ChromeHeadless",
            "./deploy_action.ps1",
        ):
            self.assertIn(required, all_commands)

    def test_deep_lanes_are_all_routed_by_verified_selector(self):
        for name, flag in (
            ("deep-nfl", "nfl"), ("deep-league", "league"),
            ("deep-market", "market"), ("deep-consumer", "consumer"),
        ):
            with self.subTest(job=name):
                job = self.jobs[name]
                self.assertEqual("selector", job["needs"])
                self.assertIn(f"needs.selector.outputs.{flag} == 'true'", job["if"])
                self.assertNotIn("continue-on-error", job)
                self.assertEqual({"contents": "read"}, job["permissions"])
                self.assertIn("tools/ci_suite_runner.py", " ".join(
                    str(s.get("run", "")) for s in job["steps"]))

    def test_merge_gate_always_present_and_checks_all_results(self):
        gate = self.jobs["merge-gate"]
        self.assertEqual("CI / Merge Gate", gate["name"])
        self.assertIn("always()", gate["if"])
        self.assertNotIn("continue-on-error", gate)
        self.assertEqual({"contents": "read"}, gate["permissions"])
        self.assertEqual(
            {"selector", "build", "fast-contracts", "fast-source",
             "fast-scheduler", "fast-angular", "fast-python",
             "deep-nfl", "deep-league", "deep-market", "deep-consumer"},
            set(gate["needs"]))
        self.assertIn("toJSON(needs)", str(gate["steps"]))
        self.assertIn("github.event_name", str(gate["steps"]))
        self.assertIn("github.event.action", str(gate["steps"]))
        self.assertIn("tools/ci_merge_gate.py", str(gate["steps"]))

    def test_fast_lanes_never_execute_full_historical_restore(self):
        for name in ("fast-contracts", "fast-source", "fast-scheduler",
                     "fast-angular", "fast-python"):
            commands = "\n".join(str(x.get("run", "")) for x in self.jobs[name]["steps"])
            with self.subTest(job=name):
                self.assertNotIn("test_nfl_source_historical_identity_replay", commands)
                self.assertNotIn("test_market_observations_full_restore", commands)
                self.assertNotIn("test_team_week_performance_integration", commands)

    def test_fast_lanes_keep_original_safety_and_angular_entrypoints(self):
        legacy = self.jobs["build"]
        original = "\n".join(str(s.get("run", "")) for s in legacy["steps"])
        for name in ("fast-contracts", "fast-source", "fast-scheduler", "fast-angular"):
            for step in self.jobs[name]["steps"]:
                for line in str(step.get("run", "")).splitlines():
                    line = line.strip()
                    if line.startswith(("./public/requests/", "node --test",
                        "npx ng test", "./deploy_action.ps1",
                        "python tools/players_league_scoring_shadow.py gate")):
                        self.assertIn(line, original)


class Cp3SelectionAndGateTests(unittest.TestCase):
    def test_routing_new_scripts_enforces_all_deep(self):
        for path in ("tools/ci_suite_runner.py", "tools/ci_merge_gate.py",
                     ".github/workflows/build.yml"):
            with self.subTest(path=path):
                chosen = ci.select([{"filename": path, "status": "modified"}], {"tests": []})
                self.assertEqual(set(ci.GROUPS), set(chosen["selected"]))

    def test_verified_timeout_only_is_strict_structural_yaml(self):
        base = """
name: Source Sync
on: [pull_request]
permissions: {contents: read}
jobs:
  audit:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - run: python tools/validator.py
"""
        valid = base.replace("timeout-minutes: 10", "timeout-minutes: 20")
        self.assertTrue(ci.timeout_only_yaml(base, valid))
        self.assertFalse(ci.timeout_only_yaml(base, valid.replace(
            "python tools/validator.py", "python tools/skip_validator.py")))
        self.assertFalse(ci.timeout_only_yaml(base, valid.replace(
            "contents: read", "contents: write")))
        self.assertFalse(ci.timeout_only_yaml(base, valid.replace(
            "timeout-minutes: 20", "timeout-minutes: 500")))
        self.assertFalse(ci.timeout_only_yaml(base, valid.replace(
            "pull_request", "push")))
        self.assertFalse(ci.timeout_only_yaml(base, base))
        self.assertFalse(ci.timeout_only_yaml(base, base.replace(
            "timeout-minutes: 10", "")))

    def test_timeout_only_event_routing_does_not_hide_other_changes(self):
        from unittest.mock import patch
        path = ".github/workflows/sync-nfl-source-data.yml"
        original = ("jobs:\n  validate:\n    runs-on: ubuntu-latest\n"
                    "    timeout-minutes: 20\n    steps:\n      - run: echo safe\n")
        bumped = original.replace("timeout-minutes: 20", "timeout-minutes: 30")
        event = {
            "repository": {"full_name": "Lolindhir/fantasy-app"},
            "pull_request": {
                "number": 7,
                "base": {"sha": "a" * 40},
                "head": {"sha": "b" * 40},
                "changed_files": 1,
            },
        }
        changed = [{"filename": path, "status": "modified"}]
        with patch.object(ci, "pr_changes", return_value=changed), \
             patch.object(ci, "_repo_file_at", side_effect=[original, bumped]), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "test"}):
            result = ci.select_from_event(event, {"tests": []})
        self.assertEqual([], result["selected"])
        self.assertFalse(result["uncertain"])

        with patch.object(ci, "pr_changes", return_value=changed), \
             patch.object(ci, "_repo_file_at", side_effect=[
                 original, bumped.replace("echo safe", "echo unsafe")]), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "test"}):
            result = ci.select_from_event(event, {"tests": []})
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))

        with patch.object(ci, "pr_changes", return_value=changed), \
             patch.object(ci, "_repo_file_at", side_effect=OSError("API down")), \
             patch.dict("os.environ", {"GITHUB_TOKEN": "test"}):
            result = ci.select_from_event(event, {"tests": []})
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))

        both = changed + [{"filename": "tools/external_source/adapter.py",
                           "status": "modified"}]
        with patch.object(ci, "pr_changes", return_value=both):
            result = ci.select_from_event(event, {"tests": []})
        self.assertIn("market-restore", result["selected"])
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))


    def test_measured_slow_repository_integrations_must_remain_deep(self):
        # Run #39149258131: the ten tests below collectively cost > 6 min
        # within the 8m41s sequential Fast Python job. Classify by semantic
        # source dependencies, never silently remove them from CI coverage.
        expected = {
          "test_market_observations_preview.py": [
                    "market-restore"
          ],
          "test_nfl_source_historical_identity_coverage.py": [
                    "nfl-identity-replay"
          ],
          "test_nfl_source_projection_intervals.py": [
                    "nfl-identity-replay"
          ],
          "test_nfl_source_historical_weekly_roster_identity.py": [
                    "nfl-identity-replay",
                    "league-pwf-twp"
          ],
          "test_nfl_source_app_espn_identity_bridge_repository.py": [
                    "nfl-identity-replay",
                    "consumer-restore"
          ],
          "test_nfl_source_current_adjudication_builder.py": [
                    "nfl-identity-replay"
          ],
          "test_nfl_source_placeholder_gsis_upgrade.py": [
                    "nfl-identity-replay"
          ],
          "test_nfl_source_projection_team_v4_2025.py": [
                    "nfl-identity-replay"
          ],
          "test_player_valuation.py": [
                    "league-pwf-twp",
                    "consumer-restore"
          ],
          "test_nfl_source_projection_v4.py": [
                    "nfl-identity-replay"
          ]
}
        registered = {entry["path"].rsplit("/", 1)[-1]: entry
                      for entry in ci.read_inventory()["tests"]}
        from tools import ci_suite_runner
        fast_paths = set(ci_suite_runner.modules_for_lane(ci.read_inventory(), "fast"))
        deep_paths = set()
        for group in ci.GROUPS:
            deep_paths.update(ci_suite_runner.modules_for_lane(ci.read_inventory(), group))
        for name, groups in expected.items():
            with self.subTest(test=name):
                row = registered[name]
                self.assertEqual("deep", row["tier"])
                self.assertEqual(set(groups), set(row["deepGroups"]))
                self.assertNotIn(row["path"], fast_paths)
                self.assertIn(row["path"], deep_paths)

    def test_full_registry_python_coverage_is_partitioned(self):
        from tools import ci_suite_runner as runner
        inv = ci.read_inventory()
        fast = set(runner.modules_for_lane(inv, "fast"))
        deep = set()
        for group in ci.GROUPS:
            deep.update(runner.modules_for_lane(inv, group))
        tracked = {row["path"] for row in inv["tests"]
                   if row["path"].startswith("tools/tests/test_")
                   and row["path"].endswith(".py")
                   and row["currentPrCoverage"] in runner.COVERED}
        self.assertEqual(tracked, fast | deep)
        self.assertFalse(fast & deep)
        self.assertIn("tools/tests/test_nfl_source_historical_identity_replay.py", deep)
        self.assertNotIn("tools/tests/test_nfl_source_historical_identity_replay.py", fast)
        self.assertIn("tools/tests/test_market_observations_full_restore.py", deep)

    @staticmethod
    def good_needs(enabled=()):
        from tools import ci_merge_gate as gate
        selected = set(enabled)
        assert set(enabled) <= set(gate.DEEP)
        full = set(gate.DEEP) == selected
        flags = {name: "true" if name in selected else "false" for name in gate.DEEP}
        flags["full"] = "true" if full else "false"
        needs = {"selector": {"result": "success", "outputs": flags}}
        for name in gate.FAST:
            needs[name] = {"result": "success"}
        for flag, job in gate.DEEP.items():
            needs[job] = {"result": "success" if flag in selected else "skipped"}
        needs["build"] = {"result": "skipped"}
        return needs

    def test_merge_gate_accepts_verified_subset_full_and_none(self):
        from tools import ci_merge_gate as gate
        for selection in ((), ("market",), ("league", "consumer"),
                          ("nfl", "league", "market", "consumer")):
            with self.subTest(selection=selection):
                self.assertEqual([], gate.verify(self.good_needs(selection)))

    def test_manual_full_audit_requires_all_deep_and_successful_legacy(self):
        from tools import ci_merge_gate as gate
        all_four = tuple(gate.DEEP)
        manual = self.good_needs(all_four)
        manual["build"]["result"] = "success"
        self.assertEqual([], gate.verify(manual, "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs(all_four), "workflow_dispatch"))
        for result in ("skipped", "failure", "cancelled", "neutral", None):
            manual = self.good_needs(all_four)
            manual["build"]["result"] = result
            self.assertTrue(gate.verify(manual, "workflow_dispatch"))
        partial = self.good_needs(("nfl",))
        partial["build"]["result"] = "success"
        self.assertTrue(gate.verify(partial, "workflow_dispatch"))

    def test_weekly_scheduler_dispatch_requires_complete_success(self):
        from tools import ci_merge_gate as gate
        selected = self.good_needs(tuple(gate.DEEP))
        selected["build"]["result"] = "success"
        self.assertEqual([], gate.verify(selected, "repository_dispatch", "scheduler-ci-full-audit"))
        for outcome in ("skipped", "failure", "cancelled", "neutral", None):
            changed = self.good_needs(tuple(gate.DEEP))
            changed["build"]["result"] = outcome
            self.assertTrue(gate.verify(changed, "repository_dispatch", "scheduler-ci-full-audit"))
        partial = self.good_needs(("nfl",))
        partial["build"]["result"] = "success"
        self.assertTrue(gate.verify(partial, "repository_dispatch", "scheduler-ci-full-audit"))
        for action in (None, "", "external-scheduler-tick", "scheduler-workflow-health"):
            self.assertTrue(gate.verify(selected, "repository_dispatch", action))
        self.assertTrue(gate.verify(selected, "push"))

    def test_weekly_audit_event_preserves_read_only_legacy_commands(self):
        import yaml
        workflow = yaml.safe_load((ci.ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"))
        self.assertEqual(["scheduler-ci-full-audit"],
                         workflow[True]["repository_dispatch"]["types"])
        self.assertEqual({"contents": "read", "pull-requests": "read"}, workflow["permissions"])
        legacy = workflow["jobs"]["build"]
        self.assertNotIn("continue-on-error", legacy)
        self.assertIn("scheduler-ci-full-audit", legacy["if"])
        self.assertFalse(any(str(x.get("run", "")).strip().startswith(("git push", "git commit"))
                             for x in legacy["steps"]))

    def test_pr_requires_legacy_skipped_even_with_all_deep(self):
        from tools import ci_merge_gate as gate
        all_four = tuple(gate.DEEP)
        needs = self.good_needs(all_four)
        self.assertEqual([], gate.verify(needs, "pull_request"))
        for outcome in ("success", "failure", "cancelled", "neutral", None):
            needs = self.good_needs(all_four)
            needs["build"]["result"] = outcome
            self.assertTrue(gate.verify(needs, "pull_request"))
        for invalid in ("push", "", None):
            self.assertTrue(gate.verify(self.good_needs(()), invalid))

    def test_unmodified_legacy_obligations_have_fast_and_deep_equivalents(self):
        import fnmatch
        import re
        from tools import ci_suite_runner as runner

        import yaml
        workflow = yaml.safe_load(
            (ci.ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
        )["jobs"]
        legacy = "\n".join(str(step.get("run", "")) for step in workflow["build"]["steps"])
        fast_job_names = ("fast-contracts", "fast-source", "fast-scheduler", "fast-angular")
        fast = "\n".join(str(step.get("run", ""))
                           for name in fast_job_names for step in workflow[name]["steps"])
        manifest = ci.read_inventory()
        # Every historical *non-test* safety contract must be on an always
        # present Fast lane, not hidden in manual-only build.
        for command in manifest["mandatoryCommands"]:
            if command["workflow"] == ".github/workflows/build.yml":
                with self.subTest(command=command["snippet"]):
                    self.assertIn(command["snippet"], fast)

        # Preserve every old PowerShell / Node / Angular command entrypoint.
        for line in legacy.splitlines():
            command = line.strip()
            if command.startswith(("./public/requests/", "node --test",
                                   "npx ng test", "./deploy_action.ps1",
                                   "python tools/players_league_scoring_shadow.py gate")):
                with self.subTest(legacy_command=command):
                    self.assertIn(command, fast)

        # Cover all previous direct Python tests, including all glob expansions,
        # through the union of registered Fast and selected Deep lanes.
        all_modules = set(runner.modules_for_lane(manifest, "fast"))
        for group in ci.GROUPS:
            all_modules.update(runner.modules_for_lane(manifest, group))
        all_modules.add("tools/tests/test_ci_test_impact.py")  # fast-contracts
        indexed = {row["path"] for row in manifest["tests"]
                   if row["path"].startswith("tools/tests/test_")
                   and row["path"].endswith(".py")}
        for name in set(re.findall(r"tools[./]tests[./](test_[a-zA-Z0-9_]+)", legacy)):
            path = f"tools/tests/{name}.py"
            self.assertIn(path, all_modules)
        for pattern in re.findall(r'-p "([^"]+\.py)"', legacy):
            for path in indexed:
                if fnmatch.fnmatch(path.rsplit("/", 1)[-1], pattern):
                    self.assertIn(path, all_modules)
        # An absent Fast runner or a missing Deep runner must be fatal.
        self.assertIn("tools/ci_suite_runner.py fast", str(workflow["fast-python"]))
        for name in ("deep-nfl", "deep-league", "deep-market", "deep-consumer"):
            self.assertIn("tools/ci_suite_runner.py", str(workflow[name]))

    def test_merge_gate_rejects_skipped_failed_cancelled_or_missing_selected(self):
        from tools import ci_merge_gate as gate
        for value in ("skipped", "failure", "cancelled", "neutral", None):
            with self.subTest(value=value):
                needs = self.good_needs(("market",))
                needs["deep-market"]["result"] = value
                self.assertTrue(gate.verify(needs))

    def test_merge_gate_rejects_fast_failure_selector_failure_or_rogue_skip(self):
        from tools import ci_merge_gate as gate
        for key in ("fast-angular", "fast-python", "fast-source", "selector"):
            needs = self.good_needs(())
            needs[key]["result"] = "failure"
            self.assertTrue(gate.verify(needs))
        needs = self.good_needs(())
        needs["deep-nfl"]["result"] = "success"  # unselected must be skipped
        self.assertTrue(gate.verify(needs))
        needs = self.good_needs(())
        needs["selector"]["outputs"]["full"] = "true"  # incoherent decision
        self.assertTrue(gate.verify(needs))
        needs = self.good_needs(())
        del needs["fast-contracts"]  # missing required job never passes
        self.assertTrue(gate.verify(needs))
        needs = self.good_needs(())
        del needs["selector"]["outputs"]["consumer"]
        self.assertTrue(gate.verify(needs))


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
