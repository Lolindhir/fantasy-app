#!/usr/bin/env python3
"""Materializer of the team-cap-outlook Shared Derived product (ADR-089, amends ADR-079; Issue #1571).

Persists the current-season TeamCapOutlook model (tools/team_cap_outlook_app_publish.py::load: canonical rosters plus the newest
player-valuation snapshot) per league at
  <repo>/data-derived/team-cap-outlook/<CanonicalLeagueID>/<Season>.json
Only a byte difference writes. The document carries no clock. The App delivery file is rendered from it by
`team_cap_outlook_app_publish.py write`. Fail-soft like the App file it feeds: an unavailable input warns and keeps the last good file.

Usage: team_cap_outlook_materialize.py [--league ID] [--check]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from league_metadata import data_meta_root, list_league_ids  # noqa: E402
from league_standings_sources import current_season, manifest  # noqa: E402
from team_cap_outlook_app_publish import OutlookError, PRODUCT, load, product_path, serialize  # noqa: E402,F401


def materialize(repo_root: Path, league_id: str, *, check_only: bool = False) -> bool:
    """Build the current-season document; True when the file is (or would be) written."""
    document = load(repo_root, league_id)
    path = product_path(repo_root, league_id, int(document["Season"]))
    text = serialize(document)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    if not check_only:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(text)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=None, help="default: every configured league (data-meta)")
    parser.add_argument("--check", action="store_true", help="dry run; exit 1 when a file would be written")
    args = parser.parse_args(argv)
    pending = 0
    for league_id in [args.league] if args.league else list(list_league_ids(data_meta_root(args.repo_root))):
        try:
            changed = materialize(args.repo_root, league_id, check_only=args.check)
        except (ValueError, OSError) as error:
            print(f"::warning title=TeamCapOutlook product unavailable::{league_id}: {error}", file=sys.stderr)
            if args.check:
                return 1
            continue
        pending += int(changed)
        print(f"TeamCapOutlook product {league_id}: {'written' if changed and not args.check else 'would write' if changed else 'unchanged'}")
    return 1 if args.check and pending else 0


if __name__ == "__main__":
    sys.exit(main())
