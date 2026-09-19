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
from league_source_data_lib.draft_materialize import (
    DRAFT_DATASET_IDS,
    DRAFT_SCOPE_DEPENDENCIES,
    plan_draft_materialization,
    resolve_current_draft_season,
)
from league_source_data_lib.league_core_materialize import (
    LEAGUE_CORE_DATASET_IDS,
    LEAGUE_CORE_SCOPE_DEPENDENCIES,
    plan_league_core_materialization,
    resolve_current_league_core_season,
)
from league_source_data_lib.materialize import (
    PlayerMappingResolver,
    persist_canonical_outputs,
    plan_canonical_materialization,
)
from league_source_data_lib.matchup_materialize import (
    MATCHUP_SCOPE_DEPENDENCIES,
    plan_matchup_materialization,
    resolve_current_matchup_scope,
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
        choices=("full", "league-core", "transactions", "drafts", "matchups"),
        default="full",
        help="Choose full League materialization or a bounded League Core/transaction/draft/matchup write scope.",
    )
    parser.add_argument(
        "--current-league-core-scope",
        action="store_true",
        help=(
            "Use the source-owned current League Core scope: league metadata/settings, "
            "members, rosters and winners/losers brackets for the current Sleeper league."
        ),
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
        "--current-draft-scope",
        action="store_true",
        help=(
            "Use the source-owned current draft scope: the current Sleeper league's "
            "draft index plus every discovered draft detail, pick and traded-pick partition."
        ),
    )
    parser.add_argument(
        "--current-matchup-scope",
        action="store_true",
        help=(
            "Use the source-owned current matchup scope: current Sleeper league evidence "
            "plus exactly the active matchup week selected by the shared current-week resolver."
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


def _validate_current_scope_args(args: argparse.Namespace) -> None:
    active_current_scopes = [
        args.current_league_core_scope,
        args.current_transaction_window,
        args.current_draft_scope,
        args.current_matchup_scope,
    ]
    if sum(bool(value) for value in active_current_scopes) > 1:
        raise ValueError("Current League source scopes are mutually exclusive")

    if args.current_league_core_scope:
        if args.command == "validate":
            raise ValueError("--current-league-core-scope does not apply to validate")
        if args.seasons or args.weeks:
            raise ValueError(
                "--current-league-core-scope owns season targeting; do not combine it with --season/--week"
            )
        if args.command == "sync" and args.dataset_ids:
            raise ValueError(
                "--current-league-core-scope owns its dataset set; do not combine it with --dataset"
            )
        if args.command == "materialize" and args.materialization_scope != "league-core":
            raise ValueError(
                "--current-league-core-scope materialization requires --materialization-scope league-core"
            )

    if args.current_transaction_window:
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

    if args.current_draft_scope:
        if args.command == "validate":
            raise ValueError("--current-draft-scope does not apply to validate")
        if args.seasons or args.weeks:
            raise ValueError(
                "--current-draft-scope owns season targeting; do not combine it with --season/--week"
            )
        if args.command == "sync" and args.dataset_ids:
            raise ValueError(
                "--current-draft-scope owns its draft dataset set; do not combine it with --dataset"
            )
        if args.command == "materialize" and args.materialization_scope != "drafts":
            raise ValueError(
                "--current-draft-scope materialization requires --materialization-scope drafts"
            )

    if args.current_matchup_scope:
        if args.command == "validate":
            raise ValueError("--current-matchup-scope does not apply to validate")
        if args.seasons or args.weeks:
            raise ValueError(
                "--current-matchup-scope owns season/week targeting; do not combine it with --season/--week"
            )
        if args.command == "sync" and args.dataset_ids:
            raise ValueError(
                "--current-matchup-scope owns its dataset set; do not combine it with --dataset"
            )
        if args.command == "materialize" and args.materialization_scope != "matchups":
            raise ValueError(
                "--current-matchup-scope materialization requires --materialization-scope matchups"
            )


def main() -> int:
    args = parse_args()
    _validate_current_scope_args(args)
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
                "--season/--week materialization targeting requires a bounded materialization scope"
            )
        if args.materialization_scope in {"league-core", "drafts"} and args.weeks:
            raise ValueError(
                f"--week does not apply to {args.materialization_scope} materialization"
            )

        resolver = PlayerMappingResolver.load(repo_root)
        results = []
        for bootstrap in selected:
            current_league_core_scope = None
            current_window = None
            current_draft_scope = None
            current_matchup_scope = None
            seasons = _target_set(args.seasons)
            weeks = _target_set(args.weeks)
            if args.current_league_core_scope:
                season = resolve_current_league_core_season(
                    repo_root,
                    bootstrap.canonical_league_id,
                    bootstrap.current_provider_league_id,
                )
                current_payload = load_persisted_current_league_payload(
                    repo_root,
                    bootstrap.current_provider_league_id,
                )
                current_matchup_scope = resolve_current_matchup_scope(
                    repo_root,
                    bootstrap.canonical_league_id,
                    bootstrap.current_provider_league_id,
                    current_payload,
                )
                seasons = {season}
                weeks = {current_matchup_scope["CurrentWeek"]}
                current_league_core_scope = {
                    "Season": season,
                    "ProviderLeagueID": bootstrap.current_provider_league_id,
                    "CurrentMatchupWeek": current_matchup_scope["CurrentWeek"],
                }
            elif args.current_transaction_window:
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
            elif args.current_draft_scope:
                season = resolve_current_draft_season(
                    repo_root,
                    bootstrap.canonical_league_id,
                    bootstrap.current_provider_league_id,
                )
                seasons = {season}
                current_draft_scope = {
                    "Season": season,
                    "ProviderLeagueID": bootstrap.current_provider_league_id,
                }
            elif args.current_matchup_scope:
                current_payload = load_persisted_current_league_payload(
                    repo_root,
                    bootstrap.current_provider_league_id,
                )
                current_matchup_scope = resolve_current_matchup_scope(
                    repo_root,
                    bootstrap.canonical_league_id,
                    bootstrap.current_provider_league_id,
                    current_payload,
                )
                seasons = {current_matchup_scope["Season"]}
                weeks = {current_matchup_scope["CurrentWeek"]}

            if args.materialization_scope == "league-core":
                outputs = plan_league_core_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                    seasons=seasons,
                )
                dependencies = list(LEAGUE_CORE_SCOPE_DEPENDENCIES)
            elif args.materialization_scope == "transactions":
                outputs = plan_transaction_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                    seasons=seasons,
                    weeks=weeks,
                )
                dependencies = list(TRANSACTION_SCOPE_DEPENDENCIES)
            elif args.materialization_scope == "drafts":
                outputs = plan_draft_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                    seasons=seasons,
                )
                dependencies = list(DRAFT_SCOPE_DEPENDENCIES)
            elif args.materialization_scope == "matchups":
                outputs = plan_matchup_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                    seasons=seasons,
                    weeks=weeks,
                )
                dependencies = list(MATCHUP_SCOPE_DEPENDENCIES)
            else:
                outputs = plan_canonical_materialization(
                    repo_root,
                    bootstrap.canonical_league_id,
                    registry,
                    resolver,
                )
                dependencies = []
            result = persist_canonical_outputs(outputs)
            item = {
                "CanonicalLeagueID": bootstrap.canonical_league_id,
                "MaterializationScope": args.materialization_scope,
                "Dependencies": dependencies,
                **result,
            }
            if current_league_core_scope is not None:
                item["CurrentLeagueCoreScope"] = current_league_core_scope
            if current_window is not None:
                item["CurrentTransactionWindow"] = current_window
            if current_draft_scope is not None:
                item["CurrentDraftScope"] = current_draft_scope
            if current_matchup_scope is not None:
                item["CurrentMatchupScope"] = current_matchup_scope
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
        if args.current_league_core_scope:
            current_instance = _load_current_instance(bootstrap, lineage_fetcher)
            manifest_season = resolve_current_league_core_season(
                repo_root,
                bootstrap.canonical_league_id,
                bootstrap.current_provider_league_id,
            )
            if current_instance.season != manifest_season:
                raise ValueError(
                    "Current Sleeper league season does not match canonical manifest for League Core scope: "
                    f"{current_instance.season} != {manifest_season}"
                )
            current_matchup_scope = resolve_current_matchup_scope(
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
                dataset_ids=set(LEAGUE_CORE_DATASET_IDS),
                seasons={manifest_season},
                weeks={current_matchup_scope["CurrentWeek"]},
            )
            raw = persist_raw_plans(plans)
            results.append(
                {
                    "CanonicalLeagueID": bootstrap.canonical_league_id,
                    "CurrentProviderLeagueID": bootstrap.current_provider_league_id,
                    "AcquisitionScope": "current-league-core",
                    "Dependencies": list(LEAGUE_CORE_DATASET_IDS),
                    "CurrentLeagueCoreScope": {
                        "Season": manifest_season,
                        "ProviderLeagueID": bootstrap.current_provider_league_id,
                        "CurrentMatchupWeek": current_matchup_scope["CurrentWeek"],
                    },
                    **raw,
                }
            )
            continue

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

        if args.current_draft_scope:
            current_instance = _load_current_instance(bootstrap, lineage_fetcher)
            manifest_season = resolve_current_draft_season(
                repo_root,
                bootstrap.canonical_league_id,
                bootstrap.current_provider_league_id,
            )
            if current_instance.season != manifest_season:
                raise ValueError(
                    "Current Sleeper league season does not match canonical manifest for draft scope: "
                    f"{current_instance.season} != {manifest_season}"
                )
            plans = plan_raw_acquisition(
                repo_root,
                [current_instance],
                registry,
                fetch_sleeper_json,
                force=args.force,
                offline=args.offline,
                dataset_ids=set(DRAFT_DATASET_IDS),
                seasons={manifest_season},
            )
            raw = persist_raw_plans(plans)
            results.append(
                {
                    "CanonicalLeagueID": bootstrap.canonical_league_id,
                    "CurrentProviderLeagueID": bootstrap.current_provider_league_id,
                    "AcquisitionScope": "current-drafts",
                    "Dependencies": list(DRAFT_DATASET_IDS),
                    "CurrentDraftScope": {
                        "Season": manifest_season,
                        "ProviderLeagueID": bootstrap.current_provider_league_id,
                    },
                    **raw,
                }
            )
            continue

        if args.current_matchup_scope:
            current_instance = _load_current_instance(bootstrap, lineage_fetcher)
            current_matchup_scope = resolve_current_matchup_scope(
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
                dataset_ids={"sleeper.league", "sleeper.matchups"},
                seasons={current_matchup_scope["Season"]},
                weeks={current_matchup_scope["CurrentWeek"]},
            )
            raw = persist_raw_plans(plans)
            results.append(
                {
                    "CanonicalLeagueID": bootstrap.canonical_league_id,
                    "CurrentProviderLeagueID": bootstrap.current_provider_league_id,
                    "AcquisitionScope": "current-matchups",
                    "Dependencies": ["sleeper.league", "sleeper.matchups"],
                    "CurrentMatchupScope": current_matchup_scope,
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
