#!/usr/bin/env python3
"""TeamCapOutlook App delivery renderer (L10 #1237, persisted product ADR-089 / Issue #1571).

The model lives in tools/derived_data_lib/team_cap_outlook.py and is persisted as the Shared Derived product
data-derived/team-cap-outlook/<CanonicalLeagueID>/<Season>.json by tools/team_cap_outlook_materialize.py. The `write` command renders
public/data/TeamCapOutlook.json from that persisted product with an unchanged App contract (no recomputation).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.team_cap_outlook import (  # noqa: E402,F401  (re-exported for existing callers)
    CONTRACT_VERSION, OutlookError, PRODUCT, build, load, product_path, read_product, serialize,
)
from league_metadata import data_meta_root, default_league_id  # noqa: E402

OUTPUT_NAME = "TeamCapOutlook.json"


def write(repo_root: Path, league_id: str) -> bool:
    serialized = serialize(read_product(repo_root, league_id))
    data_dir = repo_root / "public" / "data"
    target = data_dir / OUTPUT_NAME
    if target.is_file() and target.read_text(encoding="utf-8") == serialized:
        return False
    data_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", help="CanonicalLeagueID; default only when data-meta has exactly one league")
    args = parser.parse_args(argv)
    try:
        league_id = args.league or default_league_id(data_meta_root(args.repo_root))
        if args.command == "check":
            result = read_product(args.repo_root, league_id)
            print(f"TeamCapOutlook check: {len(result['Teams'])} teams, "
                  f"{sum(t['Status'] == 'ready' for t in result['Teams'])} ready")
        else:
            print("TeamCapOutlook written" if write(args.repo_root, league_id)
                  else "TeamCapOutlook unchanged")
    except (ValueError, OSError) as error:
        if args.command == "write":
            # Never block the existing League.json publisher for a noncritical outlook.
            # Keep last-good data; the App rejects a stale salary/roster witness.
            print(f"::warning title=TeamCapOutlook unavailable::{error}", file=sys.stderr)
            return 0
        print(f"TeamCapOutlook: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
