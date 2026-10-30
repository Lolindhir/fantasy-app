#!/usr/bin/env python3
"""Consumer generator: App WeeklyRecaps files from the weekly-recaps function (ADR-063, Issue #1199 section 4).

Renders exactly the files the App reads from the computed recap model (tools/derived_data_lib/weekly_recaps.py);
nothing is read from public/data:

  public/data/WeeklyRecaps.json                                        current season
  public/data/past_seasons/WeeklyRecaps/WeeklyRecaps_<season>.json     completed earlier seasons

Usage:
  weekly_recaps_app_publish.py write [--league ID] [--scope current|history|all] [--fail-on-error]

`write` writes a file only on a semantic difference and updates Timestamps.json[WeeklyRecaps] for the current file only.
Without --league every league of data-meta is processed; the App files carry no league dimension, so more than one
league fails closed until the App delivery gains one. A season whose canonical evidence contradicts itself keeps its last
file and raises a GitHub warning annotation; the current season fails the run with --fail-on-error.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.weekly_recaps import WeeklyRecapsError, resolve_weekly_recaps  # noqa: E402
from league_metadata import list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest  # noqa: E402
from matchup_context_app_publish import Writer, _warn, history_matchup_seasons  # noqa: E402

EXPECTED_ERRORS = (WeeklyRecapsError, LifecycleError, StandingsSourceError)


def write_current(repo_root: Path, league_id: str, writer: Writer) -> None:
    season = current_season(manifest(repo_root, league_id))
    writer.put("WeeklyRecaps.json", resolve_weekly_recaps(repo_root, league_id, season), "WeeklyRecaps")


def write_history(repo_root: Path, league_id: str, writer: Writer) -> None:
    current = current_season(manifest(repo_root, league_id))
    for season in history_matchup_seasons(repo_root, league_id, current):
        try:
            model = resolve_weekly_recaps(repo_root, league_id, season)
        except EXPECTED_ERRORS as error:
            _warn(f"Historical WeeklyRecaps {season} not published", f"{type(error).__name__}: {error}")
            continue
        writer.put(f"past_seasons/WeeklyRecaps/WeeklyRecaps_{season}.json", model)


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
