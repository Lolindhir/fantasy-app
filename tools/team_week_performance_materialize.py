#!/usr/bin/env python3
"""Controlled historical TeamWeekPerformance materialization.

Read-only by default. Single-week and all-finalized batch modes use the same
canonical source, scoring, finality and parity gates. Batch writes preflight
all selected weeks before touching derived output. No App/workflow publication.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT, data_meta_dir
from league_metadata import (list_league_ids, load_league_metadata, validate_against_manifest)
from team_week_performance import (
    build_team_week_performance,
    output_path,
    save_team_week_performance,
)
from team_week_performance_sources import load_verified_week_inputs, _league_source

PARITY_TOLERANCE = Decimal("0.010001")


def _value(value: Any, label: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Missing or invalid {label}")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if not number.is_finite():
        raise ValueError(f"Non-finite {label}")
    return number


def verify_pwf_actual_parity(
    repo_root: Path,
    model: Mapping[str, Any],
    matchup_rows: list[dict[str, Any]],
    *,
    require_pwf: bool = False,
) -> dict[str, Any]:
    """Compare canonical week matchup points with persisted final PWF Actuals.

    PWF's weekly NFL roster population differs from the fantasy ownership
    population. A missing zero-point roster candidate is acceptable; a
    missing nonzero scorer, stale non-final row, contradictory score, stale
    scoring fingerprint or duplicate ID fails the materialization gate.
    """
    season, week = model["Season"], model["Week"]
    path = (repo_root / DATA_DERIVED_ROOT / "player-week-fantasy"
            / model["CanonicalLeagueID"] / str(season) / f"{week:02d}.json")
    if not path.is_file():
        if require_pwf:
            raise ValueError(f"Required PlayerWeekFantasy parity source is missing: {path}")
        return {"State": "not-available", "Compared": 0, "MissingZeroPoints": 0}

    try:
        pwf = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid PlayerWeekFantasy parity source: {path}") from exc
    if not isinstance(pwf, dict):
        raise ValueError("PlayerWeekFantasy snapshot must be an object")
    if any(pwf.get(key) != model[key]
           for key in ("CanonicalLeagueID", "Season", "Week")):
        raise ValueError("PlayerWeekFantasy league/season/week mismatch")
    profile = pwf.get("ScoringProfile")
    if not isinstance(profile, dict) or profile.get("SettingsHash") != model["ScoringProfile"]["SettingsHash"]:
        raise ValueError("PlayerWeekFantasy scoring fingerprint mismatch")

    rows = pwf.get("Records")
    if not isinstance(rows, list):
        raise ValueError("PlayerWeekFantasy has no Records array")
    records: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid PlayerWeekFantasy record")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id or player_id in records:
            raise ValueError("Missing or duplicate PlayerWeekFantasy player identity")
        records[player_id] = row

    compared, zero_missing = 0, 0
    seen_matchups: set[str] = set()
    for team in matchup_rows:
        player_points = team.get("PlayerPoints")
        if not isinstance(player_points, list):
            raise ValueError("Missing canonical matchup PlayerPoints")
        for row in player_points:
            if not isinstance(row, dict) or not isinstance(row.get("Player"), dict):
                raise ValueError("Invalid canonical matchup PlayerPoints reference")
            player_id = row["Player"].get("CanonicalPlayerID")
            if not isinstance(player_id, str) or not player_id or player_id in seen_matchups:
                raise ValueError("Missing or duplicate canonical matchup player identity")
            seen_matchups.add(player_id)
            league_points = _value(row.get("Points"), f"matchup {player_id}")
            record = records.get(player_id)
            if record is None:
                if league_points != 0:
                    raise ValueError(f"PlayerWeekFantasy is missing nonzero scorer {player_id}")
                zero_missing += 1
                continue
            actual = record.get("Actual")
            if not isinstance(actual, dict) or actual.get("State") != "final":
                raise ValueError(f"PlayerWeekFantasy Actual is not final for {player_id}")
            materialized = _value(actual.get("Points"), f"PWF {player_id}")
            if abs(materialized - league_points) > PARITY_TOLERANCE:
                raise ValueError(f"PlayerWeekFantasy scoring mismatch for {player_id}: "
                                 f"league={league_points}, pwf={materialized}")
            compared += 1
    return {"State": "verified", "Compared": compared, "MissingZeroPoints": zero_missing}


def _checked_week(
    repo_root: Path, league_id: str, season: int, week: int, *,
    require_pwf: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single owner for canonical input, calculation and optional PWF parity."""
    inputs = load_verified_week_inputs(repo_root, league_id, season, week)
    model = build_team_week_performance(**inputs)
    parity = verify_pwf_actual_parity(
        repo_root, model, inputs["matchup_rows"], require_pwf=require_pwf,
    )
    return model, parity


