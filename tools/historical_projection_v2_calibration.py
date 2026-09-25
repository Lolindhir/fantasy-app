#!/usr/bin/env python3
"""Calibrate and evaluate V2 shrinkage player projections without future leakage."""
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

BASELINE_PREVIOUS_POSITION_MEAN = "previous-season-position-mean-loo"
BASELINE_CURRENT_POSITION_MEAN = "current-season-position-mean-loo"
BASELINE_VARIANTS = (
    BASELINE_PREVIOUS_POSITION_MEAN,
    BASELINE_CURRENT_POSITION_MEAN,
)

# Fine enough to calibrate rather than hand-pick, with a long tail to detect
# whether the optimum wants effectively complete shrinkage to the baseline.
K_GRID = tuple([index / 4 for index in range(0, 81)] + [24.0, 32.0, 48.0, 64.0])


def _season_position_aggregates(
    observations_by_week: dict[int, list[dict[str, Any]]],
) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, int]],
    dict[str, float],
    dict[str, int],
]:
    player_sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    player_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    position_sums: dict[str, float] = defaultdict(float)
    position_counts: dict[str, int] = defaultdict(int)

    for rows in observations_by_week.values():
        for row in rows:
            position = str(row["Position"])
            player_id = str(row["CanonicalPlayerID"])
            points = float(row["FantasyPoints"])
            player_sums[position][player_id] += points
            player_counts[position][player_id] += 1
            position_sums[position] += points
            position_counts[position] += 1

    return (
        {position: dict(values) for position, values in player_sums.items()},
        {position: dict(values) for position, values in player_counts.items()},
        dict(position_sums),
        dict(position_counts),
    )


def _leave_one_player_out_mean(
    *,
    position: str,
    player_id: str,
    player_sums: dict[str, dict[str, float]],
    player_counts: dict[str, dict[str, int]],
    position_sums: dict[str, float],
    position_counts: dict[str, int],
) -> float | None:
    total = float(position_sums.get(position, 0.0))
    count = int(position_counts.get(position, 0))
    total -= float(player_sums.get(position, {}).get(player_id, 0.0))
    count -= int(player_counts.get(position, {}).get(player_id, 0))
    if count <= 0:
        return None
    return total / count


def build_v2_examples(
    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]],
    *,
    target_seasons: list[int],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []

    for season in target_seasons:
        previous = observations_by_season.get(season - 1)
        current = observations_by_season.get(season)
        if previous is None:
            raise ValueError(f"V2 requires previous-season observations for {season - 1}")
        if current is None:
            raise ValueError(f"V2 requires target-season observations for {season}")

        (
            previous_player_sums,
            previous_player_counts,
            previous_position_sums,
            previous_position_counts,
        ) = _season_position_aggregates(previous)

        current_player_sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        current_player_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        current_position_sums: dict[str, float] = defaultdict(float)
        current_position_counts: dict[str, int] = defaultdict(int)
        player_history: dict[str, list[float]] = defaultdict(list)

        for week in sorted(current):
            rows = current[week]
            # All baseline/current-PPG state here contains weeks < W only.
            for row in rows:
                player_id = str(row["CanonicalPlayerID"])
                position = str(row["Position"])
                prior = player_history.get(player_id, [])
                current_ppg = sum(prior) / len(prior) if prior else None

                previous_position_mean = _leave_one_player_out_mean(
                    position=position,
                    player_id=player_id,
                    player_sums=previous_player_sums,
                    player_counts=previous_player_counts,
                    position_sums=previous_position_sums,
                    position_counts=previous_position_counts,
                )
                current_position_mean = _leave_one_player_out_mean(
                    position=position,
                    player_id=player_id,
                    player_sums=current_player_sums,
                    player_counts=current_player_counts,
                    position_sums=current_position_sums,
                    position_counts=current_position_counts,
                )
                if current_position_mean is None:
                    current_position_mean = previous_position_mean

                examples.append(
                    {
                        "Season": season,
                        "Week": week,
                        "CanonicalPlayerID": player_id,
                        "PlayerName": row.get("PlayerName"),
                        "Position": position,
                        "PriorGames": len(prior),
                        "CurrentSeasonPPG": current_ppg,
                        "Actual": float(row["FantasyPoints"]),
                        "Baselines": {
                            BASELINE_PREVIOUS_POSITION_MEAN: previous_position_mean,
                            BASELINE_CURRENT_POSITION_MEAN: current_position_mean,
                        },
                    }
                )

            # Target-week observations become model state only after all W projections.
            for row in rows:
                player_id = str(row["CanonicalPlayerID"])
                position = str(row["Position"])
                points = float(row["FantasyPoints"])
                player_history[player_id].append(points)
                current_player_sums[position][player_id] += points
                current_player_counts[position][player_id] += 1
                current_position_sums[position] += points
                current_position_counts[position] += 1

    return examples


