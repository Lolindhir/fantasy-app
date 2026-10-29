#!/usr/bin/env python3
"""CLI of the shared week-final definition (ADR-071, Issue #897).

Usage:
  week_finality.py bounds --league nfl-reise --season 2026

Prints the evidence per league week and the LeagueScoredWeek / StatsFinalWeek milestones as JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.week_finality import WeekFinalityError, resolve_week_finality  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bounds = sub.add_parser("bounds", help="print evidence and milestones")
    bounds.add_argument("--league", required=True)
    bounds.add_argument("--season", type=int, required=True)
    bounds.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        result = resolve_week_finality(args.repo_root, args.league, args.season)
    except WeekFinalityError as error:
        print(f"week_finality: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
