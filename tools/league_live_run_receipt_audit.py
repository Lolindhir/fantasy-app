#!/usr/bin/env python3
"""Correlate one real League Live run's existing read-only G5 receipts (#1263).

This does NOT create a receipt, call producers, write repository data, or skip jobs.
A no-op has no new published SHA, so neither an old output nor a job success can
be promoted to a revision-bound complete publication attestation.
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
from tools import league_source_receipt_audit as source
from tools import league_live_recovery_audit as recovery
from tools import league_live_output_revision_audit as outputs

SHA = re.compile(r"^[0-9a-f]{40}$")
LEAGUE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNPROVEN = (
    "no-commit-noop-has-no-new-immutable-publication-receipt",
    "source-provider-freshness-not-independently-proven",
    "nfl-finality-and-clock-boundaries-not-independently-proven",
    "complete-derived-and-consumer-output-parity-not-proven",
    "prior-fail-soft-and-historical-recovery-not-certified",
    "cross-writer-atomic-skip-and-requeue-not-implemented",
)
EXPECTED_SOURCE_PARTIAL = {"missing-complete-two-phase-publication-chain"}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _initial_result(run_id: int) -> dict[str, Any]:
    return {
        "schemaVersion": 1, "mode": "offline-single-run-publication-correlation",
        "runId": run_id, "status": "blocked", "reasonCodes": [],
        "observedMainSha": None, "sourcePhaseStates": {},
        "stagePublicationStates": {}, "noOpStagesObserved": [],
        "stagePublicationCommits": {},
        "sourceTwoPhasePublicationChainVerified": False,
        "jobsAndDerivedReportsCorrelated": False,
        "verifiedStageCommitAncestry": False,
        "leagueCommitSelectedGitBlobsVerified": False,
        "completePublicationReceiptVerified": False,
        "fullOutputInventoryVerified": False,
        "providerFreshnessVerified": False, "nflFinalityVerified": False,
        "recoveryClean": False, "raceFree": False,
        "safeToSkip": False, "enforced": False,
        "unproven": list(UNPROVEN),
    }


def reconcile(
    run_id: int, expected_leagues: set[str], main_sha: str,
    source_report: dict[str, Any], standings_report: dict[str, Any],
    league_report: dict[str, Any], recovery_report: dict[str, Any],
    blob_report: dict[str, Any] | None,
    is_ancestor: Callable[[str, str], bool],
) -> dict[str, Any]:
    """Pure fail-closed combination; inputs must be separately authenticated.

    A positive result is only a finite, correlated *observation*. All safety
    decisions remain false. Source/Standings/League jobs may each report a
    no-op, but only a confirmed push supplies a publication commit SHA.
    """
    result = _initial_result(run_id)
    issues: set[str] = set()
    if (type(run_id) is not int or run_id <= 0 or
            not _sha(main_sha) or not isinstance(expected_leagues, set)
            or not expected_leagues or any(
                not isinstance(league, str) or not LEAGUE.fullmatch(league)
                for league in expected_leagues)):
        result["reasonCodes"] = ["invalid-run-main-or-league-scope"]
        return result
    if any(not isinstance(report, dict) for report in
           (source_report, standings_report, league_report, recovery_report)):
        result["reasonCodes"] = ["missing-or-malformed-stage-evidence"]
        return result
    result["observedMainSha"] = main_sha

    def require_identity(name: str, report: dict[str, Any], field: str):
        if report.get("runId") != run_id or report.get("jobCompletionVerified") is not True:
            issues.add(name + "-job-or-run-not-correlated")
        # A no-op branch has no observedMainSha in the existing publication
        # report. Never fabricate one or borrow an old commit ID.
        value = report.get(field)
        if value is not None and value != main_sha:
            issues.add(name + "-observed-main-revision-mismatch")

    require_identity("source", source_report, "mainAtAudit")
    require_identity("standings", standings_report, "observedMainSha")
    require_identity("league", league_report, "observedMainSha")
    require_identity("recovery", recovery_report, "observedMainSha")
    if (source_report.get("mainAtAudit") != main_sha or
            recovery_report.get("observedMainSha") != main_sha or
            recovery_report.get("currentMainUnchangedDuringAudit") is not True):
        issues.add("stage-snapshots-not-bound-to-same-main")
    if (type(source_report.get("runAttempt")) is not int or
            source_report["runAttempt"] < 1):
        issues.add("source-run-attempt-not-verified")
    if (recovery_report.get("producerReportsComplete") is not True or
            recovery_report.get("noBlockedDerivedRowsObserved") is not True or
            recovery_report.get("status") != "producer-reported-complete"):
        issues.add("derived-producer-recovery-status-incomplete")
    if recovery_report.get("expectedLeagueIDs") != sorted(expected_leagues):
        issues.add("recovery-league-scope-not-correlated")

    phase_states: dict[str, str] = {}
    phases = source_report.get("phases")
    if not isinstance(phases, dict):
        issues.add("source-phase-evidence-missing")
    else:
        for phase in ("raw", "canonical"):
            row = phases.get(phase)
            state = row.get("state") if isinstance(row, dict) else None
            if state not in {"no-push-observed", "no-op-observed", "publication-commit-correlated"}:
                issues.add("source-" + phase + "-state-unverifiable")
            elif state == "publication-commit-correlated" and (
                    row.get("publicationCommitVerified") is not True or
                    not _sha(row.get("publicationCommitSha"))):
                issues.add("source-" + phase + "-push-unverified")
            elif state != "publication-commit-correlated" and (
                    row.get("publicationCommitVerified") is not False or
                    row.get("publicationCommitSha") is not None):
                issues.add("source-" + phase + "-no-push-misrepresented")
            if isinstance(state, str):
                phase_states[phase] = state
    result["sourcePhaseStates"] = phase_states
    source_proven = source_report.get("sourcePublishChainVerified") is True
    result["sourceTwoPhasePublicationChainVerified"] = source_proven
    source_reasons = source_report.get("reasonCodes")
    if not isinstance(source_reasons, list) or any(
            not isinstance(v, str) for v in source_reasons):
        issues.add("malformed-source-proof-reasons")
    elif source_proven:
        if source_reasons or any(v != "publication-commit-correlated"
                                 for v in phase_states.values()):
            issues.add("source-complete-chain-contradicted")
    elif (set(source_reasons) != EXPECTED_SOURCE_PARTIAL or
          phase_states.get("raw") not in
          {"no-push-observed", "publication-commit-correlated"} or
          phase_states.get("canonical") not in
          {"no-op-observed", "no-push-observed", "publication-commit-correlated"}):
        issues.add("source-partial-chain-not-a-clean-noop-observation")

    commits: dict[str, str] = {}
    states: dict[str, str] = {}
    for name, report in (("standings", standings_report), ("league", league_report)):
        if report.get("stage") != name:
            issues.add(name + "-stage-identity-mismatch")
        verified = report.get("publicationCommitVerified") is True
        state = report.get("status")
        if verified and state == "publication-commit-correlated" and _sha(report.get("publicationCommitSha")):
            commits[name] = report["publicationCommitSha"]
            states[name] = "published-commit-correlated"
        elif (state == "no-op-observed" and report.get("publicationCommitVerified") is False
              and report.get("publicationCommitSha") is None):
            states[name] = "no-op-observed"
        else:
            issues.add(name + "-publisher-evidence-unverifiable")
    result["stagePublicationStates"] = states
    result["stagePublicationCommits"] = commits
    result["noOpStagesObserved"] = sorted(
        [name for name, state in states.items() if state == "no-op-observed"] +
        (["source-canonical"] if phase_states.get("canonical") == "no-op-observed" else [])
    )
    result["jobsAndDerivedReportsCorrelated"] = not issues

    # Stage order is causal only where a concrete publisher SHA exists. A
    # green job or a no-op log never invents an edge in the commit ancestry.
    causal_edges: list[tuple[str, str]] = []
    canonical = phases.get("canonical") if isinstance(phases, dict) else None
    source_commit = canonical.get("publicationCommitSha") if (
        source_proven and isinstance(canonical, dict)) else None
    if _sha(source_commit):
        for name in ("standings", "league"):
            if name in commits:
                causal_edges.append((source_commit, commits[name]))
    if "standings" in commits and "league" in commits:
        causal_edges.append((commits["standings"], commits["league"]))
    if causal_edges:
        for start, end in causal_edges:
            try:
                if start == end or is_ancestor(start, end) is not True:
                    issues.add("cross-stage-publication-ancestry-not-verified")
            except (github.AuditError, ValueError, TypeError, KeyError):
                issues.add("cross-stage-publication-ancestry-not-verified")
    result["verifiedStageCommitAncestry"] = bool(causal_edges) and not any(
        code == "cross-stage-publication-ancestry-not-verified" for code in issues
    )

    if "league" in commits:
        if not isinstance(blob_report, dict):
            issues.add("published-league-output-snapshot-missing")
        elif (blob_report.get("revision") != commits["league"]
              or blob_report.get("selectedGitOutputBlobIdsVerified") is not True
              or blob_report.get("metadataMinimumDraftYearsVerified") is not True
              or blob_report.get("status") != "immutable-selected-output-blobs-observed"
              or blob_report.get("canonicalLeagueIDs") != sorted(expected_leagues)
              or type(blob_report.get("selectedOutputCount")) is not int
              or blob_report["selectedOutputCount"] < 1
              or not isinstance(blob_report.get("selectedOutputFingerprint"), str)
              or not re.fullmatch(r"[0-9a-f]{64}", blob_report["selectedOutputFingerprint"])):
            issues.add("published-league-selected-blob-inventory-not-verified")
        else:
            result["leagueCommitSelectedGitBlobsVerified"] = True
    elif blob_report is not None:
        issues.add("unattributed-output-snapshot-without-league-push")

    result["reasonCodes"] = sorted(issues)
    result["status"] = "correlated-read-only-observations" if not issues else "blocked"
    if issues:
        result["jobsAndDerivedReportsCorrelated"] = False
        result["verifiedStageCommitAncestry"] = False
        result["leagueCommitSelectedGitBlobsVerified"] = False
    return result


def audit_run(
    fetch: github.Fetcher, get_log: Callable[[int], str],
    repo: str, run_id: int, expected_leagues: set[str],
    observed_at: datetime,
) -> dict[str, Any]:
    """Read only the exact requested run, its logs, and immutable Git objects.

    This does not select an older success or use a moving main as a publication
    receipt. The before/after main check is observational, never an atomic lock.
    """
    result = _initial_result(run_id)
    try:
        if (not isinstance(repo, str) or
                not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
                or type(run_id) is not int or run_id <= 0
                or not isinstance(expected_leagues, set) or not expected_leagues
                or any(not isinstance(v, str) or not LEAGUE.fullmatch(v)
                        for v in expected_leagues)):
            raise github.AuditError("Invalid repo, run or expected league scope")
        start = fetch("git/ref/heads/main", {})
        revision = (start.get("object") or {}).get("sha")
        if start.get("ref") != "refs/heads/main" or not _sha(revision):
            raise github.AuditError("Main branch ref not verifiable")
        src = source.audit_source_sync(fetch, get_log, repo, run_id, observed_at)
        standings = github.audit_publication_receipt(fetch, get_log, repo, run_id,
                                                      "standings", observed_at)
        league = github.audit_publication_receipt(fetch, get_log, repo, run_id,
                                                   "league", observed_at)
        recovered = recovery.audit_run(fetch, get_log, repo, run_id,
                                       expected_leagues, observed_at)
        blob = None
        if league.get("publicationCommitVerified") is True and _sha(
                league.get("publicationCommitSha")):
            blob = outputs.audit_immutable_outputs(fetch, league["publicationCommitSha"])
        end = fetch("git/ref/heads/main", {})
        if end.get("ref") != "refs/heads/main" or (
                end.get("object") or {}).get("sha") != revision:
            raise github.AuditError("Main changed across offline reconciliation")
        result = reconcile(
            run_id, expected_leagues, revision, src, standings, league, recovered,
            blob, lambda old, new: source._ancestry(fetch, old, new),
        )
    except (github.AuditError, ValueError, TypeError, KeyError, AttributeError,
            OSError) as exc:
        result["reasonCodes"] = [type(exc).__name__ + ": " + str(exc)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--league", action="append", required=True,
                        help="Repeat for every expected canonical league ID")
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Read-only GitHub token required", file=sys.stderr)
        return 2
    result = audit_run(
        github.api_fetch(args.repo, token),
        lambda job_id: github.fetch_job_log(args.repo, token, job_id),
        args.repo, args.run_id, set(args.league), datetime.now(timezone.utc),
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "correlated-read-only-observations" else 2


if __name__ == "__main__":
    raise SystemExit(main())
