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
            ".github/workflows/update-league.yml": ("league", "league.json"),
            ".github/workflows/update-players.yml": ("players", "players.json"),
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

    def test_league_uses_dedicated_dst_safe_morning_heartbeat_without_heartbeat_commits_every_ten_minutes(self) -> None:
        workflow = self._read(".github/workflows/update-league.yml")

        self.assertIn("cron: '*/10 * * * *'", workflow)
        self.assertIn("cron: '35 4 * * *'", workflow)
        self.assertIn("cron: '35 5 * * *'", workflow)
        self.assertIn('freshness_heartbeat=false', workflow)
        self.assertIn('freshness_heartbeat=true', workflow)
        self.assertIn("Dedicated 06:35 Europe/Berlin League freshness refresh selected.", workflow)

    def test_players_only_persists_morning_or_manual_freshness_heartbeat(self) -> None:
        workflow = self._read(".github/workflows/update-players.yml")

        self.assertIn('0 8,12,18 * * *', workflow)
        self.assertIn("Existing UTC player refresh selected without morning freshness heartbeat.", workflow)
        self.assertIn("Scheduled run selected for 05:05 Europe/Berlin with freshness heartbeat.", workflow)
        self.assertIn("Manual run: schedule gate passed with freshness heartbeat.", workflow)

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


if __name__ == "__main__":
    unittest.main()
