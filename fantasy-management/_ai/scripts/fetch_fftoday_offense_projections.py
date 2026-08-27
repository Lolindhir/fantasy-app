#!/usr/bin/env python3
"""Fetch and materialize public FFToday QB/RB/WR/TE season projections."""
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
from urllib.parse import urljoin

from http_fetch_resilience import HttpFetchError, fetch_text_with_retry

SOURCE_ID = "fftoday"
SOURCE_NAME = "FFToday"
RANKING_KIND = "projections"
SCHEMA_VERSION = 1
DEFAULT_MAX_STALE_DAYS = 45
SOURCE_ROOT = "fantasy-management/sources/external-rankings/projections/fftoday"
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"
POSITIONS = {
    "QB": {"pos_id": 10, "label": "Quarterback", "fields": ["bye", "pass_completions", "pass_attempts", "pass_yards", "pass_touchdowns", "interceptions", "rush_attempts", "rush_yards", "rush_touchdowns", "projected_fantasy_points"]},
    "RB": {"pos_id": 20, "label": "Running Back", "fields": ["bye", "rush_attempts", "rush_yards", "rush_touchdowns", "receptions", "receiving_yards", "receiving_touchdowns", "projected_fantasy_points"]},
    "WR": {"pos_id": 30, "label": "Wide Receiver", "fields": ["bye", "receptions", "receiving_yards", "receiving_touchdowns", "rush_attempts", "rush_yards", "rush_touchdowns", "projected_fantasy_points"]},
    "TE": {"pos_id": 40, "label": "Tight End", "fields": ["bye", "receptions", "receiving_yards", "receiving_touchdowns", "projected_fantasy_points"]},
}
BASE_FIELDS = ["name", "Rank", "source_rank", "position", "team", "source_player_id"]


class ProjectionError(RuntimeError):
    pass


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
            anchor = {"href": self._anchor["href"], "text": " ".join(self._anchor["text"].split())}
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


def source_url(position: str, season: int) -> str:
    config = POSITIONS[position.upper()]
    return f"https://www.fftoday.com/rankings/playerproj.php?LeagueID=&PosID={config['pos_id']}&Season={season}&order_by=FFPts&sort_order=DESC"


def fetch_html(url: str, timeout: int = 30) -> tuple[str, dict[str, str]]:
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
        raise ProjectionError(str(exc)) from exc


