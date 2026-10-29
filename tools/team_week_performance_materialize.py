#!/usr/bin/env python3
"""Controlled historical TeamWeekPerformance materialization.

Read-only by default. Single-week and all-finalized batch modes use the same
canonical league source, scoring and finality gates. Strict PWF parity is an optional audit. Batch writes preflight
all selected weeks before touching derived output. No App/workflow publication.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT, data_meta_dir
from league_metadata import (list_league_ids, load_league_metadata, validate_against_manifest)
from team_week_performance import (
    build_team_week_performance,
    output_path,
    save_team_week_performance,
)
from derived_data_lib.week_finality import resolve_week_finality
from team_week_performance_sources import load_verified_week_inputs, _league_source
from player_scoring_reconciliation import reconcile


def verify_pwf_actual_parity(
    repo_root: Path,
    model: Mapping[str, Any],
    matchup_rows: list[dict[str, Any]],
    *,
    require_pwf: bool = False,
) -> dict[str, Any]:
    """Shared one-player reconciliation is the single parity decision owner.

    This preserves the existing compact TWP validation result, while making
    every compared League/PWF point and narrowly accepted exception available
    through player_scoring_reconciliation.reconcile().
    """
    report = reconcile(
        repo_root, model, matchup_rows, require_pwf=require_pwf,
    )
    if report["Errors"]:
        raise ValueError(report["Errors"][0])
    result = {
        "State": report["State"],
        "Compared": report["Compared"],
        "MissingZeroPoints": report["MissingZeroPoints"],
    }
    if report["AcceptedDivergences"]:
        result["AcceptedDivergences"] = report["AcceptedDivergences"]
    return result


def _checked_week(
    repo_root: Path, league_id: str, season: int, week: int, *,
    require_pwf: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single owner for canonical input, calculation and optional PWF parity."""
    inputs = load_verified_week_inputs(repo_root, league_id, season, week)
    model = build_team_week_performance(**inputs)
    try:
        parity = verify_pwf_actual_parity(
            repo_root, model, inputs["matchup_rows"], require_pwf=require_pwf,
        )
    except ValueError as error:
        if require_pwf:
            raise  # Explicit strict audit still fails on PWF scoring discrepancies.
        # League/Sleeper PlayerPoints own official awards. An independently
        # calculated NFL score must not veto a valid league-scored week.
        parity = {"State": "mismatch", "Reason": str(error)}
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
            # LeagueScoredWeek (ADR-071): games final and league scored, gapless.
            scored = resolve_week_finality(repo_root, current_id, year)["LeagueScoredWeek"]
            targets.extend(
                (current_id, year, week)
                for week in range(first, scored + 1)
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

    A complete empty data-derived directory is supported. Normal official
    award publication reports PWF differences without blocking valid league
    evidence; --require-pwf retains strict, independently invoked auditing.
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
                        help="Strict PWF auditing: require final PlayerWeekFantasy and exact validated scoring parity")
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
