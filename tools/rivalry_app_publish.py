#!/usr/bin/env python3
"""Consumer generator: materializes the league-rivalry product and renders the App file (Issue #1455).

  data-derived/league-rivalry/<CanonicalLeagueID>.json   Shared Derived product, one file per league over every season (written only on a difference)
  public/data/Rivalry.json                               the product document unchanged (App delivery, Angular only displays it)

Usage:
  rivalry_app_publish.py write [--league ID] [--fail-on-error]

The product covers all seasons at once, so there is no scope switch: League Live (fail-soft, a failure keeps the last product and App file and
warns) and the weekly update-transactions run call the same command. Files are written only on a semantic difference and
Timestamps.json[Rivalry] is stamped only then. Without --league more than one league fails closed (the App file carries no league dimension).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data import league_rivalry_path, materialize_league_rivalry  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError  # noqa: E402
from derived_data_lib.rivalry import RivalryError  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError  # noqa: E402
from matchup_context_app_publish import Writer, _load, _warn  # noqa: E402

EXPECTED_ERRORS = (RivalryError, MatchupContextError, LifecycleError, StandingsSourceError, LeagueMetadataError)


def leagues(requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise RivalryError(f"the App Rivalry file carries no league dimension; expected exactly one league, found {ids}")
    return ids


def publish(repo_root: Path, league_id: str, now: datetime, writer: Writer) -> None:
    out_root = data_derived_dir(repo_root)
    materialize_league_rivalry(repo_root, out_root, league_id, None, False, now)
    writer.put("Rivalry.json", _load(league_rivalry_path(out_root, league_id)), "Rivalry")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="materialize the product and write the App file (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the product cannot be built")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    now = datetime.now(timezone.utc)
    writer = Writer(args.repo_root, now)
    try:
        for league_id in leagues(args.league):
            publish(args.repo_root, league_id, now, writer)
    except EXPECTED_ERRORS as error:
        _warn("Rivalry not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
