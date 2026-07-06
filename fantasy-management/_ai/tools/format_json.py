#!/usr/bin/env python3
"""Pretty-print Fantasy Management JSON files.

Usage examples:

  python fantasy-management/_ai/tools/format_json.py \
    fantasy-management/sources/podcasts/stonedlack/episodes/2026/sl_0569.json

  python fantasy-management/_ai/tools/format_json.py \
    fantasy-management/derived/knowledge/takes/stonedlack/2026

This script is intended for manually maintained or AI-created Fantasy Management
JSON artifacts. It rewrites JSON with two-space indentation, readable line breaks,
UTF-8 output and a trailing newline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def iter_json_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*.json") if p.is_file())
        elif path.is_file() and path.suffix == ".json":
            yield path


def format_file(path: Path, *, check: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    data = json.loads(original)
    formatted = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if original == formatted:
        return False

    if check:
        print(f"would format: {path}")
        return True

    path.write_text(formatted, encoding="utf-8")
    print(f"formatted: {path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Pretty-print Fantasy Management JSON files.")
    parser.add_argument("paths", nargs="+", type=Path, help="JSON files or directories to format")
    parser.add_argument("--check", action="store_true", help="Only report files that would change")
    args = parser.parse_args()

    changed = False
    for file_path in iter_json_files(args.paths):
        changed = format_file(file_path, check=args.check) or changed

    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