def _project(example: dict[str, Any], baseline_variant: str, k: float) -> float | None:
    baseline = example["Baselines"].get(baseline_variant)
    if baseline is None:
        return None
    prior_games = int(example["PriorGames"])
    current_ppg = example.get("CurrentSeasonPPG")
    if prior_games <= 0 or current_ppg is None:
        return float(baseline)
    weight = prior_games / (prior_games + k) if k > 0 else 1.0
    return float(current_ppg) * weight + float(baseline) * (1.0 - weight)


def _scored_rows(
    examples: Iterable[dict[str, Any]],
    *,
    baseline_variant: str,
    k: float,
    comparable_only: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        if comparable_only and int(example["PriorGames"]) <= 0:
            continue
        projection = _project(example, baseline_variant, k)
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


def _v1_rows(examples: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        if int(example["PriorGames"]) <= 0 or example.get("CurrentSeasonPPG") is None:
            continue
        projection = float(example["CurrentSeasonPPG"])
        rows.append(
            {
                **example,
                "Projection": projection,
                "Error": projection - float(example["Actual"]),
            }
        )
    return rows


def _breakdowns(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_prior_games: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_position[str(row["Position"])].append(row)
        by_week[int(row["Week"])].append(row)
        by_prior_games[int(row["PriorGames"])].append(row)
    return {
        "ByPosition": {key: _metrics(value) for key, value in sorted(by_position.items())},
        "ByWeek": {str(key): _metrics(value) for key, value in sorted(by_week.items())},
        "ByPriorGames": {
            str(key): _metrics(value) for key, value in sorted(by_prior_games.items())
        },
    }


def calibrate_v2(
    examples: list[dict[str, Any]],
    *,
    calibration_seasons: list[int],
    k_grid: tuple[float, ...] = K_GRID,
) -> dict[str, Any]:
    calibration = [
        row
        for row in examples
        if int(row["Season"]) in calibration_seasons and int(row["PriorGames"]) > 0
    ]
    leaderboard: list[dict[str, Any]] = []

    for baseline_variant in BASELINE_VARIANTS:
        for k in k_grid:
            rows = _scored_rows(
                calibration,
                baseline_variant=baseline_variant,
                k=float(k),
                comparable_only=True,
            )
            metrics = _metrics(rows)
            if metrics["Count"] == 0:
                continue
            leaderboard.append(
                {
                    "BaselineVariant": baseline_variant,
                    "K": float(k),
                    "Metrics": metrics,
                }
            )

    if not leaderboard:
        raise ValueError("V2 calibration produced no comparable predictions")

    leaderboard.sort(
        key=lambda row: (
            float(row["Metrics"]["MAE"]),
            float(row["Metrics"]["RMSE"]),
            abs(float(row["Metrics"]["Bias"])),
            float(row["K"]),
            str(row["BaselineVariant"]),
        )
    )
    best = leaderboard[0]
    return {
        "CalibrationSeasons": calibration_seasons,
        "ComparableObservationCount": len(calibration),
        "KGrid": list(k_grid),
        "Selected": best,
        "LeaderboardTop20": leaderboard[:20],
    }


def evaluate_v2_holdout(
    examples: list[dict[str, Any]],
    *,
    holdout_season: int,
    baseline_variant: str,
    k: float,
) -> dict[str, Any]:
    holdout = [row for row in examples if int(row["Season"]) == holdout_season]
    v1_rows = _v1_rows(holdout)
    v2_comparable = _scored_rows(
        holdout,
        baseline_variant=baseline_variant,
        k=k,
        comparable_only=True,
    )

    v1_keys = {
        (row["Season"], row["Week"], row["CanonicalPlayerID"]) for row in v1_rows
    }
    v2_comparable = [
        row
        for row in v2_comparable
        if (row["Season"], row["Week"], row["CanonicalPlayerID"]) in v1_keys
    ]
    v2_all = _scored_rows(
        holdout,
        baseline_variant=baseline_variant,
        k=k,
        comparable_only=False,
    )
    v2_cold = [row for row in v2_all if int(row["PriorGames"]) == 0]

    v1_metrics = _metrics(v1_rows)
    v2_metrics = _metrics(v2_comparable)
    all_metrics = _metrics(v2_all)
    cold_metrics = _metrics(v2_cold)

    mae_improvement = float(v1_metrics["MAE"]) - float(v2_metrics["MAE"])
    rmse_improvement = float(v1_metrics["RMSE"]) - float(v2_metrics["RMSE"])

    return {
        "HoldoutSeason": holdout_season,
        "SelectedBaselineVariant": baseline_variant,
        "SelectedK": k,
        "Comparable": {
            "V1": v1_metrics,
            "V2": v2_metrics,
            "MAEImprovementPoints": round(mae_improvement, 4),
            "MAEImprovementPercent": round(
                100.0 * mae_improvement / float(v1_metrics["MAE"]),
                4,
            ),
            "RMSEImprovementPoints": round(rmse_improvement, 4),
            "RMSEImprovementPercent": round(
                100.0 * rmse_improvement / float(v1_metrics["RMSE"]),
                4,
            ),
            "V1Breakdowns": _breakdowns(v1_rows),
            "V2Breakdowns": _breakdowns(v2_comparable),
        },
        "ExpandedCoverage": {
            "Metrics": all_metrics,
            "ColdStartMetrics": cold_metrics,
            "AdditionalColdStartPredictions": len(v2_cold),
            "TotalPredictions": len(v2_all),
        },
    }


def build_v2_calibration_report(
    repo_root: Path,
    *,
    league_id: str,
    scoring_season: int,
    calibration_seasons: list[int],
    holdout_season: int,
    first_week: int = 1,
    last_week: int = 18,
) -> dict[str, Any]:
    all_target_seasons = sorted(set(calibration_seasons + [holdout_season]))
    required_seasons = sorted(set([season - 1 for season in all_target_seasons] + all_target_seasons))
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

    examples = build_v2_examples(
        observations_by_season,
        target_seasons=all_target_seasons,
    )
    calibration = calibrate_v2(
        examples,
        calibration_seasons=calibration_seasons,
    )
    selected = calibration["Selected"]
    holdout = evaluate_v2_holdout(
        examples,
        holdout_season=holdout_season,
        baseline_variant=str(selected["BaselineVariant"]),
        k=float(selected["K"]),
    )

    return {
        "ContractVersion": 2,
        "Model": "v2-shrunk-current-season-ppg",
        "League": league_id,
        "ScoringSeason": scoring_season,
        "CalibrationSeasons": calibration_seasons,
        "HoldoutSeason": holdout_season,
        "FirstWeek": first_week,
        "LastWeek": last_week,
        "Formula": "Projection = CurrentSeasonPPG * w + Baseline * (1 - w); w = PriorGames / (PriorGames + k)",
        "SelectionRule": "select baseline variant and k by lowest calibration MAE on V1-comparable player-games; tie-break RMSE, absolute bias, lower k",
        "LeakageRule": "calibration uses only seasons before holdout; each target-week projection uses only prior weeks plus completed prior-season position evidence",
        "BaselineRule": "position baselines are leave-one-player-out; current-season baseline uses only weeks < W and falls back to previous-season position mean",
        "ColdStartRule": "PriorGames=0 receives pure selected position baseline when available",
        "ObservationAudits": observation_audits,
        "Calibration": calibration,
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
    report = build_v2_calibration_report(
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
