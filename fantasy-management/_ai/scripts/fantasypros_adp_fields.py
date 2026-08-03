"""Field parsing helpers for normalized FantasyPros ADP rows."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from fantasypros_adp_html import FantasyProsAdpError, _clean_text, token

NULL_TOKENS = {"", "-", "—", "–", "n/a", "na", "null"}
NON_SOURCE_HEADERS = {
    "rank", "op", "overall", "player", "playername", "playerbye", "playerteambye",
    "team", "bye", "pos", "position", "avg", "average", "realtime",
}
SOURCE_ID_ALIASES = {
    "espn": "espn", "sleeper": "sleeper", "cbs": "cbs-sports",
    "cbssports": "cbs-sports", "nfl": "nfl", "nflcom": "nfl",
    "rtsports": "rtsports", "fantrax": "fantrax", "yahoo": "yahoo",
    "yahoosports": "yahoo", "ffpc": "ffpc",
    "fantasyfootballcalculator": "fantasy-football-calculator",
}


def canonical_source_id(value: str) -> str:
    normalized = token(value)
    return SOURCE_ID_ALIASES.get(normalized, normalized or "unknown")


def parse_optional_decimal(value: Any, field: str, name: str) -> Decimal | None:
    text = str(value or "").strip()
    if text.casefold() in NULL_TOKENS:
        return None
    try:
        parsed = Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise FantasyProsAdpError(
            f"Invalid FantasyPros {field} for {name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise FantasyProsAdpError(
            f"Invalid FantasyPros {field} for {name}: {value!r}"
        )
    return parsed


def parse_optional_int(value: Any, field: str, name: str) -> int | None:
    parsed = parse_optional_decimal(value, field, name)
    if parsed is None:
        return None
    if parsed != parsed.to_integral_value() or parsed <= 0:
        raise FantasyProsAdpError(
            f"FantasyPros {field} for {name} must be a positive integer: {value!r}"
        )
    return int(parsed)


def decimal_csv(value: Decimal | None) -> int | str:
    if value is None:
        return ""
    if value == value.to_integral_value():
        return int(value)
    return format(value.normalize(), "f")


def _source_stats(values: list[Decimal]) -> tuple[int | str, int | str, int | str, int | str]:
    if not values:
        return "", "", "", ""
    minimum, maximum = min(values), max(values)
    spread = maximum - minimum
    mean = sum(values) / Decimal(len(values))
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
    stdev = variance.sqrt()
    return (
        decimal_csv(minimum),
        decimal_csv(maximum),
        decimal_csv(spread),
        decimal_csv(stdev.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
    )


def _parse_team_bye(text: str) -> tuple[str, int | str]:
    normalized = _clean_text(text)
    match = re.search(r"\b([A-Z]{2,3})\s*\((\d{1,2})\)\s*$", normalized)
    if match:
        return match.group(1), int(match.group(2))
    team_only = re.search(r"\b([A-Z]{2,3})\s*$", normalized)
    return (team_only.group(1), "") if team_only else ("", "")


def _extract_player_identity(
    cell: dict[str, Any],
    *,
    team_value: str = "",
    bye_value: str = "",
) -> tuple[str, str, str, str, int | str]:
    player_links = [
        link
        for link in cell.get("links", [])
        if "/nfl/players/" in str(link.get("href", ""))
    ]
    name = ""
    slug = ""
    if player_links:
        primary = player_links[0]
        name = _clean_text(str(primary.get("text") or ""))
        href = str(primary.get("href") or "")
        match = re.search(r"/nfl/players/([^/?#]+)\.php", href)
        slug = match.group(1) if match else ""
    else:
        raw_text = _clean_text(str(cell.get("text") or ""))
        name = raw_text
        trailing = re.search(r"\s+([A-Z]{2,3})(?:\s*\((\d{1,2})\))?\s*$", raw_text)
        if trailing:
            name = raw_text[: trailing.start()].strip()
            if not team_value:
                team_value = trailing.group(1)
            if not bye_value and trailing.group(2):
                bye_value = trailing.group(2)
    if not name:
        raise FantasyProsAdpError(f"Player name missing in ADP row: {cell.get('text')!r}")

    player_id = ""
    for attrs in cell.get("element_attrs", []):
        for key in ("data-fp-id", "data-player-id", "data-player", "data-id"):
            candidate = str(attrs.get(key) or "").strip()
            if candidate.isdigit():
                player_id = candidate
                break
        if player_id:
            break
        class_value = str(attrs.get("class") or "")
        id_match = re.search(r"(?:^|\s)fp-id-(\d+)(?:\s|$)", class_value)
        if id_match:
            player_id = id_match.group(1)
            break

    team, bye = _parse_team_bye(str(cell.get("text") or ""))
    explicit_team = _clean_text(team_value).upper()
    if explicit_team and re.fullmatch(r"[A-Z]{2,3}", explicit_team):
        team = explicit_team
    explicit_bye = _clean_text(bye_value)
    if explicit_bye:
        try:
            parsed_bye = int(explicit_bye)
        except ValueError as exc:
            raise FantasyProsAdpError(
                f"Invalid FantasyPros bye for {name}: {bye_value!r}"
            ) from exc
        if not 1 <= parsed_bye <= 18:
            raise FantasyProsAdpError(
                f"Invalid FantasyPros bye for {name}: {bye_value!r}"
            )
        bye = parsed_bye
    return name, player_id, slug, team, bye


def _parse_position(value: str, name: str) -> tuple[str, str]:
    match = re.fullmatch(r"\s*(QB|RB|WR|TE|K|DST|DEF)(\d+)?\s*", value.upper())
    if not match:
        raise FantasyProsAdpError(
            f"Unexpected FantasyPros position for {name}: {value!r}"
        )
    position = "DST" if match.group(1) == "DEF" else match.group(1)
    position_rank = f"{position}{match.group(2)}" if match.group(2) else ""
    return position, position_rank


def _source_columns(headers: list[str], position_index: int, avg_index: int) -> list[tuple[int, str, str]]:
    result: list[tuple[int, str, str]] = []
    for index in range(position_index + 1, avg_index):
        label = headers[index]
        if token(label) in NON_SOURCE_HEADERS:
            continue
        result.append((index, label, canonical_source_id(label)))
    return result


def _raw_row(headers: list[str], cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": [
            {
                "text": cell.get("text", ""),
                "tag": cell.get("tag", ""),
                "attrs": cell.get("attrs", {}),
                "links": cell.get("links", []),
                "element_attrs": cell.get("element_attrs", []),
            }
            for cell in cells
        ],
        "headers": headers,
    }


def parse_source_dates(table: dict[str, Any] | None) -> list[dict[str, str]]:
    if table is None:
        return []
    rows = table.get("rows", [])
    header_index = None
    headers: list[str] = []
    for index, row in enumerate(rows):
        current = [cell.get("text", "") for cell in row]
        normalized = {token(value) for value in current}
        if {"expert", "site", "date"}.issubset(normalized):
            header_index, headers = index, current
            break
    if header_index is None:
        return []
    lookup = {token(value): index for index, value in enumerate(headers)}
    result: list[dict[str, str]] = []
    for row in rows[header_index + 1 :]:
        values = [cell.get("text", "") for cell in row]
        if len(values) < len(headers):
            continue
        site = values[lookup["site"]]
        date = values[lookup["date"]]
        expert = values[lookup["expert"]]
        if not site or not date:
            continue
        result.append(
            {
                "source_id": canonical_source_id(site),
                "site": site,
                "expert": expert,
                "published_date_label": date,
            }
        )
    return result
