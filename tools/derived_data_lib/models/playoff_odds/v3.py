"""playoff-odds-v3: A1: exact equally weighted W/T/L scenarios (Issue #1693).

No team strength, points tiebreak estimate, form or simulation. Final records
with equal win percentage share their positions equally until regular-season
completion. Parameters and the versioned adapter are immutable after use.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .record_model_v1 import compute_record_odds

MODEL_ID = "playoff-odds-v3"
KIND = "playoff-odds"
PARAMS = MappingProxyType({
    "OutcomeWeights": (1, 1, 1),  # loss, tie, win
    "MinPlayedFraction": (2, 5),
    "MaxStates": 750_000,
    "MaxTransitions": 8_000_000,
    "EqualRecordTieRule": "equal-record-teams-share-places",
})


def compute(*, teams: Sequence[Mapping[str, Any]], open_games: Sequence[tuple[str, str]],
            playoff_teams: Any, regular_season_complete: bool) -> dict[str, Any]:
    return compute_record_odds(model_id=MODEL_ID, params=PARAMS, teams=teams, open_games=open_games,
                               playoff_teams=playoff_teams, regular_season_complete=regular_season_complete)
