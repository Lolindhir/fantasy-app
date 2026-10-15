"""salary-v1: Salary and SalaryProjected, exact port of the RequestPlayers.ps1 behaviour (ADR-055).

Season points are ``avgPotentialGame * weightTotal + avgGame * weightGame``. Salary uses the three
previous seasons; SalaryProjected uses the current season, blended with the newest previous season
while few weeks are final, plus the two newest previous seasons. Both go through the same floor and
mapping:

* if the two newest of the three point values are exactly 0 the salary is 0;
* the maximum value times the floor weight of the season that holds it is the floor; no value stays
  below it; the three floored values are averaged;
* the average is mapped non-linearly (square up to ``source_max``, linear extrapolation above it)
  onto 0 to 50,000,000 dollars and rounded to whole dollars (round half to even).

Dead code of the PowerShell version (random adjustment, fallback salary, linear branch) is not part
of this model. The model is immutable after its first productive use; any change is ``salary-v2``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType

from .._common import require_finite, round_half_even

MODEL_ID = "salary-v1"
KIND = "salary"

# Previous seasons the model reads for a season's Salary (newest first). Not part of PARAMS on purpose: PARAMS
# is snapshot provenance and this value only tells consumers how much history a season needs (for example the
# Schedule archives, tools/schedule_archive.py).
HISTORY_SEASONS = 3

PARAMS = MappingProxyType({
    "WeightTotal": 0.5,
    "WeightGame": 0.5,
    "SourceMin": 0.0,
    "SourceMax": 20.0,
    "CurveExponent": 2,
    "TargetMin": 0.0,
    "TargetMax": 50_000_000.0,
    # Floor ratio by the position of the maximum among (newest, middle, oldest).
    "FloorWeights": (0.5, 0.33, 0.17),
    # AsOfFinalScoredWeek -> (weight of current season points, weight of newest previous season).
    # Week 0 uses the newest previous season only; weeks above 4 use the current season unchanged.
    "RampIn": MappingProxyType({1: (0.25, 0.75), 2: (0.35, 0.65), 3: (0.5, 0.5), 4: (0.75, 0.25)}),
})


@dataclass(frozen=True)
class SeasonInput:
    """League-scored per-game averages of one season."""

    avg_potential_game: float
    avg_game: float


@dataclass(frozen=True)
class SalaryResult:
    salary: int
    salary_projected: int


def season_points(season: SeasonInput) -> float:
    total = require_finite(season.avg_potential_game, "avg_potential_game")
    game = require_finite(season.avg_game, "avg_game")
    return total * PARAMS["WeightTotal"] + game * PARAMS["WeightGame"]


def curve_dollars(points: float, exponent: float | None = None) -> float:
    """Unrounded dollar value of averaged season points on the non-linear curve.

    ``exponent`` defaults to the model's ``CurveExponent``; analyses may pass another value to probe
    the curve. Productive code uses ``map_points_to_dollars``, which rounds this value.
    """
    exponent = PARAMS["CurveExponent"] if exponent is None else exponent
    source_min, source_max = PARAMS["SourceMin"], PARAMS["SourceMax"]
    target_min, target_max = PARAMS["TargetMin"], PARAMS["TargetMax"]
    normalized = (points - source_min) / (source_max - source_min)
    scaled = math.pow(max(normalized, 0), exponent)
    if normalized > 1:
        scaled = 1 + (normalized - 1) * exponent
    return target_min + scaled * (target_max - target_min)


def map_points_to_dollars(points: float) -> int:
    """MapSalaryFantasy: non-linear mapping of averaged season points to whole dollars."""
    return round_half_even(curve_dollars(points))


def floored_average(points_newest: float, points_middle: float, points_oldest: float) -> float:
    """Floor and average of three season point values, newest first (before the dollar mapping)."""
    p1 = require_finite(points_newest, "points_newest")
    p2 = require_finite(points_middle, "points_middle")
    p3 = require_finite(points_oldest, "points_oldest")
    if p1 == 0 and p2 == 0:
        return 0.0
    w1, w2, w3 = PARAMS["FloorWeights"]
    if p1 >= p2 and p1 >= p3:
        ratio, maximum = w1, p1
    elif p2 >= p1 and p2 >= p3:
        ratio, maximum = w2, p2
    else:
        ratio, maximum = w3, p3
    floor = maximum * ratio
    p1, p2, p3 = max(p1, floor), max(p2, floor), max(p3, floor)
    return (p1 + p2 + p3) / 3


def salary_from_points(points_newest: float, points_middle: float, points_oldest: float) -> int:
    """Get-FantasySalaryWithFloor: whole-dollar salary of three season point values, newest first."""
    return map_points_to_dollars(floored_average(points_newest, points_middle, points_oldest))


def current_season_points(points_current: float, points_previous: float, as_of_final_scored_week: int) -> float:
    """Current-season points used for SalaryProjected, blended with the newest previous season early on."""
    if isinstance(as_of_final_scored_week, bool) or not isinstance(as_of_final_scored_week, int) \
            or as_of_final_scored_week < 0:
        raise ValueError(f"as_of_final_scored_week must be a non-negative integer, got {as_of_final_scored_week!r}")
    if as_of_final_scored_week == 0:
        return points_previous
    blend = PARAMS["RampIn"].get(as_of_final_scored_week)
    if blend is None:
        return points_current
    weight_current, weight_previous = blend
    return points_current * weight_current + points_previous * weight_previous


def compute(
    current: SeasonInput,
    previous_1: SeasonInput,
    previous_2: SeasonInput,
    previous_3: SeasonInput,
    as_of_final_scored_week: int,
) -> SalaryResult:
    """Salary and SalaryProjected of one player; ``previous_1`` is the newest previous season."""
    points_current = season_points(current)
    points_1 = season_points(previous_1)
    points_2 = season_points(previous_2)
    points_3 = season_points(previous_3)
    salary = salary_from_points(points_1, points_2, points_3)
    projected_current = current_season_points(points_current, points_1, as_of_final_scored_week)
    salary_projected = salary_from_points(projected_current, points_1, points_2)
    return SalaryResult(salary=salary, salary_projected=salary_projected)
