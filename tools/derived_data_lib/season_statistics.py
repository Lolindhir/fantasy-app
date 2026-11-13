"""Pure assembly of the season-statistics product (Issue #506, .ai-context/manual/season-statistics.yaml).

Reads only canonical facts (league matchups, weekly rosters, league.json), the PlayerWeekFantasy product, the week-finality function
and data-meta; no App file and no clock. The model ``season-stats-v1`` computes the figures from the prepared weekly games; this module
prepares the games (pregame projection per team from team-range, pregame chance from win-prob) and the document.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from league_metadata import data_meta_root, load_league_metadata, model_for

from team_week_performance_sources import WeekSourceNotReady, resolve_slots_from_league
from weekly_lineup_optimizer import ScoredPlayer, maximize_lineup

from .fantasy_game_context import canonical_matchup_facts
from .models.registry import get_model
from .week_finality import resolve_week_finality
from .weekly_recaps import (
    EvidenceGap,
    _load_matchup_rows,
    _pwf_projections,
    _text,
    _weekly_roster_rows,
    roster_identity_map,
)

PRODUCT = "season-statistics"
SCHEMA_VERSION = 1


class SeasonStatisticsError(ValueError):
    """Incomplete or contradicting evidence (fail closed)."""


def projected_best_ball(
    players: list[dict[str, Any]],
    identity_map: dict[str, dict[str, dict[str, str]]] | None,
    projections_by_canonical: dict[str, Any],
    team_range_model: Any,
    slots: list[Any],
) -> tuple[float | None, int]:
    """Best possible lineup of the whole matchup player pool by PlayerWeekFantasy projection and the number of excluded players.

    Slots come from league.json RosterPositions; positions from the canonical weekly roster of the week. A player without a usable
    projection (for example insufficient history) or without a position cannot be valued and is excluded from the pool and counted
    (never guessed); a starter without a value makes the whole result unknown (None). The pool is the canonical matchup player set,
    which includes Taxi and IR players because the provider exposes no weekly Taxi/IR placement.
    """
    if identity_map is None or not slots:
        return None, 0
    candidates: list[ScoredPlayer] = []
    excluded = 0
    for player in players:
        player_id = _text(player["PlayerID"])
        canonical_id = _text(player.get("CanonicalPlayerID")) or _text(identity_map["ByPlayer"].get(player_id, {}).get("CanonicalPlayerID"))
        position = _text(identity_map["ByPlayer"].get(player_id, {}).get("Position")) or _text(identity_map["ByCanonical"].get(canonical_id, {}).get("Position"))
        values = team_range_model.projection_values(projections_by_canonical.get(canonical_id)) if canonical_id else None
        if not position or values is None:
            if player["IsStarter"]:
                return None, 0
            excluded += 1
            continue
        candidates.append(ScoredPlayer(player_id, position.upper(), repr(values[0])))
    return float(maximize_lineup(slots, candidates).points), excluded


def week_games(
    facts: list[dict[str, Any]],
    identity_map: dict[str, dict[str, dict[str, str]]] | None,
    projections_by_canonical: dict[str, Any],
    team_range_model: Any,
    win_prob_model: Any,
    slots: list[Any] | None = None,
    efficiency_actual: dict[str, float] | None = None,
    roster_by_team: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Games of one week with the pregame projection per team and the unrounded pregame chance of the first team.

    Every starter counts with its PlayerWeekFantasy projection (nothing is final); a team with a starter without a usable projection
    (or without a resolvable identity) has no pregame projection and the game no chance (unknown, never 50 percent).
    """
    games: list[dict[str, Any]] = []
    for matchup in facts:
        if len(matchup["Teams"]) != 2:
            continue
        projected: list[dict[str, Any]] = []
        for team in matchup["Teams"]:
            starters: dict[str, dict[str, Any]] = {}
            projections: dict[str, Any] = {}
            for player in team["Players"]:
                if not player["IsStarter"]:
                    continue
                player_id = _text(player["PlayerID"])
                starters[player_id] = {"final": False, "points": None, "bye": False}
                canonical_id = _text(player.get("CanonicalPlayerID"))
                if not canonical_id and identity_map:
                    canonical_id = _text(identity_map["ByPlayer"].get(player_id, {}).get("CanonicalPlayerID"))
                if canonical_id in projections_by_canonical:
                    projections[player_id] = projections_by_canonical[canonical_id]
            projected.append(team_range_model.build_team_projection(team["FantasyTeamID"], starters, projections))
        chance = None
        if all(item["State"] == "available" for item in projected):
            chance = win_prob_model.win_probability(
                projected[0]["ProjectedFinalScore"], projected[0]["StandardDeviation"],
                projected[1]["ProjectedFinalScore"], projected[1]["StandardDeviation"],
            )
        games.append({
            "FantasyMatchupID": matchup["FantasyMatchupID"],
            "Teams": [
                {"TeamID": int(team["FantasyTeamID"]), "Points": float(team["FinalScore"]),
                 "PregameProjection": projected[index]["PregameProjectedScore"],
                 **dict(zip(("ProjectedBestBallPoints", "BestBallExcludedPlayers"),
                            projected_best_ball(team["Players"], identity_map, projections_by_canonical, team_range_model, slots or []))),
                 "LineupEfficiencyActual": (efficiency_actual or {}).get((roster_by_team or {}).get(int(team["FantasyTeamID"]), ""))}
                for index, team in enumerate(matchup["Teams"])
            ],
            "WinProbability": chance,
        })
    return games


