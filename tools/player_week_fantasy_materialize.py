#!/usr/bin/env python3
"""Materialize Shared-Derived PlayerWeekFantasy for one league/season/week."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from historical_fantasy_scoring import (
    SPECIAL_TEAMS_EVENT_SCORING_KEYS,
    league_season_path,
    number,
    read_json,
)
from historical_projection_backtest import FANTASY_POSITIONS, build_scored_played_games
from historical_projection_interval_calibration import (
    MIN_GROUP_SIZE,
    STRATEGY_POSITION_PROJECTION_VOLATILITY,
    _enrich_volatility,
    _interval_for_row,
    _population_std,
    _projection_thresholds,
    _residual_groups,
    _volatility_thresholds,
    build_prior_score_volatility,
)
from historical_projection_v2_calibration import (
    _leave_one_player_out_mean,
    _season_position_aggregates,
)
from historical_projection_v3_calibration import (
    HISTORY_TWO_SEASON,
    _history_components,
    _player_baseline,
    _player_season_summaries,
)
from historical_projection_v4_calibration import (
    FEATURE_OPPORTUNITY,
    FEATURE_SNAP,
    HISTORY_DECAY,
    RECENT_WINDOW,
    VARIANT_COMBINED,
    _adjustment,
    _fallback_older_current_mean,
    _historical_usage_baseline,
    _opportunity_value,
    _position_group,
    _recent_mean,
    _usage_by_week,
    _usage_season_summaries,
    _v3_rows,
    build_v4_examples,
    evaluate_variant,
    fit_variant,
)
from player_week_fantasy import (
    PARTICIPATION_CONDITION,
    PRIMARY_INTERVAL_LEVEL,
    PUBLISHED_INTERVAL_LEVELS,
    build_player_week_fantasy_contract,
    build_scoring_profile_identity,
    derive_actual_points,
)

POINT_MODEL = "V4-C"
INTERVAL_MODEL = "V4-C-PI1"
V4_C_RIDGE = 64.0
V4_C_CLIP = 4.0
INTERVAL_LEVEL = PRIMARY_INTERVAL_LEVEL
EXCLUDED_WEEKLY_ROSTER_STATUSES = {"RET"}


def _require_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Required repository input is missing: {path}")
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Required repository input must be an object: {path}")
    return payload


def _scoring_settings(
    repo_root: Path,
    league_id: str,
    scoring_season: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = league_season_path(repo_root, league_id, scoring_season)
    payload = _require_object(path)
    if payload.get("CanonicalLeagueID") != league_id:
        raise ValueError(
            f"CanonicalLeagueID mismatch in scoring profile: expected={league_id!r} "
            f"actual={payload.get('CanonicalLeagueID')!r}"
        )
    if payload.get("Season") != scoring_season:
        raise ValueError(
            f"Scoring profile season mismatch: expected={scoring_season} "
            f"actual={payload.get('Season')!r}"
        )
    scoring = payload.get("ScoringSettings")
    if not isinstance(scoring, dict):
        raise ValueError(f"Selected League season has no ScoringSettings: {path}")
    return scoring, build_scoring_profile_identity(league_id, scoring_season, scoring)


def _target_roster(
    repo_root: Path,
    season: int,
    week: int,
) -> tuple[list[dict[str, Any]], bool]:
    path = repo_root / "source-data/nfl/weekly-rosters" / str(season) / f"{week:02d}.json"
    payload = _require_object(path)
    if payload.get("Season") != season or payload.get("Week") != week:
        raise ValueError(f"Weekly roster season/week mismatch: {path}")
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise ValueError(f"Weekly roster has no Records array: {path}")

    players: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Weekly roster contains a non-object row: {path}")
        position = str(row.get("Position") or "").upper()
        if position not in FANTASY_POSITIONS:
            continue
        roster_status = str(row.get("Status") or "").upper()
        if roster_status in EXCLUDED_WEEKLY_ROSTER_STATUSES:
            continue
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError(f"Fantasy-relevant weekly roster row lacks CanonicalPlayerID: {path}")
        if player_id in seen:
            raise ValueError(f"Duplicate CanonicalPlayerID in weekly roster: {player_id}")
        seen.add(player_id)
        players.append(
            {
                "CanonicalPlayerID": player_id,
                "PlayerName": row.get("PlayerName"),
                "Position": position,
                "Team": row.get("Team"),
                "RosterStatus": roster_status,
            }
        )
    players.sort(key=lambda row: row["CanonicalPlayerID"])
    return players, payload.get("Finalized") is True


def _scheduled_teams(repo_root: Path, season: int, week: int) -> set[str]:
    path = repo_root / "source-data/nfl/schedules" / f"{season}.json"
    payload = _require_object(path)
    if payload.get("Season") != season:
        raise ValueError(f"Schedule season mismatch: {path}")
    games = payload.get("Games")
    if not isinstance(games, list):
        raise ValueError(f"Schedule has no Games array: {path}")

    teams: set[str] = set()
    for game in games:
        if not isinstance(game, dict):
            continue
        if int(game.get("Week") or 0) != week:
            continue
        if str(game.get("GameType") or "").upper() != "REG":
            continue
        for field in ("AwayTeam", "HomeTeam"):
            team = game.get(field)
            if isinstance(team, str) and team:
                teams.add(team)
    return teams


def _week_finality(
    repo_root: Path,
    *,
    season: int,
    week: int,
) -> tuple[bool, set[str]]:
    """Return canonical REG WeekFinal plus the final game IDs for that week.

    Current-season source partitions deliberately keep Finalized=false until the
    season becomes historical. WeekFinal is therefore the temporal authority for
    whether a completed current-season week may enter pregame projection history.
    """
    path = repo_root / "source-data/nfl/game-finality" / f"{season}.json"
    payload = _require_object(path)
    if payload.get("Season") != season:
        raise ValueError(f"Game-finality season mismatch: {path}")

    weeks = payload.get("Weeks")
    games = payload.get("Games")
    if not isinstance(weeks, list) or not isinstance(games, list):
        raise ValueError(f"Game-finality payload is missing Weeks/Games arrays: {path}")

    matches = [
        row
        for row in weeks
        if isinstance(row, dict)
        and str(row.get("GameType") or "").upper() == "REG"
        and int(row.get("Week") or 0) == week
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("WeekFinal"), bool):
        raise ValueError(
            f"Expected exactly one REG WeekFinal row for {season}/W{week}: {path}"
        )

    final_game_ids = {
        str(row["GameID"])
        for row in games
        if isinstance(row, dict)
        and str(row.get("GameType") or "").upper() == "REG"
        and int(row.get("Week") or 0) == week
        and row.get("Final") is True
        and isinstance(row.get("GameID"), str)
        and row.get("GameID")
    }
    applicable = int(matches[0].get("ApplicableGameCount") or 0)
    final_count = int(matches[0].get("FinalGameCount") or 0)
    if final_count != len(final_game_ids):
        raise ValueError(
            f"Game-finality summary/game detail mismatch for {season}/W{week}: "
            f"summary={final_count} detail={len(final_game_ids)}"
        )
    if matches[0]["WeekFinal"] is True and (applicable <= 0 or final_count != applicable):
        raise ValueError(
            f"WeekFinal=true without complete final-game evidence for {season}/W{week}"
        )
    return bool(matches[0]["WeekFinal"]), final_game_ids


def _current_partition_records(
    repo_root: Path,
    relative_path: str,
    *,
    season: int,
    week: int,
) -> list[dict[str, Any]]:
    path = repo_root / "source-data/nfl" / relative_path / str(season) / f"{week:02d}.json"
    payload = _require_object(path)
    if payload.get("Season") != season or payload.get("Week") != week:
        raise ValueError(f"Current-season canonical partition season/week mismatch: {path}")
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ValueError(f"Current-season canonical partition has no Records array: {path}")
    return records


def _current_snap_rows_by_player(
    repo_root: Path,
    *,
    season: int,
    week: int,
) -> dict[str, list[dict[str, Any]]]:
    rows = _current_partition_records(
        repo_root,
        "snap-counts",
        season=season,
        week=week,
    )
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Current snap-count partition contains a non-object row: {season}/W{week}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            continue
        result[player_id].append(row)
    return dict(result)


def _current_event_rows_by_player(
    repo_root: Path,
    *,
    season: int,
    week: int,
    required: bool,
    final_game_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    path = (
        repo_root
        / "source-data/nfl/special-teams-fumble-events"
        / str(season)
        / f"{week:02d}.json"
    )
    if not path.exists():
        if required:
            raise ValueError(
                "Current-season Special Teams event evidence is required for active "
                f"scoring settings but missing for finalized {season}/W{week}: {path}"
            )
        return {}

    payload = _require_object(path)
    if payload.get("Season") != season or payload.get("Week") != week:
        raise ValueError(f"Current Special Teams event partition season/week mismatch: {path}")
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise ValueError(f"Current Special Teams event partition has no Records array: {path}")

    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Current Special Teams event partition contains non-object row: {path}")
        game_id = row.get("GameID")
        if game_id not in final_game_ids:
            raise ValueError(
                f"Current Special Teams event references a non-final/foreign game in {season}/W{week}: {game_id!r}"
            )
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError(
                f"Current finalized-week Special Teams event lacks CanonicalPlayerID: {path}"
            )
        result[player_id].append(row)
    return dict(result)


def _current_scored_played_games(
    repo_root: Path,
    *,
    season: int,
    week: int,
    scoring: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    week_final, final_game_ids = _week_finality(
        repo_root,
        season=season,
        week=week,
    )
    if not week_final:
        raise ValueError(
            f"Current-season projection history cannot consume non-final {season}/W{week}"
        )

    stat_rows = _current_partition_records(
        repo_root,
        "player-stats",
        season=season,
        week=week,
    )
    snaps_by_player = _current_snap_rows_by_player(
        repo_root,
        season=season,
        week=week,
    )
    active_event_keys = {
        key
        for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS
        if number(scoring.get(key)) != 0
    }
    events_by_player = _current_event_rows_by_player(
        repo_root,
        season=season,
        week=week,
        required=bool(active_event_keys),
        final_game_ids=final_game_ids,
    )

    observations: list[dict[str, Any]] = []
    usage: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for record in stat_rows:
        if not isinstance(record, dict):
            raise ValueError(f"Current player-stats contains a non-object row: {season}/W{week}")
        position = str(record.get("Position") or "").upper()
        if position not in FANTASY_POSITIONS:
            continue
        player_id = record.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError(
                f"Fantasy-relevant current player-stat row lacks CanonicalPlayerID: {season}/W{week}"
            )
        if player_id in seen:
            raise ValueError(f"Duplicate current player-stat record for {player_id} in {season}/W{week}")
        seen.add(player_id)

        stats = record.get("Stats")
        if not isinstance(stats, dict):
            raise ValueError(
                f"Current player-stat record has no Stats object: {season}/W{week}/{player_id}"
            )
        game_id = stats.get("game_id")
        if not isinstance(game_id, str) or game_id not in final_game_ids:
            raise ValueError(
                f"Current player-stat row is not backed by final-game evidence: "
                f"{season}/W{week}/{player_id}/{game_id!r}"
            )

        snap_rows = snaps_by_player.get(player_id, [])
        if not snap_rows:
            continue
        offense_snaps = sum(number(row.get("OffenseSnaps")) for row in snap_rows)
        special_teams_snaps = sum(number(row.get("SpecialTeamsSnaps")) for row in snap_rows)
        played = special_teams_snaps > 0 if position == "K" else offense_snaps > 0
        if not played:
            continue

        points = derive_actual_points(
            record,
            scoring,
            special_teams_fumble_events=events_by_player.get(player_id, [])
            if active_event_keys
            else None,
        )
        observations.append(
            {
                "Season": season,
                "Week": week,
                "CanonicalPlayerID": player_id,
                "PlayerName": record.get("PlayerName"),
                "Position": position,
                "FantasyPoints": points,
                "OffenseSnaps": offense_snaps,
                "SpecialTeamsSnaps": special_teams_snaps,
            }
        )

        snap_values = [
            float(row["OffensePct"])
            for row in snap_rows
            if row.get("OffensePct") not in (None, "")
        ]
        usage[player_id] = {
            "Position": position,
            "SnapShare": (
                None
                if position == "K"
                else (max(snap_values) if snap_values else None)
            ),
            "Opportunity": _opportunity_value(position, stats),
        }

    return observations, usage


def _completed_observations(
    repo_root: Path,
    *,
    season: int,
    scoring: dict[str, Any],
    last_week: int,
    current_season: bool = False,
) -> dict[int, list[dict[str, Any]]]:
    if last_week <= 0:
        return {}
    if not current_season:
        observations, _audit = build_scored_played_games(
            repo_root,
            season=season,
            scoring=scoring,
            first_week=1,
            last_week=last_week,
        )
        return observations

    result: dict[int, list[dict[str, Any]]] = {}
    for week in range(1, last_week + 1):
        observations, _usage = _current_scored_played_games(
            repo_root,
            season=season,
            week=week,
            scoring=scoring,
        )
        result[week] = observations
    return result


def _score_history(
    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]],
    player_id: str,
    seasons: list[int],
    *,
    current_before_week: int | None = None,
) -> list[float]:
    values: list[float] = []
    for season in seasons:
        for week, rows in sorted(observations_by_season.get(season, {}).items()):
            if current_before_week is not None and season == seasons[-1] and week >= current_before_week:
                continue
            for row in rows:
                if row.get("CanonicalPlayerID") == player_id:
                    values.append(float(row["FantasyPoints"]))
    return values


def _current_player_scores(
    observations_by_week: dict[int, list[dict[str, Any]]],
) -> dict[str, list[float]]:
    result: dict[str, list[float]] = defaultdict(list)
    for week in sorted(observations_by_week):
        for row in observations_by_week[week]:
            result[str(row["CanonicalPlayerID"])].append(float(row["FantasyPoints"]))
    return dict(result)


def _current_usage_history(
    observations_by_week: dict[int, list[dict[str, Any]]],
    usage_by_week: dict[int, dict[str, dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for week in sorted(observations_by_week):
        played = {str(row["CanonicalPlayerID"]) for row in observations_by_week[week]}
        usage_rows = usage_by_week.get(week, {})
        for player_id in played:
            usage = usage_rows.get(player_id)
            if not isinstance(usage, dict):
                continue
            result[player_id].append(
                {
                    "SnapShare": usage.get("SnapShare"),
                    "Opportunity": usage.get("Opportunity"),
                }
            )
    return dict(result)


def _build_model_state(
    repo_root: Path,
    *,
    target_season: int,
    scoring: dict[str, Any],
) -> dict[str, Any]:
    point_fit_seasons = [target_season - 3, target_season - 2, target_season - 1]
    interval_fit_seasons = [target_season - 3, target_season - 2]
    interval_calibration_season = target_season - 1
    required_seasons = list(range(target_season - 5, target_season))

    observations: dict[int, dict[int, list[dict[str, Any]]]] = {}
    usage: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
    for season in required_seasons:
        observations[season] = _completed_observations(
            repo_root,
            season=season,
            scoring=scoring,
            last_week=18,
        )
        usage[season] = _usage_by_week(
            repo_root,
            season=season,
            first_week=1,
            last_week=18,
        )

    examples = build_v4_examples(
        observations,
        usage,
        target_seasons=point_fit_seasons,
    )

    production_fit_rows = _v3_rows(examples, seasons=set(point_fit_seasons))
    if not production_fit_rows:
        raise ValueError("V4-C production fit has no calibration rows")
    production_fit = fit_variant(
        production_fit_rows,
        variant=VARIANT_COMBINED,
        ridge=V4_C_RIDGE,
    )

    interval_fit_rows = _v3_rows(examples, seasons=set(interval_fit_seasons))
    interval_calibration_v3 = _v3_rows(
        examples,
        seasons={interval_calibration_season},
    )
    if not interval_fit_rows or not interval_calibration_v3:
        raise ValueError("V4-C-PI1 rolling interval calibration has no rows")

    interval_base_fit = fit_variant(
        interval_fit_rows,
        variant=VARIANT_COMBINED,
        ridge=V4_C_RIDGE,
    )
    interval_rows = evaluate_variant(
        interval_calibration_v3,
        fit=interval_base_fit,
        clip=V4_C_CLIP,
    )["Rows"]

    volatility = build_prior_score_volatility(
        observations,
        target_seasons=[interval_calibration_season],
    )
    interval_rows = _enrich_volatility(interval_rows, volatility)
    projection_thresholds = _projection_thresholds(interval_rows)
    volatility_thresholds = _volatility_thresholds(
        interval_rows,
        projection_thresholds,
    )
    residual_groups = _residual_groups(
        interval_rows,
        projection_thresholds=projection_thresholds,
        volatility_thresholds=volatility_thresholds,
    )

    return {
        "Observations": observations,
        "Usage": usage,
        "ProductionFit": production_fit,
        "PointFitSeasons": point_fit_seasons,
        "IntervalFitSeasons": interval_fit_seasons,
        "IntervalCalibrationSeason": interval_calibration_season,
        "IntervalCalibrationRows": len(interval_rows),
        "ProjectionThresholds": projection_thresholds,
        "VolatilityThresholds": volatility_thresholds,
        "ResidualGroups": residual_groups,
    }


def _target_projection_context(
    repo_root: Path,
    *,
    target_season: int,
    target_week: int,
    scoring: dict[str, Any],
    model_state: dict[str, Any],
) -> dict[str, Any]:
    observations = dict(model_state["Observations"])
    usage = dict(model_state["Usage"])

    current_observations = _completed_observations(
        repo_root,
        season=target_season,
        scoring=scoring,
        last_week=target_week - 1,
        current_season=True,
    )
    current_usage: dict[int, dict[str, dict[str, Any]]] = {}
    for prior_week in range(1, target_week):
        _observations, week_usage = _current_scored_played_games(
            repo_root,
            season=target_season,
            week=prior_week,
            scoring=scoring,
        )
        current_usage[prior_week] = week_usage
    observations[target_season] = current_observations
    usage[target_season] = current_usage

    season_summaries = {
        season: _player_season_summaries(rows)
        for season, rows in observations.items()
    }
    previous_aggregates = _season_position_aggregates(
        observations[target_season - 1]
    )
    usage_summaries = {
        season: _usage_season_summaries(
            usage[season],
            {
                week: {str(row["CanonicalPlayerID"]) for row in rows}
                for week, rows in observations[season].items()
            },
        )
        for season in (target_season - 2, target_season - 1)
    }

    return {
        "Observations": observations,
        "Usage": usage,
        "SeasonSummaries": season_summaries,
        "PreviousAggregates": previous_aggregates,
        "CurrentScores": _current_player_scores(current_observations),
        "CurrentUsageHistory": _current_usage_history(
            current_observations,
            current_usage,
        ),
        "UsageSummaries": usage_summaries,
    }


def _position_prior(
    player_id: str,
    position: str,
    previous_aggregates: tuple[
        dict[str, float],
        dict[str, int],
        dict[str, float],
        dict[str, int],
    ],
) -> float | None:
    (
        player_sums,
        player_counts,
        position_sums,
        position_counts,
    ) = previous_aggregates
    return _leave_one_player_out_mean(
        position=position,
        player_id=player_id,
        player_sums=player_sums,
        player_counts=player_counts,
        position_sums=position_sums,
        position_counts=position_counts,
    )


def _v3_target_projection(
    *,
    player_id: str,
    position: str,
    target_season: int,
    context: dict[str, Any],
) -> tuple[float | None, bool, int]:
    current_scores = context["CurrentScores"].get(player_id, [])
    prior_games = len(current_scores)
    current_ppg = (
        sum(current_scores) / prior_games
        if prior_games > 0
        else None
    )

    history_ppg, effective_history_games = _history_components(
        player_id,
        target_season=target_season,
        season_summaries=context["SeasonSummaries"],
        variant=HISTORY_TWO_SEASON,
        decay=HISTORY_DECAY,
    )
    history_backed = history_ppg is not None and effective_history_games > 0

    # Product rule from #697: a true no-history cold start does not receive a
    # synthetic position-only point projection.
    if prior_games == 0 and not history_backed:
        return None, False, 0

    baseline = _player_baseline(
        history_ppg=history_ppg,
        effective_history_games=effective_history_games,
        position_prior=_position_prior(
            player_id,
            position,
            context["PreviousAggregates"],
        ),
        history_k=0.0,
    )
    if baseline is None:
        return None, history_backed, prior_games

    if prior_games <= 0 or current_ppg is None:
        return float(baseline), history_backed, prior_games

    current_k = 1.0
    weight = prior_games / (prior_games + current_k)
    return (
        float(current_ppg) * weight + float(baseline) * (1.0 - weight),
        history_backed,
        prior_games,
    )


def _usage_features(
    *,
    player_id: str,
    target_season: int,
    context: dict[str, Any],
) -> dict[str, float]:
    history = context["CurrentUsageHistory"].get(player_id, [])
    result: dict[str, float] = {}

    for feature, history_key in (
        (FEATURE_SNAP, "SnapShare"),
        (FEATURE_OPPORTUNITY, "Opportunity"),
    ):
        recent = _recent_mean(history, history_key)
        baseline = _historical_usage_baseline(
            player_id,
            target_season=target_season,
            feature=history_key,
            season_summaries=context["UsageSummaries"],
        )
        if baseline is None:
            baseline = _fallback_older_current_mean(history, history_key)
        result[feature] = (
            float(recent) - float(baseline)
            if recent is not None and baseline is not None
            else 0.0
        )
    return result


def _history_values_for_interval(
    *,
    player_id: str,
    target_season: int,
    context: dict[str, Any],
) -> list[float]:
    values: list[float] = []
    for season in (target_season - 2, target_season - 1):
        summary_rows = context["Observations"].get(season, {})
        for rows in summary_rows.values():
            for row in rows:
                if row.get("CanonicalPlayerID") == player_id:
                    values.append(float(row["FantasyPoints"]))
    values.extend(context["CurrentScores"].get(player_id, []))
    return values


def _projection_for_player(
    player: dict[str, Any],
    *,
    target_season: int,
    has_game: bool,
    context: dict[str, Any],
    model_state: dict[str, Any],
) -> dict[str, Any]:
    player_id = str(player["CanonicalPlayerID"])
    point_model = POINT_MODEL
    interval_model = INTERVAL_MODEL

    history_values = _history_values_for_interval(
        player_id=player_id,
        target_season=target_season,
        context=context,
    )
    history_games = len(history_values)

    if not has_game:
        return {
            "Status": "no-game",
            "Points": None,
            "PredictionRange": None,
            "PredictionRanges": [],
            "RangeQuality": "unavailable",
            "HistoryGames": history_games,
            "ParticipationCondition": PARTICIPATION_CONDITION,
            "AvailabilityAdjustmentApplied": False,
            "PointModel": point_model,
            "IntervalModel": interval_model,
        }

    v3_projection, history_backed, prior_games = _v3_target_projection(
        player_id=player_id,
        position=str(player["Position"]),
        target_season=target_season,
        context=context,
    )
    if v3_projection is None:
        status = "insufficient-history" if prior_games == 0 and not history_backed else "unavailable"
        return {
            "Status": status,
            "Points": None,
            "PredictionRange": None,
            "PredictionRanges": [],
            "RangeQuality": "unavailable",
            "HistoryGames": history_games,
            "ParticipationCondition": PARTICIPATION_CONDITION,
            "AvailabilityAdjustmentApplied": False,
            "PointModel": point_model,
            "IntervalModel": interval_model,
        }

    features = _usage_features(
        player_id=player_id,
        target_season=target_season,
        context=context,
    )
    row = {
        "PositionGroup": _position_group(str(player["Position"])),
        FEATURE_SNAP: features[FEATURE_SNAP],
        FEATURE_OPPORTUNITY: features[FEATURE_OPPORTUNITY],
    }
    raw_adjustment = _adjustment(row, model_state["ProductionFit"])
    adjustment = max(-V4_C_CLIP, min(V4_C_CLIP, raw_adjustment))
    projection = float(v3_projection) + adjustment

    volatility = _population_std(history_values)
    interval_row = {
        "PositionGroup": row["PositionGroup"],
        "Projection": projection,
        "PriorScoreVolatility": volatility,
    }
    intervals = {
        level: _interval_for_row(
            interval_row,
            level=level,
            strategy=STRATEGY_POSITION_PROJECTION_VOLATILITY,
            groups=model_state["ResidualGroups"],
            projection_thresholds=model_state["ProjectionThresholds"],
            volatility_thresholds=model_state["VolatilityThresholds"],
        )
        for level in PUBLISHED_INTERVAL_LEVELS
    }
    interval = intervals[INTERVAL_LEVEL]
    selected_group = str(interval["Group"])
    range_quality = (
        "player-volatility"
        if volatility is not None and selected_group.count("|") == 2
        else "limited-history-fallback"
    )

    return {
        "Status": "available",
        "Points": round(projection, 4),
        "PredictionRange": {
            "Level": INTERVAL_LEVEL,
            "Lower": round(float(interval["Lower"]), 4),
            "Upper": round(float(interval["Upper"]), 4),
        },
        "PredictionRanges": [
            {
                "Level": level,
                "Lower": round(float(intervals[level]["Lower"]), 4),
                "Upper": round(float(intervals[level]["Upper"]), 4),
            }
            for level in PUBLISHED_INTERVAL_LEVELS
        ],
        "RangeQuality": range_quality,
        "HistoryGames": history_games,
        "ParticipationCondition": PARTICIPATION_CONDITION,
        "AvailabilityAdjustmentApplied": False,
        "PointModel": point_model,
        "IntervalModel": interval_model,
    }


def _final_actual_inputs(
    repo_root: Path,
    *,
    season: int,
    week: int,
    scoring: dict[str, Any],
) -> tuple[bool, dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    week_final, final_game_ids = _week_finality(
        repo_root,
        season=season,
        week=week,
    )
    if not week_final:
        return False, {}, {}

    stats_path = repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
    if not stats_path.exists():
        return False, {}, {}
    rows = _current_partition_records(
        repo_root,
        "player-stats",
        season=season,
        week=week,
    )
    stats_by_player: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Target player-stats contains a non-object row: {stats_path}")
        player_id = row.get("CanonicalPlayerID")
        stats = row.get("Stats")
        if not isinstance(player_id, str) or not player_id:
            continue
        if not isinstance(stats, dict):
            raise ValueError(f"Target player-stat record has no Stats object: {stats_path}")
        game_id = stats.get("game_id")
        if not isinstance(game_id, str) or game_id not in final_game_ids:
            raise ValueError(
                f"Target player-stat row is not backed by final-game evidence: "
                f"{season}/W{week}/{player_id}/{game_id!r}"
            )
        stats_by_player[player_id] = row

    active_event_keys = {
        key
        for key in SPECIAL_TEAMS_EVENT_SCORING_KEYS
        if number(scoring.get(key)) != 0
    }
    events_by_player = _current_event_rows_by_player(
        repo_root,
        season=season,
        week=week,
        required=bool(active_event_keys),
        final_game_ids=final_game_ids,
    )
    return True, stats_by_player, events_by_player


def _actual_for_player(
    player: dict[str, Any],
    *,
    has_game: bool,
    finalized: bool,
    stats_by_player: dict[str, dict[str, Any]],
    events_by_player: dict[str, list[dict[str, Any]]],
    scoring: dict[str, Any],
) -> dict[str, Any]:
    if not has_game or not finalized:
        return {"Points": None, "State": "unavailable"}

    player_id = str(player["CanonicalPlayerID"])
    record = stats_by_player.get(player_id)
    if record is None:
        record = {
            "CanonicalPlayerID": player_id,
            "Position": player["Position"],
            "Stats": {},
        }
    points = derive_actual_points(
        record,
        scoring,
        special_teams_fumble_events=events_by_player.get(player_id, []),
    )
    return {"Points": round(points, 4), "State": "final"}


def build_player_week_fantasy_dataset(
    repo_root: Path,
    *,
    league_id: str,
    season: int,
    week: int,
    scoring_season: int | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    scoring_season = season if scoring_season is None else scoring_season
    scoring, scoring_profile = _scoring_settings(root, league_id, scoring_season)
    roster, roster_finalized = _target_roster(root, season, week)
    scheduled_teams = _scheduled_teams(root, season, week)

    model_state = _build_model_state(
        root,
        target_season=season,
        scoring=scoring,
    )
    context = _target_projection_context(
        root,
        target_season=season,
        target_week=week,
        scoring=scoring,
        model_state=model_state,
    )
    actual_finalized, stats_by_player, events_by_player = _final_actual_inputs(
        root,
        season=season,
        week=week,
        scoring=scoring,
    )

    records: list[dict[str, Any]] = []
    for player in roster:
        team = player.get("Team")
        has_game = isinstance(team, str) and team in scheduled_teams
        records.append(
            {
                "CanonicalPlayerID": player["CanonicalPlayerID"],
                "Projection": _projection_for_player(
                    player,
                    target_season=season,
                    has_game=has_game,
                    context=context,
                    model_state=model_state,
                ),
                "Actual": _actual_for_player(
                    player,
                    has_game=has_game,
                    finalized=actual_finalized,
                    stats_by_player=stats_by_player,
                    events_by_player=events_by_player,
                    scoring=scoring,
                ),
            }
        )

    contract = build_player_week_fantasy_contract(
        canonical_league_id=league_id,
        season=season,
        week=week,
        scoring_profile=scoring_profile,
        records=records,
    )
    contract["ProjectionModel"] = {
        "PointModel": POINT_MODEL,
        "IntervalModel": INTERVAL_MODEL,
        "V4CRidge": V4_C_RIDGE,
        "V4CAdjustmentClip": V4_C_CLIP,
        "PointFitSeasons": model_state["PointFitSeasons"],
        "IntervalCalibrationSeason": model_state["IntervalCalibrationSeason"],
        "IntervalCalibrationPointFitSeasons": model_state["IntervalFitSeasons"],
        "IntervalCalibrationRows": model_state["IntervalCalibrationRows"],
        "IntervalLevel": INTERVAL_LEVEL,
        "IntervalLevels": list(PUBLISHED_INTERVAL_LEVELS),
        "MinimumConditionalGroupSize": MIN_GROUP_SIZE,
        "ParticipationCondition": PARTICIPATION_CONDITION,
    }
    contract["Materialization"] = {
        "TargetWeeklyRosterFinalized": roster_finalized,
        "ActualScoringEvidenceFinalized": actual_finalized,
        "FantasyRelevantPositions": sorted(FANTASY_POSITIONS),
        "ExcludedWeeklyRosterStatuses": sorted(EXCLUDED_WEEKLY_ROSTER_STATUSES),
        "RecordCount": len(contract["Records"]),
        "ProjectionStatusCounts": dict(
            sorted(
                {
                    status: sum(
                        1
                        for row in contract["Records"]
                        if row["Projection"]["Status"] == status
                    )
                    for status in {
                        row["Projection"]["Status"]
                        for row in contract["Records"]
                    }
                }.items()
            )
        ),
        "ActualStateCounts": dict(
            sorted(
                {
                    state: sum(
                        1
                        for row in contract["Records"]
                        if row["Actual"]["State"] == state
                    )
                    for state in {
                        row["Actual"]["State"]
                        for row in contract["Records"]
                    }
                }.items()
            )
        ),
    }
    return contract


def output_path(
    repo_root: Path,
    *,
    league_id: str,
    season: int,
    week: int,
) -> Path:
    return (
        repo_root
        / "derived-data"
        / "player-week-fantasy"
        / league_id
        / str(season)
        / f"{week:02d}.json"
    )


def write_dataset(path: Path, payload: dict[str, Any]) -> bool:
    serialized = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == serialized:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--scoring-season", type=int)
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    payload = build_player_week_fantasy_dataset(
        root,
        league_id=args.league,
        season=args.season,
        week=args.week,
        scoring_season=args.scoring_season,
    )
    target = output_path(
        root,
        league_id=args.league,
        season=args.season,
        week=args.week,
    )
    changed = False if args.no_write else write_dataset(target, payload)

    summary = {
        "Path": str(target.relative_to(root)),
        "Changed": changed,
        "RecordCount": payload["Materialization"]["RecordCount"],
        "ProjectionStatusCounts": payload["Materialization"]["ProjectionStatusCounts"],
        "ActualStateCounts": payload["Materialization"]["ActualStateCounts"],
        "SettingsHash": payload["ScoringProfile"]["SettingsHash"],
        "PointFitSeasons": payload["ProjectionModel"]["PointFitSeasons"],
        "IntervalCalibrationSeason": payload["ProjectionModel"]["IntervalCalibrationSeason"],
    }
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
