#!/usr/bin/env python3
"""Controlled historical TeamWeekPerformance materialization.

Read-only by default. Explicit --write persists only the verified target week.
No App publication or workflow schedule is performed here.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from data_roots import DATA_DERIVED_ROOT
from team_week_performance import (
    build_team_week_performance,
    output_path,
    save_team_week_performance,
)
from team_week_performance_sources import load_verified_week_inputs

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
    if pwf.get("ScoringProfile", {}).get("SettingsHash") != model["ScoringProfile"]["SettingsHash"]:
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


def materialize(
    repo_root: Path,
    league_id: str,
    season: int,
    week: int,
    *,
    write: bool = False,
    require_pwf: bool = False,
) -> dict[str, Any]:
    inputs = load_verified_week_inputs(repo_root, league_id, season, week)
    model = build_team_week_performance(**inputs)
    parity = verify_pwf_actual_parity(
        repo_root, model, inputs["matchup_rows"], require_pwf=require_pwf,
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
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--write", action="store_true",
                        help="Opt in to writing the verified Shared Derived partition")
    parser.add_argument("--require-pwf", action="store_true",
                        help="Fail closed when no PlayerWeekFantasy week snapshot is available")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    print(json.dumps(materialize(
        root, args.league, args.season, args.week,
        write=args.write, require_pwf=args.require_pwf,
    ), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
