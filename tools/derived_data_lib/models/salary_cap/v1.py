"""salary-cap-v1: league Salary Cap, exact port of the RequestLeague.ps1 computation (ADR-055).

TopN = SalaryRelevantTeamSize * TeamCount. The cap is the mean of the TopN highest salaries times
SalaryRelevantTeamSize times 0.9, rounded to whole dollars (round half to even). Fewer players than
TopN use all players. The model is called once with Salary (SalaryCap) and once with SalaryProjected
(SalaryCapProjected). TeamCount comes from the canonical league facts and is passed in by the caller.
Immutable after its first productive use; any change is ``salary-cap-v2``.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable

from .._common import require_finite, round_half_even

MODEL_ID = "salary-cap-v1"
KIND = "salary-cap"

PARAMS = MappingProxyType({
    "SalaryRelevantTeamSize": 20,
    "Factor": 0.9,
})


@dataclass(frozen=True)
class SalaryCapResult:
    cap: int
    top_n: int
    players_considered: int


def compute(salaries: Iterable[float], team_count: int) -> SalaryCapResult:
    if isinstance(team_count, bool) or not isinstance(team_count, int) or team_count < 1:
        raise ValueError(f"team_count must be a positive integer, got {team_count!r}")
    size = PARAMS["SalaryRelevantTeamSize"]
    top_n = size * team_count
    values = [require_finite(value, "salary") for value in salaries]
    if not values:
        raise ValueError("No salaries given for the Salary Cap calculation")
    top = sorted(values, reverse=True)[:top_n]
    return SalaryCapResult(
        cap=round_half_even(raw_cap(top, size)),
        top_n=top_n,
        players_considered=len(top),
    )


def raw_cap(top_salaries: Iterable[float], relevant_team_size: int | None = None) -> float:
    """Unrounded cap of the already selected top salaries (descending order, accumulated sequentially).

    ``compute`` rounds this value; analyses that only need the raw figure call it directly.
    """
    size = PARAMS["SalaryRelevantTeamSize"] if relevant_team_size is None else relevant_team_size
    # Sequential accumulation in descending order like Measure-Object; built-in sum() is compensated
    # for floats since Python 3.12 and would not be bit-identical for non-integral salaries.
    values = list(top_salaries)
    total = 0.0
    for value in values:
        total += value
    average = total / len(values)
    return average * size * PARAMS["Factor"]
