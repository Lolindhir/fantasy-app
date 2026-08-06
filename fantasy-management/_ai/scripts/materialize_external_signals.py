#!/usr/bin/env python3
"""Join normalized external signals to player identity and league ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
CATALOG_SCHEMA_VERSION = 1
SEVERITIES = {"none", "info", "warning", "error"}
SIGNAL_TYPES = {"text", "number", "boolean"}
NON_PLAYER_HANDLINGS = {"exclude"}
ROSTER_SECTIONS = ("Roster", "Reserve", "Taxi")
QUALITY_DOMAIN = "external_signal_materialization"


class ExternalSignalMaterializationError(RuntimeError):
    """Raised when external-signal inputs cannot be materialized safely."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExternalSignalMaterializationError(
            f"Missing required JSON input: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ExternalSignalMaterializationError(
            f"Invalid JSON input {path}: {exc}"
        ) from exc


def nested_get(value: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def text(value: Any) -> str | None:
    normalized = "" if value is None else str(value).strip()
    return normalized or None


def number(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return int(parsed) if parsed.is_integer() else round(parsed, 4)


def boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = text(value)
    if normalized is None:
        return None
    if normalized.casefold() in {"true", "1", "yes"}:
        return True
    if normalized.casefold() in {"false", "0", "no"}:
        return False
    return None


def convert(value: Any, signal_type: str) -> Any:
    return {"text": text, "number": number, "boolean": boolean}[signal_type](
        value
    )


def parse_datetime(value: Any) -> datetime | None:
    normalized = text(value)
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def max_timestamp(values: Iterable[Any]) -> str | None:
    parsed = [item for item in (parse_datetime(value) for value in values) if item]
    return (
        max(parsed).isoformat().replace("+00:00", "Z")
        if parsed
        else None
    )


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def file_record(
    source_id: str,
    path: Path,
    root: Path,
    timestamp: Any = None,
) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ExternalSignalMaterializationError(
            f"Missing required source file: {path}"
        ) from exc
    return {
        "id": source_id,
        "path": relative(path, root),
        "content_sha256": sha256(content),
        "source_timestamp": max_timestamp([timestamp]),
    }


def validate_catalog(catalog: dict[str, Any]) -> None:
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ExternalSignalMaterializationError(
            "Unexpected external signal catalog schema version"
        )
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ExternalSignalMaterializationError(
            "External signal catalog must contain sources"
        )

    seen: set[str] = set()
    for source in sources:
        source_id = text(source.get("source_id"))
        if not source_id:
            raise ExternalSignalMaterializationError(
                "External signal source has no source_id"
            )
        if source_id in seen:
            raise ExternalSignalMaterializationError(
                f"Duplicate external signal source_id: {source_id}"
            )
        seen.add(source_id)

        if not isinstance(source.get("active"), bool):
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has invalid active flag"
            )
        if not source["active"]:
            continue

        required = (
            "provider",
            "dataset_id",
            "location",
            "rows_field",
            "source_player_id_field",
        )
        missing = [field for field in required if not text(source.get(field))]
        if missing:
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has no {missing[0]}"
            )
        if source.get("comparison_contract") != "top_n_activity_v1":
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has unsupported comparison contract"
            )
        if (
            not isinstance(source.get("timestamp_fields"), list)
            or not source["timestamp_fields"]
        ):
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has no timestamp_fields"
            )

        mappings = source.get("signal_fields")
        if not isinstance(mappings, list) or not mappings:
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has no signal_fields"
            )
        targets: set[str] = set()
        for mapping in mappings:
            target = text(mapping.get("target"))
            if (
                not target
                or target in targets
                or not text(mapping.get("source_field"))
                or mapping.get("type") not in SIGNAL_TYPES
            ):
                raise ExternalSignalMaterializationError(
                    f"External signal source {source_id} has invalid signal mapping"
                )
            targets.add(target)

        if source.get("unresolved_identity_severity", "info") not in SEVERITIES:
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has invalid unresolved identity severity"
            )

        rules = source.get("non_player_entity_rules") or []
        if not isinstance(rules, list):
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} has invalid non-player entity rules"
            )
        for rule in rules:
            pattern = text(rule.get("source_id_regex")) if isinstance(rule, dict) else None
            entity_type = text(rule.get("entity_type")) if isinstance(rule, dict) else None
            handling = rule.get("handling") if isinstance(rule, dict) else None
            if not pattern or not entity_type or handling not in NON_PLAYER_HANDLINGS:
                raise ExternalSignalMaterializationError(
                    f"External signal source {source_id} has invalid non-player entity rule"
                )
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ExternalSignalMaterializationError(
                    f"External signal source {source_id} has invalid non-player entity regex"
                ) from exc


