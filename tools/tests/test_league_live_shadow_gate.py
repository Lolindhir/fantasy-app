"""Fail-closed and no-skip regression cases for League Live shadow observation (#1263 G5)."""
from __future__ import annotations

import json

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tools import league_live_shadow_gate as shadow


class ShadowDecisionTests(unittest.TestCase):
    def evidence(self, stage: str = "league") -> tuple[dict, dict]:
        inputs = {path: path + "-fingerprint" for path in shadow.STAGE_INPUTS[stage]}
        current = {
            "schemaVersion": 1, "stage": stage, "scope": "all-leagues-seasons",
            "atUtc": "2026-11-03T19:30:00Z", "inputTrees": inputs,
            "missingOutputs": [], "sourceStatus": "success", "upstreamStatus": "success",
            "raceFree": True, "recoveryClean": True,
        }
        prior = {
            "schemaVersion": 1, "stage": stage, "scope": "all-leagues-seasons",
            "processedAtUtc": "2026-11-03T19:20:00Z", "validUntilUtc": "2026-11-03T19:40:00Z",
            "clockBoundaryProof": True, "completedSuccessfully": True,
            "outputsValidated": True, "raceFree": True, "recoveryClean": True,
            "inputTrees": dict(inputs),
        }
        return current, prior

    def test_positive_requires_every_proof_and_never_enforces_skip(self):
        for stage in shadow.STAGE_INPUTS:
            with self.subTest(stage=stage):
                current, prior = self.evidence(stage)
                result = shadow.decide(current, prior)
                self.assertEqual("would-skip", result["decision"])
                self.assertFalse(result["enforced"])
                self.assertEqual([], result["reasonCodes"])

    def test_missing_prior_never_skips(self):
        current, _ = self.evidence()
        result = shadow.decide(current, None)
        self.assertEqual("would-run", result["decision"])
        self.assertIn("missing-previous-successful-attestation", result["reasonCodes"])

    def test_nfl_finality_source_correction_and_derived_changes_invalidate(self):
        for stage in shadow.STAGE_INPUTS:
            for path in ("data-source", "data-derived", "data-meta"):
                with self.subTest(stage=stage, path=path):
                    current, prior = self.evidence(stage)
                    current["inputTrees"][path] = "changed"
                    self.assertIn("input-revision-changed-or-unknown",
                                  shadow.decide(current, prior)["reasonCodes"])

    def test_app_code_market_salary_and_model_change_invalidate(self):
        for path in ("public/data", "public/requests", "tools", ".github/workflows"):
            current, prior = self.evidence("league")
            current["inputTrees"][path] = "changed"
            self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_kickoff_waiver_and_week_boundaries_invalidate(self):
        for key, value in (
            ("validUntilUtc", "2026-11-03T19:30:00Z"),
            ("validUntilUtc", None),
            ("processedAtUtc", "2026-11-03T19:35:00Z"),
            ("clockBoundaryProof", False),
        ):
            with self.subTest(key=key, value=value):
                current, prior = self.evidence()
                prior[key] = value
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_races_fail_soft_recovery_errors_missing_outputs_and_unknowns_invalidate(self):
        for owner, key, value in (
            ("current", "sourceStatus", "failure"),
            ("current", "upstreamStatus", "unknown"),
            ("current", "raceFree", None),
            ("current", "recoveryClean", False),
            ("current", "missingOutputs", ["public/data/League.json"]),
            ("prior", "raceFree", False),
            ("prior", "recoveryClean", None),
            ("prior", "completedSuccessfully", False),
            ("prior", "outputsValidated", None),
            ("prior", "scope", "one-league-only"),
        ):
            with self.subTest(owner=owner, key=key):
                current, prior = self.evidence()
                (current if owner == "current" else prior)[key] = value
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_missing_input_or_one_league_scope_invalidates(self):
        current, prior = self.evidence()
        current["inputTrees"].pop("data-source")
        self.assertIn("incomplete-current-input-fingerprints",
                      shadow.decide(current, prior)["reasonCodes"])
        current, prior = self.evidence()
        current["scope"] = "nfl-reise/2026"
        self.assertIn("incomplete-multi-league-scope",
                      shadow.decide(current, prior)["reasonCodes"])

    def test_current_live_probe_does_not_invent_positive_race_or_recovery_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            for path in shadow.STAGE_OUTPUTS["standings"]:
                target = repo / path
                if path.endswith(".json"):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("{}")
                else:
                    target.mkdir(parents=True)
            with patch.object(shadow, "sha_for", return_value="test-fingerprint"), patch.object(
                shadow.subprocess, "run",
                return_value=type("Result", (), {"stdout": "a" * 40})(),
            ):
                current = shadow.collect(repo, "standings", "2026-11-03T19:30:00Z", "success", "success")
            self.assertIsNone(current["raceFree"])
            self.assertIsNone(current["recoveryClean"])
            self.assertEqual([], current["missingOutputs"])
            self.assertEqual("would-run", shadow.decide(current, None)["decision"])

    def test_decision_logs_annotate_no_enforcement(self):
        current, prior = self.evidence()
        result = {**shadow.decide(current, prior), "inputFingerprint": shadow.fingerprint(current["inputTrees"])}
        with tempfile.TemporaryDirectory() as temp:
            summary = Path(temp) / "summary.md"
            with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary)}):
                with patch("builtins.print") as printed:
                    shadow.publish_observation(result)
            self.assertIn("would-skip", summary.read_text())
            self.assertIn("(no jobs skipped)", summary.read_text())
            self.assertIn("LEAGUE_LIVE_SHADOW", printed.call_args[0][0])

    def test_workflow_preserves_publishers_and_adds_only_nonblocking_observers(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/league-live.yml").read_text()
        self.assertEqual(2, workflow.count("tools/league_live_shadow_gate.py"))
        self.assertIn("--stage standings", workflow)
        self.assertIn("--stage league", workflow)
        self.assertEqual(2, workflow.count("--source-status"))
        self.assertEqual(2, workflow.count("continue-on-error: true"))
        self.assertIn("Rebuild and publish Standings data", workflow)
        self.assertIn("Rebuild and publish League, PlayerWeekFantasy", workflow)
        self.assertIn("cancel-in-progress: false", workflow)



    def test_league_shadow_inventory_includes_future_draft_contract_surfaces(self):
        required = {
            "public/data/Drafts.json",
            "public/data/Transactions.json",
            "data-derived/league-drafts",
            "data-derived/league-transactions",
        }
        self.assertTrue(required <= set(shadow.STAGE_OUTPUTS["league"]))
        # A directory existing is not proof that all configured future seasons
        # have coherent partitions; that remains a separate production gate.

    def test_missing_draft_partition_root_or_app_drafts_forces_offline_run(self):
        for missing in ("data-derived/league-drafts", "public/data/Drafts.json",
                        "data-derived/league-transactions", "public/data/Transactions.json"):
            with self.subTest(missing=missing):
                current, prior = self.evidence("league")
                current["missingOutputs"] = [missing]
                result = shadow.decide(current, prior)
                self.assertEqual("would-run", result["decision"])
                self.assertIn("missing-or-unknown-output", result["reasonCodes"])
                self.assertFalse(result["enforced"])

    def test_forged_finality_race_and_attestation_cannot_authorize_skip(self):
        cases = (
            ("prior", "completedSuccessfully", "success"),
            ("prior", "outputsValidated", 1),
            ("prior", "clockBoundaryProof", "true"),
            ("prior", "raceFree", 1),
            ("prior", "recoveryClean", "yes"),
            ("current", "raceFree", "true"),
            ("current", "recoveryClean", 1),
        )
        for owner, field, bad in cases:
            with self.subTest(owner=owner, field=field):
                current, prior = self.evidence("league")
                (current if owner == "current" else prior)[field] = bad
                result = shadow.decide(current, prior)
                self.assertEqual("would-run", result["decision"])
                self.assertFalse(result["enforced"])

    def test_prior_revision_clock_and_league_scope_must_match(self):
        cases = (
            ("schemaVersion", 2),
            ("stage", "standings"),
            ("scope", "nfl-reise/2026"),
            ("processedAtUtc", "2026-11-03T19:31:00Z"),
            ("validUntilUtc", "2026-11-03T19:29:59Z"),
        )
        for key, bad in cases:
            with self.subTest(key=key):
                current, prior = self.evidence("league")
                prior[key] = bad
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])





