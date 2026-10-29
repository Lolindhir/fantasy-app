"""standings-v1: regular-season table, weekly tables, playoff placements and all-time standing (ADR-072).

Exact port of public/requests/utils/league/StandingUtils.psm1 (Issue #987), no new rule. A model is a pure
function of its explicit inputs: it reads no files, no clock and no league configuration. Teams are plain
dicts; the functions never mutate their inputs.

Team input (``Team``): TeamID (int), Owner, Team (team name), Points, PointsAgainst (float), Wins, Losses, Ties
(int), Record (e.g. ``WWLT``) and Streak (provider text). Results use the field names of the App contract
(Standings.json) so the consumer generator renders them without recomputation.

Rules in short: win percentage descending, points descending, points against ascending; equal keys (win
percentage to 6 decimals, points and points against to 2 decimals) share a place and the next place is the
previous plus one. Per-game values divide by the regular-season game count of the league, also while the
season is in progress (v1 behaviour). Weekly tables rebuild wins, losses, ties and points from the weekly
matchups and are accepted only while every result agrees with the team's Record (ADR-040).
Immutable after its first productive use; any change is ``standings-v2``.
"""
from __future__ import annotations

import math
import re
from types import MappingProxyType
from typing import Any, Iterable, Sequence

from .._common import dotnet_round, sequential_sum

MODEL_ID = "standings-v1"
KIND = "standings"

PARAMS = MappingProxyType({
    "RegularSeasonTiebreak": ("WinPercentage desc", "Points desc", "PointsAgainst asc"),
    "AllTimeTiebreak": ("RegularSeasonWins desc", "WinPercentage desc", "Points desc", "PointsAgainst asc"),
    "AllTimePlayoffTiebreak": (
        "Championships desc", "RunnerUps desc", "Thirds desc", "RegularSeasonWins desc",
        "PlaceAverage asc", "RegularSeasonPlace asc",
    ),
    "IronWillWinPercentageFactor": 0.25,
    "IronWillFallback": -999,
    "StreakScoreWinWeight": 0.001,
    "StreakScorePointWeight": 0.00001,
})

Team = dict[str, Any]


def ordinal(number: int) -> str:
    """Get-Ordinal: 0 -> none, 1st, 2nd, 3rd, otherwise the number plus th (11 -> 11th, 21 -> 21th)."""
    return {0: "none", 1: "1st", 2: "2nd", 3: "3rd"}.get(number, f"{number}th")


def win_percentage(team: Team) -> float:
    """Get-WinPct: -1 when no game was played."""
    games = team["Wins"] + team["Losses"] + team["Ties"]
    if games == 0:
        return -1
    return (team["Wins"] + 0.5 * team["Ties"]) / games


def _tie_key(win_pct: float, points: float, points_against: float) -> str:
    return f"{win_pct:,.6f}-{points:,.2f}-{points_against:,.2f}"


def rank_teams(teams: Sequence[Team], all_time: bool = False) -> list[Team]:
    """Get-RankedRegularSeasonStandings: sorted copies with ``PlaceRegular`` (season) or ``Place`` and ``PlaceOrdinal`` (all-time).

    Teams of an exact tie keep their input order (the PowerShell all-time hashtable order was undefined).
    """
    if all_time:
        ordered = sorted(teams, key=lambda t: (-t["RegularSeasonWins"], -win_percentage(t), -t["Points"], t["PointsAgainst"]))
    else:
        ordered = sorted(teams, key=lambda t: (-win_percentage(t), -t["Points"], t["PointsAgainst"]))
    result: list[Team] = []
    last_place: int | None = None
    last_key: str | None = None
    for index, source in enumerate(ordered):
        win_pct = win_percentage(source)
        key = _tie_key(win_pct, source["Points"], source["PointsAgainst"])
        place = 0
        if win_pct >= 0:
            if index == 0:
                place = 1
            elif key == last_key:
                place = last_place
            else:
                place = (last_place or 0) + 1
        team = dict(source)
        if all_time:
            team["Place"] = place
            team["PlaceOrdinal"] = ordinal(place)
        else:
            team["PlaceRegular"] = place
        result.append(team)
        last_place = place
        last_key = key
    return result


