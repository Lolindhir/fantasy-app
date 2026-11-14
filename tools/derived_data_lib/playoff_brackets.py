"""Playoff bracket label of a fantasy matchup (Issue #1455, amendment of ADR-075, .ai-context/manual/matchup-context.yaml).

The Matchups model only knows the stage of a week (regular season or playoffs). This module adds the bracket of a playoff matchup from the
canonical bracket facts: ``winners-bracket.json`` and ``losers-bracket.json`` of the season (Round, Match, Placement and both canonical roster
IDs per game) plus ``league.json`` ``WeekStructure`` (``PlayoffStartWeek``, ``PlayoffRoundType``, ``PlayoffRoundCount``). The label is fixed,
provider-neutral semantics without a model ID:

* ``championship``  winners-bracket game that is not a placement game (the title path including the final, Placement empty or 1)
* ``placement``     winners-bracket game with a Placement greater than 1 (third place game, fifth place game, ...)
* ``consolation``   losers-bracket game
* ``unclassified``  a playoff-stage matchup that cannot be assigned to exactly one bracket game (no game in the round window for the roster pair,
                    more than one, an unknown round format, a week outside the rounds, unresolved roster IDs); never guessed
* ``None``          regular-season matchup

A round maps to its weeks through ``PlayoffRoundType`` (Sleeper playoff_round_type): 0 one week per round, 1 one week per round except a two-week
final round, 2 two weeks per round. A matchup belongs to a bracket game when the round window of its week contains that game and the roster pair is
the pair of the game (order independent).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CHAMPIONSHIP = "championship"
PLACEMENT = "placement"
CONSOLATION = "consolation"
UNCLASSIFIED = "unclassified"
BRACKET_LABELS = (CHAMPIONSHIP, PLACEMENT, CONSOLATION, UNCLASSIFIED)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def round_windows(structure: Any) -> list[tuple[int, ...]] | None:
    """Weeks of each playoff round (round 1 first) or None when the format is unknown."""
    if not isinstance(structure, dict):
        return None
    start = _int(structure.get("PlayoffStartWeek"))
    count = _int(structure.get("PlayoffRoundCount"))
    round_type = structure.get("PlayoffRoundType")
    if start <= 0 or count <= 0 or isinstance(round_type, bool) or round_type not in (0, 1, 2):
        return None
    windows: list[tuple[int, ...]] = []
    week = start
    for index in range(count):
        two_week = round_type == 2 or (round_type == 1 and index == count - 1)
        windows.append((week, week + 1) if two_week else (week,))
        week += 2 if two_week else 1
    return windows


def _games(payload: Any, label: str) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError(f"{label} must be a list of bracket games")
    return [game for game in payload if isinstance(game, dict)]


def _pair(game: dict[str, Any]) -> frozenset[str] | None:
    first, second = game.get("Team1CanonicalLeagueRosterID"), game.get("Team2CanonicalLeagueRosterID")
    if not isinstance(first, str) or not isinstance(second, str) or not first or not second or first == second:
        return None
    return frozenset((first, second))


class SeasonBrackets:
    """Bracket games of one season indexed for matchup classification."""

    def __init__(self, structure: Any, winners: Any, losers: Any) -> None:
        self.windows = round_windows(structure)
        self.games: list[tuple[str, int, frozenset[str] | None]] = []
        for game in _games(winners, "winners-bracket"):
            placement = game.get("Placement")
            label = PLACEMENT if isinstance(placement, int) and not isinstance(placement, bool) and placement > 1 else CHAMPIONSHIP
            self.games.append((label, _int(game.get("Round")), _pair(game)))
        for game in _games(losers, "losers-bracket"):
            self.games.append((CONSOLATION, _int(game.get("Round")), _pair(game)))

    def classify(self, week: int, roster_ids: tuple[Any, Any]) -> str:
        if self.windows is None:
            return UNCLASSIFIED
        rounds = [index + 1 for index, window in enumerate(self.windows) if week in window]
        if len(rounds) != 1 or not all(isinstance(r, str) and r for r in roster_ids):
            return UNCLASSIFIED
        pair = frozenset(roster_ids)
        if len(pair) != 2:
            return UNCLASSIFIED
        labels = [label for label, rnd, game_pair in self.games if rnd == rounds[0] and game_pair == pair]
        return labels[0] if len(labels) == 1 else UNCLASSIFIED


def load_season_brackets(season_dir: Path, league_source: Any) -> SeasonBrackets:
    """Brackets of a canonical season directory; missing bracket files count as no games (every playoff matchup is then unclassified)."""
    import json

    def read(name: str) -> Any:
        path = season_dir / name
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    structure = league_source.get("WeekStructure") if isinstance(league_source, dict) else None
    return SeasonBrackets(structure, read("winners-bracket.json"), read("losers-bracket.json"))


__all__ = ["BRACKET_LABELS", "CHAMPIONSHIP", "CONSOLATION", "PLACEMENT", "UNCLASSIFIED", "SeasonBrackets", "load_season_brackets", "round_windows"]
