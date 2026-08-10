#!/usr/bin/env python3
"""Fetch and materialize public CBS Sports QB/RB/WR/TE season projections."""
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
SCHEMA_VERSION = 1
SOURCE_ROOT = "fantasy-management/sources/external-rankings/projections/cbs-sports"
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"
POSITIONS = {
    "QB": {
        "label": "Quarterback",
        "source_positions": ["QB"],
        "fields": ["games_played", "pass_attempts", "pass_completions", "pass_yards", "pass_yards_per_game", "pass_touchdowns", "interceptions", "passer_rating", "rush_attempts", "rush_yards", "rush_average", "rush_touchdowns", "fumbles_lost", "projected_fantasy_points", "projected_fantasy_points_per_game"],
    },
    "RB": {
        "label": "Running Back",
        "source_positions": ["RB", "FB"],
        "fields": ["games_played", "rush_attempts", "rush_yards", "rush_average", "rush_touchdowns", "targets", "receptions", "receiving_yards", "receiving_yards_per_game", "receiving_average", "receiving_touchdowns", "fumbles_lost", "projected_fantasy_points", "projected_fantasy_points_per_game"],
    },
    "WR": {
        "label": "Wide Receiver",
        "source_positions": ["WR"],
        "fields": ["games_played", "targets", "receptions", "receiving_yards", "receiving_yards_per_game", "receiving_average", "receiving_touchdowns", "rush_attempts", "rush_yards", "rush_average", "rush_touchdowns", "fumbles_lost", "projected_fantasy_points", "projected_fantasy_points_per_game"],
    },
    "TE": {
        "label": "Tight End",
        "source_positions": ["TE"],
        "fields": ["games_played", "targets", "receptions", "receiving_yards", "receiving_yards_per_game", "receiving_average", "receiving_touchdowns", "fumbles_lost", "projected_fantasy_points", "projected_fantasy_points_per_game"],
    },
}
BASE_FIELDS = ["name", "Rank", "source_rank", "position", "source_position", "team", "source_player_id"]


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
    return f"https://www.cbssports.com/fantasy/football/stats/{position}/{season}/season/projections/nonppr/"


