#!/usr/bin/env python3
"""Fetch FantasyPros Dynasty Superflex ECR and store a lossless snapshot.

The public FantasyPros rankings page embeds its ranking payload in the HTML as
``ecrData = {...}``. This script downloads that official page directly, extracts
and validates the payload, then writes:

- ``ranking.csv`` as a compact normalized analysis table
- ``raw-ecr-data.json`` as the complete parsed ``ecrData`` payload
- ``metadata.json`` with provenance, schema and freshness information
- ``latest.json`` as a pointer to the newest successful snapshot

No mirror or cached third-party ranking is used by this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://www.fantasypros.com/nfl/rankings/dynasty-superflex.php"
SOURCE_ID = "fantasypros"
RANKING_ID = "dynasty-superflex-ppr"
SCHEMA_VERSION = 4
MIN_PLAYER_ROWS = 150
OFFENSIVE_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
CONSENSUS_FIELDS = ("tier", "rank_min", "rank_max", "rank_ave", "rank_std")
CSV_FIELDS = [
    "name",
    "Rank",
    "position",
    "team",
    "position_rank",
    "tier",
    "rank_min",
    "rank_max",
    "rank_ave",
    "rank_std",
    "source_player_id",
]
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)


class FantasyProsFetchError(RuntimeError):
    """Raised when the source cannot be fetched or validated safely."""


def fetch_html(url: str = SOURCE_URL, *, timeout: int = 30) -> tuple[str, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="replace")
            headers = {
                "etag": response.headers.get("ETag") or "",
                "last_modified": response.headers.get("Last-Modified") or "",
                "content_type": response.headers.get("Content-Type") or "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FantasyProsFetchError(f"FantasyPros fetch failed: {exc}") from exc

    if not html.strip():
        raise FantasyProsFetchError("FantasyPros returned an empty response")
    return html, headers


def extract_ecr_data(html: str) -> dict[str, Any]:
    marker = re.search(r"(?:var\s+)?ecrData\s*=\s*(\{)", html)
    if not marker:
        raise FantasyProsFetchError("ecrData marker not found in FantasyPros HTML")

    start = marker.start(1)
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                payload = html[start : index + 1]
                break
    else:
        raise FantasyProsFetchError("ecrData payload has unbalanced braces")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FantasyProsFetchError(f"ecrData is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("players"), list):
        raise FantasyProsFetchError("ecrData does not contain a players list")
    return data


def parse_optional_int(
    value: Any,
    *,
    field_name: str,
    player_name: str,
    minimum: int = 1,
) -> int | str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise FantasyProsFetchError(
            f"Invalid {field_name} for {player_name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed != parsed.to_integral_value():
        raise FantasyProsFetchError(f"Invalid {field_name} for {player_name}: {value!r}")
    result = int(parsed)
    if result < minimum:
        raise FantasyProsFetchError(
            f"{field_name} for {player_name} must be at least {minimum}: {result}"
        )
    return result


def parse_optional_decimal(
    value: Any,
    *,
    field_name: str,
    player_name: str,
    minimum: Decimal = Decimal("0"),
) -> Decimal | str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise FantasyProsFetchError(
            f"Invalid {field_name} for {player_name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < minimum:
        raise FantasyProsFetchError(
            f"{field_name} for {player_name} must be at least {minimum}: {value!r}"
        )
    return parsed


def parse_players(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_ranks: set[int] = set()

    for player in data["players"]:
        if not isinstance(player, dict):
            continue
        name = str(player.get("player_name") or "").strip()
        position = str(player.get("player_position_id") or "").strip().upper()
        team = str(player.get("player_team_id") or "").strip().upper()
        rank_value = player.get("rank_ecr")

        if not name or position not in OFFENSIVE_POSITIONS or rank_value is None:
            continue
        try:
            rank = int(rank_value)
        except (TypeError, ValueError):
            continue
        if rank <= 0 or rank in seen_ranks:
            continue

        seen_ranks.add(rank)
        candidates.append(
            {
                "name": name,
                "Rank": rank,
                "position": position,
                "team": team,
                "position_rank": str(player.get("pos_rank") or "").strip().upper(),
                "tier": parse_optional_int(
                    player.get("tier"), field_name="tier", player_name=name
                ),
                "rank_min": parse_optional_int(
                    player.get("rank_min"), field_name="rank_min", player_name=name
                ),
                "rank_max": parse_optional_int(
                    player.get("rank_max"), field_name="rank_max", player_name=name
                ),
                "rank_ave": parse_optional_decimal(
                    player.get("rank_ave"), field_name="rank_ave", player_name=name
                ),
                "rank_std": parse_optional_decimal(
                    player.get("rank_std"), field_name="rank_std", player_name=name
                ),
                "source_player_id": str(player.get("player_id") or "").strip(),
                "position_rank_source": "source" if player.get("pos_rank") else "derived",
            }
        )

    candidates.sort(key=lambda row: row["Rank"])
    position_counters: Counter[str] = Counter()
    for row in candidates:
        position = str(row["position"])
        position_counters[position] += 1
        if not row["position_rank"]:
            row["position_rank"] = f"{position}{position_counters[position]}"

    validate_rows(candidates)
    return candidates


def validate_rows(rows: list[dict[str, Any]]) -> None:
    if len(rows) < MIN_PLAYER_ROWS:
        raise FantasyProsFetchError(
            f"Only {len(rows)} valid offensive rows found; expected at least {MIN_PLAYER_ROWS}"
        )

    ranks = [int(row["Rank"]) for row in rows]
    if ranks != sorted(ranks) or len(ranks) != len(set(ranks)):
        raise FantasyProsFetchError("Ranks are not unique and ascending")
    if any(row["position"] not in OFFENSIVE_POSITIONS for row in rows):
        raise FantasyProsFetchError("Unexpected position in parsed rows")
    if any(not str(row["position_rank"]).strip() for row in rows):
        raise FantasyProsFetchError("Position rank is missing after normalization")

    for row in rows:
        name = str(row["name"])
        rank_min = row["rank_min"]
        rank_max = row["rank_max"]
        rank_ave = row["rank_ave"]
        rank_std = row["rank_std"]

        if rank_min != "" and rank_max != "":
            minimum = int(rank_min)
            maximum = int(rank_max)
            if minimum > maximum:
                raise FantasyProsFetchError(
                    f"rank_min exceeds rank_max for {name}: {minimum} > {maximum}"
                )
            # rank_ecr is FantasyPros' final published consensus ordering. It is
            # not guaranteed to be bounded by the best/worst submitted expert
            # ranks, so outside-range ECR values are diagnostics rather than
            # malformed source data. The arithmetic mean must still remain
            # within the expert range when all three fields are present.
            if rank_ave != "" and not Decimal(minimum) <= rank_ave <= Decimal(maximum):
                raise FantasyProsFetchError(
                    f"rank_ave is outside rank_min/rank_max for {name}: {rank_ave}"
                )
        if rank_std != "" and rank_std < 0:
            raise FantasyProsFetchError(f"rank_std is negative for {name}: {rank_std}")


def render_csv(rows: Iterable[dict[str, Any]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=CSV_FIELDS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_raw_json(data: dict[str, Any]) -> str:
    """Serialize the complete parsed ecrData payload without dropping fields."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


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
    """Refresh when payload or normalized schema differs from the published snapshot."""
    metadata = latest_snapshot_metadata(repo_root)
    if metadata is None:
        return True
    snapshot = metadata.get("snapshot")
    if not isinstance(snapshot, dict):
        return True
    if metadata.get("schema_version") != SCHEMA_VERSION:
        return True
    if snapshot.get("csv_columns") != CSV_FIELDS:
        return True
    previous_hash = snapshot.get("raw_data_sha256")
    if not isinstance(previous_hash, str) or not previous_hash:
        return True
    current_hash = hashlib.sha256(render_raw_json(ecr_data).encode("utf-8")).hexdigest()
    return current_hash != previous_hash


