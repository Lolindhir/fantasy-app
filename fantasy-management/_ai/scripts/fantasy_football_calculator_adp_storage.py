"""Storage helpers for Fantasy Football Calculator ADP snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fantasy_football_calculator_adp_core import (
    ACTUAL_TEAMS,
    ANALYSIS_METADATA,
    CSV_FIELDS,
    DIRECT_FETCHER,
    SCHEMA_VERSION,
    SOURCE_ID,
    SOURCE_NAME,
    SOURCE_ROOT,
    WEBSITE,
    request_parameters,
)


def render_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in CSV_FIELDS} for row in rows)
    return output.getvalue()


def render_raw(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
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


def build_metadata(
    rows: list[dict[str, Any]],
    payload: dict[str, Any],
    config: dict[str, Any],
    sample: dict[str, Any],
    diagnostics: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    csv_text: str,
    raw_text: str,
    season: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": "adp",
        "ranking_id": config["ranking_id"],
        "ranking_name": config["ranking_name"],
        "ranking_type": "observed_mock_draft_average_draft_position",
        "official_source_url": WEBSITE,
        "api_url": source_url,
        "fetched_at": fetched_at.isoformat(),
        "season_label": season,
        "format": {
            "dynasty": False,
            "scoring": config["scoring"],
            "two_qb": config["two_qb"],
            "source_team_count": config["teams"],
            "actual_league_team_count": ACTUAL_TEAMS,
            "team_count_usage": "nearest_supported_proxy",
            "fixed_two_te_modeled_by_source": False,
        },
        "sample": sample,
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
            "diagnostics": diagnostics,
        },
        "raw_schema": {
            "top_level_keys": sorted(payload),
            "meta_keys": sorted(payload.get("meta", {})),
            "player_count": len(payload.get("players", [])),
            "player_field_names": sorted({
                key
                for item in payload.get("players", [])
                for key in item
            }),
        },
        "raw_retention": {
            "policy": "latest_only",
            "file_name": "raw-latest.json",
            "historical_raw_snapshots": False,
        },
        "normalized_history": {
            "archived": True,
            "files": ["ranking.csv", "metadata.json"],
            "skip_unchanged": True,
        },
        "extraction_provenance": {
            "method": "direct_official_rest_api",
            "uses_mirror": False,
            "response_headers": response_headers,
        },
        "analysis_usage": {
            "role": "Observed human mock-draft cost and uncertainty context",
            "primary_use": config["role"],
            "not_expert_consensus": True,
            "not_trade_market_value": True,
            "not_projection": True,
            "comparison_contract": ANALYSIS_METADATA,
            "rank_comparison": (
                "Use list-length-aware percentiles; never average the PPR "
                "and 2-QB feeds."
            ),
            "league_adjustment": (
                "Apply six-team replacement level and fixed two-QB/two-TE "
                "context during analysis."
            ),
        },
        "attribution": {
            "requested": True,
            "display_name": SOURCE_NAME,
            "website": WEBSITE,
        },
    }


def write_format(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    payload: dict[str, Any],
    config: dict[str, Any],
    sample: dict[str, Any],
    diagnostics: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    season: int,
    skip_unchanged: bool,
) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root, config)
    raw_path = root / "raw-latest.json"
    latest_path = root / "latest.json"
    snapshot_dir = root / "snapshots" / fetched_at.date().isoformat()
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    csv_text, raw_text = render_csv(rows), render_raw(payload)
    ranking_sha, raw_sha = digest(csv_text), digest(raw_text)
    previous = read_json(latest_path)
    unchanged = bool(
        skip_unchanged
        and previous
        and previous.get("schema_version") == SCHEMA_VERSION
        and previous.get("ranking_sha256") == ranking_sha
    )
    atomic_write(raw_path, raw_text)
    if unchanged:
        updated = dict(previous)
        updated.update({
            "raw_fetched_at": fetched_at.isoformat(),
            "raw_sha256": raw_sha,
            "api_url": source_url,
            "request_parameters": request_parameters(config, season),
            "latest_sample": sample,
            "freshness_status": "live_fetch",
        })
        atomic_write(
            latest_path,
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
        )
        return [raw_path, latest_path], False

    metadata = build_metadata(
        rows,
        payload,
        config,
        sample,
        diagnostics,
        fetched_at,
        source_url,
        response_headers,
        csv_text,
        raw_text,
        season,
    )
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_kind": "adp",
        "ranking_id": config["ranking_id"],
        "snapshot_date": fetched_at.date().isoformat(),
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "snapshot_path": snapshot_dir.relative_to(repo_root).as_posix(),
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "raw_latest_file": raw_path.relative_to(repo_root).as_posix(),
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "api_url": source_url,
        "request_parameters": request_parameters(config, season),
        "latest_sample": sample,
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA,
        "refresh_before_value_sensitive_analysis": True,
    }
    atomic_write(ranking_path, csv_text)
    atomic_write(
        metadata_path,
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write(
        latest_path,
        json.dumps(latest, indent=2, ensure_ascii=False) + "\n",
    )
    return [raw_path, ranking_path, metadata_path, latest_path], True
