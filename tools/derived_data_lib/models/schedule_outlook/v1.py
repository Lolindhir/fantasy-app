"""schedule-outlook-v1: pure regular-season remainder and two independent strength-of-schedule measures.

Issue #1519, checkpoint I1. This model accepts *only* normalized scheduled pairings and
already-cut-off historical team strengths. It has no file/network/clock access and cannot
inspect a future result, starter, roster, or bracket. The caller must establish that its
ratings belong to the requested as-of week and that its pairings are accepted canonical
source facts. Playoff paths and producer integration are deliberately later checkpoints.

A missing opponent rating never silently becomes zero or league average. A team is ranked
only when all its remaining opponents have a usable rating and the corresponding metric
is available for every team in the same snapshot.
"""
from __future__ import annotations

from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence

MODEL_ID = "schedule-outlook-v1"
KIND = "schedule-outlook"
PARAMS = MappingProxyType({
    "Digits": 4,
    "RemainingSoS": "arithmetic-mean-per-opponent-game",
    "Ranking": "competition-ascending-on-complete-coverage",
    "ZeroRemainingGames": "null",
})
DIGITS = 4
METRICS = (
    ("RelativeScoringStrength", "RemainingSoSRelativeStrength", "RemainingSoSRelativeStrengthRank"),
    ("ProjectedBestBallStrength", "RemainingOpponentBestBallStrength", "RemainingOpponentBestBallStrengthRank"),
)


class ScheduleOutlookError(ValueError):
    """Malformed or incomplete canonical schedule/identity evidence."""


def _text(value: Any) -> str:
    return value if isinstance(value, str) and value.strip() == value and value else ""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not isfinite(number) or number < 0:
        return None
    return number


def _round(number: float | None) -> float | None:
    return None if number is None else round(number, DIGITS) + 0.0


def compute_regular_season(
    *,
    teams: Sequence[Mapping[str, Any]],
    pairings_by_week: Mapping[int, Sequence[Mapping[str, Any]]],
    strengths_by_roster: Mapping[str, Mapping[str, Any]],
    after_week: int,
    regular_season_last_week: int,
) -> dict[str, Any]:
    """Build a week-cut-off regular-season outlook without reading an existing derived snapshot.

    `teams` must contain CanonicalLeagueRosterID and TeamID; future pairing records
    need only CanonicalLeagueMatchupID, Team1CanonicalLeagueRosterID and
    Team2CanonicalLeagueRosterID. The assembler MUST project raw matchups down to
    these three facts before calling this function. Historical strengths are
    looked up by canonical roster ID and must be prefiltered to `min(after_week,
    regular_season_last_week)` (none at Week 0).
    """
    if type(after_week) is not int or type(regular_season_last_week) is not int or after_week < 0 or regular_season_last_week < 1:
        raise ScheduleOutlookError("Invalid Week cutoff or regular-season end")
    team_map: dict[str, Any] = {}
    team_ids: set[Any] = set()
    for team in teams:
        rid, tid = team.get("CanonicalLeagueRosterID"), team.get("TeamID")
        if not _text(rid) or type(tid) is not int or tid <= 0 or tid in team_ids or rid in team_map:
            raise ScheduleOutlookError("Duplicate or invalid canonical team identity")
        team_map[rid] = tid
        team_ids.add(tid)
    if len(team_map) < 2:
        raise ScheduleOutlookError("Expected at least two distinct fantasy teams")
    if after_week == 0 and strengths_by_roster:
        raise ScheduleOutlookError("Week 0 must not contain historical scored team ratings")
    if set(strengths_by_roster) - set(team_map):
        raise ScheduleOutlookError("Ratings contain an unknown canonical roster identity")

    upcoming: list[dict[str, Any]] = []
    by_team: dict[str, list[dict[str, Any]]] = {rid: [] for rid in team_map}
    for week in range(max(1, after_week + 1), regular_season_last_week + 1):
        raw_week = pairings_by_week.get(week)
        if raw_week is None:
            raise ScheduleOutlookError(f"Missing canonical pairing source for regular-season Week {week}")
        seen_teams: set[str] = set()
        seen_matchups: set[str] = set()
        pairs: list[tuple[str, str, str]] = []
        for row in raw_week:
            matchup, a, b = (row.get("CanonicalLeagueMatchupID"),
                             row.get("Team1CanonicalLeagueRosterID"), row.get("Team2CanonicalLeagueRosterID"))
            if not all(_text(x) for x in (matchup, a, b)) or a == b or a not in team_map or b not in team_map:
                raise ScheduleOutlookError(f"Invalid regular-season pairing in Week {week}")
            if matchup in seen_matchups or a in seen_teams or b in seen_teams:
                raise ScheduleOutlookError(f"Duplicate matchup or participant in Week {week}")
            seen_matchups.add(matchup)
            seen_teams.update((a, b))
            pairs.append((matchup, min(a, b), max(a, b)))
        if seen_teams != set(team_map):
            raise ScheduleOutlookError(f"Incomplete Week {week}: missing canonical matchup participants")
        for matchup, a, b in sorted(pairs, key=lambda x: (x[1], x[2], x[0])):
            upcoming.append({"Week": week, "CanonicalLeagueMatchupID": matchup,
                             "Team1CanonicalLeagueRosterID": a, "Team2CanonicalLeagueRosterID": b})
            for own, opponent in ((a, b), (b, a)):
                rating = strengths_by_roster.get(opponent) or {}
                game = {"Week": week, "CanonicalLeagueMatchupID": matchup,
                        "OpponentCanonicalLeagueRosterID": opponent, "OpponentTeamID": team_map[opponent]}
                for source_key, _, _ in METRICS:
                    game["Opponent" + source_key] = _round(_number(rating.get(source_key)))
                by_team[own].append(game)

    result_teams: list[dict[str, Any]] = []
    for rid, team_id in sorted(team_map.items(), key=lambda x: x[1]):
        games = by_team[rid]
        record: dict[str, Any] = {
            "TeamID": team_id, "CanonicalLeagueRosterID": rid, "RemainingGames": len(games),
            "Upcoming": games,
        }
        for source_key, output_key, rank_key in METRICS:
            values = [g["Opponent" + source_key] for g in games]
            record["Known" + source_key + "Games"] = sum(v is not None for v in values)
            record[output_key] = (_round(sum(values) / len(values)) if values and all(v is not None for v in values) else None)
            record[rank_key] = None
        result_teams.append(record)

    for _, score_key, rank_key in METRICS:
        values = [x[score_key] for x in result_teams]
        if all(v is not None for v in values):
            for item in result_teams:
                item[rank_key] = 1 + sum(v < item[score_key] for v in values)

    return {"AfterWeek": after_week, "RatingWeek": None if after_week == 0 else min(after_week, regular_season_last_week),
            "UpcomingMatchups": upcoming, "Teams": result_teams}
