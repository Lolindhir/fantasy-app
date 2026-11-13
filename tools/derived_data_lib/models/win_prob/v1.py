"""win-prob-v1: win probability of a fantasy matchup from the team projections (Issue #1443).

The probability comes raw from the projection model, without a calibration factor (Robert, 2026-11-12): with the team projections
``mean`` and ``sd`` of team-range-v1 (starters independent, variances add) the team score difference is normal and
``P(A) = Phi((meanA - meanB) / sqrt(sdA^2 + sdB^2))``. A better projection model therefore improves the chance automatically.

The published value is a whole percent per team and the two values of a matchup always add up to 100 (a tie has no probability of its
own). A missing input gives ``None`` (unknown, never 50 percent). A matchup without any variance (every starter final) is decided: the
higher score has 100 percent, equal scores 50/50. The upset boundary applies to the unrounded probability of the winner.

Recap marks (Issue #1446, additive, no existing value changes): a winner below UPSET_THRESHOLD (35 percent) is an ``upset``, a winner from
35 up to (excluding) UNDERDOG_THRESHOLD (50 percent) an ``underdog`` win, every other winner gets no mark. Both boundaries live here, never in the frontend.

A model is a pure function of its explicit inputs: it reads no file, no clock and no league configuration. Immutable after its first
productive use; any change is ``win-prob-v2``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import NormalDist
from types import MappingProxyType
from typing import Any

MODEL_ID = "win-prob-v1"
KIND = "win-prob"

UPSET_THRESHOLD = 0.35
UNDERDOG_THRESHOLD = 0.5

PARAMS = MappingProxyType({
    "Distribution": "normal-difference",
    "Calibration": "none",
    "Unit": "whole-percent",
    "UpsetThreshold": UPSET_THRESHOLD,
    "UnderdogThreshold": UNDERDOG_THRESHOLD,
})

_NORMAL = NormalDist()


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def win_probability(mean_a: Any, sd_a: Any, mean_b: Any, sd_b: Any) -> float | None:
    """Unrounded probability that team A scores more than team B; None when an input is missing."""
    values = [_finite(item) for item in (mean_a, sd_a, mean_b, sd_b)]
    if any(item is None for item in values):
        return None
    mean_a, sd_a, mean_b, sd_b = values  # type: ignore[misc]
    if sd_a < 0 or sd_b < 0:
        return None
    spread = math.sqrt(sd_a * sd_a + sd_b * sd_b)
    difference = mean_a - mean_b
    if spread == 0:
        return 0.5 if difference == 0 else (1.0 if difference > 0 else 0.0)
    return _NORMAL.cdf(difference / spread)


def percent_pair(probability: float | None) -> tuple[int, int] | None:
    """Whole percent of both teams that add up to exactly 100."""
    if probability is None:
        return None
    first = int(math.floor(probability * 100 + 0.5))
    return first, 100 - first


def matchup_percentages(team_a: Mapping[str, Any], team_b: Mapping[str, Any]) -> tuple[int, int] | None:
    """Whole percent for two team projections of team-range-v1 (only when both are available)."""
    for team in (team_a, team_b):
        if team.get("State") != "available":
            return None
    return percent_pair(
        win_probability(
            team_a.get("ProjectedFinalScore"), team_a.get("StandardDeviation"),
            team_b.get("ProjectedFinalScore"), team_b.get("StandardDeviation"),
        )
    )


def is_upset(winner_probability: float | None) -> bool | None:
    """True when the winner had less than UPSET_THRESHOLD before the week; None when unknown."""
    if winner_probability is None:
        return None
    return winner_probability < UPSET_THRESHOLD


def upset_level(winner_probability: float | None) -> str | None:
    """``upset`` below UPSET_THRESHOLD, ``underdog`` below UNDERDOG_THRESHOLD, else None (also None when the chance is unknown)."""
    if winner_probability is None:
        return None
    if winner_probability < UPSET_THRESHOLD:
        return "upset"
    if winner_probability < UNDERDOG_THRESHOLD:
        return "underdog"
    return None
