"""rivalry-v2: every completed fantasy duel counts for head-to-head history (Issue #1470).

This is an immutable successor to rivalry-v1. The input assembler admits only matchups with
CompletionState='final', a result and exactly two participants. The bracket label remains
provenance/description, never an eligibility filter: championship, placement, consolation,
unclassified and missing labels are all countable after game finality. Unlike v1, a
finalized playoff game of a running season counts immediately.

The v1 record, outcome, points and rounding implementations are deliberately reused,
so the only changed domain rule is playoff eligibility.
"""
from __future__ import annotations

from types import MappingProxyType

from . import v1

MODEL_ID = "rivalry-v2"
KIND = "rivalry"

FILTERS = v1.FILTERS
PARAMS = MappingProxyType({
    "Filters": FILTERS,
    "CountedPlayoffBrackets": "all (including unclassified)",
    "PlayoffsCountAfterSeasonEnd": False,
    "PointsRounding": "half-up-2",
    "Ranking": "none",
})


def counts(stage: str, bracket: str | None, season_complete: bool) -> bool:
    """Admit every finalized regular-season or playoff matchup (the caller gates finality)."""
    return stage in ("regular-season", "playoffs")


in_filter = v1.in_filter
round_points = v1.round_points
game_record = v1.game_record
summarize = v1.summarize