def discover_finalized_weeks(
    repo_root: Path, *,
    league_id: str | None = None,
    seasons: Sequence[int] | None = None,
) -> list[tuple[str, int, int]]:
    """Enumerate all finalized fantasy weeks using league manifests and facts.

    Discovery never consults App readmodels or existing derived partitions.
    NFL week finality is independently checked per week by _checked_week().
    """
    metadata_root = data_meta_dir(repo_root)
    ids = [league_id] if league_id is not None else list_league_ids(metadata_root)
    if not ids:
        raise ValueError("No registered leagues found for historical materialization")
    requested = set(seasons or ())
    if any(type(s) is not int or s < 1 for s in requested):
        raise ValueError("Season filter must contain positive integer years")
    targets: list[tuple[str, int, int]] = []
    found_seasons: set[int] = set()
    for current_id in sorted(ids):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", current_id):
            raise ValueError(f"Invalid CanonicalLeagueID: {current_id!r}")
        metadata = load_league_metadata(current_id, metadata_root)
        manifest_path = (
            repo_root / DATA_SOURCE_ROOT / "leagues" / current_id / "manifest.json"
        )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Missing or invalid canonical league manifest: {manifest_path}") from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("Seasons"), list):
            raise ValueError(f"Invalid league season manifest: {manifest_path}")
        validate_against_manifest(metadata, manifest)
        years = [item.get("Season") for item in manifest["Seasons"]
                 if isinstance(item, dict)]
        if len(years) != len(manifest["Seasons"]) or any(
            type(year) is not int or year < 1 for year in years
        ) or len(set(years)) != len(years) or not years:
            raise ValueError(f"Invalid or duplicate league season in {manifest_path}")
        for year in sorted(years):
            if requested and year not in requested:
                continue
            found_seasons.add(year)
            _, league = _league_source(repo_root, current_id, year)
            bounds = league.get("WeekStructure")
            if not isinstance(bounds, dict) or bounds.get("Season") != year:
                raise ValueError(f"Invalid historical WeekStructure for {current_id}/{year}")
            first, ceiling, last_scored = (
                bounds.get("StartWeek"), bounds.get("ExpectedLastLeagueWeek"),
                bounds.get("LastScoredLeg"),
            )
            if any(type(value) is not int for value in (first, ceiling, last_scored)):
                raise ValueError(f"Missing final-week bounds for {current_id}/{year}")
            if not (1 <= first <= ceiling <= 25 and 0 <= last_scored <= ceiling):
                raise ValueError(f"Invalid finalized-week bounds for {current_id}/{year}")
            targets.extend(
                (current_id, year, week)
                for week in range(first, last_scored + 1)
            )
    missing = requested - found_seasons
    if missing:
        raise ValueError(f"Requested seasons do not exist in selected league manifests: {sorted(missing)}")
    return targets


