"""Fail-closed and no-skip regression cases for League Live shadow observation (#1263 G5)."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