def format_win_percentage(value: float) -> str:
    """Format-WinPct: 1.000 for a perfect record, otherwise the three decimals without the leading zero."""
    if value == 1:
        return "1.000"
    return f"{dotnet_round(value, 3):.3f}"[1:]


def _max_run(record: str, letter: str) -> int:
    runs = [len(match.group(0)) for match in re.finditer(f"{letter}+", record)]
    return max(runs) if runs else 0


def regular_season_rows(
    teams: Sequence[Team],
    regular_season_games: int,
    previous_week_places: dict[int, int] | None = None,
    weekly_movements: dict[int, list[dict[str, int]]] | None = None,
) -> list[dict[str, Any]]:
    """Get-RegularSeasonStandings: one row per team in rank order with the App contract fields.

    ``previous_week_places`` (TeamID -> place after the preceding completed week) and ``weekly_movements`` add
    PreviousWeekPlace, PlaceDelta and WeeklyMovements to every row (ADR-040); None leaves the three fields at
    null / null / [].
    """
    if regular_season_games < 1:
        raise ValueError("regular_season_games must be a positive integer")
    count = len(teams)
    avg_ppg = sequential_sum(t["Points"] for t in teams) / (count * regular_season_games) if count else 0
    avg_pag = sequential_sum(t["PointsAgainst"] for t in teams) / (count * regular_season_games) if count else 0
    avg_win_pct = sequential_sum(win_percentage(t) for t in teams) / count if count else 0

    rows: list[dict[str, Any]] = []
    for team in rank_teams(teams):
        record = team["Record"] or ""
        # PowerShell measures the runs as doubles, so the App contract carries 3.0 and not 3.
        longest_win = float(_max_run(record, "W"))
        longest_loss = float(_max_run(record, "L"))
        win_pct = win_percentage(team)
        points_per_game = team["Points"] / regular_season_games
        points_against_per_game = team["PointsAgainst"] / regular_season_games
        points_diff = points_per_game - avg_ppg
        points_against_diff = points_against_per_game - avg_pag
        efficiency = points_diff + points_against_diff + team["Wins"]
        if avg_pag > 0:
            if win_pct * PARAMS["IronWillWinPercentageFactor"] < 0:
                raise ValueError("Iron will score needs at least one completed game")
            iron_will = points_against_per_game / avg_pag + math.sqrt(win_pct * PARAMS["IronWillWinPercentageFactor"])
        else:
            iron_will = PARAMS["IronWillFallback"]

        history: list[float] = []
        wins = 0
        for index, letter in enumerate(record):
            if letter == "W":
                wins += 1
            history.append(dotnet_round(wins / (index + 1), 4))

        place = team["PlaceRegular"]
        team_id = team["TeamID"]
        row: dict[str, Any] = {
            "Place": place,
            "PlaceOrdinal": ordinal(place),
            "TeamID": team_id,
            "Owner": team["Owner"],
            "TeamName": team["Team"],
            "NumberOfGames": regular_season_games,
            "Wins": team["Wins"],
            "Losses": team["Losses"],
            "Ties": team["Ties"],
            "Points": team["Points"],
            "PointsAgainst": team["PointsAgainst"],
            "Record": record,
            "Streak": team["Streak"],
            "WinPercentage": dotnet_round(win_pct, 4),
            "WinPercentageDisplay": format_win_percentage(win_pct),
            "WinPercentageDiffLeagueAvg": dotnet_round(win_pct - avg_win_pct, 2),
            "WinPercentageHistory": history,
            "PointDifference": dotnet_round(team["Points"] - team["PointsAgainst"], 2),
            "PointsPerGame": dotnet_round(points_per_game, 2),
            "PointsPerGameDiffLeagueAvg": dotnet_round(points_diff, 2),
            "PointsAgainstPerGame": dotnet_round(points_against_per_game, 2),
            "PointsAgainstPerGameDiffLeagueAvg": dotnet_round(points_against_diff, 2),
            "LongestWinStreak": longest_win,
            "WinStreakScore": dotnet_round(
                longest_win + team["Wins"] * PARAMS["StreakScoreWinWeight"] + team["Points"] * PARAMS["StreakScorePointWeight"], 4),
            "LongestLossStreak": longest_loss,
            "LossStreakScore": dotnet_round(
                longest_loss + team["Losses"] * PARAMS["StreakScoreWinWeight"] + team["PointsAgainst"] * PARAMS["StreakScorePointWeight"], 4),
            "EfficiencyScore": dotnet_round(efficiency, 4),
            "IronWillScore": dotnet_round(iron_will, 4),
        }
        previous_place = None
        place_delta = None
        if previous_week_places is not None and team_id in previous_week_places:
            previous_place = previous_week_places[team_id]
            place_delta = previous_place - place
        row["PreviousWeekPlace"] = previous_place
        row["PlaceDelta"] = place_delta
        row["WeeklyMovements"] = list((weekly_movements or {}).get(team_id, []))
        rows.append(row)
    return rows


