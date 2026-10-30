#!/usr/bin/env python3
"""CLI of the Decision Windows (ADR-074, Issue #1199 section 2).

Usage:
  decision_windows.py resolve --league nfl-reise --season 2026 [--at 2026-10-30T12:00:00Z]
  decision_windows.py compare --league nfl-reise [--at ...]   # shadow against the published DecisionWindows.json

Prints the Decision Windows of the league season at the given instant as JSON. ``--at`` defaults to the current time;
nothing is written. Exit code 1 with a message on stderr when an input is missing or contradicting (nothing is guessed).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.decision_windows import DecisionWindowsError, resolve  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError, parse_instant  # noqa: E402


# D2 (Issue #1199): FirstObservedAtUtc now means "since when the status holds" (ESPN StatusSinceUtc) and may differ from
# the value the old generator carried over from its previous file. Everything else is compared exactly.
IGNORED_KEYS = ("FirstObservedAtUtc", "ObservedAtUtc", "AsOfUtc")


def diff_values(expected, actual, path: str = "") -> list[str]:
    """Exact differences between the published (expected) and the computed (actual) value, by JSON path."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        found = []
        for key in sorted(set(expected) | set(actual)):
            if key in IGNORED_KEYS:
                continue
            where = f"{path}.{key}" if path else key
            if key not in actual:
                found.append(f"{where}: missing in computed result")
            elif key not in expected:
                found.append(f"{where}: missing in published file")
            else:
                found.extend(diff_values(expected[key], actual[key], where))
        return found
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: published {len(expected)} items != computed {len(actual)}"]
        found = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            found.extend(diff_values(left, right, f"{path}[{index}]"))
        return found
    return [] if expected == actual and type(expected) is type(actual) else [f"{path}: published {expected!r} != computed {actual!r}"]


def compare_with_published(repo_root: Path, league_id: str, at_text: str | None) -> tuple[list[str], dict]:
    """Differences between the Decision Windows at ``AtUtc`` and the published DecisionWindows.json (shadow of ADR-074).

    ``AtUtc`` defaults to Timestamps.json DecisionWindows, the last semantic update; use ``--at`` to override.
    """
    data = repo_root / "public" / "data"
    try:
        published = json.loads((data / "DecisionWindows.json").read_text(encoding="utf-8-sig"))
        stamp = json.loads((data / "Timestamps.json").read_text(encoding="utf-8-sig"))["DecisionWindows"]
        season = int(published["Season"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise DecisionWindowsError(f"Published DecisionWindows.json/Timestamps.json unusable: {error}") from error
    at = parse_instant(at_text or stamp, "--at" if at_text else "Timestamps.DecisionWindows")
    result = resolve(repo_root, league_id, season, at)
    return diff_values(published, result), result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    resolve_parser = sub.add_parser("resolve", help="print the Decision Windows at an instant")
    resolve_parser.add_argument("--league", required=True)
    resolve_parser.add_argument("--season", type=int, required=True)
    resolve_parser.add_argument("--at", help="ISO instant with Z or offset; default: now")
    resolve_parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    compare_parser = sub.add_parser("compare", help="shadow comparison against the published DecisionWindows.json")
    compare_parser.add_argument("--league", required=True)
    compare_parser.add_argument("--at", help="ISO instant; default: Timestamps.json DecisionWindows")
    compare_parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if args.command == "compare":
        try:
            differences, result = compare_with_published(args.repo_root, args.league, args.at)
        except (DecisionWindowsError, LifecycleError) as error:
            print(f"decision_windows compare: {error}", file=sys.stderr)
            return 1
        if differences:
            print(f"decision_windows compare: {len(differences)} difference(s) at {result['AsOfUtc']}")
            for line in differences[:50]:
                print(f"  {line}")
            return 1
        print(f"decision_windows compare: identical at {result['AsOfUtc']} (ignored: {', '.join(IGNORED_KEYS)})")
        return 0
    try:
        at = parse_instant(args.at, "--at") if args.at else datetime.now(timezone.utc)
        result = resolve(args.repo_root, args.league, args.season, at)
    except (DecisionWindowsError, LifecycleError) as error:
        print(f"decision_windows: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
