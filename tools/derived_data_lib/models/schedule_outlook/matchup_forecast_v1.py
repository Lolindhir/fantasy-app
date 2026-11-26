"""Versioned analytic matchup forecast retained from playoff-odds-v2 (#1693).

This component predicts individual games only, never ranks or playoff chances.
It intentionally reuses the immutable v2 scoring basis and normal CDF. Its
output remains independent of whether the exact playoff enumeration is available.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..playoff_odds.v1 import PlayoffOddsError
from ..playoff_odds.v2 import scoring_basis, win_probability, _round

MODEL_ID = "schedule-matchup-forecast-v1"


def compute(*, teams: Sequence[Mapping[str, Any]], strength_by_roster: Mapping[str, Any],
            points_by_roster: Mapping[str, Sequence[float]], previous_points: Sequence[float],
            upcoming_matchups: Sequence[Mapping[str, Any]], regular_season_complete: bool) -> dict[str, Any]:
    ids = {t["CanonicalLeagueRosterID"]: t["TeamID"] for t in teams}
    if len(ids) != len(teams) or len(set(ids.values())) != len(teams):
        raise PlayoffOddsError("Duplicate forecast team identity")
    basis = scoring_basis(list(ids), strength_by_roster, points_by_roster, previous_points)
    scoring = {"LeagueMeanPoints": _round(basis["Mean"]), "PointsStdDev": _round(basis["StdDev"]),
               "MeanSource": basis["MeanSource"], "ScoredTeamGames": basis["Observations"],
               "PreviousSeasonTeamGames": basis["PreviousObservations"]}
    expected = basis["Expected"]
    equal = basis["Basis"] == "equal-unknown"
    spread = basis["StdDev"] or 1.0
    upcoming: dict[str, list[dict[str, Any]]] = {rid: [] for rid in ids}
    if regular_season_complete and upcoming_matchups:
        raise PlayoffOddsError("Completed regular season has forecast games")
    for game in upcoming_matchups:
        a, b = game["Team1CanonicalLeagueRosterID"], game["Team2CanonicalLeagueRosterID"]
        if a not in ids or b not in ids or a == b:
            raise PlayoffOddsError("Invalid forecast pairing")
        p = win_probability(expected[a], expected[b], spread) if expected[a] is not None else None
        for own, other, probability in ((a, b, p), (b, a, None if p is None else 1.0 - p)):
            upcoming[own].append({
                "Week": game.get("Week"), "CanonicalLeagueMatchupID": game.get("CanonicalLeagueMatchupID"),
                "OpponentCanonicalLeagueRosterID": other, "OpponentTeamID": ids[other],
                "WinProbability": 0.5 if equal else _round(probability),
                "OpponentExpectedPoints": _round(expected[other]),
                "ExpectedMargin": 0.0 if equal else (_round(expected[own] - expected[other]) if probability is not None else None),
            })
    rows = []
    for rid, tid in ids.items():
        games = upcoming[rid]
        known = [g["WinProbability"] for g in games if g["WinProbability"] is not None]
        complete_games = bool(games) and len(known) == len(games)
        rows.append({"TeamID": tid, "CanonicalLeagueRosterID": rid,
                     "ExpectedPoints": None if regular_season_complete else _round(expected[rid]),
                     "RemainingExpectedWins": _round(sum(known)) if complete_games else None,
                     "RemainingWinProbability": _round(sum(known) / len(known)) if complete_games else None,
                     "Upcoming": games})
    return {"Model": MODEL_ID, "Provenance": {"StrengthBasis": basis["Basis"],
                "StrengthReason": basis["Reason"], "RegularSeasonComplete": regular_season_complete},
            "Scoring": scoring, "Teams": rows}
