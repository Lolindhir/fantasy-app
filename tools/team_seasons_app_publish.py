#!/usr/bin/env python3
"""Consumer generator: renders the App file from the persisted league-teams product (Issue #774, ADR-098).

  data-derived/league-teams/<CanonicalLeagueID>.json   Shared Derived product, one file per league over every season (materialized beforehand)
  public/data/TeamSeasons.json                         the product document unchanged (App delivery, Angular only looks up Season + TeamID)

Usage:
  team_seasons_app_publish.py write [--league ID] [--fail-on-error]

The product covers all seasons at once, so there is no scope switch: League Live (fail-soft, a failure keeps the last App file and warns) and the
weekly update-history run call the same command. The file is written only on a semantic difference and Timestamps.json[TeamSeasons] is
stamped only then. Without --league more than one league fails closed (the App file carries no league dimension).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data import league_teams_path  # noqa: E402
from derived_data_lib.league_teams import LeagueTeamsError  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from matchup_context_app_publish import Writer, _load, _warn  # noqa: E402

EXPECTED_ERRORS = (LeagueTeamsError, LeagueMetadataError)


def leagues(requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise LeagueTeamsError(f"the App TeamSeasons file carries no league dimension; expected exactly one league, found {ids}")
    return ids


def publish(repo_root: Path, league_id: str, writer: Writer) -> None:
    path = league_teams_path(data_derived_dir(repo_root), league_id)
    if not path.is_file():
        raise LeagueTeamsError(f"league-teams product missing for {league_id}; materialize it first")
    writer.put("TeamSeasons.json", _load(path), "TeamSeasons")
    stamps = writer.data / "Timestamps.json"
    if "TeamSeasons" not in writer._stamped and stamps.is_file() and "TeamSeasons" not in _load(stamps):
        writer._stamped.append("TeamSeasons")  # first publication: the file may already equal the product, the freshness key must exist


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="render the App file from the persisted product (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the product is missing")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        for league_id in leagues(args.league):
            publish(args.repo_root, league_id, writer)
    except EXPECTED_ERRORS as error:
        _warn("TeamSeasons not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
