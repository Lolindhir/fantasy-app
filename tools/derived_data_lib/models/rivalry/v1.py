"""rivalry-v1: head-to-head counting rules of the league rivalry statistic (Issue #1455).

Pure counting of finalized fantasy matchups between two teams, no tiebreak, ranking or weighting. A model is a pure function of its explicit
inputs: it reads no file, no clock and no league configuration. Immutable after its first productive use; any change is ``rivalry-v2``.

Counting rules (they reproduce the former Angular util team-rivalry.util.ts, with the documented E1 and E2 decisions of Issue #1455):

* a matchup counts only when its CompletionState is ``final`` and it has a result (the caller passes only such games);
* regular-season matchups always count;
* a playoff matchup counts only when its season is complete (E2: playoff games of a running season count after the season ends; a later model
  version may count them at once) and its bracket label is ``championship`` or ``placement`` (E1: winners-bracket placement games are playoff
  duels, only the losers bracket is the consolation tournament); ``consolation`` and ``unclassified`` never count;
* the filters are ``all`` (every counted game), ``regular`` (counted regular-season games) and ``playoffs`` (counted playoff games);
* outcome is win, loss or tie from the result; points are the effective matchup points as published (nullable);
* the margin is the absolute point difference, null when a score is missing; a game without both scores still counts for the record
  but not for the biggest win and the closest loss;
* PointsFor and PointsAgainst are the sums of the games in chronological order (missing points count as 0), rounded half up to two decimals;
* the biggest win is the win with the largest margin, the closest loss the loss with the smallest margin; ties keep the earlier game.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

MODEL_ID = "rivalry-v1"
KIND = "rivalry"

FILTERS = ("all", "regular", "playoffs")
COUNTED_PLAYOFF_BRACKETS = ("championship", "placement")

PARAMS = MappingProxyType({
    "Filters": FILTERS,
    "CountedPlayoffBrackets": COUNTED_PLAYOFF_BRACKETS,
    "PlayoffsCountAfterSeasonEnd": True,
    "PointsRounding": "half-up-2",
    "Ranking": "none",
})


def counts(stage: str, bracket: str | None, season_complete: bool) -> bool:
    """Whether a final matchup is part of the rivalry statistic."""
    if stage == "regular-season":
        return True
    if stage == "playoffs":
        return bool(season_complete) and bracket in COUNTED_PLAYOFF_BRACKETS
    return False


def in_filter(stage: str, filter_name: str) -> bool:
    if filter_name == "all":
        return True
    return (filter_name == "regular") == (stage == "regular-season")


def round_points(value: float) -> float:
    """Half up to two decimals on the double (JavaScript Math.round(value * 100) / 100 for the non-negative sums)."""
    return math.floor(value * 100 + 0.5) / 100


def game_record(season: str, week: int, matchup_id: str, stage: str, bracket: str | None, outcome: str,
                team_points: float | None, opponent_points: float | None) -> dict[str, Any]:
    both = team_points is not None and opponent_points is not None
    return {
        "Season": season,
        "Week": week,
        "FantasyMatchupID": matchup_id,
        "Stage": stage,
        "Bracket": bracket,
        "Outcome": outcome,
        "TeamPoints": team_points,
        "OpponentPoints": opponent_points,
        "Margin": abs(team_points - opponent_points) if both else None,
    }


def summarize(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Record of one team against one opponent over chronologically ordered counted games."""
    ordered = list(games)
    wins = [g for g in ordered if g["Outcome"] == "win" and g["Margin"] is not None]
    losses = [g for g in ordered if g["Outcome"] == "loss" and g["Margin"] is not None]
    biggest = sorted(wins, key=lambda g: -g["Margin"])[0] if wins else None
    closest = sorted(losses, key=lambda g: g["Margin"])[0] if losses else None
    points_for = 0.0
    points_against = 0.0
    for game in ordered:
        points_for += game["TeamPoints"] or 0.0
        points_against += game["OpponentPoints"] or 0.0
    return {
        "Wins": sum(1 for g in ordered if g["Outcome"] == "win"),
        "Losses": sum(1 for g in ordered if g["Outcome"] == "loss"),
        "Ties": sum(1 for g in ordered if g["Outcome"] == "tie"),
        "PointsFor": round_points(points_for),
        "PointsAgainst": round_points(points_against),
        "BiggestWinMatchupID": biggest["FantasyMatchupID"] if biggest else None,
        "ClosestLossMatchupID": closest["FantasyMatchupID"] if closest else None,
        "Games": ordered,
    }
