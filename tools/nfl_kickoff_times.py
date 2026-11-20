#!/usr/bin/env python3
"""Kickoff conversion CLI for PowerShell consumers (Issue #1572).

The conversion itself is owned by derived_data_lib/nfl_games.py (nfl-games product). This thin wrapper lets
the PowerShell Schedule generator use that single implementation instead of its own Eastern-to-UTC code.

  nfl_kickoff_times.py epoch --game-day 2030-09-12 --game-time 20:15   -> epoch text, empty line when GameTime is unknown
  nfl_kickoff_times.py season --season 2026 [--repo-root R]            -> JSON {GameID: epoch text | null} of the canonical schedule
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.nfl_games import kickoff_epoch  # noqa: E402


def season_map(repo_root: Path, season: int) -> dict[str, str | None]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json"
    games = json.loads(path.read_text(encoding="utf-8")).get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"Canonical NFL schedule {season} contains no games.")
    return {
        str(game["GameID"]): kickoff_epoch(str(game["GameID"]), str(game["GameDay"]), game.get("GameTime") or None)
        for game in games
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    epoch = sub.add_parser("epoch")
    epoch.add_argument("--game-day", required=True)
    epoch.add_argument("--game-time", default="")
    season = sub.add_parser("season")
    season.add_argument("--season", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "epoch":
            print(kickoff_epoch("cli", args.game_day, args.game_time.strip() or None) or "")
        else:
            print(json.dumps(season_map(args.repo_root.resolve(), args.season)))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"nfl_kickoff_times failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
