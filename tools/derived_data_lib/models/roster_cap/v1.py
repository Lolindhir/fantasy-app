"""roster-cap-v1: deterministic top-N salary usage of one fantasy roster (#1237).

This is not salary-cap-v1: salary-cap-v1 sets the *league-wide limit* using the NFL
salary population; this model sums the top N salaries on a single fantasy roster.
Input roster order breaks equal-salary ties exactly as in the former stable JS sort.
No I/O, clock, league default, publisher or App contract is part of this model.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Iterable

MODEL_ID = "roster-cap-v1"
KIND = "roster-cap"
PARAMS = MappingProxyType({"TieOrder": "input-stable"})


@dataclass(frozen=True)
class SalaryEntry:
    player_id: str
    salary: int | float


@dataclass(frozen=True)
class RosterCapResult:
    cap: int | float
    top_player_ids: tuple[str, ...]


def compute(roster: Iterable[SalaryEntry], top_n: int) -> RosterCapResult:
    """Select and sum the highest-paid roster players, stably by input order on ties."""
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError(f"top_n must be a positive integer, got {top_n!r}")
    entries = list(roster)
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry.player_id, str) or not entry.player_id.strip() or entry.player_id in seen:
            raise ValueError(f"missing or duplicate roster PlayerID: {entry.player_id!r}")
        seen.add(entry.player_id)
        if isinstance(entry.salary, bool) or not isinstance(entry.salary, (int, float)) or not isfinite(entry.salary):
            raise ValueError(f"non-finite or non-numeric salary for {entry.player_id!r}")
    top = sorted(entries, key=lambda player: -player.salary)[:top_n]
    total: int | float = 0
    for player in top:
        total += player.salary
    return RosterCapResult(cap=total, top_player_ids=tuple(player.player_id for player in top))
