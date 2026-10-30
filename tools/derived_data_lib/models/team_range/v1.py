"""team-range-v1: team projection and central ranges from the starters' prediction ranges (ADR-075, Issue #1199).

Exact move of the method ``normal-independent-v1`` out of tools/matchup_projection.py; the numbers do not change. Points of
games that are not final are never used (a running game counts its projection until Final). A starter whose scoring
availability is "out" counts as a resolved zero without variance (like a bye); "uncertain" starters keep their
participation-conditional projection and are listed. The team projection is a sum; the team range is a normal approximation that
adds player variances (independent starters), calibrated by tools/historical_team_range_backtest.py.

A model is a pure function of its explicit inputs: it reads no file, no clock and no league configuration. Immutable after its
first productive use; any change is ``team-range-v2``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import NormalDist
from types import MappingProxyType
from typing import Any

MODEL_ID = "team-range-v1"
KIND = "team-range"

METHOD_ID = "normal-independent-v1"
SIGMA_BASIS_LEVEL = 0.9
LEVELS = (0.5, 0.8, 0.9)
AVAILABILITY_OUT = "out"
AVAILABILITY_UNCERTAIN = "uncertain"

PARAMS = MappingProxyType({
    "MethodId": METHOD_ID,
    "Levels": LEVELS,
    "SigmaBasisLevel": SIGMA_BASIS_LEVEL,
})

METHOD = MappingProxyType({
    "Id": METHOD_ID,
    "Levels": list(LEVELS),
    "SigmaBasisLevel": SIGMA_BASIS_LEVEL,
    "Assumption": "starters score independently; player variances add",
    "LivePoints": "not-used",
    "OutStarters": "zero-without-variance",
    "ParticipationCondition": "conditional-on-participation",
})


def z_for_level(level: float) -> float:
    """Two-sided normal quantile for a central interval of the given level."""
    return NormalDist().inv_cdf(0.5 + level / 2.0)


def player_sigma(lower: float, upper: float) -> float:
    """Standard deviation implied by a player's SIGMA_BASIS_LEVEL interval."""
    return (upper - lower) / (2.0 * z_for_level(SIGMA_BASIS_LEVEL))


def team_ranges(mean: float, variance: float, levels: tuple[float, ...] = LEVELS) -> list[dict[str, float]]:
    """Central ranges around the team mean; variances of independent starters add."""
    sd = math.sqrt(variance)
    return [
        {"Level": level, "Lower": round(mean - z_for_level(level) * sd, 4), "Upper": round(mean + z_for_level(level) * sd, 4)}
        for level in levels
    ]


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def projection_values(projection: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """(points, sigma) when the projection is usable, else None."""
    if not projection or projection.get("Status") != "available":
        return None
    points = _finite(projection.get("Points"))
    if points is None:
        return None
    ranges = projection.get("PredictionRanges") or (
        [projection["PredictionRange"]] if projection.get("PredictionRange") else []
    )
    basis = next((item for item in ranges if item.get("Level") == SIGMA_BASIS_LEVEL), None)
    if basis is None:
        return None
    lower, upper = _finite(basis.get("Lower")), _finite(basis.get("Upper"))
    if lower is None or upper is None or upper < lower:
        return None
    return points, player_sigma(lower, upper)


def build_team_projection(
    team_id: Any,
    starters: Mapping[str, Mapping[str, Any]],
    projections: Mapping[str, Mapping[str, Any]],
    availability: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    availability = availability or {}
    scored = 0.0
    mean = 0.0
    variance = 0.0
    pregame = 0.0
    pregame_complete = bool(starters)
    final_count = 0
    resolved = 0
    byes: list[str] = []
    out: list[str] = []
    uncertain: list[str] = []
    unavailable: list[str] = []

    for player_id in sorted(starters):
        starter = starters[player_id]
        values = projection_values(projections.get(player_id))

        if starter["bye"]:
            byes.append(player_id)
            resolved += 1
            continue

        state = availability.get(player_id)
        if not starter["final"] and state == AVAILABILITY_OUT:
            out.append(player_id)
            resolved += 1
            continue
        if not starter["final"] and state == AVAILABILITY_UNCERTAIN:
            uncertain.append(player_id)

        if values is None:
            pregame_complete = False
        else:
            pregame += values[0]

        if starter["final"]:
            if starter["points"] is None:
                unavailable.append(player_id)
                continue
            scored += starter["points"]
            mean += starter["points"]
            final_count += 1
            resolved += 1
        elif values is None:
            unavailable.append(player_id)
        else:
            points, sigma = values
            mean += points
            variance += sigma * sigma
            resolved += 1

    starter_count = len(starters)
    complete = starter_count > 0 and resolved == starter_count
    state = "available" if complete else ("partial" if resolved > 0 else "unavailable")

    return {
        "FantasyTeamID": team_id,
        "State": state,
        "StarterCount": starter_count,
        "ResolvedStarterCount": resolved,
        "FinalStarterCount": final_count,
        "ScoredPoints": round(scored, 4),
        "PregameProjectedScore": round(pregame, 4) if pregame_complete else None,
        "ProjectedFinalScore": round(mean, 4) if complete else None,
        "StandardDeviation": round(math.sqrt(variance), 4) if complete else None,
        "Ranges": team_ranges(mean, variance) if complete else [],
        "ByeStarterPlayerIDs": byes,
        "OutStarterPlayerIDs": out,
        "UncertainStarterPlayerIDs": uncertain,
        "UnavailableStarterPlayerIDs": unavailable,
    }