def materialize_all_finalized(
    repo_root: Path, *,
    league_id: str | None = None,
    seasons: Sequence[int] | None = None,
    write: bool = False,
    require_pwf: bool = False,
) -> dict[str, Any]:
    """Audit every scored week; publish nothing when a preflight gate fails.

    A complete empty data-derived directory is supported: a missing PWF file
    yields an explicitly unverified parity state unless --require-pwf is set.
    The later cross-product orchestrator will rebuild PWF first.
    """
    targets = discover_finalized_weeks(repo_root, league_id=league_id, seasons=seasons)
    checked: list[tuple[dict[str, Any], dict[str, Any]]] = []
    entries: list[dict[str, Any]] = []
    for current_id, season, week in targets:
        entry: dict[str, Any] = {
            "CanonicalLeagueID": current_id, "Season": season, "Week": week,
        }
        try:
            model, parity = _checked_week(
                repo_root, current_id, season, week, require_pwf=require_pwf,
            )
        except ValueError as exc:
            entry.update(Status="blocked", Reason=str(exc))
        else:
            entry.update(
                Status="ready", TeamCount=len(model["Teams"]),
                Path=output_path(repo_root, model).relative_to(repo_root).as_posix(),
                PlayerWeekFantasyParity=parity,
            )
            checked.append((model, entry))
        entries.append(entry)
    blocked = len(entries) - len(checked)
    # Preflight means the caller never obtains a partial materialization from a
    # known invalid week, even if earlier seasons/weeks were valid.
    changed = 0
    if write and not blocked:
        for model, entry in checked:
            was_changed = save_team_week_performance(repo_root, model)
            entry["Changed"] = was_changed
            changed += int(was_changed)
    return {
        "Mode": "all-finalized", "WriteRequested": write,
        "WriteAborted": bool(write and blocked), "TargetCount": len(targets),
        "ReadyCount": len(checked), "BlockedCount": blocked,
        "ChangedCount": changed, "Weeks": entries,
    }


def materialize(
    repo_root: Path,
    league_id: str,
    season: int,
    week: int,
    *,
    write: bool = False,
    require_pwf: bool = False,
) -> dict[str, Any]:
    model, parity = _checked_week(
        repo_root, league_id, season, week, require_pwf=require_pwf,
    )
    target = output_path(repo_root, model)
    changed = save_team_week_performance(repo_root, model) if write else False
    return {
        "Path": target.relative_to(repo_root).as_posix(),
        "Written": write,
        "Changed": changed,
        "Season": season,
        "Week": week,
        "TeamCount": len(model["Teams"]),
        "BestManagerRosterIDs": model["Awards"]["BestManagerRosterIDs"],
        "BestCoachRosterIDs": model["Awards"]["BestCoachRosterIDs"],
        "ScoringSettingsHash": model["ScoringProfile"]["SettingsHash"],
        "LineupDefinitionHash": model["LineupDefinitionHash"],
        "PlayerWeekFantasyParity": parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", help="CanonicalLeagueID; all registered leagues in batch mode by default")
    parser.add_argument("--season", type=int, action="append",
                        help="Single target season, or repeat for selected batch seasons")
    parser.add_argument("--week", type=int, help="Week for single-week materialization")
    parser.add_argument("--all-finalized", action="store_true",
                        help="Rebuild every scored week from registered league manifests")
    parser.add_argument("--write", action="store_true",
                        help="Opt in to persisting verified Shared Derived partitions")
    parser.add_argument("--require-pwf", action="store_true",
                        help="Require a final PlayerWeekFantasy parity snapshot for every selected week")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    if args.all_finalized:
        if args.week is not None:
            parser.error("--week cannot be combined with --all-finalized")
        report = materialize_all_finalized(
            root, league_id=args.league, seasons=args.season,
            write=args.write, require_pwf=args.require_pwf,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 2 if report["BlockedCount"] else 0

    if args.week is None or not args.season or len(args.season) != 1:
        parser.error("Single-week mode requires exactly one --season and --week")
    print(json.dumps(materialize(
        root, args.league or "nfl-reise", args.season[0], args.week,
        write=args.write, require_pwf=args.require_pwf,
    ), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
