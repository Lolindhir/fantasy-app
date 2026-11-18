#!/usr/bin/env python3
"""Existing nfl-games product: bounded per-GameID detail materialization (#1077).

Read-only by default. Only --write persists compact, versioned GameDetail files
under data-derived/nfl-games/details/<season>/<GameID>.json. Canonical source
week records are read once per week and only games with actual PlayerStats or
SnapCounts evidence are eligible. Preflight all selected games before writing.
No Source, original PBP, existing season-index or consumer mutation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.nfl_game_detail import _season_index
from derived_data_lib.nfl_game_detail_core import build_nfl_game_detail_v2
from derived_data_lib.nfl_pbp_accepted_season import AcceptedPBPSeasons
from nfl_source_data_lib.common import current_source_season


EXIT_DIFFERENT = 3
_VALID_GAME_ID = re.compile(r"^[0-9]{4}_[0-9]{2}_[A-Z0-9]+_[A-Z0-9]+$")


def _json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Canonical partition is not an object: {path}")
    return document


def _week_partition(
    source: Path, dataset: str, season: int, week: int,
    cache: dict[tuple[str, int], dict[str, Any] | None],
) -> dict[str, Any] | None:
    key = (dataset, week)
    if key not in cache:
        payload = _json(source / dataset / str(season) / f"{week:02d}.json")
        if payload is not None and (
            payload.get("SchemaVersion") != 2
            or payload.get("Season") != season
            or payload.get("Week") != week
            or payload.get("SourceDataset") != "nflverse." + dataset
            or type(payload.get("Finalized")) is not bool
            or not isinstance(payload.get("Records"), list)
        ):
            raise ValueError(f"Invalid canonical {dataset} partition: {season}/{week:02d}")
        cache[key] = payload
    return cache[key]


def _game_evidence_ids(
    payload: dict[str, Any] | None, dataset: str,
) -> set[str]:
    if payload is None:
        return set()
    result: set[str] = set()
    for row in payload["Records"]:
        if not isinstance(row, dict):
            raise ValueError(f"Invalid {dataset} record")
        if dataset == "player-stats":
            stats = row.get("Stats")
            game_id = stats.get("game_id") if isinstance(stats, dict) else None
        else:
            game_id = row.get("GameID")
        if not isinstance(game_id, str) or not game_id:
            raise ValueError(f"{dataset} record lacks canonical GameID")
        result.add(game_id)
    return result


def plan_season(
    repo_root: Path, season: int, *, out_root: Path | None = None,
    write: bool = False, pbp_store: AcceptedPBPSeasons | None = None,
) -> dict[str, Any]:
    """Build every eligible game and validate the entire season before writes."""
    derived = (out_root or (repo_root / DATA_DERIVED_ROOT))
    index_path = repo_root / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json"
    index = _json(index_path)
    if index is None:
        raise ValueError(f"Published canonical NFL Games index missing: {season}")
    source_season, games = _season_index(index)
    if source_season != season:
        raise ValueError(f"Index Season mismatch for {season}")
    # Discover accepted original PBP evidence from Source manifests, not a
    # hard-coded year. Absent evidence produces v2 with unavailable PBP.
    pbp = (pbp_store or AcceptedPBPSeasons(repo_root)).get(season, games)
    source_plays, source_sha = pbp if pbp is not None else ({}, None)
    src = repo_root / DATA_SOURCE_ROOT / "nfl"
    target = derived / "nfl-games" / "details" / str(season)
    by_week = defaultdict(list)
    for game_id, game in games.items():
        week = game.get("Week")
        if type(week) is not int or not 1 <= week <= 25:
            raise ValueError(f"Invalid week for {game_id}")
        if not _VALID_GAME_ID.fullmatch(game_id) or not game_id.startswith(f"{season}_"):
            raise ValueError(f"Unsafe/noncanonical GameID: {game_id}")
        by_week[week].append(game_id)
    cache: dict[tuple[str, int], dict[str, Any] | None] = {}
    preflight: list[tuple[Path, str]] = []
    eligible_ids: set[str] = set()
    unreadable = 0
    stats_missing = 0
    snaps_missing = 0
    identity_holds = 0
    invalid_snap_share_rows = 0
    skipped = 0
    pbp_observed = 0
    for week in sorted(by_week):
        stats = _week_partition(src, "player-stats", season, week, cache)
        snaps = _week_partition(src, "snap-counts", season, week, cache)
        evidence = _game_evidence_ids(stats, "player-stats") | _game_evidence_ids(snaps, "snap-counts")
        unknown = evidence.difference(by_week[week])
        if unknown:
            raise ValueError(f"Canonical week {season}/{week:02d} has unknown GameIDs: {sorted(unknown)[:3]}")
        for game_id in sorted(by_week[week]):
            if game_id not in evidence:
                skipped += 1
                continue
            plays = source_plays.get(game_id)
            detail = build_nfl_game_detail_v2(
                index, game_id, stats, snaps,
                pbp_rows=plays, pbp_asset_sha256=source_sha if plays else None,
            )
            pbp_observed += plays is not None
            eligible_ids.add(game_id)
            if detail["TeamStats"]["Status"] == "unavailable":
                stats_missing += 1
            if detail["SnapCounts"]["Status"] == "unavailable":
                snaps_missing += 1
            if (detail["TeamStats"]["UnresolvedPlayerIdentityRows"]
                    or detail["SnapCounts"]["UnresolvedPlayerIdentityRows"]):
                identity_holds += 1
            invalid_snap_share_rows += detail["SnapCounts"].get("InvalidShareRows", 0)
            serialized = json.dumps(detail, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            filename = target / (game_id + ".json")
            if filename.is_file():
                try:
                    old = filename.read_text(encoding="utf-8")
                except (UnicodeError, OSError) as exc:
                    raise ValueError(f"Unreadable existing derived detail {filename}") from exc
                if old == serialized:
                    continue
            preflight.append((filename, serialized))
    # A removed source game is not evidence for deleting already-published history.
    if target.exists():
        stale = sorted(p.name for p in target.glob("*.json") if p.stem not in eligible_ids)
        if stale:
            raise ValueError(f"Existing NFL GameDetails not supported by current accepted source: {season}, {stale[:5]}")
    if write:
        for filename, serialized in preflight:
            filename.parent.mkdir(parents=True, exist_ok=True)
            filename.write_text(serialized, encoding="utf-8")
    return {
        "Season": season,
        "IndexedGames": len(games),
        "EligibleGames": len(eligible_ids),
        "NoSourceEvidenceGames": skipped,
        "WithMissingTeamStats": stats_missing,
        "WithMissingTeamSnaps": snaps_missing,
        "WithIdentityHolds": identity_holds,
        "WithInvalidSnapShareRows": invalid_snap_share_rows,
        "AcceptedPBPSourceSeason": pbp is not None,
        "PBPGamesWithOriginalRows": pbp_observed,
        "PBPGamesWithoutOriginalRows": len(eligible_ids) - pbp_observed,
        "DetailSchemaVersion": 2,
        "ExistingUnchanged": len(eligible_ids) - len(preflight),
        "ChangedOrNew": len(preflight),
        "Written": len(preflight) if write else 0,
        "OutputDirectory": str(target),
    }


def discover_seasons(repo_root: Path) -> list[int]:
    root = repo_root / DATA_DERIVED_ROOT / "nfl-games"
    seasons = sorted(int(path.stem) for path in root.glob("[12][0-9][0-9][0-9].json"))
    if not seasons:
        raise ValueError("No canonical published NFL Games season indices")
    return seasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-root", type=Path, help="Test-only alternate Derived output root")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--season", type=int, action="append")
    group.add_argument("--current-season", action="store_true")
    group.add_argument("--all-seasons", action="store_true")
    group.add_argument("--historical-seasons", action="store_true")
    group.add_argument("--historical-v2-upgrade-needed", action="store_true",
                       help="Read-only fast check for older stored GameDetail schemas")
    parser.add_argument("--write", action="store_true", help="Opt-in to per-GameID Derived writes")
    parser.add_argument("--check", action="store_true", help="Read-only; exit 3 when output differs")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    try:
        root = args.repo_root.resolve()
        if args.historical_v2_upgrade_needed:
            if args.write or args.check or args.out_root is not None:
                raise ValueError("Historical schema preflight is read-only and takes no output options")
            current = current_source_season(root)
            historical = [s for s in discover_seasons(root) if s < current]
            base = root / DATA_DERIVED_ROOT / "nfl-games" / "details"
            upgrade_needed = False
            for season in historical:
                files = sorted((base / str(season)).glob("*.json"))
                if not files or any(
                    _json(path).get("SchemaVersion") != 2 for path in files
                ):
                    upgrade_needed = True
                    break
            print("upgrade-needed" if upgrade_needed else "schema-current")
            return 0
        if args.season:
            seasons = sorted(set(args.season))
        elif args.current_season:
            seasons = [current_source_season(root)]
        else:
            seasons = discover_seasons(root)
            if args.historical_seasons:
                current = current_source_season(root)
                seasons = [s for s in seasons if s < current]
        if not seasons:
            raise ValueError("No eligible NFL seasons")
        # Accepted original PBP is downloaded/verified/replayed at most once per
        # season per invocation; preflight and write share identical evidence.
        pbp_store = AcceptedPBPSeasons(root)
        # Preflight all selected seasons; the writer is invoked only if all pass.
        audit = [plan_season(root, season, out_root=args.out_root, pbp_store=pbp_store)
                 for season in seasons]
        if args.write:
            results = [plan_season(root, season, out_root=args.out_root, write=True, pbp_store=pbp_store)
                       for season in seasons]
        else:
            results = audit
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"nfl_game_details_materialize failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"Product": "nfl-games/details", "Mode": "write" if args.write else "read-only",
                      "Results": results}, ensure_ascii=False, indent=2))
    return EXIT_DIFFERENT if args.check and any(x["ChangedOrNew"] for x in audit) else 0


if __name__ == "__main__":
    raise SystemExit(main())
