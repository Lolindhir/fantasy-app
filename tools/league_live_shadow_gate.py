#!/usr/bin/env python3
"""Observe hypothetical League Live downstream skips without changing execution (#1263 G5).

Emits JSON observations to GitHub Actions logs and Job Summaries.
There is deliberately no persisted attestation and no job is ever skipped.
Repository tree fingerprints conservatively cover all leagues and seasons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any

SCHEMA = 1
STAGE_INPUTS = {
    "standings": (
        "data-source", "data-meta", "data-derived", "public/data",
        "tools", ".ai-context/manual", ".github/workflows",
    ),
    "league": (
        "data-source", "data-meta", "data-derived", "public/data",
        "public/requests", "tools", ".ai-context/manual", ".github/workflows",
    ),
}
STAGE_OUTPUTS = {
    "standings": ("public/data/Standings.json", "data-derived/league-standings"),
    "league": ("public/data/League.json", "public/data/DecisionWindows.json",
               "public/data/Matchups.json", "public/data/FantasyGameContext.json",
               "public/data/PlayerWeekFantasy.json", "public/data/WeeklyRecaps.json",
               "public/data/Timestamps.json",
               # Existence is only a weak readiness signal: exact configured
               # future-season partitions and owner parity require separate
               # canonical evidence before any real early exit.
               "public/data/Drafts.json", "public/data/Transactions.json",
               "data-derived/league-drafts", "data-derived/league-transactions"),
}


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("Missing or invalid UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must carry a UTC offset")
    return parsed.astimezone(timezone.utc)


def sha_for(repo: Path, path: str) -> str | None:
    result = subprocess.run(["git", "rev-parse", "--verify", f"HEAD:{path}"],
                            cwd=repo, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def collect(repo: Path, stage: str, at: str, source_status: str,
            upstream_status: str) -> dict[str, Any]:
    if stage not in STAGE_INPUTS:
        raise ValueError("Unsupported stage")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          text=True, capture_output=True, check=True).stdout.strip()
    inputs = {path: sha_for(repo, path) for path in STAGE_INPUTS[stage]}
    missing = [path for path in STAGE_OUTPUTS[stage] if not (repo / path).exists()]
    return {
        "schemaVersion": SCHEMA, "stage": stage, "scope": "all-leagues-seasons",
        "atUtc": utc(at).isoformat().replace("+00:00", "Z"),
        "checkedOutHead": head, "inputTrees": inputs, "missingOutputs": missing,
        "sourceStatus": source_status, "upstreamStatus": upstream_status,
        # This probe cannot infer a prior successful output, branch-race freedom or
        # whether an earlier fail-soft materialization retained stale products.
        "raceFree": None, "recoveryClean": None,
    }


def decide(current: dict[str, Any], prior: dict[str, Any] | None) -> dict[str, Any]:
    stage = current.get("stage")
    if stage not in STAGE_INPUTS:
        raise ValueError("Unsupported stage")
    reasons = []
    trees = current.get("inputTrees")
    if not isinstance(trees, dict) or set(trees) != set(STAGE_INPUTS[stage]) or any(
        not isinstance(trees.get(path), str) or not trees[path] for path in STAGE_INPUTS[stage]
    ):
        reasons.append("incomplete-current-input-fingerprints")
    if current.get("scope") != "all-leagues-seasons":
        reasons.append("incomplete-multi-league-scope")
    if current.get("missingOutputs") or not isinstance(current.get("missingOutputs"), list):
        reasons.append("missing-or-unknown-output")
    if current.get("sourceStatus") != "success" or current.get("upstreamStatus") != "success":
        reasons.append("upstream-not-proven-successful")
    if current.get("raceFree") is not True:
        reasons.append("race-free-not-proven")
    if current.get("recoveryClean") is not True:
        reasons.append("fail-soft-recovery-not-proven-clean")
    if prior is None:
        reasons.append("missing-previous-successful-attestation")
    else:
        if prior.get("schemaVersion") != SCHEMA or prior.get("stage") != stage or prior.get("scope") != current.get("scope"):
            reasons.append("prior-attestation-identity-mismatch")
        if prior.get("completedSuccessfully") is not True or prior.get("outputsValidated") is not True:
            reasons.append("prior-publication-not-proven-complete")
        if prior.get("raceFree") is not True or prior.get("recoveryClean") is not True:
            reasons.append("prior-recovery-or-race-unknown")
        previous_trees = prior.get("inputTrees")
        if not isinstance(previous_trees, dict) or previous_trees != trees:
            reasons.append("input-revision-changed-or-unknown")
        try:
            now = utc(current["atUtc"])
            previous_at = utc(prior["processedAtUtc"])
            valid_until = utc(prior["validUntilUtc"])
            if not previous_at <= now < valid_until:
                reasons.append("temporal-boundary-or-clock-coverage")
        except (KeyError, ValueError, TypeError):
            reasons.append("temporal-proof-unavailable")
        if prior.get("clockBoundaryProof") is not True:
            reasons.append("clock-boundary-proof-unavailable")
    return {"schemaVersion": SCHEMA, "stage": stage,
            "decision": "would-run" if reasons else "would-skip",
            "reasonCodes": sorted(set(reasons)), "enforced": False}


def fingerprint(input_trees: Any) -> str | None:
    if not isinstance(input_trees, dict) or not input_trees:
        return None
    return hashlib.sha256(json.dumps(input_trees, sort_keys=True).encode()).hexdigest()[:16]


def publish_observation(observation: dict[str, Any]) -> None:
    print("LEAGUE_LIVE_SHADOW " + json.dumps(observation, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("\n### G5 League Live shadow — " + observation["stage"] + "\n")
            stream.write("- Hypothetical decision: **" + observation["decision"] + "** (no jobs skipped)\n")
            stream.write("- Input fingerprint: " + chr(96) + str(observation.get("inputFingerprint")) + chr(96) + "\n")
            stream.write("- Reasons: " + ", ".join(observation["reasonCodes"]) + "\n")




def compare_draft_owner_membership(drafts: Any, teams: Any) -> list[str]:
    """Read-only key/owner parity; draft definitions and order come from canonical history.

    Do not rederive draft creation, trading or League's presentation sort order.
    This only verifies that each published PickKey is assigned to exactly one
    matching TeamID. A direct App-to-App equality check is insufficient unless
    the independently built canonical Derived->App parity also succeeded.
    """
    if not isinstance(drafts, list) or not drafts or not isinstance(teams, list) or not teams:
        return ["missing-or-invalid-draft-or-team-list"]
    errors: list[str] = []
    owners: dict[str, int] = {}
    for draft in drafts:
        if not isinstance(draft, dict) or not isinstance(draft.get("Picks"), list):
            errors.append("malformed-app-draft")
            continue
        for pick in draft["Picks"]:
            if not isinstance(pick, dict):
                errors.append("malformed-app-pick")
                continue
            key, owner = pick.get("PickKey"), pick.get("CurrentOwnerRosterID")
            if not isinstance(key, str) or not key or type(owner) is not int:
                errors.append("missing-pick-key-or-owner")
            elif key in owners:
                errors.append("duplicate-app-pick-key:" + key)
            else:
                owners[key] = owner
    assigned: dict[str, int] = {}
    known_teams: set[int] = set()
    for team in teams:
        if not isinstance(team, dict):
            errors.append("malformed-league-team")
            continue
        team_id, picks = team.get("TeamID"), team.get("DraftPicks")
        if type(team_id) is not int or team_id in known_teams:
            errors.append("missing-or-duplicate-team-id")
            continue
        known_teams.add(team_id)
        if not isinstance(picks, list):
            errors.append("missing-team-draft-picks:" + str(team_id))
            continue
        for key in picks:
            if not isinstance(key, str) or not key:
                errors.append("malformed-team-pick-key:" + str(team_id))
            elif key in assigned:
                errors.append("duplicate-league-pick-key:" + key)
            else:
                assigned[key] = team_id
    for key, owner in sorted(owners.items()):
        if owner not in known_teams:
            errors.append("owner-has-no-team:" + key)
        if key not in assigned:
            errors.append("league-missing-pick:" + key)
        elif assigned[key] != owner:
            errors.append("league-owner-mismatch:" + key)
    for key in sorted(assigned.keys() - owners.keys()):
        errors.append("league-extra-pick:" + key)
    return sorted(set(errors))


def audit_draft_content(repo_root: Path, league_id: str) -> dict[str, Any]:
    """Offline-only parity against canonical history, persisted Derived and App.

    Reuse the authoritative History builder and consumer renderer, rather than
    inventing a future-year horizon or a second pick-owner model. Historical
    products are verified too. No writer, network request or Git state mutation.
    This is content evidence, NOT a prior-success/race/clock attestation.
    """
    # Direct `python tools/league_live_shadow_gate.py` execution puts tools/
    # rather than the repository root on sys.path. Keep this CLI independent
    # of the runner's optional PYTHONPATH configuration.
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from tools.league_history_app_publish import (
        _difference, build_history, load_inputs, render, verified_product_history,
    )

    result: dict[str, Any] = {
        "schemaVersion": SCHEMA, "mode": "offline-draft-content",
        "canonicalLeagueID": league_id, "status": "blocked",
        "contentParityVerified": False, "safeToSkip": False, "enforced": False,
    }
    try:
        inputs = load_inputs(repo_root, league_id)
        history = build_history(inputs)
        if history.unresolved:
            raise ValueError("Canonical history has unresolved pick identities")
        persisted, references = verified_product_history(repo_root, league_id, history)
        rendered = render(persisted, inputs.league_year, references)
        expected_drafts = rendered["Drafts"]["current"]
        app_drafts = json.loads((repo_root / "public/data/Drafts.json").read_text(encoding="utf-8"))
        league = json.loads((repo_root / "public/data/League.json").read_text(encoding="utf-8"))
        if not isinstance(league, dict):
            raise ValueError("League App payload is not an object")
        errors = _difference(expected_drafts, app_drafts)
        errors.extend(compare_draft_owner_membership(expected_drafts, league.get("Teams")))
        if not expected_drafts:
            errors.append("canonical-history-has-no-current-or-future-drafts")
        years = sorted({int(d["Season"]) for d in expected_drafts})
        result.update(
            draftSeasons=years, drafts=len(expected_drafts),
            picks=sum(len(d["Picks"]) for d in expected_drafts),
            errors=errors[:25], errorCount=len(errors),
        )
        if not errors:
            result.update(status="verified", contentParityVerified=True)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        result.update(errors=[type(error).__name__ + ": " + str(error)], errorCount=1)
    return result


def parse_observed_log(log_text: str) -> dict[str, Any]:
    """Extract exactly one shadow observation from an existing GitHub job log."""
    marker = "LEAGUE_LIVE_SHADOW "
    records = [line.partition(marker)[2].strip() for line in log_text.splitlines() if marker in line]
    if len(records) != 1:
        raise ValueError(f"Expected exactly one League Live shadow observation, got {len(records)}")
    try:
        value = json.loads(records[0])
    except json.JSONDecodeError as error:
        raise ValueError("Malformed League Live shadow JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Shadow observation must be an object")
    return value


def _verified_observed_signature(row: dict[str, Any]) -> bool:
    stage = row.get("stage")
    if (stage not in STAGE_INPUTS or row.get("schemaVersion") != SCHEMA
            or row.get("enforced") is not False or row.get("decision") not in {"would-run", "would-skip"}
            or not isinstance(row.get("missingOutputs"), list) or row["missingOutputs"]
            or not isinstance(row.get("checkedOutHead"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", row["checkedOutHead"])):
        return False
    trees = row.get("inputTrees")
    if not isinstance(trees, dict) or set(trees) != set(STAGE_INPUTS[stage]):
        return False
    if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v) for v in trees.values()):
        return False
    return fingerprint(trees) == row.get("inputFingerprint")


def compare_observed_logs(previous_log: str, current_log: str) -> dict[str, Any]:
    """Compare real log signatures, not prior-success or temporal attestations.

    Log no-op markers alone do not prove a GitHub job completed successfully or
    that a downstream publication was healthy. No stage is ever skipped here.
    """
    previous, current = parse_observed_log(previous_log), parse_observed_log(current_log)
    if previous.get("stage") != current.get("stage") or previous.get("stage") not in STAGE_INPUTS:
        raise ValueError("Different or unknown League Live shadow stages")
    reasons = []
    try:
        previous_at, current_at = utc(previous.get("atUtc")), utc(current.get("atUtc"))
        if current_at <= previous_at:
            reasons.append("non-monotonic-observation-times")
    except (TypeError, ValueError):
        reasons.append("observation-time-unverifiable")
    if not _verified_observed_signature(previous) or not _verified_observed_signature(current):
        reasons.append("incomplete-or-tampered-signature")
    changed = []
    if not reasons:
        changed = sorted(p for p in STAGE_INPUTS[current["stage"]]
                         if previous["inputTrees"][p] != current["inputTrees"][p])
    return {
        "schemaVersion": SCHEMA, "stage": current["stage"],
        "classification": ("unverifiable" if reasons else
                           "changed-input-revision" if changed else "same-observed-inputs"),
        "changedPaths": changed,
        "previousHead": previous.get("checkedOutHead"),
        "currentHead": current.get("checkedOutHead"),
        "previousInputFingerprint": previous.get("inputFingerprint"),
        "currentInputFingerprint": current.get("inputFingerprint"),
        "previousPublisherNoOpLogMarker": "Generator produced no repository changes. Nothing to publish." in previous_log,
        "currentPublisherNoOpLogMarker": "Generator produced no repository changes. Nothing to publish." in current_log,
        "reasonCodes": sorted(reasons),
        "safeToSkip": False,
        "enforced": False,
        "unproven": ["prior-success-attestation", "cross-workflow-revision-and-race-safety",
                     "fail-soft-recovery-cleanliness", "temporal-boundary-safety"],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=sorted(STAGE_INPUTS))
    p.add_argument("--audit-draft-content", action="store_true",
                   help="offline-only canonical/Derived/App draft parity (no job skipping)")
    p.add_argument("--league", help="canonical league identity for the offline audit")
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--at", help="Current UTC time; defaults to process UTC now")
    p.add_argument("--source-status", default="unknown")
    p.add_argument("--upstream-status", default="unknown")
    p.add_argument("--prior-json", type=Path, help="Independent prior attestation for offline shadow replay")
    p.add_argument("--compare-log-files", nargs=2, type=Path,
                   metavar=("EARLIER_JOB_LOG", "LATER_JOB_LOG"),
                   help="Offline read-only comparison of two downloaded GitHub job logs")
    args = p.parse_args(argv)
    if args.audit_draft_content:
        if args.stage is not None or args.prior_json is not None or args.compare_log_files:
            p.error("--audit-draft-content cannot be combined with live/compare modes")
        if not args.league:
            p.error("--audit-draft-content requires --league")
        result = audit_draft_content(args.repo_root, args.league)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["contentParityVerified"] else 2
    if args.league:
        p.error("--league is only supported with --audit-draft-content")
    if args.compare_log_files:
        if args.stage is not None or args.prior_json is not None:
            p.error("--compare-log-files cannot be combined with --stage or --prior-json")
        try:
            earlier, later = (path.read_text(encoding="utf-8", errors="replace")
                              for path in args.compare_log_files)
            print(json.dumps(compare_observed_logs(earlier, later), sort_keys=True))
            return 0
        except (OSError, ValueError, TypeError) as error:
            print(f"G5 shadow log comparison unavailable: {error}", file=sys.stderr)
            return 2
    if args.stage is None:
        p.error("--stage is required for the existing live shadow observation")
    try:
        current = collect(args.repo_root, args.stage,
                          args.at or datetime.now(timezone.utc).isoformat(),
                          args.source_status, args.upstream_status)
        prior = json.loads(args.prior_json.read_text(encoding="utf-8")) if args.prior_json else None
        result = {**decide(current, prior),
                  "atUtc": current["atUtc"], "checkedOutHead": current["checkedOutHead"],
                  "inputTrees": current["inputTrees"], "inputFingerprint": fingerprint(current["inputTrees"]),
                  "missingOutputs": current["missingOutputs"]}
        publish_observation(result)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        result = {"schemaVersion": SCHEMA, "stage": args.stage, "decision": "would-run",
                  "reasonCodes": ["shadow-observation-unavailable"], "enforced": False,
                  "inputFingerprint": None}
        publish_observation(result)
        print(f"::warning title=League Live shadow unavailable::{type(error).__name__}: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
