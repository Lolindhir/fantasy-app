#!/usr/bin/env python3
"""Build provider-neutral Fantasy Operations inputs from repository data.

The script performs deterministic data preparation only. It does not browse the
web, call an AI service, make fantasy recommendations, or persist monitoring
state. External source behavior is declared in the Operations Source Catalog;
adding another source with an existing normalized contract must not require a
materializer code change.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from canonical_league_ownership import (
    CanonicalOwnershipError,
    build_canonical_ownership_snapshot,
    resolve_current_canonical_season,
)


SCHEMA_VERSION = 1
CATALOG_SCHEMA_VERSION = 1
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
SEVERITIES = {"none", "info", "warning", "error"}
SIGNAL_TYPES = {"text", "number", "boolean"}
JOIN_TYPES = {"id", "name_position"}
FANTASY_RELEVANT_POSITIONS = {"QB", "RB", "WR", "TE", "K"}


class MaterializationError(RuntimeError):
    """Raised when a required input cannot be materialized safely."""


@dataclass(frozen=True)
class SourceFile:
    id: str
    path: Path
    relative_path: str
    content_sha256: str
    source_timestamp: str | None


@dataclass(frozen=True)
class LoadedCatalogSource:
    definition: dict[str, Any]
    pointer_source: SourceFile
    ranking_source: SourceFile
    observation_source: SourceFile | None
    current_observation: dict[str, Any] | None
    rows: list[dict[str, str]]
    index: dict[str, Any]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MaterializationError(f"Missing required JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MaterializationError(f"Invalid JSON input {path}: {exc}") from exc


def load_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise MaterializationError(f"Missing required CSV input: {path}") from exc


def relative_to_root(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    while tokens and tokens[-1] in NAME_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def canonical_fantasy_position(player: dict[str, Any] | None) -> str | None:
    if not player:
        return None
    raw_position = optional_text(player.get("Position"))
    fantasy_positions = player.get("FantasyPositions")
    if fantasy_positions is None:
        return raw_position
    if not isinstance(fantasy_positions, list):
        raise MaterializationError(
            "Canonical Sleeper player FantasyPositions must be an array"
        )

    normalized = [
        value
        for value in (
            optional_text(position).upper() if optional_text(position) else None
            for position in fantasy_positions
        )
        if value
    ]
    for position in normalized:
        if position in FANTASY_RELEVANT_POSITIONS:
            return position
    return raw_position or (normalized[0] if normalized else None)


def build_canonical_identity_by_sleeper(
    document: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(document, dict) or not isinstance(document.get("Players"), list):
        raise MaterializationError(
            "Canonical player identity input must contain a Players array"
        )
    result: dict[str, dict[str, Any]] = {}
    for row in document["Players"]:
        if not isinstance(row, dict):
            raise MaterializationError(
                "Canonical player identity input contains a non-object row"
            )
        canonical_player_id = optional_text(row.get("CanonicalPlayerID"))
        if not canonical_player_id:
            raise MaterializationError(
                "Canonical player identity row has no CanonicalPlayerID"
            )
        ids = row.get("IDs") or {}
        if not isinstance(ids, dict):
            raise MaterializationError(
                f"Canonical player identity {canonical_player_id} has invalid IDs"
            )
        sleeper_id = optional_text(ids.get("Sleeper"))
        if not sleeper_id:
            continue
        if sleeper_id in result:
            raise MaterializationError(
                f"Canonical player identities contain duplicate active Sleeper ID {sleeper_id}"
            )
        result[sleeper_id] = row
    return result


def build_canonical_sleeper_player_lookup(
    document: Any,
    identity_by_sleeper: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(document, dict) or not isinstance(document.get("Records"), list):
        raise MaterializationError(
            "Canonical Sleeper player input must contain a Records array"
        )
    result: dict[str, dict[str, Any]] = {}
    for row in document["Records"]:
        if not isinstance(row, dict):
            raise MaterializationError(
                "Canonical Sleeper player input contains a non-object row"
            )
        sleeper_id = optional_text(row.get("SleeperPlayerID"))
        if not sleeper_id:
            raise MaterializationError(
                "Canonical Sleeper player row has no SleeperPlayerID"
            )
        if sleeper_id in result:
            raise MaterializationError(
                f"Canonical Sleeper players contain duplicate SleeperPlayerID {sleeper_id}"
            )
        canonical_player_id = optional_text(row.get("CanonicalPlayerID"))
        if canonical_player_id:
            identity = identity_by_sleeper.get(sleeper_id)
            identity_canonical_id = optional_text(
                (identity or {}).get("CanonicalPlayerID")
            )
            if canonical_player_id != identity_canonical_id:
                raise MaterializationError(
                    "Canonical Sleeper player identity mismatch for "
                    f"{sleeper_id}: platform={canonical_player_id}, "
                    f"identity={identity_canonical_id}"
                )
        result[sleeper_id] = row
    return result


def canonicalize_player_identity(
    player_id: str,
    legacy_player: dict[str, Any],
    identity_by_sleeper: dict[str, dict[str, Any]],
    sleeper_player_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    identity = identity_by_sleeper.get(player_id)
    if identity is None:
        raise MaterializationError(
            f"Managed roster player {player_id} has no Canonical Identity Sleeper mapping"
        )
    sleeper_player = sleeper_player_lookup.get(player_id)
    if sleeper_player is None:
        raise MaterializationError(
            f"Managed roster player {player_id} has no Canonical Sleeper player record"
        )

    player = dict(legacy_player)
    player["ID"] = player_id
    player["Name"] = optional_text(identity.get("Name"))
    player["Position"] = canonical_fantasy_position(sleeper_player)
    player["TeamAbbr"] = optional_text(sleeper_player.get("Team"))
    return player


def optional_number(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 4)


def optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_datetime(value: Any) -> datetime | None:
    text = optional_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def max_timestamp(values: Iterable[Any]) -> str | None:
    parsed = [item for item in (parse_datetime(value) for value in values) if item]
    if not parsed:
        return None
    return max(parsed).isoformat().replace("+00:00", "Z")


def source_file(source_id: str, path: Path, root: Path, timestamp: Any = None) -> SourceFile:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise MaterializationError(f"Missing required source file: {path}") from exc
    return SourceFile(
        id=source_id,
        path=path,
        relative_path=relative_to_root(path, root),
        content_sha256=sha256_text(content),
        source_timestamp=max_timestamp([timestamp]),
    )


def percentile(rank: Any, row_count: int) -> float | None:
    parsed = optional_number(rank)
    if parsed is None or row_count <= 0:
        return None
    if row_count == 1:
        return 100.0
    value = ((row_count - float(parsed)) / (row_count - 1)) * 100
    return round(max(0.0, min(100.0, value)), 2)


def convert_signal(value: Any, signal_type: str) -> Any:
    if signal_type == "number":
        return optional_number(value)
    if signal_type == "boolean":
        return optional_bool(value)
    if signal_type == "text":
        return optional_text(value)
    raise MaterializationError(f"Unsupported signal type: {signal_type}")


def validate_catalog(catalog: dict[str, Any]) -> None:
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise MaterializationError("Unexpected Operations Source Catalog schema version")
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        raise MaterializationError("Operations Source Catalog must contain sources")

    seen_ids: set[str] = set()
    primary_positions: dict[str, str] = {}
    for source in sources:
        source_id = optional_text(source.get("source_id"))
        if not source_id:
            raise MaterializationError("Catalog source has no source_id")
        if source_id in seen_ids:
            raise MaterializationError(f"Duplicate catalog source_id: {source_id}")
        seen_ids.add(source_id)

        if not isinstance(source.get("active"), bool):
            raise MaterializationError(f"Catalog source {source_id} has invalid active flag")
        if not source.get("active"):
            continue

        access = source.get("access") or {}
        if access.get("type") != "repo_latest_pointer":
            raise MaterializationError(f"Catalog source {source_id} uses unsupported access type")
        if not optional_text(access.get("location")):
            raise MaterializationError(f"Catalog source {source_id} has no location")
        if not optional_text(access.get("ranking_path_field")):
            raise MaterializationError(f"Catalog source {source_id} has no ranking_path_field")
        timestamp_fields = access.get("timestamp_fields")
        if not isinstance(timestamp_fields, list) or not timestamp_fields:
            raise MaterializationError(f"Catalog source {source_id} has no timestamp_fields")

        applicability = source.get("applicability") or {}
        positions = applicability.get("positions")
        if not isinstance(positions, list) or not positions:
            raise MaterializationError(f"Catalog source {source_id} must declare applicable positions")

        join = source.get("join") or {}
        strategies = join.get("strategies")
        if not isinstance(strategies, list) or not strategies:
            raise MaterializationError(f"Catalog source {source_id} must declare join strategies")
        for strategy in strategies:
            if strategy.get("type") not in JOIN_TYPES:
                raise MaterializationError(f"Catalog source {source_id} has unsupported join strategy")
            if not optional_text(strategy.get("method")):
                raise MaterializationError(f"Catalog source {source_id} join strategy has no method")
            if strategy.get("type") == "id":
                if not optional_text(strategy.get("player_field")) or not optional_text(strategy.get("source_field")):
                    raise MaterializationError(f"Catalog source {source_id} id join is incomplete")
            else:
                for field in ("name_field", "position_field"):
                    if not optional_text(strategy.get(field)):
                        raise MaterializationError(f"Catalog source {source_id} name join is incomplete")

        output = source.get("output") or {}
        if not optional_text(output.get("section")) or not optional_text(output.get("key")):
            raise MaterializationError(f"Catalog source {source_id} must declare output section and key")
        signals = output.get("signals")
        if not isinstance(signals, list) or not signals:
            raise MaterializationError(f"Catalog source {source_id} must declare signal mappings")
        targets: set[str] = set()
        for signal in signals:
            target = optional_text(signal.get("target"))
            if not target or target in targets:
                raise MaterializationError(f"Catalog source {source_id} has invalid signal target")
            targets.add(target)
            if signal.get("type") not in SIGNAL_TYPES:
                raise MaterializationError(f"Catalog source {source_id} has invalid signal type")
            if not optional_text(signal.get("source_field")):
                raise MaterializationError(f"Catalog source {source_id} signal {target} has no source_field")
            transform = signal.get("transform")
            if transform not in (None, "percentile_from_rank"):
                raise MaterializationError(f"Catalog source {source_id} signal {target} has invalid transform")

        quality = source.get("quality") or {}
        for key in ("missing_severity", "ambiguous_severity", "row_count_severity"):
            if quality.get(key, "none") not in SEVERITIES:
                raise MaterializationError(f"Catalog source {source_id} has invalid {key}")

        roles = source.get("roles") or {}
        if output.get("section") == "redraft_adp":
            for position in roles.get("primary_for_positions") or []:
                normalized_position = str(position).upper()
                if normalized_position in primary_positions:
                    raise MaterializationError(
                        "Multiple primary redraft ADP sources for position "
                        f"{normalized_position}: {primary_positions[normalized_position]} and {source_id}"
                    )
                primary_positions[normalized_position] = source_id

    derived_views = catalog.get("derived_views") or {}
    gap = ((derived_views.get("redraft_adp") or {}).get("format_gap") or {})
    if gap:
        for key in ("left_source_id", "right_source_id", "signal"):
            if not optional_text(gap.get(key)):
                raise MaterializationError(f"redraft_adp.format_gap has no {key}")
        for source_key in ("left_source_id", "right_source_id"):
            if gap[source_key] not in seen_ids:
                raise MaterializationError(f"redraft_adp.format_gap references unknown source {gap[source_key]}")


def build_source_index(rows: list[dict[str, str]], strategies: list[dict[str, Any]]) -> dict[str, Any]:
    indexes: list[dict[str, Any]] = []
    for strategy in strategies:
        if strategy["type"] == "id":
            by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
            source_field = strategy["source_field"]
            for row in rows:
                source_id = optional_text(row.get(source_field))
                if source_id:
                    by_id[source_id].append(row)
            indexes.append({"strategy": strategy, "values": by_id})
            continue

        by_name_position: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            key = (
                normalize_name(row.get(strategy["name_field"])),
                str(row.get(strategy["position_field"]) or "").upper(),
            )
            if key[0] and key[1]:
                by_name_position[key].append(row)
        indexes.append({"strategy": strategy, "values": by_name_position})
    return {"indexes": indexes, "row_count": len(rows)}


def match_source_row(player: dict[str, Any], source: LoadedCatalogSource) -> tuple[dict[str, str] | None, str, list[str]]:
    ambiguous_candidates: list[str] = []
    for item in source.index["indexes"]:
        strategy = item["strategy"]
        values = item["values"]
        if strategy["type"] == "id":
            player_value = optional_text(player.get(strategy["player_field"]))
            if not player_value:
                continue
            candidates = values.get(player_value, [])
        else:
            key = (
                normalize_name(player.get("Name")),
                str(player.get("Position") or "").upper(),
            )
            candidates = values.get(key, [])

        if len(candidates) == 1:
            return candidates[0], strategy["method"], []
        if len(candidates) <= 1:
            continue

        if strategy["type"] == "name_position" and optional_text(strategy.get("team_field")):
            team = str(player.get("TeamAbbr") or "").upper()
            team_candidates = [
                row
                for row in candidates
                if str(row.get(strategy["team_field"]) or "").upper() == team
            ]
            if len(team_candidates) == 1:
                return team_candidates[0], f"{strategy['method']}_team", []

        ambiguous_candidates = [
            str(row.get(strategy.get("name_field") or "name") or "")
            for row in candidates
        ]

    if ambiguous_candidates:
        return None, "ambiguous", ambiguous_candidates
    return None, "missing", []


def load_current_observation(
    root: Path,
    definition: dict[str, Any],
) -> tuple[dict[str, Any] | None, SourceFile | None]:
    access = definition["access"]
    relative_path = optional_text(access.get("observation_status_path"))
    if not relative_path:
        return None, None

    path = root / relative_path
    if not path.exists():
        return {
            "status": "missing",
            "usable": False,
            "checked_at": None,
            "published": False,
        }, None

    payload = load_json(path)
    if not isinstance(payload, dict):
        raise MaterializationError(
            f"Current source observation for {definition['source_id']} must be an object"
        )
    if payload.get("source_id") != definition["provider"]:
        raise MaterializationError(
            f"Current source observation source_id mismatch for {definition['source_id']}"
        )
    if payload.get("dataset_id") != definition["dataset_id"]:
        raise MaterializationError(
            f"Current source observation dataset_id mismatch for {definition['source_id']}"
        )
    if not isinstance(payload.get("usable"), bool):
        raise MaterializationError(
            f"Current source observation usable flag is invalid for {definition['source_id']}"
        )
    status = optional_text(payload.get("status"))
    if status not in {
        "usable",
        "reduced_coverage",
        "insufficient_coverage",
        "inactive_for_phase",
    }:
        raise MaterializationError(
            f"Current source observation status is invalid for {definition['source_id']}: {status!r}"
        )
    checked_at = optional_text(payload.get("checked_at"))
    if checked_at is None or parse_datetime(checked_at) is None:
        raise MaterializationError(
            f"Current source observation checked_at is invalid for {definition['source_id']}"
        )
    return payload, source_file(
        f"{definition['source_id']}_observation",
        path,
        root,
        checked_at,
    )


def current_observation_summary(source: LoadedCatalogSource) -> dict[str, Any] | None:
    observation = source.current_observation
    if observation is None:
        return None
    summary = {
        "status": observation.get("status"),
        "usable": bool(observation.get("usable")),
        "checked_at": observation.get("checked_at"),
        "published": bool(observation.get("published")),
    }
    if isinstance(observation.get("coverage"), dict):
        summary["coverage"] = observation["coverage"]
    if isinstance(observation.get("season_context"), dict):
        summary["season_context"] = observation["season_context"]
    return summary


def resolve_catalog_source(root: Path, definition: dict[str, Any]) -> LoadedCatalogSource:
    source_id = definition["source_id"]
    access = definition["access"]
    pointer_file = root / access["location"]
    pointer = load_json(pointer_file)
    ranking_path = optional_text(pointer.get(access["ranking_path_field"]))
    if not ranking_path:
        raise MaterializationError(f"Pointer for {source_id} has no {access['ranking_path_field']}")
    ranking_file = root / ranking_path
    timestamp = max_timestamp(pointer.get(field) for field in access["timestamp_fields"])
    rows = load_csv(ranking_file)
    observation, observation_source = load_current_observation(root, definition)
    return LoadedCatalogSource(
        definition=definition,
        pointer_source=source_file(f"{source_id}_pointer", pointer_file, root, timestamp),
        ranking_source=source_file(f"{source_id}_ranking", ranking_file, root, timestamp),
        observation_source=observation_source,
        current_observation=observation,
        rows=rows,
        index=build_source_index(rows, definition["join"]["strategies"]),
    )


def derive_injury_signal(player: dict[str, Any]) -> dict[str, Any]:
    details = player.get("InjuryDetails") if isinstance(player.get("InjuryDetails"), dict) else {}
    injured = bool(player.get("Injured"))
    designation = optional_text(details.get("Designation"))
    description = optional_text(details.get("Description"))
    return_date = optional_text(details.get("ReturnDate"))
    report_date = optional_text(details.get("Date"))
    has_signal = injured or any((designation, description, return_date, report_date))

    if injured and designation:
        coverage_status = "current_injury_signal"
    elif has_signal:
        coverage_status = "partial_injury_signal"
    else:
        coverage_status = "no_current_injury_signal"

    return {
        "coverage_status": coverage_status,
        "is_injured": injured,
        "designation": designation,
        "description": description,
        "reported_date": report_date,
        "return_date": return_date,
        "external_verification_priority": "high" if has_signal else "routine",
        "limitations": [
            "A missing structured signal is not proof of full health.",
            "Descriptions and designations are secondary-source inputs and require external verification when decision-relevant.",
        ],
    }


def severity_issue(
    severity: str,
    *,
    kind: str,
    source_id: str,
    player_id: str | None = None,
    candidates: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if severity == "none":
        return None
    issue: dict[str, Any] = {"severity": severity, "kind": kind, "source": source_id}
    if player_id is not None:
        issue["player_id"] = player_id
    if candidates:
        issue["candidates"] = candidates
    if details:
        issue.update(details)
    return issue


def source_applicable(player: dict[str, Any], definition: dict[str, Any]) -> bool:
    position = str(player.get("Position") or "").upper()
    positions = {str(item).upper() for item in definition["applicability"]["positions"]}
    return position in positions


def evaluate_source_for_player(player: dict[str, Any], source: LoadedCatalogSource) -> tuple[dict[str, Any], dict[str, Any] | None]:
    definition = source.definition
    source_id = definition["source_id"]
    signal_values = {mapping["target"]: None for mapping in definition["output"]["signals"]}

    if not source_applicable(player, definition):
        return (
            {
                "source_id": source_id,
                "source_kind": definition["source_kind"],
                "provider": definition["provider"],
                "dataset_id": definition["dataset_id"],
                "applicable": False,
                "coverage_status": definition["absence_policy"]["inapplicable"],
                "listed": False,
                "join_method": "not_applicable",
                "signals": signal_values,
                "format_context": definition.get("format_context") or {},
            },
            None,
        )

    row, join_method, candidates = match_source_row(player, source)
    if row is None:
        if join_method == "ambiguous":
            severity = definition["quality"].get("ambiguous_severity", "warning")
            coverage_status = definition["absence_policy"]["ambiguous"]
            kind = "ambiguous_join"
        else:
            severity = definition["quality"].get("missing_severity", "none")
            coverage_status = definition["absence_policy"]["missing"]
            kind = "not_listed"
        return (
            {
                "source_id": source_id,
                "source_kind": definition["source_kind"],
                "provider": definition["provider"],
                "dataset_id": definition["dataset_id"],
                "applicable": True,
                "coverage_status": coverage_status,
                "listed": False,
                "join_method": join_method,
                "signals": signal_values,
                "format_context": definition.get("format_context") or {},
            },
            severity_issue(
                severity,
                kind=kind,
                source_id=source_id,
                player_id=str(player.get("ID") or ""),
                candidates=candidates,
            ),
        )

    for mapping in definition["output"]["signals"]:
        raw_value = row.get(mapping["source_field"])
        if mapping.get("transform") == "percentile_from_rank":
            signal_values[mapping["target"]] = percentile(raw_value, source.index["row_count"])
        else:
            signal_values[mapping["target"]] = convert_signal(raw_value, mapping["type"])

    return (
        {
            "source_id": source_id,
            "source_kind": definition["source_kind"],
            "provider": definition["provider"],
            "dataset_id": definition["dataset_id"],
            "applicable": True,
            "coverage_status": "listed",
            "listed": True,
            "join_method": join_method,
            "signals": signal_values,
            "format_context": definition.get("format_context") or {},
        },
        None,
    )


def flatten_source_result(result: dict[str, Any]) -> dict[str, Any]:
    flattened = {
        "source_id": result["source_id"],
        "coverage_status": result["coverage_status"],
        "applicable": result["applicable"],
        "listed": result["listed"],
        "join_method": result["join_method"],
        **result["signals"],
    }
    if result.get("current_observation") is not None:
        flattened["current_observation"] = result["current_observation"]
    return flattened


def derive_adp_view(
    player: dict[str, Any],
    catalog: dict[str, Any],
    loaded_sources: list[LoadedCatalogSource],
    source_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    position = str(player.get("Position") or "").upper()
    formats: dict[str, dict[str, Any]] = {}
    primary_source: LoadedCatalogSource | None = None

    for source in loaded_sources:
        definition = source.definition
        if definition["output"]["section"] != "redraft_adp":
            continue
        source_id = definition["source_id"]
        output_key = definition["output"]["key"]
        formats[output_key] = flatten_source_result(source_results[source_id])
        primary_positions = {str(item).upper() for item in (definition.get("roles") or {}).get("primary_for_positions", [])}
        if position in primary_positions:
            primary_source = source

    primary_key: str | None = None
    primary_source_id: str | None = None
    primary: dict[str, Any] | None = None
    if primary_source is not None:
        primary_source_id = primary_source.definition["source_id"]
        primary_key = primary_source.definition["output"]["key"]
        primary = formats[primary_key]

    gap_value: float | None = None
    gap_definition = (((catalog.get("derived_views") or {}).get("redraft_adp") or {}).get("format_gap") or {})
    if gap_definition:
        left = source_results.get(gap_definition["left_source_id"])
        right = source_results.get(gap_definition["right_source_id"])
        signal = gap_definition["signal"]
        left_value = (left or {}).get("signals", {}).get(signal)
        right_value = (right or {}).get("signals", {}).get(signal)
        if left_value is not None and right_value is not None:
            gap_value = round(float(left_value) - float(right_value), 2)

    result: dict[str, Any] = {
        "primary_format": primary_key,
        "primary_source_id": primary_source_id,
        "primary_applicability": "applicable" if primary_source is not None else "not_applicable",
        "primary_listed": bool(primary and primary["listed"]),
        "primary": primary,
        "formats": formats,
        "format_gap": gap_value,
    }
    result.update(formats)
    return result


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "managed_team",
        "sources",
        "players",
        "quality",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise MaterializationError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise MaterializationError("Unexpected output schema version")
    player_ids = [player["player_id"] for player in data["players"]]
    if len(player_ids) != len(set(player_ids)):
        raise MaterializationError("Output contains duplicate player IDs")


def quality_status(issues: list[dict[str, Any]]) -> str:
    if any(issue["severity"] == "error" for issue in issues):
        return "error"
    if any(issue["severity"] == "warning" for issue in issues):
        return "warning"
    return "ok"


def build(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(config_path)
    if config.get("schema_version") != 2:
        raise MaterializationError("Unexpected input materialization config schema version")
    core_sources = config["sources"]
    league_display_path = root / core_sources["league_display"]
    players_path = root / core_sources["players"]
    canonical_identities_path = root / core_sources["canonical_player_identities"]
    canonical_sleeper_players_path = root / core_sources["canonical_sleeper_players"]
    timestamps_path = root / core_sources["timestamps"]
    catalog_path = root / config["source_catalog"]

    league_display = load_json(league_display_path)
    players = load_json(players_path)
    canonical_identities = load_json(canonical_identities_path)
    canonical_sleeper_players = load_json(canonical_sleeper_players_path)
    timestamps = load_json(timestamps_path)
    catalog = load_json(catalog_path)
    validate_catalog(catalog)
    if not isinstance(players, list):
        raise MaterializationError("Players input must be a JSON array")
    identity_by_sleeper = build_canonical_identity_by_sleeper(canonical_identities)
    sleeper_player_lookup = build_canonical_sleeper_player_lookup(
        canonical_sleeper_players,
        identity_by_sleeper,
    )

    managed_config = config["managed_team"]
    if managed_config.get("identity_field") != "TeamID":
        raise MaterializationError(
            "Canonical managed-roster cutover requires managed_team.identity_field = TeamID"
        )
    team_id = str(managed_config["team_id"])

    canonical_config = config.get("canonical_league") or {}
    canonical_league_id = optional_text(canonical_config.get("canonical_league_id"))
    if not canonical_league_id:
        raise MaterializationError(
            "canonical_league.canonical_league_id is required for managed-roster ownership"
        )
    try:
        canonical_season = resolve_current_canonical_season(
            root,
            canonical_league_id=canonical_league_id,
        )
        canonical_ownership = build_canonical_ownership_snapshot(
            root,
            canonical_league_id=canonical_league_id,
            season=canonical_season,
        )
    except CanonicalOwnershipError as exc:
        raise MaterializationError(
            f"Canonical managed-roster ownership is unavailable: {exc}"
        ) from exc

    canonical_teams = canonical_ownership.get("Teams") or []
    managed_team = next(
        (team for team in canonical_teams if str(team.get("TeamID")) == team_id),
        None,
    )
    if managed_team is None:
        raise MaterializationError(
            f"Managed team {team_id} not found in canonical ownership snapshot"
        )

    display_teams = (
        league_display.get("Teams")
        if isinstance(league_display, dict) and isinstance(league_display.get("Teams"), list)
        else []
    )
    managed_display_team = next(
        (
            team
            for team in display_teams
            if str(team.get(managed_config["identity_field"])) == team_id
        ),
        None,
    )
    if managed_display_team is None:
        raise MaterializationError(
            f"Managed team {team_id} not found in League.json display enrichment"
        )

    loaded_sources = [
        resolve_catalog_source(root, definition)
        for definition in catalog["sources"]
        if definition.get("active")
    ]

    player_timestamp = timestamps.get("Players") if isinstance(timestamps, dict) else None
    league_timestamp = timestamps.get("League") if isinstance(timestamps, dict) else None
    canonical_league_root = (
        root
        / "source-data"
        / "leagues"
        / canonical_league_id
    )
    canonical_season_root = canonical_league_root / "seasons" / str(canonical_season)
    source_files = [
        source_file("league_display", league_display_path, root, league_timestamp),
        source_file(
            "canonical_league_manifest",
            canonical_league_root / "manifest.json",
            root,
        ),
        source_file(
            "canonical_league",
            canonical_season_root / "league.json",
            root,
        ),
        source_file(
            "canonical_league_members",
            canonical_season_root / "members.json",
            root,
        ),
        source_file(
            "canonical_league_rosters",
            canonical_season_root / "rosters.json",
            root,
        ),
        source_file("players", players_path, root, player_timestamp),
        source_file(
            "canonical_player_identities",
            canonical_identities_path,
            root,
        ),
        source_file(
            "canonical_sleeper_players",
            canonical_sleeper_players_path,
            root,
        ),
        source_file(
            "timestamps",
            timestamps_path,
            root,
            max_timestamp(timestamps.values()) if isinstance(timestamps, dict) else None,
        ),
        source_file("operations_source_catalog", catalog_path, root),
    ]
    for source in loaded_sources:
        source_files.extend([source.pointer_source, source.ranking_source])
        if source.observation_source is not None:
            source_files.append(source.observation_source)

    player_lookup = {
        str(player.get("ID")): player
        for player in players
        if player.get("ID") is not None
    }
    sections_by_player: dict[str, list[str]] = defaultdict(list)
    for section in ("Roster", "Reserve", "Taxi"):
        for player_id in managed_team.get(section) or []:
            section_name = section.casefold()
            if section_name not in sections_by_player[str(player_id)]:
                sections_by_player[str(player_id)].append(section_name)
    starters = {str(player_id) for player_id in managed_team.get("Starter") or []}

    quality_issues: list[dict[str, Any]] = []
    source_coverage: dict[str, dict[str, int]] = {
        source.definition["source_id"]: {
            "applicable_players": 0,
            "listed_players": 0,
            "not_listed_players": 0,
            "not_applicable_players": 0,
            "ambiguous_players": 0,
        }
        for source in loaded_sources
    }
    source_observations: dict[str, dict[str, Any]] = {}
    for source in loaded_sources:
        source_id = source.definition["source_id"]
        minimum_rows = int(source.definition["quality"].get("minimum_rows", 0))
        if source.index["row_count"] < minimum_rows:
            issue = severity_issue(
                source.definition["quality"].get("row_count_severity", "error"),
                kind="unexpected_row_count",
                source_id=source_id,
                details={"actual_rows": source.index["row_count"], "minimum_rows": minimum_rows},
            )
            if issue:
                quality_issues.append(issue)

        observation = current_observation_summary(source)
        if observation is not None:
            source_observations[source_id] = observation
            observation_status = observation.get("status")
            if observation_status == "missing":
                quality_issues.append({
                    "severity": "warning",
                    "kind": "current_source_observation_missing",
                    "source": source_id,
                })
            elif observation_status == "reduced_coverage":
                quality_issues.append({
                    "severity": "warning",
                    "kind": "current_source_observation_reduced_coverage",
                    "source": source_id,
                    "observation_status": observation_status,
                    "checked_at": observation.get("checked_at"),
                    "coverage": observation.get("coverage"),
                })
            elif not observation.get("usable"):
                quality_issues.append({
                    "severity": "warning",
                    "kind": "current_source_observation_unusable",
                    "source": source_id,
                    "observation_status": observation_status,
                    "checked_at": observation.get("checked_at"),
                    "coverage": observation.get("coverage"),
                })

    output_players: list[dict[str, Any]] = []
    primary_adp_applicable = 0
    primary_adp_listed = 0
    for player_id in sorted(sections_by_player, key=lambda value: (len(value), value)):
        legacy_player = player_lookup.get(player_id)
        if legacy_player is None:
            quality_issues.append({"severity": "error", "kind": "missing_player", "player_id": player_id})
            continue
        player = canonicalize_player_identity(
            player_id,
            legacy_player,
            identity_by_sleeper,
            sleeper_player_lookup,
        )

        source_results: dict[str, dict[str, Any]] = {}
        market: dict[str, dict[str, Any]] = {}
        for source in loaded_sources:
            definition = source.definition
            source_id = definition["source_id"]
            result, issue = evaluate_source_for_player(player, source)
            observation = current_observation_summary(source)
            if observation is not None:
                result["current_observation"] = observation
            source_results[source_id] = result
            if issue:
                quality_issues.append(issue)

            coverage = source_coverage[source_id]
            if not result["applicable"]:
                coverage["not_applicable_players"] += 1
            else:
                coverage["applicable_players"] += 1
                if result["listed"]:
                    coverage["listed_players"] += 1
                elif result["join_method"] == "ambiguous":
                    coverage["ambiguous_players"] += 1
                else:
                    coverage["not_listed_players"] += 1

            if definition["output"]["section"] == "market":
                market[definition["output"]["key"]] = flatten_source_result(result)

        redraft_adp = derive_adp_view(player, catalog, loaded_sources, source_results)
        if redraft_adp["primary_applicability"] == "applicable":
            primary_adp_applicable += 1
            if redraft_adp["primary_listed"]:
                primary_adp_listed += 1

        injury = derive_injury_signal(player)
        research_reasons = ["role_opportunity_requires_qualitative_context"]
        if injury["external_verification_priority"] == "high":
            research_reasons.insert(0, "current_structured_injury_signal_requires_verification")

        output_players.append(
            {
                "player_id": player_id,
                "name": optional_text(player.get("Name")),
                "position": optional_text(player.get("Position")),
                "nfl_team": optional_text(player.get("TeamAbbr")),
                "roster_sections": sorted(sections_by_player[player_id]),
                "is_starter": player_id in starters,
                "app_data": {
                    "status": optional_text(player.get("Status")),
                    "age": optional_number(player.get("Age")),
                    "years_experience": optional_number(player.get("Year")),
                    "salary": optional_number(player.get("Salary")),
                    "salary_projected": optional_number(player.get("SalaryProjected")),
                    "is_free_agent": optional_bool(player.get("IsFreeAgent")),
                },
                "injury": injury,
                "source_signals": source_results,
                "market": market,
                "redraft_adp": redraft_adp,
                "external_research": {
                    "injury_priority": injury["external_verification_priority"],
                    "role_opportunity_priority": "routine",
                    "reasons": research_reasons,
                },
            }
        )

    source_records = [
        {
            "id": item.id,
            "path": item.relative_path,
            "content_sha256": item.content_sha256,
            "source_timestamp": item.source_timestamp,
        }
        for item in source_files
    ]
    generated_at = max_timestamp(item.source_timestamp for item in source_files)
    input_fingerprint = sha256_text(canonical_json(source_records))
    coverage = {
        "managed_roster_ids": len(sections_by_player),
        "resolved_players": len(output_players),
        "players_with_current_injury_signal": sum(
            1
            for item in output_players
            if item["injury"]["coverage_status"] != "no_current_injury_signal"
        ),
        "primary_adp_applicable": primary_adp_applicable,
        "primary_adp_listed": primary_adp_listed,
        "sources": source_coverage,
        "source_observations": source_observations,
    }
    status = quality_status(quality_issues)
    data = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "managed-roster-signals",
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "managed_team": {
            "team_id": managed_team.get("TeamID"),
            "name": optional_text(managed_display_team.get("Team")),
            "abbreviation": optional_text(managed_display_team.get("TeamAbbr")),
            "player_count": len(output_players),
        },
        "sources": source_records,
        "players": output_players,
        "quality": {
            "status": status,
            "issue_count": len(quality_issues),
            "issues": quality_issues,
            "coverage": coverage,
        },
    }
    validate_output(data)

    quality_report = {
        "schema_version": 1,
        "report_id": "fantasy-operations-data-quality",
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "status": status,
        "coverage": coverage,
        "issues": quality_issues,
        "source_freshness": [
            {
                "id": source["id"],
                "path": source["path"],
                "source_timestamp": source["source_timestamp"],
            }
            for source in source_records
        ],
        "interpretation_limits": [
            "Structured injury data is a secondary signal and not a substitute for current external verification.",
            "Role and opportunity are intentionally not inferred by this deterministic materialization.",
            "Source applicability, expected absence and warning severity are declared in the Operations Source Catalog.",
            "A not_listed or not_applicable result is not a negative player evaluation.",
        ],
    }
    return data, quality_report


def write_json_if_changed(path: Path, data: dict[str, Any]) -> bool:
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/input-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Fail when generated files are not current.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    data, quality = build(root, config_path)
    output_path = root / config["outputs"]["managed_roster_signals"]
    quality_path = root / config["outputs"]["data_quality"]

    if args.check:
        expected = {
            output_path: json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            quality_path: json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        }
        stale = [
            relative_to_root(path, root)
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print("Generated Fantasy Operations inputs are stale:")
            for path in stale:
                print(f"- {path}")
            return 1
        print("OK: Fantasy Operations inputs are current.")
        return 0

    changed = [
        relative_to_root(output_path, root) if write_json_if_changed(output_path, data) else None,
        relative_to_root(quality_path, root) if write_json_if_changed(quality_path, quality) else None,
    ]
    written = [path for path in changed if path]
    if written:
        print("Updated:")
        for path in written:
            print(f"- {path}")
    else:
        print("No Fantasy Operations input changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
