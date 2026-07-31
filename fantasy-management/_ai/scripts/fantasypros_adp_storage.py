"""Storage and retention helpers for FantasyPros ADP snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fantasypros_adp_core import (
    ACTUAL_LEAGUE_TEAM_COUNT,
    ANALYSIS_METADATA,
    CSV_FIELDS,
    DEFAULT_RETENTION_COUNT,
    DIRECT_FETCHER,
    SCHEMA_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    SOURCE_ROOT,
)


def render_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({field: row.get(field, "") for field in CSV_FIELDS} for row in rows)
    return output.getvalue()


def render_raw(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def ranking_root(repo_root: Path, config: dict[str, Any]) -> Path:
    return repo_root / SOURCE_ROOT / config["ranking_id"]


def snapshot_dates(root: Path) -> list[str]:
    snapshots = root / "snapshots"
    if not snapshots.is_dir():
        return []
    return sorted(
        child.name
        for child in snapshots.iterdir()
        if child.is_dir() and (child / "ranking.csv").is_file()
    )


def prune_snapshots(root: Path, retention_count: int) -> list[str]:
    dates = snapshot_dates(root)
    removed: list[str] = []
    for date in dates[:-retention_count]:
        shutil.rmtree(root / "snapshots" / date)
        removed.append(date)
    return removed


def build_metadata(
    *,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    diagnostics: dict[str, Any],
    raw_payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    csv_text: str,
    raw_text: str,
    season: int,
    retention_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": "adp",
        "ranking_id": config["ranking_id"],
        "ranking_name": config["ranking_name"],
        "ranking_type": "platform_composite_average_draft_position",
        "official_source_url": source_url,
        "fetched_at": fetched_at.isoformat(),
        "season_label": season,
        "format": {
            "dynasty": False,
            "season_scope": "single_season",
            "scoring": config["scoring"],
            "superflex": config["superflex"],
            "source_team_count": None,
            "actual_league_team_count": ACTUAL_LEAGUE_TEAM_COUNT,
            "fixed_two_te_modeled_by_source": False,
            "primary_for_positions": config["primary_for_positions"],
        },
        "snapshot": {
            "snapshot_date": fetched_at.date().isoformat(),
            "ranking_file": "ranking.csv",
            "metadata_file": "metadata.json",
            "raw_latest_file": "../../raw-latest.json",
            "row_count": len(rows),
            "position_counts": dict(
                sorted(Counter(row["position"] for row in rows).items())
            ),
            "csv_columns": CSV_FIELDS,
            "ranking_sha256": digest(csv_text),
            "source_raw_sha256_at_snapshot": digest(raw_text),
            "source_composition_fingerprint": diagnostics[
                "source_composition_fingerprint"
            ],
            "diagnostics": diagnostics,
        },
        "raw_schema": {
            "top_level_keys": sorted(raw_payload),
            "ranking_header_count": len(raw_payload.get("ranking_headers", [])),
            "ranking_row_count": len(raw_payload.get("ranking_rows", [])),
        },
        "raw_retention": {
            "policy": "latest_only",
            "file_name": "raw-latest.json",
            "historical_raw_snapshots": False,
            "semantics": (
                "Complete parsed public ranking table, player links, dynamic source columns "
                "and visible source-date table; the full volatile HTML document is not archived."
            ),
        },
        "normalized_history": {
            "archived": True,
            "retention_policy": "latest_changed_snapshots",
            "retention_count": retention_count,
            "files": ["ranking.csv", "metadata.json"],
            "skip_unchanged": True,
            "same_day_changes_replace_snapshot": True,
        },
        "extraction_provenance": {
            "method": "direct_official_public_html_table",
            "uses_mirror": False,
            "response_headers": response_headers,
        },
        "analysis_usage": {
            "role": "Observed cross-platform redraft draft-cost context",
            "primary_use": config["role"],
            "not_expert_consensus": True,
            "not_trade_market_value": True,
            "not_projection": True,
            "comparison_contract": ANALYSIS_METADATA,
            "rank_comparison": (
                "Use list-length-aware percentiles. Do not average this ranking with "
                "Fantasy Football Calculator or across the two FantasyPros formats."
            ),
            "source_composition_rule": (
                "A changed source composition or source-date set is a material source-context "
                "change and must not be interpreted as ordinary player movement alone."
            ),
            "league_adjustment": (
                "Use the PPR overall feed for RB/WR/TE and the Half-PPR Superflex feed for QB. "
                "Apply six-team replacement level and fixed two-QB/two-TE scarcity afterwards."
            ),
        },
        "attribution": {
            "display_name": SOURCE_NAME,
            "website": "https://www.fantasypros.com/",
        },
    }


def write_format(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
    diagnostics: dict[str, Any],
    raw_payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    season: int,
    skip_unchanged: bool,
    retention_count: int = DEFAULT_RETENTION_COUNT,
) -> tuple[list[Path], bool, list[str]]:
    if retention_count < 2:
        raise ValueError("FantasyPros ADP retention_count must be at least 2")
    root = ranking_root(repo_root, config)
    raw_path = root / "raw-latest.json"
    latest_path = root / "latest.json"
    snapshot_date = fetched_at.date().isoformat()
    snapshot_dir = root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    csv_text = render_csv(rows)
    raw_text = render_raw(raw_payload)
    ranking_sha = digest(csv_text)
    raw_sha = digest(raw_text)
    previous = read_json(latest_path)
    unchanged = bool(
        skip_unchanged
        and previous
        and previous.get("schema_version") == SCHEMA_VERSION
        and previous.get("ranking_sha256") == ranking_sha
        and previous.get("source_composition_fingerprint")
        == diagnostics["source_composition_fingerprint"]
    )

    atomic_write(raw_path, raw_text)
    if unchanged:
        updated = dict(previous)
        updated.update(
            {
                "raw_fetched_at": fetched_at.isoformat(),
                "raw_sha256": raw_sha,
                "official_source_url": source_url,
                "freshness_status": "live_fetch",
                "latest_source_dates": diagnostics["source_dates"],
                "latest_source_coverage": diagnostics["source_coverage"],
            }
        )
        atomic_write(latest_path, json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        return [raw_path, latest_path], False, []

    metadata = build_metadata(
        rows=rows,
        config=config,
        diagnostics=diagnostics,
        raw_payload=raw_payload,
        fetched_at=fetched_at,
        source_url=source_url,
        response_headers=response_headers,
        csv_text=csv_text,
        raw_text=raw_text,
        season=season,
        retention_count=retention_count,
    )
    atomic_write(ranking_path, csv_text)
    atomic_write(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    removed = prune_snapshots(root, retention_count)
    retained = snapshot_dates(root)
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_kind": "adp",
        "ranking_id": config["ranking_id"],
        "snapshot_date": snapshot_date,
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "snapshot_path": snapshot_dir.relative_to(repo_root).as_posix(),
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "raw_latest_file": raw_path.relative_to(repo_root).as_posix(),
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "source_composition_fingerprint": diagnostics[
            "source_composition_fingerprint"
        ],
        "latest_source_dates": diagnostics["source_dates"],
        "latest_source_coverage": diagnostics["source_coverage"],
        "retained_snapshot_dates": retained,
        "retention_count": retention_count,
        "official_source_url": source_url,
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA,
        "refresh_before_value_sensitive_analysis": True,
    }
    atomic_write(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    paths = [raw_path, ranking_path, metadata_path, latest_path]
    return paths, True, removed
