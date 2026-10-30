#!/usr/bin/env python3
"""CLI of the matchup context (ADR-075, Issue #1199 section 3).

Usage:
  matchup_context.py matchups --league nfl-reise --season 2026 [--at 2026-10-30T12:00:00Z]

Prints the season Matchups model of the league season at the given instant as JSON. ``--at`` defaults to the current time;
nothing is written. Exit code 1 with a message on stderr when an input is missing or contradicting (nothing is guessed).
Later steps add the FantasyGameContext, the history, the projections and the shadow comparison.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_lifecycle import LifecycleError, parse_instant  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError, resolve_matchups  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    matchups = sub.add_parser("matchups", help="print the season Matchups model at an instant")
    matchups.add_argument("--league", required=True)
    matchups.add_argument("--season", type=int, required=True)
    matchups.add_argument("--at", help="ISO instant with Z or offset; default: now")
    matchups.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        at = parse_instant(args.at, "--at") if args.at else datetime.now(timezone.utc)
        result = resolve_matchups(args.repo_root, args.league, args.season, at)
    except (MatchupContextError, LifecycleError) as error:
        print(f"matchup_context: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
