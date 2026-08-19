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

    def test_materializer_keeps_0645_as_non_disruptive_catch_up(self) -> None:
        workflow = self.workflow_text()

        self.assertIn('cron: "45 4 * * *"', workflow)
        self.assertIn('cron: "45 5 * * *"', workflow)
        self.assertIn("- fantasy-management/sources/external-rankings/**", workflow)
        self.assertIn("- fantasy-management/sources/external-signals/**", workflow)
        self.assertIn(
            "fantasy-management/_ai/scripts/resolve_fantasy_operations_materialization_trigger.py",
            workflow,
        )
        self.assertIn("jobs:\n  gate:", workflow)
        self.assertIn("needs: gate", workflow)
        self.assertIn("if: needs.gate.outputs.run == 'true'", workflow)
        self.assertIn("concurrency:\n      group: fantasy-operations-input-materialization", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'push' }}", workflow)
        self.assertNotIn("cancel-in-progress: true", workflow)
        self.assertIn("timeout-minutes: 15", workflow)

        gate_index = workflow.index("  gate:")
        materialize_index = workflow.index("  materialize:")
        concurrency_index = workflow.index("    concurrency:", materialize_index)
        self.assertLess(gate_index, materialize_index)
        self.assertGreater(concurrency_index, materialize_index)

        gate_block = workflow[gate_index:materialize_index]
        self.assertIn("fetch-depth: 2", gate_block)
        self.assertIn("$GITHUB_EVENT_PATH", gate_block)
        self.assertIn(".added[]?, .modified[]?, .removed[]?", gate_block)
        self.assertIn("Push payload is truncated", gate_block)
        self.assertIn("git rev-parse HEAD^", gate_block)
        self.assertIn("git diff --name-only HEAD^ HEAD", gate_block)
        self.assertIn("used shallow parent diff", gate_block)

        for immediate_path in (
            "public/data/League.json",
            "public/data/Players.json",
            "public/data/Timestamps.json",
        ):
            self.assertIn(immediate_path, workflow)

        self.assertIn("workflow_dispatch:", workflow)


if __name__ == "__main__":
    unittest.main()
