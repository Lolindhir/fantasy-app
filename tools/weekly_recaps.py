#!/usr/bin/env python3
"""CLI of the Weekly Recaps (ADR-063, Issue #1199 section 4).

Usage:
  weekly_recaps.py resolve --league nfl-reise --season 2026     # the season model as JSON
  weekly_recaps.py compare --league nfl-reise                   # shadow against the published App files

Nothing is written. Exit code 1 with a message on stderr when an input is missing or contradicting (nothing is guessed).
``compare`` computes the current and every published historical season and compares each exactly with the published public/data
file (validation-shadow, never an input). The only intended value difference is decision R2: the week basis LeagueScoredWeek
instead of Matchups CompletionState. The current season is expected to be identical; a completed season may gain weeks the
Matchups completion left unknown (reported as additional weeks), while every published week must stay identical.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from league_metadata import data_meta_root, default_league_id  # noqa: E402

from derived_data_lib.weekly_recaps import WeeklyRecapsError, resolve_weekly_recaps, resolve_with_skips  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest  # noqa: E402
from matchup_context import diff_values  # noqa: E402


def published_files(repo_root: Path, league_id: str) -> dict[int, Path]:
    data = repo_root / "public" / "data"
    files: dict[int, Path] = {current_season(manifest(repo_root, league_id)): data / "WeeklyRecaps.json"}
    folder = data / "past_seasons" / "WeeklyRecaps"
    for file in sorted(folder.glob("WeeklyRecaps_*.json")) if folder.is_dir() else []:
        suffix = file.stem.rsplit("_", 1)[-1]
        if suffix.isdigit():
            files[int(suffix)] = file
    return files


def compare_models(published: dict, computed: dict) -> list[str]:
    """Differences of every published week against the computed one; weeks only the computed model has are decision R2, not a difference."""
    found = diff_values({k: v for k, v in published.items() if k != "Weeks"}, {k: v for k, v in computed.items() if k != "Weeks"})
    computed_weeks = {week["Week"]: week for week in computed["Weeks"]}
    for week in published["Weeks"]:
        if week["Week"] not in computed_weeks:
            found.append(f"Weeks[{week['Week']}]: published, missing in computed result")
        else:
            found.extend(f"Weeks[{week['Week']}].{line}" for line in diff_values(week, computed_weeks[week["Week"]]))
    return found


def run_compare(repo_root: Path, league_id: str) -> int:
    failures = 0
    for season, path in sorted(published_files(repo_root, league_id).items()):
        if not path.is_file():
            print(f"{season}: published file missing ({path.name})")
            failures += 1
            continue
        computed, skipped = resolve_with_skips(repo_root, league_id, season)
        published = json.loads(path.read_text(encoding="utf-8-sig"))
        found = compare_models(published, computed)
        extra = sorted({w["Week"] for w in computed["Weeks"]} - {w["Week"] for w in published["Weeks"]})
        print(f"{season}: {'identical' if not found else str(len(found)) + ' difference(s)'}; additional weeks {extra}; evidence gaps {[w for w, _ in skipped]}")
        for line in found[:20]:
            print(f"  {line}")
        failures += bool(found)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--league", default=None, help="CanonicalLeagueID (default: the only league in data-meta)")
    resolve.add_argument("--season", type=int, required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--league", default=None, help="CanonicalLeagueID (default: the only league in data-meta)")
    args = parser.parse_args(argv)
    if args.league is None:
        args.league = default_league_id(data_meta_root(args.repo_root))
    try:
        if args.command == "resolve":
            print(json.dumps(resolve_weekly_recaps(args.repo_root, args.league, args.season), indent=2, ensure_ascii=False))
            return 0
        return run_compare(args.repo_root, args.league)
    except (WeeklyRecapsError, StandingsSourceError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
