"""awards-v1: season awards, exact port of Get-Awards in StandingUtils.psm1 (ADR-072, Issue #987).

Six awards in this order: Best Performer, Streaker, Overperformer, Brick Wall (regular season, always when a game
was completed), Clutch Peaker (needs playoff placements), Most Improved (needs the previous season). No award is
given before the first completed regular-season game. The first team in table order wins an exact tie of an
award score. The rows of the regular-season table gain the score annotations ClutchPeakerScore and
ImprovementScore because the App contract carries them (Standings.json); they are part of the result.
Display strings (StatDisplay) are part of the v1 result because the App contract is unchanged, including the
closing parenthesis of the Brick Wall text. #964 follows as ``awards-v2``.
Immutable after its first productive use; any change is ``awards-v2``.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Sequence

from .._common import dotnet_round, ps_text

MODEL_ID = "awards-v1"
KIND = "awards"

PARAMS = MappingProxyType({
    "Order": ("Best Performer", "Streaker", "Overperformer", "Brick Wall", "Clutch Peaker", "Most Improved"),
    "ClutchPeakerPlayoffPlaceWeight": 0.01,
    "ClutchPeakerOutsidePlayoffsScore": -999,
    "MostImprovedPointsPerGameWeight": 0.01,
})

_TYPES = MappingProxyType({
    "Special": MappingProxyType({"Name": "Special", "DisplayText": "Special", "Order": 1}),
    "RegularSeason": MappingProxyType({"Name": "RegularSeason", "DisplayText": "Regular Season", "Order": 2}),
})


def _type(name: str) -> dict[str, Any]:
    return dict(_TYPES[name])


def _first_max(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    best = rows[0]
    for row in rows[1:]:
        if row[key] > best[key]:
            best = row
    return best


def _award(name: str, type_name: str, icon: str, stat: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Name": name, "Type": _type(type_name), "IconUnicode": icon, "StatDisplay": stat,
        "TeamID": row["TeamID"], "Owner": row["Owner"], "TeamName": row["TeamName"],
    }


def compute(
    regular_season: Sequence[dict[str, Any]] | None,
    playoffs: Sequence[dict[str, Any]] | None,
    previous_season: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Awards plus score annotations per TeamID (``ClutchPeakerScore`` / ``ImprovementScore``).

    ``regular_season``: rows of the regular-season table in rank order (App contract fields). ``playoffs``:
    placement rows. ``previous_season``: the previous season result with a ``RegularSeason`` list, or None.
    Nothing is mutated.
    """
    annotations: dict[int, dict[str, Any]] = {}
    if not regular_season:
        return [], annotations
    if not any(row["Wins"] + row["Losses"] + row["Ties"] > 0 for row in regular_season):
        return [], annotations
    rows = list(regular_season)
    awards: list[dict[str, Any]] = []

    best = _first_max(rows, "Points")
    awards.append(_award("Best Performer", "RegularSeason", "1F525",
                         f"Points: {ps_text(best['Points'])} | Points per Game: {ps_text(best['PointsPerGame'])}", best))
    streaker = _first_max(rows, "WinStreakScore")
    awards.append(_award("Streaker", "RegularSeason", "26A1",
                         f"Longest Streak: {ps_text(streaker['LongestWinStreak'])} Wins | Record: {streaker['Record']}", streaker))
    over = _first_max(rows, "EfficiencyScore")
    awards.append(_award("Overperformer", "RegularSeason", "1F680",
                         f"Point Difference: {ps_text(over['PointDifference'])} | Wins: {ps_text(over['Wins'])}", over))
    wall = _first_max(rows, "IronWillScore")
    awards.append(_award("Brick Wall", "RegularSeason", "1F9F1",
                         f"Points Against per Game: {ps_text(wall['PointsAgainstPerGame'])} | League Difference: "
                         f"{ps_text(wall['PointsAgainstPerGameDiffLeagueAvg'])} | Wins: {ps_text(wall['Wins'])})", wall))

    if playoffs:
        by_team = {p["TeamID"]: p for p in playoffs}
        scores: dict[int, Any] = {}
        for row in rows:
            playoff = by_team.get(row["TeamID"])
            if playoff:
                scores[row["TeamID"]] = (row["Place"] - playoff["Place"]) - playoff["Place"] * PARAMS["ClutchPeakerPlayoffPlaceWeight"]
            else:
                scores[row["TeamID"]] = PARAMS["ClutchPeakerOutsidePlayoffsScore"]
            annotations.setdefault(row["TeamID"], {})["ClutchPeakerScore"] = scores[row["TeamID"]]
        clutch = rows[0]
        for row in rows[1:]:
            if scores[row["TeamID"]] > scores[clutch["TeamID"]]:
                clutch = row
        playoff = by_team[clutch["TeamID"]] if clutch["TeamID"] in by_team else None
        playoff_ordinal = playoff["PlaceOrdinal"] if playoff else ""
        awards.append(_award("Clutch Peaker", "Special", "1F3AF",
                             f"Regular Season: {clutch['PlaceOrdinal']} | Playoffs: {playoff_ordinal}", clutch))

    if previous_season:
        previous_by_team = {str(r["TeamID"]): r for r in previous_season.get("RegularSeason") or []}
        improvement: dict[int, Any] = {}
        for row in rows:
            previous = previous_by_team.get(str(row["TeamID"]))
            if previous:
                improvement[row["TeamID"]] = dotnet_round(
                    (row["WinPercentage"] - previous["WinPercentage"])
                    + (row["PointsPerGame"] - previous["PointsPerGame"]) * PARAMS["MostImprovedPointsPerGameWeight"], 4)
            else:
                improvement[row["TeamID"]] = 0
            annotations.setdefault(row["TeamID"], {})["ImprovementScore"] = improvement[row["TeamID"]]
        improved = rows[0]
        for row in rows[1:]:
            if improvement[row["TeamID"]] > improvement[improved["TeamID"]]:
                improved = row
        previous = previous_by_team.get(str(improved["TeamID"]))
        previous_wins = ps_text(previous["Wins"]) if previous else "N/A"
        previous_points = ps_text(previous["Points"]) if previous else "N/A"
        awards.append(_award("Most Improved", "RegularSeason", "1F4AA",
                             f"Wins: {previous_wins} to {ps_text(improved['Wins'])} | "
                             f"Points: {previous_points} to {ps_text(improved['Points'])}", improved))
    return awards, annotations
