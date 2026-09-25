#!/usr/bin/env python3
"""Leak-free walk-forward backtest for historical player projections."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from historical_fantasy_scoring import (
    SPECIAL_TEAMS_EVENT_SCORING_KEYS,
    league_season_path,
    number,
    read_json,
    score_record,
)

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "K"}


def _require_finalized_partition(path: Path, season: int, week: int) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Required canonical partition is missing: {path}")
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Canonical partition must be an object: {path}")
    if payload.get("Season") != season or payload.get("Week") != week:
        raise ValueError(f"Canonical partition has season/week mismatch: {path}")
    if payload.get("Finalized") is not True:
        raise ValueError(f"Canonical partition is not finalized: {path}")
    return payload


def _scoring_profile(repo_root: Path, league_id: str, scoring_season: int) -> dict[str, Any]:
    payload = read_json(league_season_path(repo_root, league_id, scoring_season))
    scoring = payload.get("ScoringSettings") if isinstance(payload, dict) else None
    if not isinstance(scoring, dict):
        raise ValueError("Selected League season has no ScoringSettings")
    return scoring


def _snap_totals_by_player(
    repo_root: Path,
    season: int,
    week: int,
) -> dict[str, dict[str, float]]:
    path = repo_root / "source-data/nfl/snap-counts" / str(season) / f"{week:02d}.json"
    payload = _require_finalized_partition(path, season, week)
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise ValueError(f"Canonical snap-count partition has no Records array: {path}")

    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"OffenseSnaps": 0.0, "SpecialTeamsSnaps": 0.0}
    )
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical snap-count partition contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            continue
        totals[player_id]["OffenseSnaps"] += number(row.get("OffenseSnaps"))
        totals[player_id]["SpecialTeamsSnaps"] += number(row.get("SpecialTeamsSnaps"))
    return dict(totals)


def _events_by_player(
    repo_root: Path,
    season: int,
    week: int,
) -> dict[str, list[dict[str, Any]]]:
    path = (
        repo_root
        / "source-data/nfl/special-teams-fumble-events"
        / str(season)
        / f"{week:02d}.json"
    )
    payload = _require_finalized_partition(path, season, week)
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise ValueError(f"Canonical special-teams event partition has no Records array: {path}")

    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical special-teams event partition contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError(f"Canonical special-teams event has no CanonicalPlayerID: {path}")
        events[player_id].append(row)
    return dict(events)


def _played(position: str, snaps: dict[str, float]) -> bool:
    if position == "K":
        return snaps["SpecialTeamsSnaps"] > 0
    return snaps["OffenseSnaps"] > 0


def build_scored_played_games(
    repo_root: Path,
    *,
    season: int,
    scoring: dict[str, Any],
    first_week: int = 1,
    last_week: int = 18,
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, Any]]:
    active_event_keys = {
        key for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS if number(scoring.get(key)) != 0
    }
    observations: dict[int, list[dict[str, Any]]] = {}
    missing_participation: list[dict[str, Any]] = []
    excluded_nonparticipation = 0
    relevant_stat_records = 0

    for week in range(first_week, last_week + 1):
        stats_path = repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
        stats_payload = _require_finalized_partition(stats_path, season, week)
        stat_rows = stats_payload.get("Records")
        if not isinstance(stat_rows, list):
            raise ValueError(f"Canonical player-stats partition has no Records array: {stats_path}")

        snap_by_player = _snap_totals_by_player(repo_root, season, week)
        events_by_player = _events_by_player(repo_root, season, week) if active_event_keys else {}

        week_observations: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in stat_rows:
            if not isinstance(record, dict):
                raise ValueError(f"Canonical player-stats contains a non-object row: {stats_path}")
            position = str(record.get("Position") or "").upper()
            if position not in FANTASY_POSITIONS:
                continue
            relevant_stat_records += 1
            player_id = record.get("CanonicalPlayerID")
            if not isinstance(player_id, str) or not player_id:
                raise ValueError(
                    f"Fantasy-relevant canonical player-stat record has no CanonicalPlayerID: "
                    f"{season}/W{week}"
                )
            if player_id in seen:
                raise ValueError(f"Duplicate canonical player-stat record for {player_id} in {season}/W{week}")
            seen.add(player_id)

            snaps = snap_by_player.get(player_id)
            if snaps is None:
                missing_participation.append(
                    {
                        "Season": season,
                        "Week": week,
                        "CanonicalPlayerID": player_id,
                        "PlayerName": record.get("PlayerName"),
                        "Position": position,
                    }
                )
                continue
            if not _played(position, snaps):
                excluded_nonparticipation += 1
                continue

            result = score_record(
                record,
                scoring,
                special_teams_fumble_events=events_by_player.get(player_id, [])
                if active_event_keys
                else None,
            )
            if result["UnsupportedNonZeroSettings"]:
                raise ValueError(
                    f"Historical scoring profile has unsupported active player settings for "
                    f"{player_id} in {season}/W{week}: {result['UnsupportedNonZeroSettings']}"
                )
            week_observations.append(
                {
                    "Season": season,
                    "Week": week,
                    "CanonicalPlayerID": player_id,
                    "PlayerName": record.get("PlayerName"),
                    "Position": position,
                    "FantasyPoints": float(result["FantasyPoints"]),
                    "OffenseSnaps": snaps["OffenseSnaps"],
                    "SpecialTeamsSnaps": snaps["SpecialTeamsSnaps"],
                }
            )
        observations[week] = week_observations

    audit = {
        "Season": season,
        "RelevantCanonicalStatRecords": relevant_stat_records,
        "PlayedGameObservations": sum(len(rows) for rows in observations.values()),
        "ExcludedNoConfirmedParticipation": excluded_nonparticipation,
        "MissingParticipationEvidenceCount": len(missing_participation),
        "MissingParticipationEvidence": missing_participation,
    }
    return observations, audit


def _metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    if not materialized:
        return {
            "Count": 0,
            "MAE": None,
            "RMSE": None,
            "Bias": None,
            "MeanProjection": None,
            "MeanActual": None,
        }
    errors = [float(row["Projection"]) - float(row["Actual"]) for row in materialized]
    abs_errors = [abs(value) for value in errors]
    squared_errors = [value * value for value in errors]
    return {
        "Count": len(materialized),
        "MAE": round(sum(abs_errors) / len(abs_errors), 4),
        "RMSE": round(math.sqrt(sum(squared_errors) / len(squared_errors)), 4),
        "Bias": round(sum(errors) / len(errors), 4),
        "MeanProjection": round(
            sum(float(row["Projection"]) for row in materialized) / len(materialized),
            4,
        ),
        "MeanActual": round(
            sum(float(row["Actual"]) for row in materialized) / len(materialized),
            4,
        ),
    }


def walk_forward_v1(
    observations_by_week: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    history: dict[str, list[float]] = defaultdict(list)
    predictions: list[dict[str, Any]] = []
    cold_starts: list[dict[str, Any]] = []

    for week in sorted(observations_by_week):
        current = observations_by_week[week]

        # Prediction happens before the current week's outcomes enter history.
        for observation in current:
            player_id = observation["CanonicalPlayerID"]
            prior = history.get(player_id, [])
            if not prior:
                cold_starts.append(
                    {
                        "Season": observation["Season"],
                        "Week": week,
                        "CanonicalPlayerID": player_id,
                        "PlayerName": observation.get("PlayerName"),
                        "Position": observation["Position"],
                        "Reason": "no-prior-confirmed-played-game",
                    }
                )
                continue
            projection = sum(prior) / len(prior)
            actual = float(observation["FantasyPoints"])
            predictions.append(
                {
                    "Season": observation["Season"],
                    "Week": week,
                    "CanonicalPlayerID": player_id,
                    "PlayerName": observation.get("PlayerName"),
                    "Position": observation["Position"],
                    "PriorGames": len(prior),
                    "Projection": projection,
                    "Actual": actual,
                    "Error": projection - actual,
                    "AbsoluteError": abs(projection - actual),
                }
            )

        # Only after all predictions for week W are fixed may week W enter state.
        for observation in current:
            history[observation["CanonicalPlayerID"]].append(
                float(observation["FantasyPoints"])
            )

    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_prior_games: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        by_position[row["Position"]].append(row)
        by_week[int(row["Week"])].append(row)
        by_prior_games[int(row["PriorGames"])].append(row)

    return {
        "Model": "v1-current-season-ppg",
        "LeakageRule": "projection for week W uses only confirmed played-game outcomes from weeks < W",
        "PredictionCount": len(predictions),
        "ColdStartCount": len(cold_starts),
        "Metrics": _metrics(predictions),
        "ByPosition": {
            key: _metrics(rows) for key, rows in sorted(by_position.items())
        },
        "ByWeek": {
            str(key): _metrics(rows) for key, rows in sorted(by_week.items())
        },
        "ByPriorGames": {
            str(key): _metrics(rows) for key, rows in sorted(by_prior_games.items())
        },
        "LargestAbsoluteErrors": sorted(
            predictions,
            key=lambda row: (-float(row["AbsoluteError"]), row["Season"], row["Week"], row["CanonicalPlayerID"]),
        )[:20],
        "ColdStarts": cold_starts,
    }


def build_v1_backtest_report(
    repo_root: Path,
    *,
    league_id: str,
    scoring_season: int,
    seasons: list[int],
    first_week: int = 1,
    last_week: int = 18,
) -> dict[str, Any]:
    scoring = _scoring_profile(repo_root, league_id, scoring_season)
    season_reports: list[dict[str, Any]] = []
    combined_predictions: list[dict[str, Any]] = []

    for season in seasons:
        observations, observation_audit = build_scored_played_games(
            repo_root,
            season=season,
            scoring=scoring,
            first_week=first_week,
            last_week=last_week,
        )
        report = walk_forward_v1(observations)
        # Keep seasons independent: V1 is current-season PPG and state resets in Week 1.
        season_reports.append(
            {
                "Season": season,
                "ObservationAudit": observation_audit,
                **report,
            }
        )
        for week_rows in observations.values():
            pass

        # Reconstruct prediction rows only for combined aggregate without carrying history across seasons.
        history: dict[str, list[float]] = defaultdict(list)
        for week in sorted(observations):
            for observation in observations[week]:
                prior = history.get(observation["CanonicalPlayerID"], [])
                if prior:
                    projection = sum(prior) / len(prior)
                    actual = float(observation["FantasyPoints"])
                    combined_predictions.append(
                        {
                            "Season": season,
                            "Week": week,
                            "CanonicalPlayerID": observation["CanonicalPlayerID"],
                            "Position": observation["Position"],
                            "PriorGames": len(prior),
                            "Projection": projection,
                            "Actual": actual,
                        }
                    )
            for observation in observations[week]:
                history[observation["CanonicalPlayerID"]].append(
                    float(observation["FantasyPoints"])
                )

    combined_by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    combined_by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    combined_by_prior_games: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in combined_predictions:
        combined_by_position[row["Position"]].append(row)
        combined_by_week[int(row["Week"])].append(row)
        combined_by_prior_games[int(row["PriorGames"])].append(row)

    return {
        "ContractVersion": 1,
        "League": league_id,
        "ScoringSeason": scoring_season,
        "Seasons": seasons,
        "FirstWeek": first_week,
        "LastWeek": last_week,
        "TargetPositions": sorted(FANTASY_POSITIONS),
        "ParticipationRule": {
            "QB/RB/WR/TE/FB": "OffenseSnaps > 0",
            "K": "SpecialTeamsSnaps > 0",
            "MissingSnapEvidence": "unknown/excluded, never zero",
        },
        "ColdStartRule": "no V1 projection until the player has at least one prior confirmed played game in the same season",
        "ByeDnpRule": "weeks without confirmed position-appropriate participation are not player-game observations",
        "InjuryRule": "no explicit injury adjustment in V1",
        "LeakageRule": "target-week outcome/participation may define evaluation membership but never enters the projection; only weeks < W feed CurrentSeasonPPG",
        "SeasonStateRule": "history resets at the start of every season",
        "Combined": {
            "PredictionCount": len(combined_predictions),
            "Metrics": _metrics(combined_predictions),
            "ByPosition": {
                key: _metrics(rows) for key, rows in sorted(combined_by_position.items())
            },
            "ByWeek": {
                str(key): _metrics(rows) for key, rows in sorted(combined_by_week.items())
            },
            "ByPriorGames": {
                str(key): _metrics(rows) for key, rows in sorted(combined_by_prior_games.items())
            },
        },
        "SeasonReports": season_reports,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--scoring-season", type=int, default=2025)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--first-week", type=int, default=1)
    parser.add_argument("--last-week", type=int, default=18)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_v1_backtest_report(
        args.repo_root.resolve(),
        league_id=args.league,
        scoring_season=args.scoring_season,
        seasons=args.seasons,
        first_week=args.first_week,
        last_week=args.last_week,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
