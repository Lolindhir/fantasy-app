#!/usr/bin/env python3
"""Validate historical League PlayerPoints against the canonical historical scorer."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from historical_fantasy_scoring import (
    SPECIAL_TEAMS_EVENT_SCORING_KEYS,
    league_season_path,
    number,
    read_json,
    score_record,
)


def _player_points_for_week(repo_root: Path, league_id: str, season: int, week: int) -> dict[str, float]:
    path = (
        repo_root
        / "source-data/leagues"
        / league_id
        / "seasons"
        / str(season)
        / "matchups"
        / f"week-{week}.json"
    )
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Canonical League matchup payload must be an array: {path}")

    points: dict[str, float] = {}
    for matchup in payload:
        if not isinstance(matchup, dict):
            raise ValueError(f"Canonical League matchup contains a non-object row: {path}")
        rows = matchup.get("PlayerPoints")
        if not isinstance(rows, list):
            raise ValueError(f"Canonical League matchup has no PlayerPoints array: {path}")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("Player"), dict):
                raise ValueError(f"Canonical League PlayerPoints row is invalid: {path}")
            player_id = row["Player"].get("CanonicalPlayerID")
            if not isinstance(player_id, str) or not player_id:
                raise ValueError(f"Canonical League PlayerPoints row has no CanonicalPlayerID: {path}")
            value = number(row.get("Points"))
            if player_id in points and points[player_id] != value:
                raise ValueError(
                    f"Conflicting League PlayerPoints for {player_id} in {season}/W{week}"
                )
            points[player_id] = value
    return points


def _player_stats_for_week(repo_root: Path, season: int, week: int) -> dict[str, dict[str, Any]]:
    path = repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
    payload = read_json(path)
    rows = payload.get("Records") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"Canonical player-stats payload has no Records array: {path}")

    by_player: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical player-stats contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            continue
        if player_id in by_player:
            raise ValueError(f"Duplicate canonical player-stat record for {player_id} in {season}/W{week}")
        by_player[player_id] = row
    return by_player


def _special_teams_events_for_week(
    repo_root: Path,
    season: int,
    week: int,
) -> dict[str, list[dict[str, Any]]]:
    path = repo_root / "source-data/nfl/special-teams-fumble-events" / str(season) / f"{week:02d}.json"
    if not path.exists():
        raise ValueError(
            "Canonical special-teams fumble evidence is missing; parity cannot assume zero: "
            f"{path}"
        )
    payload = read_json(path)
    if not isinstance(payload, dict) or payload.get("Finalized") is not True:
        raise ValueError(
            "Canonical special-teams fumble evidence is not finalized; parity cannot assume zero: "
            f"{path}"
        )
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise ValueError(f"Canonical special-teams fumble evidence has no Records array: {path}")

    by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical special-teams fumble evidence contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError(f"Canonical special-teams fumble event has no CanonicalPlayerID: {path}")
        by_player[player_id].append(row)
    return dict(by_player)


def build_parity_report(
    repo_root: Path,
    *,
    league_id: str,
    nfl_season: int,
    scoring_season: int,
    first_week: int,
    last_week: int,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    profile = read_json(league_season_path(repo_root, league_id, scoring_season))
    scoring = profile.get("ScoringSettings") if isinstance(profile, dict) else None
    if not isinstance(scoring, dict):
        raise ValueError("Selected League season has no ScoringSettings")

    active_event_keys = {
        key for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS if number(scoring.get(key)) != 0
    }
    compared = 0
    exact = 0
    skipped_zero_without_stats = 0
    missing_nonzero_stats: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []

    for week in range(first_week, last_week + 1):
        league_points = _player_points_for_week(repo_root, league_id, nfl_season, week)
        player_stats = _player_stats_for_week(repo_root, nfl_season, week)
        events_by_player = (
            _special_teams_events_for_week(repo_root, nfl_season, week)
            if active_event_keys
            else {}
        )

        for player_id, actual in sorted(league_points.items()):
            record = player_stats.get(player_id)
            if record is None:
                if abs(actual) <= tolerance:
                    skipped_zero_without_stats += 1
                    continue
                missing_nonzero_stats.append(
                    {
                        "CanonicalPlayerID": player_id,
                        "Week": week,
                        "LeaguePoints": actual,
                    }
                )
                continue

            compared += 1
            result = score_record(
                record,
                scoring,
                special_teams_fumble_events=events_by_player.get(player_id, [])
                if active_event_keys
                else None,
            )
            if result["UnsupportedNonZeroSettings"]:
                unsupported.append(
                    {
                        "CanonicalPlayerID": player_id,
                        "Week": week,
                        "Settings": result["UnsupportedNonZeroSettings"],
                    }
                )
                continue

            derived = float(result["FantasyPoints"])
            difference = derived - actual
            if abs(difference) <= tolerance:
                exact += 1
                continue
            mismatches.append(
                {
                    "CanonicalPlayerID": player_id,
                    "PlayerName": record.get("PlayerName"),
                    "Position": record.get("Position"),
                    "Week": week,
                    "DerivedPoints": round(derived, 6),
                    "LeaguePoints": actual,
                    "Difference": round(difference, 6),
                }
            )

    return {
        "League": league_id,
        "NFLSeason": nfl_season,
        "ScoringSeason": scoring_season,
        "FirstWeek": first_week,
        "LastWeek": last_week,
        "Tolerance": tolerance,
        "ComparedPlayerWeeks": compared,
        "ExactPlayerWeeks": exact,
        "SkippedZeroPlayerWeeksWithoutCanonicalStats": skipped_zero_without_stats,
        "MissingNonZeroCanonicalStats": missing_nonzero_stats,
        "UnsupportedPlayerWeeks": unsupported,
        "Mismatches": mismatches,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--nfl-season", type=int, required=True)
    parser.add_argument("--scoring-season", type=int, required=True)
    parser.add_argument("--first-week", type=int, default=1)
    parser.add_argument("--last-week", type=int, required=True)
    parser.add_argument("--tolerance", type=float, default=0.01)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_parity_report(
        args.repo_root.resolve(),
        league_id=args.league,
        nfl_season=args.nfl_season,
        scoring_season=args.scoring_season,
        first_week=args.first_week,
        last_week=args.last_week,
        tolerance=args.tolerance,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