def _number(value: str, field: str, name: str) -> Decimal:
    cleaned = str(value).replace(",", "").replace("%", "").strip()
    try:
        parsed = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ProjectionError(f"Invalid FFToday {field} for {name}: {value!r}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ProjectionError(f"Invalid FFToday {field} for {name}: {value!r}")
    return parsed


def _csv_number(value: Decimal) -> int | str:
    return int(value) if value == value.to_integral_value() else format(value.normalize(), "f")


def parse_page(html: str, *, position: str, season: int, fetched_at: datetime, max_stale_days: int = DEFAULT_MAX_STALE_DAYS) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    position = position.upper()
    config = POSITIONS.get(position)
    if not config:
        raise ProjectionError(f"Unsupported FFToday position: {position}")
    parser = TableParser()
    parser.feed(html)
    text = parser.page_text
    if not re.search(rf"{re.escape(config['label'])}\s+Projections:\s*{season}\b", text, re.IGNORECASE):
        raise ProjectionError(f"Unexpected FFToday source identity for {position} {season}")
    updated_match = re.search(r"Regular\s+Season,\s*Updated:\s*(\d{1,2})/(\d{1,2})/(\d{4})", text, re.IGNORECASE)
    if not updated_match:
        raise ProjectionError("FFToday projection update date not found")
    updated = date(int(updated_match.group(3)), int(updated_match.group(1)), int(updated_match.group(2)))
    if updated.year != season or updated > fetched_at.date():
        raise ProjectionError(f"Invalid FFToday update date: {updated.isoformat()}")
    age_days = (fetched_at.date() - updated).days
    if age_days > max_stale_days:
        raise ProjectionError(f"stale FFToday projections: {age_days} days old")

    player_href = re.compile(r"/stats/players/(\d+)/", re.IGNORECASE)
    rows: list[dict[str, Any]] = []
    for cells in parser.rows:
        player_index: int | None = None
        player_id: str | None = None
        player_name: str | None = None
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
        needed = 1 + len(config["fields"])
        if len(following) < needed:
            raise ProjectionError(f"Unexpected FFToday {position} row shape for {player_name}: {following!r}")
        team = following[0].upper()
        if not re.fullmatch(r"[A-Z]{2,3}", team):
            raise ProjectionError(f"Invalid FFToday team for {player_name}: {team!r}")
        parsed = {field: _csv_number(_number(value, field, player_name)) for field, value in zip(config["fields"], following[1:needed])}
        rows.append({
            "name": player_name,
            "position": position,
            "team": team,
            "source_player_id": player_id,
            **parsed,
            "source_updated_date": updated.isoformat(),
            "season": season,
        })
    next_href = None
    for link in parser.links:
        if link["text"].strip().casefold() == "next page":
            next_href = link["href"]
            break
    return rows, {"source_updated_date": updated.isoformat(), "source_age_days": age_days}, next_href


def fetch_all_pages(position: str, season: int, fetched_at: datetime, timeout: int = 30) -> tuple[list[dict[str, Any]], dict[str, Any], list[tuple[str, str]], dict[str, str]]:
    url = source_url(position, season)
    seen_urls: set[str] = set()
    pages: list[tuple[str, str]] = []
    rows: list[dict[str, Any]] = []
    source_updated_date: str | None = None
    response_headers: dict[str, str] = {}
    for _ in range(10):
        if url in seen_urls:
            raise ProjectionError(f"FFToday pagination loop for {position}: {url}")
        seen_urls.add(url)
        html, headers = fetch_html(url, timeout)
        response_headers = headers or response_headers
        page_rows, diagnostics, next_href = parse_page(html, position=position, season=season, fetched_at=fetched_at)
        pages.append((url, html))
        rows.extend(page_rows)
        if source_updated_date is None:
            source_updated_date = diagnostics["source_updated_date"]
        elif source_updated_date != diagnostics["source_updated_date"]:
            raise ProjectionError(f"FFToday update date changed across pages for {position}")
        if not next_href:
            break
        url = urljoin(url, next_href)
    else:
        raise ProjectionError(f"Too many FFToday pages for {position}")

    ids = [row["source_player_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ProjectionError(f"Duplicate FFToday player id across pages for {position}")
    if len(rows) < 20:
        raise ProjectionError(f"Too few FFToday {position} projection rows: {len(rows)}")
    rows.sort(key=lambda row: (-Decimal(str(row["projected_fantasy_points"])), row["source_player_id"]))
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row["source_rank"] = rank
    return rows, {
        "source_updated_date": source_updated_date,
        "row_count": len(rows),
        "page_count": len(pages),
        "pagination_detected": len(pages) > 1,
    }, pages, response_headers


def ranking_id(position: str) -> str:
    return f"redraft-{position.lower()}-preseason"


def ranking_root(repo_root: Path, position: str) -> Path:
    return repo_root / SOURCE_ROOT / ranking_id(position)


def _render_csv(rows: list[dict[str, Any]], position: str) -> str:
    fields = BASE_FIELDS + POSITIONS[position]["fields"] + ["source_updated_date", "season"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in fields} for row in rows)
    return output.getvalue()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def write_projection(*, repo_root: Path, position: str, rows: list[dict[str, Any]], pages: list[tuple[str, str]], diagnostics: dict[str, Any], fetched_at: datetime, response_headers: dict[str, str], season: int, skip_unchanged: bool) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root, position)
    raw_path = root / "raw-latest.html"
    latest_path = root / "latest.json"
    snapshot_date = fetched_at.date().isoformat()
    csv_text = _render_csv(rows, position)
    ranking_sha = _digest(csv_text)
    composite_html = "\n\n".join(f"<!-- SOURCE PAGE {index}: {url} -->\n{html}" for index, (url, html) in enumerate(pages, start=1))
    raw_sha = _digest(composite_html)
    previous = _read_json(latest_path)
    _atomic_write(raw_path, composite_html)
    if skip_unchanged and previous and previous.get("ranking_sha256") == ranking_sha:
        updated = dict(previous)
        updated.update({"raw_fetched_at": fetched_at.isoformat(), "raw_sha256": raw_sha, "source_updated_date": diagnostics["source_updated_date"], "source_page_count": diagnostics["page_count"]})
        _atomic_write(latest_path, json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        return [raw_path, latest_path], False

    snapshot_dir = root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    _atomic_write(ranking_path, csv_text)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": RANKING_KIND,
        "ranking_id": ranking_id(position),
        "ranking_name": f"FFToday Preseason {position} Projections",
        "position": position,
        "season": season,
        "source_urls": [url for url, _ in pages],
        "fetched_at": fetched_at.isoformat(),
        "source_updated_date": diagnostics["source_updated_date"],
        "source_page_count": diagnostics["page_count"],
        "row_count": len(rows),
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "http": response_headers,
        "diagnostics": diagnostics,
        "provider_points_are_league_points": False,
    }
    _atomic_write(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    pointer = {
        "schema_version": SCHEMA_VERSION,
        "ranking_id": ranking_id(position),
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "snapshot_date": snapshot_date,
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "source_updated_date": diagnostics["source_updated_date"],
        "source_page_count": diagnostics["page_count"],
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "source_url": pages[0][0],
    }
    _atomic_write(latest_path, json.dumps(pointer, indent=2, ensure_ascii=False) + "\n")
    return [raw_path, ranking_path, metadata_path, latest_path], True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--season", type=int, default=datetime.now().year)
    parser.add_argument("--positions", default="QB,RB,WR,TE")
    parser.add_argument("--skip-unchanged", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fetched_at = datetime.now(timezone.utc)
    for position in [value.strip().upper() for value in args.positions.split(",") if value.strip()]:
        rows, diagnostics, pages, headers = fetch_all_pages(position, args.season, fetched_at)
        if args.dry_run:
            print(position, len(rows), diagnostics["page_count"])
            continue
        paths, created = write_projection(repo_root=Path(args.repo_root), position=position, rows=rows, pages=pages, diagnostics=diagnostics, fetched_at=fetched_at, response_headers=headers, season=args.season, skip_unchanged=args.skip_unchanged)
        print(position, "snapshot" if created else "unchanged", *(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
