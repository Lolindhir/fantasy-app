from __future__ import annotations

from typing import Any


# nflverse weekly player stats contain a small number of legacy provider values
# that are not ordinary GSIS person identifiers. Keep those cases explicit and
# evidence-backed instead of teaching the canonical identity model to name-match.
PLAYER_STATS_NON_PLAYER_SOURCE_IDS: dict[str, dict[str, Any]] = {
    "0": {
        "Class": "team-aggregate",
        "Reason": (
            "Legacy nflverse player-stats rows use player_id=0 for unnamed team-level "
            "defensive/penalty aggregates across multiple teams; this token cannot identify a person."
        ),
    },
}


# This one-off legacy nflverse token is linked to Fernando Smith through external
# provider evidence, not through display-name matching. The 2000 Week 7 STL-ATL
# NFL gamebook credits the same Rams defender as S.Fernando, while authoritative
# roster/transaction history identifies Fernando Smith on the Rams; PFR's durable
# player identifier for Fernando Smith is SmitFe20.
PLAYER_STATS_VERIFIED_PROVIDER_ALIASES: dict[str, dict[str, str]] = {
    "XX-0000001": {
        "TargetProvider": "PFR",
        "TargetID": "SmitFe20",
        "Reason": "legacy nflverse synthetic player_id for Fernando Smith",
        "EvidenceGamebook": "https://www.nflgsis.com/2000/reg/07/1078/Gamebook.pdf",
        "EvidencePFR": "https://www.pro-football-reference.com/players/S/SmitFe20.htm",
    },
}


def non_player_stat_identity(source_id: str | None) -> dict[str, Any] | None:
    if not source_id:
        return None
    return PLAYER_STATS_NON_PLAYER_SOURCE_IDS.get(source_id)


def verified_stat_alias(source_id: str | None) -> dict[str, str] | None:
    if not source_id:
        return None
    return PLAYER_STATS_VERIFIED_PROVIDER_ALIASES.get(source_id)
