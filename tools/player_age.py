"""Shared deterministic player-age calculation for canonical-data consumers.

The decimal year rule preserves the legacy .NET half-to-even rounding used by
Players.json; the reference date is an explicit input, never a wall-clock read.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

DAYS_PER_YEAR = 365.2425


def age_at(birth_date: Any, as_of: date) -> float | None:
    """Age to one decimal; missing/invalid BirthDate yields None."""
    try:
        born = datetime.strptime(str(birth_date), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    years = (as_of - born).days / DAYS_PER_YEAR
    return float(round(years * 10.0) / 10.0)
