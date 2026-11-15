"""Read-only team snap-volume inference from canonical per-player snap counts.

Issue #1077. A team's offensive/defensive/special-teams plays are NOT the sum
of its participating players' snaps. PFR-reported fractions are rounded to two
decimal places, so infer a team total only when multiple positive participant
rows agree on exactly one integer denominator. This is *source-inferred*, not
an independently verified official play count. No persistence or source writes.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

_UNITS = ("Offense", "Defense", "SpecialTeams")
# PFR source/canonical snap shares are rounded to 2 decimal places.
_ROUNDING_TOLERANCE = 0.0050000001
# Purely a finite inference guard, NOT an estimate of actual NFL play volume.
_MAX_SUPPORTED_TEAM_SNAPS = 1000


def _unit_total(players: Sequence[Mapping[str, Any]], unit: str) -> dict[str, Any]:
    rows: list[tuple[int, float]] = []
    missing = 0
    inconsistent = False
    player_snap_sum = 0
    for player in players:
        values = player["Snaps"]
        count = values[unit + "Snaps"]
        pct = values[unit + "Pct"]
        if count is not None:
            player_snap_sum += count
        if count is None or pct is None:
            missing += 1
            continue
        if count == 0:
            if pct != 0:
                inconsistent = True
            continue
        rows.append((count, pct))

    result = {
        "TotalSnaps": None,
        "Status": "unavailable",
        "PositiveParticipantRows": len(rows),
        "MissingPlayerFields": missing,
        "ObservedPlayerSnapSum": player_snap_sum,
        "PossibleTeamTotals": 0,
    }
    if not players:
        return result
    if inconsistent:
        result["Status"] = "inconsistent-rounded-shares"
        return result
    if missing:
        result["Status"] = "missing-player-fields"
        return result
    if len(rows) < 2:
        result["Status"] = "insufficient-participants"
        return result

    lower = max(count for count, _ in rows)
    upper = _MAX_SUPPORTED_TEAM_SNAPS
    for count, pct in rows:
        lower = max(lower, math.ceil(count / (pct + _ROUNDING_TOLERANCE)))
        if pct > _ROUNDING_TOLERANCE:
            upper = min(upper, math.floor(count / (pct - _ROUNDING_TOLERANCE)))
    if lower > upper:
        result["Status"] = "inconsistent-rounded-shares"
        return result
    candidates = [
        total for total in range(lower, upper + 1)
        if all(abs(count / total - pct) <= _ROUNDING_TOLERANCE
               for count, pct in rows)
    ]
    result["PossibleTeamTotals"] = len(candidates)
    if not candidates:
        result["Status"] = "inconsistent-rounded-shares"
    elif len(candidates) != 1 or candidates[0] == _MAX_SUPPORTED_TEAM_SNAPS:
        # A denominator at our arbitrary search cap cannot prove uniqueness.
        result["Status"] = "ambiguous-rounded-shares"
    else:
        result["TotalSnaps"] = candidates[0]
        result["Status"] = "unique-rounded-share-denominator"
    return result


def infer_team_snap_volumes(
    rows: list[Mapping[str, Any]] | None,
    away_team: str, home_team: str,
) -> list[dict[str, Any]] | None:
    """Infer read-only offense, defense and ST team totals for one GameID.

    A conflicting opponent-offense/defense total fails closed for both units;
    Special Teams have their own source percentage denominator.
    """
    if rows is None:
        return None
    result = []
    for team in (away_team, home_team):
        team_players = [row for row in rows if row["Team"] == team]
        result.append({
            "Team": team,
            "PlayerRows": len(team_players),
            "Offense": _unit_total(team_players, "Offense"),
            "Defense": _unit_total(team_players, "Defense"),
            "SpecialTeams": _unit_total(team_players, "SpecialTeams"),
        })
    for off, defense in ((result[0], result[1]), (result[1], result[0])):
        off_info, def_info = off["Offense"], defense["Defense"]
        if (off_info["TotalSnaps"] is not None
                and def_info["TotalSnaps"] is not None
                and off_info["TotalSnaps"] != def_info["TotalSnaps"]):
            for metric in (off_info, def_info):
                metric["TotalSnaps"] = None
                metric["Status"] = "opponent-offense-defense-mismatch"
    return result