def weekly_tables(
    teams: Sequence[Team],
    weekly_matchups: Sequence[dict[str, Any]] | None,
    completed_weeks: int,
) -> list[dict[str, Any]]:
    """Table after every validated completed week (Get-PreviousWeekRegularSeasonPlaces for each ThroughWeek).

    ``weekly_matchups``: ``{"Week": int, "Entries": [{"TeamID", "MatchupID", "Points"}]}``. The list ends at the
    first week that is missing, incomplete, not exactly two teams per matchup, covers a team twice or whose result
    contradicts the team's Record; later weeks are never inferred. Returns ``[]`` for fewer than one completed week.
    """
    team_list = list(teams)
    if not team_list or completed_weeks < 1:
        return []
    by_week = {int(entry["Week"]): entry for entry in (weekly_matchups or []) if entry is not None}
    state = {t["TeamID"]: {"Wins": 0, "Losses": 0, "Ties": 0, "Points": 0.0, "PointsAgainst": 0.0} for t in team_list}
    record_by_team = {t["TeamID"]: t["Record"] or "" for t in team_list}
    tables: list[dict[str, Any]] = []
    for week in range(1, completed_weeks + 1):
        updated = _apply_week(state, by_week.get(week), record_by_team, week, len(team_list))
        if updated is None:
            break
        state = updated
        ranked = rank_teams([
            {"TeamID": t["TeamID"], **state[t["TeamID"]]} for t in team_list
        ])
        tables.append({
            "Week": week,
            "Teams": [
                {
                    "TeamID": t["TeamID"], "Place": t["PlaceRegular"], "Wins": t["Wins"], "Losses": t["Losses"],
                    "Ties": t["Ties"], "Points": t["Points"], "PointsAgainst": t["PointsAgainst"],
                }
                for t in sorted(ranked, key=lambda r: r["TeamID"])
            ],
        })
    return tables


