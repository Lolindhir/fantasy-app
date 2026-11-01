"""auto-cut-v1: non-authoritative projected salary-cap cuts for a fantasy team (#1237).

Exact behavioral port of RuleBasedAutoCut: while roster cap usage exceeds the given
league cap, remove the current sixth-highest-paid player (stable ties), recompute
usage and stop when under cap or no sixth player exists. Call independently with
current and projected salary inputs; no roster changes are persisted by this model.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Iterable

from ..roster_cap import v1 as roster_cap

MODEL_ID = "auto-cut-v1"
KIND = "auto-cut"
PARAMS = MappingProxyType({"CutSalaryRank": 6})


@dataclass(frozen=True)
class CutDecision:
    player_id: str
    cut_order: int
    salary_rank: int
    salary_used: int | float
    cap_before_cut: int | float
    cap_after_cut: int | float


def compute(roster: Iterable[roster_cap.SalaryEntry], top_n: int, cap_limit: int | float) -> tuple[CutDecision, ...]:
    """Return deterministic ordered candidate cuts; do not mutate the input roster."""
    if isinstance(cap_limit, bool) or not isinstance(cap_limit, (int, float)) or not isfinite(cap_limit):
        raise ValueError(f"cap_limit must be finite numeric, got {cap_limit!r}")
    remaining = list(roster)
    current_cap = roster_cap.compute(remaining, top_n).cap
    cuts: list[CutDecision] = []
    while current_cap > cap_limit:
        salary_order = sorted(remaining, key=lambda player: -player.salary)
        rank = PARAMS["CutSalaryRank"]
        if len(salary_order) < rank:
            break
        candidate = salary_order[rank - 1]
        before = current_cap
        remaining = [player for player in remaining if player.player_id != candidate.player_id]
        current_cap = roster_cap.compute(remaining, top_n).cap
        cuts.append(CutDecision(candidate.player_id, len(cuts) + 1, rank, candidate.salary, before, current_cap))
    return tuple(cuts)
