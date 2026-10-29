"""Shared "week final" definition for every consumer (ADR-071, Issue #897).

A league week is judged by three independent pieces of evidence:

* ``NflGamesFinal``    canonical NFL game finality: REG ``WeekFinal`` with complete final-game evidence.
* ``NflStatsComplete`` the canonical player-stats partition exists and covers every team playing that week.
* ``LeagueScored``     the week is at or before the league provider's ``WeekStructure.LastScoredLeg``.

Two milestones are derived from them, each the last week of an uninterrupted run starting at
``WeekStructure.StartWeek`` and capped at the last league week (0 when no week qualifies):

* ``LeagueScoredWeek`` = NflGamesFinal and LeagueScored (League, Standings, TeamWeekPerformance).
* ``StatsFinalWeek``   = NflGamesFinal and NflStatsComplete (PlayerWeekFantasy Actual, Players, PlayerValuation).

Pure function of canonical source facts, nothing is persisted. Missing current-season partitions mean
"not final yet"; contradicting evidence fails closed. Contract: ``week-finality.yaml``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT

NFL_REGULAR_SEASON_MAX_WEEK = 18
EVIDENCE = ("NflGamesFinal", "NflStatsComplete", "LeagueScored")


class WeekFinalityError(ValueError):
    """Contradicting or unusable evidence (fail closed)."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _positive(structure: dict, name: str, path: Path) -> int | None:
    value = structure.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise WeekFinalityError(f"WeekStructure.{name} must be a positive integer in {path}")
    return value


def _structure(repo_root: Path, league_id: str, season: int) -> dict[str, int]:
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json"
    if not path.is_file():
        raise WeekFinalityError(f"Canonical league source missing: {path}")
    structure = _read(path).get("WeekStructure")
    if not isinstance(structure, dict):
        raise WeekFinalityError(f"No WeekStructure in {path}")
    last_week = _positive(structure, "ExpectedLastLeagueWeek", path) or _positive(structure, "FinalLeagueWeek", path)
    if last_week is None:
        raise WeekFinalityError(f"WeekStructure in {path} cannot resolve a last league week")
    if last_week > NFL_REGULAR_SEASON_MAX_WEEK:
        raise WeekFinalityError(f"League week {last_week} exceeds NFL regular season week mapping in {path}")
    start = _positive(structure, "StartWeek", path) or 1
    scored = structure.get("LastScoredLeg")
    if scored is None:
        scored = 0
    if isinstance(scored, bool) or not isinstance(scored, int) or scored < 0:
        raise WeekFinalityError(f"WeekStructure.LastScoredLeg must be a non-negative integer in {path}")
    if scored > last_week:
        raise WeekFinalityError(f"LastScoredLeg {scored} exceeds last league week {last_week} in {path}")
    return {
        "StartWeek": start,
        "LastLeagueWeek": last_week,
        "PlayoffStartWeek": _positive(structure, "PlayoffStartWeek", path),
        "LastScoredLeg": scored,
    }


def _games_final_rows(path: Path, season: int) -> tuple[dict[int, bool], bool]:
    """REG WeekFinal per week with the final-game consistency check, plus the payload's Finalized flag."""
    payload = _read(path)
    result: dict[int, bool] = {}
    for row in payload.get("Weeks") or []:
        if str(row.get("GameType") or "REG").upper() != "REG":
            continue
        week = int(row["Week"])
        final = row.get("WeekFinal")
        if not isinstance(final, bool):
            raise WeekFinalityError(f"WeekFinal is not a boolean for {season}/W{week}: {path}")
        if final:
            applicable, done = row.get("ApplicableGameCount"), row.get("FinalGameCount")
            if not isinstance(applicable, int) or applicable <= 0 or done != applicable:
                raise WeekFinalityError(f"WeekFinal=true without complete final-game evidence for {season}/W{week}")
        result[week] = final
    return result, payload.get("Finalized") is True