def raw_payload_changed(*, repo_root: Path, ecr_data: dict[str, Any]) -> bool:
    """Backward-compatible alias that now also detects normalized schema changes."""
    return snapshot_needs_refresh(repo_root=repo_root, ecr_data=ecr_data)


def raw_schema_summary(data: dict[str, Any]) -> dict[str, Any]:
    players = data.get("players")
    player_fields: set[str] = set()
    if isinstance(players, list):
        for player in players:
            if isinstance(player, dict):
                player_fields.update(str(key) for key in player.keys())
    return {
        "top_level_keys": sorted(str(key) for key in data.keys()),
        "player_count": len(players) if isinstance(players, list) else 0,
        "player_field_names": sorted(player_fields),
    }


def consensus_field_coverage(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(1 for row in rows if row.get(field) not in (None, ""))
        for field in CONSENSUS_FIELDS
    }


def consensus_relationship_diagnostics(
    rows: list[dict[str, Any]], *, sample_limit: int = 20
) -> dict[str, Any]:
    """Describe valid cross-field relationships that merit analyst attention.

    FantasyPros can publish a final ``rank_ecr`` outside the submitted-expert
    ``rank_min``/``rank_max`` interval. Preserve those source values and surface
    them as diagnostics instead of rejecting the complete snapshot.
    """
    samples: list[dict[str, Any]] = []
    count = 0
    for row in rows:
        rank_min = row.get("rank_min")
        rank_max = row.get("rank_max")
        if rank_min in (None, "") or rank_max in (None, ""):
            continue
        rank_ecr = int(row["Rank"])
        minimum = int(rank_min)
        maximum = int(rank_max)
        if minimum <= rank_ecr <= maximum:
            continue
        count += 1
        if len(samples) < sample_limit:
            rank_ave = row.get("rank_ave")
            samples.append(
                {
                    "name": str(row["name"]),
                    "rank_ecr": rank_ecr,
                    "rank_min": minimum,
                    "rank_max": maximum,
                    "rank_ave": "" if rank_ave in (None, "") else str(rank_ave),
                }
            )
    return {
        "ecr_outside_expert_range_count": count,
        "ecr_outside_expert_range_samples": samples,
        "sample_limit": sample_limit,
    }


