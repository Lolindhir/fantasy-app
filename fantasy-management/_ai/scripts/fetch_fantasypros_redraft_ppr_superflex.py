#!/usr/bin/env python3
"""Fetch FantasyPros Redraft PPR Superflex ECR and store a lossless snapshot.

The parser, consensus validation, CSV rendering and common field semantics are
reused from the Dynasty Superflex fetcher. This entry point owns only the
Redraft source identity, snapshot path and horizon-specific metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fetch_fantasypros_dynasty_superflex as shared

SOURCE_URL = "https://www.fantasypros.com/nfl/rankings/ppr-superflex-cheatsheets.php"
SOURCE_ID = shared.SOURCE_ID
RANKING_ID = "redraft-ppr-superflex"
RANKING_NAME = "Redraft PPR Superflex ECR"
SCHEMA_VERSION = shared.SCHEMA_VERSION
MIN_PLAYER_ROWS = shared.MIN_PLAYER_ROWS
OFFENSIVE_POSITIONS = shared.OFFENSIVE_POSITIONS
CONSENSUS_FIELDS = shared.CONSENSUS_FIELDS
CSV_FIELDS = shared.CSV_FIELDS
USER_AGENT = shared.USER_AGENT
FantasyProsFetchError = shared.FantasyProsFetchError
ANALYSIS_METADATA_FILE = (
    "fantasy-management/sources/external-rankings/fantasypros/analysis-metadata.json"
)
DIRECT_FETCHER = (
    "fantasy-management/_ai/scripts/fetch_fantasypros_redraft_ppr_superflex.py"
)

extract_ecr_data = shared.extract_ecr_data
parse_players = shared.parse_players
validate_rows = shared.validate_rows
render_csv = shared.render_csv
render_raw_json = shared.render_raw_json
atomic_write_text = shared.atomic_write_text
raw_schema_summary = shared.raw_schema_summary
consensus_field_coverage = shared.consensus_field_coverage
consensus_relationship_diagnostics = shared.consensus_relationship_diagnostics
parse_timestamp = shared.parse_timestamp


def fetch_html(url: str = SOURCE_URL, *, timeout: int = 30) -> tuple[str, dict[str, str]]:
    return shared.fetch_html(url, timeout=timeout)


def validate_source_identity(data: dict[str, Any]) -> None:
    """Fail closed when the public page is not the expected PPR Superflex draft feed."""

    source_type = str(data.get("type") or "").strip().casefold()
    ranking_type = str(data.get("ranking_type_name") or "").strip().casefold()
    observed_types = {value for value in (source_type, ranking_type) if value}
    if observed_types and observed_types.isdisjoint({"draft", "overall"}):
        raise FantasyProsFetchError(
            "Unexpected FantasyPros ranking type for Redraft PPR Superflex: "
            f"type={data.get('type')!r}, ranking_type_name={data.get('ranking_type_name')!r}"
        )

    scoring = str(data.get("scoring") or "").strip().upper()
    if scoring and scoring != "PPR":
        raise FantasyProsFetchError(
            f"Unexpected FantasyPros scoring for Redraft PPR Superflex: {scoring!r}"
        )

    position_id = str(data.get("position_id") or "").strip().upper()
    if position_id and position_id != "OP":
        raise FantasyProsFetchError(
            f"Unexpected FantasyPros position_id for Redraft PPR Superflex: {position_id!r}"
        )


def ranking_root(repo_root: Path) -> Path:
    return (
        repo_root
        / "fantasy-management"
        / "sources"
        / "external-rankings"
        / "fantasypros"
        / RANKING_ID
    )


def latest_snapshot_metadata(repo_root: Path) -> dict[str, Any] | None:
    latest_path = ranking_root(repo_root) / "latest.json"
    if not latest_path.is_file():
        return None
    try:
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        metadata_file = latest.get("metadata_file")
        if not isinstance(metadata_file, str) or not metadata_file.strip():
            return None
        metadata = json.loads((repo_root / metadata_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, AttributeError):
        return None
    return metadata if isinstance(metadata, dict) else None


def snapshot_needs_refresh(*, repo_root: Path, ecr_data: dict[str, Any]) -> bool:
    metadata = latest_snapshot_metadata(repo_root)
    if metadata is None:
        return True
    snapshot = metadata.get("snapshot")
    if not isinstance(snapshot, dict):
        return True
    if metadata.get("schema_version") != SCHEMA_VERSION:
        return True
    if metadata.get("ranking_id") != RANKING_ID:
        return True
    if snapshot.get("csv_columns") != CSV_FIELDS:
        return True
    previous_hash = snapshot.get("raw_data_sha256")
    if not isinstance(previous_hash, str) or not previous_hash:
        return True
    current_hash = hashlib.sha256(render_raw_json(ecr_data).encode("utf-8")).hexdigest()
    return current_hash != previous_hash


def raw_payload_changed(*, repo_root: Path, ecr_data: dict[str, Any]) -> bool:
    return snapshot_needs_refresh(repo_root=repo_root, ecr_data=ecr_data)


def source_published_context(data: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "sport",
        "type",
        "ranking_type_name",
        "year",
        "week",
        "position_id",
        "scoring",
        "count",
        "total_experts",
        "experts_available",
        "last_updated",
        "last_updated_ts",
    )
    return {key: data.get(key) for key in keys if key in data}


def build_metadata(
    *,
    rows: list[dict[str, Any]],
    csv_content: str,
    raw_content: str,
    ecr_data: dict[str, Any],
    fetched_at,
    response_headers: dict[str, str],
) -> dict[str, Any]:
    metadata = shared.build_metadata(
        rows=rows,
        csv_content=csv_content,
        raw_content=raw_content,
        ecr_data=ecr_data,
        fetched_at=fetched_at,
        response_headers=response_headers,
    )
    source_year = str(ecr_data.get("year") or "").strip()
    metadata.update(
        {
            "ranking_id": RANKING_ID,
            "ranking_name": RANKING_NAME,
            "official_source_url": SOURCE_URL,
            "season_label": int(source_year) if source_year.isdigit() else fetched_at.year,
            "format": {
                "dynasty": False,
                "season_scope": "single_season",
                "scoring": "ppr",
                "superflex": True,
                "fixed_two_qb": False,
                "two_qb_analysis_proxy": True,
                "te_premium": False,
                "idp_included": False,
            },
            "source_published_context": source_published_context(ecr_data),
        }
    )
    usage = metadata["analysis_usage"]
    usage.update(
        {
            "role": "Current-season external expert-consensus and win-now context",
            "value_horizon": "single_season",
            "primary_use": "current_season_lineup_value",
            "comparison_contract": ANALYSIS_METADATA_FILE,
            "league_adjustment": (
                "Use for current-season production and win-now context, not as Dynasty "
                "trade value. The Mighty Giants league starts two fixed QBs and two fixed "
                "TEs, so league-specific scarcity may still require additional QB and TE adjustments."
            ),
        }
    )
    return metadata


def write_snapshot(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    ecr_data: dict[str, Any],
    fetched_at,
    response_headers: dict[str, str],
) -> tuple[Path, Path, Path, Path]:
    root = ranking_root(repo_root)
    snapshot_date = fetched_at.date().isoformat()
    snapshot_dir = root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    raw_path = snapshot_dir / "raw-ecr-data.json"
    metadata_path = snapshot_dir / "metadata.json"
    latest_path = root / "latest.json"

    csv_content = render_csv(rows)
    raw_content = render_raw_json(ecr_data)
    metadata = build_metadata(
        rows=rows,
        csv_content=csv_content,
        raw_content=raw_content,
        ecr_data=ecr_data,
        fetched_at=fetched_at,
        response_headers=response_headers,
    )
    relative_snapshot = snapshot_dir.relative_to(repo_root).as_posix()
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_id": RANKING_ID,
        "snapshot_date": snapshot_date,
        "fetched_at": fetched_at.isoformat(),
        "snapshot_path": relative_snapshot,
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "raw_data_file": raw_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA_FILE,
        "refresh_before_value_sensitive_analysis": True,
    }

    atomic_write_text(ranking_path, csv_content)
    atomic_write_text(raw_path, raw_content)
    atomic_write_text(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    atomic_write_text(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return ranking_path, raw_path, metadata_path, latest_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=SOURCE_URL, help="Official FantasyPros URL")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--from-file", type=Path, help="Parse saved HTML instead of fetching")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root used for snapshot output",
    )
    parser.add_argument(
        "--fetched-at",
        help="Override UTC timestamp for reproducible tests (ISO-8601)",
    )
    parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Do not publish when both raw payload and normalized snapshot schema are unchanged",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.from_file:
            html = args.from_file.read_text(encoding="utf-8")
            response_headers: dict[str, str] = {}
        else:
            html, response_headers = fetch_html(args.url, timeout=args.timeout)

        data = extract_ecr_data(html)
        validate_source_identity(data)
        rows = parse_players(data)
        diagnostics = consensus_relationship_diagnostics(rows)
        mismatch_count = diagnostics["ecr_outside_expert_range_count"]
        if mismatch_count:
            print(
                f"[fantasypros:redraft] note: {mismatch_count} rows have rank_ecr "
                "outside rank_min/rank_max; source values retained",
                file=sys.stderr,
            )
        fetched_at = parse_timestamp(args.fetched_at)
        repo_root = args.repo_root.resolve()

        if args.dry_run:
            counts = Counter(row["position"] for row in rows)
            position_rank_sources = Counter(row["position_rank_source"] for row in rows)
            coverage = consensus_field_coverage(rows)
            print(
                f"FantasyPros ranking={RANKING_ID} rows={len(rows)} "
                + " ".join(f"{key}={counts[key]}" for key in sorted(counts))
                + " position_rank="
                + "/".join(
                    f"{key}:{position_rank_sources[key]}"
                    for key in sorted(position_rank_sources)
                )
                + " consensus="
                + "/".join(f"{key}:{coverage[key]}" for key in CONSENSUS_FIELDS)
                + f" ecr_outside_range:{mismatch_count}"
            )
            for row in rows[:10]:
                print({key: row[key] for key in CSV_FIELDS})
            return 0

        if args.skip_unchanged and not snapshot_needs_refresh(
            repo_root=repo_root, ecr_data=data
        ):
            print("[fantasypros:redraft] payload and normalized schema unchanged; no snapshot written")
            return 0

        paths = write_snapshot(
            repo_root=repo_root,
            rows=rows,
            ecr_data=data,
            fetched_at=fetched_at,
            response_headers=response_headers,
        )
    except (FantasyProsFetchError, OSError, ValueError) as exc:
        print(f"[fantasypros:redraft] {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
