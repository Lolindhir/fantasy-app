"""Consumer-neutral, versioned all-time league records (#1672).

V1 preserves the existing BiggestUpsetAllTime selection and its regular-season
scope. Other record types must define their own eligibility and tie semantics.
"""
from __future__ import annotations

import math
from typing import Any

PRODUCT = "league-records"
SCHEMA_VERSION = 1
MODEL_ID = "league-records-v1"

UPSET_FIELDS = (
    "Week", "WinnerTeamID", "LoserTeamID", "WinnerPoints", "LoserPoints",
    "WinnerPregameWinProbability",
)


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def build(league_id: str, expected_seasons: list[int],
          documents: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Pure reduction of accepted season-statistics documents; missing is not null."""
    if not expected_seasons or len(set(expected_seasons)) != len(expected_seasons):
        raise ValueError("Expected seasons must be nonempty and unique")
    if set(documents) != set(expected_seasons):
        raise ValueError(f"{league_id}: incomplete or unexpected season-statistics input")
    coverage = []
    best = None
    best_key = None
    for season in sorted(expected_seasons):
        doc = documents[season]
        if (doc["Product"], doc["CanonicalLeagueID"], doc["Season"]) != ("season-statistics", league_id, season):
            raise ValueError(f"{league_id}/{season}: inconsistent upstream identity")
        as_of = doc["AsOf"]
        completed = as_of["CompletedWeeks"]
        scored = as_of["LeagueScoredWeek"]
        regular = doc["RegularSeasonGames"]
        if not (type(completed) is int and type(scored) is int and type(regular) is int
                and 0 <= completed <= min(scored, regular)):
            raise ValueError(f"{league_id}/{season}: invalid week coverage")
        if completed != min(scored, regular):
            raise ValueError(f"{league_id}/{season}: missing scored regular-season weeks")
        models = doc["Models"]
        threshold = doc["Thresholds"]["UpsetWinProbability"]
        if not _number(threshold) or not 0 < threshold <= 1:
            raise ValueError(f"{league_id}/{season}: invalid upset threshold")
        teams = doc["Teams"]
        roster_ids = {str(row["TeamID"]): row["CanonicalLeagueRosterID"] for row in teams}
        if len(roster_ids) != len(teams) or any(not value for value in roster_ids.values()):
            raise ValueError(f"{league_id}/{season}: ambiguous roster identity")
        coverage.append({
            "Season": season,
            "SourceSchemaVersion": doc["SchemaVersion"],
            "Models": dict(models),
            "AsOf": {"LeagueScoredWeek": scored, "CompletedWeeks": completed},
            "RegularSeasonGames": regular,
            "KnownChanceGamesByTeam": [
                {"TeamID": row["TeamID"], "KnownChanceGames": row["KnownChanceGames"]}
                for row in sorted(teams, key=lambda row: str(row["TeamID"]))
            ],
            "UpsetWinProbability": threshold,
        })
        upset = doc["BiggestUpset"]
        if upset is None:
            continue
        fact = {key: upset[key] for key in UPSET_FIELDS}
        chance = fact["WinnerPregameWinProbability"]
        week = fact["Week"]
        winner = str(fact["WinnerTeamID"])
        loser = str(fact["LoserTeamID"])
        # The source threshold is applied before its four-decimal persistence.
        # A rounded value equal to the threshold remains a valid source fact.
        if (not _number(chance) or not 0 <= chance <= threshold
                or type(week) is not int or not 1 <= week <= completed
                or winner == loser or winner not in roster_ids or loser not in roster_ids
                or not _number(fact["WinnerPoints"]) or not _number(fact["LoserPoints"])
                or fact["WinnerPoints"] <= fact["LoserPoints"]):
            raise ValueError(f"{league_id}/{season}: invalid BiggestUpset fact")
        key = (chance, season, week)
        if best_key is None or key < best_key:
            best_key = key
            best = {
                "Season": season, **fact,
                "WinnerCanonicalLeagueRosterID": roster_ids[winner],
                "LoserCanonicalLeagueRosterID": roster_ids[loser],
            }
    return {
        "SchemaVersion": SCHEMA_VERSION, "Product": PRODUCT,
        "CanonicalLeagueID": league_id, "Model": MODEL_ID,
        "Coverage": coverage, "Records": {"BiggestUpset": best},
    }


def legacy_biggest_upset(product: dict[str, Any]) -> dict[str, Any] | None:
    """Compatibility shape only; no selection or ranking."""
    record = product["Records"]["BiggestUpset"]
    return None if record is None else {key: record[key] for key in ("Season", *UPSET_FIELDS)}
