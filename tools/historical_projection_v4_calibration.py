#!/usr/bin/env python3
"""Evaluate V4 role/usage projection variants on top of the accepted V3 benchmark."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from historical_fantasy_scoring import number, read_json
from historical_projection_backtest import (
    FANTASY_POSITIONS,
    _metrics,
    _require_finalized_partition,
    _scoring_profile,
    build_scored_played_games,
)
from historical_projection_v2_calibration import _breakdowns
from historical_projection_v3_calibration import (
    HISTORY_TWO_SEASON,
    _v3_projection,
    build_v3_examples,
)

RECENT_WINDOW = 3
HISTORY_DECAY = 0.25
V3_HISTORY_K = 0.0
V3_CURRENT_K = 1.0

VARIANT_SNAP = "v4-a-snap-trend"
VARIANT_OPPORTUNITY = "v4-b-opportunity-trend"
VARIANT_COMBINED = "v4-c-snap-plus-opportunity"
VARIANTS = (VARIANT_SNAP, VARIANT_OPPORTUNITY, VARIANT_COMBINED)

RIDGE_GRID = (0.0, 0.25, 1.0, 4.0, 16.0, 64.0)
CLIP_GRID: tuple[float | None, ...] = (2.0, 4.0, 6.0, 8.0, None)

FEATURE_SNAP = "SnapTrend"
FEATURE_OPPORTUNITY = "OpportunityTrend"


def _position_group(position: str) -> str:
    position = position.upper()
    if position == "FB":
        return "RB"
    return position


def _opportunity_value(position: str, stats: dict[str, Any]) -> float:
    position = _position_group(position)
    if position == "QB":
        return number(stats.get("attempts")) + number(stats.get("carries"))
    if position == "RB":
        return number(stats.get("carries")) + number(stats.get("targets"))
    if position in {"WR", "TE"}:
        return number(stats.get("targets"))
    if position == "K":
        return number(stats.get("fg_att")) + number(stats.get("pat_att"))
    return 0.0


def _snap_pct_by_player(
    repo_root: Path,
    season: int,
    week: int,
) -> dict[str, float]:
    path = repo_root / "source-data/nfl/snap-counts" / str(season) / f"{week:02d}.json"
    payload = _require_finalized_partition(path, season, week)
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ValueError(f"Canonical snap-count partition has no Records array: {path}")

    result: dict[str, float] = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError(f"Canonical snap-count partition contains a non-object row: {path}")
        player_id = row.get("CanonicalPlayerID")
        if not isinstance(player_id, str) or not player_id:
            continue
        value = row.get("OffensePct")
        if value is None or value == "":
            continue
        pct = float(value)
        # A player should only have one NFL game in a week. max() keeps the
        # feature deterministic if duplicate game-level evidence ever appears.
        result[player_id] = max(result.get(player_id, 0.0), pct)
    return result


def _usage_by_week(
    repo_root: Path,
    *,
    season: int,
    first_week: int,
    last_week: int,
) -> dict[int, dict[str, dict[str, Any]]]:
    result: dict[int, dict[str, dict[str, Any]]] = {}

    for week in range(first_week, last_week + 1):
        stats_path = (
            repo_root / "source-data/nfl/player-stats" / str(season) / f"{week:02d}.json"
        )
        payload = _require_finalized_partition(stats_path, season, week)
        records = payload.get("Records")
        if not isinstance(records, list):
            raise ValueError(f"Canonical player-stats partition has no Records array: {stats_path}")

        snap_pct = _snap_pct_by_player(repo_root, season, week)
        rows: dict[str, dict[str, Any]] = {}
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Canonical player-stats contains a non-object row: {stats_path}")
            position = str(record.get("Position") or "").upper()
            if position not in FANTASY_POSITIONS:
                continue
            player_id = record.get("CanonicalPlayerID")
            if not isinstance(player_id, str) or not player_id:
                continue
            stats = record.get("Stats")
            if not isinstance(stats, dict):
                raise ValueError(
                    f"Canonical player stat record has no Stats object: {season}/W{week}/{player_id}"
                )
            rows[player_id] = {
                "Position": position,
                "SnapShare": None if position == "K" else snap_pct.get(player_id),
                "Opportunity": _opportunity_value(position, stats),
            }
        result[week] = rows

    return result


def _usage_season_summaries(
    usage_by_week: dict[int, dict[str, dict[str, Any]]],
    played_ids_by_week: dict[int, set[str]],
) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"SnapShare": 0.0, "Opportunity": 0.0}
    )
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"SnapShare": 0, "Opportunity": 0}
    )

    for week, rows in usage_by_week.items():
        played_ids = played_ids_by_week.get(week, set())
        for player_id, row in rows.items():
            if player_id not in played_ids:
                continue
            snap = row.get("SnapShare")
            if snap is not None:
                totals[player_id]["SnapShare"] += float(snap)
                counts[player_id]["SnapShare"] += 1
            opportunity = row.get("Opportunity")
            if opportunity is not None:
                totals[player_id]["Opportunity"] += float(opportunity)
                counts[player_id]["Opportunity"] += 1

    result: dict[str, dict[str, Any]] = {}
    for player_id in set(totals) | set(counts):
        result[player_id] = {}
        for feature in ("SnapShare", "Opportunity"):
            count = counts[player_id][feature]
            result[player_id][feature] = {
                "Count": count,
                "Mean": totals[player_id][feature] / count if count > 0 else None,
            }
    return result


def _historical_usage_baseline(
    player_id: str,
    *,
    target_season: int,
    feature: str,
    season_summaries: dict[int, dict[str, dict[str, Any]]],
) -> float | None:
    weighted_total = 0.0
    effective_count = 0.0
    for season, weight in (
        (target_season - 1, 1.0),
        (target_season - 2, HISTORY_DECAY),
    ):
        row = season_summaries.get(season, {}).get(player_id, {}).get(feature)
        if not isinstance(row, dict):
            continue
        mean = row.get("Mean")
        count = int(row.get("Count") or 0)
        if mean is None or count <= 0:
            continue
        weighted_count = float(count) * weight
        weighted_total += float(mean) * weighted_count
        effective_count += weighted_count
    if effective_count <= 0:
        return None
    return weighted_total / effective_count


def _recent_mean(history: list[dict[str, Any]], feature: str) -> float | None:
    values = [
        float(row[feature])
        for row in history[-RECENT_WINDOW:]
        if row.get(feature) is not None
    ]
    return sum(values) / len(values) if values else None


def _fallback_older_current_mean(
    history: list[dict[str, Any]],
    feature: str,
) -> float | None:
    if len(history) <= RECENT_WINDOW:
        return None
    values = [
        float(row[feature])
        for row in history[:-RECENT_WINDOW]
        if row.get(feature) is not None
    ]
    return sum(values) / len(values) if values else None


def build_v4_examples(
    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]],
    usage_by_season: dict[int, dict[int, dict[str, dict[str, Any]]]],
    *,
    target_seasons: list[int],
) -> list[dict[str, Any]]:
    examples = build_v3_examples(
        observations_by_season,
        target_seasons=target_seasons,
    )
    example_by_key = {
        (int(row["Season"]), int(row["Week"]), str(row["CanonicalPlayerID"])): row
        for row in examples
    }

    played_ids_by_season = {
        season: {
            week: {str(row["CanonicalPlayerID"]) for row in rows}
            for week, rows in observations_by_week.items()
        }
        for season, observations_by_week in observations_by_season.items()
    }
    season_summaries = {
        season: _usage_season_summaries(
            usage_by_season[season],
            played_ids_by_season[season],
        )
        for season in usage_by_season
    }

    for season in target_seasons:
        current_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for week in sorted(observations_by_season[season]):
            observations = observations_by_season[season][week]
            week_usage = usage_by_season[season].get(week, {})

            for observation in observations:
                player_id = str(observation["CanonicalPlayerID"])
                key = (season, week, player_id)
                example = example_by_key[key]
                history = current_history.get(player_id, [])

                for feature, history_key in (
                    (FEATURE_SNAP, "SnapShare"),
                    (FEATURE_OPPORTUNITY, "Opportunity"),
                ):
                    recent = _recent_mean(history, history_key)
                    baseline = _historical_usage_baseline(
                        player_id,
                        target_season=season,
                        feature=history_key,
                        season_summaries=season_summaries,
                    )
                    baseline_source = "completed-history"
                    if baseline is None:
                        baseline = _fallback_older_current_mean(history, history_key)
                        baseline_source = (
                            "older-current-season" if baseline is not None else "unavailable"
                        )

                    available = recent is not None and baseline is not None
                    example[feature] = (
                        float(recent) - float(baseline) if available else 0.0
                    )
                    example[f"{feature}Available"] = available
                    example[f"{feature}Recent"] = recent
                    example[f"{feature}Baseline"] = baseline
                    example[f"{feature}BaselineSource"] = baseline_source

            # Current Week W usage enters state only after every W projection feature
            # has been fixed.
            for observation in observations:
                player_id = str(observation["CanonicalPlayerID"])
                usage = week_usage.get(player_id)
                if usage is None:
                    continue
                current_history[player_id].append(
                    {
                        "SnapShare": usage.get("SnapShare"),
                        "Opportunity": usage.get("Opportunity"),
                    }
                )

    return examples


def _v3_rows(
    examples: Iterable[dict[str, Any]],
    *,
    seasons: set[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example in examples:
        if int(example["Season"]) not in seasons or int(example["PriorGames"]) <= 0:
            continue
        projection, _history_backed = _v3_projection(
            example,
            variant=HISTORY_TWO_SEASON,
            decay=HISTORY_DECAY,
            history_k=V3_HISTORY_K,
            current_k=V3_CURRENT_K,
        )
        if projection is None:
            continue
        rows.append(
            {
                **example,
                "V3Projection": float(projection),
                "V3Residual": float(example["Actual"]) - float(projection),
                "PositionGroup": _position_group(str(example["Position"])),
            }
        )
    return rows


def _features_for_variant(variant: str) -> tuple[str, ...]:
    if variant == VARIANT_SNAP:
        return (FEATURE_SNAP,)
    if variant == VARIANT_OPPORTUNITY:
        return (FEATURE_OPPORTUNITY,)
    if variant == VARIANT_COMBINED:
        return (FEATURE_SNAP, FEATURE_OPPORTUNITY)
    raise ValueError(f"Unknown V4 variant: {variant}")


def _feature_scale(
    rows: list[dict[str, Any]],
    feature: str,
) -> float:
    values = [
        float(row[feature])
        for row in rows
        if bool(row.get(f"{feature}Available"))
    ]
    if not values:
        return 1.0
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return rms if rms > 1e-12 else 1.0


def _solve_ridge(
    rows: list[dict[str, Any]],
    features: tuple[str, ...],
    *,
    ridge: float,
) -> dict[str, Any]:
    scales = {feature: _feature_scale(rows, feature) for feature in features}
    if len(features) == 1:
        feature = features[0]
        xx = 0.0
        xy = 0.0
        for row in rows:
            x = float(row[feature]) / scales[feature]
            y = float(row["V3Residual"])
            xx += x * x
            xy += x * y
        beta = xy / (xx + ridge) if xx + ridge > 0 else 0.0
        return {"Scales": scales, "Betas": {feature: beta}}

    if len(features) != 2:
        raise ValueError("V4 ridge solver supports one or two features")

    f1, f2 = features
    a11 = ridge
    a12 = 0.0
    a22 = ridge
    b1 = 0.0
    b2 = 0.0
    for row in rows:
        x1 = float(row[f1]) / scales[f1]
        x2 = float(row[f2]) / scales[f2]
        y = float(row["V3Residual"])
        a11 += x1 * x1
        a12 += x1 * x2
        a22 += x2 * x2
        b1 += x1 * y
        b2 += x2 * y

    determinant = a11 * a22 - a12 * a12
    if abs(determinant) <= 1e-12:
        beta1 = 0.0
        beta2 = 0.0
    else:
        beta1 = (b1 * a22 - b2 * a12) / determinant
        beta2 = (a11 * b2 - a12 * b1) / determinant
    return {"Scales": scales, "Betas": {f1: beta1, f2: beta2}}


def fit_variant(
    rows: list[dict[str, Any]],
    *,
    variant: str,
    ridge: float,
) -> dict[str, Any]:
    features = _features_for_variant(variant)
    by_position: dict[str, Any] = {}
    for position in sorted({str(row["PositionGroup"]) for row in rows}):
        position_rows = [row for row in rows if row["PositionGroup"] == position]
        by_position[position] = _solve_ridge(
            position_rows,
            features,
            ridge=ridge,
        )
    return {
        "Variant": variant,
        "Ridge": ridge,
        "Features": list(features),
        "ByPosition": by_position,
    }


def _adjustment(
    row: dict[str, Any],
    fit: dict[str, Any],
) -> float:
    position = str(row["PositionGroup"])
    position_fit = fit["ByPosition"].get(position)
    if not isinstance(position_fit, dict):
        return 0.0
    total = 0.0
    for feature in fit["Features"]:
        scale = float(position_fit["Scales"][feature])
        beta = float(position_fit["Betas"][feature])
        total += beta * (float(row[feature]) / scale)
    return total


def evaluate_variant(
    rows: list[dict[str, Any]],
    *,
    fit: dict[str, Any],
    clip: float | None,
) -> dict[str, Any]:
    predictions: list[dict[str, Any]] = []
    adjusted_count = 0
    clipped_count = 0

    for row in rows:
        raw_adjustment = _adjustment(row, fit)
        adjustment = raw_adjustment
        if clip is not None:
            adjustment = max(-clip, min(clip, adjustment))
            if adjustment != raw_adjustment:
                clipped_count += 1
        if abs(adjustment) > 1e-12:
            adjusted_count += 1
        projection = float(row["V3Projection"]) + adjustment
        predictions.append(
            {
                **row,
                "Projection": projection,
                "Adjustment": adjustment,
                "Error": projection - float(row["Actual"]),
            }
        )

    return {
        "Metrics": _metrics(predictions),
        "Breakdowns": _breakdowns(predictions),
        "AdjustedCount": adjusted_count,
        "ClippedCount": clipped_count,
        "Rows": predictions,
    }


def calibrate_variant(
    examples: list[dict[str, Any]],
    *,
    variant: str,
    development_season: int,
    validation_season: int,
    calibration_seasons: list[int],
) -> dict[str, Any]:
    development_rows = _v3_rows(examples, seasons={development_season})
    validation_rows = _v3_rows(examples, seasons={validation_season})
    calibration_rows = _v3_rows(examples, seasons=set(calibration_seasons))

    leaderboard: list[dict[str, Any]] = []
    for ridge in RIDGE_GRID:
        fit = fit_variant(development_rows, variant=variant, ridge=ridge)
        for clip in CLIP_GRID:
            evaluated = evaluate_variant(validation_rows, fit=fit, clip=clip)
            metrics = evaluated["Metrics"]
            leaderboard.append(
                {
                    "Ridge": ridge,
                    "Clip": clip,
                    "Metrics": metrics,
                    "AdjustedCount": evaluated["AdjustedCount"],
                    "ClippedCount": evaluated["ClippedCount"],
                }
            )

    leaderboard.sort(
        key=lambda row: (
            float(row["Metrics"]["MAE"]),
            float(row["Metrics"]["RMSE"]),
            abs(float(row["Metrics"]["Bias"])),
            float("inf") if row["Clip"] is None else float(row["Clip"]),
            float(row["Ridge"]),
        )
    )
    selected = leaderboard[0]
    final_fit = fit_variant(
        calibration_rows,
        variant=variant,
        ridge=float(selected["Ridge"]),
    )
    return {
        "Variant": variant,
        "DevelopmentSeason": development_season,
        "ValidationSeason": validation_season,
        "CalibrationSeasons": calibration_seasons,
        "Selected": selected,
        "FinalFit": final_fit,
        "Leaderboard": leaderboard,
    }


def evaluate_holdout(
    examples: list[dict[str, Any]],
    *,
    holdout_season: int,
    calibrations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = _v3_rows(examples, seasons={holdout_season})
    baseline_rows = [
        {
            **row,
            "Projection": float(row["V3Projection"]),
            "Error": float(row["V3Projection"]) - float(row["Actual"]),
        }
        for row in rows
    ]
    result: dict[str, Any] = {
        "V3": {
            "Metrics": _metrics(baseline_rows),
            "Breakdowns": _breakdowns(baseline_rows),
            "PredictionCount": len(baseline_rows),
        }
    }

    for variant, calibration in calibrations.items():
        selected = calibration["Selected"]
        evaluated = evaluate_variant(
            rows,
            fit=calibration["FinalFit"],
            clip=selected["Clip"],
        )
        v4_metrics = evaluated["Metrics"]
        v3_metrics = result["V3"]["Metrics"]
        result[variant] = {
            "Metrics": v4_metrics,
            "Breakdowns": evaluated["Breakdowns"],
            "PredictionCount": len(evaluated["Rows"]),
            "AdjustedCount": evaluated["AdjustedCount"],
            "ClippedCount": evaluated["ClippedCount"],
            "MAEImprovementPoints": round(
                float(v3_metrics["MAE"]) - float(v4_metrics["MAE"]),
                4,
            ),
            "RMSEImprovementPoints": round(
                float(v3_metrics["RMSE"]) - float(v4_metrics["RMSE"]),
                4,
            ),
        }
    return result


def build_v4_report(
    repo_root: Path,
    *,
    league_id: str,
    scoring_season: int,
    calibration_seasons: list[int],
    holdout_season: int,
    first_week: int = 1,
    last_week: int = 18,
) -> dict[str, Any]:
    if len(calibration_seasons) < 2:
        raise ValueError("V4 requires at least two calibration seasons")
    development_season = calibration_seasons[0]
    validation_season = calibration_seasons[-1]
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
    usage_by_season: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}

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
        usage_by_season[season] = _usage_by_week(
            repo_root,
            season=season,
            first_week=first_week,
            last_week=last_week,
        )

    examples = build_v4_examples(
        observations_by_season,
        usage_by_season,
        target_seasons=target_seasons,
    )

    calibrations = {
        variant: calibrate_variant(
            examples,
            variant=variant,
            development_season=development_season,
            validation_season=validation_season,
            calibration_seasons=calibration_seasons,
        )
        for variant in VARIANTS
    }
    holdout = evaluate_holdout(
        examples,
        holdout_season=holdout_season,
        calibrations=calibrations,
    )

    return {
        "ContractVersion": 4,
        "Model": "v4-role-usage-adjustment-on-v3",
        "League": league_id,
        "ScoringSeason": scoring_season,
        "CalibrationSeasons": calibration_seasons,
        "DevelopmentSeason": development_season,
        "ValidationSeason": validation_season,
        "HoldoutSeason": holdout_season,
        "FirstWeek": first_week,
        "LastWeek": last_week,
        "V3Contract": {
            "HistoryVariant": HISTORY_TWO_SEASON,
            "TMinus1Weight": 1.0,
            "TMinus2Weight": HISTORY_DECAY,
            "HistoryK": V3_HISTORY_K,
            "CurrentK": V3_CURRENT_K,
        },
        "UsageContract": {
            "RecentWindowPlayedGames": RECENT_WINDOW,
            "HistoricalBaseline": (
                "player mean from T-1 weight 1.0 plus T-2 weight 0.25; "
                "if unavailable, older current-season games before the recent window"
            ),
            "SnapTrend": (
                "recent offense snap share minus historical/fallback baseline; "
                "K receives no snap adjustment"
            ),
            "OpportunityTrend": {
                "QB": "pass attempts + carries",
                "RB/FB": "carries + targets",
                "WR/TE": "targets",
                "K": "field-goal attempts + PAT attempts",
            },
            "LeakageRule": (
                "Week W fantasy points, snaps and opportunities never enter Week W features; "
                "2025 never participates in coefficient or hyperparameter selection"
            ),
        },
        "CalibrationMethod": (
            "fit position-specific additive residual adjustment on 2023; select ridge/clip on 2024; "
            "refit selected ridge on 2023+2024; evaluate untouched 2025"
        ),
        "ObservationAudits": observation_audits,
        "Calibrations": calibrations,
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
    report = build_v4_report(
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
