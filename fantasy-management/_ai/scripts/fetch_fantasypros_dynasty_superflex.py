#!/usr/bin/env python3
"""Fetch FantasyPros Dynasty Superflex ECR directly and store a dated snapshot.

The public FantasyPros rankings page embeds its ranking payload in the HTML as
``ecrData = {...}``. This script downloads that official page directly, extracts
and validates the player rows, then writes:

- ``ranking.csv`` in a dated snapshot folder
- ``metadata.json`` next to the CSV
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
from pathlib import Path
from typing import Any, Iterable

SOURCE_URL = "https://www.fantasypros.com/nfl/rankings/dynasty-superflex.php"
SOURCE_ID = "fantasypros"
RANKING_ID = "dynasty-superflex-ppr"
MIN_PLAYER_ROWS = 150
OFFENSIVE_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
CSV_FIELDS = ["name", "Rank", "position", "team"]
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


def parse_players(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
        rows.append({"name": name, "Rank": rank, "position": position, "team": team})

    rows.sort(key=lambda row: row["Rank"])
    validate_rows(rows)
    return rows


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


def render_csv(rows: Iterable[dict[str, Any]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def build_metadata(
    *,
    rows: list[dict[str, Any]],
    csv_content: str,
    fetched_at: datetime,
    response_headers: dict[str, str],
) -> dict[str, Any]:
    ranks = [int(row["Rank"]) for row in rows]
    missing_ranks = sorted(set(range(min(ranks), max(ranks) + 1)) - set(ranks))
    position_counts = Counter(str(row["position"]) for row in rows)

    return {
        "schema_version": 2,
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
            "row_count": len(rows),
            "rank_min": min(ranks),
            "rank_max": max(ranks),
            "missing_ranks": missing_ranks,
            "position_counts": dict(sorted(position_counts.items())),
            "sha256": hashlib.sha256(csv_content.encode("utf-8")).hexdigest(),
        },
        "extraction_provenance": {
            "method": "direct_official_html_ecrData",
            "uses_mirror": False,
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
    fetched_at: datetime,
    response_headers: dict[str, str],
) -> tuple[Path, Path, Path]:
    ranking_root = (
        repo_root
        / "fantasy-management"
        / "sources"
        / "external-rankings"
        / "fantasypros"
        / RANKING_ID
    )
    snapshot_date = fetched_at.date().isoformat()
    snapshot_dir = ranking_root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    latest_path = ranking_root / "latest.json"

    csv_content = render_csv(rows)
    metadata = build_metadata(
        rows=rows,
        csv_content=csv_content,
        fetched_at=fetched_at,
        response_headers=response_headers,
    )
    relative_snapshot = snapshot_dir.relative_to(repo_root).as_posix()
    latest = {
        "schema_version": 2,
        "source_id": SOURCE_ID,
        "ranking_id": RANKING_ID,
        "snapshot_date": snapshot_date,
        "fetched_at": fetched_at.isoformat(),
        "snapshot_path": relative_snapshot,
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "freshness_status": "live_fetch",
        "refresh_before_value_sensitive_analysis": True,
    }

    atomic_write_text(ranking_path, csv_content)
    atomic_write_text(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    atomic_write_text(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return ranking_path, metadata_path, latest_path


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
        fetched_at = parse_timestamp(args.fetched_at)

        if args.dry_run:
            counts = Counter(row["position"] for row in rows)
            print(
                f"FantasyPros rows={len(rows)} "
                + " ".join(f"{key}={counts[key]}" for key in sorted(counts))
            )
            for row in rows[:10]:
                print(row)
            return 0

        paths = write_snapshot(
            repo_root=args.repo_root.resolve(),
            rows=rows,
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
