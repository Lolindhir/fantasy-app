#!/usr/bin/env python3
"""Calibrate and evaluate V3 player-history projection baselines without future leakage."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from historical_projection_backtest import (
    _metrics,
    _scoring_profile,
    build_scored_played_games,
)
from historical_projection_v2_calibration import (
    K_GRID,
    _breakdowns,
    _leave_one_player_out_mean,
    _season_position_aggregates,
)

HISTORY_PREVIOUS_ONLY = "previous-season-player-history"
HISTORY_TWO_SEASON = "two-season-recency-player-history"
HISTORY_VARIANTS = (HISTORY_PREVIOUS_ONLY, HISTORY_TWO_SEASON)
HISTORY_DECAYS = (0.25, 0.5, 0.75, 1.0)
HISTORY_K_GRID = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 24.0, 32.0)
V2_K = 0.5


def _player_season_summaries(
    observations_by_week: dict[int, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    names: dict[str, Any] = {}
    positions: dict[str, str] = {}

    for rows in observations_by_week.values():
        for row in rows:
            player_id = str(row["CanonicalPlayerID"])
            totals[player_id] += float(row["FantasyPoints"])
            counts[player_id] += 1
            names[player_id] = row.get("PlayerName")
            positions[player_id] = str(row["Position"])

    return {
        player_id: {
            "Games": counts[player_id],
            "PPG": totals[player_id] / counts[player_id],
            "PlayerName": names.get(player_id),
            "Position": positions.get(player_id),
        }
        for player_id in counts
        if counts[player_id] > 0
    }


def _history_components(
    player_id: str,
    *,
    target_season: int,
    season_summaries: dict[int, dict[str, dict[str, Any]]],
    variant: str,
    decay: float,
) -> tuple[float | None, float]:
    if variant not in HISTORY_VARIANTS:
        raise ValueError(f"Unknown V3 player-history variant: {variant}")

    weighted_points = 0.0
    effective_games = 0.0

    previous = season_summaries.get(target_season - 1, {}).get(player_id)
    if previous is not None:
        games = float(previous["Games"])
        weighted_points += float(previous["PPG"]) * games
        effective_games += games

    if variant == HISTORY_TWO_SEASON:
        older = season_summaries.get(target_season - 2, {}).get(player_id)
        if older is not None:
            games = float(older["Games"]) * decay
            weighted_points += float(older["PPG"]) * games
            effective_games += games

    if effective_games <= 0:
        return None, 0.0
    return weighted_points / effective_games, effective_games


def _player_baseline(
    *,
    history_ppg: float | None,
    effective_history_games: float,
    position_prior: float | None,
    history_k: float,
) -> float | None:
    if position_prior is None:
        return history_ppg
    if history_ppg is None or effective_history_games <= 0:
        return float(position_prior)
    if history_k <= 0:
        return float(history_ppg)
    weight = effective_history_games / (effective_history_games + history_k)
    return float(history_ppg) * weight + float(position_prior) * (1.0 - weight)


def build_v3_examples(
    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]],
    *,
    target_seasons: list[int],
) -> list[dict[str, Any]]:
    season_summaries = {
        season: _player_season_summaries(rows)
        for season, rows in observations_by_season.items()
    }
    position_aggregates = {
        season: _season_position_aggregates(rows)
        for season, rows in observations_by_season.items()
    }
    examples: list[dict[str, Any]] = []

    for season in target_seasons:
        current = observations_by_season.get(season)
        if current is None:
            raise ValueError(f"V3 requires target-season observations for {season}")
        previous_aggregates = position_aggregates.get(season - 1)
        if previous_aggregates is None:
            raise ValueError(f"V3 requires previous-season position evidence for {season - 1}")

        (
            previous_player_sums,
            previous_player_counts,
            previous_position_sums,
            previous_position_counts,
        ) = previous_aggregates

        current_player_history: dict[str, list[float]] = defaultdict(list)

        for week in sorted(current):
            rows = current[week]
            for row in rows:
                player_id = str(row["CanonicalPlayerID"])
                position = str(row["Position"])
                prior = current_player_history.get(player_id, [])
                current_ppg = sum(prior) / len(prior) if prior else None

                position_prior = _leave_one_player_out_mean(
                    position=position,
                    player_id=player_id,
                    player_sums=previous_player_sums,
                    player_counts=previous_player_counts,
                    position_sums=previous_position_sums,
                    position_counts=previous_position_counts,
                )

                history_candidates: dict[str, dict[str, Any]] = {}
                history_ppg, history_games = _history_components(
                    player_id,
                    target_season=season,
                    season_summaries=season_summaries,
                    variant=HISTORY_PREVIOUS_ONLY,
                    decay=0.0,
                )
                history_candidates[HISTORY_PREVIOUS_ONLY] = {
                    "HistoryPPG": history_ppg,
                    "EffectiveHistoryGames": history_games,
                    "Decay": 0.0,
                }
                for decay in HISTORY_DECAYS:
                    history_ppg, history_games = _history_components(
                        player_id,
                        target_season=season,
                        season_summaries=season_summaries,
                        variant=HISTORY_TWO_SEASON,
                        decay=decay,
                    )
                    history_candidates[f"{HISTORY_TWO_SEASON}:{decay}"] = {
                        "HistoryPPG": history_ppg,
                        "EffectiveHistoryGames": history_games,
                        "Decay": decay,
                    }

                examples.append(
                    {
                        "Season": season,
                        "Week": week,
                        "CanonicalPlayerID": player_id,
                        "PlayerName": row.get("PlayerName"),
                        "Position": position,
                        "PriorGames": len(prior),
                        "CurrentSeasonPPG": current_ppg,
                        "PositionPrior": position_prior,
                        "Actual": float(row["FantasyPoints"]),
                        "HistoryCandidates": history_candidates,
                    }
                )

            # Current-week outcomes enter state only after all W projections are fixed.
            for row in rows:
                current_player_history[str(row["CanonicalPlayerID"])].append(
                    float(row["FantasyPoints"])
                )

    return examples


def _candidate_key(variant: str, decay: float) -> str:
    if variant == HISTORY_PREVIOUS_ONLY:
        return HISTORY_PREVIOUS_ONLY
    return f"{HISTORY_TWO_SEASON}:{decay}"


def _baseline_for(
    example: dict[str, Any],
    *,
    variant: str,
    decay: float,
    history_k: float,
) -> tuple[float | None, bool]:
    candidate = example["HistoryCandidates"][_candidate_key(variant, decay)]
    history_ppg = candidate["HistoryPPG"]
    effective_history_games = float(candidate["EffectiveHistoryGames"])
    return (
        _player_baseline(
            history_ppg=history_ppg,
            effective_history_games=effective_history_games,
            position_prior=example.get("PositionPrior"),
            history_k=history_k,
        ),
        history_ppg is not None and effective_history_games > 0,
    )


def _v3_projection(
    example: dict[str, Any],
    *,
    variant: str,
    decay: float,
    history_k: float,
    current_k: float,
) -> tuple[float | None, bool]:
    baseline, history_backed = _baseline_for(
        example,
        variant=variant,
        decay=decay,
        history_k=history_k,
    )
    if baseline is None:
        return None, history_backed

    prior_games = int(example["PriorGames"])
    current_ppg = example.get("CurrentSeasonPPG")
    if prior_games <= 0 or current_ppg is None:
        return baseline, history_backed
    if current_k <= 0:
        return float(current_ppg), history_backed

    weight = prior_games / (prior_games + current_k)
    return (
        float(current_ppg) * weight + float(baseline) * (1.0 - weight),
        history_backed,
    )


def _v2_projection(example: dict[str, Any]) -> float | None:
    position_prior = example.get("PositionPrior")
    if position_prior is None:
        return None
    prior_games = int(example["PriorGames"])
    current_ppg = example.get("CurrentSeasonPPG")
    if prior_games <= 0 or current_ppg is None:
        return float(position_prior)
    weight = prior_games / (prior_games + V2_K)
    return float(current_ppg) * weight + float(position_prior) * (1.0 - weight)


def _rows_for_v3(
    examples: Iterable[dict[str, Any]],
    *,
    variant: str,
    decay: float,
    history_k: float,
    current_k: float,
    comparable_only: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        if comparable_only and int(example["PriorGames"]) <= 0:
            continue
        projection, history_backed = _v3_projection(
            example,
            variant=variant,
            decay=decay,
            history_k=history_k,
            current_k=current_k,
        )
        if projection is None:
            continue
        rows.append(
            {
                **example,
                "Projection": projection,
                "HistoryBacked": history_backed,
                "Error": projection - float(example["Actual"]),
            }
        )
    return rows


def _rows_for_v2(
    examples: Iterable[dict[str, Any]],
    *,
    comparable_only: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        if comparable_only and int(example["PriorGames"]) <= 0:
            continue
        projection = _v2_projection(example)
        if projection is None:
            continue
        rows.append(
            {
                **example,
                "Projection": projection,
                "Error": projection - float(example["Actual"]),
            }
        )
    return rows


def calibrate_player_baseline(
    examples: list[dict[str, Any]],
    *,
    calibration_seasons: list[int],
) -> dict[str, Any]:
    cold_starts = [
        row
        for row in examples
        if int(row["Season"]) in calibration_seasons and int(row["PriorGames"]) == 0
    ]
    leaderboard: list[dict[str, Any]] = []

    for variant in HISTORY_VARIANTS:
        decays = (0.0,) if variant == HISTORY_PREVIOUS_ONLY else HISTORY_DECAYS
        for decay in decays:
            for history_k in HISTORY_K_GRID:
                rows = _rows_for_v3(
                    cold_starts,
                    variant=variant,
                    decay=decay,
                    history_k=history_k,
                    current_k=0.0,
                    comparable_only=False,
                )
                history_backed = [row for row in rows if row["HistoryBacked"]]
                metrics = _metrics(history_backed)
                if metrics["Count"] == 0:
                    continue
                leaderboard.append(
                    {
                        "HistoryVariant": variant,
                        "HistoryDecay": decay,
                        "HistoryK": history_k,
                        "HistoryBackedColdStartMetrics": metrics,
                        "AllColdStartMetrics": _metrics(rows),
                    }
                )

    if not leaderboard:
        raise ValueError("V3 player-baseline calibration produced no history-backed cold starts")

    leaderboard.sort(
        key=lambda row: (
            float(row["HistoryBackedColdStartMetrics"]["MAE"]),
            float(row["HistoryBackedColdStartMetrics"]["RMSE"]),
            abs(float(row["HistoryBackedColdStartMetrics"]["Bias"])),
            0 if row["HistoryVariant"] == HISTORY_PREVIOUS_ONLY else 1,
            float(row["HistoryK"]),
            float(row["HistoryDecay"]),
        )
    )
    return {
        "CalibrationSeasons": calibration_seasons,
        "ColdStartObservationCount": len(cold_starts),
        "Selected": leaderboard[0],
        "LeaderboardTop20": leaderboard[:20],
    }


def calibrate_current_shrinkage(
    examples: list[dict[str, Any]],
    *,
    calibration_seasons: list[int],
    player_baseline: dict[str, Any],
) -> dict[str, Any]:
    comparable = [
        row
        for row in examples
        if int(row["Season"]) in calibration_seasons and int(row["PriorGames"]) > 0
    ]
    leaderboard: list[dict[str, Any]] = []

    for current_k in K_GRID:
        rows = _rows_for_v3(
            comparable,
            variant=str(player_baseline["HistoryVariant"]),
            decay=float(player_baseline["HistoryDecay"]),
            history_k=float(player_baseline["HistoryK"]),
            current_k=float(current_k),
            comparable_only=True,
        )
        metrics = _metrics(rows)
        if metrics["Count"] == 0:
            continue
        leaderboard.append(
            {
                "CurrentK": float(current_k),
                "Metrics": metrics,
            }
        )

    if not leaderboard:
        raise ValueError("V3 current-season shrinkage calibration produced no comparable rows")

    leaderboard.sort(
        key=lambda row: (
            float(row["Metrics"]["MAE"]),
            float(row["Metrics"]["RMSE"]),
            abs(float(row["Metrics"]["Bias"])),
            float(row["CurrentK"]),
        )
    )
    return {
        "CalibrationSeasons": calibration_seasons,
        "ComparableObservationCount": len(comparable),
        "Selected": leaderboard[0],
        "LeaderboardTop20": leaderboard[:20],
    }


def evaluate_v3_holdout(
    examples: list[dict[str, Any]],
    *,
    holdout_season: int,
    player_baseline: dict[str, Any],
    current_k: float,
) -> dict[str, Any]:
    holdout = [row for row in examples if int(row["Season"]) == holdout_season]

    v2_comparable = _rows_for_v2(holdout, comparable_only=True)
    v3_comparable = _rows_for_v3(
        holdout,
        variant=str(player_baseline["HistoryVariant"]),
        decay=float(player_baseline["HistoryDecay"]),
        history_k=float(player_baseline["HistoryK"]),
        current_k=current_k,
        comparable_only=True,
    )
    common_keys = {
        (row["Season"], row["Week"], row["CanonicalPlayerID"]) for row in v2_comparable
    } & {
        (row["Season"], row["Week"], row["CanonicalPlayerID"]) for row in v3_comparable
    }
    v2_comparable = [
        row for row in v2_comparable
        if (row["Season"], row["Week"], row["CanonicalPlayerID"]) in common_keys
    ]
    v3_comparable = [
        row for row in v3_comparable
        if (row["Season"], row["Week"], row["CanonicalPlayerID"]) in common_keys
    ]

    v2_all = _rows_for_v2(holdout, comparable_only=False)
    v3_all = _rows_for_v3(
        holdout,
        variant=str(player_baseline["HistoryVariant"]),
        decay=float(player_baseline["HistoryDecay"]),
        history_k=float(player_baseline["HistoryK"]),
        current_k=current_k,
        comparable_only=False,
    )

    v2_cold = [row for row in v2_all if int(row["PriorGames"]) == 0]
    v3_cold = [row for row in v3_all if int(row["PriorGames"]) == 0]
    v3_cold_history = [row for row in v3_cold if row["HistoryBacked"]]
    v3_cold_no_history = [row for row in v3_cold if not row["HistoryBacked"]]
    v2_cold_by_key = {
        (row["Season"], row["Week"], row["CanonicalPlayerID"]): row for row in v2_cold
    }
    v2_cold_history = [
        v2_cold_by_key[(row["Season"], row["Week"], row["CanonicalPlayerID"])]
        for row in v3_cold_history
        if (row["Season"], row["Week"], row["CanonicalPlayerID"]) in v2_cold_by_key
    ]

    v2_metrics = _metrics(v2_comparable)
    v3_metrics = _metrics(v3_comparable)
    mae_improvement = float(v2_metrics["MAE"]) - float(v3_metrics["MAE"])
    rmse_improvement = float(v2_metrics["RMSE"]) - float(v3_metrics["RMSE"])

    v2_cold_history_metrics = _metrics(v2_cold_history)
    v3_cold_history_metrics = _metrics(v3_cold_history)

    return {
        "HoldoutSeason": holdout_season,
        "Comparable": {
            "V2": v2_metrics,
            "V3": v3_metrics,
            "MAEImprovementPoints": round(mae_improvement, 4),
            "MAEImprovementPercent": round(
                100.0 * mae_improvement / float(v2_metrics["MAE"]),
                4,
            ),
            "RMSEImprovementPoints": round(rmse_improvement, 4),
            "RMSEImprovementPercent": round(
                100.0 * rmse_improvement / float(v2_metrics["RMSE"]),
                4,
            ),
            "V2Breakdowns": _breakdowns(v2_comparable),
            "V3Breakdowns": _breakdowns(v3_comparable),
        },
        "ColdStart": {
            "V2All": _metrics(v2_cold),
            "V3All": _metrics(v3_cold),
            "HistoryBackedCount": len(v3_cold_history),
            "NoHistoryCount": len(v3_cold_no_history),
            "V2HistoryBacked": v2_cold_history_metrics,
            "V3HistoryBacked": v3_cold_history_metrics,
            "HistoryBackedMAEImprovementPoints": (
                round(
                    float(v2_cold_history_metrics["MAE"])
                    - float(v3_cold_history_metrics["MAE"]),
                    4,
                )
                if v2_cold_history_metrics["MAE"] is not None
                else None
            ),
            "V3NoHistory": _metrics(v3_cold_no_history),
        },
        "ExpandedCoverage": {
            "V2": _metrics(v2_all),
            "V3": _metrics(v3_all),
            "V2PredictionCount": len(v2_all),
            "V3PredictionCount": len(v3_all),
        },
    }


def build_v3_calibration_report(
    repo_root: Path,
    *,
    league_id: str,
    scoring_season: int,
    calibration_seasons: list[int],
    holdout_season: int,
    first_week: int = 1,
    last_week: int = 18,
) -> dict[str, Any]:
    target_seasons = sorted(set(calibration_seasons + [holdout_season]))
    required_seasons = sorted(
        set(
            target_seasons
            + [season - 1 for season in target_seasons]
            + [season - 2 for season in target_seasons]
        )
    )
    scoring = _scoring_profile(repo_root, league_id, scoring_season)

    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]] = {}
    observation_audits: list[dict[str, Any]] = []
    for season in required_seasons:
        observations, audit = build_scored_played_games(
            repo_root,
            season=season,
            scoring=scoring,
            first_week=first_week,
            last_week=last_week,
        )
        observations_by_season[season] = observations
        observation_audits.append(audit)

    examples = build_v3_examples(
        observations_by_season,
        target_seasons=target_seasons,
    )

    baseline_calibration = calibrate_player_baseline(
        examples,
        calibration_seasons=calibration_seasons,
    )
    selected_baseline = baseline_calibration["Selected"]

    current_calibration = calibrate_current_shrinkage(
        examples,
        calibration_seasons=calibration_seasons,
        player_baseline=selected_baseline,
    )
    selected_current = current_calibration["Selected"]

    holdout = evaluate_v3_holdout(
        examples,
        holdout_season=holdout_season,
        player_baseline=selected_baseline,
        current_k=float(selected_current["CurrentK"]),
    )

    return {
        "ContractVersion": 3,
        "Model": "v3-player-history-position-prior",
        "League": league_id,
        "ScoringSeason": scoring_season,
        "CalibrationSeasons": calibration_seasons,
        "HoldoutSeason": holdout_season,
        "FirstWeek": first_week,
        "LastWeek": last_week,
        "PlayerBaselineFormula": (
            "PlayerBaseline = PlayerHistoryPPG * h + PreviousSeasonPositionPrior * (1 - h); "
            "h = EffectiveHistoryGames / (EffectiveHistoryGames + history_k)"
        ),
        "ProjectionFormula": (
            "Projection = CurrentSeasonPPG * w + PlayerBaseline * (1 - w); "
            "w = PriorGames / (PriorGames + current_k)"
        ),
        "LeakageRule": (
            "2025 is never used for calibration; player history uses only completed prior seasons; "
            "CurrentSeasonPPG uses only weeks < W"
        ),
        "PositionPriorRule": "previous completed season position mean, leave-one-player-out",
        "ObservationAudits": observation_audits,
        "PlayerBaselineCalibration": baseline_calibration,
        "CurrentSeasonCalibration": current_calibration,
        "Holdout": holdout,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--scoring-season", type=int, default=2025)
    parser.add_argument("--calibration-seasons", type=int, nargs="+", default=[2023, 2024])
    parser.add_argument("--holdout-season", type=int, default=2025)
    parser.add_argument("--first-week", type=int, default=1)
    parser.add_argument("--last-week", type=int, default=18)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_v3_calibration_report(
        args.repo_root.resolve(),
        league_id=args.league,
        scoring_season=args.scoring_season,
        calibration_seasons=args.calibration_seasons,
        holdout_season=args.holdout_season,
        first_week=args.first_week,
        last_week=args.last_week,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