def _games_final(repo_root: Path, season: int, weeks: range, league_complete: bool) -> dict[int, bool]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl/game-finality" / f"{season}.json"
    if not path.is_file():
        if league_complete:
            raise WeekFinalityError(f"Game finality missing for completed season: {path}")
        return {week: False for week in weeks}
    rows, finalized = _games_final_rows(path, season)
    result: dict[int, bool] = {}
    for week in weeks:
        if week not in rows and (league_complete or finalized):
            raise WeekFinalityError(f"No REG game-finality row for {season}/W{week}: {path}")
        result[week] = rows.get(week, False)
    return result


def games_final_weeks(repo_root: Path, season: int) -> set[int]:
    """Regular-season weeks whose NFL games are all final (NflGamesFinal alone, any season)."""
    path = repo_root / DATA_SOURCE_ROOT / "nfl/game-finality" / f"{season}.json"
    if not path.is_file():
        raise WeekFinalityError(f"Game finality missing: {path}")
    return {week for week, final in _games_final_rows(path, season)[0].items() if final}


def _playing_teams(repo_root: Path, season: int) -> dict[int, set[str]] | None:
    schedule_path = repo_root / DATA_SOURCE_ROOT / "nfl/schedules" / f"{season}.json"
    if not schedule_path.is_file():
        return None
    playing: dict[int, set[str]] = {}
    for game in _read(schedule_path)["Games"]:
        if game.get("GameType", "REG") != "REG":
            continue
        teams = playing.setdefault(int(game["Week"]), set())
        teams.update(team for team in (game.get("HomeTeam"), game.get("AwayTeam")) if team)
    return playing


def _stats_complete(repo_root: Path, season: int, week: int, playing: dict[int, set[str]] | None) -> bool:
    stats_path = repo_root / DATA_SOURCE_ROOT / "nfl/player-stats" / str(season) / f"{week:02d}.json"
    if playing is None or not stats_path.is_file():
        return False
    covered = {
        record.get("Team")
        for record in _read(stats_path)["Records"]
        if record.get("SeasonType", "REG") == "REG"
    }
    return bool(playing.get(week)) and playing[week] <= covered


def stats_complete_weeks(repo_root: Path, season: int, weeks: set[int] | range) -> set[int]:
    """Weeks (of the given ones) whose player-stats partition covers every playing team (NflStatsComplete)."""
    playing = _playing_teams(repo_root, season)
    return {week for week in weeks if _stats_complete(repo_root, season, week, playing)}


def _milestone(weeks: list[dict[str, Any]], *needed: str) -> int:
    reached = 0
    for row in weeks:
        if not all(row[name] for name in needed):
            break
        reached = row["Week"]
    return reached


def resolve_week_finality(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    """Evidence per league week plus the LeagueScoredWeek and StatsFinalWeek milestones."""
    structure = _structure(repo_root, league_id, season)
    first, last = structure["StartWeek"], structure["LastLeagueWeek"]
    weeks_range = range(first, last + 1)
    games = _games_final(repo_root, season, weeks_range, structure["LastScoredLeg"] >= last)
    playing = _playing_teams(repo_root, season)
    weeks: list[dict[str, Any]] = []
    for week in weeks_range:
        row = {
            "Week": week,
            "NflGamesFinal": games[week],
            "NflStatsComplete": _stats_complete(repo_root, season, week, playing),
            "LeagueScored": week <= structure["LastScoredLeg"],
        }
        row["Pending"] = [name for name in EVIDENCE if not row[name]]
        weeks.append(row)
    return {
        "CanonicalLeagueID": league_id,
        "Season": season,
        **structure,
        "LeagueScoredWeek": _milestone(weeks, "NflGamesFinal", "LeagueScored"),
        "StatsFinalWeek": _milestone(weeks, "NflGamesFinal", "NflStatsComplete"),
        "Weeks": weeks,
    }
