#!/usr/bin/env python3
"""Validate Fantasy Management podcast episode packages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from episode_package_validation_common import (
    RegistryIndex, Report, load_and_validate_registry, repo_root_from_script,
)
from episode_package_validation import validate_episode_package


def discover_episode_packages(root: Path) -> list[Path]:
    return [path.parent for path in sorted((root / "fantasy-management/sources/podcasts").glob("*/episodes/*/*/index.json"))]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Fantasy Management podcast episode packages.")
    parser.add_argument("packages", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--schema", default=None)
    parser.add_argument("--skip-schema", action="store_true")
    parser.add_argument("--skip-registry", action="store_true")
    parser.add_argument("--warnings-as-errors", action="store_true")
    parser.add_argument("--json-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    schema = Path(args.schema).resolve() if args.schema else root / "fantasy-management/_ai/schemas/episode-takes.schema.json"
    report = Report()
    packages = discover_episode_packages(root) if args.all else [Path(value).resolve() for value in args.packages]
    if not packages:
        print("No episode packages selected. Pass package paths or use --all.", file=sys.stderr)
        return 2
    registry = load_and_validate_registry(root, report, args.skip_registry)
    for package in packages:
        if not package.exists():
            report.error(package, "Episode package directory does not exist.")
        else:
            validate_episode_package(package, root, schema, registry, report, args.skip_schema, args.skip_registry)
    print(json.dumps(report.to_json(), indent=2, ensure_ascii=False) if args.json_report else "", end="") if args.json_report else report.print_text()
    return 1 if report.errors or (args.warnings_as_errors and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
