#!/usr/bin/env python3
"""Fetch, validate and materialize CBS Sports preseason kicker projections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

SOURCE_ID = "cbs-sports"
SOURCE_NAME = "CBS Sports"
RANKING_KIND = "projections"
RANKING_ID = "redraft-kicker-preseason"
RANKING_NAME = "CBS Sports Preseason Kicker Projections"
SCHEMA_VERSION = 1
MIN_ROWS = 20
SOURCE_ROOT = "fantasy-management/sources/external-rankings/projections/cbs-sports"
ANALYSIS_METADATA = f"{SOURCE_ROOT}/analysis-metadata.json"
DIRECT_FETCHER = "fantasy-management/_ai/scripts/fetch_cbs_sports_kicker_projections.py"
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"
CSV_FIELDS = [
    "name",
    "Rank",
    "source_rank",
    "position",
    "team",
    "source_player_id",
    "games_played",
    "fgm",
    "fga",
    "longest_field_goal",
    "fg_1_19_made",
    "fg_1_19_attempts",
    "fg_20_29_made",
    "fg_20_29_attempts",
    "fg_30_39_made",
    "fg_30_39_attempts",
    "fg_40_49_made",
    "fg_40_49_attempts",
    "fg_50_plus_made",
    "fg_50_plus_attempts",
    "xpm",
    "xpa",
    "projected_fantasy_points",
    "projected_fantasy_points_per_game",
    "season",
]


class CBSSportsProjectionError(RuntimeError):
    """Raised when the public CBS Sports projection page is not safe to publish."""


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, Any]]] = []
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None
        self._anchor: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = {"text": [], "links": []}
        elif tag == "a":
            self._anchor = {"href": values.get("href", ""), "text": ""}

    def handle_data(self, data: str) -> None:
        if data:
            self.text_parts.append(data)
        if self._cell is not None:
            self._cell["text"].append(data)
        if self._anchor is not None:
            self._anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor is not None:
            anchor = {
                "href": self._anchor["href"],
                "text": " ".join(self._anchor["text"].split()),
            }
            self.links.append(anchor)
            if self._cell is not None:
                self._cell["links"].append(anchor)
            self._anchor = None
        elif tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join("".join(self._cell["text"]).split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    @property
    def page_text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


def source_url(season: int) -> str:
    return (
        "https://www.cbssports.com/fantasy/football/stats/"
        f"K/{season}/season/projections/nonppr/"
    )


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_html(url: str, timeout: int) -> tuple[str, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
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
        raise CBSSportsProjectionError(f"CBS Sports fetch failed: {exc}") from exc
    return body, headers


def _decimal(value: str, field: str, name: str, minimum: Decimal = Decimal("0")) -> Decimal:
    cleaned = value.replace(",", "").replace("%", "").strip()
    try:
        parsed = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise CBSSportsProjectionError(
            f"Invalid CBS Sports {field} for {name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < minimum:
        raise CBSSportsProjectionError(
            f"Invalid CBS Sports {field} for {name}: {value!r}"
        )
    return parsed


def _integer(value: str, field: str, name: str, minimum: int = 0) -> int:
    parsed = _decimal(value, field, name, Decimal(minimum))
    if parsed != parsed.to_integral_value():
        raise CBSSportsProjectionError(
            f"CBS Sports {field} for {name} must be an integer: {value!r}"
        )
    return int(parsed)


def _optional_integer(value: str, field: str, name: str) -> int | None:
    if value.strip() in {"", "-", "–", "—"}:
        return None
    return _integer(value, field, name)


def _optional_decimal(value: str, field: str, name: str) -> Decimal | None:
    if value.strip() in {"", "-", "–", "—"}:
        return None
    return _decimal(value, field, name)


def _csv_number(value: Decimal) -> int | str:
    if value == value.to_integral_value():
        return int(value)
    return format(value.normalize(), "f")


def _validate_page_identity(text: str, season: int) -> None:
    if not re.search(
        rf"\b{season}\s+Projections\s+Fantasy\s+Football\s+Kicker\s+Stats\b",
        text,
        re.IGNORECASE,
    ):
        raise CBSSportsProjectionError(
            f"Unexpected CBS Sports source identity; expected {season} Kicker projections"
        )
    required_headers = [
        "Games Played",
        "Field Goals Made",
        "Field Goal Attempts",
        "Field Goals 50+ Yards",
        "Extra Points Made",
        "Extra Points Attempted",
        "Fantasy Points Per Game",
    ]
    missing = [header for header in required_headers if header.casefold() not in text.casefold()]
    if missing:
        raise CBSSportsProjectionError(
            "CBS Sports kicker projection headers changed or are incomplete: "
            + ", ".join(missing)
        )
    if not re.search(r"\bNon-PPR\b", text, re.IGNORECASE):
        raise CBSSportsProjectionError("CBS Sports Non-PPR source context not found")


def parse_projection_html(
    html: str,
    *,
    season: int,
    fetched_at: datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    del fetched_at  # CBS exposes no reliable projection-updated timestamp on this surface.
    parser = TableParser()
    parser.feed(html)
    text = parser.page_text
    _validate_page_identity(text, season)

    if any(
        link["text"].strip().casefold() in {"next", "next page"}
        for link in parser.links
    ):
        raise CBSSportsProjectionError(
            "CBS Sports kicker projections became paginated; parser requires completeness review"
        )

    player_href = re.compile(r"/nfl/players/(\d+)/", re.IGNORECASE)
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()

    for cells in parser.rows:
        player_index: int | None = None
        player_id: str | None = None
        player_name: str | None = None
        for index, cell in enumerate(cells):
            matching_links: list[tuple[str, str]] = []
            for link in cell["links"]:
                match = player_href.search(link["href"])
                if match and link["text"].strip():
                    matching_links.append((match.group(1), link["text"].strip()))
            if matching_links:
                player_index = index
                player_id = matching_links[0][0]
                player_name = max((value[1] for value in matching_links), key=len)
                break
        if player_index is None or not player_id or not player_name:
            continue

        player_cell_text = str(cells[player_index]["text"])
        team_match = re.search(r"\bK\s+([A-Z]{2,3})\b", player_cell_text)
        if not team_match:
            raise CBSSportsProjectionError(
                f"CBS Sports team could not be resolved for {player_name}: {player_cell_text!r}"
            )
        team = team_match.group(1).upper()

        following = [str(cell["text"]).strip() for cell in cells[player_index + 1:]]
        if len(following) < 18:
            raise CBSSportsProjectionError(
                f"Unexpected CBS Sports kicker row shape for {player_name}: {following!r}"
            )
        (
            gp_s,
            fgm_s,
            fga_s,
            longest_s,
            fg_1_19_made_s,
            fg_1_19_attempts_s,
            fg_20_29_made_s,
            fg_20_29_attempts_s,
            fg_30_39_made_s,
            fg_30_39_attempts_s,
            fg_40_49_made_s,
            fg_40_49_attempts_s,
            fg_50_plus_made_s,
            fg_50_plus_attempts_s,
            xpm_s,
            xpa_s,
            fpts_s,
            fppg_s,
        ) = following[:18]

        if player_id in ids:
            raise CBSSportsProjectionError(f"Duplicate CBS Sports player id: {player_id}")
        ids.add(player_id)

        games_played = _integer(gp_s, "games played", player_name)
        if games_played > 18:
            raise CBSSportsProjectionError(
                f"Invalid CBS Sports games played for {player_name}: {games_played}"
            )
        fgm = _integer(fgm_s, "FGM", player_name)
        fga = _integer(fga_s, "FGA", player_name)
        if fgm > fga:
            raise CBSSportsProjectionError(f"CBS Sports FGM exceeds FGA for {player_name}")
        longest = _optional_integer(longest_s, "longest field goal", player_name)

        raw_distance_values = [
            _optional_decimal(fg_1_19_made_s, "FG 1-19 made", player_name),
            _optional_decimal(fg_1_19_attempts_s, "FG 1-19 attempts", player_name),
            _optional_decimal(fg_20_29_made_s, "FG 20-29 made", player_name),
            _optional_decimal(fg_20_29_attempts_s, "FG 20-29 attempts", player_name),
            _optional_decimal(fg_30_39_made_s, "FG 30-39 made", player_name),
            _optional_decimal(fg_30_39_attempts_s, "FG 30-39 attempts", player_name),
            _optional_decimal(fg_40_49_made_s, "FG 40-49 made", player_name),
            _optional_decimal(fg_40_49_attempts_s, "FG 40-49 attempts", player_name),
            _optional_decimal(fg_50_plus_made_s, "FG 50+ made", player_name),
            _optional_decimal(fg_50_plus_attempts_s, "FG 50+ attempts", player_name),
        ]
        if any(value is None for value in raw_distance_values):
            if fgm != 0 or fga != 0:
                raise CBSSportsProjectionError(
                    f"CBS Sports missing distance buckets for non-zero projection: {player_name}"
                )
            distance_values = [Decimal("0") for _ in raw_distance_values]
        else:
            distance_values = [value for value in raw_distance_values if value is not None]
        for offset in range(0, len(distance_values), 2):
            if distance_values[offset] > distance_values[offset + 1]:
                raise CBSSportsProjectionError(
                    f"CBS Sports distance-bucket makes exceed attempts for {player_name}"
                )

        xpm = _integer(xpm_s, "XPM", player_name)
        xpa = _integer(xpa_s, "XPA", player_name)
        if xpm > xpa:
            raise CBSSportsProjectionError(f"CBS Sports XPM exceeds XPA for {player_name}")
        points = _decimal(fpts_s, "FPTS", player_name)
        points_per_game = _decimal(fppg_s, "FPPG", player_name)
        if games_played > 0:
            expected_fppg = points / Decimal(games_played)
            if abs(expected_fppg - points_per_game) > Decimal("0.15"):
                raise CBSSportsProjectionError(
                    f"CBS Sports FPPG inconsistent for {player_name}: "
                    f"{points_per_game} vs {expected_fppg}"
                )
        elif points != 0 or points_per_game != 0:
            raise CBSSportsProjectionError(
                f"CBS Sports non-zero points with zero games for {player_name}"
            )

        rows.append({
            "name": player_name,
            "Rank": 0,
            "source_rank": len(rows) + 1,
            "position": "K",
            "team": team,
            "source_player_id": player_id,
            "games_played": games_played,
            "fgm": fgm,
            "fga": fga,
            "longest_field_goal": "" if longest is None else longest,
            "fg_1_19_made": _csv_number(distance_values[0]),
            "fg_1_19_attempts": _csv_number(distance_values[1]),
            "fg_20_29_made": _csv_number(distance_values[2]),
            "fg_20_29_attempts": _csv_number(distance_values[3]),
            "fg_30_39_made": _csv_number(distance_values[4]),
            "fg_30_39_attempts": _csv_number(distance_values[5]),
            "fg_40_49_made": _csv_number(distance_values[6]),
            "fg_40_49_attempts": _csv_number(distance_values[7]),
            "fg_50_plus_made": _csv_number(distance_values[8]),
            "fg_50_plus_attempts": _csv_number(distance_values[9]),
            "xpm": xpm,
            "xpa": xpa,
            "projected_fantasy_points": _csv_number(points),
            "projected_fantasy_points_per_game": _csv_number(points_per_game),
            "season": season,
            "_points": points,
        })

    if len(rows) < MIN_ROWS:
        raise CBSSportsProjectionError(
            f"Too few CBS Sports kicker projection rows: {len(rows)}"
        )

    rows.sort(
        key=lambda row: (
            -row["_points"],
            -row["fgm"],
            -row["xpm"],
            row["source_player_id"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row.pop("_points")

    return rows, {
        "row_count": len(rows),
        "unique_source_player_ids": len(ids) == len(rows),
        "source_scoring_label": "Non-PPR",
        "source_update_timestamp_available": False,
        "pagination_detected": False,
    }


def _render_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in CSV_FIELDS} for row in rows)
    return output.getvalue()


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


def write_projection(
    *,
    repo_root: Path,
    rows: list[dict[str, Any]],
    html: str,
    diagnostics: dict[str, Any],
    fetched_at: datetime,
    source_url_value: str,
    response_headers: dict[str, str],
    season: int,
    skip_unchanged: bool,
) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root)
    raw_path = root / "raw-latest.html"
    latest_path = root / "latest.json"
    snapshot_dir = root / "snapshots" / fetched_at.date().isoformat()
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    csv_text = _render_csv(rows)
    ranking_sha = _digest(csv_text)
    raw_sha = _digest(html)
    previous = _read_json(latest_path)
    unchanged = bool(
        skip_unchanged
        and previous
        and previous.get("schema_version") == SCHEMA_VERSION
        and previous.get("ranking_sha256") == ranking_sha
    )
    _atomic_write(raw_path, html)
    if unchanged:
        updated = dict(previous)
        updated.update({
            "raw_fetched_at": fetched_at.isoformat(),
            "raw_sha256": raw_sha,
            "source_url": source_url_value,
            "freshness_status": "live_fetch",
        })
        _atomic_write(latest_path, json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        return [raw_path, latest_path], False

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": RANKING_KIND,
        "ranking_id": RANKING_ID,
        "ranking_name": RANKING_NAME,
        "ranking_type": "provider_regular_season_stat_projection_ordered_by_source_fantasy_points",
        "source_url": source_url_value,
        "fetched_at": fetched_at.isoformat(),
        "season_label": season,
        "source_update_timestamp_available": False,
        "format": {
            "dynasty": False,
            "horizon": "preseason_full_regular_season",
            "position": "K",
            "source_scoring_label": diagnostics["source_scoring_label"],
            "custom_scoring_used": False,
            "actual_league_team_count": 6,
            "actual_fixed_kicker_starters": 1,
        },
        "snapshot": {
            "snapshot_date": fetched_at.date().isoformat(),
            "ranking_file": "ranking.csv",
            "metadata_file": "metadata.json",
            "raw_latest_file": "../../raw-latest.html",
            "row_count": len(rows),
            "position_counts": {"K": len(rows)},
            "csv_columns": CSV_FIELDS,
            "ranking_sha256": ranking_sha,
            "source_raw_sha256_at_snapshot": raw_sha,
            "diagnostics": diagnostics,
        },
        "raw_retention": {
            "policy": "latest_only",
            "file_name": "raw-latest.html",
            "historical_raw_snapshots": False,
        },
        "normalized_history": {
            "archived": True,
            "files": ["ranking.csv", "metadata.json"],
            "skip_unchanged": True,
        },
        "extraction_provenance": {
            "method": "public_provider_html_table",
            "uses_login": False,
            "uses_custom_scoring_profile": False,
            "response_headers": response_headers,
        },
        "analysis_usage": {
            "role": "Projected full-season kicker production",
            "not_expert_consensus": True,
            "not_adp": True,
            "not_trade_market_value": True,
            "source_points_are_league_specific": False,
            "rank_comparison": "Use K-only list-length-aware percentiles across ranking sources.",
            "league_adjustment": (
                "Use projected kicking stats as source evidence; apply actual league scoring separately when needed."
            ),
        },
    }
    latest = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "ranking_kind": RANKING_KIND,
        "ranking_id": RANKING_ID,
        "snapshot_date": fetched_at.date().isoformat(),
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "source_update_timestamp_available": False,
        "snapshot_path": snapshot_dir.relative_to(repo_root).as_posix(),
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "raw_latest_file": raw_path.relative_to(repo_root).as_posix(),
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "source_url": source_url_value,
        "freshness_status": "live_fetch",
        "direct_fetcher": DIRECT_FETCHER,
        "analysis_metadata_file": ANALYSIS_METADATA,
        "refresh_before_value_sensitive_analysis": True,
    }
    _atomic_write(ranking_path, csv_text)
    _atomic_write(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    _atomic_write(latest_path, json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return [raw_path, ranking_path, metadata_path, latest_path], True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--fetched-at")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.season < 2000:
            raise ValueError("Invalid season")
        fetched_at = parse_timestamp(args.fetched_at)
        url = source_url(args.season)
        if args.input:
            html = args.input.read_text(encoding="utf-8")
            headers: dict[str, str] = {}
        else:
            html, headers = fetch_html(url, args.timeout)
        rows, diagnostics = parse_projection_html(
            html,
            season=args.season,
            fetched_at=fetched_at,
        )
        if args.dry_run:
            print(
                f"CBS Sports projections ranking={RANKING_ID} rows={len(rows)} "
                f"scoring={diagnostics['source_scoring_label']} "
                "source_updated=unavailable"
            )
            return 0
        paths, created = write_projection(
            repo_root=args.repo_root.resolve(),
            rows=rows,
            html=html,
            diagnostics=diagnostics,
            fetched_at=fetched_at,
            source_url_value=url,
            response_headers=headers,
            season=args.season,
            skip_unchanged=args.skip_unchanged,
        )
        action = "snapshot-created" if created else "ranking-unchanged"
        print(f"[cbs-sports-projections:kicker] {action}")
        for path in paths:
            print(path)
        return 0
    except (CBSSportsProjectionError, OSError, ValueError) as exc:
        print(f"[cbs-sports-projections] {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
