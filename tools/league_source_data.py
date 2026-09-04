#!/usr/bin/env python3
"""Synchronize persistent fantasy-league provider data and canonical league identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from league_source_data_lib.acquire import (
    fetch_sleeper_json,
    persist_raw_plans,
    plan_raw_acquisition,
)
from league_source_data_lib.core import (
    discover_sleeper_lineage,
    fetch_sleeper_league,
    load_bootstraps,
    persisted_sleeper_fetcher,
    sync_bootstrap,
)
from league_source_data_lib.materialize import (
    PlayerMappingResolver,
    persist_canonical_outputs,
    plan_canonical_materialization,
)
from league_source_data_lib.registry import load_league_registry


def combine_sync_results(identity: dict, raw: dict) -> dict:
    result = {**identity, **raw}
    result["RawFilesChanged"] = int(identity.get("RawFilesChanged", 0)) + int(
        raw.get("RawFilesChanged", 0)
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("sync", "materialize", "validate"),
        nargs="?",
        default="sync",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--canonical-league-id",
        action="append",
        dest="canonical_league_ids",
        help="Restrict to one CanonicalLeagueID; may be repeated.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Read already persisted Sleeper raw files instead of fetching the API.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly repair/refetch historical provider partitions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    bootstraps = load_bootstraps(repo_root)
    registry = load_league_registry(repo_root)
    requested = set(args.canonical_league_ids or [])
    known = {item.canonical_league_id for item in bootstraps}
    unknown = requested - known
    if unknown:
        raise ValueError(
            f"Unknown CanonicalLeagueID(s): {', '.join(sorted(unknown))}"
        )
    selected = [
        item
        for item in bootstraps
        if not requested or item.canonical_league_id in requested
    ]
    if not selected:
        raise ValueError("No league bootstrap files found or selected")

    if args.command == "validate":
        print(
            json.dumps(
                {
                    "BootstrapCount": len(selected),
                    "CanonicalLeagueIDs": [
                        b.canonical_league_id for b in selected
                    ],
                    "DatasetCount": len(registry),
                    "DatasetIDs": [dataset.id for dataset in registry],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "materialize":
        resolver = PlayerMappingResolver.load(repo_root)
        results = []
        for bootstrap in selected:
            outputs = plan_canonical_materialization(
                repo_root,
                bootstrap.canonical_league_id,
                registry,
                resolver,
            )
            result = persist_canonical_outputs(outputs)
            results.append(
                {
                    "CanonicalLeagueID": bootstrap.canonical_league_id,
                    **result,
                }
            )
        print(json.dumps({"Leagues": results}, indent=2))
        return 0

    lineage_fetcher = (
        persisted_sleeper_fetcher(repo_root)
        if args.offline
        else fetch_sleeper_league
    )
    results = []
    for bootstrap in selected:
        lineage = discover_sleeper_lineage(
            bootstrap.current_provider_league_id,
            lineage_fetcher,
        )
        lineage_by_id = {
            item.provider_league_id: item.payload for item in lineage
        }
        identity = sync_bootstrap(
            repo_root,
            bootstrap,
            lineage_by_id.__getitem__,
        )
        plans = plan_raw_acquisition(
            repo_root,
            lineage,
            registry,
            fetch_sleeper_json,
            force=args.force,
            offline=args.offline,
        )
        raw = persist_raw_plans(plans)
        results.append(combine_sync_results(identity, raw))

    print(json.dumps({"Leagues": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
