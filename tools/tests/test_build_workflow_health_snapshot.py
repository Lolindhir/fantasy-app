import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "build_workflow_health_snapshot.py"
REPOSITORY_ROOT = Path(__file__).parents[2]
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

    def test_scheduler_repository_dispatch_is_relevant_but_manual_dispatch_is_ignored(self):
        entry = {"category": "important", "relevantEvents": ["repository_dispatch"]}
        runs = [
            run(2, "success", "2026-08-29T23:50:00Z", event="workflow_dispatch"),
            run(1, "success", "2026-08-29T23:40:00Z", event="repository_dispatch"),
        ]
        result, incidents = module.evaluate_workflow("w.yml", entry, CATEGORY, API_WORKFLOW, runs, EVALUATION, NOW)
        self.assertEqual(result["latestRelevantRun"]["id"], 1)
        self.assertEqual(result["latestRelevantRun"]["event"], "repository_dispatch")
        self.assertEqual(incidents, [])

    def test_weekly_audit_first_due_grace_then_missing_or_failed(self):
        entry = {
            "category": "important", "relevantEvents": ["repository_dispatch"],
            "staleAfterMinutes": 11520,
            "firstDueAt": "2026-10-22T00:15:00Z", "firstDueGraceMinutes": 120,
        }
        category = {"notify": True, "consecutiveFailures": 1}
        before = datetime.fromisoformat("2026-10-22T01:00:00+00:00")
        after = datetime.fromisoformat("2026-10-22T02:20:00+00:00")
        waiting, incidents = module.evaluate_workflow(
            ".github/workflows/build.yml", entry, category, API_WORKFLOW, [], EVALUATION, before)
        self.assertTrue(waiting["awaitingFirstScheduledAudit"])
        self.assertEqual([], incidents)
        _, missing = module.evaluate_workflow(
            ".github/workflows/build.yml", entry, category, API_WORKFLOW, [], EVALUATION, after)
        self.assertIn("missing-success-evidence", [x["type"] for x in missing])
        _, failures = module.evaluate_workflow(
            ".github/workflows/build.yml", entry, category, API_WORKFLOW,
            [run(4, "failure", "2026-10-22T00:55:00Z", event="repository_dispatch")],
            EVALUATION, before)
        self.assertIn("failure-streak", [x["type"] for x in failures])
        _, healed = module.evaluate_workflow(
            ".github/workflows/build.yml", entry, category, API_WORKFLOW,
            [run(5, "success", "2026-10-22T01:25:00Z", event="repository_dispatch"),
             run(4, "failure", "2026-10-22T00:55:00Z", event="repository_dispatch")],
            EVALUATION, after)
        self.assertEqual([], healed)

    def test_weekly_audit_stale_result_ignores_operator_manual_success(self):
        entry = {"category": "important", "relevantEvents": ["repository_dispatch"],
                 "staleAfterMinutes": 11520}
        category = {"notify": True, "consecutiveFailures": 1}
        now = datetime.fromisoformat("2026-11-02T00:00:00+00:00")
        _, incidents = module.evaluate_workflow(
            ".github/workflows/build.yml", entry, category, API_WORKFLOW,
            [run(2, "success", "2026-11-01T23:30:00Z", event="workflow_dispatch"),
             run(1, "success", "2026-10-22T00:45:00Z", event="repository_dispatch")],
            EVALUATION, now)
        self.assertIn("stale-success", [x["type"] for x in incidents])

    def test_inflight_run_is_exposed_without_affecting_completed_health_evaluation(self):
        runs = [
            run(2, None, "2026-08-29T23:55:00Z", status="in_progress"),
            run(1, "success", "2026-08-29T23:40:00Z"),
        ]
        result, incidents = module.evaluate_workflow("w.yml", ENTRY, CATEGORY, API_WORKFLOW, runs, EVALUATION, NOW)
        self.assertEqual(result["latestRelevantInFlightRun"]["id"], 2)
        self.assertEqual(result["latestRelevantInFlightRun"]["status"], "in_progress")
        self.assertEqual(result["latestRelevantRun"]["id"], 1)
        self.assertEqual(result["failureStreak"], 0)
        self.assertEqual(incidents, [])