class DraftContentAuditTests(unittest.TestCase):
    def fixture(self):
        drafts = [
            {"DraftKey": "2026_Rookie", "Season": "2026",
             "Picks": [{"PickKey": "2026_Rookie_R1_OO1", "CurrentOwnerRosterID": 2}]},
            {"DraftKey": "2031_Rookie", "Season": "2031",
             "Picks": [{"PickKey": "2031_Rookie_R1_OO2", "CurrentOwnerRosterID": 1}]},
            {"DraftKey": "2032_Free_Agent", "Season": "2032",
             "Picks": [{"PickKey": "2032_Free_Agent_R1_OO1", "CurrentOwnerRosterID": 2}]},
        ]
        teams = [
            {"TeamID": 1, "DraftPicks": ["2031_Rookie_R1_OO2"]},
            {"TeamID": 2, "DraftPicks": ["2026_Rookie_R1_OO1", "2032_Free_Agent_R1_OO1"]},
        ]
        return drafts, teams

    def test_owner_projection_has_dynamic_future_years_and_trades(self):
        drafts, teams = self.fixture()
        self.assertEqual([], shadow.compare_draft_owner_membership(drafts, teams))
        self.assertEqual({2026, 2031, 2032}, {int(d["Season"]) for d in drafts})

    def test_owner_projection_rejects_missing_extra_duplicate_and_wrong_team(self):
        drafts, teams = self.fixture()
        wrong = [{"TeamID": 1, "DraftPicks": [
            "2031_Rookie_R1_OO2", "2026_Rookie_R1_OO1", "extraneous"]},
                 {"TeamID": 2, "DraftPicks": [
                     "2026_Rookie_R1_OO1", "2032_Free_Agent_R1_OO1"]}]
        result = shadow.compare_draft_owner_membership(drafts, wrong)
        self.assertIn("league-owner-mismatch:2026_Rookie_R1_OO1", result)
        self.assertIn("duplicate-league-pick-key:2026_Rookie_R1_OO1", result)
        self.assertIn("league-extra-pick:extraneous", result)
        missing = [{"TeamID": 1, "DraftPicks": []}, {"TeamID": 2, "DraftPicks": []}]
        self.assertIn("league-missing-pick:2031_Rookie_R1_OO2",
                      shadow.compare_draft_owner_membership(drafts, missing))
        duplicate_drafts = list(drafts) + [drafts[0]]
        self.assertIn("duplicate-app-pick-key:2026_Rookie_R1_OO1",
                      shadow.compare_draft_owner_membership(duplicate_drafts, teams))

    def test_owner_projection_rejects_unknown_team_and_malformed_inputs(self):
        drafts, teams = self.fixture()
        drafts[0]["Picks"][0]["CurrentOwnerRosterID"] = 99
        self.assertIn("owner-has-no-team:2026_Rookie_R1_OO1",
                      shadow.compare_draft_owner_membership(drafts, teams))
        self.assertTrue(shadow.compare_draft_owner_membership([], teams))
        self.assertTrue(shadow.compare_draft_owner_membership(drafts, [{"TeamID": 1, "DraftPicks": "not-list"}]))

    def test_offline_audit_reuses_history_and_never_authorizes_live_skip(self):
        drafts, teams = self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "public/data"
            data.mkdir(parents=True)
            (data / "Drafts.json").write_text(json.dumps(drafts), encoding="utf-8")
            (data / "League.json").write_text(json.dumps({"Teams": teams}), encoding="utf-8")
            with patch("tools.league_history_app_publish.load_inputs",
                       return_value=SimpleNamespace(league_year=2026)), patch(
                       "tools.league_history_app_publish.build_history",
                       return_value=SimpleNamespace(unresolved=[])), patch(
                       "tools.league_history_app_publish.verified_product_history",
                       return_value=(object(), None)), patch(
                       "tools.league_history_app_publish.render",
                       return_value={"Drafts": {"current": drafts}}):
                result = shadow.audit_draft_content(root, "nfl-reise")
                self.assertEqual("verified", result["status"])
                self.assertEqual([2026, 2031, 2032], result["draftSeasons"])
                self.assertEqual(3, result["picks"])
                self.assertTrue(result["contentParityVerified"])
                self.assertFalse(result["safeToSkip"])
                self.assertFalse(result["enforced"])
                (data / "Drafts.json").write_text("[]", encoding="utf-8")
                invalid = shadow.audit_draft_content(root, "nfl-reise")
                self.assertEqual("blocked", invalid["status"])
                self.assertFalse(invalid["contentParityVerified"])

    def test_offline_audit_missing_future_derived_partition_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tools.league_history_app_publish.load_inputs",
                       return_value=SimpleNamespace(league_year=2026)), patch(
                       "tools.league_history_app_publish.build_history",
                       return_value=SimpleNamespace(unresolved=[])), patch(
                       "tools.league_history_app_publish.verified_product_history",
                       side_effect=ValueError("Stale Shared Derived league-drafts/2031")):
                result = shadow.audit_draft_content(Path(tmp), "nfl-reise")
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["contentParityVerified"])
                self.assertFalse(result["safeToSkip"])
                self.assertIn("2031", result["errors"][0])

    def test_offline_audit_cli_is_separate_from_live_and_requires_league(self):
        with patch.object(shadow, "audit_draft_content", return_value={
            "contentParityVerified": True, "safeToSkip": False, "enforced": False,
        }) as audit:
            with patch("builtins.print"):
                self.assertEqual(0, shadow.main(["--audit-draft-content", "--league", "nfl-reise"]))
            audit.assert_called_once()
        with self.assertRaises(SystemExit):
            shadow.main(["--audit-draft-content"])
        with self.assertRaises(SystemExit):
            shadow.main(["--audit-draft-content", "--league", "nfl-reise", "--stage", "league"])


