from __future__ import annotations

import unittest
from pathlib import Path


class KickerStreamingWorkflowTests(unittest.TestCase):
    def workflow_text(self) -> str:
        root = Path(__file__).resolve().parents[4]
        workflow_path = root / ".github/workflows/materialize-fantasy-operations-inputs.yml"
        return workflow_path.read_text(encoding="utf-8")

    def test_production_workflow_materializes_kicker_inputs_after_free_agents(self) -> None:
        workflow = self.workflow_text()

        required_paths = [
            "fantasy-management/automation/kicker-streaming-input-materialization.json",
            "fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py",
            "fantasy-management/_ai/scripts/tests/test_build_kicker_streaming_inputs.py",
            "fantasy-management/_ai/scripts/tests/test_kicker_streaming_workflow.py",
            "fantasy-management/_ai/schemas/kicker-streaming-inputs.schema.json",
        ]
        for path in required_paths:
            self.assertIn(path, workflow)

        free_agent_build = "python fantasy-management/_ai/scripts/build_free_agent_dataset.py"
        kicker_build = "python fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py"
        self.assertIn(free_agent_build, workflow)
        self.assertIn(kicker_build, workflow)
        self.assertLess(workflow.index(free_agent_build), workflow.index(kicker_build))

        self.assertIn(
            "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            workflow,
        )
        self.assertIn("kicker-streaming-inputs.schema.json", workflow)
        self.assertIn('data["population"]["candidate_count"]', workflow)
        self.assertIn('data["population"]["free_agent_count"]', workflow)

    def test_materializer_batches_external_refreshes_before_monitoring(self) -> None:
        workflow = self.workflow_text()

        self.assertIn('cron: "45 4 * * *"', workflow)
        self.assertIn('cron: "45 5 * * *"', workflow)
        self.assertIn(
            "Scheduled consolidation selected for 06:45 Europe/Berlin.",
            workflow,
        )
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("timeout-minutes: 15", workflow)

        for immediate_path in (
            "public/data/League.json",
            "public/data/Players.json",
            "public/data/Timestamps.json",
        ):
            self.assertIn(immediate_path, workflow)

        self.assertNotIn(
            "- fantasy-management/sources/external-rankings/**",
            workflow,
        )
        self.assertNotIn(
            "- fantasy-management/sources/external-signals/**",
            workflow,
        )
        self.assertIn("workflow_dispatch:", workflow)


if __name__ == "__main__":
    unittest.main()
