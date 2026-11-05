#!/usr/bin/env python3
"""Read-only G5 audit: current-scope League Source no-op reported at a Git revision.

This is NOT an independent provider-freshness or canonical-data replay proof,
nor an authorization to skip any production job (#1263).
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
from tools import league_source_receipt_audit as receipts

STAMP = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z"
LOG_LINE = re.compile(rf"^(?P<at>{STAMP}) (?P<message>.*)$")
RESET = re.compile(r"^HEAD is now at ([0-9a-f]{7,40}) .+$")
ATTEMPT = re.compile(r"^League source publish attempt ([1-9]\d*)/([1-9]\d*)$")
NO_CHANGE = "No canonical League data-source changes detected."
PARTS = {"league-core", "transactions", "drafts"}
# Conservative coverage of Source inputs and generation logic, not every
# possible shared NFL/finality/model dependency. Never a live skip criterion.
INPUT_ROOTS = ("data-source", "data-meta", "tools", ".ai-context", ".github", "public")


def _parse_job_log(log: str) -> dict[str, Any]:
    """Parse exactly three real timestamped producer JSON blocks, not shell echoes."""
    errors: list[str] = []
    if not isinstance(log, str) or not log:
        return {"reasonCodes": ["source-log-unavailable"]}
    blocks: list[dict[str, Any]] = []
    resets: list[str] = []
    attempts: list[tuple[int, int]] = []
    no_changes: list[int] = []
    push_lines: list[int] = []
    buffer: list[str] | None = None
    for index, line in enumerate(log.splitlines()):
        match = LOG_LINE.fullmatch(line)
        if match is None:
            continue
        payload = match.group("message")
        # GitHub Actions echoes source shell code with ANSI decoration; never
        # let an echoed command or provider response forge an execution event.
        if "\x1b[" in payload:
            continue
        if buffer is not None:
            buffer.append(payload)
            if payload == "}":
                try:
                    value = json.loads("\n".join(buffer))
                    if not isinstance(value, dict):
                        raise ValueError("Result must be an object")
                    blocks.append(value)
                except (ValueError, json.JSONDecodeError):
                    errors.append("invalid-source-result-json")
                buffer = None
            elif len(buffer) > 350:
                errors.append("oversized-source-result-json")
                buffer = None
            continue
        if payload == "{":
            buffer = [payload]
        if m := RESET.fullmatch(payload):
            resets.append(m.group(1))
        if m := ATTEMPT.fullmatch(payload):
            attempts.append((int(m.group(1)), int(m.group(2))))
        if payload == NO_CHANGE:
            no_changes.append(index)
        if "HEAD -> main" in payload or payload.startswith("[main "):
            push_lines.append(index)
    if buffer is not None or len(blocks) != 3:
        errors.append("missing-or-ambiguous-three-source-results")
    if attempts != [(1, 3)]:
        errors.append("source-retry-or-incomplete-attempt")
    if len(resets) != 2 or resets[0] != resets[1]:
        errors.append("source-reset-revision-race-or-missing")
    if push_lines:
        errors.append("unexpected-source-publish-in-noop")
    if len(no_changes) != 1:
        errors.append("missing-or-ambiguous-canonical-noop-marker")
    if errors:
        return {"reasonCodes": sorted(set(errors))}
    raw, first, second = blocks
    raw_rows, first_rows, second_rows = (
        value.get("Leagues") for value in (raw, first, second)
    )
    if any(not isinstance(rows, list) or not rows for rows in
           (raw_rows, first_rows, second_rows)):
        return {"reasonCodes": ["missing-source-result-league-list"]}
    if first != second:
        errors.append("canonical-second-pass-differs")
    def by_id(rows: list[Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("malformed-source-league-row")
            key = row.get("CanonicalLeagueID")
            if not isinstance(key, str) or not key or key in result:
                raise ValueError("missing-or-duplicate-source-league")
            result[key] = row
        return result
    try:
        raws = by_id(raw_rows)
        canon = by_id(first_rows)
        again = by_id(second_rows)
    except ValueError as error:
        return {"reasonCodes": [str(error)]}
    if raws.keys() != canon.keys() or canon.keys() != again.keys():
        errors.append("source-result-league-set-mismatch")
    for league in sorted(raws.keys() & canon.keys()):
        r, c = raws[league], canon[league]
        if (r.get("Scope") != "current"
                or r.get("AcquisitionScope") != "current"
                or c.get("Scope") != "current"
                or c.get("MaterializationScope") != "current"
                or r.get("Parts") != c.get("Parts")
                or not isinstance(r.get("Parts"), list)
                or set(r["Parts"]) != PARTS
                or len(r["Parts"]) != len(PARTS)):
            errors.append("wrong-or-mismatched-current-scope")
        for field in ("RawFilesChanged", "MetadataFilesChanged"):
            if type(r.get(field)) is not int or r[field] != 0:
                errors.append("raw-source-change-or-invalid-count")
        if (type(r.get("DatasetPartitions")) is not int
                or r["DatasetPartitions"] <= 0
                or type(c.get("CanonicalFiles")) is not int
                or c["CanonicalFiles"] <= 0
                or type(c.get("CanonicalFilesChanged")) is not int
                or c["CanonicalFilesChanged"] != 0):
            errors.append("canonical-change-or-incomplete-result")
        for field in ("CurrentLeagueCoreScope", "CurrentTransactionWindow",
                      "CurrentDraftScope"):
            if not isinstance(r.get(field), dict) or r[field] != c.get(field):
                errors.append("current-source-window-identity-mismatch")
        provider = r.get("CurrentProviderLeagueID")
        if (not isinstance(provider, str) or not provider.isdigit()
                or r.get("CurrentLeagueCoreScope", {}).get("ProviderLeagueID") != provider
                or r.get("CurrentDraftScope", {}).get("ProviderLeagueID") != provider):
            errors.append("invalid-current-provider-identity")
        if (not isinstance(r.get("Dependencies"), list) or not r["Dependencies"]
                or not isinstance(c.get("Dependencies"), list) or not c["Dependencies"]):
            errors.append("missing-source-dependency-evidence")
    return {"reasonCodes": sorted(set(errors)),
            "resetShortSha": resets[0],
            "canonicalLeagueIDs": sorted(raws),
            "rawPartitions": sum(r["DatasetPartitions"] for r in raws.values()
                                 if type(r.get("DatasetPartitions")) is int),
            "canonicalFiles": sum(c["CanonicalFiles"] for c in canon.values()
                                  if type(c.get("CanonicalFiles")) is int)}


def _root_tree(fetch: github.Fetcher, commit_sha: str) -> dict[str, str]:
    if not receipts._sha(commit_sha):
        raise github.AuditError("Unverified commit SHA")
    commit = fetch(f"commits/{commit_sha}", {})
    if commit.get("sha") != commit_sha:
        raise github.AuditError("Commit identity mismatch")
    details = commit.get("commit")
    tree = details.get("tree") if isinstance(details, dict) else None
    tree_sha = tree.get("sha") if isinstance(tree, dict) else None
    if not receipts._sha(tree_sha):
        raise github.AuditError("Commit tree identity not available")
    response = fetch(f"git/trees/{tree_sha}", {})
    if (response.get("sha") != tree_sha or response.get("truncated") is True
            or not isinstance(response.get("tree"), list)):
        raise github.AuditError("Incomplete Git tree evidence")
    entries: dict[str, str] = {}
    for row in response["tree"]:
        if (not isinstance(row, dict) or not isinstance(row.get("path"), str)
                or row["path"] in entries):
            raise github.AuditError("Ambiguous Git tree entry")
        if row["path"] in INPUT_ROOTS:
            if row.get("type") != "tree" or not receipts._sha(row.get("sha")):
                raise github.AuditError("Input root absent or not a Git tree")
            entries[row["path"]] = row["sha"]
    if set(entries) != set(INPUT_ROOTS):
        raise github.AuditError("Relevant Source and code roots unavailable")
    return entries


def audit_current_scope_noop(
    fetch: github.Fetcher, get_log: Callable[[int], str], repo: str,
    run_id: int, now: datetime,
) -> dict[str, Any]:
    """Bound producer-reported zero-change run to a Git tree, not a future skip."""
    base: dict[str, Any] = {
        "schemaVersion": 1, "mode": "offline-current-scope-noop-revision",
        "runId": run_id, "status": "blocked",
        "jobCompletionVerified": False,
        "reportedNoOpAtSourceRevisionVerified": False,
        "sourceRevisionSha": None, "mainAtAudit": None,
        "currentMainInputTreesUnchanged": False,
        "independentProviderFreshnessVerified": False,
        "independentCanonicalReplayVerified": False,
        "allSourceDerivedAppOutputsValidated": False,
        "timeAndFinalityVerified": False, "raceFree": False,
        "recoveryClean": False, "safeToSkip": False, "enforced": False,
        "reasonCodes": [],
    }
    try:
        saved: dict[str, str] = {}
        def fixed_ref(resource: str, params: dict[str, Any]) -> dict[str, Any]:
            result = fetch(resource, params)
            if resource == "git/ref/heads/main":
                sha = (result.get("object") or {}).get("sha")
                if "sha" in saved and saved["sha"] != sha:
                    raise github.AuditError("Main advanced during audit")
                saved["sha"] = sha
            return result

        jobs = github.fetch_jobs(fixed_ref, run_id)
        run = fixed_ref(f"actions/runs/{run_id}", {})
        name = "source / sync" if run.get("path") == github.LEAGUE_LIVE_PATH else "sync"
        matching = [j for j in jobs if (j.get("name") == name and
                    j.get("run_attempt") == run.get("run_attempt"))]
        if len(matching) != 1 or type(matching[0].get("id")) is not int:
            raise github.AuditError("Current-attempt Source Sync job ambiguous")
        log = get_log(matching[0]["id"])
        original = receipts.audit_source_sync(
            fixed_ref, lambda _id: log, repo, run_id, now
        )
        if not original["jobCompletionVerified"]:
            raise github.AuditError("Run/validation/source job not successful")
        base["jobCompletionVerified"] = True
        if (original.get("phases", {}).get("raw", {}).get("state")
                != "no-push-observed" or
                original.get("phases", {}).get("canonical", {}).get("state")
                != "no-op-observed" or
                original.get("reasonCodes") !=
                ["missing-complete-two-phase-publication-chain"]):
            raise github.AuditError("Source publisher's no-push trace is not a clean no-op")
        observed = _parse_job_log(log)
        if observed["reasonCodes"]:
            raise github.AuditError("; ".join(observed["reasonCodes"]))
        short = observed["resetShortSha"]
        resolved = fixed_ref(f"commits/{short}", {})
        full = resolved.get("sha")
        if not receipts._sha(full) or not full.startswith(short):
            raise github.AuditError("Reset revision could not resolve unambiguously")
        main = saved.get("sha")
        if not receipts._sha(main) or not receipts._ancestry(fixed_ref, full, main):
            raise github.AuditError("Reset revision is not an ancestor of observed main")
        base["sourceRevisionSha"] = full
        base["mainAtAudit"] = main
        source_trees = _root_tree(fixed_ref, full)
        main_trees = _root_tree(fixed_ref, main)
        # A second independent main read detects a moving ref during API checks.
        fixed_ref("git/ref/heads/main", {})
        base.update(
            status="run-revision-noop-reported",
            reportedNoOpAtSourceRevisionVerified=True,
            canonicalLeagueIDs=observed["canonicalLeagueIDs"],
            rawPartitionsChecked=observed["rawPartitions"],
            canonicalFilesChecked=observed["canonicalFiles"],
            sourceInputTreeShas=source_trees,
            currentMainInputTreesUnchanged=(source_trees == main_trees),
        )
    except (github.AuditError, ValueError, KeyError, TypeError, AttributeError) as error:
        base["reasonCodes"] = [type(error).__name__ + ": " + str(error)]
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if len(args.repo.split("/")) != 2 or not all(
            re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in args.repo.split("/")
        ):
            raise github.AuditError("Invalid repository")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise github.AuditError("Missing GitHub read-only token")
        data = audit_current_scope_noop(
            github.api_fetch(args.repo, token),
            lambda job_id: github.fetch_job_log(args.repo, token, job_id),
            args.repo, args.run_id, datetime.now(timezone.utc),
        )
        print(json.dumps(data, sort_keys=True))
        return 0 if data["reportedNoOpAtSourceRevisionVerified"] else 2
    except (github.AuditError, ValueError) as error:
        print("G5 Current Source no-op audit blocked: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
