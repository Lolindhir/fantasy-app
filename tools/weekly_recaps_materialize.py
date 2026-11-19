#!/usr/bin/env python3
"""Materializer of the weekly-recaps Shared Derived product (ADR-089, amends ADR-063 and ADR-086; Issue #1571).

The pure function tools/derived_data_lib/weekly_recaps.py (KeyPlayers, KeyGames, TeamAwards, lineup efficiency, win probability marks and
PlayerAwards) stays the single implementation. This module persists its season model per league; the App files WeeklyRecaps.json, the
historical App archives and PlayerAwardHistory.json are rendered from the persisted documents by tools/weekly_recaps_app_publish.py with an
unchanged App contract, so no App generator reads its own archive as input (Issue #1571 L3).

Layout (CanonicalLeagueID and Season are part of the path; the model carries no clock, so unchanged inputs write nothing):
  <out-root>/weekly-recaps/<CanonicalLeagueID>/<Season>.json

Usage:
  weekly_recaps_materialize.py [--league ID] [--scope current|history|all] [--out-root DIR] [--check] [--fail-on-error]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.weekly_recaps import WeeklyRecapsError, resolve_weekly_recaps  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest, manifest_seasons  # noqa: E402
from matchup_context_materialize import completed_seasons  # noqa: E402

PRODUCT = "weekly-recaps"
EXPECTED_ERRORS = (WeeklyRecapsError, LifecycleError, StandingsSourceError, LeagueMetadataError)


def product_path(out_root: Path, league_id: str, season: int) -> Path:
    return out_root / PRODUCT / league_id / f"{season}.json"


def serialize(document: Any) -> str:
    """Deterministic compact JSON; the same bytes the restore probe digests."""
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"


def read_model(out_root: Path, league_id: str, season: int) -> dict[str, Any] | None:
    """The persisted season model, or None when it was never materialized."""
    path = product_path(out_root, league_id, season)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", file=sys.stderr)


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


def materialize_season(repo_root: Path, out_root: Path, league_id: str, season: int, *, check_only: bool = False) -> dict[str, Any]:
    """Build and write one season model on a byte difference."""
    text = serialize(resolve_weekly_recaps(repo_root, league_id, season))
    path = product_path(out_root, league_id, season)
    changed = not (path.is_file() and path.read_text(encoding="utf-8") == text)
    if changed and not check_only:
        _atomic_write(path, text)
    return {"Season": season, "CanonicalLeagueID": league_id, "Written" if not check_only else "WouldWrite": int(changed)}


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
    repo_root: Path, out_root: Path, league_id: str, scope: str, *, check_only: bool = False, fail_on_error: bool = False,
) -> list[dict[str, Any]]:
    current, seasons = seasons_for_scope(repo_root, league_id, scope)
    summaries: list[dict[str, Any]] = []
    for season in seasons:
        try:
            summaries.append(materialize_season(repo_root, out_root, league_id, season, check_only=check_only))
        except EXPECTED_ERRORS as error:
            _warn(f"weekly-recaps {season} not materialized", f"{type(error).__name__}: {error}")
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
    pending = 0
    try:
        for league_id in [args.league] if args.league else list(list_league_ids()):
            for summary in materialize(args.repo_root, out_root, league_id, args.scope,
                                       check_only=args.check, fail_on_error=args.fail_on_error):
                pending += summary.get("WouldWrite", 0)
                print(json.dumps(summary, sort_keys=True))
    except EXPECTED_ERRORS as error:
        print(f"weekly-recaps materialization failed: {error}", file=sys.stderr)
        return 1
    return 1 if args.check and pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
