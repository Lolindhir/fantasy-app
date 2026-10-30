#!/usr/bin/env python3
"""Consumer generator: App Matchups and FantasyGameContext files from the matchup-context function (ADR-075, Issue #1199 section 3).

Renders exactly the files the App reads from the computed matchup context (tools/derived_data_lib/matchup_context.py and
fantasy_game_context.py); nothing is read from public/data:

  public/data/Matchups.json                                   season Matchups model of the current season
  public/data/FantasyGameContext.json                         FantasyGameContext of the current lineup week
  public/data/past_seasons/Matchups/Matchups_<season>.json    completed earlier seasons
  public/data/past_seasons/FantasyGameContext/FantasyGameContext_<season>.json   history of earlier seasons

The team projection file stays with the PlayerWeekFantasy refresh (tools/player_week_fantasy_refresh.py).

Usage:
  matchup_context_app_publish.py write [--league nfl-reise] [--scope current|history|all] [--fail-on-error]

`write` writes a file only on a semantic difference and updates Timestamps.json[Matchups|FantasyGameContext] for the current
files only. A season whose canonical evidence is incomplete keeps its last file and raises a GitHub warning annotation; the
current Matchups model is required (WeeklyRecaps reads it) and fails the run. FantasyGameContext keeps its previous file when
no current matchup week is loadable.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.fantasy_game_context import resolve_current_context, resolve_historical_season  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError, resolve_matchups  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest  # noqa: E402
from matchup_context import diff_values  # noqa: E402

FIRST_CONTEXT_HISTORY_SEASON = 2022
EXPECTED_ERRORS = (MatchupContextError, LifecycleError, StandingsSourceError)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", file=sys.stderr)


def history_matchup_seasons(repo_root: Path, league_id: str, current: int) -> list[int]:
    """Earlier seasons whose canonical league source is complete (the Matchups history rule)."""
    root = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons"
    seasons: list[int] = []
    for folder in sorted(root.iterdir()) if root.is_dir() else []:
        if not folder.name.isdigit() or int(folder.name) >= current:
            continue
        league_file = folder / "league.json"
        if league_file.is_file() and _load(league_file).get("Status") == "complete":
            seasons.append(int(folder.name))
    return seasons


def history_context_seasons(repo_root: Path, current: int) -> list[int]:
    """The previous season (from 2022) plus every earlier season that already has a file."""
    seasons = {current - 1} if current - 1 >= FIRST_CONTEXT_HISTORY_SEASON else set()
    folder = repo_root / "public" / "data" / "past_seasons" / "FantasyGameContext"
    for file in folder.glob("FantasyGameContext_*.json") if folder.is_dir() else []:
        suffix = file.stem.rsplit("_", 1)[-1]
        if suffix.isdigit() and int(suffix) < current:
            seasons.add(int(suffix))
    return sorted(seasons)


class Writer:
    """Writes App files only where they differ semantically and records the Timestamps.json keys to refresh."""

    def __init__(self, repo_root: Path, now: datetime) -> None:
        self.data = repo_root / "public" / "data"
        self.stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.changed: list[str] = []
        self._stamped: list[str] = []

    def put(self, relative: str, payload: Any, timestamp_key: str | None = None) -> None:
        path = self.data / relative
        if path.is_file() and not diff_values(_load(path), json.loads(json.dumps(payload))):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(payload), encoding="utf-8")
        self.changed.append(f"public/data/{relative}")
        if timestamp_key:
            self._stamped.append(timestamp_key)

    def finish(self) -> list[str]:
        if self._stamped:
            path = self.data / "Timestamps.json"
            timestamps = _load(path) if path.is_file() else {}
            for key in self._stamped:
                timestamps[key] = self.stamp
            path.write_text(_dump(timestamps), encoding="utf-8")
            self.changed.append("public/data/Timestamps.json")
        return self.changed


def _guarded(label: str, build: Callable[[], Any]) -> Any | None:
    """Result of ``build`` or None after a warning when the canonical evidence is incomplete (last file stays)."""
    try:
        return build()
    except EXPECTED_ERRORS as error:
        _warn(f"{label} not published", f"{type(error).__name__}: {error}")
        return None


def write_current(repo_root: Path, league_id: str, writer: Writer, at_utc: datetime) -> None:
    season = current_season(manifest(repo_root, league_id))
    writer.put("Matchups.json", resolve_matchups(repo_root, league_id, season, at_utc), "Matchups")
    context = _guarded("FantasyGameContext", lambda: resolve_current_context(repo_root, league_id, season, at_utc))
    if context is not None:
        writer.put("FantasyGameContext.json", context, "FantasyGameContext")


def write_history(repo_root: Path, league_id: str, writer: Writer, at_utc: datetime) -> None:
    current = current_season(manifest(repo_root, league_id))
    for season in history_matchup_seasons(repo_root, league_id, current):
        model = _guarded(f"Historical Matchups {season}", lambda s=season: resolve_matchups(repo_root, league_id, s, at_utc))
        if model is not None:
            writer.put(f"past_seasons/Matchups/Matchups_{season}.json", model)
    for season in history_context_seasons(repo_root, current):
        model = _guarded(f"Historical FantasyGameContext {season}", lambda s=season: resolve_historical_season(repo_root, league_id, s))
        if model is not None:
            writer.put(f"past_seasons/FantasyGameContext/FantasyGameContext_{season}.json", model)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="write the App files from the matchup context (semantic no-op)")
    write.add_argument("--league", default="nfl-reise")
    write.add_argument("--scope", choices=("current", "history", "all"), default="current")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when a required model cannot be built")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    now = datetime.now(timezone.utc)
    writer = Writer(args.repo_root, now)
    try:
        if args.scope in ("current", "all"):
            write_current(args.repo_root, args.league, writer, now)
        if args.scope in ("history", "all"):
            write_history(args.repo_root, args.league, writer, now)
    except EXPECTED_ERRORS as error:
        _warn("Matchups not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
