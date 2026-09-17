#!/usr/bin/env python3
"""Synchronize persistent fantasy-league provider data and canonical league identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from league_source_data_lib.acquire import (
    fetch_sleeper_json,
    persist_raw_plans,
    plan_raw_acquisition,
)
from league_source_data_lib.core import (
    SleeperLeagueInstance,
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
from league_source_data_lib.transaction_materialize import (
    TRANSACTION_SCOPE_DEPENDENCIES,
    plan_transaction_materialization,
)
from league_source_data_lib.transaction_window import (
    load_persisted_current_league_payload,
    resolve_current_transaction_window,
)


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
        "--dataset",
        action="append",
        dest="dataset_ids",
        help="Restrict sync acquisition to one registry dataset; may be repeated.",
    )
    parser.add_argument(
        "--season",
        action="append",
        dest="seasons",
        type=int,
        help="Restrict sync or scoped materialization to one season; may be repeated.",
    )
    parser.add_argument(
        "--week",
        action="append",
        dest="weeks",
        type=int,
        help="Restrict week-scoped sync/materialization to one week; may be repeated.",
    )
    parser.add_argument(
        "--materialization-scope",
        choices=("full", "transactions"),
        default="full",
        help="Choose full League materialization or the transaction-only write scope.",
    )
    parser.add_argument(
        "--current-transaction-window",
        action="store_true",
        help=(
            "Use the source-owned current transaction window: current Sleeper week "
            "plus the previous week, bounded by the canonical NFL regular-season schedule."
        ),
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


def _target_set(values: list[int] | list[str] | None) -> set | None:
    if not values:
        return None
    return set(values)


def _load_current_instance(
    bootstrap,
    fetcher: Callable[[str], dict],
) -> SleeperLeagueInstance:
    provider_league_id = bootstrap.current_provider_league_id
    payload = fetcher(provider_league_id)
    if not isinstance(payload, dict):
        raise ValueError(
            f"Current Sleeper league payload must be an object: {provider_league_id}"
        )
    payload_league_id = str(payload.get("league_id") or "").strip()
    if payload_league_id != provider_league_id:
        raise ValueError(
            "Current Sleeper league payload identity mismatch: "
            f"expected {provider_league_id!r}, got {payload_league_id!r}"
        )
    try:
        season = int(payload.get("season"))
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Current Sleeper league payload has invalid season: {payload.get('season')!r}"
        ) from error
    if season < 1:
        raise ValueError(f"Current Sleeper league season must be positive: {season}")
    previous = str(payload.get("previous_league_id") or "").strip() or None
    return SleeperLeagueInstance(provider_league_id, season, previous, payload)


def _validate_current_window_args(args: argparse.Namespace) -> None:
    if not args.current_transaction_window:
        return
    if args.command == "validate":
        raise ValueError("--current-transaction-window does not apply to validate")
    if args.seasons or args.weeks:
        raise ValueError(
            "--current-transaction-window owns season/week targeting; do not combine it with --season/--week"
        )
    if args.command == "sync":
        requested = set(args.dataset_ids or [])
        if requested and requested != {"sleeper.transactions"}:
            raise ValueError(
                "--current-transaction-window sync supports only dataset=sleeper.transactions"
            )
    if args.command == "materialize" and args.materialization_scope != "transactions":
        raise ValueError(
            "--current-transaction-window materialization requires --materialization-scope transactions"
        )


def main() -> int:
    args = parse_args()
    _validate_current_window_args(args)
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
        if args.dataset_ids:
            raise ValueError("--dataset applies to sync acquisition, not materialization")
        if args.materialization_scope == "full" and (args.seasons or args.weeks):
            raise ValueError(
                "--season/--week materialization targeting requires "
                "--materialization-scope transactions"
            )

        resolver = PlayerMappingResolver.load(repo_root)
        results = []
        for bootstrap in selected:
            current_window = None
            seasons = _target_set(args.seasons)
            weeks = _target_set(args.weeks)
            if args.current_transaction_window:
                current_payload = load_persisted_current_league_payload(
                    repo_root,
                    bootstrap.current_provider_league_id,
                )
                current_window = resolve_current_transaction_window(
                    repo_root,
                    bootstrap.canonical_league_id,
                    bootstrap.current_provider_league_id,
                    current_payload,
                )
                seasons = {current_window["Season"]}
                weeks = set(current_window["Weeks"])

            if args.materialization_scope == "transactions":
                outputs = plan_transaction_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                    seasons=seasons,
                    weeks=weeks,
                )
            else:
                outputs = plan_canonical_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                )
            result = persist_canonical_outputs(outputs)
            item = {
                "CanonicalLeagueID": bootstrap.canonical_league_id,
                "MaterializationScope": args.materialization_scope,
                "Dependencies": (
                    list(TRANSACTION_SCOPE_DEPENDENCIES)
                    if args.materialization_scope == "transactions"
                    else []
                ),
                **result,
            }
            if current_window is not None:
                item["CurrentTransactionWindow"] = current_window
            results.append(item)
        print(json.dumps({"Leagues": results}, indent=2))
        return 0

    lineage_fetcher = (
        persisted_sleeper_fetcher(repo_root)
        if args.offline
        else fetch_sleeper_league
    )
    results = []
    for bootstrap in selected:
        if args.current_transaction_window:
            current_instance = _load_current_instance(bootstrap, lineage_fetcher)
            current_window = resolve_current_transaction_window(
                repo_root,
                bootstrap.canonical_league_id,
                bootstrap.current_provider_league_id,
                current_instance.payload,
            )
            plans = plan_raw_acquisition(
                repo_root,
                [current_instance],
                registry,
                fetch_sleeper_json,
                force=args.force,
                offline=args.offline,
                dataset_ids={"sleeper.league", "sleeper.transactions"},
                seasons={current_window["Season"]},
                weeks=set(current_window["Weeks"]),
            )
            raw = persist_raw_plans(plans)
            results.append(
                {
                    "CanonicalLeagueID": bootstrap.canonical_league_id,
                    "CurrentProviderLeagueID": bootstrap.current_provider_league_id,
                    "AcquisitionScope": "current-transactions",
                    "Dependencies": ["sleeper.league", "sleeper.transactions"],
                    "CurrentTransactionWindow": current_window,
                    **raw,
                }
            )
            continue

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
            dataset_ids=_target_set(args.dataset_ids),
            seasons=_target_set(args.seasons),
            weeks=_target_set(args.weeks),
        )
        raw = persist_raw_plans(plans)
        results.append(combine_sync_results(identity, raw))

    print(json.dumps({"Leagues": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
