#!/usr/bin/env python3
"""Read-only G5 evidence for League Source raw/canonical publication phases (#1263).

One explicitly selected GitHub Actions run; never used by productive workflows.
No log/no-push observation or successful run is a freshness or skip attestation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any, Callable

from tools import audit_workflow_job_costs as github

SHA = re.compile(r"^[0-9a-f]{40}$")
STAMP = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z"
PHASE_MESSAGES = {
    "raw": "refresh Sleeper league raw sources",
    "canonical": "materialize canonical league sources",
}
COMMIT_LINE = re.compile(
    rf"^(?P<time>{STAMP}) \[main (?P<sha>[0-9a-f]{{7,40}})\] "
    r"data\(league-source\): (?P<subject>refresh Sleeper league raw sources|materialize canonical league sources)"
)
PUSH_LINE = re.compile(
    rf"^(?P<time>{STAMP})\s+(?P<old>[0-9a-f]{{7,40}})\.\."
    r"(?P<new>[0-9a-f]{7,40})\s+HEAD -> main\s*$"
)
NOOP_CANONICAL = "No canonical League data-source changes detected."
ROOTS = {
    "raw": ("data-source/providers/sleeper/leagues/", "data-source/leagues/"),
    "canonical": ("data-source/leagues/", "data-source/_sync/"),
}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _ancestry(fetch: github.Fetcher, ancestor: str, target: str) -> bool:
    if not _sha(ancestor) or not _sha(target):
        return False
    compare = fetch(f"compare/{ancestor}...{target}", {})
    if not isinstance(compare, dict) or compare.get("behind_by") != 0 or not (
        isinstance(compare.get("base_commit"), dict)
        and compare["base_commit"].get("sha") == ancestor
        and isinstance(compare.get("merge_base_commit"), dict)
        and compare["merge_base_commit"].get("sha") == ancestor
    ):
        return False
    if compare.get("status") == "identical":
        return ancestor == target and compare.get("ahead_by") == 0
    commits = compare.get("commits")
    return (compare.get("status") == "ahead"
            and type(compare.get("ahead_by")) is int
            and compare["ahead_by"] > 0
            and isinstance(commits, list) and bool(commits)
            and isinstance(commits[-1], dict)
            and commits[-1].get("sha") == target)


def _log_line(line: str) -> str:
    """Remove the Actions timestamp; do not strip ANSI shell-echo sequences."""
    parts = line.split(" ", 1)
    if len(parts) < 2 or not parts[0].endswith("Z"):
        return ""
    return parts[1]


def parse_source_phases(log: str, repo: str) -> dict[str, Any]:
    """Extract exactly attributable push receipts; raw absence is NOT no-op proof."""
    result: dict[str, Any] = {
        "raw": {"state": "no-push-observed", "publicationCommitVerified": False},
        "canonical": {"state": "no-push-observed", "publicationCommitVerified": False},
        "reasonCodes": [],
    }
    if not isinstance(log, str) or not log:
        result["reasonCodes"].append("missing-source-sync-job-log")
        return result
    lines = log.splitlines()
    attempts = [s for s in lines if re.fullmatch(
        rf"{STAMP} League source publish attempt [1-9]\d*/[1-9]\d*", s.strip()
    )]
    if len(attempts) != 1 or not attempts[0].endswith("attempt 1/3"):
        result["reasonCodes"].append("missing-or-retried-source-attempt")
    markers: list[tuple[int, str, str]] = []
    pushes: dict[str, list[dict[str, str]]] = {phase: [] for phase in PHASE_MESSAGES}
    for i, raw in enumerate(lines):
        line = raw.strip()
        m = COMMIT_LINE.fullmatch(line)
        if m:
            phase = next(k for k, value in PHASE_MESSAGES.items()
                         if value == m.group("subject"))
            markers.append((i, phase, m.group("sha")))
        p = PUSH_LINE.fullmatch(line)
        if p:
            # Require real Git remote output, not an echoed shell command.
            nearby = [_log_line(s).strip() for s in lines[max(0, i - 2):i]]
            accepted = {
                f"To https://github.com/{repo}",
                f"To https://github.com/{repo}.git",
            }
            if not any(v in accepted for v in nearby):
                result["reasonCodes"].append("unattributed-source-push")
                continue
            preceding = [v for v in markers if v[0] < i and
                         p.group("new").startswith(v[2][:7]) and
                         v[2].startswith(p.group("new"))]
            # Git abbreviations can be different lengths. Exact mutual prefix
            # is not required, but the shorter must match the longer.
            if not preceding:
                preceding = [v for v in markers if v[0] < i and
                             (v[2].startswith(p.group("new")) or
                              p.group("new").startswith(v[2]))]
            if len(preceding) != 1:
                result["reasonCodes"].append("unmatched-or-ambiguous-commit-marker")
                continue
            _, phase, marker_sha = preceding[0]
            pushes[phase].append({
                "oldPrefix": p.group("old"),
                "newPrefix": p.group("new"),
                "markerPrefix": marker_sha,
                "pushedAtUtc": p.group("time"),
            })
    for phase in PHASE_MESSAGES:
        if len(pushes[phase]) > 1:
            result["reasonCodes"].append("multiple-source-pushes-" + phase)
        elif len(pushes[phase]) == 1:
            result[phase] = {"state": "push-observed",
                             "publicationCommitVerified": False,
                             **pushes[phase][0]}
    canonical_noops = sum(NOOP_CANONICAL in line and "\x1b[" not in line
                          for line in lines)
    if canonical_noops > 1 or (canonical_noops and pushes["canonical"]):
        result["reasonCodes"].append("contradictory-canonical-noop")
    elif canonical_noops == 1 and not pushes["canonical"]:
        result["canonical"] = {"state": "no-op-observed",
                                "publicationCommitVerified": False}
    if len(markers) != sum(len(v) for v in pushes.values()):
        result["reasonCodes"].append("unmatched-or-unpublished-commit-marker")
    return result


def verify_source_commit(
    fetch: github.Fetcher, run: dict[str, Any], job: dict[str, Any],
    receipt: dict[str, Any], phase: str, main_sha: str,
) -> dict[str, Any]:
    """Verify one phase's immutable Git commit on observed main."""
    reasons: list[str] = []
    if receipt.get("state") != "push-observed":
        return {"state": receipt.get("state", "blocked"),
                "publicationCommitVerified": False, "reasonCodes": []}
    commit = fetch(f"commits/{receipt['newPrefix']}", {})
    full_sha = commit.get("sha")
    parents = commit.get("parents")
    details = commit.get("commit")
    if not _sha(full_sha) or not (
        full_sha.startswith(receipt["newPrefix"])
        and (full_sha.startswith(receipt["markerPrefix"]) or
             receipt["markerPrefix"].startswith(full_sha))
    ):
        reasons.append("source-published-sha-mismatch")
    if (not isinstance(parents, list) or len(parents) != 1 or
            not isinstance(parents[0], dict) or
            not _sha(parents[0].get("sha")) or
            not parents[0]["sha"].startswith(receipt["oldPrefix"])):
        reasons.append("source-parent-sha-mismatch")
    if not isinstance(details, dict):
        details = {}
        reasons.append("source-commit-metadata-unavailable")
    author = details.get("author")
    email = author.get("email") if isinstance(author, dict) else None
    if email != "github-actions@github.com" and not (
        isinstance(email, str) and
        re.fullmatch(r"\d+\+github-actions\[bot\]@users\.noreply\.github\.com", email)
    ):
        reasons.append("source-commit-author-mismatch")
    msg = details.get("message")
    if not isinstance(msg, str) or not msg.startswith(
        f"data(league-source): {PHASE_MESSAGES[phase]}"
    ):
        reasons.append("source-commit-phase-mismatch")
    changed = commit.get("files")
    if (not isinstance(changed, list) or not changed or len(changed) >= 300 or
            any(not isinstance(item, dict) or
                    not isinstance(item.get("filename"), str) for item in changed)):
        reasons.append("source-commit-diff-missing-or-truncated")
        changed = []
    if any(not item["filename"].startswith(ROOTS[phase]) for item in changed):
        reasons.append("source-commit-outside-publication-scope")
    try:
        started = github.parse_utc(job.get("started_at"))
        ended = github.parse_utc(job.get("completed_at"))
        committer = details.get("committer")
        committed_at = github.parse_utc(
            committer.get("date") if isinstance(committer, dict) else None
        )
        pushed_at = github.parse_utc(receipt.get("pushedAtUtc"))
        if not started <= committed_at <= pushed_at <= ended:
            reasons.append("source-publish-outside-job-window")
    except (github.AuditError, TypeError, ValueError):
        reasons.append("source-timestamp-evidence-unavailable")
    if not _ancestry(fetch, full_sha, main_sha):
        reasons.append("source-commit-not-on-observed-main")
    return {
        "state": "publication-commit-correlated" if not reasons else "blocked",
        "publicationCommitSha": full_sha,
        "publishedParentSha": parents[0].get("sha") if (
            isinstance(parents, list) and len(parents) == 1 and
            isinstance(parents[0], dict)) else None,
        "changedPaths": sorted(item["filename"] for item in changed),
        "publicationCommitVerified": not reasons,
        "reasonCodes": sorted(set(reasons)),
    }


