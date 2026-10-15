"""grading-v1: rank grade (A to F), exact port of Get-LetterGrade / Add-PositionalGradings (ADR-055).

The grade is the first letter whose threshold times the position multiplier is greater than or equal to
the Combined_Pos rank; above the last threshold it is F. Multipliers: K 1, RB and WR 2, everything else
1.5 (position match is case-insensitive like PowerShell ``-eq``).

A player without a Combined_Pos rank gets no grade: the Rank row carries null for Value, Rank and Grade.
The legacy PowerShell code graded such a player as if the rank were 0 and gave an A; Robert decided on
2026-10-15 that this is a defect and corrected it in v1 itself (an explicit, one-time exception to model
immutability, because the model had only been in productive use for hours and the old behaviour was never
intended). The Form row of the Players grading is not part of this model.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any

from .._common import require_finite

MODEL_ID = "grading-v1"
KIND = "grading"

PARAMS = MappingProxyType({
    "Thresholds": (6, 12, 18, 24, 30),
    "Grades": ("A", "B", "C", "D", "E", "F"),
    "PositionMultiplier": MappingProxyType({"K": 1.0, "RB": 2.0, "WR": 2.0}),
    "DefaultMultiplier": 1.5,
})


def letter_grade(rank: float | None, position: str | None) -> str | None:
    """Letter for a rank, or None when the player has no rank (unknown, never a grade)."""
    if rank is None:
        return None
    value = require_finite(rank, "rank")
    multiplier = PARAMS["PositionMultiplier"].get(str(position or "").upper(), PARAMS["DefaultMultiplier"])
    grades = PARAMS["Grades"]
    for threshold, grade in zip(PARAMS["Thresholds"], grades):
        if value <= threshold * multiplier:
            return grade
    return grades[-1]


def rank_row(rank: int | None, position: str | None) -> dict[str, Any]:
    """The Rank grading row as Players.json carries it."""
    return {"Type": "Rank", "Value": rank, "Rank": rank, "Grade": letter_grade(rank, position)}