class SnapshotTests(unittest.TestCase):
    def test_canonical_monitoring_policy_parses(self):
        policy = module.load_policy(REPOSITORY_ROOT / ".ai-context/manual/workflow-monitoring.yaml")
        self.assertEqual(policy["ownership"]["canonicalFile"], ".ai-context/manual/workflow-monitoring.yaml")
        self.assertEqual(policy["snapshot"]["cadence"]["observationBarrier"]["deadlineAnchor"], "productive-blocker-start-or-dispatch-time")
        self.assertEqual(policy["workflows"][".github/workflows/build.yml"]["firstDueAt"], "2026-10-22T00:15:00Z")

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

    def test_weekly_audit_run_query_is_server_filtered_despite_many_prs(self):
        entry = {
            "category": "important", "consecutiveFailures": 1,
            "relevantEvents": ["repository_dispatch"], "runListEvent": "repository_dispatch",
            "staleAfterMinutes": 11520, "firstDueAt": "2026-10-22T00:15:00Z",
            "firstDueGraceMinutes": 120,
        }
        policy = {
            "ownership": {"canonicalFile": ".ai-context/manual/workflow-monitoring.yaml"},
            "runEvaluation": {**EVALUATION, "recentRunsToInspect": 20},
            "categories": {"important": {"notify": True, "consecutiveFailures": 2}},
            "workflows": {".github/workflows/build.yml": entry},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/build.yml").write_text("name: CI\n", encoding="utf-8")
            queries = []
            def api_get(path):
                queries.append(path)
                if path.startswith("/actions/workflows?"):
                    return {"workflows": [{"id": 10, "path": ".github/workflows/build.yml", "state": "active"}]}
                return {"workflow_runs": [
                    run(123, "failure", "2026-10-22T01:00:00Z", event="repository_dispatch")]}
            observed = datetime.fromisoformat("2026-10-22T01:05:00+00:00")
            snapshot = module.build_snapshot(policy, "owner/repo", root, api_get, observed)
            self.assertIn("/actions/workflows/10/runs?per_page=20&event=repository_dispatch", queries)
            self.assertIn("failure-streak", [x["type"] for x in snapshot["incidents"]])

    def test_notification_due_only_on_first_observation(self):
        incident = {"incidentKey": "abc", "type": "failure-streak", "workflow": "w.yml"}
        first = {"generatedAt": "2026-08-29T23:00:00Z", "incidents": [{**incident, "firstObservedAt": "2026-08-29T23:00:00Z"}]}
        current = [{**incident}]
        module.carry_incident_observation_state(current, first, NOW, 24)
        self.assertFalse(current[0]["notificationDue"])

    def test_failure_streak_growth_is_material_change(self):
        prior_incident = {
            "incidentKey": "abc",
            "type": "failure-streak",
            "workflow": "w.yml",
            "category": "important",
            "failureStreak": 2,
            "firstObservedAt": "2026-08-29T23:00:00Z",
        }
        previous = {"generatedAt": "2026-08-29T23:30:00Z", "incidents": [prior_incident]}
        current = [{**prior_incident, "failureStreak": 3}]
        module.carry_incident_observation_state(current, previous, NOW, 24)
        self.assertTrue(current[0]["notificationDue"])


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


class GithubGetterRetryTests(unittest.TestCase):
    def getter(self, outcomes, delays=None):
        calls = []
        sleeps = []

        def opener(request, timeout):
            calls.append(request.full_url)
            outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
            if isinstance(outcome, BaseException):
                raise outcome
            return _FakeResponse(outcome)

        get = module.github_getter(
            "owner/repo", "token", opener=opener, sleep=sleeps.append, jitter=lambda: 0.0,
            **({"retry_delays": delays} if delays else {}),
        )
        return get, calls, sleeps

    @staticmethod
    def http_error(code, headers=None):
        import io
        from email.message import Message
        message = Message()
        for key, value in (headers or {}).items():
            message[key] = value
        return module.HTTPError("https://api.github.com/x", code, "err", message, io.BytesIO(b'{"message":"Server Error"}'))

    def test_single_502_is_retried_and_succeeds(self):
        get, calls, sleeps = self.getter([self.http_error(502), b'{"ok": true}'])
        self.assertEqual(get("/actions/workflows?per_page=100"), {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2.0])

    def test_persistent_5xx_fails_after_budget_with_backoff(self):
        get, calls, sleeps = self.getter([self.http_error(503)])
        with self.assertRaisesRegex(RuntimeError, "GitHub API 503"):
            get("/x")
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, [2.0, 5.0, 10.0])

    def test_retry_after_is_honoured_on_429(self):
        get, _calls, sleeps = self.getter([self.http_error(429, {"Retry-After": "20"}), b"{}"])
        get("/x")
        self.assertEqual(sleeps, [20.0])

    def test_network_abort_is_retried(self):
        get, calls, sleeps = self.getter([module.URLError("reset"), b"{}"])
        get("/x")
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2.0])

    def test_client_errors_fail_immediately(self):
        for code in (401, 403, 404, 422):
            get, calls, sleeps = self.getter([self.http_error(code)])
            with self.assertRaisesRegex(RuntimeError, f"GitHub API {code}"):
                get("/x")
            self.assertEqual(len(calls), 1)
            self.assertEqual(sleeps, [])

VOLUME_SETTINGS = {"windowHours": 24, "warningFactor": 2, "warningOffset": 2, "cancelledWarningMinimum": 5}


