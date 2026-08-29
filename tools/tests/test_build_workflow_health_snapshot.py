import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "build_workflow_health_snapshot.py"
spec = importlib.util.spec_from_file_location("workflow_health", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def run(run_id, conclusion, created, event="schedule", branch="main", status="completed"):
    return {
        "id": run_id,
        "event": event,
        "head_branch": branch,
        "head_sha": f"sha-{run_id}",
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "updated_at": created,
        "html_url": f"https://example.test/runs/{run_id}",
    }


EVALUATION = {
    "defaultBranch": "main",
    "healthyConclusions": ["success"],
    "unhealthyConclusions": ["failure", "timed_out"],
    "ignoredConclusions": ["cancelled", "skipped", "neutral"],
}
CATEGORY = {"notify": True, "consecutiveFailures": 2}
ENTRY = {"category": "important", "relevantEvents": ["schedule"]}
API_WORKFLOW = {"id": 10, "state": "active"}
NOW = datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)


class WorkflowEvaluationTests(unittest.TestCase):
    def test_feature_branch_failure_is_ignored(self):
        result, incidents = module.evaluate_workflow(
            "w.yml", ENTRY, CATEGORY, API_WORKFLOW,
            [run(1, "failure", "2026-08-29T23:00:00Z", branch="feature/x")],
            EVALUATION, NOW,
        )
        self.assertEqual(result["failureStreak"], 0)
        self.assertEqual(incidents, [])

    def test_two_failures_trigger_incident(self):
        runs = [
            run(3, "failure", "2026-08-29T23:50:00Z"),
            run(2, "failure", "2026-08-29T23:40:00Z"),
            run(1, "success", "2026-08-29T23:30:00Z"),
        ]
        result, incidents = module.evaluate_workflow("w.yml", ENTRY, CATEGORY, API_WORKFLOW, runs, EVALUATION, NOW)
        self.assertEqual(result["failureStreak"], 2)
        self.assertEqual([i["type"] for i in incidents], ["failure-streak"])

    def test_newer_success_heals_older_failure(self):
        runs = [
            run(3, "success", "2026-08-29T23:50:00Z"),
            run(2, "failure", "2026-08-29T23:40:00Z"),
            run(1, "failure", "2026-08-29T23:30:00Z"),
        ]
        result, incidents = module.evaluate_workflow("w.yml", ENTRY, CATEGORY, API_WORKFLOW, runs, EVALUATION, NOW)
        self.assertEqual(result["failureStreak"], 0)
        self.assertEqual(incidents, [])

    def test_staleness_uses_latest_success(self):
        entry = {**ENTRY, "staleAfterMinutes": 45}
        runs = [run(1, "success", "2026-08-29T22:00:00Z")]
        result, incidents = module.evaluate_workflow("w.yml", entry, CATEGORY, API_WORKFLOW, runs, EVALUATION, NOW)
        self.assertEqual(result["successAgeMinutes"], 120)
        self.assertIn("stale-success", [i["type"] for i in incidents])


class SnapshotTests(unittest.TestCase):
    def test_configuration_drift_is_fail_closed(self):
        policy = {
            "ownership": {"canonicalFile": ".ai-context/manual/workflow-monitoring.yaml"},
            "runEvaluation": {**EVALUATION, "recentRunsToInspect": 20},
            "categories": {"important": CATEGORY},
            "workflows": {".github/workflows/known.yml": ENTRY},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/known.yml").write_text("name: known\n", encoding="utf-8")
            (root / ".github/workflows/new.yml").write_text("name: new\n", encoding="utf-8")

            def api_get(path):
                if path.startswith("/actions/workflows?"):
                    return {"workflows": [{"id": 10, "path": ".github/workflows/known.yml", "state": "active"}]}
                return {"workflow_runs": [run(1, "success", "2026-08-29T23:50:00Z")]}

            snapshot = module.build_snapshot(policy, "owner/repo", root, api_get, NOW)
            self.assertEqual(snapshot["overall"], "incident")
            self.assertIn("unclassified-workflow", [i["type"] for i in snapshot["configurationDrift"]])

    def test_notification_due_only_on_first_observation(self):
        incident = {"incidentKey": "abc", "type": "failure-streak", "workflow": "w.yml"}
        first = {"generatedAt": "2026-08-29T23:00:00Z", "incidents": [{**incident, "firstObservedAt": "2026-08-29T23:00:00Z"}]}
        current = [{**incident}]
        module.carry_incident_observation_state(current, first, NOW, 24)
        self.assertFalse(current[0]["notificationDue"])


if __name__ == "__main__":
    unittest.main()
