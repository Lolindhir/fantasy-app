#!/usr/bin/env python3
"""Consumer generator: App WeeklyRecaps files from the weekly-recaps product (ADR-063, ADR-089).

Renders exactly the files the App reads from the persisted documents of data-derived/weekly-recaps (materialized by
tools/weekly_recaps_materialize.py from tools/derived_data_lib/weekly_recaps.py); nothing is read from public/data:

  public/data/WeeklyRecaps.json                                        current season
  public/data/past_seasons/WeeklyRecaps/WeeklyRecaps_<season>.json     completed earlier seasons
  public/data/PlayerAwardHistory.json                                  weekly player award counts and week lists across seasons (Issue #499)

Usage:
  weekly_recaps_app_publish.py write [--league ID] [--scope current|history|all] [--fail-on-error]

PlayerAwardHistory.json is rendered from the persisted season models of every season (L3: no published archive is an input). `write` writes a file only on a semantic difference and updates Timestamps.json[WeeklyRecaps] for the current file only.
Without --league every league of data-meta is processed; the App files carry no league dimension, so more than one
league fails closed until the App delivery gains one. A season whose canonical evidence contradicts itself keeps its last
file and raises a GitHub warning annotation; the current season fails the run with --fail-on-error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from data_roots import data_derived_dir  # noqa: E402
from derived_data_lib.weekly_recaps import WeeklyRecapsError, player_award_history  # noqa: E402
from league_metadata import list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest, manifest_seasons  # noqa: E402
from matchup_context_app_publish import Writer, _warn, history_matchup_seasons  # noqa: E402
from weekly_recaps_materialize import read_model  # noqa: E402

EXPECTED_ERRORS = (WeeklyRecapsError, LifecycleError, StandingsSourceError)


def _model(repo_root: Path, league_id: str, season: int) -> dict:
    model = read_model(data_derived_dir(repo_root), league_id, season)
    if model is None:
        raise WeeklyRecapsError(f"weekly-recaps product {season} is not materialized")
    return model


def write_current(repo_root: Path, league_id: str, writer: Writer) -> dict[int, dict]:
    season = current_season(manifest(repo_root, league_id))
    model = _model(repo_root, league_id, season)
    writer.put("WeeklyRecaps.json", model, "WeeklyRecaps")
    return {season: model}


def write_history(repo_root: Path, league_id: str, writer: Writer) -> dict[int, dict]:
    current = current_season(manifest(repo_root, league_id))
    models: dict[int, dict] = {}
    for season in history_matchup_seasons(repo_root, league_id, current):
        try:
            model = _model(repo_root, league_id, season)
        except EXPECTED_ERRORS as error:
            _warn(f"Historical WeeklyRecaps {season} not published", f"{type(error).__name__}: {error}")
            continue
        writer.put(f"past_seasons/WeeklyRecaps/WeeklyRecaps_{season}.json", model)
        models[season] = model
    return models


def product_models(repo_root: Path, league_id: str) -> dict[int, dict]:
    """The persisted season models of every season with a product document (L3: no App archive is read)."""
    models: dict[int, dict] = {}
    for season in manifest_seasons(manifest(repo_root, league_id)):
        model = read_model(data_derived_dir(repo_root), league_id, season)
        if model is not None:
            models[season] = model
    return models


def write_award_history(repo_root: Path, league_id: str, writer: Writer) -> None:
    """PlayerAwardHistory.json from the persisted season models; nothing is written while no season carries player awards."""
    from derived_data_lib.league_player_refs import LeaguePlayerReferenceResolver

    models = product_models(repo_root, league_id)
    if not any("PlayerAwards" in week for model in models.values() for week in model.get("Weeks", [])):
        return
    resolver = LeaguePlayerReferenceResolver.from_repo(repo_root)
    document = player_award_history(models, lambda player_id, season: resolver.resolve(player_id, season))
    writer.put("PlayerAwardHistory.json", document, "PlayerAwardHistory")


def leagues(repo_root: Path, requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise WeeklyRecapsError(f"the App WeeklyRecaps files carry no league dimension; expected exactly one league, found {ids}")
    return ids


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="write the App files from the recap function (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--scope", choices=("current", "history", "all"), default="current")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the current season cannot be built")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        for league_id in leagues(args.repo_root, args.league):
            if args.scope in ("current", "all"):
                write_current(args.repo_root, league_id, writer)
            if args.scope in ("history", "all"):
                write_history(args.repo_root, league_id, writer)
            write_award_history(args.repo_root, league_id, writer)
    except EXPECTED_ERRORS as error:
        _warn("WeeklyRecaps not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
