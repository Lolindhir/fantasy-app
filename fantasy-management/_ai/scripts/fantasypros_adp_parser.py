"""Ranking-table parsing and normalization for FantasyPros ADP."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from decimal import Decimal
from typing import Any

from fantasypros_adp_config import ACTUAL_LEAGUE_TEAM_COUNT, OFFENSIVE_POSITIONS
from fantasypros_adp_fields import (
    _extract_player_identity,
    _parse_position,
    _raw_row,
    _source_columns,
    _source_stats,
    decimal_csv,
    parse_optional_decimal,
    parse_optional_int,
    parse_source_dates,
)
from fantasypros_adp_html import (
    FantasyProsAdpError,
    find_ranking_table,
    find_source_table,
    parse_ranking_document,
    parse_tables,
    table_diagnostics,
    token,
)
from fantasypros_adp_config import validate_source_identity


def _index_for(headers: list[str], aliases: set[str]) -> int | None:
    return next(
        (index for index, value in enumerate(headers) if token(value) in aliases),
        None,
    )


def parse_adp_page(
    payload: str,
    config: dict[str, Any],
    *,
    season: int,
    source_url: str,
    identity_html: str | None = None,
    extraction_method: str = "canonical_public_html_table",
    ranking_fetch_url: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    ranking_parsed = parse_ranking_document(payload)
    identity_parsed = parse_tables(identity_html) if identity_html is not None else ranking_parsed
    table, headers, header_index = find_ranking_table(ranking_parsed)
    validate_source_identity(identity_parsed, config, season, headers)

    header_lookup = {token(value): index for index, value in enumerate(headers)}
    player_index = _index_for(
        headers, {"player", "playername", "playerbye", "playerteambye"}
    )
    position_index = _index_for(headers, {"pos", "position"})
    team_index = _index_for(headers, {"team", "tm"})
    bye_index = _index_for(headers, {"bye", "byeweek"})
    rank_index = header_lookup.get(token(config["rank_header"]))
    avg_index = header_lookup.get("avg", header_lookup.get("average"))
    realtime_index = header_lookup.get("realtime")
    overall_index = (
        header_lookup.get(token(config["overall_header"]))
        if config["overall_header"]
        else None
    )
    if None in {player_index, position_index, rank_index, avg_index}:
        raise FantasyProsAdpError(
            f"Required FantasyPros columns are missing for {config['ranking_id']}: {headers}"
        )
    source_columns = _source_columns(headers, int(position_index), int(avg_index))
    if not source_columns:
        raise FantasyProsAdpError(
            f"FantasyPros source columns are missing for {config['ranking_id']}"
        )

    rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    seen_players: set[str] = set()
    source_coverage: Counter[str] = Counter()
    excluded_positions: Counter[str] = Counter()
    for cells in table.get("rows", [])[header_index + 1 :]:
        if len(cells) < len(headers):
            continue
        raw_rows.append(_raw_row(headers, cells))
        try:
            source_format_rank = parse_optional_int(
                cells[int(rank_index)].get("text"), "format rank", "row"
            )
        except FantasyProsAdpError:
            continue
        if source_format_rank is None:
            continue
        team_value = cells[int(team_index)].get("text", "") if team_index is not None else ""
        bye_value = cells[int(bye_index)].get("text", "") if bye_index is not None else ""
        name, player_id, slug, team, bye = _extract_player_identity(
            cells[int(player_index)],
            team_value=team_value,
            bye_value=bye_value,
        )
        position, position_rank = _parse_position(
            cells[int(position_index)].get("text", ""), name
        )
        if position not in OFFENSIVE_POSITIONS:
            excluded_positions[position] += 1
            continue
        identity = player_id or slug or f"{token(name)}:{position}"
        if identity in seen_players:
            raise FantasyProsAdpError(f"Duplicate FantasyPros player identity: {identity}")
        seen_players.add(identity)

        source_ranks: dict[str, int | str | None] = {}
        numeric_source_ranks: list[Decimal] = []
        source_labels: dict[str, str] = {}
        for index, label, source_id in source_columns:
            parsed_rank = parse_optional_decimal(
                cells[index].get("text"), f"{label} rank", name
            )
            source_ranks[source_id] = (
                int(parsed_rank)
                if parsed_rank is not None and parsed_rank == parsed_rank.to_integral_value()
                else (decimal_csv(parsed_rank) if parsed_rank is not None else None)
            )
            source_labels[source_id] = label
            if parsed_rank is not None:
                numeric_source_ranks.append(parsed_rank)
                source_coverage[source_id] += 1

        adp_average = parse_optional_decimal(
            cells[int(avg_index)].get("text"), "AVG", name
        )
        if adp_average is None or not numeric_source_ranks:
            raise FantasyProsAdpError(
                f"FantasyPros AVG or contributing source ranks missing for {name}"
            )
        calculated = sum(numeric_source_ranks) / Decimal(len(numeric_source_ranks))
        if abs(adp_average - calculated) > Decimal("0.11"):
            raise FantasyProsAdpError(
                f"FantasyPros AVG mismatch for {name}: published={adp_average}, calculated={calculated}"
            )
        minimum, maximum, rank_range, rank_std = _source_stats(numeric_source_ranks)
        realtime = (
            parse_optional_decimal(cells[int(realtime_index)].get("text"), "Real-Time", name)
            if realtime_index is not None
            else None
        )
        source_overall_rank = (
            parse_optional_int(cells[int(overall_index)].get("text"), "Overall", name)
            if overall_index is not None
            else None
        )
        rows.append(
            {
                "name": name,
                "Rank": 0,
                "source_format_rank": source_format_rank,
                "source_overall_rank": source_overall_rank or "",
                "position": position,
                "position_rank": position_rank,
                "team": team,
                "bye": bye,
                "source_player_id": player_id,
                "player_slug": slug,
                "adp_average": decimal_csv(adp_average),
                "realtime_value": decimal_csv(realtime),
                "source_ranks_json": json.dumps(
                    source_ranks, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
                "contributing_source_count": len(numeric_source_ranks),
                "source_rank_min": minimum,
                "source_rank_max": maximum,
                "source_rank_range": rank_range,
                "source_rank_std": rank_std,
                "source_format": config["ranking_id"],
                "actual_league_team_count": ACTUAL_LEAGUE_TEAM_COUNT,
                "_adp": adp_average,
                "_identity": identity,
                "_source_labels": source_labels,
            }
        )

    rows.sort(key=lambda row: (row["_adp"], row["source_format_rank"], row["_identity"]))
    for normalized_rank, row in enumerate(rows, start=1):
        row["Rank"] = normalized_rank
        row.pop("_adp")
        row.pop("_identity")
        row.pop("_source_labels")

    if len(rows) < config["min_rows"]:
        raise FantasyProsAdpError(
            f"Too few offensive FantasyPros rows for {config['ranking_id']}: {len(rows)}"
        )
    if len({row["Rank"] for row in rows}) != len(rows):
        raise FantasyProsAdpError("Normalized FantasyPros ranks are not unique")

    source_dates = parse_source_dates(find_source_table(identity_parsed))
    source_labels = {source_id: label for _, label, source_id in source_columns}
    active_sources = sorted(source_id for source_id, count in source_coverage.items() if count)
    composition_payload = {
        "active_source_ids": active_sources,
        "source_labels": source_labels,
        "source_dates": source_dates,
        "source_coverage": dict(sorted(source_coverage.items())),
    }
    composition_fingerprint = hashlib.sha256(
        json.dumps(composition_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    diagnostics = {
        "source_row_count": len(raw_rows),
        "normalized_player_count": len(rows),
        "excluded_position_counts": dict(sorted(excluded_positions.items())),
        "source_columns": [
            {"column_index": index, "label": label, "source_id": source_id}
            for index, label, source_id in source_columns
        ],
        "source_coverage": dict(sorted(source_coverage.items())),
        "active_source_ids": active_sources,
        "source_dates": source_dates,
        "source_composition_fingerprint": composition_fingerprint,
        "ranking_document": table_diagnostics(ranking_parsed),
        "identity_document": table_diagnostics(identity_parsed),
        "extraction_method": extraction_method,
    }
    raw_payload = {
        "schema_version": 2,
        "official_source_url": source_url,
        "ranking_fetch_url": ranking_fetch_url or source_url,
        "extraction_method": extraction_method,
        "page_title": identity_parsed["title"],
        "ranking_page_title": ranking_parsed["title"],
        "ranking_document_format": ranking_parsed.get("document_format", "unknown"),
        "ranking_headers": headers,
        "ranking_rows": raw_rows,
        "source_dates": source_dates,
        "source_columns": diagnostics["source_columns"],
        "document_identity_excerpt": identity_parsed["document_text"][:2000],
        "ranking_document_diagnostics": diagnostics["ranking_document"],
        "identity_document_diagnostics": diagnostics["identity_document"],
    }
    return rows, diagnostics, raw_payload
