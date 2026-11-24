#!/usr/bin/env python3
"""Consumer generator: App Matchups, FantasyGameContext and MatchupProjections files from the matchup-context product (ADR-075, ADR-089).

Renders exactly the files the App reads from the persisted documents of data-derived/matchup-context (materialized by
tools/matchup_context_materialize.py, which calls the pure function tools/derived_data_lib/matchup_context.py); nothing is
read from public/data and no computation happens here:

  public/data/Matchups.json                                   season Matchups model of the current season
  public/data/FantasyGameContext.json                         FantasyGameContext of the current lineup week
  public/data/FantasyGameContextHistory.json                  finished weeks of the current season (ScoringState partial)
  public/data/MatchupProjections.json                         team projections of the lineup week (WinProbability, HybridExpected)
  public/data/past_seasons/Matchups/Matchups_<season>.json    completed earlier seasons
  public/data/past_seasons/FantasyGameContext/FantasyGameContext_<season>.json   history of earlier seasons

The documents come from the product, so the materializer runs first (products before consumers).

Usage:
  matchup_context_app_publish.py write [--league nfl-reise] [--scope current|history|all] [--fail-on-error]

`write` writes a file only on a semantic difference and updates Timestamps.json[Matchups|FantasyGameContext] for the current
files only. A season whose product document is missing keeps its last file and raises a GitHub warning annotation; the
current Matchups document is required and fails the run. FantasyGameContext and MatchupProjections keep their previous file when
the product holds no current matchup week.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from league_metadata import data_meta_root, default_league_id  # noqa: E402

from app_delivery import Writer, history_matchup_seasons, load_json, warn  # noqa: E402
from data_roots import data_derived_dir  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError  # noqa: E402
from league_standings_sources import current_season, manifest  # noqa: E402
from matchup_context_materialize import CONTEXT_HISTORY, CURRENT, EXPECTED_ERRORS, MATCHUPS, read_document  # noqa: E402

FIRST_CONTEXT_HISTORY_SEASON = 2022


def history_context_seasons(repo_root: Path, current: int) -> list[int]:
    """The previous season (from 2022) plus every earlier season that already has a file."""
    seasons = {current - 1} if current - 1 >= FIRST_CONTEXT_HISTORY_SEASON else set()
    folder = repo_root / "public" / "data" / "past_seasons" / "FantasyGameContext"
    for file in folder.glob("FantasyGameContext_*.json") if folder.is_dir() else []:
        suffix = file.stem.rsplit("_", 1)[-1]
        if suffix.isdigit() and int(suffix) < current:
            seasons.add(int(suffix))
    return sorted(seasons)


def _product(repo_root: Path, league_id: str, season: int, name: str) -> Any | None:
    return read_document(data_derived_dir(repo_root), league_id, season, name)


def write_current(repo_root: Path, league_id: str, writer: Writer, at_utc: datetime | None = None) -> None:
    """Render the current App files from the persisted matchup-context documents (products before consumers, ADR-089)."""
    season = current_season(manifest(repo_root, league_id))
    matchups = _product(repo_root, league_id, season, MATCHUPS)
    if matchups is None:
        raise MatchupContextError(f"matchup-context product {season}/{MATCHUPS} is not materialized")
    writer.put("Matchups.json", matchups, "Matchups")
    current = _product(repo_root, league_id, season, CURRENT) or {}
    # No loadable current matchup week (or no projections of that week): the previous App file stays.
    if current.get("FantasyGameContext") is not None:
        writer.put("FantasyGameContext.json", current["FantasyGameContext"], "FantasyGameContext")
    if current.get("MatchupProjections") is not None:
        writer.put("MatchupProjections.json", current["MatchupProjections"])
    # Not under past_seasons: that tree is cached long-term, while this file changes with every finished week.
    finished = _product(repo_root, league_id, season, CONTEXT_HISTORY)
    if finished is None:
        warn("FantasyGameContextHistory not published", f"matchup-context product {season}/{CONTEXT_HISTORY} is not materialized")
    else:
        writer.put("FantasyGameContextHistory.json", finished)


def write_history(repo_root: Path, league_id: str, writer: Writer, at_utc: datetime | None = None) -> None:
    current = current_season(manifest(repo_root, league_id))
    for season in history_matchup_seasons(repo_root, league_id, current):
        model = _product(repo_root, league_id, season, MATCHUPS)
        if model is None:
            warn(f"Historical Matchups {season} not published", "matchup-context product document is not materialized")
            continue
        writer.put(f"past_seasons/Matchups/Matchups_{season}.json", model)
    for season in history_context_seasons(repo_root, current):
        model = _product(repo_root, league_id, season, CONTEXT_HISTORY)
        if model is None:
            warn(f"Historical FantasyGameContext {season} not published", "matchup-context product document is not materialized")
            continue
        writer.put(f"past_seasons/FantasyGameContext/FantasyGameContext_{season}.json", model)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="write the App files from the matchup context (semantic no-op)")
    write.add_argument("--league", default=None, help="CanonicalLeagueID (default: the only league in data-meta)")
    write.add_argument("--scope", choices=("current", "history", "all"), default="current")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when a required model cannot be built")
    args = parser.parse_args(argv)
    if args.league is None:
        args.league = default_league_id(data_meta_root(args.repo_root))
    return args


def run_write(args: argparse.Namespace) -> int:
    now = datetime.now(timezone.utc)
    writer = Writer(args.repo_root, now)
    try:
        if args.scope in ("current", "all"):
            write_current(args.repo_root, args.league, writer, now)
        if args.scope in ("history", "all"):
            write_history(args.repo_root, args.league, writer, now)
    except EXPECTED_ERRORS as error:
        warn("Matchups not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
