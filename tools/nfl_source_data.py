#!/usr/bin/env python3
"""Synchronize provider NFL data and materialize provider-independent identities/draft facts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nfl_source_data_lib.common import load_json, load_registry, sync_dataset
from nfl_source_data_lib.materialize import materialize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sync", "materialize", "audit"), nargs="?", default="sync")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dataset", action="append", dest="datasets", help="Restrict sync to a dataset id; may be repeated")
    parser.add_argument("--force", action="store_true", help="Replace raw files even when their content hash is unchanged")
    parser.add_argument("--offline", action="store_true", help="Do not fetch; validate and use already persisted raw files")
    parser.add_argument("--raw-only", action="store_true", help="For sync, stop after validated provider raw data is persisted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    registry = load_registry(repo_root)
    datasets = {dataset.id: dataset for dataset in registry}

    if args.command == "audit":
        audit_path = repo_root / "source-data/audits/nfl-source-data-audit.json"
        audit = load_json(audit_path)
        if audit is None:
            raise FileNotFoundError(
                f"No materialized audit exists at {audit_path}; run materialize or sync first."
            )
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        return 0

    if args.raw_only and args.command != "sync":
        raise ValueError("--raw-only is only valid with the sync command")

    if args.command == "sync":
        requested = set(args.datasets or [])
        unknown = requested - set(datasets)
        if unknown:
            raise ValueError(f"Unknown dataset id(s): {', '.join(sorted(unknown))}")
        selected = [dataset for dataset in registry if not requested or dataset.id in requested]
        for dataset in selected:
            result = sync_dataset(dataset, force=args.force, offline=args.offline)
            print(f"{dataset.id}: {result['status']} ({result['rowCount']} rows)")
        if args.raw_only:
            print("canonical materialization skipped: --raw-only requested")
            return 0
        if not all(dataset.raw_path.exists() for dataset in registry):
            print("materialization skipped: not all registered raw datasets are available")
            return 0

    result = materialize(repo_root, datasets)
    if args.command == "sync":
        print(f"canonical identities: {result['identityCount']}")
        print(f"provider mappings: {result['providerMappingCount']}")
        print(f"provider mapping conflicts: {result['providerMappingConflictCount']}")
        print(f"draft seasons: {result['draftSeasonCount']}")
        coverage = result["audit"]["draftStatusCoverage"]
        print("draft coverage: " + ", ".join(f"{key}={value}" for key, value in sorted(coverage.items())))
    else:
        print(json.dumps({key: value for key, value in result.items() if key != "audit"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
