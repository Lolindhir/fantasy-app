#!/usr/bin/env python3
"""Read-only preview of one NFL Game detail from existing canonical evidence.

No persistent or published data. Long gains are NOT full play-by-play.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.nfl_game_detail import build_nfl_game_detail


def preview(repo_root: Path, season: int, game_id: str) -> dict:
    index_path = repo_root / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json"
    if not index_path.is_file():
        raise ValueError(f"Canonical nfl-games season unavailable: {season}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    source_path = repo_root / DATA_SOURCE_ROOT / "nfl" / "player-game-long-gains" / f"{season}.json"
    source = json.loads(source_path.read_text(encoding="utf-8")) if source_path.is_file() else None
    return build_nfl_game_detail(index, game_id, source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--game-id", required=True)
    args = parser.parse_args()
    try:
        document = preview(args.repo_root.resolve(), args.season, args.game_id)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"nfl_game_detail_preview failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(document, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
