#!/usr/bin/env python3
"""Refresh current App PlayerWeekFantasy and safely catch up its preceding scored week.

The current week follows FantasyGameContext and feeds the App PWF delivery
model and MatchupProjections. Once the preceding week is *both* canonically league
scored and NFL finalized, rebuild its source-owned Shared-Derived snapshot as
well. This prevents late-arriving final NFL statistics from being frozen as
zero when the App advances to a new week. The preceding-week repair never
publishes an App model or rebuilds older/historical seasons.

A target week with no usable canonical roster is skipped. An inconsistent
finished-week gate or incomplete materialization is fail-closed. Writes use
the existing classified League Live rebuild-and-retry scope.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.week_finality import stats_complete_weeks  # noqa: E402
from matchup_projection import publish_matchup_projections  # noqa: E402
from player_week_fantasy_app_publish import materialize_app_player_week_fantasy  # noqa: E402
from player_week_fantasy_materialize import (  # noqa: E402
    _week_finality,
    build_player_week_fantasy_dataset,
    output_path,
    write_dataset,
)
from data_roots import DATA_SOURCE_ROOT

CONTEXT_PATH = Path("public/data/FantasyGameContext.json")
SLEEPER_PROVIDER = "Sleeper"


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


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _canonical_league_id(repo_root: Path, provider_league_id: str, season: int) -> str:
    matches: list[str] = []
    for path in sorted((repo_root / DATA_SOURCE_ROOT / "leagues").glob(f"*/seasons/{season}/league.json")):
        league = _read_object(path)
        for mapping in league.get("ProviderMappings") or []:
            if (
                isinstance(mapping, dict)
                and mapping.get("Provider") == SLEEPER_PROVIDER
                and str(mapping.get("ProviderLeagueID")) == provider_league_id
            ):
                matches.append(str(league.get("CanonicalLeagueID")))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one canonical league for Sleeper league {provider_league_id} "
            f"in season {season}, found {len(matches)}"
        )
    return matches[0]


def resolve_target(repo_root: Path) -> tuple[str, int, int]:
    context = _read_object(repo_root / CONTEXT_PATH)
    provider_league_id = context.get("LeagueID")
    if not isinstance(provider_league_id, (str, int)) or isinstance(provider_league_id, bool):
        raise ValueError("FantasyGameContext.LeagueID must be a string or integer")
    season = _positive_int(context.get("Season"), "FantasyGameContext.Season")
    week = _positive_int(context.get("Week"), "FantasyGameContext.Week")
    league_id = _canonical_league_id(repo_root, str(provider_league_id), season)
    return league_id, season, week


def weekly_roster_path(repo_root: Path, season: int, week: int) -> Path:
    return repo_root / DATA_SOURCE_ROOT / "nfl" / "weekly-rosters" / str(season) / f"{week:02d}.json"


def refresh_previous_scored_week(
    repo_root: Path, *, league_id: str, season: int, current_week: int,
) -> dict[str, Any] | None:
    """Repair only the immediate previous week, never unscored/live/historical weeks.

    The Sleeper scored-week bound is necessary but not sufficient: independent
    canonical NFL game finality and actual evidence must also be complete.
    Unlike live projections, this strict replay never allows a provisional
    target-week roster.
    """
    if current_week <= 1:
        return None
    league = _read_object(
        repo_root / DATA_SOURCE_ROOT / "leagues" / league_id
        / "seasons" / str(season) / "league.json"
    )
    bounds = league.get("WeekStructure")
    if (league.get("CanonicalLeagueID") != league_id or league.get("Season") != season
            or not isinstance(bounds, dict) or bounds.get("Season") != season
            or type(bounds.get("LastScoredLeg")) is not int):
        raise ValueError("Cannot safely determine canonical league scored-week boundary")
    previous = current_week - 1
    if bounds["LastScoredLeg"] != previous:
        return None

    final, game_ids = _week_finality(repo_root, season=season, week=previous)
    if final is not True or not game_ids:
        raise ValueError(
            f"League-scored week {season}/W{previous} lacks canonical NFL finality"
        )
    if not stats_complete_weeks(repo_root, season, {previous}):
        # Sleeper scores before nflverse stats cover every team (ADR-071): wait instead of
        # publishing final 0 points for the missing teams; a later run finalizes the week.
        return {"Season": season, "Week": previous, "Status": "awaiting-stats-coverage"}
    candidate = build_player_week_fantasy_dataset(
        repo_root, league_id=league_id, season=season, week=previous,
    )
    metadata = candidate.get("Materialization")
    if (not isinstance(metadata, dict)
            or metadata.get("ActualScoringEvidenceFinalized") is not True
            or metadata.get("TargetRosterProvisional") is not False
            or not isinstance(candidate.get("Records"), list)
            or not candidate["Records"]):
        raise ValueError(
            f"Finished-week PWF snapshot is incomplete: {league_id}/{season}/W{previous}"
        )
    changed = write_dataset(
        output_path(repo_root, league_id=league_id, season=season, week=previous),
        candidate,
    )
    return {"Season": season, "Week": previous, "DerivedChanged": changed,
            "RecordCount": len(candidate["Records"])}


def refresh(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    league_id, season, week = resolve_target(root)
    target = {"CanonicalLeagueID": league_id, "Season": season, "Week": week}

    target_roster_exists = weekly_roster_path(root, season, week).is_file()
    previous_roster_exists = week > 1 and weekly_roster_path(root, season, week - 1).is_file()
    if not target_roster_exists and not previous_roster_exists:
        return {**target, "Status": "skipped-weekly-roster-not-synced"}

    # The current App refresh can project one week ahead using last-known NFL
    # membership while NFLverse's new weekly partition is not yet available.
    # This is not enabled for historical/backtest materialization.
    provisional = not target_roster_exists
    build_args = {"league_id": league_id, "season": season, "week": week}
    if provisional:
        build_args["allow_provisional_roster"] = True
    payload = build_player_week_fantasy_dataset(root, **build_args)
    derived_changed = write_dataset(
        output_path(root, league_id=league_id, season=season, week=week), payload
    )
    published, app_changed = materialize_app_player_week_fantasy(root, league_id, season, week)
    matchup_projections = publish_matchup_projections(root)
    previous_scored = refresh_previous_scored_week(
        root, league_id=league_id, season=season, current_week=week,
    )
    return {
        **target,
        "Status": "published",
        "RosterSourceWeek": week - 1 if provisional else week,
        "RosterProvisional": provisional,
        "DerivedChanged": derived_changed,
        "AppChanged": app_changed,
        "RecordCount": len(published["Records"]),
        "MatchupProjections": matchup_projections,
        "FinalizedPreviousWeek": previous_scored,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=TOOLS.parent)
    args = parser.parse_args(argv)
    print(json.dumps(refresh(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
