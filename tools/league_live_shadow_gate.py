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
               "public/data/Timestamps.json"),
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=sorted(STAGE_INPUTS), required=True)
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--at", help="Current UTC time; defaults to process UTC now")
    p.add_argument("--source-status", default="unknown")
    p.add_argument("--upstream-status", default="unknown")
    p.add_argument("--prior-json", type=Path, help="Independent prior attestation for offline shadow replay")
    args = p.parse_args(argv)
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