def fetch_html(url: str, timeout: int = 30) -> tuple[str, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            return body, {
                "etag": response.headers.get("ETag") or "",
                "last_modified": response.headers.get("Last-Modified") or "",
                "content_type": response.headers.get("Content-Type") or "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProjectionError(f"CBS Sports fetch failed: {exc}") from exc


def _number(value: str, field: str, name: str) -> Decimal:
    cleaned = value.replace(",", "").replace("%", "").strip()
    if cleaned in {"", "-", "–", "—"}:
        return Decimal("0")
    try:
        parsed = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ProjectionError(f"Invalid CBS {field} for {name}: {value!r}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ProjectionError(f"Invalid CBS {field} for {name}: {value!r}")
    return parsed


def _csv_number(value: Decimal) -> int | str:
    return int(value) if value == value.to_integral_value() else format(value.normalize(), "f")


def parse_projection_html(html: str, *, position: str, season: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    position = position.upper()
    config = POSITIONS.get(position)
    if not config:
        raise ProjectionError(f"Unsupported CBS position: {position}")
    parser = TableParser()
    parser.feed(html)
    text = parser.page_text
    if not re.search(rf"\b{season}\s+Projections\s+Fantasy\s+Football\s+{re.escape(config['label'])}\s+Stats\b", text, re.IGNORECASE):
        raise ProjectionError(f"Unexpected CBS source identity for {position} {season}")
    if not re.search(r"\bNon-PPR\b", text, re.IGNORECASE):
        raise ProjectionError("CBS Non-PPR source context not found")
    if any(link["text"].strip().casefold() in {"next", "next page"} for link in parser.links):
        raise ProjectionError(f"CBS {position} projections became paginated")

    player_href = re.compile(r"/nfl/players/(\d+)/", re.IGNORECASE)
    source_position_team = re.compile(r"\b(QB|RB|FB|WR|TE)\s+([A-Z]{2,3})\b")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for cells in parser.rows:
        player_index: int | None = None
        player_id: str | None = None
        player_name: str | None = None
        for index, cell in enumerate(cells):
            matches: list[tuple[str, str]] = []
            for link in cell["links"]:
                match = player_href.search(link["href"])
                if match and link["text"].strip():
                    matches.append((match.group(1), link["text"].strip()))
            if matches:
                player_index = index
                player_id = matches[0][0]
                player_name = max((value[1] for value in matches), key=len)
                break
        if player_index is None or not player_id or not player_name:
            continue
        if player_id in ids:
            raise ProjectionError(f"Duplicate CBS player id: {player_id}")
        ids.add(player_id)
        player_cell_text = str(cells[player_index]["text"])
        position_team_match = source_position_team.search(player_cell_text)
        if not position_team_match:
            raise ProjectionError(f"CBS position/team could not be resolved for {player_name}: {player_cell_text!r}")
        source_position = position_team_match.group(1)
        if source_position not in config["source_positions"]:
            raise ProjectionError(
                f"Unexpected CBS source position {source_position} on {position} page for {player_name}"
            )
        team = position_team_match.group(2)
        following = [str(cell["text"]).strip() for cell in cells[player_index + 1:]]
        fields = config["fields"]
        if len(following) < len(fields):
            raise ProjectionError(f"Unexpected CBS {position} row shape for {player_name}: {following!r}")
        parsed = {field: _csv_number(_number(value, field, player_name)) for field, value in zip(fields, following[:len(fields)])}
        games = Decimal(str(parsed["games_played"]))
        points = Decimal(str(parsed["projected_fantasy_points"]))
        points_per_game = Decimal(str(parsed["projected_fantasy_points_per_game"]))
        if games > 18:
            raise ProjectionError(f"Invalid CBS games played for {player_name}: {games}")
        if games > 0 and abs(points / games - points_per_game) > Decimal("0.2"):
            raise ProjectionError(f"CBS FPPG inconsistent for {player_name}")
        rows.append({
            "name": player_name,
            "Rank": 0,
            "source_rank": len(rows) + 1,
            "position": position,
            "source_position": source_position,
            "team": team,
            "source_player_id": player_id,
            **parsed,
            "season": season,
            "_points": points,
        })
    if len(rows) < 20:
        raise ProjectionError(f"Too few CBS {position} projection rows: {len(rows)}")
    rows.sort(key=lambda row: (-row["_points"], row["source_player_id"]))
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row.pop("_points")
    return rows, {"row_count": len(rows), "source_update_timestamp_available": False, "pagination_detected": False}


def ranking_id(position: str) -> str:
    return f"redraft-{position.lower()}-preseason"


def ranking_root(repo_root: Path, position: str) -> Path:
    return repo_root / SOURCE_ROOT / ranking_id(position)


def _render_csv(rows: list[dict[str, Any]], position: str) -> str:
    fields = BASE_FIELDS + POSITIONS[position]["fields"] + ["season"]
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


def write_projection(*, repo_root: Path, position: str, rows: list[dict[str, Any]], html: str, diagnostics: dict[str, Any], fetched_at: datetime, source_url_value: str, response_headers: dict[str, str], season: int, skip_unchanged: bool) -> tuple[list[Path], bool]:
    root = ranking_root(repo_root, position)
    raw_path = root / "raw-latest.html"
    latest_path = root / "latest.json"
    snapshot_date = fetched_at.date().isoformat()
    csv_text = _render_csv(rows, position)
    ranking_sha = _digest(csv_text)
    raw_sha = _digest(html)
    previous = _read_json(latest_path)
    _atomic_write(raw_path, html)
    if skip_unchanged and previous and previous.get("ranking_sha256") == ranking_sha:
        updated = dict(previous)
        updated.update({"raw_fetched_at": fetched_at.isoformat(), "raw_sha256": raw_sha, "source_url": source_url_value, "source_update_timestamp_available": False})
        _atomic_write(latest_path, json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        return [raw_path, latest_path], False

    snapshot_dir = root / "snapshots" / snapshot_date
    ranking_path = snapshot_dir / "ranking.csv"
    metadata_path = snapshot_dir / "metadata.json"
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "ranking_kind": RANKING_KIND,
        "ranking_id": ranking_id(position),
        "ranking_name": f"CBS Sports Preseason {position} Projections",
        "position": position,
        "season": season,
        "source_format": "nonppr",
        "source_url": source_url_value,
        "fetched_at": fetched_at.isoformat(),
        "source_update_timestamp_available": False,
        "row_count": len(rows),
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "http": response_headers,
        "diagnostics": diagnostics,
        "provider_points_are_league_points": False,
    }
    _atomic_write(ranking_path, csv_text)
    _atomic_write(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    pointer = {
        "schema_version": SCHEMA_VERSION,
        "ranking_id": ranking_id(position),
        "ranking_file": ranking_path.relative_to(repo_root).as_posix(),
        "metadata_file": metadata_path.relative_to(repo_root).as_posix(),
        "snapshot_date": snapshot_date,
        "ranking_fetched_at": fetched_at.isoformat(),
        "raw_fetched_at": fetched_at.isoformat(),
        "source_update_timestamp_available": False,
        "ranking_sha256": ranking_sha,
        "raw_sha256": raw_sha,
        "source_url": source_url_value,
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
        html, headers = fetch_html(source_url(position, args.season))
        rows, diagnostics = parse_projection_html(html, position=position, season=args.season)
        if args.dry_run:
            print(position, len(rows))
            continue
        paths, created = write_projection(repo_root=Path(args.repo_root), position=position, rows=rows, html=html, diagnostics=diagnostics, fetched_at=fetched_at, source_url_value=source_url(position, args.season), response_headers=headers, season=args.season, skip_unchanged=args.skip_unchanged)
        print(position, "snapshot" if created else "unchanged", *(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
