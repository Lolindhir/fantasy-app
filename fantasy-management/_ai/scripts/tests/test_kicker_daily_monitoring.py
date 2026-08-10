from __future__ import annotations

import json
import unittest
from pathlib import Path


class KickerDailyMonitoringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]

    def load_json(self, relative_path: str) -> dict:
        return json.loads((self.root / relative_path).read_text(encoding="utf-8"))

    def test_target_set_uses_current_kicker_streaming_contract(self) -> None:
        target_set = self.load_json(
            "fantasy-management/automation/target-sets/kicker-daily-monitoring.json"
        )
        self.assertEqual("kicker-daily-monitoring", target_set["id"])
        self.assertEqual("dynamic", target_set["mode"])
        self.assertEqual(1, len(target_set["selectors"]))

        selector = target_set["selectors"][0]
        self.assertEqual("kicker_streaming_candidates", selector["selector_type"])
        self.assertEqual("player", selector["entity_type"])
        self.assertEqual(
            "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            selector["parameters"]["source_path"],
        )
        self.assertEqual(["held", "free_agent"], selector["parameters"]["availability"])
        self.assertTrue(selector["parameters"]["fail_closed_when_source_missing_or_empty"])
        self.assertTrue(selector["parameters"]["require_candidate_count_match"])
        self.assertEqual(
            ["kicker-signal-movement"],
            [binding["profile_ref"] for binding in selector["profile_bindings"]],
        )

    def test_profile_reuses_kicker_contract_and_baseline_engine(self) -> None:
        profile = self.load_json(
            "fantasy-management/automation/profiles/kicker-signal-movement.json"
        )
        bindings = {binding["id"]: binding for binding in profile["source_bindings"]}

        contract = bindings["kicker-streaming-inputs-current"]
        self.assertEqual("kicker-streaming-inputs", contract["dataset_id"])
        self.assertEqual("repo_file", contract["access"]["type"])
        self.assertEqual(
            "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            contract["access"]["location"],
        )
        self.assertTrue(contract["format_context"]["league_scoring_reconciled"])
        self.assertEqual(30, contract["freshness_policy"]["max_age_hours"])

        baseline = bindings["kicker-baseline-analysis"]
        self.assertEqual("derived", baseline["access"]["type"])
        self.assertTrue(baseline["format_context"]["weekly_recommendation_forbidden"])
        self.assertEqual(
            "research_tiebreaker_only",
            baseline["format_context"]["activity_policy"],
        )

    def test_profile_has_material_kicker_change_classes(self) -> None:
        profile = self.load_json(
            "fantasy-management/automation/profiles/kicker-signal-movement.json"
        )
        classifications = {
            criterion["materiality"]["classification"]
            for criterion in profile["criteria"]
            if criterion["materiality"]["is_material"]
        }
        self.assertTrue(
            {
                "kicker_job_risk_change",
                "kicker_injury_change",
                "kicker_shortlist_entry",
                "kicker_baseline_change",
                "kicker_adp_change",
                "kicker_projection_change",
                "kicker_activity_change",
                "kicker_job_security_change",
            }.issubset(classifications)
        )

    def test_job_registers_kicker_target_profile_and_workflow(self) -> None:
        job = self.load_json("fantasy-management/automation/jobs/entity-observation.json")
        dependency_paths = {dependency["path"] for dependency in job["dependencies"]}
        ref_paths = {ref["path"] for ref in job["configuration_refs"]}

        required_paths = {
            "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            "fantasy-management/automation/target-sets/kicker-daily-monitoring.json",
            "fantasy-management/automation/profiles/kicker-signal-movement.json",
            "fantasy-management/automation/workflows/kicker-daily-monitoring.md",
        }
        self.assertTrue(required_paths.issubset(dependency_paths | ref_paths))
        self.assertIn(
            "fantasy-management/automation/target-sets/kicker-daily-monitoring.json",
            ref_paths,
        )
        self.assertIn(
            "fantasy-management/automation/profiles/kicker-signal-movement.json",
            ref_paths,
        )
        self.assertIn(
            "fantasy-management/automation/workflows/kicker-daily-monitoring.md",
            ref_paths,
        )

    def test_documentation_keeps_daily_and_weekly_decisions_separate(self) -> None:
        daily = (
            self.root
            / "fantasy-management/automation/workflows/kicker-daily-monitoring.md"
        ).read_text(encoding="utf-8")
        architecture = (
            self.root / "fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Weekly Lineup + Waiver", daily)
        self.assertIn("kein automatischer Add/Drop", daily)
        self.assertIn("Drop Opportunity Cost", architecture)
        self.assertIn("genau einen Kicker halten", architecture)
        self.assertIn("Zwei Kicker", architecture)


if __name__ == "__main__":
    unittest.main()
