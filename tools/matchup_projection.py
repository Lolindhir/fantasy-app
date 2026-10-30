#!/usr/bin/env python3
"""Publish team-level matchup projections and ranges into the App delivery layer.

Inputs are the computed FantasyGameContext (matchup-context function, ADR-075: current starters, game status, final points),
the App adaptation of the Shared Derived PlayerWeekFantasy product (player projections and ranges) and the shared Decision
Windows function (scoring availability per player, ADR-074). Nothing is read from public/data. The projection method is the
team-range model chosen per season in data-meta (team-range-v1, tools/derived_data_lib/models/team_range); this module only
collects the starters, joins the projections and writes MatchupProjections.json. No arithmetic belongs in the frontend.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Mapping

from derived_data_lib.decision_windows import DecisionWindowsError, resolve as resolve_decision_windows
from derived_data_lib.league_lifecycle import LifecycleError
from league_metadata import LeagueMetadataError, data_meta_root, load_league_metadata, model_for
from derived_data_lib.models.registry import get_model
from derived_data_lib.models.team_range import v1 as team_range_v1
from derived_data_lib.models.team_range.v1 import (  # noqa: F401  (re-exported, the method lives in the model)
    AVAILABILITY_OUT,
    AVAILABILITY_UNCERTAIN,
    METHOD_ID,
    SIGMA_BASIS_LEVEL,
    build_team_projection,
    player_sigma,
    projection_values as _projection_values,
    team_ranges,
    z_for_level,
)
from player_week_fantasy import DISPLAY_INTERVAL_LEVEL, PUBLISHED_INTERVAL_LEVELS

SCHEMA_VERSION = 2
AXIS_STEP = 20
AXIS_PADDING = 10
OUTPUT_PATH = Path("public/data/MatchupProjections.json")


def _is_final(status: Any) -> bool:
    return isinstance(status, str) and re.match(r"^Final", status, re.IGNORECASE) is not None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _team_key(matchup_id: Any, team_id: Any) -> tuple[str, str]:
    return str(matchup_id), str(team_id)


def _player_index(player_model: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in player_model.get("Records", []):
        player_id = record.get("PlayerID")
        if player_id is None or str(player_id).strip() == "":
            continue
        key = str(player_id)
        if key in index:
            raise ValueError(f"Duplicate App PlayerID in PlayerWeekFantasy: {key}")
        index[key] = record["Projection"]
    return index


def _collect_starters(context: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    starters: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for game in context.get("Games", []):
        final = _is_final(game.get("Status"))
        for team in game.get("FantasyTeams", []):
            key = _team_key(team.get("FantasyMatchupID"), team.get("FantasyTeamID"))
            for player in team.get("Players", []):
                if not player.get("IsStarter"):
                    continue
                starters[key][str(player["PlayerID"])] = {
                    "final": final,
                    "points": _finite(player.get("Points")),
                    "bye": False,
                }
    for association in context.get("NonGameAssociations", []):
        if not association.get("IsStarter") or not association.get("FantasyMatchupID"):
            continue
        key = _team_key(association["FantasyMatchupID"], association["FantasyTeamID"])
        starters[key].setdefault(
            str(association["PlayerID"]),
            {"final": False, "points": None, "bye": association.get("Kind") == "bye"},
        )
    return starters


def _axis(teams: list[dict[str, Any]], level: float) -> dict[str, int] | None:
    bounds = [
        item
        for team in teams
        for item in team["Ranges"]
        if item["Level"] == level
    ]
    if len(bounds) != len(teams) or not bounds:
        return None
    return {
        "Min": math.floor((min(item["Lower"] for item in bounds) - AXIS_PADDING) / AXIS_STEP) * AXIS_STEP,
        "Max": math.ceil((max(item["Upper"] for item in bounds) + AXIS_PADDING) / AXIS_STEP) * AXIS_STEP,
        "Step": AXIS_STEP,
    }


def build_matchup_projections(
    context: Mapping[str, Any],
    player_model: Mapping[str, Any],
    *,
    display_level: float = DISPLAY_INTERVAL_LEVEL,
    availability: Mapping[str, str] | None = None,
    model: Any = team_range_v1,
) -> dict[str, Any]:
    """Pure builder. Raises ValueError when the two inputs do not describe the same week."""

    if str(context.get("Season")) != str(player_model.get("Season")) or int(context["Week"]) != int(
        player_model["Week"]
    ):
        raise ValueError(
            "FantasyGameContext and PlayerWeekFantasy target different weeks: "
            f"context={context.get('Season')}/W{context.get('Week')} "
            f"players={player_model.get('Season')}/W{player_model.get('Week')}"
        )
    if display_level not in PUBLISHED_INTERVAL_LEVELS:
        raise ValueError(f"Display level {display_level} is not a published interval level")

    projections = _player_index(player_model)
    starters_by_team = _collect_starters(context)

    matchups: list[dict[str, Any]] = []
    for matchup in context.get("FantasyMatchups", []):
        teams = [
            model.build_team_projection(
                team_id,
                starters_by_team.get(_team_key(matchup["FantasyMatchupID"], team_id), {}),
                projections,
                availability,
            )
            for team_id in matchup["TeamIDs"]
        ]
        matchups.append(
            {
                "FantasyMatchupID": matchup["FantasyMatchupID"],
                "Teams": teams,
                "Axis": _axis(teams, display_level),
            }
        )

    return {
        "SchemaVersion": SCHEMA_VERSION,
        "CanonicalLeagueID": player_model.get("CanonicalLeagueID"),
        "Season": player_model["Season"],
        "Week": player_model["Week"],
        "DisplayLevel": display_level,
        "Method": dict(model.METHOD),
        "Matchups": matchups,
    }


def write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _decision_windows(root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any] | None:
    """Current Decision Windows from the shared function (ADR-074); None when it cannot be computed.

    The function is computed at ``at_utc`` and nothing is read from public/data. A failure keeps the projections without
    availability and is reported on stderr.
    """

    try:
        return resolve_decision_windows(root, league_id, season, at_utc)
    except (DecisionWindowsError, LifecycleError, LeagueMetadataError, KeyError, ValueError, OSError) as exc:
        print(f"matchup_projection: Decision Windows unavailable, availability ignored: {exc}", file=sys.stderr)
        return None


def _availability_by_player(root: Path, league_id: str, context: Mapping[str, Any], at_utc: datetime) -> dict[str, str]:
    """Scoring availability per App PlayerID; empty when unavailable or the function targets another week."""

    windows = _decision_windows(root, league_id, int(context["Season"]), at_utc)
    if windows is None:
        return {}
    if str(windows.get("Season")) != str(context.get("Season")) or str(windows.get("LineupWeek")) != str(
        context.get("Week")
    ):
        return {}
    return {
        str(item["PlayerID"]): item["State"]
        for item in windows.get("ScoringAvailabilityObservations") or []
        if item.get("PlayerID") is not None and isinstance(item.get("State"), str)
    }


def publish_matchup_projections(
    repo_root: Path,
    context: Mapping[str, Any],
    player_model: Mapping[str, Any],
    *,
    league_id: str,
    at_utc: datetime,
) -> dict[str, Any]:
    """Build from the FantasyGameContext function result and the PlayerWeekFantasy App model and write on change.

    Neither input is read from public/data: the context is the computed matchup-context result (ADR-075) and the player model is
    the in-memory App adaptation of the Shared Derived PlayerWeekFantasy product. The method is the team-range model chosen
    for the season in data-meta (Models.TeamRange). A context/player-model week mismatch skips publication and keeps the
    existing file: the consumer ignores a snapshot that targets another week.
    """

    root = repo_root.resolve()
    season = int(context["Season"])
    model = get_model(model_for(load_league_metadata(league_id, data_meta_root(root)), season, "TeamRange"), "team-range")
    try:
        payload = build_matchup_projections(
            context, player_model, availability=_availability_by_player(root, league_id, context, at_utc), model=model
        )
    except ValueError as exc:
        if "target different weeks" in str(exc):
            return {"Status": "skipped-week-mismatch", "Detail": str(exc)}
        raise
    changed = write_json_if_changed(root / OUTPUT_PATH, payload)
    teams = [team for matchup in payload["Matchups"] for team in matchup["Teams"]]
    return {
        "Status": "published",
        "Changed": changed,
        "Season": payload["Season"],
        "Week": payload["Week"],
        "MatchupCount": len(payload["Matchups"]),
        "AvailableTeamCount": sum(1 for team in teams if team["State"] == "available"),
        "TeamCount": len(teams),
    }