def _apply_week(
    state: dict[int, dict[str, Any]],
    week_entry: dict[str, Any] | None,
    records: dict[int, str],
    week: int,
    team_count: int,
) -> dict[int, dict[str, Any]] | None:
    if week_entry is None:
        return None
    entries = list(week_entry.get("Entries") or [])
    if len(entries) != team_count:
        return None
    by_matchup: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("Points") is None or entry.get("MatchupID") is None or entry.get("TeamID") not in state:
            return None
        by_matchup.setdefault(str(entry["MatchupID"]), []).append(entry)
    updated = {team_id: dict(values) for team_id, values in state.items()}
    seen: set[int] = set()
    for pair in by_matchup.values():
        if len(pair) != 2:
            return None
        for index in range(2):
            own, opponent = pair[index], pair[1 - index]
            team_id = own["TeamID"]
            if team_id in seen:
                return None
            seen.add(team_id)
            own_points, opponent_points = float(own["Points"]), float(opponent["Points"])
            result = "W" if own_points > opponent_points else "L" if own_points < opponent_points else "T"
            record = records[team_id]
            if len(record) < week or record[week - 1] != result:
                return None
            key = {"W": "Wins", "L": "Losses", "T": "Ties"}[result]
            updated[team_id][key] += 1
            updated[team_id]["Points"] = dotnet_round(updated[team_id]["Points"] + own_points, 2)
            updated[team_id]["PointsAgainst"] = dotnet_round(updated[team_id]["PointsAgainst"] + opponent_points, 2)
    return updated


def weekly_movements(tables: Sequence[dict[str, Any]], team_ids: Iterable[int]) -> dict[int, list[dict[str, int]]]:
    """Get-WeeklyRegularSeasonMovements: Week, Place, PreviousWeekPlace and PlaceDelta from week 2 on."""
    history: dict[int, list[dict[str, int]]] = {team_id: [] for team_id in team_ids}
    previous: dict[int, int] | None = None
    for table in tables:
        places = {entry["TeamID"]: entry["Place"] for entry in table["Teams"]}
        if previous is not None:
            if any(team_id not in places or team_id not in previous for team_id in history):
                return history
            for team_id in history:
                history[team_id].append({
                    "Week": table["Week"],
                    "Place": places[team_id],
                    "PreviousWeekPlace": previous[team_id],
                    "PlaceDelta": previous[team_id] - places[team_id],
                })
        previous = places
    return history


def previous_week_places(tables: Sequence[dict[str, Any]], completed_weeks: int) -> dict[int, int] | None:
    """Places after the week before the last completed week; None without a validated comparison."""
    if completed_weeks < 2:
        return None
    for table in tables:
        if table["Week"] == completed_weeks - 1:
            return {entry["TeamID"]: entry["Place"] for entry in table["Teams"]}
    return None


def _bracket_placements(matches: Sequence[dict[str, Any]] | None, start_place: int) -> dict[str, int]:
    placements: dict[str, int] = {}
    for match in matches or []:
        place, winner, loser = match.get("p"), match.get("w"), match.get("l")
        if place and winner and loser:
            placements[str(start_place + place - 1)] = winner
            placements[str(start_place + place)] = loser
    return placements