def _efficiency_actual(repo_root: Path, league_id: str, season: int, week: int) -> dict[str, float]:
    """EfficiencyPercent per CanonicalLeagueRosterID from the TeamWeekPerformance partition (taken over, not recomputed); empty when absent."""
    path = repo_root / DATA_DERIVED_ROOT / "team-week-performance" / league_id / str(season) / f"{week:02d}.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    return {
        team["CanonicalLeagueRosterID"]: float(team["EfficiencyPercent"])
        for team in document.get("Teams", [])
        if isinstance(team.get("EfficiencyPercent"), (int, float))
    }


def _lineup_slots(season_dir: Path, identity_map: dict[str, dict[str, dict[str, str]]] | None) -> list[Any]:
    if identity_map is None:
        return []
    league = json.loads((season_dir / "league.json").read_text(encoding="utf-8"))
    positions = {key: value["Position"] for key, value in identity_map["ByPlayer"].items() if value.get("Position")}
    try:
        return resolve_slots_from_league(league["RosterPositions"], positions)
    except (WeekSourceNotReady, KeyError):
        return []


def build_weeks(
    repo_root: Path, league_id: str, season: int, last_week: int, team_range_model: Any, win_prob_model: Any,
    roster_by_team: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Regular-season weeks 1..last_week as an uninterrupted run; the run ends at the first week without usable matchup facts."""
    season_dir = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    weeks: list[dict[str, Any]] = []
    for week in range(1, last_week + 1):
        rows = _load_matchup_rows(season_dir, week)
        if not rows:
            break
        facts = canonical_matchup_facts(str(season), week, rows)
        if not facts or any(len(m["Teams"]) != 2 for m in facts):
            break
        try:
            identity_map = roster_identity_map(_weekly_roster_rows(repo_root, season, week))
        except EvidenceGap:
            identity_map = None
        projections = _pwf_projections(repo_root, league_id, season, week) if identity_map is not None else {}
        weeks.append({"Week": week, "Games": week_games(
            facts, identity_map, projections, team_range_model, win_prob_model,
            _lineup_slots(season_dir, identity_map), _efficiency_actual(repo_root, league_id, season, week), roster_by_team,
        )})
    return weeks


def resolve(repo_root: Path, league_id: str, season: int, teams: list[dict[str, Any]], regular_season_games: int, is_completed: bool) -> dict[str, Any]:
    """The product document of one season; ``teams`` are the dicts of league_standings_sources.build_teams."""
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    model = get_model(model_for(metadata, season, "SeasonStats"), "season-stats")
    team_range_model = get_model(model_for(metadata, season, "TeamRange"), "team-range")
    win_prob_model = get_model(model_for(metadata, season, "WinProb"), "win-prob")
    finality = resolve_week_finality(repo_root, league_id, season)
    scored = int(finality["LeagueScoredWeek"])
    last = min(scored, regular_season_games)
    ordered = sorted(teams, key=lambda t: t["TeamID"])
    roster_by_team = {t["TeamID"]: t["CanonicalLeagueRosterID"] for t in ordered}
    weeks = build_weeks(repo_root, league_id, season, last, team_range_model, win_prob_model, roster_by_team) if last > 0 else []
    team_ids = [t["TeamID"] for t in ordered]
    for week in weeks:
        seen = sorted(team["TeamID"] for game in week["Games"] for team in game["Teams"])
        if seen != team_ids:
            raise SeasonStatisticsError(f"Week {week['Week']} of {league_id}/{season} does not cover every team exactly once: {seen}")
    result = model.compute(team_ids, weeks)
    identity = {t["TeamID"]: t for t in ordered}
    stats_teams = [
        {
            "TeamID": item["TeamID"], "CanonicalLeagueRosterID": identity[item["TeamID"]]["CanonicalLeagueRosterID"],
            "Owner": identity[item["TeamID"]]["Owner"], "TeamName": identity[item["TeamID"]]["Team"],
            **{key: value for key, value in item.items() if key != "TeamID"},
        }
        for item in result["Teams"]
    ]
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "Models": {"SeasonStats": model.MODEL_ID, "TeamRange": team_range_model.MODEL_ID, "WinProb": win_prob_model.MODEL_ID},
        "Thresholds": {"UnderdogWinProbability": model.UNDERDOG_THRESHOLD, "UpsetWinProbability": model.UPSET_THRESHOLD},
        "IsCompleted": is_completed,
        "RegularSeasonGames": regular_season_games,
        "AsOf": {"LeagueScoredWeek": scored, "CompletedWeeks": weeks[-1]["Week"] if weeks else 0},
        "Teams": stats_teams,
        "Weeks": result["Weeks"],
        "BiggestUpset": result["BiggestUpset"],
    }
