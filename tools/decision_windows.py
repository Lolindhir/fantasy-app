#!/usr/bin/env python3
"""CLI of the Decision Windows (ADR-074, Issue #1199 section 2).

Usage:
  decision_windows.py resolve --league nfl-reise --season 2026 [--at 2026-10-30T12:00:00Z]

Prints the Decision Windows of the league season at the given instant as JSON. ``--at`` defaults to the current time;
nothing is written. Exit code 1 with a message on stderr when an input is missing or contradicting (nothing is guessed).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.decision_windows import DecisionWindowsError, resolve  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError, parse_instant  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    resolve_parser = sub.add_parser("resolve", help="print the Decision Windows at an instant")
    resolve_parser.add_argument("--league", required=True)
    resolve_parser.add_argument("--season", type=int, required=True)
    resolve_parser.add_argument("--at", help="ISO instant with Z or offset; default: now")
    resolve_parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        at = parse_instant(args.at, "--at") if args.at else datetime.now(timezone.utc)
        result = resolve(args.repo_root, args.league, args.season, at)
    except (DecisionWindowsError, LifecycleError) as error:
        print(f"decision_windows: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
