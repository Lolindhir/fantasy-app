#!/usr/bin/env python3
"""CLI of the matchup context (ADR-075, Issue #1199 section 3).

Usage:
  matchup_context.py matchups --league nfl-reise --season 2026 [--at 2026-10-30T12:00:00Z]
  matchup_context.py context --league nfl-reise --season 2026 [--at ...]    # FantasyGameContext of the current matchup week
  matchup_context.py history --league nfl-reise --season 2025               # FantasyGameContext history of a completed season
  matchup_context.py compare --league nfl-reise [--at ...]                  # shadow against the published App files

Prints the model as JSON. ``--at`` defaults to the current time; nothing is written. Exit code 1 with a message on stderr
when an input is missing or contradicting (nothing is guessed). ``compare`` computes every model and compares it exactly with
the published public/data file (validation-shadow, never an input). The only intended value difference is decision M2: the
counterfactual week-final rule of the FantasyGameContext (LeagueScoredWeek instead of Sleeper last_scored_leg).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_lifecycle import LifecycleError, parse_instant  # noqa: E402
from derived_data_lib.fantasy_game_context import resolve_current_context, resolve_historical_season  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError, resolve_matchups  # noqa: E402


def diff_values(expected, actual, path: str = "") -> list[str]:
    """Exact differences between the published (expected) and the computed (actual) value, by JSON path."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        found: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            where = f"{path}.{key}" if path else key
            if key not in actual:
                found.append(f"{where}: missing in computed result")
            elif key not in expected:
                found.append(f"{where}: missing in published file")
            else:
                found.extend(diff_values(expected[key], actual[key], where))
        return found
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: published {len(expected)} items != computed {len(actual)}"]
        found = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            found.extend(diff_values(left, right, f"{path}[{index}]"))
        return found
    same = expected == actual and type(expected) is type(actual)
    return [] if same or (isinstance(expected, (int, float)) and isinstance(actual, (int, float)) and not isinstance(expected, bool) and not isinstance(actual, bool) and expected == actual) else [f"{path}: published {expected!r} != computed {actual!r}"]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compare_with_published(repo_root: Path, league_id: str, at_text: str | None) -> dict[str, list[str] | str]:
    """Label to differences (or a note) for the current and historical Matchups and FantasyGameContext files.

    The current files are computed at their Timestamps.json instant (last semantic update) unless ``--at`` is given, so inputs
    that changed afterwards can show up as differences; run it right after a League Live publication. Historical seasons are
    computed at the current time.
    """
    data = repo_root / "public" / "data"
    stamps = _load(data / "Timestamps.json")
    now = datetime.now(timezone.utc)
    report: dict[str, list[str] | str] = {}

    published = _load(data / "Matchups.json")
    at = parse_instant(at_text or stamps["Matchups"], "--at" if at_text else "Timestamps.Matchups")
    report["Matchups.json"] = diff_values(published, resolve_matchups(repo_root, league_id, int(published["Season"]), at))

    published = _load(data / "FantasyGameContext.json")
    at = parse_instant(at_text or stamps["FantasyGameContext"], "--at" if at_text else "Timestamps.FantasyGameContext")
    context = resolve_current_context(repo_root, league_id, int(published["Season"]), at)
    report["FantasyGameContext.json"] = "not comparable: no loadable matchup week at that instant" if context is None else diff_values(published, context)

    past = data / "past_seasons"
    for folder, prefix, compute in (
        ("Matchups", "Matchups", lambda season: resolve_matchups(repo_root, league_id, season, now)),
        ("FantasyGameContext", "FantasyGameContext", lambda season: resolve_historical_season(repo_root, league_id, season)),
    ):
        for file in sorted((past / folder).glob(f"{prefix}_*.json")):
            season = int(file.stem.rsplit("_", 1)[1])
            report[f"past_seasons/{folder}/{file.name}"] = diff_values(_load(file), compute(season))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    matchups = sub.add_parser("matchups", help="print the season Matchups model at an instant")
    matchups.add_argument("--league", required=True)
    matchups.add_argument("--season", type=int, required=True)
    matchups.add_argument("--at", help="ISO instant with Z or offset; default: now")
    matchups.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    context_parser = sub.add_parser("context", help="print the FantasyGameContext of the current matchup week")
    context_parser.add_argument("--league", required=True)
    context_parser.add_argument("--season", type=int, required=True)
    context_parser.add_argument("--at", help="ISO instant with Z or offset; default: now")
    context_parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    history = sub.add_parser("history", help="print the FantasyGameContext history of a completed season")
    history.add_argument("--league", required=True)
    history.add_argument("--season", type=int, required=True)
    history.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    compare = sub.add_parser("compare", help="shadow comparison against the published App files")
    compare.add_argument("--league", required=True)
    compare.add_argument("--at", help="ISO instant; default: the Timestamps.json instants")
    compare.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if args.command == "compare":
        try:
            report = compare_with_published(args.repo_root, args.league, args.at)
        except (MatchupContextError, LifecycleError, OSError, KeyError, ValueError) as error:
            print(f"matchup_context compare: {error}", file=sys.stderr)
            return 1
        failed = False
        for label, outcome in report.items():
            if isinstance(outcome, str):
                print(f"{label}: {outcome}")
            elif outcome:
                failed = True
                print(f"{label}: {len(outcome)} difference(s)")
                for line in outcome[:20]:
                    print(f"  {line}")
            else:
                print(f"{label}: identical")
        return 1 if failed else 0
    try:
        at = parse_instant(args.at, "--at") if args.at else datetime.now(timezone.utc)
        if args.command == "history":
            result = resolve_historical_season(args.repo_root, args.league, args.season)
        elif args.command == "context":
            result = resolve_current_context(args.repo_root, args.league, args.season, at)
            if result is None:
                print("matchup_context: no loadable matchup week at that instant", file=sys.stderr)
                return 1
        else:
            result = resolve_matchups(args.repo_root, args.league, args.season, at)
    except (MatchupContextError, LifecycleError) as error:
        print(f"matchup_context: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
