#!/usr/bin/env python3
"""Read-only clean-root recovery probe for existing valuation and LeagueHistory (#471).

This is NOT a publisher or an all-product restore implementation. It detects
dependencies on previously generated data before activating a weekly writer.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from derived_data import (
    LEAGUE_DRAFTS, LEAGUE_TRANSACTIONS,
    materialize_league_history, materialize_player_valuation,
)

PRODUCTS = ("player-valuation", LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS)


def _files(root: Path, product: str) -> dict[str, bytes]:
    directory = root / "data-derived" / product
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in sorted(directory.rglob("*.json"))
    } if directory.is_dir() else {}


def _written(summary: dict[str, Any]) -> int:
    return sum(int(season["Written"]) for season in summary["Seasons"])


def _restore_product(
    product: str, shadow: Path, source: Path, league: str,
) -> dict[str, Any]:
    output = shadow / "data-derived"

    def build() -> dict[str, Any]:
        if product == "player-valuation":
            return materialize_player_valuation(
                shadow, output, league, None, False,
            )
        return materialize_league_history(shadow, output, league, product, None, False)

    try:
        initial = build()
        first = _files(shadow, product)
        if not first:
            raise ValueError("Materializer produced no product snapshots")
        second = build()
        repeated = _files(shadow, product)
        second_writes = _written(second)
        existing = _files(source, product)
        mismatches = sorted(k for k in existing if repeated.get(k) != existing[k])
        stable = second_writes == 0 and first == repeated
        hold_rows = sum(int(x.get("HeldRowsAcrossSnapshots", 0)) for x in initial["Seasons"])
        result: dict[str, Any] = {
            "Status": "ready" if stable and not mismatches else "blocked",
            "RebuiltCount": len(first),
            "WouldAddCount": len(set(first) - set(existing)),
            "PreviouslyPublishedCount": len(existing),
            "ExistingMismatchCount": len(mismatches),
            "ExistingMismatchExamples": mismatches[:12],
            "SecondPassWrites": second_writes,
            "SecondPassByteIdentical": first == repeated,
            "HeldRowsAcrossSnapshots": hold_rows,
        }
        if not stable:
            result["Reason"] = "Second pass changed reconstructed output"
        elif mismatches:
            result["Reason"] = "Clean-root output differs from previously published data"
        return result
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        return {"Status": "blocked", "Reason": str(exc)}


def audit(repo_root: Path, *, league: str = "nfl-reise") -> dict[str, Any]:
    """Regenerate selected products with NO existing Derived or App files as inputs.

    Only canonical data-source and data-meta are visible in the temporary root.
    Live repository data-derived, public/data and workflow state remain untouched.
    """
    source = repo_root.resolve()
    for name in ("data-source", "data-meta"):
        if not (source / name).is_dir():
            raise ValueError(f"Missing required canonical root: {name}")
    with tempfile.TemporaryDirectory(prefix="derived-clean-root-audit-") as tmp:
        shadow = Path(tmp)
        for name in ("data-source", "data-meta"):
            (shadow / name).symlink_to(source / name, target_is_directory=True)
        (shadow / "public/data").mkdir(parents=True)
        (shadow / "data-derived").mkdir()
        results = {
            product: _restore_product(product, shadow, source, league)
            for product in PRODUCTS
        }
    return {
        "Mode": "source-only-clean-root-probe",
        "League": league,
        "ReadOnly": True,
        "Published": False,
        "Scope": list(PRODUCTS),
        "Products": results,
        "BlockedProducts": sorted(k for k, v in results.items() if v["Status"] != "ready"),
        "ReadyForFullRestore": all(v["Status"] == "ready" for v in results.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default="nfl-reise")
    args = parser.parse_args()
    try:
        result = audit(args.repo_root, league=args.league)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Clean-root probe could not start: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ReadyForFullRestore"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