def dispatch_runs(count, conclusion="success", start_minutes_ago=30, spacing=10):
    return [
        run(
            1000 + index,
            conclusion,
            (NOW - timedelta(minutes=start_minutes_ago + index * spacing)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            event="repository_dispatch",
        )
        for index in range(count)
    ]


class RunVolumeTests(unittest.TestCase):
    PLAYERS = {"id": "players", "timezone": "America/New_York", "cron": ["15 1 * * *", "0 8 * * *", "30 13 * * *"]}

    def test_cron_slot_count_uses_target_timezone(self):
        start = NOW - timedelta(hours=24)
        self.assertEqual(module.count_cron_slots(self.PLAYERS["cron"], self.PLAYERS["timezone"], start, NOW), 3)
        self.assertEqual(module.count_cron_slots(["*/10 * * * *"], "Etc/UTC", start, NOW), 144)
        self.assertEqual(module.count_cron_slots(["0 17 * * 3"], "Europe/Berlin", start, NOW), 0)

    def test_forty_six_runs_for_three_slots_warns(self):
        volume = module.evaluate_run_volume(self.PLAYERS, dispatch_runs(46, spacing=15), VOLUME_SETTINGS, EVALUATION, NOW)
        self.assertEqual(volume["expected24h"], 3)
        self.assertEqual(volume["observed24h"], 46)
        self.assertTrue(volume["warning"])

    def test_normal_volume_with_retries_does_not_warn(self):
        volume = module.evaluate_run_volume(self.PLAYERS, dispatch_runs(8, spacing=60), VOLUME_SETTINGS, EVALUATION, NOW)
        self.assertFalse(volume["warning"])

    def test_game_window_target_at_dense_cron_does_not_warn(self):
        target = {"id": "nfl-live", "timezone": "Europe/Berlin", "cron": ["*/10 * * * *"], "mode": "game-window"}
        volume = module.evaluate_run_volume(target, dispatch_runs(100, spacing=10), VOLUME_SETTINGS, EVALUATION, NOW)
        self.assertEqual(volume["expected24h"], 144)
        self.assertFalse(volume["warning"])
        self.assertTrue(volume["truncated"])

    def test_push_manual_and_old_runs_are_not_counted(self):
        runs = dispatch_runs(1) + [
            run(1, "success", "2026-08-29T23:00:00Z", event="push"),
            run(2, "success", "2026-08-29T22:00:00Z", event="workflow_dispatch"),
            run(3, "success", "2026-08-27T22:00:00Z", event="repository_dispatch"),
        ]
        volume = module.evaluate_run_volume(self.PLAYERS, runs, VOLUME_SETTINGS, EVALUATION, NOW)
        self.assertEqual(volume["observed24h"], 1)

    def test_many_cancelled_runs_set_hint(self):
        volume = module.evaluate_run_volume(self.PLAYERS, dispatch_runs(7, "cancelled", spacing=60), VOLUME_SETTINGS, EVALUATION, NOW)
        self.assertTrue(volume["cancelledWarning"])
        self.assertFalse(volume["warning"])

    def test_snapshot_lists_warning_without_incident(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "update-players.yml").write_text("name: x\n")
            (root / ".github" / "workflow-schedules.json").write_text(
                '{"targets": [{"id": "players", "path": ".github/workflows/update-players.yml", '
                '"timezone": "America/New_York", "cron": ["15 1 * * *", "0 8 * * *", "30 13 * * *"]}]}'
            )
            policy = {
                "ownership": {"canonicalFile": "p.yaml"},
                "categories": {"important": CATEGORY},
                "runEvaluation": {**EVALUATION, "runVolume": {**VOLUME_SETTINGS, "scheduleConfig": ".github/workflow-schedules.json"}},
                "workflows": {".github/workflows/update-players.yml": {"category": "important", "relevantEvents": ["repository_dispatch"]}},
            }

            def api_get(path):
                if path.startswith("/actions/workflows?"):
                    return {"workflows": [{"id": 10, "path": ".github/workflows/update-players.yml", "state": "active"}]}
                return {"workflow_runs": dispatch_runs(46, spacing=15)}

            snapshot = module.build_snapshot(policy, "o/r", root, api_get, NOW)
        self.assertEqual(snapshot["overall"], "healthy")
        self.assertEqual(snapshot["incidents"], [])
        self.assertEqual([w["type"] for w in snapshot["warnings"]], ["multiple-starts"])
        self.assertTrue(snapshot["workflows"][".github/workflows/update-players.yml"]["runVolume"]["warning"])

    def test_canonical_policy_declares_run_volume(self):
        policy = module.load_policy(REPOSITORY_ROOT / ".ai-context/manual/workflow-monitoring.yaml")
        settings = policy["runEvaluation"]["runVolume"]
        targets = module.load_scheduler_targets(REPOSITORY_ROOT, settings["scheduleConfig"])
        self.assertIn(".github/workflows/league-live.yml", targets)
        for target in targets.values():
            module.count_cron_slots(target["cron"], target.get("timezone", "UTC"), NOW - timedelta(hours=1), NOW)


if __name__ == "__main__":
    unittest.main()
