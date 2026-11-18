"""Season-scoped nflverse franchise abbreviation reconciliation.

This is an identity-context alias, NOT player identity resolution. Canonical
GameIDs and schedule teams retain their historical era tokens, while nflverse
stat/play row team labels may use modern franchise abbreviations. Each allowed
pair is limited to the documented historical window; arbitrary mismatches fail.
Shared by NFL Games original PBP audit and Core GameDetail.
"""
from __future__ import annotations

HISTORICAL_FRANCHISE_NAMES = (
    (1999, 2016, frozenset(("SD", "LAC"))),
    (1999, 2019, frozenset(("OAK", "LV"))),
    (1999, 2015, frozenset(("STL", "LA"))),
)


def franchise_equal(provider_team: str, canonical_team: str, season: int) -> bool:
    if provider_team == canonical_team:
        return True
    if not isinstance(provider_team, str) or not isinstance(canonical_team, str):
        return False
    return any(
        start <= season <= end and {provider_team, canonical_team} == pair
        for start, end, pair in HISTORICAL_FRANCHISE_NAMES
    )


def reconcile_game_team(
    team: str, opponent: str, away: str, home: str, season: int,
) -> str | None:
    """Return exactly one canonical team only for a fully consistent two-team pair."""
    if franchise_equal(team, away, season) and franchise_equal(opponent, home, season):
        return away
    if franchise_equal(team, home, season) and franchise_equal(opponent, away, season):
        return home
    return None
