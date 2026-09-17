#!/usr/bin/env python3
"""Build the current app transaction base from canonical League source-data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from transaction_canonical_shadow import (
    build_roster_provider_lookup,
    load_canonical_transactions,
    load_json,
)


def build_repo_canonical_transactions(
    repo_root: Path,
    *,
    canonical_league_id: str,
    season: int,
) -> list[dict[str, object]]:
    season_dir = (
        repo_root
        / "source-data"
        / "leagues"
        / canonical_league_id
        / "seasons"
        / str(season)
    )
    rosters = load_json(season_dir / "rosters.json")
    roster_lookup = build_roster_provider_lookup(rosters)
    return load_canonical_transactions(season_dir, roster_lookup, season=season)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--canonical-league-id", required=True)
    parser.add_argument("--season", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    transactions = build_repo_canonical_transactions(
        args.repo_root.resolve(),
        canonical_league_id=args.canonical_league_id,
        season=args.season,
    )
    print(json.dumps(transactions, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
