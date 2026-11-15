#!/usr/bin/env python3
"""Read-only preview of one NFL Game detail from existing canonical evidence.

No persistent or published data. Long gains are NOT full play-by-play.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.nfl_game_detail import build_nfl_game_detail
from derived_data_lib.nfl_game_detail_core import build_nfl_game_detail_core


def preview(
    repo_root: Path, season: int, game_id: str,
    pbp_csv_gz: Path | None = None, expected_sha256: str | None = None,
    *, core_v1: bool = False,
) -> dict:
    index_path = repo_root / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json"
    if not index_path.is_file():
        raise ValueError(f"Canonical nfl-games season unavailable: {season}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    matches = [row for row in index.get("Games", []) if row.get("GameID") == game_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or duplicated canonical GameID: {game_id}")
    week = matches[0].get("Week")
    if type(week) is not int or not 1 <= week <= 25:
        raise ValueError(f"Invalid game week for {game_id}")
    if core_v1:
        if pbp_csv_gz is not None or expected_sha256 is not None:
            raise ValueError("--core-v1 cannot be combined with original PBP flags")
        nfl_source = repo_root / DATA_SOURCE_ROOT / "nfl"
        def optional_partition(name: str) -> dict | None:
            path = nfl_source / name / f"{season}" / f"{week:02d}.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        return build_nfl_game_detail_core(
            index, game_id, optional_partition("player-stats"),
            optional_partition("snap-counts"),
        )
    if pbp_csv_gz is not None:
        # PBP-first mode: deliberately no player-stats or snap-count dependencies.
        if not pbp_csv_gz.is_file():
            raise ValueError(f"Original PBP gzip unavailable: {pbp_csv_gz}")
        with pbp_csv_gz.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if expected_sha256 is not None and expected_sha256.lower() != digest:
            raise ValueError("Original PBP asset SHA256 does not match requested digest")
        rows, scan = _load_original_game_rows(pbp_csv_gz, game_id)
        # Detect an asset changing between digest verification and stream replay.
        with pbp_csv_gz.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != digest:
                raise ValueError("Original PBP compressed asset changed during replay")
        result = build_nfl_game_detail(
            index, game_id, pbp_rows=rows, pbp_asset_sha256=digest,
        )
        validated_plays = result["PlayByPlay"]["OriginalPlays"]["Plays"]
        result["PlayByPlay"]["OriginalPlays"]["SourceReadAudit"] = {
            **scan,
            "GzipStreamReadToEOF": True,
            "ExpectedSHA256Matched": True if expected_sha256 is not None else None,
            "UniqueValidatedPlayIDs": len(validated_plays),
            "FirstPlayID": validated_plays[0]["PlayID"],
            "LastPlayID": validated_plays[-1]["PlayID"],
            "PlayIDsAreNotRequiredToBeConsecutive": True,
        }
        return result
    if expected_sha256 is not None:
        raise ValueError("--expected-sha256 requires --pbp-csv-gz")
    nfl_source = repo_root / DATA_SOURCE_ROOT / "nfl"

    def optional_json(path: Path) -> dict | None:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    gains = optional_json(nfl_source / "player-game-long-gains" / f"{season}.json")
    stats = optional_json(nfl_source / "player-stats" / f"{season}" / f"{week:02d}.json")
    snaps = optional_json(nfl_source / "snap-counts" / f"{season}" / f"{week:02d}.json")
    return build_nfl_game_detail(index, game_id, gains, stats, snaps)


_PBP_REQUIRED_COLUMNS = {
    "game_id", "play_id", "season", "season_type", "week",
    "home_team", "away_team", "qtr", "down", "ydstogo", "yardline_100",
    "posteam", "defteam", "play_type", "desc", "epa", "success",
}


def _load_original_game_rows(
    path: Path, game_id: str,
) -> tuple[list[dict[str, str]], dict]:
    """Fully scan the original gzip CSV, retaining only the requested GameID.

    A successful EOF establishes gzip/CSV stream consumption, NOT that nflverse
    has complete play evidence for this game or season.
    """
    result: list[dict[str, str]] = []
    game_ids: set[str] = set()
    season_row_count = 0
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not fields or any(not f for f in fields):
            raise ValueError("Malformed/duplicate original PBP CSV headers")
        missing = sorted(_PBP_REQUIRED_COLUMNS - set(fields))
        if missing:
            raise ValueError("Missing original PBP columns: " + ", ".join(missing))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed original PBP CSV row width")
            season_row_count += 1
            key = (row.get("game_id") or "").strip()
            if key:
                game_ids.add(key)
            if key == game_id:
                result.append(row)
    if not result:
        raise ValueError(f"Original PBP GameID not found: {game_id}")
    return result, {
        "SeasonSourceRowsScanned": season_row_count,
        "DistinctGameIDsInAsset": len(game_ids),
        "CsvColumnCount": len(fields),
        "MatchedGameRowCount": len(result),
        "CompressedAssetBytes": path.stat().st_size,
        "OriginalAssetCompletenessVerified": False,
        "GamePlayCompletenessVerified": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--game-id", required=True)
    parser.add_argument(
        "--pbp-csv-gz", type=Path, default=None,
        help="Local original nflverse play_by_play_<season>.csv.gz; no network/download/write",
    )
    parser.add_argument(
        "--expected-sha256", default=None,
        help="Optional expected SHA256 of the original compressed season asset",
    )
    parser.add_argument(
        "--core-v1", action="store_true",
        help="Read-only versioned Shared Derived GameDetail core candidate; no writes",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="PBP-only compact stdout summary: source read audit and provisional metrics",
    )
    args = parser.parse_args()
    try:
        if args.summary and (args.pbp_csv_gz is None or args.core_v1):
            raise ValueError("--summary requires --pbp-csv-gz without --core-v1")
        document = preview(
            args.repo_root.resolve(), args.season, args.game_id,
            args.pbp_csv_gz, args.expected_sha256, core_v1=args.core_v1,
        )
    except (OSError, ValueError, TypeError, KeyError, EOFError, csv.Error,
            json.JSONDecodeError) as error:
        print(f"nfl_game_detail_preview failed: {error}", file=sys.stderr)
        return 1
    if args.summary:
        original = document["PlayByPlay"]["OriginalPlays"]
        document = {
            "SchemaVersion": document["SchemaVersion"],
            "Season": document["Season"],
            "GameID": document["GameID"],
            "GameFinal": document["Game"].get("Final"),
            "FullPlayByPlayAvailable": document["PlayByPlay"]["FullPlayByPlayAvailable"],
            "SourceStatus": original["Status"],
            "CompletenessVerified": original["CompletenessVerified"],
            "PlayCount": original["PlayCount"],
            "SourceAssetSHA256": original["SourceAssetSHA256"],
            "SourceReadAudit": original["SourceReadAudit"],
            "Analytics": original["Analytics"],
        }
    print(json.dumps(document, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
