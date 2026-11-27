#!/usr/bin/env python3
"""Read-only by default; materialize one league-records snapshot per league with --write."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from data_roots import data_derived_dir, data_meta_dir
from league_metadata import list_league_ids
from league_standings_sources import manifest, manifest_seasons, current_season
from derived_data_lib.league_records import PRODUCT, SCHEMA_VERSION, MODEL_ID, build, legacy_biggest_upset


def resolve(repo_root: Path, out_root: Path, league_id: str) -> dict[str, Any]:
    lineage = manifest(repo_root, league_id)
    if lineage["CanonicalLeagueID"] != league_id:
        raise ValueError(f"{league_id}: manifest identity mismatch")
    current = current_season(lineage)
    seasons = [year for year in manifest_seasons(lineage) if year <= current]
    if current not in seasons:
        raise ValueError(f"{league_id}: current season not in manifest")
    documents = {}
    for year in seasons:
        path = out_root / "season-statistics" / league_id / f"{year}.json"
        documents[year] = json.loads(path.read_text(encoding="utf-8"))
    return build(league_id, seasons, documents)


def read_persisted(out_root: Path, league_id: str) -> dict[str, Any]:
    """Read the published shared contract, never select a record in a consumer."""
    path = out_root / PRODUCT / f"{league_id}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if (doc["Product"], doc["SchemaVersion"], doc["CanonicalLeagueID"], doc["Model"]) != (PRODUCT, SCHEMA_VERSION, league_id, MODEL_ID):
        raise ValueError(f"{league_id}: incompatible league-records snapshot")
    if not isinstance(doc["Coverage"], list) or not doc["Coverage"]:
        raise ValueError(f"{league_id}: missing league-records coverage")
    legacy_biggest_upset(doc)  # validate the required compatibility fields
    return doc


def materialize(repo_root: Path, out_root: Path, league_id: str, *, write: bool = False) -> dict[str, Any]:
    document = resolve(repo_root, out_root, league_id)
    content = json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    path = out_root / PRODUCT / f"{league_id}.json"
    changed = not path.is_file() or path.read_text(encoding="utf-8") != content
    if write and changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"Product": PRODUCT, "CanonicalLeagueID": league_id,
            "Written": int(write and changed), "WouldWrite": int(changed),
            "Document": document}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-root", type=Path)
    parser.add_argument("--league")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo_root
        out = args.out_root or data_derived_dir(root)
        leagues = [args.league] if args.league else list_league_ids(data_meta_dir(root))
        reports = [materialize(root, out, league, write=args.write) for league in leagues]
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"league-records: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(reports, indent=2, ensure_ascii=False))
    return 3 if args.check and any(r["WouldWrite"] for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
