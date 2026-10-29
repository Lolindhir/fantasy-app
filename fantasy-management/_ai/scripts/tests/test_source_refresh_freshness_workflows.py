from __future__ import annotations

import json
import unittest
from pathlib import Path


class SourceRefreshFreshnessWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]

    def _read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def _schedule_target(self, target_id: str) -> dict:
        config = json.loads(self._read(".github/workflow-schedules.json"))
        return next(target for target in config["targets"] if target["id"] == target_id)

    FM_DAILY = ".github/workflows/fm-daily.yml"
    MATERIALIZE_SCRIPT = "fantasy-management/_ai/scripts/materialize_operations_inputs.sh"

    def _materializer_text(self) -> str:
        """Workflow plus the generator script it runs through tools/rebuild_and_publish.py."""
        return self._read(self.FM_DAILY) + "\n" + self._read(self.MATERIALIZE_SCRIPT)

    def test_source_workflows_publish_success_heartbeats(self) -> None:
        providers = {
            "fantasypros": "fantasypros.json",
            "fantasycalc": "fantasycalc.json",
            "fantasy-football-calculator": "fantasy-football-calculator.json",
            "fftoday": "fftoday.json",
            "cbs-sports": "cbs-sports.json",
            "sleeper-trending": "sleeper.json",
        }
        workflow = self._read(self.FM_DAILY)
        providers_job = workflow.split("  providers:\n", 1)[1].split("\n  materialize:\n", 1)[0]

        self.assertIn("write_source_refresh_heartbeat.py", providers_job)
        self.assertLess(
            providers_job.index("write_source_refresh_heartbeat.py"),
            providers_job.index("Commit and push updates"),
        )
        for source_id, heartbeat_file in providers.items():
            with self.subTest(source=source_id):
                self.assertIn(f"source_id: {source_id}\n", providers_job)
                heartbeat_dir = (
                    "data-source/market/_status"
                    if source_id in {"sleeper-trending", "fantasycalc", "fantasypros", "fantasy-football-calculator", "cbs-sports", "fftoday"}
                    else "fantasy-management/sources/refresh-status"
                )
                self.assertIn(f"{heartbeat_dir}/{heartbeat_file}", providers_job)

    def test_source_workflows_use_shared_race_safe_publisher(self) -> None:
        workflow = self._read(self.FM_DAILY)

        self.assertTrue((self.root / "tools/publish_generated_commit.py").is_file())
        self.assertIn(
            "python tools/publish_generated_commit.py --remote origin --branch main",
            workflow,
        )
        self.assertNotIn("git push https://x-access-token:", workflow)
        self.assertNotIn("git push origin HEAD:main", workflow)

    def test_fm_daily_pipeline_runs_providers_as_matrix_before_materializer(self) -> None:
        workflow = self._read(self.FM_DAILY)
        target = self._schedule_target("fm-daily")

        self.assertEqual(target["workflow"], "fm-daily.yml")
        self.assertEqual(target["eventType"], "scheduler-fm-daily")
        self.assertEqual(target["timezone"], "Europe/Berlin")
        self.assertEqual(target["cron"], ["20 5 * * *"])
        self.assertEqual(target["satisfyingEvents"], ["repository_dispatch", "workflow_dispatch"])
        self.assertIn("- scheduler-fm-daily", workflow)
        self.assertNotIn("\n  schedule:\n", workflow)

        self.assertIn("fail-fast: false", workflow)
        providers_job = workflow.split("  providers:\n", 1)[1].split("\n  materialize:\n", 1)[0]
        for label in (
            "FM • Ranking • FantasyPros ECR",
            "FM • Ranking • FantasyCalc Market",
            "FM • Ranking • FFC ADP",
            "FM • Projection • FFToday",
            "FM • Projection • CBS Sports",
            "FM • Signal • Sleeper Trending",
        ):
            self.assertIn(f'label: "{label}"', providers_job)

        # The materializer runs after all providers, also when one of them failed.
        materialize_job = workflow.split("\n  materialize:\n", 1)[1].split("\n  report:\n", 1)[0]
        self.assertIn("needs: [gate, providers]", materialize_job)
        self.assertIn("!cancelled() && needs.gate.outputs.run == 'true'", materialize_job)

        # Partial provider failures stay visible.
        report_job = workflow.split("\n  report:\n", 1)[1]
        self.assertIn("needs: [providers, materialize]", report_job)
        self.assertIn("GITHUB_STEP_SUMMARY", report_job)
        self.assertIn("::warning", report_job)

    def test_fm_daily_provider_triggers_are_pull_request_validation_only(self) -> None:
        workflow = self._read(self.FM_DAILY)
        trigger_section = workflow.split("on:\n", 1)[1].split("  workflow_dispatch", 1)[0]
        push_section, pull_request_section = trigger_section.split("  pull_request:\n", 1)

        self.assertIn("  push:\n", trigger_section)
        for fetcher_path in (
            "fantasy-management/_ai/scripts/fetch_*.py",
            "fantasy-management/_ai/scripts/tests/test_fetch_*.py",
            ".github/workflows/fm-daily.yml",
        ):
            self.assertIn(f"      - {fetcher_path}\n", pull_request_section)
        # Provider commits must not start a second materializer run; fetcher changes refresh at the next daily run.
        self.assertNotIn("fantasy-management/sources/", trigger_section)
        self.assertNotIn("fetch_", push_section)
        self.assertIn("if: ${{ github.event_name != 'push' }}", workflow)
        self.assertGreaterEqual(workflow.count("github.event_name != 'pull_request'"), 4)
        self.assertIn(
            'run-name: "FM • Pipeline • Daily • ${{ github.event.head_commit.message || github.event.pull_request.title || github.event_name }}"',
            workflow,
        )

    def test_league_app_workflow_has_no_fantasy_management_dependency(self) -> None:
        # This is a cross-context invariant: FM may consume League app data, not own its producer.
        workflow = self._read(".github/workflows/league-live.yml")
        publication_wrapper = self._read("public/requests/RequestLeaguePublication.ps1")
        target = self._schedule_target("league-live")

        self.assertEqual(target["cron"], ["*/10 * * * *"])
        self.assertEqual(target["timezone"], "Etc/UTC")
        self.assertEqual(target["eventType"], "scheduler-league-live")
        for required in (
            "repository_dispatch:",
            "- scheduler-league-live",
            "python3 tools/rebuild_and_publish.py",
            "--scope league",
            "--path public/data",
            "pwsh ./public/requests/RequestLeaguePublication.ps1",
        ):
            self.assertIn(required, workflow)

        for required in (
            '& pwsh -NoLogo -NoProfile -File "$PSScriptRoot/RequestLeague.ps1"',
            '& pwsh -NoLogo -NoProfile -File "$PSScriptRoot/RequestWeeklyRecaps.ps1"',
        ):
            self.assertIn(required, publication_wrapper)
        self.assertNotIn("fantasy-management/", publication_wrapper)

        for forbidden in (
            "\n  schedule:\n",
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
        target = self._schedule_target("players")

        self.assertEqual(target["cron"], ["15 1 * * *", "0 8 * * *", "30 13 * * *"])
        self.assertEqual(target["timezone"], "America/New_York")
        self.assertEqual(target["eventType"], "scheduler-update-players")
        for required in (
            "repository_dispatch:",
            "- scheduler-update-players",
            "python3 tools/rebuild_and_publish.py",
            "--scope players",
            "--path public/data",
            "pwsh ./public/requests/RequestPlayers.ps1",
        ):
            self.assertIn(required, workflow)

        for forbidden in (
            "\n  schedule:\n",
            'cron: "0 8,12,18 * * *"',
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
        workflow = self._materializer_text()

        for required in (
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
        # Source and heartbeat commits are produced by the pipeline itself and never push-trigger the materializer.
        self.assertNotIn("fantasy-management/sources/refresh-status/**", self._read(self.FM_DAILY))

    def test_daily_chain_uses_central_schedule_and_does_not_cancel_running_materialization(self) -> None:
        workflow = self._read(self.FM_DAILY)

        self.assertNotIn("\n  schedule:\n", workflow)
        self.assertIn("repository_dispatch:", workflow)
        # A League/Players push queues behind a running materialization instead of cancelling the daily chain.
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotIn("cancel-in-progress: ${{ github.event_name == 'push' }}", workflow)

    def test_materializer_reports_trigger_start_and_publish_observability_without_using_it_for_readiness(self) -> None:
        workflow = self._read(self.FM_DAILY)

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
        workflow = self._read(self.FM_DAILY)

        self.assertNotIn("fantasy-management/generated/operations/**", workflow)

    def test_materializer_publishes_through_shared_rebuild_helper(self) -> None:
        workflow = self._read(self.FM_DAILY)
        script = self._read(self.MATERIALIZE_SCRIPT)

        for required in (
            "python3 tools/rebuild_and_publish.py",
            "--scope fantasy-operations",
            "--path fantasy-management/generated/operations",
            "bash fantasy-management/_ai/scripts/materialize_operations_inputs.sh",
        ):
            self.assertIn(required, workflow)
        for forbidden in ("git push", "for attempt in 1 2 3", "git reset --hard origin/main"):
            self.assertNotIn(forbidden, workflow)
            self.assertNotIn(forbidden, script)
        # The helper owns commit and push; the generator script only rebuilds files.
        self.assertNotIn("git commit", script)


if __name__ == "__main__":
    unittest.main()