def audit_source_sync(
    fetch: github.Fetcher, get_log: Callable[[int], str], repo: str,
    run_id: int, now: datetime,
) -> dict[str, Any]:
    """All outputs are offline observations; never a skip/readiness attestation."""
    if type(run_id) is not int or run_id <= 0:
        raise github.AuditError("Invalid source run ID")
    run = fetch(f"actions/runs/{run_id}", {})
    jobs = github.fetch_jobs(fetch, run_id)
    ref = fetch("git/ref/heads/main", {})
    main_sha = (ref.get("object") or {}).get("sha")
    source_path = ".github/workflows/sync-league-source-data.yml"
    is_live = run.get("path") == github.LEAGUE_LIVE_PATH
    correct_job = "source / sync" if is_live else "sync"
    validate_job = "source / validate" if is_live else "validate"
    reasons: list[str] = []
    if (run.get("path") not in {github.LEAGUE_LIVE_PATH, source_path}
            or run.get("head_branch") != "main"
            or run.get("event") not in {"repository_dispatch", "schedule", "workflow_dispatch"}
            or (run.get("repository") or {}).get("full_name") != repo
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or type(run.get("run_attempt")) is not int or run["run_attempt"] <= 0):
        reasons.append("source-run-status-or-identity-unverified")
    if not _sha(main_sha) or not _sha(run.get("head_sha")) or (
        ref.get("ref") != "refs/heads/main"
    ):
        reasons.append("source-main-ref-or-head-unverified")
    elif not _ancestry(fetch, run["head_sha"], main_sha):
        reasons.append("source-run-start-not-on-main")
    try:
        if not (github.parse_utc(run["created_at"])
                <= github.parse_utc(run["updated_at"]) <= now.astimezone(timezone.utc)):
            reasons.append("source-run-time-unverified")
    except (KeyError, github.AuditError, TypeError, ValueError):
        reasons.append("source-run-time-unverified")
    current = [j for j in jobs if j.get("run_attempt") == run.get("run_attempt")]
    named: dict[str, dict[str, Any]] = {}
    for j in current:
        name = j.get("name")
        if not isinstance(name, str) or name in named:
            reasons.append("duplicate-or-malformed-source-job")
            continue
        named[name] = j
        if j.get("run_id") != run_id or j.get("status") != "completed":
            reasons.append("incomplete-or-wrong-source-job")
    for name in (validate_job, correct_job):
        j = named.get(name)
        if not j or j.get("conclusion") != "success" or type(j.get("id")) is not int:
            reasons.append("missing-or-failed-source-" + name.replace(" ", "-"))
        elif name == correct_job:
            try:
                if not (github.parse_utc(run["created_at"])
                        <= github.parse_utc(j["started_at"])
                        <= github.parse_utc(j["completed_at"])
                        <= github.parse_utc(run["updated_at"])):
                    reasons.append("source-job-time-unverified")
            except (KeyError, github.AuditError, TypeError, ValueError):
                reasons.append("source-job-time-unverified")
    if is_live:
        for name in ("standings", "league"):
            if named.get(name, {}).get("conclusion") != "success":
                reasons.append("required-downstream-not-successful")
    base = {"schemaVersion": 1, "mode": "offline-source-two-phase-receipt",
            "runId": run_id, "runAttempt": run.get("run_attempt"),
            "mainAtAudit": main_sha, "jobCompletionVerified": not reasons,
            "sourcePublishChainVerified": False,
            "rawNoOpVerified": False, "canonicalNoOpVerified": False,
            "outputsValidated": False, "timeAndFinalityVerified": False,
            "raceFree": False, "recoveryClean": False,
            "safeToSkip": False, "enforced": False}
    if reasons:
        return {**base, "status": "blocked", "reasonCodes": sorted(set(reasons))}
    parsed = parse_source_phases(get_log(named[correct_job]["id"]), repo)
    phases = {p: parsed[p] for p in PHASE_MESSAGES}
    issues = list(parsed["reasonCodes"])
    if not issues:
        for phase in PHASE_MESSAGES:
            if phases[phase]["state"] == "push-observed":
                phases[phase] = verify_source_commit(
                    fetch, run, named[correct_job], phases[phase], phase, main_sha,
                )
                issues.extend(phases[phase].get("reasonCodes", []))
    if all(phases[p]["publicationCommitVerified"] for p in PHASE_MESSAGES):
        if phases["canonical"]["publishedParentSha"] != phases["raw"]["publicationCommitSha"]:
            issues.append("source-raw-to-canonical-chain-broken")
    else:
        # Neither silence nor a textual "No canonical changes" is a
        # publication/no-op attestation at a revision.
        issues.append("missing-complete-two-phase-publication-chain")
    verified = not issues
    return {**base, "status": (
        "both-publication-commits-correlated" if verified else "partial-or-blocked"
    ), "sourcePublishChainVerified": verified,
        "jobCompletionVerified": True,
        "phases": phases, "reasonCodes": sorted(set(issues))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if len(args.repo.split("/")) != 2 or not all(
            re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in args.repo.split("/")
        ):
            raise github.AuditError("Invalid owner/repository")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise github.AuditError("Missing read-only GitHub token")
        out = audit_source_sync(
            github.api_fetch(args.repo, token),
            lambda job_id: github.fetch_job_log(args.repo, token, job_id),
            args.repo, args.run_id, datetime.now(timezone.utc),
        )
        print(json.dumps(out, sort_keys=True))
        return 0 if out["sourcePublishChainVerified"] else 2
    except (github.AuditError, ValueError, TypeError) as exc:
        print(f"G5 source receipt audit unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
