#!/usr/bin/env python3
"""CLI of the league-teams identity rule (Issue #774, ADR-098).

Usage:
  league_teams.py season --league nfl-reise --season 2026 [--repo-root PATH]

Prints the fantasy-team identity of one season (manager fields, TeamName, TeamNameSource, TeamAbbr, TeamAvatar) as a JSON list,
computed by the single implementation tools/derived_data_lib/league_teams.py from the canonical members and rosters. Nothing is written.
Exit code 1 with a message on stderr when canonical evidence is missing or contradicting (fail closed).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_teams import LeagueTeamsError, season_teams_for  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["season"])
    parser.add_argument("--league", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    try:
        teams = season_teams_for(args.repo_root, args.league, args.season)
    except LeagueTeamsError as error:
        print(f"league_teams: {error}", file=sys.stderr)
        return 1
    print(json.dumps(teams, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
