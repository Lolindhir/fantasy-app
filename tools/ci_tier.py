"""Test tier marker shared by the Fast and Deep CI lanes (Issue #1122).

A test module may mix cheap deterministic cases with one expensive
real-source replay. The Fast lane exports ``CI_TEST_TIER=fast`` and skips the
cases decorated with ``deep_only``; every other context (Deep lane, full audit,
local runs) executes them, so a Deep module is never weakened.
"""
from __future__ import annotations

import os
import unittest

FAST_ENV = "CI_TEST_TIER"


def fast_tier() -> bool:
    return os.environ.get(FAST_ENV) == "fast"


def deep_only(reason: str):
    """Skip the decorated test (or class) in the Fast lane only."""
    return unittest.skipIf(fast_tier(), f"Deep-only: {reason}")
