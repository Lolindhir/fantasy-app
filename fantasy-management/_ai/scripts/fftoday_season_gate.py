#!/usr/bin/env python3
"""Phase gate for the FFToday preseason projection fetchers."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nfl_season_context import (  # noqa: E402
    NflSeasonContextError,
    resolve_nfl_season_context,
)

ACTIVE_PHASE = "pre_regular_season"


def skip_reason(repo_root: Path, season: int, as_of: datetime) -> str | None:
    """Return why FFToday must not be requested now, or None when the preseason is active.

    FFToday only publishes preseason projections. Outside the canonical
    pre_regular_season phase there is nothing new to fetch, so no request is made.
    A season without a canonical schedule is not an active preseason either.
    """

    try:
        context = resolve_nfl_season_context(repo_root, as_of=as_of, season=season)
    except NflSeasonContextError as exc:
        return f"no canonical NFL schedule for season {season} ({exc})"
    phase = context["phase"]
    if phase != ACTIVE_PHASE:
        return f"NFL season {season} is in phase {phase}, FFToday only publishes preseason projections"
    return None
