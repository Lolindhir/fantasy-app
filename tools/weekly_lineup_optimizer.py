"""Deterministic, position-constrained hindsight fantasy lineup optimization.

The caller owns season-specific slot eligibility and week-scoped roster/points
facts. This module deliberately does not infer positions, ownership, or locks.
It can therefore be reused by weekly team awards without creating a second
league-rule implementation alongside FantasyRelevance slot eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True)
class StartingSlot:
    slot_id: str
    eligible_positions: frozenset[str]


@dataclass(frozen=True)
class ScoredPlayer:
    player_id: str
    position: str
    points: Decimal | int | float | str


@dataclass(frozen=True)
class LineupAssignment:
    slot_id: str
    player_id: str
    points: Decimal


@dataclass(frozen=True)
class OptimalLineup:
    points: Decimal
    assignments: tuple[LineupAssignment, ...]
    unfilled_slot_ids: tuple[str, ...]


def _min_cost_assignment(costs: list[list[int]]) -> list[int]:
    """Rectangular Hungarian algorithm, rows <= columns; returns column/row.

    Matching is global rather than greedy, so overlapping FLEX slot types do
    not steal players needed by more restrictive positions.
    """
    row_count = len(costs)
    col_count = len(costs[0])
    if row_count > col_count:
        raise ValueError("Assignment requires at least as many columns as rows")
    infinity = max(abs(value) for row in costs for value in row) * (row_count + 2) + 1
    row_potential = [0] * (row_count + 1)
    col_potential = [0] * (col_count + 1)
    matching = [0] * (col_count + 1)
    path = [0] * (col_count + 1)

    for row in range(1, row_count + 1):
        matching[0] = row
        min_cost = [infinity] * (col_count + 1)
        visited = [False] * (col_count + 1)
        column = 0
        while True:
            visited[column] = True
            active_row = matching[column]
            delta = infinity
            next_column = 0
            for candidate in range(1, col_count + 1):
                if visited[candidate]:
                    continue
                reduced = (
                    costs[active_row - 1][candidate - 1]
                    - row_potential[active_row]
                    - col_potential[candidate]
                )
                if reduced < min_cost[candidate]:
                    min_cost[candidate] = reduced
                    path[candidate] = column
                if min_cost[candidate] < delta:
                    delta = min_cost[candidate]
                    next_column = candidate
            for candidate in range(col_count + 1):
                if visited[candidate]:
                    row_potential[matching[candidate]] += delta
                    col_potential[candidate] -= delta
                else:
                    min_cost[candidate] -= delta
            column = next_column
            if matching[column] == 0:
                break
        while True:
            previous = path[column]
            matching[column] = matching[previous]
            column = previous
            if column == 0:
                break

    chosen = [-1] * row_count
    for column in range(1, col_count + 1):
        if matching[column]:
            chosen[matching[column] - 1] = column - 1
    return chosen


def maximize_lineup(
    slots: Iterable[StartingSlot],
    players: Iterable[ScoredPlayer],
) -> OptimalLineup:
    """Return the theoretical highest-scoring position-conformant lineup.

    Every rostered player supplied by the caller can compete, including taxi,
    reserve/IR and bench; the caller must supply the *historical* team roster.
    An empty slot is allowed and scores zero, including when the only legal
    available player has negative points. This is an explicit theoretical
    potential convention, not a simulation of Sleeper lineup submission rules.
    """
    slot_list = list(slots)
    player_list = list(players)
    if len({slot.slot_id for slot in slot_list}) != len(slot_list):
        raise ValueError("Duplicate lineup slot IDs")
    if len({player.player_id for player in player_list}) != len(player_list):
        raise ValueError("Duplicate player IDs")
    if any(not slot.slot_id or not slot.eligible_positions for slot in slot_list):
        raise ValueError("Slot ID and eligible positions must be present")
    if any(not player.player_id or not player.position for player in player_list):
        raise ValueError("Player ID and position must be present")
    if not slot_list:
        return OptimalLineup(Decimal(0), (), ())

    scored: list[tuple[ScoredPlayer, Decimal]] = []
    for player in player_list:
        try:
            score = Decimal(str(player.points))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid points for {player.player_id}") from exc
        if not score.is_finite():
            raise ValueError(f"Non-finite points for {player.player_id}")
        scored.append((player, score))

    # Fix input-order dependence: equal-score solutions get a deterministic
    # canonical traversal order. Award score, not arbitrary tie order, is key.
    scored.sort(key=lambda item: item[0].player_id)
    decimal_places = max((max(0, -score.as_tuple().exponent) for _, score in scored), default=0)
    scale = 10**decimal_places
    weights = [int(score * scale) for _, score in scored]
    penalty = sum(abs(value) for value in weights) + 1
    costs = []
    for slot in slot_list:
        costs.append([
            -weight if player.position in slot.eligible_positions else penalty
            for (player, _), weight in zip(scored, weights)
        ] + [0] * len(slot_list))  # virtual empty candidates, one per slot

    chosen = _min_cost_assignment(costs)
    assignments = []
    unfilled = []
    total = Decimal(0)
    for slot, column in zip(slot_list, chosen):
        if column >= len(scored):
            unfilled.append(slot.slot_id)
            continue
        player, score = scored[column]
        if player.position not in slot.eligible_positions:
            raise RuntimeError("Optimizer selected an ineligible player")
        assignments.append(LineupAssignment(slot.slot_id, player.player_id, score))
        total += score
    return OptimalLineup(total, tuple(assignments), tuple(unfilled))