class ShadowLogComparisonTests(unittest.TestCase):
    def log(self, stage: str = "league", at: str = "2026-11-03T20:17:31Z",
            changed_path: str | None = None, no_op: bool = True) -> str:
        trees = {name: "a" * 40 for name in shadow.STAGE_INPUTS[stage]}
        if changed_path:
            trees[changed_path] = "b" * 40
        row = {
            "schemaVersion": shadow.SCHEMA, "stage": stage, "atUtc": at,
            "checkedOutHead": "c" * 40, "decision": "would-run", "enforced": False,
            "inputTrees": trees, "inputFingerprint": shadow.fingerprint(trees),
            "missingOutputs": [], "reasonCodes": ["missing-previous-successful-attestation"],
        }
        return ("20:01 log before\n20:02 LEAGUE_LIVE_SHADOW " + json.dumps(row)
                + "\n" + ("Generator produced no repository changes. Nothing to publish."
                          if no_op else "Generator produced changes"))

    def test_equal_input_evidence_never_authorizes_skip(self):
        observed = shadow.compare_observed_logs(self.log(), self.log(at="2026-11-03T20:31:30Z"))
        self.assertEqual("same-observed-inputs", observed["classification"])
        self.assertEqual([], observed["changedPaths"])
        self.assertTrue(observed["previousPublisherNoOpLogMarker"])
        self.assertTrue(observed["currentPublisherNoOpLogMarker"])
        self.assertFalse(observed["safeToSkip"])
        self.assertFalse(observed["enforced"])
        self.assertIn("temporal-boundary-safety", observed["unproven"])

    def test_source_finality_derived_meta_changes_invalidate_input_equality(self):
        for path in ("data-source", "data-derived", "data-meta"):
            with self.subTest(path=path):
                observed = shadow.compare_observed_logs(
                    self.log(), self.log(at="2026-11-03T20:31:30Z", changed_path=path))
                self.assertEqual("changed-input-revision", observed["classification"])
                self.assertEqual([path], observed["changedPaths"])
                self.assertFalse(observed["safeToSkip"])

    def test_different_stages_rejected(self):
        with self.assertRaisesRegex(ValueError, "stages"):
            shadow.compare_observed_logs(self.log("standings"), self.log("league"))

    def test_duplicate_missing_malformed_observations_are_rejected(self):
        good = self.log()
        for text in (good + "\n" + good, "no shadow record", "LEAGUE_LIVE_SHADOW {bad-json"):
            with self.subTest(text=text[:25]):
                with self.assertRaises(ValueError):
                    shadow.compare_observed_logs(text, good)

    def test_nonmonotonic_time_bad_signature_and_missing_output_fail_closed(self):
        earlier = self.log()
        reversed_order = shadow.compare_observed_logs(
            earlier, self.log(at="2026-11-03T20:00:00Z"))
        self.assertEqual("unverifiable", reversed_order["classification"])
        bad = self.log(at="2026-11-03T20:31:30Z").replace('"inputFingerprint": "', '"inputFingerprint": "bad')
        self.assertEqual("unverifiable", shadow.compare_observed_logs(earlier, bad)["classification"])
        absent = self.log(at="2026-11-03T20:31:30Z").replace('"missingOutputs": []', '"missingOutputs": ["public/data/League.json"]')
        self.assertEqual("unverifiable", shadow.compare_observed_logs(earlier, absent)["classification"])

    def test_publisher_noop_is_only_log_marker_not_asserted_success(self):
        result = shadow.compare_observed_logs(
            self.log(), self.log(at="2026-11-03T20:31:30Z", no_op=False))
        self.assertEqual("same-observed-inputs", result["classification"])
        self.assertFalse(result["currentPublisherNoOpLogMarker"])
        self.assertFalse(result["safeToSkip"])

    def test_compare_log_files_cli_keeps_existing_live_stage_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            earlier, later = Path(temp) / "earlier.log", Path(temp) / "later.log"
            earlier.write_text(self.log(), encoding="utf-8")
            later.write_text(self.log(at="2026-11-03T20:31:30Z"), encoding="utf-8")
            with patch("builtins.print") as printed:
                rc = shadow.main(["--compare-log-files", str(earlier), str(later)])
            self.assertEqual(0, rc)
            self.assertEqual("same-observed-inputs", json.loads(printed.call_args[0][0])["classification"])
            self.assertFalse(json.loads(printed.call_args[0][0])["safeToSkip"])
            self.assertEqual(2, shadow.main(["--compare-log-files", str(earlier), str(Path(temp) / "missing")]))

if __name__ == "__main__":
    unittest.main()
