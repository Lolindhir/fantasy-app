"""Read-only G5 GitHub Actions job-cost evidence and API pagination regressions."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools import audit_workflow_job_costs as audit


def run(run_id, day="2026-11-01", moment="12:00:00Z", conclusion="success"):
    return {
        "id": run_id, "created_at": f"{day}T{moment}",
        "path": ".github/workflows/league-live.yml", "event": "repository_dispatch",
        "status": "completed", "conclusion": conclusion, "run_attempt": 1,
    }


def job(job_id, started="2026-11-01T12:00:05Z",
        completed="2026-11-01T12:01:05Z", conclusion="success"):
    return {
        "id": job_id, "name": "build", "created_at": "2026-11-01T12:00:03Z",
        "started_at": started, "completed_at": completed, "conclusion": conclusion,
    }


class G5WorkflowCostAuditTests(unittest.TestCase):
    def test_paginated_run_census_requires_all_rows(self):
        def fetch(resource, params):
            self.assertEqual("actions/runs", resource)
            if params["page"] == 1:
                return {"total_count": 101, "workflow_runs": [run(i) for i in range(1, 101)]}
            return {"total_count": 101, "workflow_runs": [run(101)]}
        a = datetime(2026, 11, 1, tzinfo=timezone.utc)
        b = a.replace(hour=23, minute=59, second=59)
        self.assertEqual(101, len(audit.fetch_window(fetch, a, b)))
        def truncated(resource, params):
            result = fetch(resource, params)
            if params["page"] == 2:
                result["workflow_runs"] = []
            return result
        with self.assertRaisesRegex(audit.AuditError, "Incomplete run pages"):
            audit.fetch_window(truncated, a, b)

    def test_large_utc_day_splits_before_1000_api_limit(self):
        observed_ranges = []
        def fetch(resource, params):
            window = params["created"]
            if window == "2026-11-01T00:00:00Z..2026-11-01T23:59:59Z":
                return {"total_count": 1001, "workflow_runs": []}
            observed_ranges.append(window)
            if "T11:59:59Z" in window:
                return {"total_count": 1, "workflow_runs": [run(1, moment="11:59:59Z")]}
            return {"total_count": 1, "workflow_runs": [run(2, moment="12:00:00Z")]}
        a = datetime(2026, 11, 1, tzinfo=timezone.utc)
        b = a.replace(hour=23, minute=59, second=59)
        self.assertEqual({1, 2}, {r["id"] for r in audit.fetch_window(fetch, a, b)})
        self.assertIn("2026-11-01T12:00:00Z..2026-11-01T23:59:59Z", observed_ranges)

    def test_deterministic_samples_span_stratum(self):
        rows = [run(i, moment=f"{i:02d}:00:00Z") for i in range(10)]
        self.assertEqual([0, 4, 9], [r["id"] for r in audit.sample_evenly(rows, 3)])
        self.assertEqual([5], [r["id"] for r in audit.sample_evenly(rows, 1)])

    def test_queue_skips_and_unknown_times_not_misreported_as_cost(self):
        rows = [job(1), job(2, started=None, completed=None, conclusion="skipped")]
        result = audit.job_elapsed(rows)
        self.assertEqual(60, result["runnerSeconds"])
        self.assertEqual(2, result["queueSecondsObserved"])
        self.assertEqual(1, result["executedJobs"])
        self.assertEqual(1, result["skippedJobs"])
        self.assertEqual({"build": 60}, result["byJobNameSeconds"])
        self.assertIsNone(audit.job_elapsed([job(3, completed=None)])["runnerSeconds"])
        with self.assertRaises(audit.AuditError):
            audit.seconds_between("2026-11-01T12:01:05Z", "2026-11-01T12:00:05Z")

    def test_all_attempt_jobs_are_paginated_and_unique(self):
        def fetch(resource, params):
            self.assertEqual("all", params["filter"])
            if params["page"] == 1:
                return {"total_count": 101, "jobs": [job(i) for i in range(100)]}
            return {"total_count": 101, "jobs": [job(100)]}
        self.assertEqual(101, len(audit.fetch_jobs(fetch, 42)))
        def duplicate(resource, params):
            row = fetch(resource, params)
            if params["page"] == 2:
                row["jobs"] = [job(99)]
            return row
        with self.assertRaisesRegex(audit.AuditError, "Incomplete/duplicated jobs"):
            audit.fetch_jobs(duplicate, 42)

    def test_exact_runs_and_estimated_jobs_remain_distinct(self):
        rows = [run(i, moment=f"12:{i:02d}:00Z") for i in range(1, 6)]
        rows += [run(20, moment="13:00:00Z", conclusion="failure")]
        rows += [dict(run(30, moment="14:00:00Z"), status="in_progress", conclusion=None)]
        def fetch(resource, params):
            self.assertTrue(resource.endswith("/jobs"))
            return {"total_count": 1, "jobs": [job(int(resource.split("/")[2]))]}
        result = audit.summarize(rows, fetch, 2, 5)
        self.assertEqual(7, result["runCount"])
        self.assertEqual(3, result["jobListRequests"])
        self.assertIsNone(result["billableMinutes"])
        self.assertEqual("not-measured", result["noOpEvidence"])
        success = next(x for x in result["strata"] if x["conclusion"] == "success")
        self.assertEqual(5, success["runCount"])
        self.assertEqual(2, success["sampledRunCount"])
        self.assertEqual(300, success["projectedRunnerSeconds"])
        incomplete = next(x for x in result["strata"] if x["conclusion"].startswith("incomplete:"))
        self.assertIsNone(incomplete["projectedRunnerSeconds"])
        with self.assertRaisesRegex(audit.AuditError, "Would request"):
            audit.summarize(rows, fetch, 2, 2)


if __name__ == "__main__":
    unittest.main()
