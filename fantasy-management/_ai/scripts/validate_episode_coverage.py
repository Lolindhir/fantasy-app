#!/usr/bin/env python3
"""Validate cross-file entity coverage for podcast episode packages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from episode_coverage_validation_common import Report, repo_root_from_script
from episode_coverage_validation import validate_package


def discover_episode_packages(root: Path) -> list[Path]:
    return [path.parent for path in sorted((root / "fantasy-management/sources/podcasts").glob("*/episodes/*/*/index.json"))]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate podcast mention coverage.")
    parser.add_argument("packages", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--index-schema", default=None)
    parser.add_argument("--mentions-schema", default=None)
    parser.add_argument("--no-legacy-warnings", action="store_true")
    parser.add_argument("--warnings-as-errors", action="store_true")
    parser.add_argument("--json-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    index_schema = Path(args.index_schema).resolve() if args.index_schema else root / "fantasy-management/_ai/schemas/episode-index.schema.json"
    mentions_schema = Path(args.mentions_schema).resolve() if args.mentions_schema else root / "fantasy-management/_ai/schemas/episode-mentions.schema.json"
    report = Report()
    packages = discover_episode_packages(root) if args.all else [Path(value).resolve() for value in args.packages]
    if not packages:
        print("No episode packages selected. Pass package paths or use --all.", file=sys.stderr)
        return 2
    for package in packages:
        if not package.exists():
            report.error(package, "Episode package directory does not exist.")
        else:
            validate_package(package, root, index_schema, mentions_schema, report, not args.no_legacy_warnings)
    print(json.dumps(report.to_json(), indent=2, ensure_ascii=False) if args.json_report else "", end="") if args.json_report else report.print_text()
    return 1 if report.errors or (args.warnings_as_errors and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
