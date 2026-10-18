"""Historical PlayerWeekFantasy batch adapter (Issue #471, first producer checkpoint).

Enumerates scored league weeks from canonical sources, checks independent NFL
finality, and delegates *all* calculations to the existing PWF materializer.
Read-only by default; an isolated --out-root is supported for restore tests.
No App publication, scheduler integration, or derived-data seed is used.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT, data_meta_dir
from league_metadata import list_league_ids, load_league_metadata, validate_against_manifest
from player_week_fantasy_materialize import (
    _week_finality,
    build_player_week_fantasy_dataset,
)


def discover_scored_weeks(
    repo_root: Path, *,
    league_id: str | None = None,
    seasons: Sequence[int] | None = None,
    weeks: Sequence[int] | None = None,
) -> list[tuple[str, int, int]]:
    """Source/metadata-discovered finalized-scoring candidates, not derived-file inventory."""
    selected_seasons, selected_weeks = set(seasons or ()), set(weeks or ())
    if any(type(s) is not int or s < 1 for s in selected_seasons):
        raise ValueError("Season filters must be positive integer years")
    if any(type(w) is not int or w < 1 for w in selected_weeks):
        raise ValueError("Week filters must be positive integers")
    ids = [league_id] if league_id is not None else list_league_ids(data_meta_dir(repo_root))
    if not ids:
        raise ValueError("No registered leagues for historical PWF discovery")
    targets: list[tuple[str, int, int]] = []
    found_seasons: set[int] = set()
    for current_id in sorted(ids):
        if not isinstance(current_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", current_id):
            raise ValueError(f"Invalid CanonicalLeagueID: {current_id!r}")
        manifest_path = repo_root / DATA_SOURCE_ROOT / "leagues" / current_id / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("Seasons"), list):
            raise ValueError(f"Invalid league manifest: {manifest_path}")
        metadata = load_league_metadata(current_id, data_meta_dir(repo_root))
        validate_against_manifest(metadata, manifest)
        years = [entry.get("Season") for entry in manifest["Seasons"] if isinstance(entry, dict)]
        if (not years or len(years) != len(manifest["Seasons"])
                or any(type(year) is not int or year < 1 for year in years)
                or len(set(years)) != len(years)):
            raise ValueError(f"Invalid season inventory: {manifest_path}")
        for year in sorted(years):
            if selected_seasons and year not in selected_seasons:
                continue
            found_seasons.add(year)
            league_path = (repo_root / DATA_SOURCE_ROOT / "leagues" / current_id
                           / "seasons" / str(year) / "league.json")
            league = json.loads(league_path.read_text(encoding="utf-8"))
            bounds = league.get("WeekStructure") if isinstance(league, dict) else None
            if not isinstance(bounds, dict) or bounds.get("Season") != year:
                raise ValueError(f"Missing season-specific WeekStructure: {league_path}")
            first, ceiling, scored = (bounds.get("StartWeek"),
                                      bounds.get("ExpectedLastLeagueWeek"),
                                      bounds.get("LastScoredLeg"))
            if (any(type(value) is not int for value in (first, ceiling, scored))
                    or not 1 <= first <= ceiling <= 25 or not 0 <= scored <= ceiling):
                raise ValueError(f"Invalid league scored-week bounds: {league_path}")
            targets.extend((current_id, year, week)
                           for week in range(first, scored + 1)
                           if not selected_weeks or week in selected_weeks)
    if selected_seasons - found_seasons:
        raise ValueError(f"Unknown requested seasons: {sorted(selected_seasons - found_seasons)}")
    if selected_weeks and not targets:
        raise ValueError("No scored league weeks matched the requested week filters")
    return targets


def _serialized(payload: dict[str, Any]) -> str:
    """Same bytes as player_week_fantasy_materialize.write_dataset."""
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def materialize_historical(
    repo_root: Path, *,
    league_id: str | None = None,
    seasons: Sequence[int] | None = None,
    weeks: Sequence[int] | None = None,
    out_root: Path | None = None,
    write: bool = False,
) -> dict[str, Any]:
    """Preflight all requested weeks; any blocked week prevents *all* writes."""
    root = repo_root.resolve()
    output_root = (out_root or (root / DATA_DERIVED_ROOT)).resolve()
    targets = discover_scored_weeks(root, league_id=league_id, seasons=seasons, weeks=weeks)
    staged: list[tuple[Path, str, dict[str, Any]]] = []
    entries: list[dict[str, Any]] = []
    for current_id, year, week in targets:
        entry: dict[str, Any] = {"CanonicalLeagueID": current_id, "Season": year, "Week": week}
        entries.append(entry)
        try:
            complete, games = _week_finality(root, season=year, week=week)
            if complete is not True or not games:
                raise ValueError("NFL regular-season week is not final")
            payload = build_player_week_fantasy_dataset(
                root, league_id=current_id, season=year, week=week,
            )
            metadata = payload.get("Materialization")
            if (not isinstance(metadata, dict)
                    or metadata.get("ActualScoringEvidenceFinalized") is not True
                    or metadata.get("TargetRosterProvisional") is not False
                    or not isinstance(payload.get("Records"), list)
                    or not payload["Records"]):
                raise ValueError("Final player scoring or target-week roster evidence incomplete")
            target = output_root / "player-week-fantasy" / current_id / str(year) / f"{week:02d}.json"
            serialized = _serialized(payload)
            changed = not target.is_file() or target.read_text(encoding="utf-8") != serialized
            entry.update(Status="ready", Path=str(target), Changed=changed,
                         RecordCount=len(payload["Records"]),
                         ActualStates=metadata["ActualStateCounts"])
            staged.append((target, serialized, entry))
        except (ValueError, KeyError, OSError, TypeError) as error:
            entry.update(Status="blocked", Reason=str(error))
    blocked = sum(entry["Status"] == "blocked" for entry in entries)
    changed = sum(bool(entry["Changed"]) for entry in entries if entry["Status"] == "ready")
    if write and not blocked:
        for target, serialized, entry in staged:
            if entry["Changed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(serialized, encoding="utf-8")
    return {
        "Mode": "historical-pwf", "WriteRequested": write,
        "WriteAborted": bool(write and blocked), "TargetCount": len(targets),
        "ReadyCount": len(targets) - blocked, "BlockedCount": blocked,
        "ChangedCount" if write and not blocked else "WouldChangeCount": changed,
        "Weeks": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league")
    parser.add_argument("--season", type=int, action="append")
    parser.add_argument("--week", type=int, action="append")
    parser.add_argument("--out-root", type=Path, help="Explicit isolated derived output root")
    parser.add_argument("--write", action="store_true", help="Opt-in: write only after all selected weeks pass")
    args = parser.parse_args(argv)
    try:
        report = materialize_historical(
            args.repo_root, league_id=args.league, seasons=args.season,
            weeks=args.week, out_root=args.out_root, write=args.write,
        )
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(2, f"historical PWF discovery failed: {error}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 2 if report["BlockedCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
