from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
JOB_PATH = ROOT / "fantasy-management/automation/jobs/entity-observation.json"
GATE_PATH = ROOT / "fantasy-management/automation/workflows/free-agent-monitoring-availability-gate.md"
FA_BOARD_PATH = "fantasy-management/generated/operations/fa-board-readmodel.json"
GATE_WORKFLOW_PATH = "fantasy-management/automation/workflows/free-agent-monitoring-availability-gate.md"


class FreeAgentMonitoringAvailabilityGateTests(unittest.TestCase):
    def test_entity_observation_requires_fa_board_and_gate_workflow(self) -> None:
        job = json.loads(JOB_PATH.read_text(encoding="utf-8"))

        dependencies = {
            item["path"]: item
            for item in job["dependencies"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        self.assertIn(FA_BOARD_PATH, dependencies)
        self.assertTrue(dependencies[FA_BOARD_PATH]["required"])

        workflow_refs = {
            item["path"]
            for item in job["configuration_refs"]
            if isinstance(item, dict) and item.get("kind") == "workflow"
        }
        self.assertIn(GATE_WORKFLOW_PATH, workflow_refs)

    def test_gate_is_fail_closed_without_destroying_discovery(self) -> None:
        contract = GATE_PATH.read_text(encoding="utf-8")

        self.assertIn("Only `availability_status = available`", contract)
        for status in ("drafted", "rostered", "unknown"):
            self.assertIn(f"`{status}`", contract)
        self.assertIn("Preserve the Movement event", contract)
        self.assertIn("do not notify or escalate the player as a currently available Free Agent", contract)
        self.assertIn("independent non-availability significance", contract)
        self.assertIn("Scheduled monitoring remains read-only", contract)


if __name__ == "__main__":
    unittest.main()
