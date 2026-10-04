#!/usr/bin/env python3
"""Refresh the App PlayerWeekFantasy publication for the current App week.

The target league/season/week is read from the published FantasyGameContext, so
the PlayerWeekFantasy snapshot always matches the week the Angular consumer
joins against. The step materializes the Shared-Derived snapshot and then
publishes the App delivery adapter; both writes are deterministic no-ops when
nothing changed.

A target week whose canonical weekly-roster partition is not synced yet is
skipped without touching the existing publication. Every other failure is
fail-closed.
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

from player_week_fantasy_app_publish import materialize_app_player_week_fantasy  # noqa: E402
from player_week_fantasy_materialize import (  # noqa: E402
    build_player_week_fantasy_dataset,
    output_path,
    write_dataset,
)

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
    for path in sorted((repo_root / "source-data" / "leagues").glob(f"*/seasons/{season}/league.json")):
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
    return repo_root / "source-data" / "nfl" / "weekly-rosters" / str(season) / f"{week:02d}.json"


def refresh(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    league_id, season, week = resolve_target(root)
    target = {"CanonicalLeagueID": league_id, "Season": season, "Week": week}

    if not weekly_roster_path(root, season, week).is_file():
        return {**target, "Status": "skipped-weekly-roster-not-synced"}

    payload = build_player_week_fantasy_dataset(
        root, league_id=league_id, season=season, week=week
    )
    derived_changed = write_dataset(
        output_path(root, league_id=league_id, season=season, week=week), payload
    )
    published, app_changed = materialize_app_player_week_fantasy(root, league_id, season, week)
    return {
        **target,
        "Status": "published",
        "DerivedChanged": derived_changed,
        "AppChanged": app_changed,
        "RecordCount": len(published["Records"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=TOOLS.parent)
    args = parser.parse_args(argv)
    print(json.dumps(refresh(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
