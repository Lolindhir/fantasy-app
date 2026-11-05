"""Read-only G5 GitHub Actions job-cost evidence and API pagination regressions."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

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



class G5LastLeagueLiveProvenanceTests(unittest.TestCase):
    """Real run/job API status is not publication-commit or skip evidence."""

    def evidence(self):
        sha = "a" * 40
        main = "b" * 40
        latest = {
            "id": 41966328830, "run_attempt": 2,
            "repository": {"full_name": "Lolindhir/fantasy-app"},
            "path": audit.LEAGUE_LIVE_PATH, "head_branch": "main",
            "head_sha": sha, "event": "repository_dispatch",
            "status": "completed", "conclusion": "success",
            "created_at": "2026-11-05T04:12:13Z",
            "updated_at": "2026-11-05T04:16:01Z",
        }
        jobs = [
            {
                "id": index, "run_id": latest["id"], "run_attempt": 2,
                "name": name, "status": "completed", "conclusion": "success",
                "started_at": "2026-11-05T04:12:14Z",
                "completed_at": "2026-11-05T04:16:00Z",
            }
            for index, name in enumerate(sorted(audit.LEAGUE_LIVE_REQUIRED_JOBS), 1)
        ]
        jobs += [
            {
                "id": 10, "run_id": latest["id"], "run_attempt": 2,
                "name": "historical_preflight",
                "status": "completed", "conclusion": "skipped",
            },
            {
                "id": 11, "run_id": latest["id"], "run_attempt": 2,
                "name": "source / validate_current_sparse_pr",
                "status": "completed", "conclusion": "skipped",
            },
            # An older failed attempt must not override the latest attempt.
            {
                "id": 12, "run_id": latest["id"], "run_attempt": 1,
                "name": "league", "status": "completed", "conclusion": "failure",
            },
        ]
        ref = {"ref": "refs/heads/main", "object": {"sha": main}}
        comparison = {
            "status": "ahead", "behind_by": 0, "ahead_by": 2,
            "base_commit": {"sha": sha}, "merge_base_commit": {"sha": sha},
        }
        return latest, jobs, ref, comparison

    def evaluate(self, run, jobs, ref, comparison):
        return audit.evaluate_last_league_live_run(
            run, jobs, ref, comparison,
            repo="Lolindhir/fantasy-app",
            observed_at=datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
        )

    def test_independently_successful_jobs_never_prove_publication_or_skip(self):
        run, jobs, ref, comparison = self.evidence()
        result = self.evaluate(run, jobs, ref, comparison)
        self.assertEqual("job-completion-confirmed", result["status"])
        self.assertTrue(result["jobCompletionVerified"])
        self.assertTrue(result["mainAdvancedSinceRunStart"])
        self.assertEqual([], result["reasonCodes"])
        self.assertEqual(sorted(audit.LEAGUE_LIVE_REQUIRED_JOBS), result["verifiedJobs"])
        for key in ("publicationCommitVerified", "outputsValidated",
                    "timeAndFinalityVerified", "raceFree", "recoveryClean",
                    "safeToSkip", "enforced"):
            self.assertIs(result[key], False, key)

    def test_latest_failure_pending_or_wrong_identity_blocks(self):
        cases = (
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("event", "workflow_dispatch"),
            ("path", ".github/workflows/other.yml"),
            ("head_branch", "feature"),
            ("run_attempt", None),
            ("head_sha", "not-sha"),
            ("updated_at", "2026-11-05T04:09:01Z"),
        )
        for field, bad in cases:
            with self.subTest(field=field):
                run, jobs, ref, comparison = self.evidence()
                run[field] = bad
                result = self.evaluate(run, jobs, ref, comparison)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["jobCompletionVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_required_jobs_fail_closed_on_mismatch_skips_and_reruns(self):
        for name, bad in (
            ("name", "different"), ("status", "in_progress"),
            ("conclusion", "skipped"), ("run_id", 999),
            ("run_attempt", 3), ("started_at", None),
            ("completed_at", "2026-11-05T04:10:00Z"),
        ):
            with self.subTest(field=name):
                run, jobs, ref, comparison = self.evidence()
                jobs[0][name] = bad
                self.assertEqual("blocked", self.evaluate(run, jobs, ref, comparison)["status"])
        run, jobs, ref, comparison = self.evidence()
        jobs.append(dict(jobs[0], id=900))
        self.assertIn("duplicate-or-unnamed-current-job",
                      self.evaluate(run, jobs, ref, comparison)["reasonCodes"])
        run, jobs, ref, comparison = self.evidence()
        jobs[0].pop("run_attempt")
        self.assertIn("job-attempt-unverifiable",
                      self.evaluate(run, jobs, ref, comparison)["reasonCodes"])

    def test_diverged_main_bad_ref_or_unverified_compare_blocks(self):
        run, jobs, ref, comparison = self.evidence()
        ref["ref"] = "refs/heads/feature"
        self.assertEqual("blocked", self.evaluate(run, jobs, ref, comparison)["status"])
        run, jobs, ref, comparison = self.evidence()
        comparison["status"] = "diverged"
        comparison["behind_by"] = 3
        self.assertIn("main-not-proven-descendant-of-run-start",
                      self.evaluate(run, jobs, ref, comparison)["reasonCodes"])
        run, jobs, ref, comparison = self.evidence()
        comparison["merge_base_commit"]["sha"] = "c" * 40
        self.assertEqual("blocked", self.evaluate(run, jobs, ref, comparison)["status"])

    def test_latest_unfiltered_api_run_never_falls_back_to_old_success(self):
        run, jobs, ref, comparison = self.evidence()
        latest = dict(run, id=41966328999, conclusion="failure")
        older_success = dict(run, id=41966328830)
        requested = []
        def fetch(resource, params):
            requested.append(resource)
            if resource == "actions/workflows/league-live.yml/runs":
                return {"total_count": 2, "workflow_runs": [latest, older_success]}
            if resource == f"actions/runs/{latest['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                return ref
            if resource.startswith("compare/"):
                return comparison
            self.fail("unexpected read " + resource)
        result = audit.audit_latest_league_live_run(
            fetch, "Lolindhir/fantasy-app",
            datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
        )
        self.assertEqual("blocked", result["status"])
        self.assertEqual(latest["id"], result["runId"])
        self.assertNotIn("actions/runs/41966328830/jobs", requested)

    def test_empty_or_unordered_api_and_missing_job_pages_fail_closed(self):
        def empty(resource, params):
            return {"total_count": 0, "workflow_runs": []}
        with self.assertRaisesRegex(audit.AuditError, "unavailable"):
            audit.audit_latest_league_live_run(
                empty, "Lolindhir/fantasy-app",
                datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
            )
        run, jobs, ref, comparison = self.evidence()
        def missing(resource, params):
            if resource == "actions/workflows/league-live.yml/runs":
                return {"total_count": 1, "workflow_runs": [run]}
            if resource.endswith("/jobs"):
                return {"total_count": 4, "jobs": []}
            self.fail("unexpected read " + resource)
        with self.assertRaisesRegex(audit.AuditError, "Incomplete/duplicated jobs"):
            audit.audit_latest_league_live_run(
                missing, "Lolindhir/fantasy-app",
                datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
            )

    def test_latest_run_cli_does_not_change_cost_audit_contract(self):
        run, jobs, ref, comparison = self.evidence()
        def fetch(resource, params):
            if resource == "actions/workflows/league-live.yml/runs":
                return {"total_count": 1, "workflow_runs": [run]}
            if resource == f"actions/runs/{run['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                return ref
            if resource.startswith("compare/"):
                return comparison
            self.fail("unexpected read " + resource)
        with patch.dict("os.environ", {"GH_TOKEN": "synthetic-test-token"}):
            with patch.object(audit, "api_fetch", return_value=fetch):
                with patch("builtins.print") as printed:
                    self.assertEqual(0, audit.main([
                        "--repo", "Lolindhir/fantasy-app",
                        "--audit-latest-league-live",
                    ]))
                self.assertIn('"safeToSkip":false',
                              printed.call_args[0][0])
        self.assertEqual(2, audit.main(["--repo", "Lolindhir/fantasy-app"]))


if __name__ == "__main__":
    unittest.main()
