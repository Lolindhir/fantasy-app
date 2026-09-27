#!/usr/bin/env python3
"""Calibrate empirical player prediction intervals around the accepted V4-C point model."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from historical_projection_backtest import _scoring_profile, build_scored_played_games
from historical_projection_v4_calibration import (
    VARIANT_COMBINED,
    _position_group,
    _usage_by_week,
    _v3_rows,
    build_v4_examples,
    evaluate_variant,
    fit_variant,
)

V4_C_RIDGE = 64.0
V4_C_CLIP = 4.0
CALIBRATION_SEASON = 2024
HOLDOUT_SEASON = 2025
INTERVAL_LEVELS = (0.50, 0.80, 0.90, 0.95)
MIN_GROUP_SIZE = 60

STRATEGY_GLOBAL = "global"
STRATEGY_POSITION = "position"
STRATEGY_POSITION_PROJECTION = "position-projection"
STRATEGY_POSITION_PROJECTION_VOLATILITY = "position-projection-volatility"
STRATEGIES = (
    STRATEGY_GLOBAL,
    STRATEGY_POSITION,
    STRATEGY_POSITION_PROJECTION,
    STRATEGY_POSITION_PROJECTION_VOLATILITY,
)


def _quantile(values: list[float], probability: float) -> float:
    """Linear empirical quantile, used only for bucket thresholds."""
    if not values:
        raise ValueError("Cannot compute a quantile from an empty sample")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    probability = max(0.0, min(1.0, probability))
    index = probability * (len(ordered) - 1)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _conservative_residual_quantile(
    values: list[float],
    probability: float,
    *,
    side: str,
) -> float:
    """Return an outward empirical order statistic for prediction bounds.

    For lower bounds we round the requested order-statistic rank downward; for
    upper bounds we round upward. This is deliberately a little conservative
    versus interpolating signed residual quantiles.
    """
    if not values:
        raise ValueError("Cannot calibrate an interval from an empty residual sample")
    ordered = sorted(values)
    n = len(ordered)
    raw_rank = (n + 1) * probability
    if side == "lower":
        rank = math.floor(raw_rank)
    elif side == "upper":
        rank = math.ceil(raw_rank)
    else:
        raise ValueError(f"Unknown quantile side: {side}")
    rank = max(1, min(n, rank))
    return ordered[rank - 1]


def _population_std(values: list[float]) -> float | None:
    if len(values) < 4:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def build_prior_score_volatility(
    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]],
    *,
    target_seasons: Iterable[int],
) -> dict[tuple[int, int, str], float | None]:
    """Build a pregame player volatility proxy without target-week leakage.

    The proxy is the population standard deviation of the player's fantasy
    scores from the previous two completed seasons plus prior target-season
    played games. At least four historical games are required.
    """
    result: dict[tuple[int, int, str], float | None] = {}

    for season in target_seasons:
        completed_history: dict[str, list[float]] = defaultdict(list)
        for prior_season in (season - 2, season - 1):
            for rows in observations_by_season.get(prior_season, {}).values():
                for row in rows:
                    completed_history[str(row["CanonicalPlayerID"])].append(
                        float(row["FantasyPoints"])
                    )

        current_history: dict[str, list[float]] = defaultdict(list)
        for week in sorted(observations_by_season.get(season, {})):
            rows = observations_by_season[season][week]
            for row in rows:
                player_id = str(row["CanonicalPlayerID"])
                history = completed_history.get(player_id, []) + current_history.get(
                    player_id, []
                )
                result[(season, week, player_id)] = _population_std(history)

            # Week W outcome becomes available only after the Week W feature is fixed.
            for row in rows:
                current_history[str(row["CanonicalPlayerID"])].append(
                    float(row["FantasyPoints"])
                )

    return result


def _enrich_volatility(
    rows: list[dict[str, Any]],
    volatility_by_key: dict[tuple[int, int, str], float | None],
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "PriorScoreVolatility": volatility_by_key.get(
                (
                    int(row["Season"]),
                    int(row["Week"]),
                    str(row["CanonicalPlayerID"]),
                )
            ),
        }
        for row in rows
    ]


def _projection_thresholds(
    calibration_rows: list[dict[str, Any]],
) -> dict[str, tuple[float, float]]:
    by_position: dict[str, list[float]] = defaultdict(list)
    for row in calibration_rows:
        by_position[str(row["PositionGroup"])].append(float(row["Projection"]))
    return {
        position: (_quantile(values, 1.0 / 3.0), _quantile(values, 2.0 / 3.0))
        for position, values in by_position.items()
    }


def _projection_bucket(
    row: dict[str, Any],
    thresholds: dict[str, tuple[float, float]],
) -> str:
    position = str(row["PositionGroup"])
    low, high = thresholds[position]
    projection = float(row["Projection"])
    if projection <= low:
        return "low"
    if projection <= high:
        return "mid"
    return "high"


def _volatility_thresholds(
    calibration_rows: list[dict[str, Any]],
    projection_thresholds: dict[str, tuple[float, float]],
) -> dict[str, float]:
    by_group: dict[str, list[float]] = defaultdict(list)
    for row in calibration_rows:
        volatility = row.get("PriorScoreVolatility")
        if volatility is None:
            continue
        key = (
            f'{row["PositionGroup"]}|'
            f'{_projection_bucket(row, projection_thresholds)}'
        )
        by_group[key].append(float(volatility))
    return {
        key: _quantile(values, 0.5)
        for key, values in by_group.items()
        if values
    }


def _volatility_bucket(
    row: dict[str, Any],
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> str | None:
    volatility = row.get("PriorScoreVolatility")
    if volatility is None:
        return None
    base = (
        f'{row["PositionGroup"]}|'
        f'{_projection_bucket(row, projection_thresholds)}'
    )
    threshold = volatility_thresholds.get(base)
    if threshold is None:
        return None
    return "low" if float(volatility) <= threshold else "high"


def _group_candidates(
    row: dict[str, Any],
    *,
    strategy: str,
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> list[str]:
    position = str(row["PositionGroup"])
    projection_bucket = _projection_bucket(row, projection_thresholds)
    position_projection = f"{position}|{projection_bucket}"

    if strategy == STRATEGY_GLOBAL:
        return ["global"]
    if strategy == STRATEGY_POSITION:
        return [position, "global"]
    if strategy == STRATEGY_POSITION_PROJECTION:
        return [position_projection, position, "global"]
    if strategy == STRATEGY_POSITION_PROJECTION_VOLATILITY:
        volatility_bucket = _volatility_bucket(
            row,
            projection_thresholds,
            volatility_thresholds,
        )
        candidates: list[str] = []
        if volatility_bucket is not None:
            candidates.append(f"{position_projection}|{volatility_bucket}")
        candidates.extend([position_projection, position, "global"])
        return candidates
    raise ValueError(f"Unknown interval strategy: {strategy}")


def _residual_groups(
    calibration_rows: list[dict[str, Any]],
    *,
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> dict[str, list[float]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in calibration_rows:
        residual = float(row["Actual"]) - float(row["Projection"])
        position = str(row["PositionGroup"])
        projection_bucket = _projection_bucket(row, projection_thresholds)
        position_projection = f"{position}|{projection_bucket}"

        groups["global"].append(residual)
        groups[position].append(residual)
        groups[position_projection].append(residual)

        volatility_bucket = _volatility_bucket(
            row,
            projection_thresholds,
            volatility_thresholds,
        )
        if volatility_bucket is not None:
            groups[f"{position_projection}|{volatility_bucket}"].append(residual)

    return dict(groups)


def _selected_group(
    row: dict[str, Any],
    *,
    strategy: str,
    groups: dict[str, list[float]],
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> str:
    for key in _group_candidates(
        row,
        strategy=strategy,
        projection_thresholds=projection_thresholds,
        volatility_thresholds=volatility_thresholds,
    ):
        if key == "global" or len(groups.get(key, [])) >= MIN_GROUP_SIZE:
            return key
    return "global"


def _interval_for_row(
    row: dict[str, Any],
    *,
    level: float,
    strategy: str,
    groups: dict[str, list[float]],
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> dict[str, Any]:
    group = _selected_group(
        row,
        strategy=strategy,
        groups=groups,
        projection_thresholds=projection_thresholds,
        volatility_thresholds=volatility_thresholds,
    )
    residuals = groups[group]
    alpha = 1.0 - level
    lower_residual = _conservative_residual_quantile(
        residuals,
        alpha / 2.0,
        side="lower",
    )
    upper_residual = _conservative_residual_quantile(
        residuals,
        1.0 - alpha / 2.0,
        side="upper",
    )
    projection = float(row["Projection"])
    return {
        "Lower": projection + lower_residual,
        "Upper": projection + upper_residual,
        "LowerResidual": lower_residual,
        "UpperResidual": upper_residual,
        "Group": group,
        "CalibrationCount": len(residuals),
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return _quantile(values, 0.5)


def _evaluate_level(
    rows: list[dict[str, Any]],
    *,
    level: float,
    strategy: str,
    groups: dict[str, list[float]],
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> dict[str, Any]:
    evaluated: list[dict[str, Any]] = []
    lower_misses = 0
    upper_misses = 0

    for row in rows:
        interval = _interval_for_row(
            row,
            level=level,
            strategy=strategy,
            groups=groups,
            projection_thresholds=projection_thresholds,
            volatility_thresholds=volatility_thresholds,
        )
        actual = float(row["Actual"])
        lower = float(interval["Lower"])
        upper = float(interval["Upper"])
        if actual < lower:
            lower_misses += 1
        elif actual > upper:
            upper_misses += 1
        evaluated.append(
            {
                **row,
                **interval,
                "Covered": lower <= actual <= upper,
                "Width": upper - lower,
                "LowerDistance": float(row["Projection"]) - lower,
                "UpperDistance": upper - float(row["Projection"]),
            }
        )

    count = len(evaluated)
    covered = sum(1 for row in evaluated if row["Covered"])
    widths = [float(row["Width"]) for row in evaluated]
    lower_distances = [float(row["LowerDistance"]) for row in evaluated]
    upper_distances = [float(row["UpperDistance"]) for row in evaluated]

    return {
        "NominalCoveragePercent": round(level * 100.0, 2),
        "Count": count,
        "CoveredCount": covered,
        "CoveragePercent": round(100.0 * covered / count, 4) if count else None,
        "CoverageErrorPoints": (
            round(100.0 * covered / count - level * 100.0, 4) if count else None
        ),
        "MeanWidth": round(sum(widths) / count, 4) if count else None,
        "MedianWidth": round(float(_median(widths)), 4) if count else None,
        "MeanLowerDistance": (
            round(sum(lower_distances) / count, 4) if count else None
        ),
        "MeanUpperDistance": (
            round(sum(upper_distances) / count, 4) if count else None
        ),
        "LowerMissCount": lower_misses,
        "UpperMissCount": upper_misses,
        "LowerMissPercent": round(100.0 * lower_misses / count, 4) if count else None,
        "UpperMissPercent": round(100.0 * upper_misses / count, 4) if count else None,
        "Rows": evaluated,
    }


def _strip_rows(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "Rows"}


def evaluate_strategy(
    holdout_rows: list[dict[str, Any]],
    *,
    strategy: str,
    groups: dict[str, list[float]],
    projection_thresholds: dict[str, tuple[float, float]],
    volatility_thresholds: dict[str, float],
) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    raw_90: dict[str, Any] | None = None

    for level in INTERVAL_LEVELS:
        result = _evaluate_level(
            holdout_rows,
            level=level,
            strategy=strategy,
            groups=groups,
            projection_thresholds=projection_thresholds,
            volatility_thresholds=volatility_thresholds,
        )
        levels[str(int(level * 100))] = _strip_rows(result)
        if level == 0.90:
            raw_90 = result

    assert raw_90 is not None
    rows_90 = raw_90["Rows"]

    by_position = {}
    for position in sorted({str(row["PositionGroup"]) for row in rows_90}):
        subset = [row for row in rows_90 if str(row["PositionGroup"]) == position]
        count = len(subset)
        covered = sum(1 for row in subset if row["Covered"])
        widths = [float(row["Width"]) for row in subset]
        by_position[position] = {
            "Count": count,
            "CoveragePercent": round(100.0 * covered / count, 4),
            "MeanWidth": round(sum(widths) / count, 4),
        }

    fallback_usage: dict[str, int] = defaultdict(int)
    for row in rows_90:
        fallback_usage[str(row["Group"])] += 1

    volatility_width: dict[str, Any] = {}
    if strategy == STRATEGY_POSITION_PROJECTION_VOLATILITY:
        for volatility_class in ("low", "high", "unavailable"):
            subset = []
            for row in rows_90:
                bucket = _volatility_bucket(
                    row,
                    projection_thresholds,
                    volatility_thresholds,
                )
                label = bucket if bucket is not None else "unavailable"
                if label == volatility_class:
                    subset.append(row)
            if not subset:
                continue
            widths = [float(row["Width"]) for row in subset]
            covered = sum(1 for row in subset if row["Covered"])
            volatility_width[volatility_class] = {
                "Count": len(subset),
                "CoveragePercent": round(100.0 * covered / len(subset), 4),
                "MeanWidth": round(sum(widths) / len(subset), 4),
                "MedianWidth": round(float(_median(widths)), 4),
            }

    return {
        "Strategy": strategy,
        "Levels": levels,
        "Coverage90ByPosition": by_position,
        "GroupUsage90": dict(sorted(fallback_usage.items())),
        "Width90ByVolatilityClass": volatility_width,
    }


def build_interval_report(
    repo_root: Path,
    *,
    league_id: str,
    scoring_season: int,
    first_week: int = 1,
    last_week: int = 18,
) -> dict[str, Any]:
    scoring = _scoring_profile(repo_root, league_id, scoring_season)
    required_seasons = (2021, 2022, 2023, 2024, 2025)

    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]] = {}
    usage_by_season: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
    for season in required_seasons:
        observations, _audit = build_scored_played_games(
            repo_root,
            season=season,
            scoring=scoring,
            first_week=first_week,
            last_week=last_week,
        )
        observations_by_season[season] = observations
        usage_by_season[season] = _usage_by_week(
            repo_root,
            season=season,
            first_week=first_week,
            last_week=last_week,
        )

    examples = build_v4_examples(
        observations_by_season,
        usage_by_season,
        target_seasons=[2023, CALIBRATION_SEASON, HOLDOUT_SEASON],
    )

    development_rows = _v3_rows(examples, seasons={2023})
    calibration_v3_rows = _v3_rows(examples, seasons={CALIBRATION_SEASON})
    final_fit_rows = _v3_rows(examples, seasons={2023, CALIBRATION_SEASON})
    holdout_v3_rows = _v3_rows(examples, seasons={HOLDOUT_SEASON})

    calibration_fit = fit_variant(
        development_rows,
        variant=VARIANT_COMBINED,
        ridge=V4_C_RIDGE,
    )
    calibration_rows = evaluate_variant(
        calibration_v3_rows,
        fit=calibration_fit,
        clip=V4_C_CLIP,
    )["Rows"]

    final_fit = fit_variant(
        final_fit_rows,
        variant=VARIANT_COMBINED,
        ridge=V4_C_RIDGE,
    )
    holdout_rows = evaluate_variant(
        holdout_v3_rows,
        fit=final_fit,
        clip=V4_C_CLIP,
    )["Rows"]

    volatility_by_key = build_prior_score_volatility(
        observations_by_season,
        target_seasons=[CALIBRATION_SEASON, HOLDOUT_SEASON],
    )
    calibration_rows = _enrich_volatility(calibration_rows, volatility_by_key)
    holdout_rows = _enrich_volatility(holdout_rows, volatility_by_key)

    projection_thresholds = _projection_thresholds(calibration_rows)
    volatility_thresholds = _volatility_thresholds(
        calibration_rows,
        projection_thresholds,
    )
    groups = _residual_groups(
        calibration_rows,
        projection_thresholds=projection_thresholds,
        volatility_thresholds=volatility_thresholds,
    )

    strategies = {
        strategy: evaluate_strategy(
            holdout_rows,
            strategy=strategy,
            groups=groups,
            projection_thresholds=projection_thresholds,
            volatility_thresholds=volatility_thresholds,
        )
        for strategy in STRATEGIES
    }

    group_sizes = {key: len(values) for key, values in groups.items()}

    return {
        "ContractVersion": 1,
        "Model": "v4-c-asymmetric-empirical-prediction-intervals",
        "League": league_id,
        "ScoringSeason": scoring_season,
        "PointModel": {
            "Variant": VARIANT_COMBINED,
            "Ridge": V4_C_RIDGE,
            "Clip": V4_C_CLIP,
            "CalibrationFitSeason": 2023,
            "FinalFitSeasons": [2023, 2024],
        },
        "IntervalCalibration": {
            "Season": CALIBRATION_SEASON,
            "Rows": len(calibration_rows),
            "Rule": (
                "signed V4-C residual quantiles from 2024 predictions produced by "
                "a point model fit on 2023 only"
            ),
            "MinimumConditionalGroupSize": MIN_GROUP_SIZE,
            "ProjectionBuckets": "position-specific terciles learned from 2024 calibration projections",
            "VolatilityProxy": (
                "pregame population standard deviation of fantasy points from T-2, T-1 "
                "and prior target-season played games; minimum four historical games"
            ),
            "ParticipationCondition": (
                "interval calibration/evaluation uses played-game observations and is "
                "therefore conditional on player participation"
            ),
        },
        "Holdout": {
            "Season": HOLDOUT_SEASON,
            "Rows": len(holdout_rows),
        },
        "ProjectionThresholds": {
            position: [round(low, 6), round(high, 6)]
            for position, (low, high) in sorted(projection_thresholds.items())
        },
        "VolatilityThresholds": {
            key: round(value, 6)
            for key, value in sorted(volatility_thresholds.items())
        },
        "CalibrationGroupSizes": dict(sorted(group_sizes.items())),
        "Strategies": strategies,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--scoring-season", type=int, default=2025)
    parser.add_argument("--first-week", type=int, default=1)
    parser.add_argument("--last-week", type=int, default=18)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_interval_report(
        args.repo_root.resolve(),
        league_id=args.league,
        scoring_season=args.scoring_season,
        first_week=args.first_week,
        last_week=args.last_week,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
