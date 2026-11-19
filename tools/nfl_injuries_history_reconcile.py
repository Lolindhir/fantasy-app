#!/usr/bin/env python3
"""Recurring NFL Injury source admission and historical reconciliation (#1421).

No year lists, Git commits, pushes, permissions or schedules. Historical
batch Raw admission preflights all missing official originals before staging; accepted
historical originals remain frozen. Canonical consumes persisted Raw; Derived
consumes persisted Canonical. --write only stages files in the existing writer.
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
from nfl_injuries_refresh import discover_injury_history, release_api, source_asset
from nfl_source_data_lib.common import current_source_season
from nfl_source_data_lib.injury_product_plan import (
    build_injury_artifacts, plan_injury_history_inventory, plan_release_refresh,
)
from nfl_source_data_lib.injury_reports import valid_injury_season

_METADATA_NAME = re.compile(r"^metadata-([0-9]{4})\.json$")
_RAW_NAME = re.compile(r"^raw-([0-9]{4})\.csv$")
_CANONICAL_SEASON_NAME = re.compile(r"^[0-9]{4}$")

# The sole documented cancelled game omitted from the canonical nflverse schedule.
# Same historical fact as tools/schedule_archive.py::SUPPLEMENTS. Do NOT add a
# fabricated played game or change canonical NFL schedules to make this join pass.
_CANCELLED_2022_GAME_ID = "2022_17_BUF_CIN"


def _verified_cancelled_game_unlinked_reports(
    season: int, artifacts: dict[str, bytes], schedule: dict[str, Any],
) -> int:
    """Count ONLY unmatched 2022 BUF/CIN week-17 cancelled-game observations.

    Retain GameID=null and GameLinkState=not-found in Canonical. The exception
    authorizes original-source admission, not an assertion that the game played.
    Every other unlinked, ambiguous or unresolved observation remains blocking.
    """
    if season != 2022:
        return 0
    if any(game.get("GameID") == _CANCELLED_2022_GAME_ID
           for game in schedule.get("Games", [])):
        return 0
    week_path = "data-source/nfl/injuries/2022/17.json"
    if week_path not in artifacts:
        return 0
    partition = json.loads(artifacts[week_path])
    return sum(
        1 for row in partition["Observations"]
        if row.get("Season") == 2022
        and row.get("Week") == 17
        and row.get("GameType") == "REG"
        and row.get("SourceTeam") in {"BUF", "CIN"}
        and row.get("GameLinkState") == "not-found"
        and row.get("GameID") is None
    )


def _json(root: Path, relative: str) -> dict[str, Any]:
    path = _assert_bounded_path(root, relative)
    if not path.is_file():
        raise ValueError(f"Required accepted Injury input is absent: {relative}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Invalid accepted Injury input: {relative}")
    return obj


def accepted_historical_injury_seasons(
    repo_root: Path, *, allow_incomplete: bool = False,
) -> tuple[list[int], int]:
    """Discover authenticated Raw/metadata pairs.

    Normal consumers reject orphaned originals. The missing-source intake alone
    may inspect them for recovery without weakening Canonical/Derived readers.
    """
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
    if meta_years != raw_years and not allow_incomplete:
        raise ValueError(f"Incomplete Injury Source original/metadata pairs: "
                         f"metadataOnly={sorted(meta_years - raw_years)}, "
                         f"rawOnly={sorted(raw_years - meta_years)}")
    historical = []
    for season in sorted(meta_years & raw_years):
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




def stage_next_verified_missing_injury_source(
    repo_root: Path, *, write: bool = False,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    fetch_asset: Callable[[str], bytes] = source_asset,
    pinned_season: int | None = None,
) -> dict[str, Any]:
    """Recurring, bounded admission/recovery of ONE missing historical source.

    Always rediscover official release seasons. A fully absent Source pair, a
    missing CSV, or a missing metadata file remains eligible on every weekly
    or explicitly requested run. Existing original bytes are never replaced.
    Upstream SHA is checked when present; otherwise a pinned official asset
    URL/ID/size, self-hash and full semantic preflight attest the first import.
    """
    accepted, current = accepted_historical_injury_seasons(
        repo_root, allow_incomplete=True)
    source_dir = _assert_bounded_path(
        repo_root, "data-source/providers/nflverse/injuries")
    incomplete: set[int] = set()
    if source_dir.exists():
        if not source_dir.is_dir() or source_dir.is_symlink():
            raise ValueError("Historical Injury Source directory is not a real directory")
        raw_years = set()
        meta_years = set()
        for entry in source_dir.iterdir():
            if entry.name.startswith("raw-") and entry.name.endswith(".csv"):
                match = _RAW_NAME.fullmatch(entry.name)
                if not match or entry.is_symlink() or not entry.is_file():
                    raise ValueError("Invalid persisted historical Injury original")
                raw_years.add(int(match.group(1)))
            elif entry.name.startswith("metadata-") and entry.name.endswith(".json"):
                match = _METADATA_NAME.fullmatch(entry.name)
                if not match or entry.is_symlink() or not entry.is_file():
                    raise ValueError("Invalid persisted historical Injury metadata")
                meta_years.add(int(match.group(1)))
        incomplete = {year for year in raw_years ^ meta_years if year < current}

    release = fetch_release()
    inventory = discover_injury_history(
        repo_root=repo_root, fetch_release=lambda: release,
        allow_incomplete=True)
    if inventory["CurrentSeason"] != current:
        raise ValueError("Historical Injury current season changed during discovery")
    candidates = inventory["CandidateSeasons"]
    missing_orphan = sorted(incomplete - set(candidates))
    if missing_orphan:
        raise ValueError(
            f"Incomplete frozen Injury Source cannot be recovered from official "
            f"release and accepted schedule: {missing_orphan}")
    if pinned_season is not None:
        if (not valid_injury_season(pinned_season)
                or pinned_season >= current):
            raise ValueError("Pinned historical Injury season is invalid or current")
        if pinned_season in accepted:
            return {
                "Phase": "intake", "Status": "pinned-original-already-accepted",
                "Season": pinned_season, "CurrentSeason": current,
                "AcceptedHistoricalSeasons": accepted,
                "BlockedSeasons": inventory["BlockedSeasons"],
                "PersistedMissingUpstream": inventory["PersistedMissingUpstream"],
                "Staged": False, "PublicationPerformed": False,
            }
        if pinned_season not in candidates:
            raise ValueError(
                f"Pinned historical Injury season {pinned_season} is no longer "
                "eligible for the originally selected admission")

    if not candidates:
        return {
            "Phase": "intake", "Status": "no-eligible-missing-original",
            "Season": None, "CurrentSeason": current,
            "AcceptedHistoricalSeasons": accepted,
            "BlockedSeasons": inventory["BlockedSeasons"],
            "PersistedMissingUpstream": inventory["PersistedMissingUpstream"],
            "Staged": False, "PublicationPerformed": False,
        }

    # Prioritize recovery of a vanished half-pair over first-time history.
    # Exactly one season per invocation keeps the existing Source writer bounded.
    season = (pinned_season if pinned_season is not None else
              max(incomplete) if incomplete else max(candidates))
    if season >= current or season in accepted:
        raise ValueError("Historical Injury admission selected accepted/current Source")
    raw_name = f"data-source/providers/nflverse/injuries/raw-{season}.csv"
    meta_name = f"data-source/providers/nflverse/injuries/metadata-{season}.json"
    raw_path = _assert_bounded_path(repo_root, raw_name)
    meta_path = _assert_bounded_path(repo_root, meta_name)
    if raw_path.is_symlink() or meta_path.is_symlink():
        raise ValueError("Symlinked missing historical Injury Source is not recoverable")
    if raw_path.is_file() and meta_path.is_file():
        raise ValueError("Historical Injury original exists; no frozen replacement")

    decision = plan_release_refresh(release, season=season)
    if decision["Action"] == "retry-later":
        raise ValueError("Selected historical Injury asset disappeared upstream")
    upstream = decision["SourceAsset"]
    original = fetch_asset(upstream["DownloadUrl"])
    if not isinstance(original, bytes) or len(original) != upstream["ByteSize"]:
        raise ValueError("Historical Injury original fails official asset byte-size proof")
    computed_digest = hashlib.sha256(original).hexdigest()
    official_digest = upstream["Sha256"]
    if official_digest is not None and computed_digest != official_digest:
        raise ValueError("Historical Injury original disagrees with official SHA-256/size")
    # If any part of an accepted original survives, it must bind exactly to
    # these downloaded bytes. No new revision is introduced through recovery.
    if raw_path.is_file() and raw_path.read_bytes() != original:
        raise ValueError("Missing historical metadata cannot replace frozen CSV bytes")
    if meta_path.is_file():
        prior = _json(repo_root, meta_name)
        if (prior.get("SchemaVersion") != 1
                or prior.get("SourceDataset") != "nflverse.injuries"
                or prior.get("Season") != season
                or prior.get("AssetSha256") != computed_digest
                or prior.get("AssetByteSize") != len(original)):
            raise ValueError("Missing historical CSV does not match frozen metadata")
    canonical_path = _assert_bounded_path(
        repo_root, f"data-source/nfl/injuries/{season}/manifest.json")
    if canonical_path.is_file():
        manifest = _json(
            repo_root, f"data-source/nfl/injuries/{season}/manifest.json")
        if (manifest.get("Season") != season
                or manifest.get("SourceDataset") != "nflverse.injuries"
                or manifest.get("SourceAssetSha256") != computed_digest):
            raise ValueError("Historical source recovery conflicts with frozen Canonical provenance")

    players = _json(repo_root, "data-source/nfl/identities/players.json")
    schedule = _json(repo_root, f"data-source/nfl/schedules/{season}.json")
    plan = build_injury_artifacts(
        season=season, source_csv=original, players=players,
        schedule=schedule, expected_source_sha256=computed_digest,
        release_asset=upstream)
    manifest = json.loads(plan[f"data-source/nfl/injuries/{season}/manifest.json"])
    quality = manifest["CanonicalQuality"]
    count = manifest["SourceRowCount"]
    identities = quality["IdentityResolutionCounts"]
    links = quality["GameLinkCounts"]
    cancelled_count = _verified_cancelled_game_unlinked_reports(
        season, plan, schedule)
    if (count < 1 or identities.get("resolved-current-graph") != count
            or links.get("linked", 0) + cancelled_count != count
            or any(identities.get(state) for state in ("unresolved", "ambiguous"))
            or links.get("not-found", 0) != cancelled_count
            or any(links.get(state) for state in
                   ("ambiguous", "not-evaluated"))):
        raise ValueError(
            "Historical Injury source admission needs identity/game-link review: "
            + json.dumps(quality, sort_keys=True))

    expected_new = {p for p, present in
                    ((raw_name, raw_path.is_file()), (meta_name, meta_path.is_file()))
                    if not present}
    planned = run_injury_phase(
        repo_root, season, "raw", source_csv=original,
        expected_source_sha256=computed_digest, release_json=release, write=False)
    if (planned["Changed"] or planned["ObsoleteRequiresReview"]
            or set(planned["New"]) != expected_new):
        raise ValueError(
            "Historical Injury admission would change frozen originals or exceed missing Raw paths")
    staged = run_injury_phase(
        repo_root, season, "raw", source_csv=original,
        expected_source_sha256=computed_digest, release_json=release, write=True,
    ) if write else planned
    return {
        "Phase": "intake",
        "Status": ("staged-missing-validated-source" if write
                   else "validated-missing-source-dry-run"),
        "SourceAttestation": ("matched-official-sha256" if official_digest
                             else "official-release-asset-and-self-sha256"),
        "Season": season, "CurrentSeason": current,
        "SourceAssetSha256": computed_digest,
        "SourceRowCount": count, "ObservedWeekCount": manifest["ObservedWeekCount"],
        "KnownCancelledGameReports": cancelled_count,
        "Quality": quality, "NewRawPaths": sorted(expected_new),
        "BlockedSeasons": inventory["BlockedSeasons"],
        "AcceptedHistoricalSeasons": accepted,
        "Staged": bool(write and staged["Written"]),
        "PublicationPerformed": False,
    }




def stage_all_verified_missing_injury_sources(
    repo_root: Path, *, write: bool = False,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    fetch_asset: Callable[[str], bytes] = source_asset,
    pinned_seasons: list[int] | None = None,
) -> dict[str, Any]:
    """Preflight ALL missing originals before staging any Raw files.

    The exact selection is pinned across the Source workflow's publication
    retries. An accepted pinned season becomes a no-op, never a reason to
    discover and import a different year during the same invocation.
    """
    accepted, current = accepted_historical_injury_seasons(
        repo_root, allow_incomplete=True)
    release = fetch_release()
    inventory = discover_injury_history(
        repo_root=repo_root, fetch_release=lambda: release,
        allow_incomplete=True)
    if inventory["CurrentSeason"] != current:
        raise ValueError("Historical Injury current season changed during batch discovery")
    candidates = set(inventory["CandidateSeasons"])
    if pinned_seasons is None:
        selected = sorted(candidates, reverse=True)
    else:
        selected = list(pinned_seasons)
        if (len(selected) != len(set(selected))
                or any(not valid_injury_season(year) or year >= current
                       for year in selected)):
            raise ValueError("Invalid pinned historical Injury batch")
        if any(year not in candidates and year not in accepted for year in selected):
            raise ValueError("Pinned historical Injury batch includes ineligible Source")
    # This remains an all-or-nothing Source admission: a bad original, a
    # mismatched frozen half-pair, or a failed player/game join prevents every
    # new Raw file in the batch from being staged/published.
    cache: dict[str, bytes] = {}

    def cached_asset(url: str) -> bytes:
        if url not in cache:
            cache[url] = fetch_asset(url)
        return cache[url]

    pending = [year for year in selected if year not in accepted]
    common = {"fetch_release": lambda: release, "fetch_asset": cached_asset}
    previews = {}
    for year in pending:
        previews[year] = stage_next_verified_missing_injury_source(
            repo_root, pinned_season=year, write=False, **common)
    new_paths = sorted(
        path for year in pending for path in previews[year]["NewRawPaths"])
    per_season = []
    for year in selected:
        if year in accepted:
            per_season.append({"Season": year, "Status": "pinned-original-already-accepted",
                               "Staged": False})
            continue
        result = (stage_next_verified_missing_injury_source(
            repo_root, pinned_season=year, write=True, **common)
            if write else previews[year])
        per_season.append({"Season": year, "Status": result["Status"],
                           "Staged": result["Staged"],
                           "SourceAssetSha256": result["SourceAssetSha256"],
                           "SourceRowCount": result["SourceRowCount"]})
    staged = [entry["Season"] for entry in per_season if entry["Staged"]]
    return {
        "Phase": "intake", "Status": (
            "staged-validated-history-batch" if staged else
            "validated-missing-history-batch-dry-run" if pending else
            "no-eligible-missing-original"),
        "Seasons": selected, "CurrentSeason": current,
        "AcceptedHistoricalSeasons": accepted,
        "StagedSeasons": staged,
        "NoOpSeasons": [year for year in selected if year in accepted],
        "NewRawPaths": new_paths if write else [],
        "BlockedSeasons": inventory["BlockedSeasons"],
        "PersistedMissingUpstream": inventory["PersistedMissingUpstream"],
        "PerSeason": per_season,
        "Staged": bool(staged), "PublicationPerformed": False,
    }


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
    parser.add_argument("--phase", choices=("intake", "canonical", "derived", "revisions"), required=True)
    parser.add_argument("--season", type=int,
                        help="Pin one historical intake season (legacy single-source mode)")
    parser.add_argument("--all-missing", action="store_true",
                        help="Preflight and stage every eligible missing original in one batch")
    parser.add_argument("--seasons", type=str,
                        help="Comma-separated pinned batch; never discover extra seasons on retry")
    parser.add_argument("--write", action="store_true",
                        help="Stage eligible missing Raw or accepted canonical/derived locally only")
    parser.add_argument("--require-noop", action="store_true",
                        help="Fail if any historical result would change; never write")
    parser.add_argument("--fail-on-review", action="store_true",
                        help="For upstream revisions only: return failure on changed/unverifiable frozen history")
    args = parser.parse_args(argv)
    if args.season is not None and args.phase != "intake":
        parser.error("--season is only valid for historical intake")
    if (args.all_missing or args.seasons is not None) and args.phase != "intake":
        parser.error("--all-missing/--seasons require historical intake")
    if args.season is not None and (args.all_missing or args.seasons is not None):
        parser.error("--season cannot be combined with batch intake")
    if args.seasons is not None and not re.fullmatch(r"[0-9]{4}(,[0-9]{4})*", args.seasons):
        parser.error("--seasons requires comma-separated four-digit seasons")
    try:
        if args.phase == "revisions":
            if args.write or args.require_noop:
                parser.error("Revision observation is read-only")
            result = audit_frozen_injury_revisions(args.repo_root)
        elif args.phase == "intake":
            if args.fail_on_review or args.require_noop:
                parser.error("Intake has no revision-failure or replay-no-op mode")
            if args.all_missing or args.seasons is not None:
                selected = ([int(value) for value in args.seasons.split(",")]
                            if args.seasons is not None else None)
                result = stage_all_verified_missing_injury_sources(
                    args.repo_root, write=args.write, pinned_seasons=selected)
            else:
                result = stage_next_verified_missing_injury_source(
                    args.repo_root, write=args.write, pinned_season=args.season)
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
