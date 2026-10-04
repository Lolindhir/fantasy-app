#!/usr/bin/env python3
"""Publish team-level matchup projections and ranges into the App delivery layer.

Inputs are the App read models FantasyGameContext.json (current starters, game
status, points so far) and PlayerWeekFantasy.json (published player projections
and ranges). The team projection is a sum; the team range is a normal
approximation that adds player variances (independent players), calibrated by
tools/historical_team_range_backtest.py. No arithmetic belongs in the frontend.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist
from typing import Any, Mapping

from player_week_fantasy import DISPLAY_INTERVAL_LEVEL, PUBLISHED_INTERVAL_LEVELS

SCHEMA_VERSION = 1
METHOD_ID = "normal-independent-v1"
SIGMA_BASIS_LEVEL = 0.9
AXIS_STEP = 20
AXIS_PADDING = 10
OUTPUT_PATH = Path("public/data/MatchupProjections.json")
CONTEXT_PATH = Path("public/data/FantasyGameContext.json")
PLAYER_PATH = Path("public/data/PlayerWeekFantasy.json")


def z_for_level(level: float) -> float:
    """Two-sided normal quantile for a central interval of the given level."""

    return NormalDist().inv_cdf(0.5 + level / 2.0)


def player_sigma(lower: float, upper: float) -> float:
    """Standard deviation implied by a player's SIGMA_BASIS_LEVEL interval."""

    return (upper - lower) / (2.0 * z_for_level(SIGMA_BASIS_LEVEL))


def team_ranges(
    mean: float,
    variance: float,
    levels: tuple[float, ...] = PUBLISHED_INTERVAL_LEVELS,
) -> list[dict[str, float]]:
    """Central ranges around the team mean; variances of independent starters add."""

    sd = math.sqrt(variance)
    return [
        {
            "Level": level,
            "Lower": round(mean - z_for_level(level) * sd, 4),
            "Upper": round(mean + z_for_level(level) * sd, 4),
        }
        for level in levels
    ]


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


def _projection_values(projection: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """(points, sigma) when the projection is usable, else None."""

    if not projection or projection.get("Status") != "available":
        return None
    points = _finite(projection.get("Points"))
    if points is None:
        return None
    ranges = projection.get("PredictionRanges") or (
        [projection["PredictionRange"]] if projection.get("PredictionRange") else []
    )
    basis = next((item for item in ranges if item.get("Level") == SIGMA_BASIS_LEVEL), None)
    if basis is None:
        return None
    lower, upper = _finite(basis.get("Lower")), _finite(basis.get("Upper"))
    if lower is None or upper is None or upper < lower:
        return None
    return points, player_sigma(lower, upper)


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


def build_team_projection(
    team_id: Any,
    starters: Mapping[str, Mapping[str, Any]],
    projections: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    scored = 0.0
    mean = 0.0
    variance = 0.0
    pregame = 0.0
    pregame_complete = bool(starters)
    final_count = 0
    resolved = 0
    byes: list[str] = []
    unavailable: list[str] = []

    for player_id in sorted(starters):
        starter = starters[player_id]
        values = _projection_values(projections.get(player_id))

        if starter["bye"]:
            byes.append(player_id)
            resolved += 1
            continue

        if values is None:
            pregame_complete = False
        else:
            pregame += values[0]

        if starter["final"]:
            if starter["points"] is None:
                unavailable.append(player_id)
                continue
            scored += starter["points"]
            mean += starter["points"]
            final_count += 1
            resolved += 1
        elif values is None:
            unavailable.append(player_id)
        else:
            points, sigma = values
            # A game that is not final counts its projection but never less than the points
            # already scored, so live scoring is not counted twice. Interim rule until the
            # live remaining-points model exists.
            mean += max(starter["points"] or 0.0, points)
            variance += sigma * sigma
            resolved += 1

    starter_count = len(starters)
    complete = starter_count > 0 and resolved == starter_count
    state = "available" if complete else ("partial" if resolved > 0 else "unavailable")

    return {
        "FantasyTeamID": team_id,
        "State": state,
        "StarterCount": starter_count,
        "ResolvedStarterCount": resolved,
        "FinalStarterCount": final_count,
        "ScoredPoints": round(scored, 4),
        "PregameProjectedScore": round(pregame, 4) if pregame_complete else None,
        "ProjectedFinalScore": round(mean, 4) if complete else None,
        "StandardDeviation": round(math.sqrt(variance), 4) if complete else None,
        "Ranges": team_ranges(mean, variance) if complete else [],
        "ByeStarterPlayerIDs": byes,
        "UnavailableStarterPlayerIDs": unavailable,
    }


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
            build_team_projection(
                team_id,
                starters_by_team.get(_team_key(matchup["FantasyMatchupID"], team_id), {}),
                projections,
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
        "Method": {
            "Id": METHOD_ID,
            "Levels": list(PUBLISHED_INTERVAL_LEVELS),
            "SigmaBasisLevel": SIGMA_BASIS_LEVEL,
            "Assumption": "starters score independently; player variances add",
            "ParticipationCondition": "conditional-on-participation",
        },
        "Matchups": matchups,
    }


def write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Required input is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Input is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Input must be a JSON object: {path}")
    return payload


def publish_matchup_projections(repo_root: Path) -> dict[str, Any]:
    """Build from the published App read models and write when the content changed.

    A context/player-model week mismatch skips publication and keeps the existing file:
    the consumer ignores a snapshot that targets another week.
    """

    root = repo_root.resolve()
    context = _read_object(root / CONTEXT_PATH)
    player_model = _read_object(root / PLAYER_PATH)
    try:
        payload = build_matchup_projections(context, player_model)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    print(json.dumps(publish_matchup_projections(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
