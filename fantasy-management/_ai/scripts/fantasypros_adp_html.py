"""HTML and export-table extraction helpers for FantasyPros ADP pages."""

from __future__ import annotations

import csv
import io
import re
import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any


class FantasyProsAdpError(RuntimeError):
    """Raised when a FantasyPros ADP page cannot be trusted or normalized."""


def token(value: Any) -> str:
    return "".join(char for char in str(value or "").casefold() if char.isalnum())


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _merge_query(url: str, values: dict[str, Any]) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in values.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )


def build_source_url(
    config: dict[str, Any],
    season: int,
    *,
    current_season: int | None = None,
) -> str:
    """Use the canonical no-query URL for the active season."""
    active = current_season or datetime.now(timezone.utc).year
    return config["url"] if season == active else _merge_query(config["url"], {"year": season})


def build_export_url(
    config: dict[str, Any],
    season: int,
    *,
    current_season: int | None = None,
) -> str:
    return _merge_query(
        build_source_url(config, season, current_season=current_season),
        {"export": "xls"},
    )


class _TableParser(HTMLParser):
    """Collect title, visible document text and lossless-enough table cells."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.document_parts: list[str] = []
        self.tables: list[dict[str, Any]] = []
        self._in_title = False
        self._table: dict[str, Any] | None = None
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None
        self._anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "table":
            self._table = {"attrs": attributes, "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = {
                "tag": tag,
                "attrs": attributes,
                "text_parts": [],
                "links": [],
                "element_attrs": [attributes],
            }
        elif self._cell is not None:
            self._cell["element_attrs"].append(attributes)
            if tag == "a":
                self._anchor = {
                    "href": attributes.get("href", ""),
                    "attrs": attributes,
                    "text_parts": [],
                }

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = _clean_text(" ".join(self._anchor.pop("text_parts")))
            if self._cell is not None:
                self._cell["links"].append(self._anchor)
            self._anchor = None
        elif tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._cell["text"] = _clean_text(" ".join(self._cell.pop("text_parts")))
            self._row.append(self._cell)
            self._cell = None
            self._anchor = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
            self._row = None
            self._cell = None

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        self.document_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if self._cell is not None:
            self._cell["text_parts"].append(data)
        if self._anchor is not None:
            self._anchor["text_parts"].append(data)

    @property
    def title(self) -> str:
        return _clean_text(" ".join(self.title_parts))

    @property
    def document_text(self) -> str:
        return _clean_text(" ".join(self.document_parts))


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_tables(html: str) -> dict[str, Any]:
    parser = _TableParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise FantasyProsAdpError(f"FantasyPros HTML parsing failed: {exc}") from exc
    return {
        "title": parser.title,
        "document_text": parser.document_text,
        "tables": parser.tables,
        "document_format": "html",
    }


def _cell(text: str, tag: str) -> dict[str, Any]:
    return {
        "tag": tag,
        "attrs": {},
        "text": _clean_text(text),
        "links": [],
        "element_attrs": [{}],
    }


def _delimited_rows(payload: str, delimiter: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(payload), delimiter=delimiter)
    return [[_clean_text(value) for value in row] for row in reader if any(value.strip() for value in row)]


def parse_export_table(payload: str) -> dict[str, Any]:
    """Parse the public ``export=xls`` response when it is TSV/CSV text."""
    candidates: list[list[list[str]]] = []
    for delimiter in ("\t", ",", ";"):
        rows = _delimited_rows(payload, delimiter)
        if rows:
            candidates.append(rows)

    selected: tuple[list[list[str]], int] | None = None
    for rows in candidates:
        for index, row in enumerate(rows):
            normalized = {token(value) for value in row}
            has_rank = bool(normalized.intersection({"rank", "op"}))
            has_player = bool(
                normalized.intersection({"player", "playername", "playerbye", "playerteambye"})
            )
            if has_rank and has_player and normalized.intersection({"avg", "average"}):
                if selected is None or len(row) > len(selected[0][selected[1]]):
                    selected = (rows, index)
                break
    if selected is None:
        raise FantasyProsAdpError("FantasyPros ADP export table not found")

    rows, header_index = selected
    headers = rows[header_index]
    width = len(headers)
    table_rows: list[list[dict[str, Any]]] = [[_cell(value, "th") for value in headers]]
    for row in rows[header_index + 1 :]:
        if len(row) < width:
            row = row + [""] * (width - len(row))
        elif len(row) > width:
            row = row[:width]
        table_rows.append([_cell(value, "td") for value in row])
    return {
        "title": "",
        "document_text": _clean_text(" ".join(" ".join(row) for row in rows[:header_index])),
        "tables": [{"attrs": {"source": "official-export"}, "rows": table_rows}],
        "document_format": "delimited_export",
    }


def parse_ranking_document(payload: str) -> dict[str, Any]:
    parsed = parse_tables(payload)
    try:
        find_ranking_table(parsed)
        return parsed
    except FantasyProsAdpError as exc:
        if str(exc) != "FantasyPros ADP ranking table not found":
            raise
    if re.search(r"<\s*(?:!doctype|html|head|body|table)\b", payload, re.IGNORECASE):
        raise FantasyProsAdpError("FantasyPros ADP ranking table not found")
    return parse_export_table(payload)


def _header_map(table: dict[str, Any]) -> tuple[list[str], int] | None:
    for index, row in enumerate(table.get("rows", [])):
        headers = [cell.get("text", "") for cell in row]
        normalized = {token(value) for value in headers}
        if normalized.intersection({"avg", "average"}) and normalized.intersection(
            {"player", "playername", "playerbye", "playerteambye"}
        ):
            return headers, index
    return None


def find_ranking_table(parsed: dict[str, Any]) -> tuple[dict[str, Any], list[str], int]:
    candidates: list[tuple[dict[str, Any], list[str], int]] = []
    for table in parsed["tables"]:
        result = _header_map(table)
        if result is not None:
            headers, index = result
            candidates.append((table, headers, index))
    if not candidates:
        raise FantasyProsAdpError("FantasyPros ADP ranking table not found")
    candidates.sort(key=lambda item: len(item[0].get("rows", [])), reverse=True)
    return candidates[0]


def find_source_table(parsed: dict[str, Any]) -> dict[str, Any] | None:
    for table in parsed["tables"]:
        for row in table.get("rows", []):
            headers = {token(cell.get("text", "")) for cell in row}
            if {"expert", "site", "date"}.issubset(headers):
                return table
    return None


def table_diagnostics(parsed: dict[str, Any]) -> dict[str, Any]:
    samples: list[list[str]] = []
    for table in parsed.get("tables", [])[:5]:
        for row in table.get("rows", [])[:3]:
            values = [_clean_text(str(cell.get("text", ""))) for cell in row]
            if values:
                samples.append(values[:20])
    return {
        "document_format": parsed.get("document_format", "unknown"),
        "table_count": len(parsed.get("tables", [])),
        "header_samples": samples[:10],
    }
