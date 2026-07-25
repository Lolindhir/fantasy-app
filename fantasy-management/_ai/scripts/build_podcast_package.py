#!/usr/bin/env python3
"""Build one published podcast package deterministically from a ready work package."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from podcast_package_builder import build_published_package
from podcast_pipeline_types import PipelineDataError, repo_root_from_script


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a published podcast package from an incremental work package.")
    parser.add_argument("work_package")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--json-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    output = Path(args.output).resolve() if args.output else None
    try:
        result = build_published_package(
            Path(args.work_package).resolve(),
            root,
            output,
            replace_existing=args.replace_existing,
        )
    except PipelineDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    payload = {
        "output_dir": result.output_dir.as_posix(),
        "take_count": result.take_count,
        "mention_count": result.mention_count,
        "section_count": result.section_count,
    }
    if args.json_report:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            "OK: built podcast package at "
            f"{result.output_dir.as_posix()} "
            f"({result.take_count} take(s), {result.mention_count} mention(s), {result.section_count} section(s))."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
