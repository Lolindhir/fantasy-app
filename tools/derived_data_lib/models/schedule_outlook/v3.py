"""schedule-outlook-v3: like schedule-outlook-v2, but the previous season fades out linearly (Issue #1607).

Only the weight of the previous season changes. With g = games played and R = number of regular-season weeks
of the season (read from the canonical week structure, never a constant), the current season counts with

    weight = min(1, g / (R / 2))

so before game 1 only the previous season counts (weight 0), the weight rises evenly, and from half of the
regular season on only the current season counts (R = 12: after week 6; R = 14: after week 7). A team without
a previous season uses the current season alone once g >= 1 (before that the strength is None, never invented).
Everything else (points-per-game-relative-to-league strength, remaining schedule, classification bands, no
projection input) is identical to v2 and reused from it. The model has no file/network/clock access.
"""
from __future__ import annotations

from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from . import v1 as _v1
from .v1 import ScheduleOutlookError, compute_playoff_paths  # noqa: F401  (re-exported: identical semantics)
from .v2 import _round, _usable, classify_opponent, classify_schedule

MODEL_ID = "schedule-outlook-v3"
KIND = "schedule-outlook"
USES_PREVIOUS_SEASON = True
PARAMS = MappingProxyType({
    "Digits": 4,
    "Strength": "points-per-game-relative-to-league-blended-with-previous-season",
    "PreviousSeasonFade": "linear-to-zero-at-half-of-regular-season-weeks",
    "FadeFraction": 0.5,
    "OpponentBand": 0.05,
    "ScheduleBand": 0.03,
    "RemainingSoS": "mean-remaining-opponents-over-mean-other-teams",
    "ZeroRemainingGames": "null",
})
DIGITS = 4


def current_weight(games: int, regular_season_weeks: int, fraction: float | None = None) -> float:
    """Weight of the current season: 0 before game 1, linear up to 1 at fraction * regular_season_weeks."""
    fraction = float(PARAMS["FadeFraction"] if fraction is None else fraction)
    if games <= 0:
        return 0.0
    horizon = regular_season_weeks * fraction
    return 1.0 if horizon <= 0 else min(1.0, games / horizon)


def blend(current: float | None, previous: float | None, games: int, weight: float) -> tuple[float | None, float]:
    """Return (strength, weight of the current season) for one team."""
    if games <= 0:
        return previous, 0.0
    if previous is None:
        return current, 1.0
    if current is None:
        return None, weight
    return weight * current + (1 - weight) * previous, weight


def compute_regular_season(
    *,
    teams: Sequence[Mapping[str, Any]],
    pairings_by_week: Mapping[int, Sequence[Mapping[str, Any]]],
    strengths_by_roster: Mapping[str, Mapping[str, Any]],
    previous_strength_by_roster: Mapping[str, Any],
    after_week: int,
    regular_season_last_week: int,
    fraction: float | None = None,
) -> dict[str, Any]:
    """Week-cut-off outlook. ``strengths_by_roster`` holds RelativeScoringStrength at the cutoff (none at Week 0);
    ``previous_strength_by_roster`` the previous-season final value per roster (missing key or None = unknown)."""
    fraction = float(PARAMS["FadeFraction"] if fraction is None else fraction)
    if not isfinite(fraction) or fraction <= 0:
        raise ScheduleOutlookError("FadeFraction must be a positive finite number")
    # Validation and the upcoming schedule come from v1 (no ratings passed; strengths are rebuilt here).
    skeleton = _v1.compute_regular_season(
        teams=teams, pairings_by_week=pairings_by_week, strengths_by_roster={},
        after_week=after_week, regular_season_last_week=regular_season_last_week)
    rids = {t["CanonicalLeagueRosterID"] for t in teams}
    if set(strengths_by_roster) - rids or set(previous_strength_by_roster) - rids:
        raise ScheduleOutlookError("Strengths contain an unknown canonical roster identity")
    games = min(after_week, regular_season_last_week)

    strength: dict[str, dict[str, Any]] = {}
    for rid in sorted(rids):
        current = _usable((strengths_by_roster.get(rid) or {}).get("RelativeScoringStrength"))
        previous = _usable(previous_strength_by_roster.get(rid))
        value, weight = blend(current, previous, games, current_weight(games, regular_season_last_week, fraction))
        strength[rid] = {"Value": _round(value), "CurrentRelative": _round(current) if games else None,
                         "PreviousRelative": _round(previous), "CurrentWeight": _round(weight), "GamesPlayed": games}
    raw = {rid: s["Value"] for rid, s in strength.items()}
    all_known = all(v is not None for v in raw.values())
    total = sum(raw.values()) if all_known else None
    n = len(rids)
    ob, sb = float(PARAMS["OpponentBand"]), float(PARAMS["ScheduleBand"])

    result_teams: list[dict[str, Any]] = []
    for team in skeleton["Teams"]:
        rid = team["CanonicalLeagueRosterID"]
        upcoming = []
        for game in team["Upcoming"]:
            opponent = raw[game["OpponentCanonicalLeagueRosterID"]]
            upcoming.append({
                "Week": game["Week"], "CanonicalLeagueMatchupID": game["CanonicalLeagueMatchupID"],
                "OpponentCanonicalLeagueRosterID": game["OpponentCanonicalLeagueRosterID"],
                "OpponentTeamID": game["OpponentTeamID"],
                "OpponentStrength": opponent, "OpponentClass": classify_opponent(opponent, ob),
            })
        values = [g["OpponentStrength"] for g in upcoming]
        ratio = None
        if upcoming and all(v is not None for v in values) and all_known:
            others = (total - raw[rid]) / (n - 1)
            if others > 0:
                ratio = _round((sum(values) / len(values)) / others)
        result_teams.append({
            "TeamID": team["TeamID"], "CanonicalLeagueRosterID": rid, "RemainingGames": team["RemainingGames"],
            "Strength": strength[rid],
            "KnownOpponentStrengthGames": sum(v is not None for v in values),
            "RemainingSoS": ratio, "RemainingSoSClass": classify_schedule(ratio, sb),
            "Upcoming": upcoming,
        })
    return {"AfterWeek": after_week, "RatingWeek": skeleton["RatingWeek"],
            "StrengthParams": {"FadeFraction": fraction, "OpponentBand": ob, "ScheduleBand": sb},
            "UpcomingMatchups": skeleton["UpcomingMatchups"], "Teams": result_teams}
