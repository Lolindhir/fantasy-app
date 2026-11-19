#!/usr/bin/env python3
"""Materializer of the matchup-context Shared Derived product (ADR-089, amends ADR-075; Issue #1571).

The pure function tools/derived_data_lib/matchup_context.py (plus fantasy_game_context.py and the team-range/win-prob projection
of tools/matchup_projection.py) stays the single implementation. This module persists its results per league and season; the App
files (Matchups.json, FantasyGameContext.json, FantasyGameContextHistory.json, MatchupProjections.json, past_seasons files) are
rendered from the persisted documents by tools/matchup_context_app_publish.py with an unchanged App contract.

Layout (CanonicalLeagueID and Season are part of the path; no AsOfUtc is stored, so unchanged inputs write nothing):
  <out-root>/matchup-context/<CanonicalLeagueID>/<Season>/matchups.json              season Matchups model
  <out-root>/matchup-context/<CanonicalLeagueID>/<Season>/fantasy-game-context.json  history document (final for a completed season,
                                                                                      partial = finished weeks of the running season)
  <out-root>/matchup-context/<CanonicalLeagueID>/<Season>/current.json               running season only: FantasyGameContext of the lineup
                                                                                      week and MatchupProjections (WinProbability, HybridExpected)

The documents of the running season depend on the clock through the Decision Windows (kickoffs, locks): they are current snapshots,
written only on a semantic change and excluded from the clean-root equality of the restore probe. Every document of a completed
season is a pure function of canonical facts and products and is covered by it.

Usage:
  matchup_context_materialize.py [--league ID] [--scope current|history|all] [--out-root DIR] [--check] [--fail-on-error]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT, data_derived_dir  # noqa: E402
from derived_data_lib.fantasy_game_context import (  # noqa: E402
    resolve_current_context, resolve_current_season_history, resolve_historical_season,
)
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError, resolve_matchups  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest, manifest_seasons  # noqa: E402
from matchup_projection import compute_matchup_projections  # noqa: E402
from player_week_fantasy_app_publish import load_app_player_week_fantasy  # noqa: E402

PRODUCT = "matchup-context"
SCHEMA_VERSION = 1
CURRENT_PRODUCT = "matchup-context-current"
FIRST_CONTEXT_HISTORY_SEASON = 2022
MATCHUPS = "matchups.json"
CONTEXT_HISTORY = "fantasy-game-context.json"
CURRENT = "current.json"
EXPECTED_ERRORS = (MatchupContextError, LifecycleError, StandingsSourceError, LeagueMetadataError)


def _warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", file=sys.stderr)


def product_dir(out_root: Path, league_id: str, season: int) -> Path:
    return out_root / PRODUCT / league_id / str(season)


def serialize(document: Any) -> str:
    """Deterministic compact JSON; the same bytes the restore probe digests."""
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"


def read_document(out_root: Path, league_id: str, season: int, name: str) -> Any | None:
    """The persisted document, or None when it was never materialized."""
    path = product_dir(out_root, league_id, season) / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def completed_seasons(repo_root: Path, league_id: str, current: int) -> list[int]:
    """Earlier seasons whose canonical league source is complete (the Matchups history rule)."""
    root = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons"
    seasons: list[int] = []
    for folder in sorted(root.iterdir()) if root.is_dir() else []:
        if not folder.name.isdigit() or int(folder.name) >= current:
            continue
        league_file = folder / "league.json"
        if league_file.is_file() and json.loads(league_file.read_text(encoding="utf-8-sig")).get("Status") == "complete":
            seasons.append(int(folder.name))
    return seasons


def current_document(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """FantasyGameContext of the lineup week and its MatchupProjections; both null when no current matchup week is loadable."""
    context = resolve_current_context(repo_root, league_id, season, at_utc)
    projections = None
    if context is not None:
        try:
            player_model = load_app_player_week_fantasy(repo_root, league_id, season, int(context["Week"]))
        except (OSError, ValueError, KeyError) as error:
            _warn("MatchupProjections not materialized", f"{type(error).__name__}: {error}")
        else:
            projections = compute_matchup_projections(repo_root, context, player_model, league_id=league_id, at_utc=at_utc)
    return {
        "SchemaVersion": SCHEMA_VERSION, "Product": CURRENT_PRODUCT, "CanonicalLeagueID": league_id, "Season": season,
        "Week": None if context is None else int(context["Week"]),
        "FantasyGameContext": context, "MatchupProjections": projections,
    }


def build_documents(
    repo_root: Path, league_id: str, season: int, current: int, at_utc: datetime,
) -> dict[str, Callable[[], Any]]:
    """Lazy builders of the documents of one season; a failing optional document is skipped with a warning by the caller."""
    if season == current:
        return {
            MATCHUPS: lambda: resolve_matchups(repo_root, league_id, season, at_utc),
            CONTEXT_HISTORY: lambda: resolve_current_season_history(repo_root, league_id, season, at_utc),
            CURRENT: lambda: current_document(repo_root, league_id, season, at_utc),
        }
    builders: dict[str, Callable[[], Any]] = {MATCHUPS: lambda: resolve_matchups(repo_root, league_id, season, at_utc)}
    if season >= FIRST_CONTEXT_HISTORY_SEASON:
        builders[CONTEXT_HISTORY] = lambda: resolve_historical_season(repo_root, league_id, season)
    return builders


def materialize_season(
    repo_root: Path, out_root: Path, league_id: str, season: int, current: int, at_utc: datetime,
    *, check_only: bool = False, required: frozenset[str] = frozenset({MATCHUPS}),
) -> dict[str, Any]:
    """Build and write the documents of one season on a byte difference; an optional document that cannot be built keeps its last file."""
    folder = product_dir(out_root, league_id, season)
    written: list[str] = []
    skipped: list[str] = []
    unchanged = 0
    for name, build in build_documents(repo_root, league_id, season, current, at_utc).items():
        try:
            text = serialize(build())
        except EXPECTED_ERRORS as error:
            if name in required:
                raise
            skipped.append(name)
            _warn(f"matchup-context {season} {name} not materialized", f"{type(error).__name__}: {error}")
            continue
        path = folder / name
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            unchanged += 1
            continue
        written.append(name)
        if not check_only:
            _atomic_write(path, text)
    return {"Season": season, "CanonicalLeagueID": league_id, "Written" if not check_only else "WouldWrite": len(written),
            "WrittenFiles": written, "Unchanged": unchanged, "Skipped": skipped}


def seasons_for_scope(repo_root: Path, league_id: str, scope: str) -> tuple[int, list[int]]:
    current = current_season(manifest(repo_root, league_id))
    available = set(manifest_seasons(manifest(repo_root, league_id)))
    seasons: list[int] = []
    if scope in ("history", "all"):
        seasons += [s for s in completed_seasons(repo_root, league_id, current) if s in available]
    if scope in ("current", "all"):
        seasons.append(current)
    return current, seasons


def materialize(
    repo_root: Path, out_root: Path, league_id: str, scope: str, at_utc: datetime,
    *, check_only: bool = False, fail_on_error: bool = False,
) -> list[dict[str, Any]]:
    current, seasons = seasons_for_scope(repo_root, league_id, scope)
    summaries: list[dict[str, Any]] = []
    for season in seasons:
        try:
            summaries.append(materialize_season(repo_root, out_root, league_id, season, current, at_utc, check_only=check_only))
        except EXPECTED_ERRORS as error:
            _warn(f"matchup-context {season} not materialized", f"{type(error).__name__}: {error}")
            if fail_on_error and season == current:
                raise
    return summaries


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=None, help="default: every configured league (data-meta)")
    parser.add_argument("--scope", choices=("current", "history", "all"), default="current")
    parser.add_argument("--out-root", type=Path, default=None, help="default: the repository data-derived root")
    parser.add_argument("--check", action="store_true", help="dry run; exit 1 when a file would be written")
    parser.add_argument("--fail-on-error", action="store_true", help="exit 1 when the running season cannot be materialized")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_root = args.out_root if args.out_root is not None else data_derived_dir(args.repo_root)
    now = datetime.now(timezone.utc)
    pending = 0
    try:
        for league_id in [args.league] if args.league else list(list_league_ids()):
            for summary in materialize(args.repo_root, out_root, league_id, args.scope, now,
                                       check_only=args.check, fail_on_error=args.fail_on_error):
                pending += summary.get("WouldWrite", 0)
                print(json.dumps(summary, sort_keys=True))
    except EXPECTED_ERRORS as error:
        print(f"matchup-context materialization failed: {error}", file=sys.stderr)
        return 1
    return 1 if args.check and pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
