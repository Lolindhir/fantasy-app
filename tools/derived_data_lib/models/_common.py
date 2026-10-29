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


def dotnet_round(value: float, digits: int) -> float:
    """[math]::Round(value, digits) of .NET: scale by 10**digits, round half to even, scale back.

    Python's round(value, digits) rounds the exact decimal expansion and differs on values such as 2.675;
    PowerShell (.NET 5+) scales the double first. The models reproduce the PowerShell results exactly.
    """
    if not math.isfinite(value):
        raise ValueError(f"cannot round a non-finite value: {value!r}")
    power = 10.0 ** digits
    return float(round(value * power)) / power


def sequential_sum(values) -> float:
    """Left-to-right double accumulation like Measure-Object -Sum; no compensated summation."""
    total = 0.0
    for value in values:
        total += value
    return total


def ps_text(value: object) -> str:
    """String interpolation of a number as PowerShell does it (invariant, whole doubles without decimals)."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value) and value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return repr(value)
    return str(value)
