from __future__ import annotations

import unittest
from pathlib import Path


class SourceRefreshFreshnessWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]

    def _read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def test_external_source_workflows_publish_success_heartbeats(self) -> None:
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
