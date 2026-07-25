#!/usr/bin/env python3
"""Validate incremental podcast extraction work packages."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from podcast_pipeline_types import PipelineReport, repo_root_from_script
from podcast_work_validation import validate_work_package


def discover_work_packages(root: Path) -> list[Path]:
    base = root / "fantasy-management/podcast-work"
    return [path.parent for path in sorted(base.glob("*/*/*/work-status.json"))]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate incremental podcast extraction work packages.")
    parser.add_argument("packages", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--warnings-as-errors", action="store_true")
    parser.add_argument("--json-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    packages = discover_work_packages(root) if args.all else [Path(value).resolve() for value in args.packages]
    if not packages:
        print("No podcast work packages selected. Pass package paths or use --all.", file=sys.stderr)
        return 2
    report = PipelineReport()
    for package in packages:
        if not package.exists():
            report.error(package, "Podcast work package directory does not exist.")
            continue
        validate_work_package(package, root, report, require_ready=args.require_ready)
    if args.json_report:
        print(json.dumps(report.to_json(), indent=2, ensure_ascii=False))
    else:
        report.print_text()
    return 1 if report.errors or (args.warnings_as_errors and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
