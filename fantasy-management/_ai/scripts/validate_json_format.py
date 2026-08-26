#!/usr/bin/env python3
"""Validate that JSON files use the repository's canonical pretty-print format."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class JsonFormatError(ValueError):
    """Raised when a JSON file is invalid or not canonically formatted."""


def canonical_json_text(value: Any) -> str:
    """Return the canonical repository representation for human-maintained JSON."""

    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def validate_json_format(path: Path) -> None:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise JsonFormatError(f"Missing JSON file: {path}") from exc

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonFormatError(f"JSON file is not valid UTF-8: {path}") from exc

    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JsonFormatError(f"Invalid JSON in {path}: {exc}") from exc

    expected = canonical_json_text(value)
    if text != expected:
        raise JsonFormatError(
            f"{path} is not canonically formatted. "
            "Expected UTF-8 JSON serialized with "
            "json.dumps(..., ensure_ascii=False, indent=2) plus one final newline."
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    errors: list[str] = []

    for path in args.paths:
        try:
            validate_json_format(path)
        except JsonFormatError as exc:
            errors.append(str(exc))

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