def classify_non_player_entity(
    source_entity_id: str,
    source: dict[str, Any],
) -> dict[str, str] | None:
    """Return the first matching declarative non-player entity rule."""

    for rule in source.get("non_player_entity_rules") or []:
        if re.fullmatch(rule["source_id_regex"], source_entity_id):
            return {
                "entity_type": rule["entity_type"],
                "handling": rule["handling"],
            }
    return None


def quality_status(issues: list[dict[str, Any]]) -> str:
    if any(issue.get("severity") == "error" for issue in issues):
        return "error"
    if any(issue.get("severity") == "warning" for issue in issues):
        return "warning"
    return "ok"


def build_ownership(
    teams: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for team in teams:
        team_id = str(team.get("TeamID") or "")
        for section in ROSTER_SECTIONS:
            for player_id in team.get(section) or []:
                record = result[str(player_id)].setdefault(
                    team_id,
                    {
                        "team_id": team.get("TeamID"),
                        "team_name": text(team.get("Team")),
                        "team_abbreviation": text(team.get("TeamAbbr")),
                        "roster_sections": [],
                    },
                )
                section_name = section.casefold()
                if section_name not in record["roster_sections"]:
                    record["roster_sections"].append(section_name)
    return {
        player_id: [
            {
                **record,
                "roster_sections": sorted(record["roster_sections"]),
            }
            for _, record in sorted(records.items())
        ]
        for player_id, records in result.items()
    }


def ownership_for(
    player_id: str,
    ownership: dict[str, list[dict[str, Any]]],
    managed_team_id: str,
) -> dict[str, Any]:
    teams = ownership.get(player_id, [])
    if not teams:
        status = "fantasy_free_agent"
    elif len(teams) > 1:
        status = "multiple_rosters"
    elif str(teams[0]["team_id"]) == managed_team_id:
        status = "mighty_giants"
    else:
        status = "opponent_rostered"
    return {"status": status, "teams": teams}


def comparison_index(
    document: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    comparison = (
        document.get("comparison")
        if isinstance(document.get("comparison"), dict)
        else {}
    )
    activity = (
        comparison.get("activity")
        if isinstance(comparison.get("activity"), dict)
        else {}
    )
    indexed: dict[str, dict[str, Any]] = defaultdict(dict)
    for activity_type, changes in activity.items():
        if not isinstance(changes, dict):
            continue
        for kind in ("entered_top_n", "left_top_n"):
            for player_id in changes.get(kind) or []:
                indexed[str(player_id)].setdefault(activity_type, {})[kind] = True
        for kind in ("rank_changed", "count_changed"):
            for item in changes.get(kind) or []:
                if not isinstance(item, dict):
                    continue
                player_id = text(
                    item.get("sleeper_player_id") or item.get("player_id")
                )
                if player_id:
                    indexed[player_id].setdefault(activity_type, {})[kind] = item

    state = {
        "baseline": bool(comparison.get("baseline")),
        "comparable": bool(comparison.get("comparable")),
        "reason": text(comparison.get("reason")),
        "previous_generated_at": text(comparison.get("previous_generated_at")),
        "material_event_eligible": bool(
            comparison.get("material_event_eligible")
        ),
        "rolling_window_warning": text(
            comparison.get("rolling_window_warning")
        ),
    }
    return dict(indexed), state


def build_views(
    source_id: str,
    players: list[dict[str, Any]],
) -> dict[str, Any]:
    views = {"add": [], "drop": []}
    for player in players:
        source = player["source_signals"].get(source_id)
        if not source:
            continue
        signals = source["signals"]
        for activity_type in ("add", "drop"):
            rank = signals.get(f"{activity_type}_rank")
            if rank is None:
                continue
            views[activity_type].append(
                {
                    "rank": rank,
                    "player_id": player["player_id"],
                    "name": player["name"],
                    "position": player["position"],
                    "nfl_team": player["nfl_team"],
                    "count": signals.get(f"{activity_type}_count"),
                    "ownership_status": player["ownership"]["status"],
                    "owner_teams": player["ownership"]["teams"],
                }
            )
    for rows in views.values():
        rows.sort(key=lambda row: (row["rank"], row["player_id"]))
    return views


def count_by_key(
    values: Iterable[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value[key])] += 1
    return dict(sorted(counts.items()))


def build(
    root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(config_path)
    if config.get("schema_version") != 1:
        raise ExternalSignalMaterializationError(
            "Unexpected external signal materialization config schema version"
        )

    paths = {key: root / value for key, value in config["sources"].items()}
    catalog_path = root / config["signal_catalog"]
    league = load_json(paths["league"])
    players = load_json(paths["players"])
    quality = load_json(paths["base_quality"])
    catalog = load_json(catalog_path)
    validate_catalog(catalog)

    if not isinstance(players, list):
        raise ExternalSignalMaterializationError(
            "Players input must be a JSON array"
        )

    teams = league.get("Teams") or []
    managed = config["managed_team"]
    managed_id = str(managed["team_id"])
    managed_team = next(
        (
            team
            for team in teams
            if str(team.get(managed["identity_field"])) == managed_id
        ),
        None,
    )
    if not managed_team:
        raise ExternalSignalMaterializationError(
            f"Managed team {managed_id} not found"
        )

    player_lookup = {
        str(player.get("ID")): player
        for player in players
        if player.get("ID") is not None
    }
    ownership = build_ownership(teams)
    records = [
        file_record("league", paths["league"], root),
        file_record("players", paths["players"], root),
        file_record("external_signal_catalog", catalog_path, root),
    ]
    entries: dict[str, dict[str, Any]] = {}
    states: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for source in catalog["sources"]:
        if not source.get("active"):
            continue

        source_id = source["source_id"]
        source_path = root / source["location"]
        document = load_json(source_path)
        rows = nested_get(document, source["rows_field"])
        if (
            not isinstance(document, dict)
            or not isinstance(rows, list)
            or not rows
            or not all(isinstance(row, dict) for row in rows)
        ):
            raise ExternalSignalMaterializationError(
                f"External signal source {source_id} rows are not a non-empty object array"
            )

        source_timestamp = max_timestamp(
            nested_get(document, field)
            for field in source["timestamp_fields"]
        )
        records.append(
            file_record(
                f"{source_id}_json",
                source_path,
                root,
                source_timestamp,
            )
        )
        changes, comparison = comparison_index(document)

        row_by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            player_id = text(
                nested_get(row, source["source_player_id_field"])
            )
            if not player_id:
                raise ExternalSignalMaterializationError(
                    f"External signal source {source_id} row has no player identity"
                )
            if player_id in row_by_id:
                raise ExternalSignalMaterializationError(
                    f"External signal source {source_id} has duplicate player identity {player_id}"
                )
            row_by_id[player_id] = row

        excluded_entities: list[dict[str, str]] = []
        candidate_ids = sorted(
            set(row_by_id) | set(changes),
            key=lambda value: (len(value), value),
        )
        for player_id in candidate_ids:
            classification = classify_non_player_entity(player_id, source)
            if classification:
                if classification["handling"] == "exclude":
                    excluded_entities.append(
                        {
                            "source_entity_id": player_id,
                            "entity_type": classification["entity_type"],
                        }
                    )
                    continue
                raise ExternalSignalMaterializationError(
                    f"Unsupported non-player entity handling for {source_id}: "
                    f"{classification['handling']}"
                )

            row = row_by_id.get(player_id)
            local = player_lookup.get(player_id)
            owner = ownership_for(player_id, ownership, managed_id)
            entry = entries.setdefault(
                player_id,
                {
                    "player_id": player_id,
                    "name": text((local or {}).get("Name")),
                    "position": text((local or {}).get("Position")),
                    "nfl_team": text((local or {}).get("TeamAbbr")),
                    "identity_status": "resolved" if local else "unresolved",
                    "ownership": owner,
                    "source_signals": {},
                },
            )
            entry["source_signals"][source_id] = {
                "provider": source["provider"],
                "dataset_id": source["dataset_id"],
                "source_timestamp": source_timestamp,
                "listed_in_current_source_union": row is not None,
                "signals": {
                    mapping["target"]: (
                        convert(
                            nested_get(row, mapping["source_field"]),
                            mapping["type"],
                        )
                        if row
                        else None
                    )
                    for mapping in source["signal_fields"]
                },
                "changes": changes.get(player_id, {}),
                "comparison": comparison,
            }

            severity = source.get("unresolved_identity_severity", "info")
            if not local and severity != "none":
                issues.append(
                    {
                        "domain": QUALITY_DOMAIN,
                        "severity": severity,
                        "kind": "unresolved_external_signal_player",
                        "source": source_id,
                        "player_id": player_id,
                    }
                )
            if owner["status"] == "multiple_rosters":
                issues.append(
                    {
                        "domain": QUALITY_DOMAIN,
                        "severity": "error",
                        "kind": "player_on_multiple_fantasy_rosters",
                        "source": source_id,
                        "player_id": player_id,
                        "teams": owner["teams"],
                    }
                )

        states.append(
            {
                "source_id": source_id,
                "provider": source["provider"],
                "dataset_id": source["dataset_id"],
                "source_timestamp": source_timestamp,
                "attribution": text(
                    nested_get(
                        document,
                        source.get("attribution_field", "attribution"),
                    )
                ),
                "row_count": len(rows),
                "materialized_entity_count": len(candidate_ids)
                - len(excluded_entities),
                "excluded_non_player_entities": {
                    "count": len(excluded_entities),
                    "by_type": count_by_key(
                        excluded_entities,
                        "entity_type",
                    ),
                    "entity_ids": sorted(
                        item["source_entity_id"]
                        for item in excluded_entities
                    ),
                },
                "comparison": comparison,
            }
        )

    output_players = sorted(
        entries.values(),
        key=lambda item: (
            item["name"] is None,
            item["name"] or "",
            item["player_id"],
        ),
    )
    views = {
        source["source_id"]: build_views(
            source["source_id"],
            output_players,
        )
        for source in catalog["sources"]
        if source.get("active")
    }

    ownership_counts: dict[str, int] = defaultdict(int)
    for player in output_players:
        ownership_counts[player["ownership"]["status"]] += 1

    excluded_by_type: dict[str, int] = defaultdict(int)
    for state in states:
        for entity_type, count in state[
            "excluded_non_player_entities"
        ]["by_type"].items():
            excluded_by_type[entity_type] += count

    summary = {
        "players": len(output_players),
        "resolved_players": sum(
            player["identity_status"] == "resolved"
            for player in output_players
        ),
        "unresolved_players": sum(
            player["identity_status"] == "unresolved"
            for player in output_players
        ),
        "excluded_non_player_entities": sum(excluded_by_type.values()),
        "excluded_non_player_entities_by_type": dict(
            sorted(excluded_by_type.items())
        ),
        "ownership": dict(sorted(ownership_counts.items())),
    }

    for state in states:
        source_players = [
            player
            for player in output_players
            if state["source_id"] in player["source_signals"]
        ]
        state["resolved_players"] = sum(
            player["identity_status"] == "resolved"
            for player in source_players
        )
        state["unresolved_players"] = sum(
            player["identity_status"] == "unresolved"
            for player in source_players
        )
        state["ownership"] = count_by_key(
            [player["ownership"] for player in source_players],
            "status",
        )

    generated_at = max_timestamp(
        record["source_timestamp"] for record in records
    )
    fingerprint = sha256(canonical_json(records))
    dataset = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "external-signal-relevance",
        "generated_at": generated_at,
        "input_fingerprint": fingerprint,
        "managed_team": {
            "team_id": managed_team.get(managed["identity_field"]),
            "name": text(managed_team.get("Team")),
            "abbreviation": text(managed_team.get("TeamAbbr")),
        },
        "sources": records,
        "source_states": states,
        "summary": summary,
        "views": views,
        "players": output_players,
        "quality": {
            "status": quality_status(issues),
            "issue_count": len(issues),
            "issues": issues,
        },
    }

    base_issues = [
        issue
        for issue in quality.get("issues", [])
        if issue.get("domain") != QUALITY_DOMAIN
    ]
    combined = base_issues + issues
    coverage = dict(quality.get("coverage") or {})
    coverage["external_signals"] = {
        state["source_id"]: {
            "row_count": state["row_count"],
            "materialized_entity_count": state[
                "materialized_entity_count"
            ],
            "resolved_players": state["resolved_players"],
            "unresolved_players": state["unresolved_players"],
            "excluded_non_player_entities": state[
                "excluded_non_player_entities"
            ],
            "ownership": state["ownership"],
            "baseline": state["comparison"]["baseline"],
            "material_event_eligible": state["comparison"][
                "material_event_eligible"
            ],
        }
        for state in states
    }

    freshness = [
        item
        for item in quality.get("source_freshness", [])
        if not str(item.get("id", "")).startswith("external_signal_")
    ]
    freshness.extend(
        {
            "id": f"external_signal_{state['source_id']}",
            "path": next(
                record["path"]
                for record in records
                if record["id"] == f"{state['source_id']}_json"
            ),
            "source_timestamp": state["source_timestamp"],
        }
        for state in states
    )
    quality.update(
        {
            "generated_at": max_timestamp(
                [quality.get("generated_at"), generated_at]
            ),
            "input_fingerprint": sha256(
                canonical_json(
                    {
                        "base": quality.get("input_fingerprint"),
                        "external_signals": fingerprint,
                    }
                )
            ),
            "status": quality_status(combined),
            "coverage": coverage,
            "issues": combined,
            "source_freshness": freshness,
        }
    )
    limits = list(quality.get("interpretation_limits") or [])
    note = (
        "External roster-activity signals are research triggers and not "
        "automatic add, drop, trade, hold, shop or cut recommendations."
    )
    if note not in limits:
        limits.append(note)
    non_player_note = (
        "Catalog-classified non-player entities are excluded from player "
        "identity, ownership and free-agent views and reported separately."
    )
    if non_player_note not in limits:
        limits.append(non_player_note)
    quality["interpretation_limits"] = limits
    return dataset, quality


def write_if_changed(path: Path, data: dict[str, Any]) -> bool:
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "fantasy-management/automation/"
            "external-signal-materialization.json"
        ),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    root = args.root.resolve()
    config_path = (
        args.config
        if args.config.is_absolute()
        else root / args.config
    )
    config = load_json(config_path)
    dataset, quality = build(root, config_path)
    outputs = {
        root / config["outputs"]["external_signal_relevance"]: dataset,
        root / config["outputs"]["data_quality"]: quality,
    }

    if args.check:
        stale = [
            relative(path, root)
            for path, data in outputs.items()
            if not path.exists()
            or path.read_text(encoding="utf-8")
            != json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        ]
        if stale:
            print("Generated external signal inputs are stale:")
            print("\n".join(f"- {path}" for path in stale))
            return 1
        print("OK: external signal relevance is current.")
        return 0

    written = [
        relative(path, root)
        for path, data in outputs.items()
        if write_if_changed(path, data)
    ]
    if written:
        print("Updated:")
        print("\n".join(f"- {path}" for path in written))
    else:
        print("No external signal relevance changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
