"""Regression contracts for the CI inventory, Core/Fast selection, Deep isolation and merge gate (Issues #1095, #1122)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock
import subprocess
import tempfile
import unittest

from tools import ci_test_impact as ci


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {"tests": [
            {"path": "tools/tests/test_nfl_source_historical_identity_replay.py",
             "tier": "deep", "deepGroups": ["nfl-identity-replay"],
             "fastGroups": ["nfl-identity-replay"], "currentPrCoverage": "build"},
            {"path": "tools/tests/test_market_observations_full_restore.py",
             "tier": "deep", "deepGroups": ["market-restore"],
             "fastGroups": [], "currentPrCoverage": "build"},
            {"path": "tools/tests/test_ci_test_impact.py",
             "tier": "fast", "deepGroups": [], "fastGroups": [], "currentPrCoverage": "shadow"},
        ]}

    def choose(self, *paths):
        return ci.select([{"filename": p, "status": "modified"} for p in paths], self.inventory)

    def test_odds_observation_code_selects_market_and_consumer_fast(self):
        for path in ("tools/odds_observation.py", "tools/odds_observation_buffer.py",
                     "tools/odds_scoped_source_preflight.py", "tools/odds_state_publish.py"):
            with self.subTest(path=path):
                result = self.choose(path)
                self.assertEqual({"market-restore", "consumer-restore"},
                                 set(result["selected"]))
                self.assertFalse(result["uncertain"])

    def test_docs_and_angular_are_fast_only(self):
        self.assertEqual([], self.choose("docs/contributing.md")["selected"])
        self.assertEqual([], self.choose("src/app/app.component.ts")["selected"])

    def test_historical_replay_test_edits_select_its_fast_family_only(self):
        result = self.choose("tools/tests/test_nfl_source_historical_identity_replay.py")
        self.assertEqual(["nfl-identity-replay"], result["selected"])
        self.assertEqual([], result["blocks"])
        self.assertFalse(result["uncertain"])

    def test_selection_never_contains_deep_decisions(self):
        # Deep is not part of pull-request selection at all: only the event
        # layer reports ``deep`` and it is empty for pull requests.
        event = {"repository": {"full_name": "Lolindhir/fantasy-app"},
                 "pull_request": {"number": 1, "base": {"sha": "a" * 40},
                                  "head": {"sha": "b" * 40}, "changed_files": 1}}
        changed = [{"filename": "tools/nfl_source_data_lib/phase1.py", "status": "modified"}]
        with mock.patch.object(ci, "pr_changes", return_value=changed):
            result = ci.select_from_event(event, self.inventory)
        self.assertEqual("pr", result["mode"])
        self.assertEqual([], result["deep"])
        self.assertEqual(set(ci.GROUPS), set(result["selected"]))

    def test_angular_only_change_selects_only_the_angular_block(self):
        result = self.choose("src/app/features/overview/overview.ts")
        self.assertEqual([], result["selected"])
        self.assertEqual(["angular"], result["blocks"])
        self.assertFalse(result["uncertain"])

    def test_scheduler_and_powershell_changes_select_their_own_block(self):
        self.assertEqual(["scheduler"], self.choose("tools/run-workflow-scheduler-runtime.cjs")["blocks"])
        self.assertEqual(["scheduler"], self.choose(".github/workflow-schedules.json")["blocks"])

    def test_league_history_change_selects_derived_families_not_identity_or_market(self):
        selected = set(self.choose("tools/league_history_app_publish.py")["selected"])
        self.assertEqual({"league-pwf-twp", "consumer-restore"}, selected)

    def test_league_standings_sources_select_derived_families(self):
        selected = set(self.choose("tools/league_standings_sources.py")["selected"])
        self.assertEqual({"league-pwf-twp", "consumer-restore"}, selected)

    def test_decision_windows_cli_selects_derived_families(self):
        selected = set(self.choose("tools/decision_windows.py")["selected"])
        self.assertEqual({"league-pwf-twp", "consumer-restore"}, selected)

    def test_matchup_context_cli_selects_derived_families(self):
        selected = set(self.choose("tools/matchup_context.py")["selected"])
        self.assertEqual({"league-pwf-twp", "consumer-restore"}, selected)

    def test_league_live_derived_refresh_selects_derived_families(self):
        selected = set(self.choose("tools/league_live_derived_refresh.py")["selected"])
        self.assertEqual({"league-pwf-twp", "consumer-restore"}, selected)

    def test_documentation_and_canonical_contracts_select_no_block(self):
        for path in ("docs/contributing.md", ".ai-context/manual/decisions.yaml"):
            with self.subTest(path=path):
                result = self.choose(path)
                self.assertEqual([], result["blocks"])

    def test_mixed_paths_union_families_and_blocks(self):
        result = self.choose("src/app/app.ts", "tools/external_source/fantasypros.py")
        self.assertEqual({"market-restore", "consumer-restore"}, set(result["selected"]))
        self.assertIn("angular", result["blocks"])

    def test_ci_and_policy_changes_select_every_fast_family_and_block(self):
        for path in (".github/workflows/build.yml", "tools/ci_suite_runner.py", "tools/ci_tier.py"):
            with self.subTest(path=path):
                result = self.choose(path)
                self.assertEqual(set(ci.GROUPS), set(result["selected"]))
                self.assertEqual(set(ci.BLOCKS), set(result["blocks"]))
                self.assertTrue(result["uncertain"])

    def test_route_outputs_never_enable_deep_for_a_pull_request(self):
        result = dict(ci.select([{"filename": "tools/ci_test_impact.py", "status": "modified"}],
                                self.inventory), mode="pr", deep=[])
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            with mock.patch.dict("os.environ", {"GITHUB_OUTPUT": str(out)}):
                ci.emit_route_outputs(result)
            lines = dict(x.split("=", 1) for x in out.read_text().splitlines())
        self.assertEqual("pr", lines["mode"])
        for key in ("deep_nfl", "deep_league", "deep_market", "deep_consumer"):
            self.assertEqual("false", lines[key])
        for key in ("nfl", "league", "market", "consumer", "angular", "scheduler", "powershell"):
            self.assertEqual("true", lines[key])

    def test_dispatch_scope_selects_full_audit_or_exactly_one_deep_group(self):
        full = ci.select_from_event({"inputs": {"scope": "full"}}, self.inventory)
        self.assertEqual("full", full["mode"])
        self.assertEqual(set(ci.GROUPS), set(full["deep"]))
        self.assertEqual(set(ci.BLOCKS), set(full["blocks"]))
        one = ci.select_from_event({"inputs": {"scope": "market-restore"}}, self.inventory)
        self.assertEqual(("deep", ["market-restore"], []), (one["mode"], one["deep"], one["blocks"]))
        self.assertEqual("full", ci.select_from_event({}, self.inventory)["mode"])
        with self.assertRaises(ValueError):
            ci.select_from_event({"inputs": {"scope": "everything"}}, self.inventory)

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

    def test_week_finality_cli_routes_like_the_scoring_implementation(self):
        groups = self.choose("tools/week_finality.py")["selected"]
        self.assertEqual({"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}, set(groups))

    def test_historical_cross_product_orchestrator_uses_strict_fast_closure(self):
        result = self.choose("tools/historical_derived_orchestrate.py")
        self.assertEqual(
            {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"},
            set(result["selected"]),
        )
        self.assertFalse(result["uncertain"])

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

    def test_architecture_reviewer_checks_ci_impact_for_pr_and_periodic_audit(self):
        """Both independent review scopes must assess CI inventory, routing and actual execution."""
        import yaml

        contract = yaml.safe_load(
            (ci.ROOT / ".ai-context/manual/architecture-review.yaml").read_text(encoding="utf-8")
        )
        independent = contract["modes"]["independentReview"]
        self.assertEqual("read-only", independent["defaultMode"])
        contexts = independent["reviewContexts"]
        self.assertEqual({"changeFocused", "periodicRepositoryAudit"}, set(contexts))
        for name in contexts:
            with self.subTest(context=name):
                evidence = "\n".join(contexts[name]["ciImpactEvidence"])
                self.assertIn("Deep", evidence)
                self.assertIn("test", evidence.lower())
                self.assertIn("Issue", evidence)
        dimensions = contract["dimensions"]["ciImpactAndTestCoverage"]
        checks = "\n".join(dimensions["checks"])
        self.assertIn("really invoke", checks)
        self.assertIn("uncovered", checks.lower())
        self.assertIn("four Deep", checks)
        self.assertIn("both change-focused reviews and periodic", dimensions["reviewRule"])
        self.assertIn("ci-impact-and-coverage", contract["reviewOutput"]["requiredSections"])

    def test_core_is_unconditional_and_every_fast_block_is_selector_gated(self):
        core = self.jobs["fast-contracts"]
        self.assertNotIn("needs", core)
        self.assertNotIn("if", core)
        self.assertEqual({"contents": "read"}, core["permissions"])
        self.assertLessEqual(core["timeout-minutes"], 15)
        blocks = {"fast-nfl": "nfl", "fast-league": "league", "fast-market": "market",
                  "fast-consumer": "consumer", "fast-powershell": "powershell",
                  "fast-scheduler": "scheduler", "fast-angular": "angular"}
        for name, flag in blocks.items():
            with self.subTest(job=name):
                job = self.jobs[name]
                self.assertEqual("selector", job["needs"])
                self.assertIn(f"needs.selector.outputs.{flag} == 'true'", job["if"])
                self.assertNotIn("continue-on-error", job)
                self.assertEqual({"contents": "read"}, job["permissions"])
                self.assertLessEqual(job["timeout-minutes"], 15)

    def test_fast_families_run_the_fast_lane_and_core_runs_the_core_lane(self):
        runs = lambda name: " ".join(str(x.get("run", "")) for x in self.jobs[name]["steps"])
        self.assertIn("tools/ci_suite_runner.py core", runs("fast-contracts"))
        for name, group in (("fast-nfl", "nfl-identity-replay"), ("fast-league", "league-pwf-twp"),
                            ("fast-market", "market-restore"), ("fast-consumer", "consumer-restore")):
            with self.subTest(job=name):
                self.assertIn(f"tools/ci_suite_runner.py fast {group}", runs(name))

    def test_historical_legacy_build_remains_complete_audit_only(self):
        job = self.jobs["build"]
        self.assertEqual("selector", job["needs"])
        self.assertIn("needs.selector.outputs.mode == 'full'", job["if"])
        self.assertIn("github.event_name == 'workflow_dispatch'", job["if"])
        self.assertIn("github.event.action == 'scheduler-ci-full-audit'", job["if"])
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

    def test_restore_gate_is_read_only_and_audit_only(self):
        job = self.jobs["restore-gate"]
        self.assertEqual("selector", job["needs"])
        self.assertEqual(self.jobs["build"]["if"], job["if"])
        self.assertNotIn("continue-on-error", job)
        self.assertEqual({"contents": "read"}, job["permissions"])
        commands = "\n".join(str(s.get("run", "")) for s in job["steps"])
        self.assertIn("tools/derived_clean_root_audit.py", commands)
        self.assertNotIn("git push", commands)
        self.assertNotIn("git commit", commands)

    def test_deep_lanes_are_routed_only_by_deep_selector_outputs(self):
        for name, flag, group in (
            ("deep-nfl", "deep_nfl", "nfl-identity-replay"),
            ("deep-league", "deep_league", "league-pwf-twp"),
            ("deep-market", "deep_market", "market-restore"),
            ("deep-consumer", "deep_consumer", "consumer-restore"),
        ):
            with self.subTest(job=name):
                job = self.jobs[name]
                self.assertEqual("selector", job["needs"])
                self.assertEqual(f"${{{{ needs.selector.outputs.{flag} == 'true' }}}}", job["if"])
                self.assertNotIn("continue-on-error", job)
                self.assertEqual({"contents": "read"}, job["permissions"])
                self.assertIn(f"tools/ci_suite_runner.py deep {group}", " ".join(
                    str(s.get("run", "")) for s in job["steps"]))

    def test_dispatch_scope_options_cover_full_and_every_deep_group(self):
        options = self.workflow[True]["workflow_dispatch"]["inputs"]["scope"]["options"]
        self.assertEqual(["full", *ci.GROUPS], options)

    def test_merge_gate_always_present_and_checks_all_results(self):
        gate = self.jobs["merge-gate"]
        self.assertEqual("CI / Merge Gate", gate["name"])
        self.assertIn("always()", gate["if"])
        self.assertNotIn("continue-on-error", gate)
        self.assertEqual({"contents": "read"}, gate["permissions"])
        self.assertEqual(
            {"selector", "build", "restore-gate", "fast-contracts", "fast-nfl", "fast-league", "fast-market",
             "fast-consumer", "fast-powershell", "fast-scheduler", "fast-angular",
             "deep-nfl", "deep-league", "deep-market", "deep-consumer"},
            set(gate["needs"]))
        self.assertIn("toJSON(needs)", str(gate["steps"]))
        self.assertIn("github.event_name", str(gate["steps"]))
        self.assertIn("github.event.action", str(gate["steps"]))
        self.assertIn("tools/ci_merge_gate.py", str(gate["steps"]))

    def test_fast_and_core_jobs_never_execute_deep_restores_directly(self):
        for name in ("fast-contracts", "fast-nfl", "fast-league", "fast-market",
                     "fast-consumer", "fast-powershell", "fast-scheduler", "fast-angular"):
            commands = "\n".join(str(x.get("run", "")) for x in self.jobs[name]["steps"])
            with self.subTest(job=name):
                self.assertNotIn("test_nfl_source_historical_identity_replay", commands)
                self.assertNotIn("test_market_observations_full_restore", commands)
                self.assertNotIn("test_team_week_performance_integration", commands)
                self.assertNotIn("ci_suite_runner.py deep", commands)

    def test_fast_blocks_keep_original_safety_and_angular_entrypoints(self):
        original = "\n".join(str(s.get("run", "")) for s in self.jobs["build"]["steps"])
        for name in ("fast-league", "fast-powershell", "fast-scheduler", "fast-angular"):
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


    def test_measured_slow_repository_integrations_remain_deep_with_a_fast_counterpart(self):
        # Slow historical replays and restores stay in Deep (weekly audit or
        # manual dispatch) and each has a cheap Fast counterpart family.
        expected = {
            "test_market_observations_full_restore.py": ("market-restore", None),
            "test_market_observations_preview.py": ("market-restore", "market-restore"),
            "test_nfl_source_historical_identity_replay.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_historical_identity_coverage.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_projection_intervals.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_historical_weekly_roster_identity.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_app_espn_identity_bridge_repository.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_current_adjudication_builder.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_nfl_source_placeholder_gsis_upgrade.py": ("nfl-identity-replay", "nfl-identity-replay"),
            "test_league_source_historical_pwf_batch.py": ("league-pwf-twp", "league-pwf-twp"),
            "test_player_valuation.py": ("league-pwf-twp", "consumer-restore"),
        }
        from tools import ci_suite_runner
        inventory = ci.read_inventory()
        registered = {entry["path"].rsplit("/", 1)[-1]: entry for entry in inventory["tests"]}
        for name, (deep_group, fast_group) in expected.items():
            with self.subTest(test=name):
                row = registered[name]
                self.assertEqual("deep", row["tier"])
                self.assertIn(deep_group, row["deepGroups"])
                self.assertIn(row["path"], ci_suite_runner.modules_for_lane(inventory, "deep", deep_group))
                core = ci_suite_runner.modules_for_lane(inventory, "core")
                self.assertNotIn(row["path"], core)
                if fast_group:
                    self.assertIn(fast_group, row["fastGroups"])
                    self.assertIn(row["path"], ci_suite_runner.modules_for_lane(inventory, "fast", fast_group))

    def test_every_deep_category_has_fast_counterparts_and_pr_never_runs_deep(self):
        from tools import ci_suite_runner as runner
        inventory = ci.read_inventory()
        for group in ci.GROUPS:
            with self.subTest(group=group):
                fast = runner.modules_for_lane(inventory, "fast", group)
                deep = runner.modules_for_lane(inventory, "deep", group)
                self.assertTrue(fast)
                self.assertTrue(deep)
                deep_only_modules = [row for row in inventory["tests"]
                                     if row["tier"] == "deep" and group in row["deepGroups"]]
                self.assertTrue(deep_only_modules)

    def test_deep_only_marker_skips_only_in_the_fast_tier(self):
        import os
        from tools import ci_tier
        with mock.patch.dict(os.environ, {ci_tier.FAST_ENV: "fast"}):
            self.assertTrue(ci_tier.fast_tier())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ci_tier.FAST_ENV, None)
            self.assertFalse(ci_tier.fast_tier())

    def test_full_registry_python_coverage_is_partitioned(self):
        from tools import ci_suite_runner as runner
        inv = ci.read_inventory()
        core = set(runner.modules_for_lane(inv, "core"))
        fast, deep = set(), set()
        for group in ci.GROUPS:
            fast.update(runner.modules_for_lane(inv, "fast", group))
            deep.update(runner.modules_for_lane(inv, "deep", group))
        tracked = {row["path"] for row in inv["tests"]
                   if row["path"].startswith("tools/tests/test_")
                   and row["path"].endswith(".py")
                   and row["currentPrCoverage"] in runner.COVERED}
        # Nothing registered as covered may be dropped by any lane.
        self.assertEqual(tracked, core | fast | deep)
        self.assertFalse(core & fast)
        self.assertFalse(core & deep)
        self.assertIn("tools/tests/test_nfl_source_historical_identity_replay.py", deep)
        self.assertNotIn("tools/tests/test_nfl_source_historical_identity_replay.py", core)
        self.assertIn("tools/tests/test_market_observations_full_restore.py", deep)
        self.assertNotIn("tools/tests/test_market_observations_full_restore.py", fast)

    def test_runner_rejects_unknown_or_inconsistent_lanes(self):
        from tools import ci_suite_runner as runner
        inventory = ci.read_inventory()
        for lane, group in (("core", "market-restore"), ("fast", None), ("deep", None),
                            ("fast", "imaginary"), ("other", None)):
            with self.subTest(lane=lane, group=group):
                with self.assertRaises(ValueError):
                    runner.modules_for_lane(inventory, lane, group)

    @staticmethod
    def good_needs(mode="pr", fast=(), deep=()):
        from tools import ci_merge_gate as gate
        fast_flags = set(fast)
        deep_flags = set(deep)
        assert fast_flags <= set(gate.FAST) and deep_flags <= set(gate.DEEP)
        outputs = {"mode": mode}
        outputs.update({name: "true" if name in fast_flags else "false" for name in gate.FAST})
        outputs.update({name: "true" if name in deep_flags else "false" for name in gate.DEEP})
        needs = {"selector": {"result": "success", "outputs": outputs}, gate.CORE: {"result": "success"}}
        for name, job in gate.FAST.items():
            needs[job] = {"result": "success" if name in fast_flags else "skipped"}
        for name, job in gate.DEEP.items():
            needs[job] = {"result": "success" if name in deep_flags else "skipped"}
        for audit_job in gate.AUDIT_JOBS:
            needs[audit_job] = {"result": "success" if mode == "full" else "skipped"}
        return needs

    def test_merge_gate_accepts_core_plus_exactly_the_selected_fast_blocks(self):
        from tools import ci_merge_gate as gate
        for fast in ((), ("market",), ("league", "consumer"), tuple(gate.FAST)):
            with self.subTest(fast=fast):
                self.assertEqual([], gate.verify(self.good_needs("pr", fast), "pull_request"))

    def test_merge_gate_rejects_pull_request_deep_and_legacy_build(self):
        from tools import ci_merge_gate as gate
        needs = self.good_needs("pr", ("nfl",), ("deep_nfl",))
        self.assertTrue(gate.verify(needs, "pull_request"))
        needs = self.good_needs("pr")
        needs["deep-nfl"]["result"] = "success"
        self.assertTrue(gate.verify(needs, "pull_request"))
        for job in gate.AUDIT_JOBS:
            for outcome in ("success", "failure", "cancelled", "neutral", None):
                needs = self.good_needs("pr")
                needs[job]["result"] = outcome
                self.assertTrue(gate.verify(needs, "pull_request"))
        for invalid in ("push", "", None):
            self.assertTrue(gate.verify(self.good_needs("pr"), invalid))

    def test_merge_gate_rejects_wrong_skips_and_failed_blocks(self):
        from tools import ci_merge_gate as gate
        for value in ("skipped", "failure", "cancelled", "neutral", None):
            with self.subTest(value=value):
                needs = self.good_needs("pr", ("market",))
                needs["fast-market"]["result"] = value
                self.assertTrue(gate.verify(needs, "pull_request"))
        needs = self.good_needs("pr", ("market",))
        needs["fast-nfl"]["result"] = "success"  # not selected: must be skipped
        self.assertTrue(gate.verify(needs, "pull_request"))
        for key in ("fast-contracts", "selector"):
            needs = self.good_needs("pr")
            needs[key]["result"] = "failure"
            self.assertTrue(gate.verify(needs, "pull_request"))
        needs = self.good_needs("pr")
        del needs["fast-contracts"]
        self.assertTrue(gate.verify(needs, "pull_request"))
        needs = self.good_needs("pr")
        del needs["selector"]["outputs"]["consumer"]
        self.assertTrue(gate.verify(needs, "pull_request"))
        needs = self.good_needs("pr")
        needs["selector"]["outputs"]["mode"] = "full"  # incoherent with a pull request
        self.assertTrue(gate.verify(needs, "pull_request"))

    def test_full_audit_requires_every_fast_block_every_deep_category_and_legacy_build(self):
        from tools import ci_merge_gate as gate
        every_fast, every_deep = tuple(gate.FAST), tuple(gate.DEEP)
        full = self.good_needs("full", every_fast, every_deep)
        self.assertEqual([], gate.verify(full, "workflow_dispatch"))
        self.assertEqual([], gate.verify(full, "repository_dispatch", "scheduler-ci-full-audit"))
        for job in gate.AUDIT_JOBS:
            for outcome in ("skipped", "failure", "cancelled", "neutral", None):
                changed = self.good_needs("full", every_fast, every_deep)
                changed[job]["result"] = outcome
                self.assertTrue(gate.verify(changed, "workflow_dispatch"))
                self.assertTrue(gate.verify(changed, "repository_dispatch", "scheduler-ci-full-audit"))
        missing = self.good_needs("full", every_fast, every_deep)
        del missing["restore-gate"]
        self.assertTrue(gate.verify(missing, "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("full", every_fast, ("deep_nfl",)), "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("full", ("nfl",), every_deep), "workflow_dispatch"))
        for action in (None, "", "external-scheduler-tick", "scheduler-workflow-health"):
            self.assertTrue(gate.verify(full, "repository_dispatch", action))
        self.assertTrue(gate.verify(full, "push"))

    def test_deep_scope_dispatch_runs_exactly_one_deep_category_without_fast_or_legacy(self):
        from tools import ci_merge_gate as gate
        self.assertEqual([], gate.verify(self.good_needs("deep", (), ("deep_market",)), "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("deep", (), ()), "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("deep", (), ("deep_market", "deep_nfl")), "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("deep", ("market",), ("deep_market",)), "workflow_dispatch"))
        self.assertTrue(gate.verify(self.good_needs("deep", (), ("deep_market",)), "pull_request"))
        scheduled = self.good_needs("deep", (), ("deep_market",))
        self.assertTrue(gate.verify(scheduled, "repository_dispatch", "scheduler-ci-full-audit"))

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

    def test_existing_uncovered_baseline_is_frozen_and_auditable(self):
        data = ci.read_inventory()
        report = ci.validate(ci.ROOT, data)
        self.assertEqual(27, report["legacyUncovered"])
        self.assertEqual(0, report["explicitlyExceptedUncovered"])
        self.assertEqual(27, report["currentlyNotInPr"])
        # Merely adding to the baseline in the manifest must not legitimize a gap.
        data["coveragePolicy"]["legacyUncoveredTests"].append("tools/tests/test_unreviewed.py")
        with self.assertRaisesRegex(ValueError, "Legacy uncovered-test baseline drift"):
            ci.validate(ci.ROOT, data)

    def test_new_uncovered_test_needs_explicit_issue_backed_exception(self):
        data = ci.read_inventory()
        new_path = "tools/tests/test_future_uncovered.py"
        data["tests"].append({
            "path": new_path, "tier": "fast", "deepGroups": [], "fastGroups": [],
            "currentPrCoverage": "not-in-current-pr-ci",
        })
        tracked = ci.discover(ci.ROOT) | {new_path}
        original_coverage = ci.baseline_coverage(ci.ROOT, tracked - {new_path}, data)

        def coverage(_root, _paths, _inventory=None):
            return {**original_coverage, new_path: "not-in-current-pr-ci"}

        with (mock.patch.object(ci, "discover", return_value=tracked),
              mock.patch.object(ci, "baseline_coverage", side_effect=coverage)):
            with self.assertRaisesRegex(ValueError, "Unreviewed PR-CI coverage gap"):
                ci.validate(ci.ROOT, data)
            data["coveragePolicy"]["exceptions"][new_path] = {
                "issue": "", "reason": "Too short"
            }
            with self.assertRaisesRegex(ValueError, "Invalid uncovered-test exception"):
                ci.validate(ci.ROOT, data)
            data["coveragePolicy"]["exceptions"][new_path] = {
                "issue": "#1113",
                "reason": "Requires integration environment unavailable on standard CI runners",
            }
            counts = ci.validate(ci.ROOT, data)
            self.assertEqual(1, counts["explicitlyExceptedUncovered"])
            self.assertEqual(28, counts["currentlyNotInPr"])
            # A waiver for an already-covered test is stale and must fail.
            data["coveragePolicy"]["exceptions"]["tools/tests/test_ci_test_impact.py"] = {
                "issue": "#1113",
                "reason": "Deliberately stale waiver for test already covered by the Fast job",
            }
            with self.assertRaisesRegex(ValueError, "Unreviewed PR-CI coverage gap"):
                ci.validate(ci.ROOT, data)

    def test_deep_group_and_routing_remain_explicit(self):
        data = ci.read_inventory()
        candidate = data["tests"][0].copy()
        candidate["tier"] = "deep"
        candidate["deepGroups"] = ["imaginary-group"]
        data["tests"][0] = candidate
        with self.assertRaisesRegex(ValueError, "Invalid deep groups"):
            ci.validate(ci.ROOT, data)
        for path, groups in (
            ("tools/external_source/new_provider.py", {"market-restore", "consumer-restore"}),
            ("tools/team_week_performance_new.py",
             {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}),
            ("tools/surprise_new_module.py", set(ci.GROUPS)),
        ):
            with self.subTest(path=path):
                selected = ci.select([{"filename": path, "status": "added"}], ci.read_inventory())
                self.assertEqual(groups, set(selected["selected"]))


if __name__ == "__main__":
    unittest.main()
