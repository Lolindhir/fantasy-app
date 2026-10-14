"""Numeric helpers shared by the models (no model-specific behaviour)."""
from __future__ import annotations

import math
from typing import Any


def require_finite(value: Any, name: str) -> float:
    """Return ``value`` as float; booleans, non-numbers, NaN and infinity are errors."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def round_half_even(value: float) -> int:
    """[math]::Round(value): round half to even on the binary value, whole units."""
    return int(round(value))
