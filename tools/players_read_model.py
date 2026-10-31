#!/usr/bin/env python3
"""CLI of the Players read model (ADR-076, Issue #1226).

Usage:
  players_read_model.py resolve --league nfl-reise --season 2026 --as-of 2026-10-31 [--out FILE]

Resolves the the Players file rows for one league, one season and one reference date (Age) from canonical facts and the
player-valuation snapshot. Prints a summary and the warnings; with --out the rows are written as the published file text.
Nothing in the repository is written. Exit code 1 with a message on stderr when an input is missing or contradicting.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.players_read_model import PlayersReadModelError, resolve, serialize_players  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("resolve", help="resolve the Players rows for a reference date")
    cmd.add_argument("--league", required=True)
    cmd.add_argument("--season", type=int, required=True)
    cmd.add_argument("--as-of", required=True, help="reference date YYYY-MM-DD (Age)")
    cmd.add_argument("--out", type=Path, help="write the rows as the Players file text to this file")
    cmd.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        as_of = date.fromisoformat(args.as_of)
        result = resolve(args.repo_root, args.league, args.season, as_of)
    except (PlayersReadModelError, ValueError) as error:
        print(f"players_read_model: {error}", file=sys.stderr)
        return 1
    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.out:
        args.out.write_text(serialize_players(result.players), encoding="utf-8")
    print(f"players_read_model: {len(result.players)} players, AsOfDate {result.as_of.isoformat()}, {len(result.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
