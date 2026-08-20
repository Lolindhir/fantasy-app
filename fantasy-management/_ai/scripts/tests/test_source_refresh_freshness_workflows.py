from __future__ import annotations

import unittest
from pathlib import Path


class SourceRefreshFreshnessWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]

    def _read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def test_source_workflows_publish_success_heartbeats(self) -> None:
        workflows = {
            ".github/workflows/update-fantasypros-rankings.yml": ("fantasypros", "fantasypros.json"),
            ".github/workflows/update-fantasycalc-rankings.yml": ("fantasycalc", "fantasycalc.json"),
            ".github/workflows/update-fantasy-football-calculator-adp.yml": (
                "fantasy-football-calculator",
                "fantasy-football-calculator.json",
            ),
            ".github/workflows/update-fftoday-projections.yml": ("fftoday", "fftoday.json"),
            ".github/workflows/update-cbs-sports-projections.yml": ("cbs-sports", "cbs-sports.json"),
            ".github/workflows/update-sleeper-trending.yml": ("sleeper-trending", "sleeper-trending.json"),
        }

        for workflow_path, (source_id, heartbeat_file) in workflows.items():
            with self.subTest(workflow=workflow_path):
                workflow = self._read(workflow_path)
                self.assertIn("write_source_refresh_heartbeat.py", workflow)
                self.assertIn(f"--source-id {source_id}", workflow)
                self.assertIn(f"fantasy-management/sources/refresh-status/{heartbeat_file}", workflow)
                self.assertLess(
                    workflow.index("write_source_refresh_heartbeat.py"),
                    workflow.index("Commit and push updates"),
                )

    def test_source_workflows_use_shared_race_safe_publisher(self) -> None:
        workflows = (
            ".github/workflows/update-fantasypros-rankings.yml",
            ".github/workflows/update-fantasycalc-rankings.yml",
            ".github/workflows/update-fantasy-football-calculator-adp.yml",
            ".github/workflows/update-fftoday-projections.yml",
            ".github/workflows/update-cbs-sports-projections.yml",
            ".github/workflows/update-sleeper-trending.yml",
        )

        self.assertTrue((self.root / "tools/publish_generated_commit.py").is_file())
        for workflow_path in workflows:
            with self.subTest(workflow=workflow_path):
                workflow = self._read(workflow_path)
                self.assertIn(
                    "python tools/publish_generated_commit.py --remote origin --branch main",
                    workflow,
                )
                self.assertNotIn("git push https://x-access-token:", workflow)
                self.assertNotIn("git push origin HEAD:main", workflow)

    def test_league_app_workflow_has_no_fantasy_management_dependency(self) -> None:
        # This is a cross-context invariant: FM may consume League app data, not own its producer.
        workflow = self._read(".github/workflows/update-league.yml")

        for required in (
            "cron: '*/10 * * * *'",
            "pwsh ./public/requests/RequestLeague.ps1",
            "git add public/data/**",
        ):
            self.assertIn(required, workflow)

        for forbidden in (
            "refresh_mode",
            "freshness_heartbeat",
            "write_source_refresh_heartbeat.py",
            "fantasy-management/",
            "actions/setup-python",
            "cron: '35 4 * * *'",
            "cron: '35 5 * * *'",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_players_app_workflow_has_no_fantasy_management_dependency(self) -> None:
        # This is a cross-context invariant: FM may consume Players.json, not own its producer.
        workflow = self._read(".github/workflows/update-players.yml")

        for required in (
            'cron: "0 8,12,18 * * *"',
            "pwsh ./public/requests/RequestPlayers.ps1",
            "git add public/data/**",
        ):
            self.assertIn(required, workflow)

        for forbidden in (
            'cron: "5 3 * * *"',
            'cron: "5 4 * * *"',
            "05:05 Europe/Berlin",
            "Resolve Berlin schedule window",
            "schedule_gate",
            "TZ=Europe/Berlin",
            "github.event.schedule",
            "freshness_heartbeat",
            "write_source_refresh_heartbeat.py",
            "fantasy-management/",
            "actions/setup-python",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_materializer_consumes_heartbeat_directory_and_publishes_gate(self) -> None:
        workflow = self._read(".github/workflows/materialize-fantasy-operations-inputs.yml")

        for required in (
            "fantasy-management/sources/refresh-status/**",
            "fantasy-management/automation/source-freshness-gate.json",
            "fantasy-management/_ai/scripts/build_source_freshness_gate.py",
            "fantasy-management/_ai/scripts/tests/test_build_source_freshness_gate.py",
            "fantasy-management/_ai/scripts/tests/test_source_refresh_freshness_workflows.py",
            "fantasy-management/_ai/schemas/source-freshness-gate.schema.json",
            "fantasy-management/generated/operations/source-freshness.json",
        ):
            self.assertIn(required, workflow)

        self.assertLess(
            workflow.index("python fantasy-management/_ai/scripts/build_source_freshness_gate.py"),
            workflow.index("python fantasy-management/_ai/scripts/build_fantasy_operations_inputs.py"),
        )
        self.assertIn("no_event_conclusion_allowed", workflow)

    def test_0645_catch_up_does_not_cancel_a_running_source_materialization(self) -> None:
        workflow = self._read(".github/workflows/materialize-fantasy-operations-inputs.yml")

        self.assertIn('cron: "45 4 * * *"', workflow)
        self.assertIn('cron: "45 5 * * *"', workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'push' }}", workflow)

    def test_materializer_reports_trigger_start_and_publish_observability_without_using_it_for_readiness(self) -> None:
        workflow = self._read(".github/workflows/materialize-fantasy-operations-inputs.yml")

        for required in (
            "Capture materialization observability start",
            "MATERIALIZER_STARTED_AT",
            "TRIGGER_COMMIT_AT",
            "summarize_fantasy_operations_materialization_observability.py",
            "--outcome published",
            "--outcome no_changes",
            "$GITHUB_STEP_SUMMARY",
        ):
            self.assertIn(required, workflow)

        self.assertNotIn("MATERIALIZER_STARTED_AT", self._read("fantasy-management/_ai/scripts/build_source_freshness_gate.py"))
        self.assertNotIn("TRIGGER_COMMIT_AT", self._read("fantasy-management/_ai/scripts/build_source_freshness_gate.py"))

    def test_generated_operations_outputs_are_not_push_triggers(self) -> None:
        workflow = self._read(".github/workflows/materialize-fantasy-operations-inputs.yml")

        self.assertNotIn("fantasy-management/generated/operations/**", workflow)

    def test_materializer_keeps_retry_rebuild_push_race_hardening(self) -> None:
        workflow = self._read(".github/workflows/materialize-fantasy-operations-inputs.yml")

        for required in (
            "for attempt in 1 2 3; do",
            "git fetch origin main",
            "git reset --hard origin/main",
            "Push race on attempt ${attempt}; rebuilding from current main.",
            "Unable to publish materialized Fantasy Operations inputs after 3 attempts.",
        ):
            self.assertIn(required, workflow)


if __name__ == "__main__":
    unittest.main()
