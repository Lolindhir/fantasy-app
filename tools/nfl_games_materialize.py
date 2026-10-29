#!/usr/bin/env python3
"""Global NFL Game Shared-Derived materializer (#1077).

Read-only by default; --write is a deliberate opt-in and is NOT wired into a
workflow. Inputs are only season-partitioned canonical NFL Source facts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.nfl_games import build_nfl_games

EXIT_DIFFERENT = 3


def _load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Source unavailable: {path}")
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"Source not an object: {path}")
    return payload


def materialize(
    repo_root: Path,
    season: int,
    *,
    out_root: Path | None = None,
    write: bool = False,
) -> dict:
    source = repo_root / DATA_SOURCE_ROOT / "nfl"
    inputs = [
        _load(source / name / f"{season}.json")
        for name in ("schedules", "game-finality", "schedule-odds")
    ]
    document = build_nfl_games(*inputs)
    target = (out_root or (repo_root / DATA_DERIVED_ROOT)) / "nfl-games" / f"{season}.json"
    serialized = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    unchanged = target.is_file() and target.read_text(encoding="utf-8") == serialized
    if write and not unchanged:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    return {
        "Product": "nfl-games",
        "Season": season,
        "GameCount": len(document["Games"]),
        "WithCompleteMarketLines": sum(
            1 for game in document["Games"]
            if game["Market"]["ImpliedHomePoints"] is not None
        ),
        "OutputPath": str(target),
        "Unchanged": unchanged,
        "Written": bool(write and not unchanged),
        "WouldWrite": not unchanged,
    }


def discover_seasons(repo_root: Path) -> list[int]:
    base = repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules"
    seasons = sorted({int(p.stem) for p in base.glob("*.json") if p.stem.isdigit()})
    if not seasons:
        raise ValueError("No canonical NFL schedule seasons discovered")
    return seasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-root", type=Path, help="override Shared Derived output root (e.g. isolated test dir)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--season", type=int, action="append", help="season to materialize, repeatable")
    group.add_argument("--all-seasons", action="store_true", help="discover seasons from canonical source schedules")
    parser.add_argument("--write", action="store_true", help="persist validated output (opt in)")
    parser.add_argument("--check", action="store_true", help="read-only; exit 3 if a partition differs")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    try:
        root = args.repo_root.resolve()
        seasons = discover_seasons(root) if args.all_seasons else sorted(set(args.season))
        # Preflight all requested seasons before touching any output.
        previews = [materialize(root, season, out_root=args.out_root) for season in seasons]
        if args.write:
            results = [materialize(root, season, out_root=args.out_root, write=True)
                       for season in seasons]
        else:
            results = previews
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"nfl_games_materialize failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"Results": results}, ensure_ascii=False, indent=2))
    return EXIT_DIFFERENT if args.check and any(r["WouldWrite"] for r in previews) else 0


if __name__ == "__main__":
    raise SystemExit(main())
