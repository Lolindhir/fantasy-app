"""weekly-recap-v1: Weekly Recap baseline without player awards (Issue #499).

Registers the behaviour of the Weekly Recaps before the weekly player awards: KeyPlayers, KeyGames, TeamAwards, lineup efficiency and the win
probability marks only. It computes nothing itself; ``PLAYER_AWARDS`` is False, so the recap carries no ``PlayerAwards`` field. A model is a pure
function of its explicit inputs: it reads no file, no clock and no league configuration. Immutable after its first productive use; any change is a
new version (``weekly-recap-v2`` adds the player awards).
"""
from __future__ import annotations

from types import MappingProxyType

MODEL_ID = "weekly-recap-v1"
KIND = "weekly-recap"

PLAYER_AWARDS = False

PARAMS = MappingProxyType({
    "PlayerAwards": PLAYER_AWARDS,
})
