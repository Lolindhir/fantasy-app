#!/usr/bin/env python3
"""G5: read-only temporal and cross-writer dependency invalidation probe (#1263).

A completed snapshot is not an independent provider-freshness or finality
attestation. Never authorize an actual live job skip from this tool.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from tools import league_live_shadow_gate as shadow
from derived_data_lib.league_lifecycle import LifecycleError, load_facts, parse_instant

SHA = re.compile(r"^[0-9a-f]{40}$")
UTC = timezone.utc
CLOCK_FIELDS = ("Status", "Phase", "CurrentWeek", "FinalScoredWeek",
                "WaiversOpen", "NextWaiverRun", "TradesOpen", "CutsAllowed",
                "PlayoffStartWeek", "LineupWeek")


def audit_temporal_window(
    facts: Any, model: Any, from_at: datetime, to_at: datetime,
    *, max_observation_minutes: int = 60,
) -> dict[str, Any]:
    """Check all *known* clock hazards using the canonical lifecycle model.

    Checking only the lifecycle state at two instants is insufficient: a
    kickoff, waiver run, or cap/season transition between them is a hazard,
    even when the model states at both endpoints happen to match.
    """
    errors: set[str] = set()
    events: list[dict[str, str]] = []
    result: dict[str, Any] = {
        "status": "blocked", "knownClockWindowClear": False,
        "crossedBoundaries": events, "reasonCodes": [],
        "independentProviderFreshnessVerified": False,
        "independentNflFinalityVerified": False,
        "timeAndFinalityVerified": False,
        "safeToSkip": False, "enforced": False,
    }
    if (not isinstance(from_at, datetime) or not isinstance(to_at, datetime)
            or from_at.tzinfo is None or to_at.tzinfo is None
            or from_at.utcoffset() is None or to_at.utcoffset() is None
            or type(max_observation_minutes) is not int
            or not 0 < max_observation_minutes <= 1440):
        result["reasonCodes"] = ["invalid-time-window-input"]
        return result
    start, end = from_at.astimezone(UTC), to_at.astimezone(UTC)
    result["fromUtc"] = start.isoformat().replace("+00:00", "Z")
    result["toUtc"] = end.isoformat().replace("+00:00", "Z")
    if end <= start:
        errors.add("non-forward-time-window")
    if (end - start).total_seconds() > max_observation_minutes * 60:
        errors.add("observation-window-too-long")
    if errors:
        result["reasonCodes"] = sorted(errors)
        return result
    try:
        earlier = model.resolve(facts, start)
        later = model.resolve(facts, end)
        for value in (earlier, later):
            if not isinstance(value, dict) or not isinstance(value.get("Boundaries"), dict):
                raise ValueError("Lifecycle result lacks explicit boundaries")
        for message in earlier.get("Warnings", []) + later.get("Warnings", []):
            if not isinstance(message, str):
                errors.add("unknown-lifecycle-warning")
            else:
                errors.add("lifecycle-warning-unresolved")
        def add_event(kind: str, moment: datetime) -> None:
            events.append({
                "kind": kind,
                "atUtc": moment.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            })
        for field in ("CapWindowEnd", "SeasonWindowStart", "NextWaiverRun"):
            raw = earlier["Boundaries"].get(field)
            if raw is not None:
                at = parse_instant(raw, field)
                if start < at <= end:
                    add_event(field, at)
        # Do not infer waiver processing from "WaiversOpen". Require the
        # canonical model to give a known next run when waivers are enabled.
        if earlier.get("WaiversOpen") is True and (
            earlier["Boundaries"].get("NextWaiverRun") is None
        ):
            errors.add("waiver-schedule-unverifiable")
        for game in facts.games:
            at = game.kickoff_utc
            if at is None:
                if not game.final:
                    errors.add("unresolved-nfl-game-kickoff")
                continue
            if not isinstance(at, datetime) or at.tzinfo is None:
                errors.add("invalid-nfl-kickoff")
                continue
            at = at.astimezone(UTC)
            if start < at <= end:
                add_event("NflGameKickoff:" + str(game.key), at)
            if at <= end and game.final is not True:
                errors.add("nonfinal-nfl-game-already-started")
        for field in CLOCK_FIELDS:
            if earlier.get(field) != later.get(field):
                errors.add("lifecycle-output-changed:" + field)
        if events:
            errors.add("known-clock-boundary-crossed")
    except (ValueError, TypeError, KeyError, AttributeError, LifecycleError) as exc:
        errors.add("lifecycle-time-evidence-invalid:" + type(exc).__name__)
    result.update(
        status="known-clock-window-clear" if not errors else "blocked",
        knownClockWindowClear=not errors,
        reasonCodes=sorted(errors),
        crossedBoundaries=sorted(events, key=lambda r: (r["atUtc"], r["kind"])),
    )
    return result


def compare_stage_roots(stage: str, before: Any, after: Any) -> dict[str, Any]:
    """Compare full Git-tree IDs for the *existing* shadow stage dependencies.

    This is not a branch race lock, persistent attestation or output check.
    """
    if stage not in shadow.STAGE_INPUTS:
        raise ValueError("Unknown League Live stage")
    expected = set(shadow.STAGE_INPUTS[stage])
    reason: set[str] = set()
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or set(before) != expected or set(after) != expected
            or any(not isinstance(v, str) or SHA.fullmatch(v) is None
                   for v in list(before.values()) + list(after.values()))):
        reason.add("missing-or-invalid-revision-tree")
    changed = (sorted(path for path in expected if before[path] != after[path])
               if not reason else [])
    if changed:
        reason.add("cross-writer-input-revision-changed")
    return {
        "stage": stage, "dependencyTreesUnchanged": not reason,
        "changedDependencyRoots": changed, "reasonCodes": sorted(reason),
        "raceFree": False, "recoveryClean": False,
        "outputsValidated": False, "safeToSkip": False, "enforced": False,
    }


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True,
        check=False, timeout=30,
    )
    if p.returncode:
        raise ValueError("Git revision/tree/ancestry evidence unavailable")
    return p.stdout.strip()


def audit_repo_window(
    repo: Path, league_id: str, season: int, stage: str, previous_sha: str,
    from_at: datetime, to_at: datetime,
) -> dict[str, Any]:
    """Snapshot-oriented offline probe: clean HEAD + canonical model + Git trees."""
    output: dict[str, Any] = {
        "schemaVersion": 1, "mode": "offline-time-and-cross-writer-invalidation",
        "status": "blocked", "reasonCodes": [], "previousCommitSha": previous_sha,
        "currentCommitSha": None, "knownClockWindowClear": False,
        "dependencyTreesUnchanged": False,
        "allSourceDerivedAppOutputsValidated": False,
        "independentProviderFreshnessVerified": False,
        "independentNflFinalityVerified": False,
        "raceFree": False, "recoveryClean": False,
        "timeAndFinalityVerified": False, "safeToSkip": False,
        "enforced": False,
    }
    errors: list[str] = []
    try:
        repo = Path(repo).resolve(strict=True)
        if (stage not in shadow.STAGE_INPUTS
                or not isinstance(league_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", league_id)
                or type(season) is not int or not 2000 <= season <= 2200
                or not isinstance(previous_sha, str) or not SHA.fullmatch(previous_sha)):
            raise ValueError("Invalid league, stage, season or revision identity")
        top = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if top != repo:
            raise ValueError("Offline probe requires exact repository root")
        now_sha = _git(repo, "rev-parse", "--verify", "HEAD")
        output["currentCommitSha"] = now_sha
        if not SHA.fullmatch(now_sha):
            raise ValueError("Git HEAD identity unavailable")
        if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ValueError("Worktree is not a clean immutable Git snapshot")
        _git(repo, "merge-base", "--is-ancestor", previous_sha, now_sha)
        model, facts = load_facts(repo, league_id, season)
        clock = audit_temporal_window(facts, model, from_at, to_at)
        trees: dict[str, dict[str, str]] = {}
        for label, sha in (("previous", previous_sha), ("current", now_sha)):
            trees[label] = {
                path: _git(repo, "rev-parse", "--verify", f"{sha}:{path}")
                for path in shadow.STAGE_INPUTS[stage]
            }
        revisions = compare_stage_roots(stage, trees["previous"], trees["current"])
        if _git(repo, "rev-parse", "--verify", "HEAD") != now_sha:
            raise ValueError("Observed Git HEAD changed during audit")
        output.update(
            status=("observation-no-known-invalidations"
                    if clock["knownClockWindowClear"]
                    and revisions["dependencyTreesUnchanged"] else "blocked"),
            knownClockWindowClear=clock["knownClockWindowClear"],
            dependencyTreesUnchanged=revisions["dependencyTreesUnchanged"],
            crossedBoundaries=clock["crossedBoundaries"],
            changedDependencyRoots=revisions["changedDependencyRoots"],
            reasonCodes=sorted(set(clock["reasonCodes"] + revisions["reasonCodes"])),
        )
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired,
            LifecycleError) as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
        output["reasonCodes"] = errors
    return output


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=ROOT)
    p.add_argument("--league", required=True)
    p.add_argument("--season", required=True, type=int)
    p.add_argument("--stage", choices=sorted(shadow.STAGE_INPUTS), required=True)
    p.add_argument("--previous-sha", required=True)
    p.add_argument("--from-utc", required=True)
    p.add_argument("--to-utc", required=True)
    args = p.parse_args(argv)
    try:
        first = parse_instant(args.from_utc, "from-utc")
        second = parse_instant(args.to_utc, "to-utc")
    except (LifecycleError, ValueError):
        first, second = None, None
    result = audit_repo_window(
        args.repo_root, args.league, args.season, args.stage,
        args.previous_sha, first, second,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if (result["knownClockWindowClear"] and
                 result["dependencyTreesUnchanged"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
