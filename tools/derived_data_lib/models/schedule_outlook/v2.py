"""schedule-outlook-v2: schedule outlook with a fact-based strength of schedule (Issue #1589).

Same pure regular-season remainder and playoff-path reconstruction as schedule-outlook-v1 (reused, not
copied), but the opponent strength is a pure statement about *points scored*, never a projection:

* Current strength = RelativeScoringStrength of the season-statistics product at the cutoff (team points per
  game / league points per team-game), already as-of safe.
* Previous strength = the same figure at the end of the same team's previous regular season (matched by
  TeamID = provider roster identity, like the all-time standings). Missing previous season gives None.
* Blend: with g = games played, the current season counts with g / (g + K) and the previous season with the
  rest. Before game 1 only the previous season counts; without a previous season the current season counts
  alone once g >= 1, and before that the strength is None (never an invented 1.0 or 50 percent).
* Remaining schedule: mean strength of the remaining opponents divided by the mean strength of the *other*
  teams (self-exclusion: the team never plays itself, so its own strength must not shape the baseline).
  1.0 means an average schedule. No displayed rank.
* Classification thresholds live here (PARAMS) so the frontend only displays: per opponent weaker / similar /
  stronger relative to league average 1.0, for the rest of the schedule easier / average / harder.

A missing opponent strength makes the remaining-schedule value None; it is never replaced by league average.
The model has no file/network/clock access. K is a parameter (default PARAMS) so a future model version can
change it without touching old seasons.
"""
from __future__ import annotations

from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from . import v1 as _v1
from .v1 import ScheduleOutlookError, compute_playoff_paths  # noqa: F401  (re-exported: identical semantics)

MODEL_ID = "schedule-outlook-v2"
KIND = "schedule-outlook"
USES_PREVIOUS_SEASON = True
PARAMS = MappingProxyType({
    "Digits": 4,
    "Strength": "points-per-game-relative-to-league-blended-with-previous-season",
    "CurrentSeasonWeightK": 3,
    "OpponentBand": 0.05,
    "ScheduleBand": 0.03,
    "RemainingSoS": "mean-remaining-opponents-over-mean-other-teams",
    "ZeroRemainingGames": "null",
})
DIGITS = 4


def _round(number: float | None) -> float | None:
    return None if number is None else round(number, DIGITS) + 0.0


def _usable(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) and number >= 0 else None


def blend(current: float | None, previous: float | None, games: int, k: float) -> tuple[float | None, float]:
    """Return (strength, weight of the current season) for one team."""
    if games <= 0:
        return previous, 0.0
    weight = games / (games + k)
    if previous is None:
        return current, 1.0
    if current is None:
        return None, weight
    return weight * current + (1 - weight) * previous, weight


def classify_opponent(strength: float | None, band: float) -> str | None:
    if strength is None:
        return None
    return "weaker" if strength < 1 - band else "stronger" if strength > 1 + band else "similar"


def classify_schedule(ratio: float | None, band: float) -> str | None:
    if ratio is None:
        return None
    return "easier" if ratio < 1 - band else "harder" if ratio > 1 + band else "average"


def compute_regular_season(
    *,
    teams: Sequence[Mapping[str, Any]],
    pairings_by_week: Mapping[int, Sequence[Mapping[str, Any]]],
    strengths_by_roster: Mapping[str, Mapping[str, Any]],
    previous_strength_by_roster: Mapping[str, Any],
    after_week: int,
    regular_season_last_week: int,
    k: float | None = None,
) -> dict[str, Any]:
    """Week-cut-off outlook. ``strengths_by_roster`` holds RelativeScoringStrength at the cutoff (none at Week 0);
    ``previous_strength_by_roster`` the previous-season final value per roster (missing key or None = unknown)."""
    k = float(PARAMS["CurrentSeasonWeightK"] if k is None else k)
    if not isfinite(k) or k <= 0:
        raise ScheduleOutlookError("K must be a positive finite number")
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
        value, weight = blend(current, previous, games, k)
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
            "StrengthParams": {"CurrentSeasonWeightK": k, "OpponentBand": ob, "ScheduleBand": sb},
            "UpcomingMatchups": skeleton["UpcomingMatchups"], "Teams": result_teams}
