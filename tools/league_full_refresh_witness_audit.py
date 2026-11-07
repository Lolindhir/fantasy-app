#!/usr/bin/env python3
"""Offline, revision-pinned validation of existing source-owned full League witness.

This does NOT prove the latest provider state, a successful new current-scope run,
a no-op, or permission to skip any live workflow. It never writes repository data.
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

from tools import league_source_refresh_witness as source

SHA40 = re.compile(r"^[0-9a-f]{40}$")
LEAGUE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
EXPECTED_FIELDS = {
    "schemaVersion", "CanonicalLeagueID", "CanonicalLeagueSeasonID",
    "ProviderLeagueID", "Season", "Week", "FinalityFingerprint",
    "Scope", "SucceededAtUtc", "Inputs", "InputsFingerprint",
}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=25, check=False,
    )
    if result.returncode:
        raise ValueError("Git repository revision or tracked-file evidence unavailable")
    return result.stdout.strip()


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Timestamp must be a UTC Z string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("Timestamp is not UTC")
    return parsed


def audit_full_witness(
    root: Path, league_id: str, *, observed_at: datetime,
    max_age_hours: float = 24.0,
) -> dict[str, Any]:
    """Validate one already-published full-week witness against a clean HEAD.

    Reuses the source owner's existing finality, manifest, metadata, hashing and
    canonical source identity rules. Verifies the bytes are still from the
    observed Git revision. This is historical coverage, never skip authority.
    """
    result: dict[str, Any] = {
        "schemaVersion": 1, "mode": "offline-source-full-week-revision-proof",
        "canonicalLeagueID": league_id, "status": "blocked",
        "observedCommitSha": None, "sourceWitnessVerified": False,
        "contentRevisionVerified": False, "observedAgeBoundVerified": False,
        "providerFreshnessVerified": False, "currentScopeNoOpVerified": False,
        "lastSuccessfulRunVerified": False, "outputsValidated": False,
        "timeAndFinalityVerified": False, "raceFree": False,
        "recoveryClean": False, "safeToSkip": False, "enforced": False,
        "reasonCodes": [],
    }
    errors: list[str] = []
    try:
        if (not isinstance(league_id, str)
                or not LEAGUE_ID.fullmatch(league_id)):
            raise ValueError("Invalid canonical league identity")
        if (observed_at.tzinfo is None or observed_at.utcoffset() is None
                or type(max_age_hours) not in (int, float)
                or not (0.0 < max_age_hours <= 168.0)):
            raise ValueError("Invalid audit clock or selected age bound")
        at = observed_at.astimezone(timezone.utc)
        root = Path(root).resolve(strict=True)
        top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if root != top:
            raise ValueError("Audit requires repository root, not a subdirectory")
        head = _git(root, "rev-parse", "--verify", "HEAD")
        if not SHA40.fullmatch(head):
            raise ValueError("Invalid Git HEAD")
        result["observedCommitSha"] = head
        # Dirty state, including untracked files, is not an immutable snapshot.
        if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ValueError("Worktree is not an exact clean Git revision")
        preflight = source.prepare(root)
        candidates = [c for c in preflight["candidates"]
                      if c["CanonicalLeagueID"] == league_id]
        if len(candidates) != 1:
            raise ValueError("No unique finalized League candidate")
        identity = candidates[0]
        season, week = identity["Season"], identity["Week"]
        witness_path = (Path(source.WITNESS_ROOT) / league_id
                        / f"{season}-week-{week:02d}.json")
        location = root / witness_path
        if not location.is_file() or location.is_symlink():
            raise ValueError("Current finalized-week witness missing or unsafe")
        witness = source._load(location)
        if not isinstance(witness, dict) or set(witness) != EXPECTED_FIELDS:
            raise ValueError("Witness schema or required fields mismatch")
        if witness["schemaVersion"] != 1 or witness["Scope"] != "full":
            raise ValueError("Witness is not from a validated full refresh")
        if any(witness.get(k) != v for k, v in identity.items()):
            raise ValueError("Source identity or NFL finality changed since witness")
        inputs = source._inputs(root, identity)
        if witness["Inputs"] != inputs:
            raise ValueError("Witness inputs differ from current Source bytes")
        computed = source._digest({"identity": identity, "inputs": inputs})
        if witness["InputsFingerprint"] != computed:
            raise ValueError("Witness fingerprint does not match canonical inputs")
        source_paths = [item["path"] for item in inputs]
        if (len(source_paths) != len(set(source_paths))
                or any(not (root / p).is_file() or (root / p).is_symlink()
                       for p in source_paths)):
            raise ValueError("Untracked, duplicated, or unsafe evidence path")
        _git(root, "ls-files", "--error-unmatch", "--",
             witness_path.as_posix(), *source_paths,
             "data-source/nfl/game-finality/" + str(season) + ".json")
        succeeded = _timestamp(witness["SucceededAtUtc"])
        age = (at - succeeded).total_seconds()
        if age < 0:
            raise ValueError("Full refresh witness was issued in the future")
        if age > max_age_hours * 3600:
            raise ValueError("Full refresh witness exceeds selected age bound")
        result.update(
            status="historical-full-week-content-confirmed",
            sourceWitnessVerified=True, contentRevisionVerified=True,
            observedAgeBoundVerified=True, season=season, finalizedWeek=week,
            witnessSucceededAtUtc=witness["SucceededAtUtc"],
            observedAgeHours=round(age / 3600, 3),
            coveredInputCount=len(inputs), inputsFingerprint=computed,
        )
    except (OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as error:
        errors.append(type(error).__name__ + ": " + str(error))
    result["reasonCodes"] = errors[:6]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--league", required=True)
    parser.add_argument("--max-age-hours", type=float, default=24.0,
                        help="Historical observation age cap; NOT a live skip TTL")
    args = parser.parse_args(argv)
    result = audit_full_witness(
        args.repo_root, args.league, observed_at=datetime.now(timezone.utc),
        max_age_hours=args.max_age_hours,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["sourceWitnessVerified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
