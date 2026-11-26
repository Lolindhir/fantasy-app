"""Exact W/T/L outcome-mass kernel for Issue #1693 (A1/A2 candidate).

Pure integer arithmetic; each state stores the total mass of all paths yielding
the same vector of doubled standings points (2*Wins + Ties). The caller owns
model selection, the as-of gate, official final standings and JSON delivery.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import lcm
from typing import Sequence


class EnumerationLimit(ValueError):
    """A deterministic work limit was reached; never return partial odds."""


@dataclass(frozen=True)
class ExactPlaces:
    denominator: int
    numerators: tuple[tuple[int, ...], ...]
    state_count: int
    transitions: int


def enumerate_places(
    starts: Sequence[int],
    pairs: Sequence[tuple[int, int]],
    weights: tuple[int, int, int],
    *,
    max_states: int,
    max_transitions: int,
) -> ExactPlaces:
    """Exact marginal place mass, equally splitting ties in final record.

    weights correspond to first-team loss, tie, win. All must be positive.
    starts and pairs use the same team index; final game counts must be equal
    in the caller. The integer denominator includes lcm(1..team_count) so
    equally splitting any tied block never needs rounding or permutations.
    """
    n = len(starts)
    if n < 2 or any(type(s) is not int or s < 0 for s in starts):
        raise ValueError("Invalid initial standings scores")
    if len(weights) != 3 or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("Expected positive integer W/T/L weights")
    if type(max_states) is not int or type(max_transitions) is not int or min(max_states, max_transitions) < 1:
        raise ValueError("Expected positive integer work limits")
    for a, b in pairs:
        if type(a) is not int or type(b) is not int or not (0 <= a < n and 0 <= b < n) or a == b:
            raise ValueError("Invalid open game pairing")
    states: dict[tuple[int, ...], int] = {tuple(starts): 1}
    transitions = 0
    for a, b in pairs:
        transitions += 3 * len(states)
        if transitions > max_transitions:
            raise EnumerationLimit("transition-limit-exceeded")
        nxt: dict[tuple[int, ...], int] = {}
        for state, mass in states.items():
            new = list(state)
            for outcome, weight in enumerate(weights):
                new[a] = state[a] + outcome
                new[b] = state[b] + 2 - outcome
                key = tuple(new)
                nxt[key] = nxt.get(key, 0) + mass * weight
                if len(nxt) > max_states:
                    raise EnumerationLimit("state-limit-exceeded")
        states = nxt

    scale = lcm(*range(1, n + 1))
    denominator = sum(weights) ** len(pairs) * scale
    numerators = [[0] * n for _ in range(n)]
    for state, mass in states.items():
        order = sorted(range(n), key=lambda i: -state[i])
        first = 0
        while first < n:
            end = first + 1
            while end < n and state[order[end]] == state[order[first]]:
                end += 1
            share = mass * scale // (end - first)
            for i in order[first:end]:
                for place in range(first, end):
                    numerators[i][place] += share
            first = end
    return ExactPlaces(denominator, tuple(tuple(row) for row in numerators), len(states), transitions)
