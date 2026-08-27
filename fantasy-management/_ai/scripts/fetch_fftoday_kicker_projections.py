#!/usr/bin/env python3
"""Fetch, validate and materialize FFToday preseason kicker projections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from http_fetch_resilience import HttpFetchError, fetch_text_with_retry

SOURCE_ID = "fftoday"
SOURCE_NAME = "FFToday"
RANKING_KIND = "projections"
RANKING_ID = "redraft-kicker-preseason"
RANKING_NAME = "FFToday Preseason Kicker Projections"
SCHEMA_VERSION = 1
MIN_ROWS = 20
DEFAULT_MAX_STALE_DAYS = 45
SOURCE_ROOT = "fantasy-management/sources/external-rankings/projections/fftoday"
ANALYSIS_METADATA = f"{SOURCE_ROOT}/analysis-metadata.json"
DIRECT_FETCHER = "fantasy-management/_ai/scripts/fetch_fftoday_kicker_projections.py"
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"
CSV_FIELDS = [
    "name", "Rank", "source_rank", "position", "team", "source_player_id",
    "bye", "fgm", "fga", "fg_pct", "epm", "epa",
    "projected_fantasy_points", "source_updated_date", "season",
]


class FFTodayProjectionError(RuntimeError):
    """Raised when the public FFToday projection page is not safe to publish."""


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
        "https://www.fftoday.com/rankings/playerproj.php?"
        f"LeagueID=&PosID=80&Season={season}&order_by=FFPts&sort_order=DESC"
    )


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_html(url: str, timeout: int) -> tuple[str, dict[str, str]]:
    try:
        return fetch_text_with_retry(
            url,
            timeout=timeout,
            source_name=SOURCE_NAME,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
    except HttpFetchError as exc:
        raise FFTodayProjectionError(str(exc)) from exc


def _decimal(value: str, field: str, name: str, minimum: Decimal = Decimal("0")) -> Decimal:
    cleaned = value.replace(",", "").replace("%", "").strip()
    try:
        parsed = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise FFTodayProjectionError(
            f"Invalid FFToday {field} for {name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < minimum:
        raise FFTodayProjectionError(
            f"Invalid FFToday {field} for {name}: {value!r}"
        )
    return parsed


def _integer(value: str, field: str, name: str, minimum: int = 0) -> int:
    parsed = _decimal(value, field, name, Decimal(minimum))
    if parsed != parsed.to_integral_value():
        raise FFTodayProjectionError(
            f"FFToday {field} for {name} must be an integer: {value!r}"
        )
    return int(parsed)


def _csv_number(value: Decimal) -> int | str:
    if value == value.to_integral_value():
        return int(value)
    return format(value.normalize(), "f")


def parse_projection_html(
    html: str,
    *,
    season: int,
    fetched_at: datetime,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parser = TableParser()
    parser.feed(html)
    text = parser.page_text

    if not re.search(rf"Kicker\s+Projections:\s*{season}\b", text, re.IGNORECASE):
        raise FFTodayProjectionError(
            f"Unexpected FFToday source identity; expected Kicker Projections: {season}"
        )
    updated_match = re.search(
        r"Regular\s+Season,\s*Updated:\s*(\d{1,2})/(\d{1,2})/(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not updated_match:
        raise FFTodayProjectionError("FFToday projection update date not found")
    updated = date(
        int(updated_match.group(3)),
        int(updated_match.group(1)),
        int(updated_match.group(2)),
    )
    if updated.year != season:
        raise FFTodayProjectionError(
            f"FFToday update date does not match season: {updated.isoformat()}"
        )
    if updated > fetched_at.date():
        raise FFTodayProjectionError(
            f"FFToday update date is in the future: {updated.isoformat()}"
        )
    age_days = (fetched_at.date() - updated).days
    if age_days > max_stale_days:
        raise FFTodayProjectionError(f"stale FFToday projections: {age_days} days old")

    if any("next page" in link["text"].casefold() for link in parser.links):
        raise FFTodayProjectionError(
            "FFToday kicker projections became paginated; parser requires completeness review"
        )

    scoring_match = re.search(r"([A-Za-z0-9 .+\-/]+?)\s+Scoring:\s*Review\s+Scoring", text)
    scoring_label = scoring_match.group(1).strip() if scoring_match else "FFToday default"

    player_href = re.compile(r"/stats/players/(\d+)/", re.IGNORECASE)
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()

    for cells in parser.rows:
        player_index = None
        player_id = None
        player_name = None
        for index, cell in enumerate(cells):
            for link in cell["links"]:
                match = player_href.search(link["href"])
                if match:
                    player_index = index
                    player_id = match.group(1)
                    player_name = link["text"].strip()
                    break
            if player_index is not None:
                break
        if player_index is None or not player_id or not player_name:
            continue

        following = [str(cell["text"]).strip() for cell in cells[player_index + 1:]]
        if len(following) < 8:
            raise FFTodayProjectionError(
                f"Unexpected FFToday kicker row shape for {player_name}: {following!r}"
            )
        team, bye_s, fgm_s, fga_s, pct_s, epm_s, epa_s, points_s = following[:8]
        team = team.upper()
        if not re.fullmatch(r"[A-Z]{2,3}", team):
            raise FFTodayProjectionError(
                f"Invalid FFToday team for {player_name}: {team!r}"
            )
        if player_id in ids:
            raise FFTodayProjectionError(f"Duplicate FFToday player id: {player_id}")
        ids.add(player_id)

        bye = _integer(bye_s, "bye", player_name, 1)
        if bye > 18:
            raise FFTodayProjectionError(f"Invalid FFToday bye for {player_name}: {bye}")
        fgm = _integer(fgm_s, "FGM", player_name)
        fga = _integer(fga_s, "FGA", player_name)
        fg_pct = _decimal(pct_s, "FG%", player_name)
        epm = _integer(epm_s, "EPM", player_name)
        epa = _integer(epa_s, "EPA", player_name)
        points = _decimal(points_s, "FPts", player_name)
        if fgm > fga:
            raise FFTodayProjectionError(f"FFToday FGM exceeds FGA for {player_name}")
        if epm > epa:
            raise FFTodayProjectionError(f"FFToday EPM exceeds EPA for {player_name}")
        if fg_pct > 100:
            raise FFTodayProjectionError(f"FFToday FG% above 100 for {player_name}")
        if fga > 0:
            expected_pct = (Decimal(fgm) / Decimal(fga)) * Decimal(100)
            if abs(expected_pct - fg_pct) > Decimal("0.2"):
                raise FFTodayProjectionError(
                    f"FFToday FG% inconsistent for {player_name}: {fg_pct} vs {expected_pct}"
                )

        rows.append({
            "name": player_name,
            "Rank": 0,
            "source_rank": len(rows) + 1,
            "position": "K",
            "team": team,
            "source_player_id": player_id,
            "bye": bye,
            "fgm": fgm,
            "fga": fga,
            "fg_pct": _csv_number(fg_pct),
            "epm": epm,
            "epa": epa,
            "projected_fantasy_points": _csv_number(points),
            "source_updated_date": updated.isoformat(),
            "season": season,
            "_points": points,
        })

    if len(rows) < MIN_ROWS:
        raise FFTodayProjectionError(f"Too few FFToday kicker projection rows: {len(rows)}")

    rows.sort(
        key=lambda row: (
            -row["_points"],
            -row["fgm"],
            -row["epm"],
            row["source_player_id"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row.pop("_points")

    return rows, {
        "source_updated_date": updated.isoformat(),
        "source_age_days": age_days,
        "source_scoring_label": scoring_label,
        "row_count": len(rows),
        "unique_source_player_ids": len(ids) == len(rows),
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
            "source_updated_date": diagnostics["source_updated_date"],
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
        "source_updated_date": diagnostics["source_updated_date"],
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
        "source_updated_date": diagnostics["source_updated_date"],
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
    parser.add_argument("--max-stale-days", type=int, default=DEFAULT_MAX_STALE_DAYS)
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
        if args.season < 2000 or args.max_stale_days < 0:
            raise ValueError("Invalid season or max-stale-days")
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
            max_stale_days=args.max_stale_days,
        )
        if args.dry_run:
            print(
                f"FFToday projections ranking={RANKING_ID} rows={len(rows)} "
                f"updated={diagnostics['source_updated_date']} "
                f"scoring={diagnostics['source_scoring_label']}"
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
        print(f"[fftoday-projections:kicker] {action}")
        for path in paths:
            print(path)
        return 0
    except (FFTodayProjectionError, OSError, ValueError) as exc:
        print(f"[fftoday-projections] {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
