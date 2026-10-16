#!/usr/bin/env python3
"""CLI of the shared external market source layer (contract: .ai-context/manual/external-source-data.yaml).

Commands:
  validate   check data-source/external-registry.json (fail-closed)
  identity   materialize the per-dataset identity index; --check only reports differences

Acquisition (sync) is added provider by provider with the migration steps of Issue #988.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from external_source import identity as identity_mod  # noqa: E402
from external_source.registry import ExternalRegistryError, get_dataset, load_registry  # noqa: E402

REPO_ROOT = TOOLS_DIR.parent


def cmd_validate(args: argparse.Namespace) -> int:
    registry = load_registry(args.repo_root)
    print(f"external-registry.json valid: {len(registry['datasets'])} datasets")
    return 0


def cmd_identity(args: argparse.Namespace) -> int:
    registry = load_registry(args.repo_root)
    datasets = [get_dataset(registry, args.dataset)] if args.dataset else registry["datasets"]
    index = identity_mod.MappingIndex.load(args.repo_root)
    differing = 0
    for dataset in datasets:
        built = identity_mod.build_identity(args.repo_root, dataset, index)
        if built is None:
            continue
        if args.check:
            path = identity_mod.dataset_dir(args.repo_root, dataset) / identity_mod.IDENTITY_FILE_NAME
            if not path.is_file() or path.read_text(encoding="utf-8") != identity_mod.render(built):
                print(f"identity index differs: {dataset['id']}")
                differing += 1
        elif identity_mod.write_if_changed(args.repo_root, dataset, built):
            print(f"identity index written: {dataset['id']}")
    return 1 if differing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    ident = sub.add_parser("identity")
    ident.add_argument("--dataset")
    ident.add_argument("--check", action="store_true")
    ident.set_defaults(func=cmd_identity)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ExternalRegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
