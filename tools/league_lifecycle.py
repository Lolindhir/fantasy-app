#!/usr/bin/env python3
"""CLI of the league lifecycle (ADR-073, Issue #1199).

Usage:
  league_lifecycle.py resolve --league nfl-reise --season 2026 [--at 2026-10-30T12:00:00Z]
  league_lifecycle.py compare --league nfl-reise [--at ...]   # shadow against the published League.json

Prints the lifecycle of the league season at the given instant as JSON. ``--at`` defaults to the current time and is
always echoed as ``AtUtc`` in the result; nothing is written. Exit code 1 with a message on stderr when an input is
missing or contradicting (no status is guessed).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_lifecycle import LifecycleError, parse_instant, resolve_lifecycle  # noqa: E402


# League.json field -> lifecycle result key (identical names; compared exactly, values as published).
COMPARED_FIELDS = (
    "Status", "Phase", "CurrentWeek", "FinalScoredWeek", "LastLeagueWeek", "PlayoffStartWeek", "PlayoffStart",
    "SeasonKickoff", "TradesOpen", "TradeReviewDays", "TradeDeadlineWeek", "WaiversOpen", "NextWaiverRun", "CutsAllowed",
)


def compare_with_published(repo_root: Path, league_id: str, at_text: str | None) -> tuple[list[str], dict]:
    """Differences between the lifecycle at ``AtUtc`` and the published League.json (shadow of ADR-073).

    ``AtUtc`` defaults to Timestamps.json League, the last semantic League update; use ``--at`` to override.
    """
    data = repo_root / "public" / "data"
    try:
        published = json.loads((data / "League.json").read_text(encoding="utf-8-sig"))
        stamp = json.loads((data / "Timestamps.json").read_text(encoding="utf-8-sig"))["League"]
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise LifecycleError(f"Published League.json/Timestamps.json unusable: {error}") from error
    at = parse_instant(at_text or stamp, "--at" if at_text else "Timestamps.League")
    result = resolve_lifecycle(repo_root, league_id, int(published["Season"]), at)
    differences = []
    for field in COMPARED_FIELDS:
        if field not in published:
            differences.append(f"{field}: missing in League.json")
        elif published[field] != result[field]:
            differences.append(f"{field}: published {published[field]!r} != lifecycle {result[field]!r}")
    return differences, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve", help="print the lifecycle at an instant")
    resolve.add_argument("--league", required=True)
    resolve.add_argument("--season", type=int, required=True)
    resolve.add_argument("--at", help="ISO instant with Z or offset; default: now")
    resolve.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    compare = sub.add_parser("compare", help="shadow comparison against the published League.json")
    compare.add_argument("--league", required=True)
    compare.add_argument("--at", help="ISO instant; default: Timestamps.json League")
    compare.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if args.command == "compare":
        try:
            differences, result = compare_with_published(args.repo_root, args.league, args.at)
        except LifecycleError as error:
            print(f"league_lifecycle: {error}", file=sys.stderr)
            return 1
        if differences:
            print(f"league_lifecycle compare: {len(differences)} difference(s) at {result['AtUtc']}")
            for line in differences:
                print(f"  {line}")
            return 2
        print(f"league_lifecycle compare: identical for {len(COMPARED_FIELDS)} fields at {result['AtUtc']}")
        return 0
    try:
        at = parse_instant(args.at, "--at") if args.at else datetime.now(timezone.utc)
        result = resolve_lifecycle(args.repo_root, args.league, args.season, at)
    except LifecycleError as error:
        print(f"league_lifecycle: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
