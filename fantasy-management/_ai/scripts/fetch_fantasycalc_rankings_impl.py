#!/usr/bin/env python3
"""Fetch FantasyCalc market values for the Mighty Giants league format.

FantasyCalc is queried twice: Dynasty and Redraft. The source's nearest supported
league-size proxy is eight teams for the actual six-team league. Each format keeps
only the newest complete API response as ``raw-latest.json``. Historical snapshots
contain only our normalized ``ranking.csv`` and the accompanying ``metadata.json``.

FantasyCalc's ``overallRank`` is retained as ``source_overall_rank`` and is not
assumed to be globally unique. Our ``Rank`` column is a deterministic unique row
order derived from source rank, value and source asset id.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

API_URL = "https://api.fantasycalc.com/values/current"
WEBSITE_URL = "https://fantasycalc.com/"
SOURCE_ID = "fantasycalc"
SCHEMA_VERSION = 2
ACTUAL_LEAGUE_TEAMS = 6
SOURCE_TEAM_PROXY = 8
NUM_QBS = 2
PPR = 1
MIN_NORMALIZED_ROWS = 100
POSITIONS = frozenset({"QB", "RB", "WR", "TE", "PICK"})
PLAYER_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
DIRECT_FETCHER = "fantasy-management/_ai/scripts/fetch_fantasycalc_rankings.py"
ANALYSIS_METADATA_FILE = (
    "fantasy-management/sources/external-rankings/fantasycalc/analysis-metadata.json"
)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)

FORMAT_CONFIGS: dict[str, dict[str, Any]] = {
    "dynasty": {
        "ranking_id": "dynasty-superflex-ppr-8-team",
        "ranking_name": "FantasyCalc Dynasty Superflex PPR 8-Team Market Values",
        "is_dynasty": True,
        "value_horizon": "multi_season",
        "primary_use": "dynasty_trade_market_value",
        "expects_picks": True,
    },
    "redraft": {
        "ranking_id": "redraft-superflex-ppr-8-team",
        "ranking_name": "FantasyCalc Redraft Superflex PPR 8-Team Market Values",
        "is_dynasty": False,
        "value_horizon": "single_season",
        "primary_use": "current_season_trade_market_value",
        "expects_picks": False,
    },
}

CSV_FIELDS = [
    "name",
    "Rank",
    "source_overall_rank",
    "asset_type",
    "position",
    "team",
    "value",
    "position_rank",
    "tier",
    "trend_30_day",
    "source_asset_id",
    "sleeper_id",
    "mfl_id",
    "espn_id",
    "age",
    "years_experience",
    "adp",
    "trade_frequency",
    "roster_percent",
    "redraft_value",
    "combined_value",
    "redraft_dynasty_value_difference",
    "redraft_dynasty_value_percent_difference",
    "starter",
]


class FantasyCalcFetchError(RuntimeError):
    """Raised when FantasyCalc cannot be fetched or normalized safely."""


def request_parameters(config: dict[str, Any]) -> dict[str, str]:
    return {
        "isDynasty": str(bool(config["is_dynasty"])).lower(),
        "numQbs": str(NUM_QBS),
        "numTeams": str(SOURCE_TEAM_PROXY),
        "ppr": str(PPR),
        "includeAdp": "true",
        "includeRosterPercent": "true",
    }


def build_source_url(config: dict[str, Any], base_url: str = API_URL) -> str:
    return f"{base_url}?{urllib.parse.urlencode(request_parameters(config))}"


def fetch_payload(
    config: dict[str, Any], *, base_url: str = API_URL, timeout: int = 30
) -> tuple[list[dict[str, Any]], dict[str, str], str]:
    source_url = build_source_url(config, base_url)
    request = urllib.request.Request(
        source_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            headers = {
                "etag": response.headers.get("ETag") or "",
                "last_modified": response.headers.get("Last-Modified") or "",
                "content_type": response.headers.get("Content-Type") or "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FantasyCalcFetchError(f"FantasyCalc fetch failed: {exc}") from exc

    if not body.strip():
        raise FantasyCalcFetchError("FantasyCalc returned an empty response")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise FantasyCalcFetchError(f"FantasyCalc response is not valid JSON: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise FantasyCalcFetchError("FantasyCalc response is not a non-empty array")
    if not all(isinstance(item, dict) for item in payload):
        raise FantasyCalcFetchError("FantasyCalc response contains non-object entries")
    return payload, headers, source_url


def parse_required_int(
    value: Any, *, field_name: str, asset_name: str, minimum: int = 0
) -> int:
    if isinstance(value, bool):
        raise FantasyCalcFetchError(f"Invalid {field_name} for {asset_name}: {value!r}")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FantasyCalcFetchError(
            f"Invalid {field_name} for {asset_name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed != parsed.to_integral_value():
        raise FantasyCalcFetchError(f"Invalid {field_name} for {asset_name}: {value!r}")
    result = int(parsed)
    if result < minimum:
        raise FantasyCalcFetchError(
            f"{field_name} for {asset_name} must be at least {minimum}: {result}"
        )
    return result


def parse_optional_number(
    value: Any, *, field_name: str, asset_name: str, minimum: Decimal | None = None
) -> int | float | str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if isinstance(value, bool):
        raise FantasyCalcFetchError(f"Invalid {field_name} for {asset_name}: {value!r}")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FantasyCalcFetchError(
            f"Invalid {field_name} for {asset_name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or (minimum is not None and parsed < minimum):
        raise FantasyCalcFetchError(f"Invalid {field_name} for {asset_name}: {value!r}")
    if parsed == parsed.to_integral_value():
        return int(parsed)
    return float(parsed)


def parse_assets(
    payload: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for source_order, entry in enumerate(payload):
        player = entry.get("player")
        if not isinstance(player, dict):
            raise FantasyCalcFetchError("FantasyCalc entry is missing a player object")
        name = str(player.get("name") or "").strip()
        position = str(player.get("position") or "").strip().upper()
        source_asset_id = str(player.get("id") or "").strip()
        if not name or not source_asset_id:
            raise FantasyCalcFetchError("FantasyCalc asset is missing name or source ID")
        if position not in POSITIONS:
            raise FantasyCalcFetchError(f"Unexpected FantasyCalc position for {name}: {position!r}")
        if source_asset_id in seen_ids:
            raise FantasyCalcFetchError(f"Duplicate FantasyCalc source ID: {source_asset_id}")
        seen_ids.add(source_asset_id)

        source_overall_rank = parse_required_int(
            entry.get("overallRank"), field_name="overallRank", asset_name=name, minimum=1
        )
        value = parse_required_int(
            entry.get("value"), field_name="value", asset_name=name, minimum=0
        )
        rows.append(
            {
                "name": name,
                "Rank": 0,
                "source_overall_rank": source_overall_rank,
                "asset_type": "draft_pick" if position == "PICK" else "player",
                "position": position,
                "team": str(player.get("maybeTeam") or "").strip().upper(),
                "value": value,
                "position_rank": parse_optional_number(
                    entry.get("positionRank"),
                    field_name="positionRank",
                    asset_name=name,
                    minimum=Decimal("1"),
                ),
                "tier": parse_optional_number(
                    entry.get("maybeTier"),
                    field_name="maybeTier",
                    asset_name=name,
                    minimum=Decimal("1"),
                ),
                "trend_30_day": parse_optional_number(
                    entry.get("trend30Day"), field_name="trend30Day", asset_name=name
                ),
                "source_asset_id": source_asset_id,
                "sleeper_id": str(player.get("sleeperId") or "").strip(),
                "mfl_id": str(player.get("mflId") or "").strip(),
                "espn_id": str(player.get("espnId") or "").strip(),
                "age": parse_optional_number(
                    player.get("maybeAge"),
                    field_name="maybeAge",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "years_experience": parse_optional_number(
                    player.get("maybeYoe"),
                    field_name="maybeYoe",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "adp": parse_optional_number(
                    entry.get("maybeAdp"),
                    field_name="maybeAdp",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "trade_frequency": parse_optional_number(
                    entry.get("maybeTradeFrequency"),
                    field_name="maybeTradeFrequency",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "roster_percent": parse_optional_number(
                    entry.get("maybeRosterPercent"),
                    field_name="maybeRosterPercent",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "redraft_value": parse_optional_number(
                    entry.get("redraftValue"),
                    field_name="redraftValue",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "combined_value": parse_optional_number(
                    entry.get("combinedValue"),
                    field_name="combinedValue",
                    asset_name=name,
                    minimum=Decimal("0"),
                ),
                "redraft_dynasty_value_difference": parse_optional_number(
                    entry.get("redraftDynastyValueDifference"),
                    field_name="redraftDynastyValueDifference",
                    asset_name=name,
                ),
                "redraft_dynasty_value_percent_difference": parse_optional_number(
                    entry.get("redraftDynastyValuePercDifference"),
                    field_name="redraftDynastyValuePercDifference",
                    asset_name=name,
                ),
                "starter": bool(entry.get("starter")),
                "_source_order": source_order,
            }
        )

    # FantasyCalc can publish duplicate overallRank values. Preserve those source
    # ranks, then create a deterministic unique normalized row order for our CSV.
    rows.sort(
        key=lambda row: (
            int(row["source_overall_rank"]),
            -int(row["value"]),
            str(row["source_asset_id"]),
            int(row["_source_order"]),
        )
    )
    for normalized_rank, row in enumerate(rows, start=1):
        row["Rank"] = normalized_rank
        row.pop("_source_order", None)

    validate_rows(rows, config)
    return rows


def source_rank_diagnostics(
    rows: list[dict[str, Any]], *, sample_limit: int = 20
) -> dict[str, Any]:
    counts = Counter(int(row["source_overall_rank"]) for row in rows)
    duplicate_ranks = sorted(rank for rank, count in counts.items() if count > 1)
    samples: list[dict[str, Any]] = []
    for source_rank in duplicate_ranks[:sample_limit]:
        assets = [
            {
                "name": str(row["name"]),
                "position": str(row["position"]),
                "value": int(row["value"]),
                "normalized_rank": int(row["Rank"]),
                "source_asset_id": str(row["source_asset_id"]),
            }
            for row in rows
            if int(row["source_overall_rank"]) == source_rank
        ]
        samples.append({"source_overall_rank": source_rank, "assets": assets})
    return {
        "source_overall_rank_unique": not duplicate_ranks,
        "duplicate_source_rank_group_count": len(duplicate_ranks),
        "duplicate_source_rank_row_count": sum(counts[rank] for rank in duplicate_ranks),
        "duplicate_source_rank_samples": samples,
        "sample_limit": sample_limit,
        "normalized_rank_method": (
            "source_overall_rank_asc_then_value_desc_then_source_asset_id"
        ),
    }


def validate_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    if len(rows) < MIN_NORMALIZED_ROWS:
        raise FantasyCalcFetchError(
            f"Only {len(rows)} normalized rows found; expected at least {MIN_NORMALIZED_ROWS}"
        )
    ranks = [int(row["Rank"]) for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise FantasyCalcFetchError("Normalized FantasyCalc ranks are not contiguous and unique")

    position_counts = Counter(str(row["position"]) for row in rows)
    missing_positions = sorted(PLAYER_POSITIONS - set(position_counts))
    if missing_positions:
        raise FantasyCalcFetchError(
            "FantasyCalc payload is missing player positions: " + ", ".join(missing_positions)
        )
    pick_count = position_counts.get("PICK", 0)
    if config["expects_picks"] and pick_count < 4:
        raise FantasyCalcFetchError(
            f"Dynasty FantasyCalc payload contains only {pick_count} draft picks"
        )
    if not config["expects_picks"] and pick_count:
        raise FantasyCalcFetchError("Redraft FantasyCalc payload unexpectedly contains draft picks")


def render_csv(rows: Iterable[dict[str, Any]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=CSV_FIELDS, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_raw_json(payload: list[dict[str, Any]]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def ranking_root(repo_root: Path, config: dict[str, Any]) -> Path:
    return (
        repo_root
        / "fantasy-management"
        / "sources"
        / "external-rankings"
        / "fantasycalc"
        / str(config["ranking_id"])
    )


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def latest_snapshot_metadata(repo_root: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    latest = load_json(ranking_root(repo_root, config) / "latest.json")
    if latest is None:
        return None
    metadata_file = latest.get("metadata_file")
    if not isinstance(metadata_file, str) or not metadata_file.strip():
        return None
    return load_json(repo_root / metadata_file)


def raw_schema_summary(payload: list[dict[str, Any]]) -> dict[str, Any]:
    entry_fields: set[str] = set()
    player_fields: set[str] = set()
    for entry in payload:
        entry_fields.update(str(key) for key in entry)
        player = entry.get("player")
        if isinstance(player, dict):
            player_fields.update(str(key) for key in player)
    return {
        "top_level_type": "array",
        "entry_count": len(payload),
        "entry_field_names": sorted(entry_fields),
        "player_field_names": sorted(player_fields),
    }


def ranking_needs_snapshot(
    *, repo_root: Path, config: dict[str, Any], csv_content: str
) -> bool:
    metadata = latest_snapshot_metadata(repo_root, config)
    if metadata is None or metadata.get("schema_version") != SCHEMA_VERSION:
        return True
    snapshot = metadata.get("snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("csv_columns") != CSV_FIELDS:
        return True
    previous_hash = snapshot.get("ranking_sha256")
    current_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()
    return not isinstance(previous_hash, str) or previous_hash != current_hash


def build_metadata(
    *,
    rows: list[dict[str, Any]],
    csv_content: str,
    raw_content: str,
    payload: list[dict[str, Any]],
    config: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
) -> dict[str, Any]:
    position_counts = Counter(str(row["position"]) for row in rows)
    asset_counts = Counter(str(row["asset_type"]) for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": "FantasyCalc",
        "ranking_id": config["ranking_id"],
        "ranking_name": config["ranking_name"],
        "ranking_type": "observed_trade_market_value_ranking",
        "official_source_url": WEBSITE_URL,
        "api_url": source_url,
        "fetched_at": fetched_at.isoformat(),
        "source_updated_at": None,
        "format": {
            "dynasty": bool(config["is_dynasty"]),
            "season_scope": config["value_horizon"],
            "scoring": "ppr",
            "superflex": True,
            "source_team_count": SOURCE_TEAM_PROXY,
            "actual_league_team_count": ACTUAL_LEAGUE_TEAMS,
            "team_count_usage": "nearest_supported_proxy",
            "te_premium": False,
            "fixed_two_te_modeled_by_source": False,
        },
        "request_parameters": request_parameters(config),
        "snapshot": {
            "snapshot_date": fetched_at.date().isoformat(),
            "ranking_file": "ranking.csv",
            "metadata_file": "metadata.json",
            "raw_latest_file": "../../raw-latest.json",
            "row_count": len(rows),
            "asset_type_counts": dict(sorted(asset_counts.items())),
            "position_counts": dict(sorted(position_counts.items())),
            "csv_columns": CSV_FIELDS,
            "ranking_sha256": hashlib.sha256(csv_content.encode("utf-8")).hexdigest(),
            "source_raw_sha256_at_snapshot": hashlib.sha256(
                raw_content.encode("utf-8")
            ).hexdigest(),
            "rank_diagnostics": source_rank_diagnostics(rows),
        },
        "raw_schema": raw_schema_summary(payload),
        "extraction_provenance": {
            "method": "direct_public_json_api",
            "response_headers": response_headers,
            "raw_retention": "latest_only",
            "historical_archive": "normalized_rankings_and_metadata_only",
        },
        "freshness": {
            "status": "live_fetch",
            "source_timestamp_available": False,
            "refresh_before_value_sensitive_analysis": True,
        },
        "analysis_usage": {
            "role": "Observed trade-market value and plausibility context",
            "value_horizon": config["value_horizon"],
            "primary_use": config["primary_use"],
            "not_projection": True,
            "not_expert_consensus": True,
            "comparison_contract": ANALYSIS_METADATA_FILE,
            "preferred_player_join": [
                "sleeper_id",
                "source_asset_id",
                "normalized_name_position",
            ],
            "rank_semantics": {
                "Rank": (
                    "Repository-normalized unique row order. Use for deterministic joins and "
                    "list-length percentiles."
                ),
                "source_overall_rank": (
                    "FantasyCalc-published overallRank. May contain duplicate values and must "
                    "not be treated as a unique key."
                ),
            },
            "league_adjustment": (
                "FantasyCalc uses the nearest supported eight-team proxy for the actual "
                "six-team league. It models Superflex and PPR, but not two fixed TE starters; "
                "apply additional replacement-level and TE-scarcity context during analysis."
            ),
        },
        "attribution": {
            "required": True,
            "display_name": "FantasyCalc",
            "website": WEBSITE_URL,
        },
    }


def update_latest_for_raw_only(
    *,
    repo_root: Path,
    config: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    raw_path: Path,
    raw_content: str,
) -> Path:
    root = ranking_root(repo_root, config)
    latest_path = root / "latest.json"
    latest = load_json(latest_path)
    if latest is None:
        raise FantasyCalcFetchError("Cannot update raw-only freshness without a ranking snapshot")
    latest.update(
        {
            "raw_latest_file": raw_path.relative_to(repo_root).as_posix(),
            "raw_fetched_at": fetched_at.isoformat(),
            "raw_sha256": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
            "api_url": source_url,
            "request_parameters": request_parameters(config),
            "freshness_status": "live_fetch",
        }
    )
    atomic_write_text(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return latest_path


def write_format(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    payload: list[dict[str, Any]],
    config: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    response_headers: dict[str, str],
    skip_unchanged: bool,
) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root, config)
    raw_path = root / "raw-latest.json"
    raw_content = render_raw_json(payload)
    csv_content = render_csv(rows)

    # The complete source response is intentionally retained only at this path.
    atomic_write_text(raw_path, raw_content)

    if skip_unchanged and not ranking_needs_snapshot(
        repo_root=repo_root, config=config, csv_content=csv_content
    ):
        latest_path = update_latest_for_raw_only(
            repo_root=repo_root,
            config=config,
            fetched_at=fetched_at,
            source_url=source_url,
            raw_path=raw_path,
            raw_content=raw_content,
        )
        return [raw_path, latest_path], False

    snapshot_date = fetched_at.date().isoformat()
    snapshot_dir = root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    latest_path = root / "latest.json"
    metadata = build_metadata(
        rows=rows,
        csv_content=csv_content,
        raw_content=raw_content,
        payload=payload,
        config=config,
        fetched_at=fetched_at,
        source_url=source_url,
        response_headers=response_headers,
    )
    relative_snapshot = snapshot_dir.relative_to(repo_root).as_posix()
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_id": config["ranking_id"],
        "snapshot_date": snapshot_date,
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "snapshot_path": relative_snapshot,
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "raw_latest_file": raw_path.relative_to(repo_root).as_posix(),
        "raw_sha256": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
        "api_url": source_url,
        "request_parameters": request_parameters(config),
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA_FILE,
        "refresh_before_value_sensitive_analysis": True,
    }

    atomic_write_text(ranking_path, csv_content)
    atomic_write_text(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    atomic_write_text(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return [raw_path, ranking_path, metadata_path, latest_path], True


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=API_URL, help="FantasyCalc API base URL")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--format", choices=["all", *FORMAT_CONFIGS], default="all")
    parser.add_argument(
        "--from-file",
        type=Path,
        help="Parse saved JSON; requires --format dynasty or --format redraft",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--fetched-at", help="Override UTC timestamp for tests")
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.from_file and args.format == "all":
        print("[fantasycalc] --from-file requires one explicit --format", file=sys.stderr)
        return 2

    format_keys = list(FORMAT_CONFIGS) if args.format == "all" else [args.format]
    fetched_at = parse_timestamp(args.fetched_at)
    repo_root = args.repo_root.resolve()

    try:
        for format_key in format_keys:
            config = FORMAT_CONFIGS[format_key]
            if args.from_file:
                payload = json.loads(args.from_file.read_text(encoding="utf-8"))
                if not isinstance(payload, list):
                    raise FantasyCalcFetchError("Saved FantasyCalc JSON must be an array")
                response_headers: dict[str, str] = {}
                source_url = build_source_url(config, args.url)
            else:
                payload, response_headers, source_url = fetch_payload(
                    config, base_url=args.url, timeout=args.timeout
                )
            rows = parse_assets(payload, config)
            diagnostics = source_rank_diagnostics(rows)
            if diagnostics["duplicate_source_rank_group_count"]:
                print(
                    "[fantasycalc] note: "
                    f"{diagnostics['duplicate_source_rank_group_count']} duplicate source-rank "
                    "groups retained; normalized Rank is unique",
                    file=sys.stderr,
                )

            if args.dry_run:
                counts = Counter(str(row["position"]) for row in rows)
                print(
                    f"FantasyCalc {format_key} rows={len(rows)} "
                    + " ".join(f"{key}={counts[key]}" for key in sorted(counts))
                    + f" duplicate_source_rank_groups={diagnostics['duplicate_source_rank_group_count']}"
                )
                for row in rows[:10]:
                    print({key: row[key] for key in CSV_FIELDS})
                continue

            paths, created = write_format(
                repo_root=repo_root,
                rows=rows,
                payload=payload,
                config=config,
                fetched_at=fetched_at,
                source_url=source_url,
                response_headers=response_headers,
                skip_unchanged=args.skip_unchanged,
            )
            action = "snapshot written" if created else "ranking unchanged; raw latest refreshed"
            print(f"[fantasycalc] {format_key}: {action}")
            for path in paths:
                print(path)
    except (FantasyCalcFetchError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[fantasycalc] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
