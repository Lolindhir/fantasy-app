#!/usr/bin/env python3
"""Synchronize persistent fantasy-league provider lineage and canonical identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from league_source_data_lib.core import (
    fetch_sleeper_league,
    load_bootstraps,
    persisted_sleeper_fetcher,
    sync_bootstrap,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sync", "validate"), nargs="?", default="sync")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--canonical-league-id",
        action="append",
        dest="canonical_league_ids",
        help="Restrict to one CanonicalLeagueID; may be repeated.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Read already persisted Sleeper league raw files instead of fetching the API.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    bootstraps = load_bootstraps(repo_root)
    requested = set(args.canonical_league_ids or [])
    known = {item.canonical_league_id for item in bootstraps}
    unknown = requested - known
    if unknown:
        raise ValueError(f"Unknown CanonicalLeagueID(s): {', '.join(sorted(unknown))}")
    selected = [item for item in bootstraps if not requested or item.canonical_league_id in requested]
    if not selected:
        raise ValueError("No league bootstrap files found or selected")

    if args.command == "validate":
        print(json.dumps({"BootstrapCount": len(selected), "CanonicalLeagueIDs": [b.canonical_league_id for b in selected]}, indent=2))
        return 0

    fetcher = persisted_sleeper_fetcher(repo_root) if args.offline else fetch_sleeper_league
    results = [sync_bootstrap(repo_root, bootstrap, fetcher) for bootstrap in selected]
    print(json.dumps({"Leagues": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
