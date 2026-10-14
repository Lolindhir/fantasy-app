"""Player rankings: Total, PerGame, Combined, position variants and Combined_Previous (ADR-055).

Exact port of RequestPlayers.ps1::Add-Rankings and PlayerUtils.psm1::Add-PreviousSeasonCombinedRanking.
This is a deterministic order statistic without league choice, so it has no model ID; its behaviour is part
of the player-valuation product contract (``derived-models.yaml``, ``rankingFunctions``).

* Active players have ``avg_potential_game > 0`` and ``avg_game > 0``; inactive players get no rows.
* Ranks are competition ranks: equal values share the rank of the first of them and the following rank
  skips (1, 1, 3). The tiebreak sort keys of the PowerShell version never changed a rank and are not needed.
* Combined = rank of ``rankTotal * 0.5 + rankPerGame * 0.5`` (ascending); ``_Pos`` types use the same rules
  inside one position group; ``Combined_Previous`` ranks the newest previous season of players whose
  previous ``avg_potential_game`` and ``avg_game`` are both greater than 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable, Sequence

from .models._common import require_finite

WEIGHT_TOTAL = 0.5
WEIGHT_GAME = 0.5
RANKING_TYPES = ("Total", "PerGame", "Combined", "Total_Pos", "PerGame_Pos", "Combined_Pos", "Combined_Previous")


@dataclass(frozen=True)
class RankingInput:
    """League-scored averages of one player; ``key`` is the row key (any unique hashable)."""

    key: Hashable
    position: str
    avg_potential_game: float
    avg_game: float
    previous_avg_potential_game: float | None = None
    previous_avg_game: float | None = None


def _competition_ranks(items: Sequence[RankingInput], value_of: Callable[[RankingInput], float],
                       *, descending: bool) -> dict[Hashable, int]:
    ranks: dict[Hashable, int] = {}
    previous: float | None = None
    rank = 0
    for index, item in enumerate(sorted(items, key=value_of, reverse=descending), start=1):
        value = value_of(item)
        if previous is None or value != previous:
            rank = index
        previous = value
        ranks[item.key] = rank
    return ranks


def _combined(items: Sequence[RankingInput], rank_total: dict[Hashable, int], rank_game: dict[Hashable, int],
              *, require_positive: bool) -> dict[Hashable, int]:
    values = {item.key: rank_total[item.key] * WEIGHT_TOTAL + rank_game[item.key] * WEIGHT_GAME for item in items}
    kept = [item for item in items if not require_positive or values[item.key] > 0]
    return _competition_ranks(kept, lambda item: values[item.key], descending=False)


def compute_rankings(players: Sequence[RankingInput]) -> dict[Hashable, list[dict[str, int | str]]]:
    """Ranking rows per player key in ``RANKING_TYPES`` order; every input key is present (empty = inactive)."""
    keys = [player.key for player in players]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate ranking key")
    result: dict[Hashable, dict[str, int]] = {key: {} for key in keys}

    active = []
    for player in players:
        total = require_finite(player.avg_potential_game, "avg_potential_game")
        game = require_finite(player.avg_game, "avg_game")
        if total > 0 and game > 0:
            if not isinstance(player.position, str) or not player.position:
                raise ValueError(f"Active player {player.key!r} has no position")
            active.append(player)

    def by_total(item: RankingInput) -> float:
        return item.avg_potential_game

    def by_game(item: RankingInput) -> float:
        return item.avg_game

    def add(groups: Sequence[RankingInput], names: tuple[str, str, str]) -> None:
        rank_total = _competition_ranks(groups, by_total, descending=True)
        rank_game = _competition_ranks(groups, by_game, descending=True)
        for key, rank in rank_total.items():
            result[key][names[0]] = rank
        for key, rank in rank_game.items():
            result[key][names[1]] = rank
        for key, rank in _combined(groups, rank_total, rank_game, require_positive=True).items():
            result[key][names[2]] = rank

    add(active, ("Total", "PerGame", "Combined"))
    for position in sorted({player.position for player in active}):
        add([player for player in active if player.position == position],
            ("Total_Pos", "PerGame_Pos", "Combined_Pos"))

    with_history = []
    for player in players:
        if player.previous_avg_potential_game is None or player.previous_avg_game is None:
            continue
        previous_total = require_finite(player.previous_avg_potential_game, "previous_avg_potential_game")
        previous_game = require_finite(player.previous_avg_game, "previous_avg_game")
        if previous_total > 0 and previous_game > 0:
            with_history.append(RankingInput(player.key, player.position, previous_total, previous_game))
    previous_total_ranks = _competition_ranks(with_history, by_total, descending=True)
    previous_game_ranks = _competition_ranks(with_history, by_game, descending=True)
    for key, rank in _combined(with_history, previous_total_ranks, previous_game_ranks, require_positive=False).items():
        result[key]["Combined_Previous"] = rank

    return {key: [{"Type": name, "Value": ranks[name]} for name in RANKING_TYPES if name in ranks]
            for key, ranks in result.items()}
