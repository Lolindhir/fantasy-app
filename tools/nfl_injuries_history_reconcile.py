#!/usr/bin/env python3
"""Weekly accepted-history NFL Injury Source/Derived reconciler (Issue #1421).

No year lists, provider downloads, Git commits, pushes, permissions or schedules.
Canonical reads only accepted Raw, identity and schedule; Derived reads only
persisted Canonical. Only the existing classified publishers may call --write.
Frozen upstream revisions are independently observed, never auto-replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

from nfl_injuries_materialize import _assert_bounded_path
from nfl_injuries_phase import run_injury_phase
from nfl_injuries_refresh import release_api
from nfl_source_data_lib.common import current_source_season
from nfl_source_data_lib.injury_product_plan import (
    plan_injury_history_inventory, plan_release_refresh,
)
from nfl_source_data_lib.injury_reports import valid_injury_season

_METADATA_NAME = re.compile(r"^metadata-([0-9]{4})\.json$")
_RAW_NAME = re.compile(r"^raw-([0-9]{4})\.csv$")
_CANONICAL_SEASON_NAME = re.compile(r"^[0-9]{4}$")


def _json(root: Path, relative: str) -> dict[str, Any]:
    path = _assert_bounded_path(root, relative)
    if not path.is_file():
        raise ValueError(f"Required accepted Injury input is absent: {relative}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Invalid accepted Injury input: {relative}")
    return obj


def accepted_historical_injury_seasons(repo_root: Path) -> tuple[list[int], int]:
    """Discover exact persisted Raw/metadata pairs, fail on orphaned provenance."""
    if not repo_root.is_dir():
        raise ValueError("Injury repository root does not exist")
    current = current_source_season(repo_root)
    root = repo_root / "data-source/providers/nflverse/injuries"
    if not root.exists():
        return [], current
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Stored Injury Source directory must not be a symlink")
    meta_years: set[int] = set()
    raw_years: set[int] = set()
    for entry in root.iterdir():
        name = entry.name
        if name.startswith("metadata-") and name.endswith(".json"):
            match = _METADATA_NAME.fullmatch(name)
            if not match or not valid_injury_season(int(match.group(1))):
                raise ValueError("Invalid Injury Source metadata name")
            meta_years.add(int(match.group(1)))
        if name.startswith("raw-") and name.endswith(".csv"):
            match = _RAW_NAME.fullmatch(name)
            if not match or not valid_injury_season(int(match.group(1))):
                raise ValueError("Invalid Injury Source CSV name")
            raw_years.add(int(match.group(1)))
    if meta_years != raw_years:
        raise ValueError(f"Incomplete Injury Source original/metadata pairs: "
                         f"metadataOnly={sorted(meta_years - raw_years)}, "
                         f"rawOnly={sorted(raw_years - meta_years)}")
    historical = []
    for season in sorted(meta_years):
        prefix = "data-source/providers/nflverse/injuries/"
        metadata = _json(repo_root, f"{prefix}metadata-{season}.json")
        csv_path = _assert_bounded_path(repo_root, f"{prefix}raw-{season}.csv")
        source = csv_path.read_bytes()
        if (metadata.get("SourceDataset") != "nflverse.injuries"
                or metadata.get("SchemaVersion") != 1
                or metadata.get("Season") != season
                or not source or metadata.get("AssetByteSize") != len(source)
                or metadata.get("AssetSha256") != hashlib.sha256(source).hexdigest()):
            raise ValueError(f"Persisted Injury Source is not authenticated for season {season}")
        if season < current:
            historical.append(season)
    return historical, current



def accepted_canonical_injury_seasons(repo_root: Path) -> list[int]:
    """Discover Derived partitions only from published Canonical manifests.

    No Raw, release metadata, identity graph, schedule or League manifest
    participates even in season discovery for this Derived owner.
    """
    root = _assert_bounded_path(repo_root, "data-source/nfl/injuries")
    if not root.exists():
        return []
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Canonical Injury season root must be a real directory")
    seasons: list[int] = []
    for child in sorted(root.iterdir()):
        if child.is_symlink():
            raise ValueError("Symlinked Canonical Injury season directory")
        if not child.is_dir():
            raise ValueError("Unexpected file in Canonical Injury season root")
        if not _CANONICAL_SEASON_NAME.fullmatch(child.name):
            raise ValueError("Invalid Canonical Injury season directory")
        season = int(child.name)
        if not valid_injury_season(season):
            raise ValueError("Invalid Canonical Injury season identifier")
        manifest = _json(repo_root, f"data-source/nfl/injuries/{season}/manifest.json")
        if (manifest.get("Season") != season
                or manifest.get("SchemaVersion") != 1
                or manifest.get("SourceDataset") != "nflverse.injuries"):
            raise ValueError("Canonical Injury manifest season identity mismatch")
        seasons.append(season)
    return seasons

def reconcile_accepted_injury_history(
    repo_root: Path, *, phase: str, write: bool = False,
    require_noop: bool = False,
) -> dict[str, Any]:
    """Preflight all phase-owned accepted seasons before local mutation.

    Canonical selects verified historical Raw. Derived selects published
    Canonical seasons only, including current-season Canonical if present.
    """
    if phase not in {"canonical", "derived"}:
        raise ValueError("History reconcile phase must be canonical or derived")
    if write and require_noop:
        raise ValueError("Cannot require no-op while writing")
    if phase == "canonical":
        seasons, current = accepted_historical_injury_seasons(repo_root)
        players = (_json(repo_root, "data-source/nfl/identities/players.json")
                   if seasons else None)
    else:
        seasons = accepted_canonical_injury_seasons(repo_root)
        current = None
        players = None
    planned: dict[int, dict[str, Any]] = {}
    for season in seasons:
        schedule = (_json(repo_root, f"data-source/nfl/schedules/{season}.json")
                    if phase == "canonical" else None)
        planned[season] = run_injury_phase(
            repo_root, season, phase, write=False,
            players=players, schedule=schedule,
        )
        if planned[season]["ObsoleteRequiresReview"]:
            raise ValueError(
                f"Historical Injury {season}: retired week evidence needs manual review")
    if require_noop and any(p["Changed"] or p["New"] for p in planned.values()):
        raise ValueError("Historical Injury source-replay is not a semantic no-op")
    results = {}
    for season in seasons:
        if write:
            schedule = (_json(repo_root, f"data-source/nfl/schedules/{season}.json")
                        if phase == "canonical" else None)
            results[season] = run_injury_phase(
                repo_root, season, phase, write=True,
                players=players, schedule=schedule,
            )
        else:
            results[season] = planned[season]
    changed = [season for season, result in results.items()
               if result["Changed"] or result["New"]]
    return {
        "Phase": phase, "CurrentSeason": current,
        "AcceptedHistoricalSeasons": seasons,
        "EvaluatedSeasonCount": len(seasons),
        "ChangedSeasons": changed,
        "NoOpSeasons": sorted(set(seasons) - set(changed)),
        "NewFiles": sum(len(r["New"]) for r in results.values()),
        "ChangedFiles": sum(len(r["Changed"]) for r in results.values()),
        "Written": write and bool(changed),
        "PublicationPerformed": False,
        "PerSeason": [
            {"Season": season, "Status": result["Status"],
             "New": result["New"], "Changed": result["Changed"]}
            for season, result in results.items()
        ],
    }


def audit_frozen_injury_revisions(
    repo_root: Path, *,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
) -> dict[str, Any]:
    """Report upstream revisions but never fetch or replace frozen originals."""
    seasons, current = accepted_historical_injury_seasons(repo_root)
    release = fetch_release()
    schedule_root = repo_root / "data-source/nfl/schedules"
    schedules = [
        int(p.stem) for p in schedule_root.glob("*.json")
        if p.is_file() and not p.is_symlink()
        and re.fullmatch(r"[0-9]{4}\.json", p.name)
    ]
    inventory = plan_injury_history_inventory(
        release, current_season=current,
        persisted_seasons=seasons,
        schedule_seasons=schedules,
    )
    observed: list[dict[str, Any]] = []
    requires_review: list[int] = []
    for season in seasons:
        metadata = _json(
            repo_root,
            f"data-source/providers/nflverse/injuries/metadata-{season}.json")
        decision = plan_release_refresh(
            release, season=season, stored_metadata=metadata)
        if decision["Action"] == "retry-later":
            state = "review-upstream-asset-missing"
        elif decision["FullSourceDigestAvailable"]:
            state = ("unchanged-official-digest"
                     if decision["SourceAsset"]["Sha256"] == metadata["AssetSha256"]
                     else "review-upstream-digest-changed")
        else:
            asset = decision["SourceAsset"]
            state = (
                "unchanged-unhashed-provider-revision"
                if asset["Id"] == metadata.get("ReleaseAssetId")
                and asset["UpdatedAt"] == metadata.get("ReleaseAssetUpdatedAt")
                and asset["ByteSize"] == metadata.get("AssetByteSize")
                else "review-unverifiable-provider-revision"
            )
        if state.startswith("review-"):
            requires_review.append(season)
        observed.append({"Season": season, "State": state})
    return {
        "CurrentSeason": current,
        "AcceptedHistoricalSeasons": seasons,
        "AcceptedRevisionStates": observed,
        "RequiresReview": requires_review,
        "MissingHistoryCandidates": inventory["CandidateSeasons"],
        "BlockedHistory": inventory["BlockedSeasons"],
        "PersistedMissingUpstream": inventory["PersistedMissingUpstream"],
        "OriginalsReplaced": False,
        "PublicationPerformed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--phase", choices=("canonical", "derived", "revisions"), required=True)
    parser.add_argument("--write", action="store_true",
                        help="Stage accepted canonical/derived output locally only")
    parser.add_argument("--require-noop", action="store_true",
                        help="Fail if any historical result would change; never write")
    parser.add_argument("--fail-on-review", action="store_true",
                        help="For upstream revisions only: return failure on changed/unverifiable frozen history")
    args = parser.parse_args(argv)
    try:
        if args.phase == "revisions":
            if args.write or args.require_noop:
                parser.error("Revision observation is read-only")
            result = audit_frozen_injury_revisions(args.repo_root)
        else:
            if args.fail_on_review:
                parser.error("--fail-on-review requires --phase revisions")
            result = reconcile_accepted_injury_history(
                args.repo_root, phase=args.phase, write=args.write,
                require_noop=args.require_noop,
            )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Historical Injury reconciliation failed closed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    if args.fail_on_review and result["RequiresReview"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
