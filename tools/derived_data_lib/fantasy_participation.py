"""Fantasy-relevant game predicate (Issue #1236).

This is NOT an NFL participation counter. Scoreless special-teams-only appearances
must not dilute salary. Non-K nonzero scoring counts regardless of offensive snaps;
kickers retain their established attempt-based participation predicate.
"""
from __future__ import annotations


def is_fantasy_game(position: str, offense_snaps: float, kick_attempts: float, points: float) -> bool:
    if position == "K":
        return kick_attempts > 0
    return offense_snaps > 0 or points != 0