def playoff_standings(
    winners_bracket: Sequence[dict[str, Any]] | None,
    losers_bracket: Sequence[dict[str, Any]] | None,
    teams: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Get-PlayoffStandings: placement rows from the winners bracket (start place 1) followed by the losers bracket.

    Bracket matches use the legacy shape (``r, m, t1, t2, w, l, p``). ``teams`` carry TeamID, Owner,
    OwnerAvatarID, Team and TeamAvatar. Empty while the winners bracket has no decided placement match.
    """
    if not winners_bracket:
        return []
    winner_placements = _bracket_placements(winners_bracket, 1)
    if not winner_placements:
        return []
    loser_placements = _bracket_placements(losers_bracket, len(winner_placements) + 1)
    merged = {**winner_placements, **loser_placements}
    by_id = {t["TeamID"]: t for t in teams}
    rows: list[dict[str, Any]] = []
    for key in sorted(merged):
        place = int(key)
        team_id = merged[key]
        info = by_id.get(team_id)
        place_type = "Winner" if place <= len(winner_placements) else "Loser"
        ordinal_text = {1: "1st", 2: "2nd", 3: "3rd"}.get(place, f"{place}th")
        if info is not None:
            rows.append({
                "Place": place, "TeamID": team_id, "Owner": info["Owner"], "OwnerAvatarID": info["OwnerAvatarID"],
                "TeamName": info["Team"], "TeamAvatar": info["TeamAvatar"], "PlaceType": place_type, "PlaceOrdinal": ordinal_text,
            })
        else:
            rows.append({
                "Place": place, "TeamID": team_id, "Owner": "Unknown Owner", "OwnerAvatarID": None,
                "TeamName": f"Unknown Team (ID: {team_id})", "TeamAvatar": None, "PlaceType": place_type, "PlaceOrdinal": ordinal_text,
            })
    return rows


def all_time_standings(seasons_newest_first: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Get-OutputStandingsForAllTime: overall (playoff) and regular-season standing over the given completed seasons.

    ``seasons_newest_first``: season results with ``RegularSeason`` and ``Playoffs`` rows, newest season first
    (the order fixes the owner and team name shown and the Placements array).
    """
    season_count = len(seasons_newest_first)
    regular: dict[int, dict[str, Any]] = {}
    playoffs: dict[int, dict[str, Any]] = {}
    for season in seasons_newest_first:
        for row in season["RegularSeason"]:
            entry = regular.setdefault(row["TeamID"], {
                "Place": 0, "PlaceOrdinal": "none", "TeamID": row["TeamID"], "Owner": row["Owner"], "TeamName": row["TeamName"],
                "Wins": 0, "Losses": 0, "Ties": 0, "WinPercentage": -1, "Points": 0.0, "PointsAgainst": 0.0, "RegularSeasonWins": 0,
            })
            if row["Place"] == 1:
                entry["RegularSeasonWins"] += 1
            entry["Wins"] += row["Wins"]
            entry["Losses"] += row["Losses"]
            entry["Ties"] += row["Ties"]
            entry["Points"] += row["Points"]
            entry["PointsAgainst"] += row["PointsAgainst"]
        for row in season["Playoffs"]:
            entry = playoffs.setdefault(row["TeamID"], {
                "Place": 0, "PlaceOrdinal": "none", "TeamID": row["TeamID"], "Owner": row["Owner"], "TeamName": row["TeamName"],
                "Championships": 0, "RunnerUps": 0, "Thirds": 0, "PlaceCumulative": 0, "PlaceAverage": -1, "Placements": [],
            })
            if row["Place"] == 1:
                entry["Championships"] += 1
            if row["Place"] == 2:
                entry["RunnerUps"] += 1
            if row["Place"] == 3:
                entry["Thirds"] += 1
            entry["PlaceCumulative"] += row["Place"]
            entry["Placements"].append(row["Place"])

    for entry in regular.values():
        entry["WinPercentage"] = dotnet_round(win_percentage(entry), 4)
        entry["Points"] = dotnet_round(entry["Points"], 2)
        entry["PointsAgainst"] = dotnet_round(entry["PointsAgainst"], 2)
    for entry in playoffs.values():
        average = entry["PlaceCumulative"] / season_count if season_count > 0 else -1
        entry["PlaceAverage"] = dotnet_round(average, 2)

    ranked_regular = rank_teams(list(regular.values()), all_time=True)
    regular_by_id = {t["TeamID"]: t for t in ranked_regular}
    missing = 2 ** 31 - 1
    ranked_playoffs = sorted(playoffs.values(), key=lambda t: (
        -t["Championships"], -t["RunnerUps"], -t["Thirds"],
        -(regular_by_id[t["TeamID"]]["RegularSeasonWins"] if t["TeamID"] in regular_by_id else missing),
        t["PlaceAverage"],
        regular_by_id[t["TeamID"]]["Place"] if t["TeamID"] in regular_by_id else missing,
    ))
    playoff_rows = []
    for index, source in enumerate(ranked_playoffs):
        row = dict(source)
        row["Place"] = index + 1
        row["PlaceOrdinal"] = ordinal(index + 1)
        playoff_rows.append(row)
    return {"Playoffs": playoff_rows, "RegularSeason": ranked_regular}
