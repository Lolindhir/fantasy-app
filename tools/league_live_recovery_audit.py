#!/usr/bin/env python3
"""G5 read-only League Live fail-soft/recovery observation (#1263).

A green League job can retain stale TeamWeekPerformance or History products.
This audits producer statuses in the *exact authenticated job log* alongside
the complete GitHub run, without treating the result as recovery or skip proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import audit_workflow_job_costs as github

TIMESTAMPED = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z (.*)$")
LEAGUE = re.compile(r"^[A-Za-z0-9_-]+$")
EXPECTED = frozenset({"league-transactions", "league-drafts", "team-week-performance"})
ALLOWED = frozenset({"changed", "unchanged"})


def parse_derived_refresh(log: str, expected_leagues: set[str]) -> dict[str, Any]:
    """Strictly classify one source-derived refresh report, not output parity.

    No status is inferred from a missing row, a green job, or an absent warning.
    Rebuild/retry ambiguity stays blocked: an earlier attempt's report is not
    evidence that the final attempt re-created all derived products.
    """
    reasons: set[str] = set()
    observed: dict[str, Any] = {
        "status": "blocked", "producerReportsComplete": False,
        "noBlockedDerivedRowsObserved": False, "products": [],
        "reasonCodes": [], "noOpPublisherMessageObserved": False,
        "safeToSkip": False, "enforced": False,
    }
    if (not isinstance(log, str) or not log or not expected_leagues
            or any(not isinstance(v, str) or not LEAGUE.fullmatch(v)
                   for v in expected_leagues)):
        observed["reasonCodes"] = ["missing-log-or-expected-league-scope"]
        return observed
    payloads: list[str] = []
    for line in log.splitlines():
        match = TIMESTAMPED.fullmatch(line)
        if match is None or "\x1b[" in match.group(1):
            continue  # Ignore Actions shell-echo decorations and untrusted code.
        payloads.append(match.group(1))
    starts = [i for i, text in enumerate(payloads)
              if re.fullmatch(r"Rebuild/publish attempt [1-9]\d*/[1-9]\d* for league\.", text)]
    if len(starts) != 1 or payloads[starts[0]] != "Rebuild/publish attempt 1/3 for league.":
        reasons.add("rebuild-retry-or-ambiguous-attempt")
    if len(starts) != 1:
        observed["reasonCodes"] = sorted(reasons)
        return observed
    following = payloads[starts[0]+1:]
    if not following or following[0] != "[":
        reasons.add("missing-derived-refresh-result")
        observed["reasonCodes"] = sorted(reasons)
        return observed
    lines: list[str] = []
    array_end = None
    for i, value in enumerate(following):
        if i > 1000:
            reasons.add("oversized-derived-refresh-report")
            break
        lines.append(value)
        if value == "]":
            array_end = i
            break
    if array_end is None:
        reasons.add("truncated-derived-refresh-report")
        observed["reasonCodes"] = sorted(reasons)
        return observed
    try:
        rows = json.loads("\n".join(lines))
    except (json.JSONDecodeError, ValueError):
        rows = None
    if not isinstance(rows, list) or not rows:
        reasons.add("invalid-derived-refresh-list")
        observed["reasonCodes"] = sorted(reasons)
        return observed
    actual: set[tuple[str, str]] = set()
    products: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            reasons.add("malformed-derived-product")
            continue
        league, product, season, status = (
            row.get("CanonicalLeagueID"), row.get("Product"),
            row.get("Season"), row.get("Status"),
        )
        if (not isinstance(league, str) or league not in expected_leagues
                or not isinstance(product, str) or product not in EXPECTED
                or type(season) is not int or not 2000 <= season <= 2200):
            reasons.add("unexpected-derived-identity-or-season")
            continue
        identity = (league, product)
        if identity in actual:
            reasons.add("duplicate-derived-product")
        actual.add(identity)
        if status not in ALLOWED or type(status) is not str:
            reasons.add("blocked-or-unready-derived-product")
        parity = row.get("PlayerWeekFantasyParity")
        if product == "team-week-performance":
            if (type(row.get("Week")) is not int or row["Week"] < 1
                    or not isinstance(parity, dict)
                    or parity.get("State") != "verified"):
                reasons.add("twp-week-or-parity-not-verified")
        elif parity is not None:
            reasons.add("unexpected-derived-parity-scope")
        products.append({
            "league": league, "product": product, "season": season,
            "status": status if isinstance(status, str) else None,
            "parityState": parity.get("State") if isinstance(parity, dict) else None,
        })
    expected = {(league, product) for league in expected_leagues for product in EXPECTED}
    if actual != expected:
        reasons.add("missing-or-extra-derived-product")
    noops = [i for i, value in enumerate(payloads)
             if value == "Generator produced no repository changes. Nothing to publish."]
    if len(noops) > 1:
        reasons.add("multiple-noop-publisher-markers")
    if len(noops) == 1:
        observed["noOpPublisherMessageObserved"] = True
        if noops[0] <= starts[0] + array_end + 1:
            reasons.add("no-op-publisher-marker-before-derivation")
        if any(product.get("status") == "changed" for product in products):
            reasons.add("changed-derived-product-with-noop-publisher")
    observed.update(
        status="derived-producer-reported-complete" if not reasons else "blocked",
        producerReportsComplete=not reasons,
        noBlockedDerivedRowsObserved=not reasons,
        products=sorted(products, key=lambda v: (v["league"], v["product"])),
        reasonCodes=sorted(reasons),
    )
    return observed


def audit_run(
    fetch: github.Fetcher, get_log: Callable[[int], str],
    repo: str, run_id: int, expected_leagues: set[str], observed_at: datetime,
) -> dict[str, Any]:
    """Correlate latest-attempt League job with one fail-soft observation."""
    result: dict[str, Any] = {
        "schemaVersion": 1, "mode": "offline-league-live-recovery-observation",
        "runId": run_id, "status": "blocked", "reasonCodes": [],
        "jobCompletionVerified": False, "noBlockedDerivedRowsObserved": False,
        "producerReportsComplete": False, "currentMainUnchangedDuringAudit": False,
        "publicationCommitVerified": False, "allOutputsValidated": False,
        "recoveryClean": False, "raceFree": False, "safeToSkip": False,
        "enforced": False,
    }
    try:
        if type(run_id) is not int or run_id <= 0:
            raise github.AuditError("Invalid run ID")
        run = fetch(f"actions/runs/{run_id}", {})
        jobs = github.fetch_jobs(fetch, run_id)
        first = fetch("git/ref/heads/main", {})
        head = (first.get("object") or {}).get("sha")
        if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
            raise github.AuditError("Main SHA missing or invalid")
        cmp = fetch(f"compare/{run.get('head_sha')}...{head}", {})
        completed = github.evaluate_last_league_live_run(
            run, jobs, first, cmp, repo=repo, observed_at=observed_at)
        if not completed["jobCompletionVerified"]:
            raise github.AuditError(
                "Run/job evidence incomplete: " + ",".join(completed["reasonCodes"])
            )
        result["jobCompletionVerified"] = True
        matching = [job for job in jobs if job.get("name") == "league"
                    and job.get("run_attempt") == run.get("run_attempt")]
        if len(matching) != 1 or type(matching[0].get("id")) is not int:
            raise github.AuditError("Latest-attempt League job missing or ambiguous")
        evaluated = parse_derived_refresh(
            get_log(matching[0]["id"]), expected_leagues)
        end = fetch("git/ref/heads/main", {})
        if (end.get("ref") != "refs/heads/main" or
                (end.get("object") or {}).get("sha") != head):
            raise github.AuditError("Main revision advanced during audit")
        result.update(
            observedMainSha=head, expectedLeagueIDs=sorted(expected_leagues),
            currentMainUnchangedDuringAudit=True,
            noBlockedDerivedRowsObserved=evaluated["noBlockedDerivedRowsObserved"],
            producerReportsComplete=evaluated["producerReportsComplete"],
            derivedProductStatuses=evaluated["products"],
            noOpPublisherMessageObserved=evaluated["noOpPublisherMessageObserved"],
            reasonCodes=evaluated["reasonCodes"],
            status=("producer-reported-complete"
                    if evaluated["producerReportsComplete"] else "blocked"),
        )
    except (github.AuditError, ValueError, TypeError, KeyError, AttributeError) as error:
        result["reasonCodes"] = [type(error).__name__ + ": " + str(error)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--league", required=True, action="append",
                        help="Repeat for each expected canonical league ID")
    args = parser.parse_args(argv)
    try:
        if len(args.repo.split("/")) != 2 or not all(
            re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in args.repo.split("/")
        ):
            raise github.AuditError("Invalid owner/repository")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise github.AuditError("Missing read-only GitHub token")
        result = audit_run(
            github.api_fetch(args.repo, token),
            lambda job_id: github.fetch_job_log(args.repo, token, job_id),
            args.repo, args.run_id, set(args.league), datetime.now(timezone.utc))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["producerReportsComplete"] else 2
    except (github.AuditError, ValueError) as error:
        print("G5 recovery observation blocked: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
