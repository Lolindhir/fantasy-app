"""Pure assembly of the league-standings product (ADR-072, .ai-context/manual/league-standings.yaml).

Takes the prepared inputs of one league season and the registered models and builds the product document of
that season. No file, clock or league configuration is read here; ``tools/league_standings_sources.py`` reads
the canonical facts and ``tools/derived_data.py`` writes the documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

PRODUCT = "league-standings"
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SeasonInputs:
    """Prepared canonical facts of one league season.

    ``teams``: dicts with TeamID (provider roster ID), CanonicalLeagueRosterID, Owner, OwnerAvatarID, Team (team
    name), TeamAvatar, Points, PointsAgainst, Wins, Losses, Ties, Record and Streak.
    ``winners_bracket`` / ``losers_bracket``: matches in the legacy shape (r, m, t1, t2, w, l, p) with provider roster IDs.
    ``weekly_matchups``: ``{"Week", "Entries": [{"TeamID", "MatchupID", "Points"}]}`` for the regular-season weeks.
    """

    league_id: str
    season: int
    league_status: str
    is_completed: bool
    regular_season_games: int
    league_scored_week: int
    teams: list[dict[str, Any]]
    winners_bracket: list[dict[str, Any]]
    losers_bracket: list[dict[str, Any]]
    weekly_matchups: list[dict[str, Any]]


def build_season(
    inputs: SeasonInputs,
    standings_model: Any,
    awards_model: Any,
    previous: dict[str, Any] | None,
    completed_before: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Product document of one season.

    ``previous``: the document of the previous manifest season (Most Improved) or None. ``completed_before``:
    the documents of all earlier completed seasons, newest first (all-time chain).
    """
    teams = sorted(inputs.teams, key=lambda t: t["TeamID"])
    completed_weeks = min(inputs.league_scored_week, inputs.regular_season_games)
    tables = standings_model.weekly_tables(teams, inputs.weekly_matchups, completed_weeks)
    team_ids = [t["TeamID"] for t in teams]
    rows = standings_model.regular_season_rows(
        teams,
        inputs.regular_season_games,
        standings_model.previous_week_places(tables, completed_weeks),
        standings_model.weekly_movements(tables, team_ids),
    )
    playoffs = standings_model.playoff_standings(inputs.winners_bracket, inputs.losers_bracket, teams)
    awards, annotations = awards_model.compute(rows, playoffs, previous)
    for row in rows:
        row.update(annotations.get(row["TeamID"], {}))

    document: dict[str, Any] = {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": inputs.league_id,
        "Season": inputs.season,
        "Models": {"Standings": standings_model.MODEL_ID, "Awards": awards_model.MODEL_ID},
        "LeagueStatus": inputs.league_status,
        "IsCompleted": inputs.is_completed,
        "RegularSeasonGames": inputs.regular_season_games,
        "AsOf": {"LeagueScoredWeek": inputs.league_scored_week, "CompletedWeeks": completed_weeks},
        "Teams": [
            {
                "TeamID": t["TeamID"], "CanonicalLeagueRosterID": t["CanonicalLeagueRosterID"], "Owner": t["Owner"],
                "OwnerAvatarID": t["OwnerAvatarID"], "TeamName": t["Team"], "TeamAvatar": t["TeamAvatar"],
            }
            for t in teams
        ],
        "RegularSeason": rows,
        "Weeks": tables,
        "Playoffs": playoffs,
        "Awards": awards,
    }
    chain = list(completed_before)
    through = chain[0]["Season"] if chain else None
    if inputs.is_completed:
        chain = [document] + chain
        through = inputs.season
    all_time = standings_model.all_time_standings(chain) if chain else {"Playoffs": [], "RegularSeason": []}
    document["AllTime"] = {"ThroughSeason": through, "Playoffs": all_time["Playoffs"], "RegularSeason": all_time["RegularSeason"]}
    return document
