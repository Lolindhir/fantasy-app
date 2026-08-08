"""Materialize a kicker-only ADP ranking from an existing FFC PPR payload."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCE_ID = "fantasy-football-calculator"
SOURCE_NAME = "Fantasy Football Calculator"
SOURCE_ROOT = (
    "fantasy-management/sources/external-rankings/adp/"
    "fantasy-football-calculator"
)
RANKING_ID = "redraft-ppr-8-team-kicker"
RANKING_NAME = "Fantasy Football Calculator Redraft PPR 8-Team Kicker ADP"
ANALYSIS_METADATA = f"{SOURCE_ROOT}/analysis-metadata.json"
DIRECT_FETCHER = (
    "fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py"
)
SCHEMA_VERSION = 1
ACTUAL_TEAMS = 6
SOURCE_TEAMS = 8
MIN_KICKER_ROWS = 8
CSV_FIELDS = [
    "name", "Rank", "source_rank", "position", "team", "source_player_id",
    "adp", "adp_formatted", "times_drafted", "high", "low", "stdev", "bye",
    "source_format", "source_team_count", "actual_league_team_count",
    "sample_total_drafts", "sample_start_date", "sample_end_date",
]


class FantasyFootballCalculatorKickerError(RuntimeError):
    """Raised when kicker rows cannot be materialized safely."""


def _number(value: Any, field: str, name: str, minimum: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, bool):
        raise FantasyFootballCalculatorKickerError(
            f"Invalid FFC {field} for {name}: {value!r}"
        )
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FantasyFootballCalculatorKickerError(
            f"Invalid FFC {field} for {name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < minimum:
        raise FantasyFootballCalculatorKickerError(
            f"Invalid FFC {field} for {name}: {value!r}"
        )
    return parsed


def _integer(value: Any, field: str, name: str, minimum: int = 0) -> int:
    parsed = _number(value, field, name, Decimal(minimum))
    if parsed != parsed.to_integral_value():
        raise FantasyFootballCalculatorKickerError(
            f"FFC {field} for {name} must be an integer: {value!r}"
        )
    return int(parsed)


def _csv_number(value: Decimal) -> int | str:
    if value == value.to_integral_value():
        return int(value)
    return format(value.normalize(), "f")


def _bye(value: Any, name: str) -> int | str:
    if value is None or str(value).strip() in {"", "-"}:
        return ""
    result = _integer(value, "bye", name)
    if result > 18:
        raise FantasyFootballCalculatorKickerError(
            f"Invalid FFC bye for {name}: {result}"
        )
    return result


def parse_kickers(
    payload: dict[str, Any],
    sample: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    players = payload.get("players")
    if not isinstance(players, list):
        raise FantasyFootballCalculatorKickerError("FFC payload has no player list")

    rows: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    tolerance = Decimal("0.11")

    for source_rank, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            raise FantasyFootballCalculatorKickerError("FFC players contain non-object entries")
        raw_position = str(player.get("position") or "").strip().upper()
        if raw_position not in {"PK", "K", "KICKER"}:
            continue

        name = str(player.get("name") or "").strip()
        player_id = str(player.get("player_id") or "").strip()
        if not name or not player_id:
            raise FantasyFootballCalculatorKickerError(
                "FFC kicker is missing name or player_id"
            )
        if player_id in identifiers:
            raise FantasyFootballCalculatorKickerError(
                f"Duplicate FFC kicker player_id: {player_id}"
            )
        identifiers.add(player_id)

        adp = _number(player.get("adp"), "adp", name, Decimal("0.01"))
        high = _number(player.get("high"), "high", name, Decimal("0.01"))
        low = _number(player.get("low"), "low", name, Decimal("0.01"))
        stdev = _number(player.get("stdev"), "stdev", name)
        drafted = _integer(player.get("times_drafted"), "times_drafted", name, 1)
        if high > low or adp + tolerance < high or adp - tolerance > low:
            raise FantasyFootballCalculatorKickerError(
                f"FFC ADP outside high/low for {name}: "
                f"high={high}, adp={adp}, low={low}"
            )

        rows.append({
            "name": name,
            "Rank": 0,
            "source_rank": source_rank,
            "position": "K",
            "team": str(player.get("team") or "").strip().upper(),
            "source_player_id": player_id,
            "adp": _csv_number(adp),
            "adp_formatted": str(player.get("adp_formatted") or "").strip(),
            "times_drafted": drafted,
            "high": _csv_number(high),
            "low": _csv_number(low),
            "stdev": _csv_number(stdev),
            "bye": _bye(player.get("bye"), name),
            "source_format": "ppr",
            "source_team_count": SOURCE_TEAMS,
            "actual_league_team_count": ACTUAL_TEAMS,
            "sample_total_drafts": sample["total_drafts"],
            "sample_start_date": sample["start_date"],
            "sample_end_date": sample["end_date"],
            "_adp": adp,
        })

    rows.sort(
        key=lambda row: (
            row["_adp"],
            -row["times_drafted"],
            row["source_player_id"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row.pop("_adp")

    if len(rows) < MIN_KICKER_ROWS:
        raise FantasyFootballCalculatorKickerError(
            f"Too few FFC kicker rows for {RANKING_ID}: {len(rows)}"
        )

    return rows, {
        "source_player_count": len(players),
        "normalized_player_count": len(rows),
        "normalized_position": "K",
        "source_position": "PK",
        "normalized_rank_unique": len(rows) == len({row["Rank"] for row in rows}),
        "reuses_ppr_all_position_payload": True,
    }


def _render_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in CSV_FIELDS} for row in rows)
    return output.getvalue()


def _render_raw(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def ranking_root(repo_root: Path) -> Path:
    return repo_root / SOURCE_ROOT / RANKING_ID


def write_kicker_format(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    payload: dict[str, Any],
    sample: dict[str, Any],
    diagnostics: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    season: int,
    skip_unchanged: bool,
) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root)
    raw_path = root / "raw-latest.json"
    latest_path = root / "latest.json"
    snapshot_dir = root / "snapshots" / fetched_at.date().isoformat()
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"

    csv_text = _render_csv(rows)
    raw_text = _render_raw(payload)
    ranking_sha = _digest(csv_text)
    raw_sha = _digest(raw_text)
    previous = _read_json(latest_path)
    unchanged = bool(
        skip_unchanged
        and previous
        and previous.get("schema_version") == SCHEMA_VERSION
        and previous.get("ranking_sha256") == ranking_sha
    )

    _atomic_write(raw_path, raw_text)
    request_parameters = {"teams": "8", "year": str(season), "position": "all"}
    if unchanged:
        updated = dict(previous)
        updated.update({
            "raw_fetched_at": fetched_at.isoformat(),
            "raw_sha256": raw_sha,
            "api_url": source_url,
            "request_parameters": request_parameters,
            "latest_sample": sample,
            "freshness_status": "live_fetch",
        })
        _atomic_write(
            latest_path,
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
        )
        return [raw_path, latest_path], False

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": "adp",
        "ranking_id": RANKING_ID,
        "ranking_name": RANKING_NAME,
        "ranking_type": "observed_mock_draft_average_draft_position",
        "official_source_url": "https://fantasyfootballcalculator.com/",
        "api_url": source_url,
        "fetched_at": fetched_at.isoformat(),
        "season_label": season,
        "format": {
            "dynasty": False,
            "scoring": "ppr",
            "position": "K",
            "source_position": "PK",
            "source_team_count": SOURCE_TEAMS,
            "actual_league_team_count": ACTUAL_TEAMS,
            "team_count_usage": "nearest_supported_proxy",
            "actual_fixed_kicker_starters": 1,
        },
        "sample": sample,
        "snapshot": {
            "snapshot_date": fetched_at.date().isoformat(),
            "ranking_file": "ranking.csv",
            "metadata_file": "metadata.json",
            "raw_latest_file": "../../raw-latest.json",
            "row_count": len(rows),
            "position_counts": {"K": len(rows)},
            "csv_columns": CSV_FIELDS,
            "ranking_sha256": ranking_sha,
            "source_raw_sha256_at_snapshot": raw_sha,
            "diagnostics": diagnostics,
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
            "method": "derived_from_same_official_ppr_all_position_api_payload",
            "additional_network_request": False,
            "source_ranking_id": "redraft-ppr-8-team",
            "response_headers": response_headers,
        },
        "analysis_usage": {
            "role": "Observed kicker mock-draft cost and uncertainty context",
            "primary_use": "kicker_draft_cost",
            "not_expert_consensus": True,
            "not_trade_market_value": True,
            "not_projection": True,
            "comparison_contract": ANALYSIS_METADATA,
            "rank_comparison": "Compare K-only ranks through list-length-aware percentiles.",
            "league_adjustment": (
                "Apply six-team replacement level and one fixed kicker starter during analysis."
            ),
        },
        "attribution": {
            "requested": True,
            "display_name": SOURCE_NAME,
            "website": "https://fantasyfootballcalculator.com/",
        },
    }
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_kind": "adp",
        "ranking_id": RANKING_ID,
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
        "request_parameters": request_parameters,
        "latest_sample": sample,
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA,
        "refresh_before_value_sensitive_analysis": True,
        "reuses_source_payload_without_extra_request": True,
    }
    _atomic_write(ranking_path, csv_text)
    _atomic_write(
        metadata_path,
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
    )
    _atomic_write(
        latest_path,
        json.dumps(latest, indent=2, ensure_ascii=False) + "\n",
    )
    return [raw_path, ranking_path, metadata_path, latest_path], True
