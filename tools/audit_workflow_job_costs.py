#!/usr/bin/env python3
"""Read-only GitHub Actions run census plus deterministic job-time sampling (#1263 G5).

Usage:
  GH_TOKEN=... python tools/audit_workflow_job_costs.py --repo OWNER/REPO --start 2026-10-27 --end 2026-11-03

End UTC date is exclusive. Samples are job-time proxies, never billed minutes
or proof that a run produced changed content. No workflow/branch mutations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PER_PAGE = 100
MAX_SEARCH_RESULTS = 1000
Fetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


class AuditError(RuntimeError):
    """Fail closed when GitHub evidence is incomplete."""


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AuditError(f"Invalid timestamp: {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditError(f"Invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise AuditError(f"Timestamp lacks UTC offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def seconds_between(start: str, end: str) -> float:
    duration = (parse_utc(end) - parse_utc(start)).total_seconds()
    if duration < 0:
        raise AuditError("Job completed before its start")
    return duration


def api_fetch(repo: str, token: str) -> Fetcher:
    def fetch(resource: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urlencode(params)
        url = f"https://api.github.com/repos/{repo}/{resource}" + (f"?{query}" if query else "")
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fantasy-app-read-only-g5-audit",
        })
        for attempt in range(3):
            try:
                with urlopen(request, timeout=40) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise AuditError(f"Unexpected GitHub response for {resource}")
                return payload
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise AuditError(f"GitHub read failed: HTTP {exc.code} for {resource}") from exc
            except (URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise AuditError(f"GitHub read failed for {resource}: {type(exc).__name__}") from exc
            time.sleep(2 ** attempt)
        raise AuditError(f"Unreachable retry failure for {resource}")
    return fetch


def _range_query(start: datetime, end: datetime) -> str:
    return (start.strftime("%Y-%m-%dT%H:%M:%SZ") + ".." +
            end.strftime("%Y-%m-%dT%H:%M:%SZ"))


def fetch_window(fetch: Fetcher, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Split >1000-run windows recursively; never accept API pagination truncation."""
    if start > end:
        return []
    resource = "actions/runs"
    params = {"created": _range_query(start, end), "per_page": PER_PAGE, "page": 1}
    first = fetch(resource, params)
    count = first.get("total_count")
    if not isinstance(count, int) or count < 0:
        raise AuditError("GitHub run response has no valid total_count")
    if count > MAX_SEARCH_RESULTS:
        midpoint = start + timedelta(seconds=int((end - start).total_seconds()) // 2)
        if midpoint >= end:
            raise AuditError("GitHub result cap reached in a one-second window")
        return (fetch_window(fetch, start, midpoint) +
                fetch_window(fetch, midpoint + timedelta(seconds=1), end))
    result = list(first.get("workflow_runs") or [])
    for page in range(2, (count + PER_PAGE - 1) // PER_PAGE + 1):
        result.extend(fetch(resource, {**params, "page": page}).get("workflow_runs") or [])
    unique: dict[int, dict[str, Any]] = {}
    for run in result:
        if not isinstance(run, dict) or not isinstance(run.get("id"), int):
            raise AuditError("Invalid workflow run in API response")
        if run["id"] in unique:
            raise AuditError(f"Duplicate run: {run['id']}")
        created = parse_utc(run.get("created_at"))
        if not start <= created <= end + timedelta(seconds=0.999999):
            raise AuditError(f"Run {run['id']} outside requested UTC window")
        unique[run["id"]] = run
    if len(unique) != count:
        raise AuditError(f"Incomplete run pages: expected {count}, got {len(unique)}")
    return list(unique.values())


def fetch_runs(fetch: Fetcher, start: date, end: date) -> list[dict[str, Any]]:
    seen: dict[int, dict[str, Any]] = {}
    cursor = start
    while cursor < end:
        a = datetime.combine(cursor, datetime.min.time(), tzinfo=timezone.utc)
        for run in fetch_window(fetch, a, a + timedelta(days=1) - timedelta(seconds=1)):
            if run["id"] in seen:
                raise AuditError(f"Duplicate run between UTC dates: {run['id']}")
            seen[run["id"]] = run
        cursor += timedelta(days=1)
    return list(seen.values())


def sample_evenly(rows: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: (r["created_at"], r["id"]))
    n = len(ordered)
    if n <= size:
        return ordered
    if size == 1:
        return [ordered[n // 2]]
    return [ordered[i * (n - 1) // (size - 1)] for i in range(size)]


def fetch_jobs(fetch: Fetcher, run_id: int) -> list[dict[str, Any]]:
    """All visible job attempts, including paginated rerun jobs."""
    resource = f"actions/runs/{run_id}/jobs"
    params = {"filter": "all", "per_page": PER_PAGE, "page": 1}
    first = fetch(resource, params)
    count = first.get("total_count")
    if not isinstance(count, int) or count < 0:
        raise AuditError(f"Missing job count for run {run_id}")
    rows = list(first.get("jobs") or [])
    for page in range(2, (count + PER_PAGE - 1) // PER_PAGE + 1):
        rows.extend(fetch(resource, {**params, "page": page}).get("jobs") or [])
    if len(rows) != count or len({j.get("id") for j in rows}) != count:
        raise AuditError(f"Incomplete/duplicated jobs for run {run_id}")
    return rows


def job_elapsed(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    seconds = queue = 0.0
    executed = skipped = incomplete = 0
    by_name: dict[str, float] = defaultdict(float)
    for job in jobs:
        if job.get("conclusion") == "skipped":
            skipped += 1
            continue
        if not job.get("started_at") or not job.get("completed_at"):
            incomplete += 1
            continue
        elapsed = seconds_between(job["started_at"], job["completed_at"])
        seconds += elapsed
        executed += 1
        by_name[str(job.get("name") or "unknown")] += elapsed
        if job.get("created_at"):
            queue += seconds_between(job["created_at"], job["started_at"])
    return {
        "runnerSeconds": round(seconds, 3) if incomplete == 0 else None,
        "queueSecondsObserved": round(queue, 3),
        "executedJobs": executed,
        "skippedJobs": skipped,
        "jobsMissingTiming": incomplete,
        "byJobNameSeconds": dict(sorted(by_name.items())),
    }


def summarize(runs: list[dict[str, Any]], fetch: Fetcher, sample_per_stratum: int,
              max_job_requests: int) -> dict[str, Any]:
    strata: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        status = run.get("status") or "unknown"
        conclusion = run.get("conclusion") or f"incomplete:{status}"
        key = (parse_utc(run["created_at"]).date().isoformat(),
               str(run.get("path") or "unknown"), str(run.get("event") or "unknown"),
               str(conclusion))
        strata[key].append(run)
    chosen: list[tuple[tuple[str, str, str, str], dict[str, Any]]] = []
    for key, group in sorted(strata.items()):
        if key[3].startswith("incomplete:"):
            continue
        chosen.extend((key, row) for row in sample_evenly(group, sample_per_stratum))
    if len(chosen) > max_job_requests:
        raise AuditError(f"Would request {len(chosen)} job lists (budget {max_job_requests}); "
                         "reduce days/sampling or explicitly raise limit")
    observations: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for key, run in chosen:
        timing = job_elapsed(fetch_jobs(fetch, run["id"]))
        observations[key].append({"runId": run["id"], "runAttempt": run.get("run_attempt"), **timing})
    records = []
    for key, group in sorted(strata.items()):
        measured = observations.get(key, [])
        valid = [row["runnerSeconds"] for row in measured if row["runnerSeconds"] is not None]
        projection = (round(sum(valid) / len(valid) * len(group), 1)
                      if len(valid) == len(measured) and valid else None)
        records.append({
            "utcDate": key[0], "workflowPath": key[1], "event": key[2],
            "conclusion": key[3], "runCount": len(group),
            "sampledRunCount": len(measured),
            "sampledRunnerSeconds": round(sum(valid), 1),
            "projectedRunnerSeconds": projection,
            "jobEvidence": ("complete" if len(measured) == len(group)
                            else "deterministic-time-spread-sample"),
            "observations": measured,
        })
    return {
        "schemaVersion": 1, "runCount": len(runs), "jobListRequests": len(chosen),
        "method": "exact-run-census-stratified-deterministic-job-sample",
        "limitations": [
            "Projected runner seconds are estimates, not an exact 7/30-day job census.",
            "Runner job duration is not GitHub billed minutes or price.",
            "Time-spread samples are not probabilistic confidence intervals.",
            "No content-change/no-op classification from successful or skipped jobs.",
            "Run status may change after capture; incomplete runs have no projection.",
            "GitHub filter=all retrieves available job attempts; job logs not downloaded.",
        ],
        "noOpEvidence": "not-measured", "billableMinutes": None,
        "strata": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub OWNER/REPO")
    parser.add_argument("--start", required=True, help="UTC date inclusive, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="UTC date exclusive, YYYY-MM-DD")
    parser.add_argument("--sample-per-stratum", type=int, default=3)
    parser.add_argument("--max-job-requests", type=int, default=500)
    args = parser.parse_args(argv)
    try:
        start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        if start >= end or args.sample_per_stratum < 1 or args.max_job_requests < 1:
            raise AuditError("Invalid date window or sampling request")
        if len(args.repo.split("/")) != 2 or any(
            not part or not all(c.isalnum() or c in "-_." for c in part)
            for part in args.repo.split("/")
        ):
            raise AuditError("Repository must be OWNER/REPO")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise AuditError("Set GH_TOKEN or GITHUB_TOKEN (read-only Actions permission)")
        fetch = api_fetch(args.repo, token)
        result = summarize(fetch_runs(fetch, start, end), fetch,
                           args.sample_per_stratum, args.max_job_requests)
        result.update({"repository": args.repo, "startUtcInclusive": args.start,
                       "endUtcExclusive": args.end,
                       "finishedAtUtc": datetime.now(timezone.utc).isoformat()})
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (AuditError, ValueError) as exc:
        print(f"G5 audit incomplete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
