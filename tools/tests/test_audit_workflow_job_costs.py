"""Read-only G5 GitHub Actions job-cost evidence and API pagination regressions."""
from __future__ import annotations

import unittest
import json
from datetime import datetime, timezone
from unittest.mock import patch

from tools import audit_workflow_job_costs as audit
from tools import league_source_receipt_audit as source
from tools import league_current_noop_audit as current
from tools import league_live_recovery_audit as recovery


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
            "created_at": "2026-11-01T04:12:13Z",
            "updated_at": "2026-11-01T04:16:01Z",
        }
        jobs = [
            {
                "id": index, "run_id": latest["id"], "run_attempt": 2,
                "name": name, "status": "completed", "conclusion": "success",
                "started_at": "2026-11-01T04:12:14Z",
                "completed_at": "2026-11-01T04:16:00Z",
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
            "commits": [{"sha": "c" * 40}, {"sha": main}],
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
            ("updated_at", "2026-11-01T04:09:01Z"),
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
            ("completed_at", "2026-11-01T04:10:00Z"),
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
        run, jobs, ref, comparison = self.evidence()
        comparison["commits"][-1]["sha"] = "d" * 40
        self.assertIn("main-not-proven-descendant-of-run-start",
                      self.evaluate(run, jobs, ref, comparison)["reasonCodes"])

    def test_latest_unfiltered_api_run_never_falls_back_to_old_success(self):
        run, jobs, ref, comparison = self.evidence()
        latest = dict(run, id=41966328999, conclusion="failure")
        jobs = [dict(j, run_id=latest["id"]) for j in jobs]
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



class G5PublicationReceiptTests(unittest.TestCase):
    """Never turn one published commit into a whole-pipeline skip proof."""

    def evidence(self):
        run, jobs, ref, run_compare = G5LastLeagueLiveProvenanceTests().evidence()
        scope_job = next(j for j in jobs if j["name"] == "league"
                         and j["run_attempt"] == run["run_attempt"])
        old = "d" * 40
        published = "c" * 40
        log = (
            "2026-11-01T04:15:58.100Z To https://github.com/Lolindhir/fantasy-app\n"
            "2026-11-01T04:15:58.200Z    ddddddd..ccccccc  HEAD -> main\n"
            "2026-11-01T04:15:58.300Z Rebuilt generated-data publish succeeded on attempt 1.\n"
        )
        commit = {
            "sha": published,
            "parents": [{"sha": old}],
            "commit": {
                "message": "data(league): FantasyGameContext, Timestamps",
                "author": {"email": "github-actions@github.com"},
                "committer": {"date": "2026-11-01T04:15:57Z"},
            },
            "files": [{"filename": "public/data/FantasyGameContext.json"},
                      {"filename": "public/data/Timestamps.json"}],
        }
        receipt_compare = {
            "status": "ahead", "behind_by": 0, "ahead_by": 2,
            "base_commit": {"sha": published},
            "merge_base_commit": {"sha": published},
            "commits": [{"sha": "e" * 40}, {"sha": ref["object"]["sha"]}],
        }
        return run, jobs, ref, run_compare, scope_job, log, commit, receipt_compare

    def evaluate(self, changes=None, log=None):
        run, jobs, ref, run_cmp, job, good_log, commit, receipt_cmp = self.evidence()
        if changes is not None:
            changes(run, jobs, ref, run_cmp, job, commit, receipt_cmp)
        fetched = []
        def fetch(resource, params):
            fetched.append(resource)
            if resource == f"actions/runs/{run['id']}":
                return run
            if resource == f"actions/runs/{run['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                return ref
            if resource == f"compare/{run['head_sha']}...{ref['object']['sha']}":
                return run_cmp
            if resource == f"commits/{'c'*7}":
                return commit
            if resource == f"compare/{commit['sha']}...{ref['object']['sha']}":
                return receipt_cmp
            raise AssertionError("unexpected request: " + resource)
        result = audit.audit_publication_receipt(
            fetch, lambda id: log if log is not None else good_log,
            "Lolindhir/fantasy-app", run["id"], "league",
            datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
        )
        return result, fetched

    def test_realistic_authenticated_push_binds_immutable_commit(self):
        result, fetched = self.evaluate()
        self.assertEqual("publication-commit-correlated", result["status"])
        self.assertTrue(result["publicationCommitVerified"])
        self.assertTrue(result["jobCompletionVerified"])
        self.assertEqual("c" * 40, result["publicationCommitSha"])
        self.assertEqual(["public/data/FantasyGameContext.json",
                          "public/data/Timestamps.json"], result["changedPaths"])
        self.assertIn("commits/ccccccc", fetched)
        for name in ("outputsValidated", "timeAndFinalityVerified", "raceFree",
                     "recoveryClean", "safeToSkip", "enforced"):
            self.assertIs(result[name], False, name)

    def test_noop_is_not_a_publication_receipt(self):
        result, fetched = self.evaluate(log=(
            "2026-11-01T04:15:58Z Generator produced no repository changes. Nothing to publish.\n"
        ))
        self.assertEqual("no-op-observed", result["status"])
        self.assertFalse(result["publicationCommitVerified"])
        self.assertFalse(result["safeToSkip"])
        self.assertNotIn("commits/ccccccc", fetched)

    def test_unattributed_or_ambiguous_push_fails_closed(self):
        _, _, _, _, _, log, _, _ = self.evidence()
        for bad in (
            log.replace("Rebuilt generated-data publish succeeded", "Unverified push"),
            log.replace("To https://github.com/Lolindhir/fantasy-app",
                        "To https://github.com/another/repository"),
            log + log,
            "2026-11-01T04:15:58Z  ddddddd..ccccccc  HEAD -> feature\n",
        ):
            with self.subTest(log=bad[:70]):
                result, _ = self.evaluate(log=bad)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["publicationCommitVerified"])

    def test_wrong_commit_parent_author_scope_paths_and_clock_fail_closed(self):
        cases = (
            lambda r, j, ref, c, job, commit, pc:
                commit["parents"].__setitem__(0, {"sha": "f" * 40}),
            lambda r, j, ref, c, job, commit, pc:
                commit["commit"]["author"].__setitem__("email", "other@example.com"),
            lambda r, j, ref, c, job, commit, pc:
                commit["commit"].__setitem__("message", "data(players): unrelated"),
            lambda r, j, ref, c, job, commit, pc:
                commit["files"].append({"filename": "data-meta/nfl-reise/metadata.json"}),
            lambda r, j, ref, c, job, commit, pc:
                commit["commit"]["committer"].__setitem__("date", "2026-11-01T04:10:00Z"),
            lambda r, j, ref, c, job, commit, pc:
                pc.__setitem__("status", "diverged"),
            lambda r, j, ref, c, job, commit, pc:
                pc["commits"][-1].__setitem__("sha", "f" * 40),
        )
        for i, mutate in enumerate(cases):
            with self.subTest(case=i):
                result, _ = self.evaluate(changes=mutate)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["publicationCommitVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_incomplete_or_failed_run_never_reads_writer_log(self):
        for outcome in ("failure", "cancelled", None):
            with self.subTest(outcome=outcome):
                def change(run, jobs, ref, cmp, job, commit, pc):
                    run["conclusion"] = outcome
                result, fetched = self.evaluate(changes=change)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["jobCompletionVerified"])
                self.assertNotIn("commits/ccccccc", fetched)

    def test_evidence_timestamp_must_be_within_exact_job(self):
        run, jobs, ref, cmp, job, log, commit, pc = self.evidence()
        bad = log.replace("04:15:58", "04:18:58")
        result, _ = self.evaluate(log=bad)
        self.assertEqual("blocked", result["status"])
        self.assertIn("commit-time-outside-job", result["reasonCodes"])

    def test_authorization_stripped_on_log_storage_redirect(self):
        from urllib.request import Request
        request = Request("https://api.github.com/repos/owner/repo/actions/jobs/1/logs",
                          headers={"Authorization": "Bearer sensitive-token"})
        redirected = audit.NoCredentialRedirect().redirect_request(
            request, None, 302, "Found", {}, "https://storage.example.net/signed/log",
        )
        self.assertFalse(redirected.has_header("Authorization"))
        with self.assertRaises(audit.AuditError):
            audit.NoCredentialRedirect().redirect_request(
                request, None, 302, "Found", {}, "http://storage.example.net/log",
            )



class G5SourceSyncTwoPhaseReceiptTests(unittest.TestCase):
    """Actual raw->canonical commits versus unverified no-push observations."""

    def fixture(self):
        repo = "Lolindhir/fantasy-app"
        started = "4454dcf30a3ba0315b5d3c7fb1526eab4405bc72"
        rawsha = "8c8bb7159399170d4ae187b6923439a8f7d0daf9"
        canonsha = "3fc5691db879604c02ba0ff663d794abf771278c"
        main = "f92184a87bd77202ea21b5945c4c8663f117eb5f"
        run = {
            "id": 41962202248, "run_attempt": 1, "path": source_path(),
            "head_branch": "main", "head_sha": started,
            "repository": {"full_name": repo}, "event": "repository_dispatch",
            "status": "completed", "conclusion": "success",
            "created_at": "2026-11-05T03:32:10Z",
            "updated_at": "2026-11-05T03:37:26Z",
        }
        jobs = [
            {
                "id": 11 + index, "run_id": run["id"], "run_attempt": 1,
                "name": name, "status": "completed", "conclusion": "success",
                "started_at": "2026-11-05T03:33:00Z" if name == "validate"
                              else "2026-11-05T03:37:00Z",
                "completed_at": "2026-11-05T03:34:00Z" if name == "validate"
                                else "2026-11-05T03:37:24Z",
            }
            for index, name in enumerate(("validate", "sync"))
        ]
        jobs.append(dict(jobs[0], id=20, name="validate_current_sparse_pr",
                         conclusion="skipped"))
        commits = {
            rawsha: {
                "sha": rawsha, "parents": [{"sha": started}],
                "commit": {
                    "message": "data(league-source): refresh Sleeper league raw sources • 2026-11-05 04:37 CET",
                    "author": {"email": "41898282+github-actions[bot]@users.noreply.github.com"},
                    "committer": {"date": "2026-11-05T03:37:14Z"},
                },
                "files": [{"filename": "data-source/providers/sleeper/leagues/abc/matchups/week-10.json"}],
            },
            canonsha: {
                "sha": canonsha, "parents": [{"sha": rawsha}],
                "commit": {
                    "message": "data(league-source): materialize canonical league sources • 2026-11-05 04:37 CET",
                    "author": {"email": "41898282+github-actions[bot]@users.noreply.github.com"},
                    "committer": {"date": "2026-11-05T03:37:20Z"},
                },
                "files": [{"filename": "data-source/leagues/nfl-reise/seasons/2026/matchups/week-10.json"},
                          {"filename": "data-source/_sync/league-refresh-witnesses/nfl-reise/2026-week-08.json"}],
            },
        }
        log = "\n".join([
            "2026-11-05T03:37:05.6169881Z League source publish attempt 1/3",
            "2026-11-05T03:37:14.3826880Z [main 8c8bb71] data(league-source): refresh Sleeper league raw sources • 2026-11-05 04:37 CET",
            "2026-11-05T03:37:15.9968153Z To https://github.com/Lolindhir/fantasy-app.git",
            "2026-11-05T03:37:15.9968546Z    4454dcf..8c8bb71  HEAD -> main",
            "2026-11-05T03:37:20.9879663Z [main 3fc5691] data(league-source): materialize canonical league sources • 2026-11-05 04:37 CET",
            "2026-11-05T03:37:22.7382133Z To https://github.com/Lolindhir/fantasy-app.git",
            "2026-11-05T03:37:22.7382505Z    8c8bb71..3fc5691  HEAD -> main",
            "2026-11-05T03:37:22.7441209Z League data-source publish succeeded.",
        ])
        return run, jobs, main, commits, log

    def evaluate(self, modify=None):
        run, jobs, main, commits, log = self.fixture()
        if modify:
            run, jobs, main, commits, log = modify(run, jobs, main, commits, log)
        fetched: list[str] = []
        def fetch(resource, params):
            fetched.append(resource)
            if resource == f"actions/runs/{run['id']}":
                return run
            if resource == f"actions/runs/{run['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                return {"ref": "refs/heads/main", "object": {"sha": main}}
            if resource.startswith("commits/"):
                prefix = resource.split("/", 1)[1]
                return next(value for sha, value in commits.items() if sha.startswith(prefix))
            if resource.startswith("compare/"):
                begin, end = resource.split("/", 1)[1].split("...")
                return {"status": "ahead", "behind_by": 0, "ahead_by": 3,
                        "base_commit": {"sha": begin},
                        "merge_base_commit": {"sha": begin},
                        "commits": [{"sha": "b" * 40}, {"sha": end}]}
            self.fail("unexpected API endpoint: " + resource)
        result = source.audit_source_sync(
            fetch, lambda job_id: log, "Lolindhir/fantasy-app", run["id"],
            datetime(2026, 11, 5, 5, 10, tzinfo=timezone.utc),
        )
        return result, fetched

    def test_real_full_sync_correlates_raw_and_canonical_chain(self):
        result, fetched = self.evaluate()
        self.assertEqual("both-publication-commits-correlated", result["status"])
        self.assertTrue(result["sourcePublishChainVerified"])
        self.assertTrue(result["jobCompletionVerified"])
        self.assertEqual(
            "8c8bb7159399170d4ae187b6923439a8f7d0daf9",
            result["phases"]["canonical"]["publishedParentSha"],
        )
        for flag in ("rawNoOpVerified", "canonicalNoOpVerified", "safeToSkip",
                     "enforced", "timeAndFinalityVerified", "raceFree", "recoveryClean",
                     "outputsValidated"):
            self.assertFalse(result[flag], flag)
        self.assertIn("commits/8c8bb71", fetched)
        self.assertIn("commits/3fc5691", fetched)

    def test_no_push_observation_does_not_prove_raw_or_canonical_noop(self):
        def change(run, jobs, main, commits, log):
            log = ("2026-11-05T03:37:05Z League source publish attempt 1/3\n"
                   "2026-11-05T03:37:20Z No canonical League data-source changes detected.")
            return run, jobs, main, commits, log
        result, fetched = self.evaluate(change)
        self.assertFalse(result["sourcePublishChainVerified"])
        self.assertEqual("no-push-observed", result["phases"]["raw"]["state"])
        self.assertEqual("no-op-observed", result["phases"]["canonical"]["state"])
        self.assertFalse(result["rawNoOpVerified"])
        self.assertFalse(result["canonicalNoOpVerified"])
        self.assertFalse(result["safeToSkip"])
        self.assertFalse(any(p.startswith("commits/") for p in fetched))

    def test_raw_push_with_canonical_noop_only_proves_raw_commit(self):
        def change(run, jobs, main, commits, log):
            log = "\n".join(log.splitlines()[:4] + [
                "2026-11-05T03:37:22Z No canonical League data-source changes detected."
            ])
            return run, jobs, main, commits, log
        result, fetched = self.evaluate(change)
        self.assertTrue(result["phases"]["raw"]["publicationCommitVerified"])
        self.assertEqual("no-op-observed", result["phases"]["canonical"]["state"])
        self.assertFalse(result["sourcePublishChainVerified"])
        self.assertFalse(result["safeToSkip"])

    def test_missing_or_wrong_push_log_or_duplicate_marker_fails_closed(self):
        edits = (
            lambda s: s.replace("To https://github.com/Lolindhir/fantasy-app.git",
                                "To https://github.com/wrong/repo.git"),
            lambda s: s + "\n" + "\n".join(s.splitlines()[4:]),
            lambda s: s.replace("8c8bb71..3fc5691  HEAD -> main",
                                "8c8bb71..3fc5691  HEAD -> other"),
            lambda s: s.replace("League source publish attempt 1/3",
                                "League source publish attempt 2/3"),
            lambda s: s.replace("[main 3fc5691]", "[main fffffff]"),
        )
        for edit in edits:
            with self.subTest(edit=str(edit)):
                def change(run, jobs, main, commits, log):
                    return run, jobs, main, commits, edit(log)
                result, _ = self.evaluate(change)
                self.assertFalse(result["sourcePublishChainVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_commit_mismatches_and_out_of_scope_files_block(self):
        modifiers = (
            lambda commits: commits["3fc5691db879604c02ba0ff663d794abf771278c"]["parents"].__setitem__(0, {"sha": "f" * 40}),
            lambda commits: commits["3fc5691db879604c02ba0ff663d794abf771278c"]["files"].append({"filename": "data-meta/nfl-reise/metadata.json"}),
            lambda commits: commits["8c8bb7159399170d4ae187b6923439a8f7d0daf9"]["commit"].__setitem__("message", "data(league-source): wrong scope"),
            lambda commits: commits["8c8bb7159399170d4ae187b6923439a8f7d0daf9"]["commit"]["committer"].__setitem__("date", "2026-11-05T03:50:00Z"),
        )
        for modify in modifiers:
            with self.subTest(case=str(modify)):
                def change(run, jobs, main, commits, log):
                    modify(commits)
                    return run, jobs, main, commits, log
                result, _ = self.evaluate(change)
                self.assertFalse(result["sourcePublishChainVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_failed_run_or_missing_sync_job_never_claims_chain(self):
        for mode in ("failed", "missing", "other-repo", "incomplete"):
            with self.subTest(mode=mode):
                def change(run, jobs, main, commits, log):
                    if mode == "failed":
                        run["conclusion"] = "failure"
                    elif mode == "missing":
                        jobs[:] = [job for job in jobs if job["name"] != "sync"]
                    elif mode == "other-repo":
                        run["repository"]["full_name"] = "other/repository"
                    else:
                        jobs[1]["conclusion"] = "skipped"
                    return run, jobs, main, commits, log
                result, fetched = self.evaluate(change)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["jobCompletionVerified"])
                self.assertFalse(any(p.startswith("commits/") for p in fetched))

    def test_existing_league_live_job_name_is_supported_without_new_writer(self):
        def change(run, jobs, main, commits, log):
            run["path"] = audit.LEAGUE_LIVE_PATH
            jobs[0]["name"] = "source / validate"
            jobs[1]["name"] = "source / sync"
            jobs += [dict(jobs[0], id=90, name="standings"),
                     dict(jobs[0], id=91, name="league")]
            return run, jobs, main, commits, log
        result, _ = self.evaluate(change)
        self.assertTrue(result["sourcePublishChainVerified"])
        self.assertFalse(result["enforced"])

    def test_cli_without_token_fails_without_network_or_dispatch(self):
        with patch.dict("os.environ", {"GH_TOKEN": "", "GITHUB_TOKEN": ""}):
            self.assertEqual(2, source.main([
                "--repo", "Lolindhir/fantasy-app", "--run-id", "41962202248",
            ]))




class G5CurrentScopeNoOpRevisionTests(unittest.TestCase):
    """Job-reported zero changes at a Git tree, never source freshness or skip."""

    def fixture(self):
        run, jobs, main, _commits, _old_log = G5SourceSyncTwoPhaseReceiptTests().fixture()
        raw = {
            "Leagues": [{
                "CanonicalLeagueID": "nfl-reise", "Scope": "current",
                "AcquisitionScope": "current",
                "Dependencies": ["sleeper.league", "sleeper.matchups"],
                "Parts": ["league-core", "transactions", "drafts"],
                "DatasetPartitions": 16, "RawFilesChanged": 0,
                "MetadataFilesChanged": 0,
                "CurrentProviderLeagueID": "1354177383984267264",
                "CurrentLeagueCoreScope": {
                    "Season": 2026, "ProviderLeagueID": "1354177383984267264",
                    "CurrentMatchupWeek": 9,
                },
                "CurrentTransactionWindow": {
                    "CanonicalLeagueID": "nfl-reise", "Season": 2026,
                    "CurrentWeek": 9, "Weeks": [8, 9],
                },
                "CurrentDraftScope": {
                    "Season": 2026, "ProviderLeagueID": "1354177383984267264",
                },
            }]
        }
        row = raw["Leagues"][0]
        canonical = {
            "Leagues": [{
                "CanonicalLeagueID": row["CanonicalLeagueID"],
                "Scope": "current", "MaterializationScope": "current",
                "Dependencies": ["raw-sleeper-league", "raw-sleeper-matchups"],
                "Parts": list(row["Parts"]), "CanonicalFiles": 9,
                "CanonicalFilesChanged": 0,
                "CurrentLeagueCoreScope": dict(row["CurrentLeagueCoreScope"]),
                "CurrentTransactionWindow": dict(row["CurrentTransactionWindow"]),
                "CurrentDraftScope": dict(row["CurrentDraftScope"]),
            }]
        }
        return run, jobs, main, raw, canonical

    def log(self, run, raw, canonical):
        def block(data):
            return "\n".join(
                "2026-11-05T03:37:15Z " + line
                for line in json.dumps(data, indent=2).splitlines()
            )
        return "\n".join([
            "2026-11-05T03:37:05Z League source publish attempt 1/3",
            "2026-11-05T03:37:10Z HEAD is now at 4454dcf before-source",
            block(raw),
            "2026-11-05T03:37:16Z HEAD is now at 4454dcf before-materialize",
            block(canonical),
            block(canonical),
            "2026-11-05T03:37:23Z No canonical League data-source changes detected.",
        ])

    def evaluate(self, change=None, *, main_tree_changed=False, main_moves=False):
        run, jobs, main, raw, canonical = self.fixture()
        log = self.log(run, raw, canonical)
        if change:
            run, jobs, main, log = change(run, jobs, main, log)
        start_sha = run["head_sha"]
        fetched = []
        ref_reads = 0
        roots = list(current.INPUT_ROOTS)
        root_shas = {name: f"{index+1:x}"*40 for index, name in enumerate(roots)}
        def fetch(resource, params):
            nonlocal ref_reads
            fetched.append(resource)
            if resource == f"actions/runs/{run['id']}":
                return run
            if resource == f"actions/runs/{run['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                ref_reads += 1
                return {"ref": "refs/heads/main", "object": {
                    "sha": ("f"*40 if main_moves and ref_reads > 1 else main)
                }}
            if resource.startswith("compare/"):
                a, b = resource[len("compare/"):].split("...")
                if a == b:
                    return {"status": "identical", "behind_by": 0, "ahead_by": 0,
                            "base_commit": {"sha": a},
                            "merge_base_commit": {"sha": a}}
                return {"status": "ahead", "behind_by": 0, "ahead_by": 1,
                        "base_commit": {"sha": a},
                        "merge_base_commit": {"sha": a},
                        "commits": [{"sha": b}]}
            if resource.startswith("commits/"):
                prefix = resource[len("commits/"):]
                if start_sha.startswith(prefix):
                    sha, tree = start_sha, "a"*40
                elif main.startswith(prefix):
                    sha, tree = main, "b"*40
                else:
                    self.fail("unexpected commit " + resource)
                return {"sha": sha, "commit": {"tree": {"sha": tree}}}
            if resource.startswith("git/trees/"):
                sha = resource[len("git/trees/"):]
                if sha not in {"a"*40, "b"*40}:
                    self.fail("unexpected tree " + resource)
                is_main = sha == "b"*40
                return {"sha": sha, "truncated": False,
                        "tree": [
                            {"path": name, "type": "tree",
                             "sha": ("d"*40 if main_tree_changed and is_main
                                     and name == "data-source" else root_shas[name])}
                            for name in roots
                        ]}
            self.fail("unexpected endpoint " + resource)
        result = current.audit_current_scope_noop(
            fetch, lambda _job: log, "Lolindhir/fantasy-app", run["id"],
            datetime(2026, 11, 5, 5, 10, tzinfo=timezone.utc),
        )
        return result, fetched

    def test_actual_current_scope_zero_counts_bind_to_revision_only(self):
        result, fetched = self.evaluate()
        self.assertEqual("run-revision-noop-reported", result["status"])
        self.assertTrue(result["jobCompletionVerified"])
        self.assertTrue(result["reportedNoOpAtSourceRevisionVerified"])
        self.assertTrue(result["currentMainInputTreesUnchanged"])
        self.assertEqual(["nfl-reise"], result["canonicalLeagueIDs"])
        self.assertEqual(16, result["rawPartitionsChecked"])
        self.assertEqual(9, result["canonicalFilesChecked"])
        self.assertEqual([], result["reasonCodes"])
        self.assertIn("git/trees/" + "a"*40, fetched)
        for flag in ("independentProviderFreshnessVerified",
                     "independentCanonicalReplayVerified",
                     "allSourceDerivedAppOutputsValidated",
                     "timeAndFinalityVerified", "raceFree", "recoveryClean",
                     "safeToSkip", "enforced"):
            self.assertIs(result[flag], False, flag)

    def test_new_main_source_tree_invalidates_current_reuse_not_history(self):
        result, _ = self.evaluate(main_tree_changed=True)
        self.assertTrue(result["reportedNoOpAtSourceRevisionVerified"])
        self.assertFalse(result["currentMainInputTreesUnchanged"])
        self.assertFalse(result["safeToSkip"])

    def test_raw_or_canonical_changes_and_second_pass_drift_block(self):
        for data, field, bad in (
            ("raw", "RawFilesChanged", 1),
            ("raw", "MetadataFilesChanged", 1),
            ("raw", "DatasetPartitions", 0),
            ("canonical", "CanonicalFilesChanged", 2),
            ("canonical", "CanonicalFiles", 0),
            ("canonical", "MaterializationScope", "full"),
        ):
            with self.subTest(data=data, field=field):
                run, jobs, main, raw, canonical = self.fixture()
                (raw if data == "raw" else canonical)["Leagues"][0][field] = bad
                def altered(r, j, m, _):
                    return r, j, m, self.log(r, raw, canonical)
                result, _ = self.evaluate(altered)
                self.assertFalse(result["reportedNoOpAtSourceRevisionVerified"])
                self.assertFalse(result["safeToSkip"])
        def altered_second(r, j, m, log):
            return r, j, m, log.replace(
                '"CanonicalFiles": 9', '"CanonicalFiles": 8', 1
            )
        result, _ = self.evaluate(altered_second)
        self.assertFalse(result["reportedNoOpAtSourceRevisionVerified"])

    def test_retry_reset_race_missing_result_push_and_marker_block(self):
        edits = [
            lambda s: s.replace("attempt 1/3", "attempt 2/3"),
            lambda s: s.replace("HEAD is now at 4454dcf before-materialize",
                                "HEAD is now at 8888888 before-materialize"),
            lambda s: s.replace('"Leagues":', '"WrongKey":', 1),
            lambda s: s.replace("No canonical League data-source changes detected.",
                                "Canonical change was published."),
            lambda s: s + "\n2026-11-05T03:37:23Z    4454dcf..bbbbbbb HEAD -> main",
            lambda s: s.replace("No canonical League data-source changes detected.",
                                "No canonical League data-source changes detected.\n"
                                "2026-11-05T03:37:24Z No canonical League data-source changes detected."),
        ]
        for edit in edits:
            with self.subTest(name=str(edit)):
                def altered(run, jobs, main, log):
                    return run, jobs, main, edit(log)
                result, _ = self.evaluate(altered)
                self.assertFalse(result["reportedNoOpAtSourceRevisionVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_run_failure_missing_validation_or_incomplete_source_blocks(self):
        for mode in ("run", "validate", "source"):
            with self.subTest(mode=mode):
                def altered(run, jobs, main, log):
                    if mode == "run":
                        run["conclusion"] = "failure"
                    elif mode == "validate":
                        jobs[:] = [x for x in jobs if x["name"] != "validate"]
                    else:
                        next(x for x in jobs if x["name"] == "sync")["status"] = "in_progress"
                    return run, jobs, main, log
                result, _ = self.evaluate(altered)
                self.assertFalse(result["reportedNoOpAtSourceRevisionVerified"])
                self.assertFalse(result["safeToSkip"])

    def test_main_moves_during_audit_denies_revision_proof(self):
        result, _ = self.evaluate(main_moves=True)
        self.assertEqual("blocked", result["status"])
        self.assertIn("Main advanced during audit", result["reasonCodes"][0])
        self.assertFalse(result["safeToSkip"])

    def test_cli_missing_token_never_fetches_or_dispatches(self):
        with patch.dict("os.environ", {"GH_TOKEN": "", "GITHUB_TOKEN": ""}):
            self.assertEqual(2, current.main([
                "--repo", "Lolindhir/fantasy-app", "--run-id", "42088460708",
            ]))




class G5LeagueLiveRecoveryObservationTests(unittest.TestCase):
    """Derived fail-soft observation never elevates a green job to skip proof."""

    def rows(self):
        return [
            {"CanonicalLeagueID": "nfl-reise", "Season": 2026,
             "Product": "league-transactions", "Status": "unchanged"},
            {"CanonicalLeagueID": "nfl-reise", "Season": 2026,
             "Product": "league-drafts", "Status": "unchanged"},
            {"CanonicalLeagueID": "nfl-reise", "Season": 2026,
             "Product": "team-week-performance", "Status": "unchanged",
             "Week": 8, "PlayerWeekFantasyParity": {
                 "State": "verified", "Compared": 177}},
        ]

    def log(self, rows=None, *, attempt="1/3", no_op=True):
        body = json.dumps(self.rows() if rows is None else rows,
                          indent=2, sort_keys=True)
        lines = [
            f"2026-11-01T04:15:58Z Rebuild/publish attempt {attempt} for league.",
        ]
        lines += ["2026-11-01T04:15:58Z " + line for line in body.splitlines()]
        if no_op:
            lines.append("2026-11-01T04:15:59Z Generator produced no repository changes. Nothing to publish.")
        return "\n".join(lines)

    def test_valid_reports_still_never_prove_recovery_race_or_skip(self):
        evidence = recovery.parse_derived_refresh(self.log(), {"nfl-reise"})
        self.assertEqual("derived-producer-reported-complete", evidence["status"])
        self.assertTrue(evidence["noBlockedDerivedRowsObserved"])
        self.assertEqual(3, len(evidence["products"]))
        self.assertTrue(evidence["noOpPublisherMessageObserved"])
        self.assertFalse(evidence["safeToSkip"])
        self.assertFalse(evidence["enforced"])

    def test_blocked_twp_and_history_are_not_masked_by_green_noop(self):
        for product, state in (("team-week-performance", "blocked"),
                               ("team-week-performance", "no-scored-week"),
                               ("league-drafts", "blocked"),
                               ("league-transactions", "blocked")):
            with self.subTest(product=product, state=state):
                rows = self.rows()
                next(r for r in rows if r["Product"] == product)["Status"] = state
                report = recovery.parse_derived_refresh(self.log(rows), {"nfl-reise"})
                self.assertEqual("blocked", report["status"])
                self.assertFalse(report["noBlockedDerivedRowsObserved"])
                self.assertIn("blocked-or-unready-derived-product", report["reasonCodes"])

    def test_twp_parity_missing_or_nonverified_blocks(self):
        for parity in (None, {}, {"State": "blocked"},
                       {"State": "accepted-divergence"}):
            with self.subTest(parity=parity):
                rows = self.rows()
                rows[-1]["PlayerWeekFantasyParity"] = parity
                report = recovery.parse_derived_refresh(self.log(rows), {"nfl-reise"})
                self.assertIn("twp-week-or-parity-not-verified", report["reasonCodes"])
                self.assertFalse(report["safeToSkip"])

    def test_missing_duplicate_extra_malformed_or_unhashable_rows_block(self):
        cases = [
            self.rows()[:2],
            self.rows() + [self.rows()[0]],
            self.rows() + [{"CanonicalLeagueID": "other", "Season": 2026,
                            "Product": "league-drafts", "Status": "unchanged"}],
            self.rows() + ["not-a-product"],
        ]
        invalid = self.rows()
        invalid[1]["Status"] = []
        cases.append(invalid)
        for rows in cases:
            with self.subTest(rows=str(rows)[:90]):
                report = recovery.parse_derived_refresh(self.log(rows), {"nfl-reise"})
                self.assertEqual("blocked", report["status"])
                self.assertFalse(report["safeToSkip"])

    def test_retry_truncation_shell_echo_and_noop_contradictions_block(self):
        cases = [
            self.log(attempt="2/3"),
            self.log() + "\n2026-11-01T04:16:00Z Rebuild/publish attempt 2/3 for league.",
            self.log().replace("2026-11-01T04:15:58Z ]", ""),
            self.log().replace('"Status": "unchanged"', '"Status": "changed"', 1),
            self.log().replace("Generator produced no repository changes. Nothing to publish.",
                               "Generator produced no repository changes. Nothing to publish.\n"
                               "2026-11-01T04:16:00Z Generator produced no repository changes. Nothing to publish."),
            "2026-11-01T04:15:58Z \x1b[36;1mRebuild/publish attempt 1/3 for league.\x1b[0m",
        ]
        for payload in cases:
            with self.subTest(log=payload[:95]):
                report = recovery.parse_derived_refresh(payload, {"nfl-reise"})
                self.assertEqual("blocked", report["status"])
                self.assertFalse(report["safeToSkip"])

    def audit(self, mutate=None):
        run, jobs, ref, compare = G5LastLeagueLiveProvenanceTests().evidence()
        payload = self.log()
        if mutate:
            run, jobs, ref, compare, payload = mutate(run, jobs, ref, compare, payload)
        reads = []
        def fetch(resource, params):
            reads.append(resource)
            if resource == f"actions/runs/{run['id']}":
                return run
            if resource == f"actions/runs/{run['id']}/jobs":
                return {"total_count": len(jobs), "jobs": jobs}
            if resource == "git/ref/heads/main":
                return ref
            if resource.startswith("compare/"):
                return compare
            self.fail("unexpected read " + resource)
        log_calls = []
        def job_log(job_id):
            log_calls.append(job_id)
            return payload
        result = recovery.audit_run(
            fetch, job_log, "Lolindhir/fantasy-app", run["id"], {"nfl-reise"},
            datetime(2026, 11, 5, 4, 19, tzinfo=timezone.utc),
        )
        return result, reads, log_calls

    def test_authenticated_run_completion_and_derived_report_are_separate(self):
        r, reads, log_calls = self.audit()
        self.assertEqual("producer-reported-complete", r["status"])
        self.assertTrue(r["jobCompletionVerified"])
        self.assertTrue(r["currentMainUnchangedDuringAudit"])
        self.assertTrue(r["noBlockedDerivedRowsObserved"])
        self.assertEqual(2, reads.count("git/ref/heads/main"))
        self.assertEqual(1, len(log_calls))
        for key in ("publicationCommitVerified", "allOutputsValidated",
                    "recoveryClean", "raceFree", "safeToSkip", "enforced"):
            self.assertIs(r[key], False, key)

    def test_failed_or_in_progress_workflow_never_inspects_derived_log(self):
        for status, conclusion in (("completed", "failure"),
                                   ("in_progress", None)):
            with self.subTest(status=status):
                def altered(run, jobs, ref, cmp, log):
                    run["status"] = status
                    run["conclusion"] = conclusion
                    return run, jobs, ref, cmp, log
                result, _, log_calls = self.audit(altered)
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["jobCompletionVerified"])
                self.assertEqual([], log_calls)

    def test_moving_ref_and_missing_or_skipped_league_job_fail_closed(self):
        def moved(run, jobs, ref, cmp, log):
            class MovingRef(dict):
                def __init__(self, before):
                    super().__init__(before)
                    self.reads = 0
                def get(self, key, default=None):
                    if key == "object":
                        self.reads += 1
                        return ({"sha": "f"*40} if self.reads > 1
                                else super().get(key, default))
                    return super().get(key, default)
            return run, jobs, MovingRef(ref), cmp, log
        result, _, _ = self.audit(moved)
        self.assertEqual("blocked", result["status"])
        self.assertIn("Main revision advanced during audit", result["reasonCodes"][0])
        def skipped(run, jobs, ref, cmp, log):
            for job in jobs:
                if job["name"] == "league" and job["run_attempt"] == run["run_attempt"]:
                    job["conclusion"] = "skipped"
            return run, jobs, ref, cmp, log
        result, _, no_log = self.audit(skipped)
        self.assertEqual("blocked", result["status"])
        self.assertEqual([], no_log)

    def test_cli_missing_token_is_read_only_fail_closed(self):
        with patch.dict("os.environ", {"GH_TOKEN": "", "GITHUB_TOKEN": ""}):
            self.assertEqual(2, recovery.main([
                "--repo", "Lolindhir/fantasy-app",
                "--run-id", "42094886471", "--league", "nfl-reise",
            ]))

def source_path():
    return ".github/workflows/sync-league-source-data.yml"


if __name__ == "__main__":
    unittest.main()