def build_metadata(
    *,
    rows: list[dict[str, Any]],
    csv_content: str,
    raw_content: str,
    ecr_data: dict[str, Any],
    fetched_at: datetime,
    response_headers: dict[str, str],
) -> dict[str, Any]:
    ranks = [int(row["Rank"]) for row in rows]
    missing_ranks = sorted(set(range(min(ranks), max(ranks) + 1)) - set(ranks))
    position_counts = Counter(str(row["position"]) for row in rows)
    position_rank_sources = Counter(str(row["position_rank_source"]) for row in rows)

    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": "FantasyPros",
        "ranking_id": RANKING_ID,
        "ranking_name": "Dynasty Superflex PPR ECR",
        "ranking_type": "expert_consensus_ranking",
        "official_source_url": SOURCE_URL,
        "fetched_at": fetched_at.isoformat(),
        "season_label": fetched_at.year,
        "format": {
            "dynasty": True,
            "scoring": "ppr",
            "superflex": True,
            "fixed_two_qb": False,
            "two_qb_analysis_proxy": True,
            "te_premium": False,
            "idp_included": False,
        },
        "snapshot": {
            "snapshot_date": fetched_at.date().isoformat(),
            "ranking_file": "ranking.csv",
            "raw_data_file": "raw-ecr-data.json",
            "row_count": len(rows),
            "rank_min": min(ranks),
            "rank_max": max(ranks),
            "missing_ranks": missing_ranks,
            "position_counts": dict(sorted(position_counts.items())),
            "position_rank_source_counts": dict(sorted(position_rank_sources.items())),
            "consensus_field_coverage": consensus_field_coverage(rows),
            "consensus_relationship_diagnostics": consensus_relationship_diagnostics(rows),
            "csv_columns": CSV_FIELDS,
            "ranking_sha256": hashlib.sha256(csv_content.encode("utf-8")).hexdigest(),
            "raw_data_sha256": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
        },
        "raw_schema": raw_schema_summary(ecr_data),
        "extraction_provenance": {
            "method": "direct_official_html_ecrData",
            "uses_mirror": False,
            "raw_payload_semantics": (
                "Complete parsed ecrData object; JSON whitespace is normalized but fields are not dropped."
            ),
            "response_headers": response_headers,
        },
        "freshness": {
            "status": "live_fetch",
            "refresh_before_value_sensitive_analysis": True,
        },
        "analysis_usage": {
            "role": "External expert-consensus context",
            "not_adp": True,
            "not_league_specific": True,
            "consensus_metrics": {
                "tier": "FantasyPros value cluster; prefer tier breaks over small rank gaps.",
                "rank_min_rank_max": (
                    "Best and worst submitted expert ranks; range can be influenced by outliers "
                    "and is not guaranteed to contain the final published rank_ecr."
                ),
                "rank_ave": "Mean submitted expert rank.",
                "rank_std": "Dispersion of expert ranks; lower values indicate tighter agreement.",
            },
            "league_adjustment": (
                "Use as a Superflex proxy. In the Mighty Giants league with two fixed QB "
                "starters, quarterbacks may require an additional scarcity boost."
            ),
        },
    }


def write_snapshot(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    ecr_data: dict[str, Any],
    fetched_at: datetime,
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
        "direct_fetcher": "fantasy-management/_ai/scripts/fetch_fantasypros_dynasty_superflex.py",
        "refresh_before_value_sensitive_analysis": True,
    }

    # Write the snapshot files before moving latest.json. A failed write must not
    # publish a pointer to an incomplete snapshot.
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


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.from_file:
            html = args.from_file.read_text(encoding="utf-8")
            response_headers: dict[str, str] = {}
        else:
            html, response_headers = fetch_html(args.url, timeout=args.timeout)

        data = extract_ecr_data(html)
        rows = parse_players(data)
        relationship_diagnostics = consensus_relationship_diagnostics(rows)
        mismatch_count = relationship_diagnostics["ecr_outside_expert_range_count"]
        if mismatch_count:
            print(
                f"[fantasypros] note: {mismatch_count} rows have rank_ecr outside "
                "rank_min/rank_max; source values retained",
                file=sys.stderr,
            )
        fetched_at = parse_timestamp(args.fetched_at)
        repo_root = args.repo_root.resolve()

        if args.dry_run:
            counts = Counter(row["position"] for row in rows)
            position_rank_sources = Counter(row["position_rank_source"] for row in rows)
            coverage = consensus_field_coverage(rows)
            print(
                f"FantasyPros rows={len(rows)} "
                + " ".join(f"{key}={counts[key]}" for key in sorted(counts))
                + " position_rank="
                + "/".join(
                    f"{key}:{position_rank_sources[key]}" for key in sorted(position_rank_sources)
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
            print("[fantasypros] payload and normalized schema unchanged; no snapshot written")
            return 0

        paths = write_snapshot(
            repo_root=repo_root,
            rows=rows,
            ecr_data=data,
            fetched_at=fetched_at,
            response_headers=response_headers,
        )
    except (FantasyProsFetchError, OSError, ValueError) as exc:
        print(f"[fantasypros] {exc}", file=sys.stderr)
        return 1

    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
