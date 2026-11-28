"""Shared legacy historical pregame projection assembly (Issue #1451 AC6A).

Pure, result-neutral extraction from Weekly Recaps and Season Statistics.
No file reads, clock, fitted state, model selection or new bye/availability
semantics. The caller still owns its legacy projection/rounding/upset adapter.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def historical_team_projection(
    team: dict[str, Any],
    identity_map: dict[str, dict[str, dict[str, str]]] | None,
    projections_by_canonical: dict[str, Any],
    team_range_model: Any,
) -> dict[str, Any]:
    """Prepare the recorded starters for the selected legacy team-range model.

    Direct canonical identity wins over the weekly identity lookup. The
    historical calculation deliberately uses neither actual points nor live
    availability; even a known bye retains legacy missing-projection semantics
    until AC6C. Preserve provider-key deduplication and model input ordering.
    """
    starters: dict[str, dict[str, Any]] = {}
    projections: dict[str, Any] = {}
    for player in team["Players"]:
        if not player["IsStarter"]:
            continue
        player_id = _text(player["PlayerID"])
        starters[player_id] = {"final": False, "points": None, "bye": False}
        canonical_id = _text(player.get("CanonicalPlayerID"))
        if not canonical_id and identity_map:
            canonical_id = _text(identity_map["ByPlayer"].get(player_id, {}).get("CanonicalPlayerID"))
        if canonical_id in projections_by_canonical:
            projections[player_id] = projections_by_canonical[canonical_id]
    return team_range_model.build_team_projection(team["FantasyTeamID"], starters, projections)


def raw_matchup_probability(
    first: dict[str, Any], second: dict[str, Any], win_prob_model: Any,
) -> float | None:
    """Pass the legacy rounded team parameters through the selected model.

    Callers retain their existing availability gates; this helper does not
    introduce a new fallback, tie law or probability rounding policy.
    """
    return win_prob_model.win_probability(
        first["ProjectedFinalScore"], first["StandardDeviation"],
        second["ProjectedFinalScore"], second["StandardDeviation"],
    )
