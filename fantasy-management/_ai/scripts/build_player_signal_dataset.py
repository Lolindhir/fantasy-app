#!/usr/bin/env python3
"""Build the central provider-neutral Fantasy Operations player-signal dataset.

This layer joins current app/player data, league ownership, normalized external
rankings/projections and already materialized external activity signals. It is a
deterministic preparation layer: it does not browse, call AI services or emit
fantasy recommendations.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402
import materialize_external_signals as external_signals  # noqa: E402


SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "player-signals"


class PlayerSignalMaterializationError(RuntimeError):
    """Raised when the central player-signal dataset cannot be built safely."""


def source_record(source: ops.SourceFile) -> dict[str, Any]:
    return {
        "id": source.id,
        "path": source.relative_path,
        "content_sha256": source.content_sha256,
        "source_timestamp": source.source_timestamp,
    }


def freshness_view(
    source: ops.LoadedCatalogSource,
    generated_at: str | None,
) -> dict[str, Any]:
    source_timestamp = source.ranking_source.source_timestamp
    max_age_hours = int((source.definition.get("freshness") or {}).get("max_age_hours", 0))
    generated_dt = ops.parse_datetime(generated_at)
    source_dt = ops.parse_datetime(source_timestamp)
    age_hours: float | None = None
    status = "unknown"
    if generated_dt is not None and source_dt is not None:
        age_hours = round(max(0.0, (generated_dt - source_dt).total_seconds() / 3600), 2)
        status = "stale" if max_age_hours and age_hours > max_age_hours else "current"
    return {
        "source_timestamp": source_timestamp,
        "max_age_hours": max_age_hours or None,
        "age_hours_at_materialization": age_hours,
        "status": status,
    }


def enrich_source_result(
    result: dict[str, Any],
    source: ops.LoadedCatalogSource,
    generated_at: str | None,
) -> dict[str, Any]:
    return {
        **result,
        "freshness": freshness_view(source, generated_at),
    }


def activity_index(document: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    views = document.get("views") if isinstance(document.get("views"), dict) else {}
    sleeper = views.get("sleeper-trending") if isinstance(views.get("sleeper-trending"), dict) else {}
    indexed: dict[str, dict[str, Any]] = defaultdict(dict)
    for activity_type in ("add", "drop"):
        rows = sleeper.get(activity_type) if isinstance(sleeper.get(activity_type), list) else []
        for row in rows:
            if not isinstance(row, dict) or row.get("player_id") is None:
                continue
            indexed[str(row["player_id"])][activity_type] = {
                "status": "listed",
                "rank": ops.optional_number(row.get("rank")),
                "count": ops.optional_number(row.get("count")),
            }

    source_states = document.get("source_states") if isinstance(document.get("source_states"), list) else []
    sleeper_state = next(
        (state for state in source_states if isinstance(state, dict) and state.get("source_id") == "sleeper-trending"),
        {},
    )
    metadata = {
        "source_id": "sleeper-trending",
        "provider": sleeper_state.get("provider") or "sleeper",
        "dataset_id": sleeper_state.get("dataset_id"),
        "source_timestamp": sleeper_state.get("source_timestamp"),
        "comparison": sleeper_state.get("comparison") if isinstance(sleeper_state.get("comparison"), dict) else {},
    }
    return indexed, metadata


def activity_view(player_id: str, indexed: dict[str, dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    player_activity = indexed.get(player_id, {})
    add = player_activity.get("add") or {"status": "not_listed", "rank": None, "count": None}
    drop = player_activity.get("drop") or {"status": "not_listed", "rank": None, "count": None}
    listed = add["status"] == "listed" or drop["status"] == "listed"
    return {
        **metadata,
        "coverage_status": "listed_in_current_union" if listed else "not_listed_in_current_union",
        "listed": listed,
        "add": add,
        "drop": drop,
        "absence_semantics": "not_listed means outside the provider top-N list, never zero activity",
    }


def projection_view(
    loaded_sources: list[ops.LoadedCatalogSource],
    source_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    providers: dict[str, dict[str, Any]] = {}
    listed_percentiles: list[float] = []
    for source in loaded_sources:
        definition = source.definition
        if definition["output"]["section"] != "projections":
            continue
        result = source_results[definition["source_id"]]
        key = definition["output"]["key"]
        providers[key] = ops.flatten_source_result(result)
        percentile_value = (result.get("signals") or {}).get("percentile")
        if result.get("listed") and percentile_value is not None:
            listed_percentiles.append(float(percentile_value))

    consensus_percentile: float | None = None
    percentile_spread: float | None = None
    if listed_percentiles:
        consensus_percentile = round(sum(listed_percentiles) / len(listed_percentiles), 2)
    if len(listed_percentiles) >= 2:
        percentile_spread = round(max(listed_percentiles) - min(listed_percentiles), 2)

    return {
        "providers": providers,
        "summary": {
            "applicable_provider_count": sum(1 for value in providers.values() if value["applicable"]),
            "listed_provider_count": sum(1 for value in providers.values() if value["listed"]),
            "consensus_percentile": consensus_percentile,
            "percentile_spread": percentile_spread,
            "provider_fantasy_points_policy": "kept_separate_not_averaged",
        },
    }


def role_view(player: dict[str, Any]) -> dict[str, Any]:
    depth_position = ops.optional_text(player.get("SleeperDepthChartPosition"))
    depth_order = ops.optional_number(player.get("SleeperDepthChartOrder"))
    return {
        "sleeper_depth_chart_position": depth_position,
        "sleeper_depth_chart_order": depth_order,
        "coverage_status": "available" if depth_position is not None or depth_order is not None else "not_available",
        "interpretation": "nominal_depth_chart_only_not_usage",
    }


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "managed_team",
        "population",
        "sources",
        "players",
        "quality",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise PlayerSignalMaterializationError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise PlayerSignalMaterializationError("Unexpected player-signal schema version")
    player_ids = [str(player.get("player_id")) for player in data["players"]]
    if len(player_ids) != len(set(player_ids)):
        raise PlayerSignalMaterializationError("Player-signal output contains duplicate player IDs")


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = ops.load_json(config_path)
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise PlayerSignalMaterializationError("Unexpected player-signal materialization config schema version")

    core = config["sources"]
    league_path = root / core["league"]
    players_path = root / core["players"]
    timestamps_path = root / core["timestamps"]
    external_signal_path = root / core["external_signal_relevance"]
    catalog_path = root / config["source_catalog"]

    league = ops.load_json(league_path)
    players = ops.load_json(players_path)
    timestamps = ops.load_json(timestamps_path)
    external_signal_document = ops.load_json(external_signal_path)
    catalog = ops.load_json(catalog_path)
    ops.validate_catalog(catalog)
    if not isinstance(players, list):
        raise PlayerSignalMaterializationError("Players input must be a JSON array")

    teams = league.get("Teams") if isinstance(league.get("Teams"), list) else []
    managed_team_id = str(config["managed_team"]["team_id"])
    managed_team = next((team for team in teams if str(team.get("TeamID")) == managed_team_id), None)
    if managed_team is None:
        raise PlayerSignalMaterializationError(f"Managed team {managed_team_id} not found")

    loaded_sources = [
        ops.resolve_catalog_source(root, definition)
        for definition in catalog["sources"]
        if definition.get("active")
    ]
    ownership = external_signals.build_ownership(teams)
    activity_by_player, activity_metadata = activity_index(external_signal_document)

    player_timestamp = timestamps.get("Players") if isinstance(timestamps, dict) else None
    league_timestamp = timestamps.get("League") if isinstance(timestamps, dict) else None
    external_signal_timestamp = external_signal_document.get("generated_at") if isinstance(external_signal_document, dict) else None
    input_sources = [
        ops.source_file("league", league_path, root, league_timestamp),
        ops.source_file("players", players_path, root, player_timestamp),
        ops.source_file(
            "timestamps",
            timestamps_path,
            root,
            ops.max_timestamp(timestamps.values()) if isinstance(timestamps, dict) else None,
        ),
        ops.source_file("operations_source_catalog", catalog_path, root),
        ops.source_file("external_signal_relevance", external_signal_path, root, external_signal_timestamp),
    ]
    for source in loaded_sources:
        input_sources.extend([source.pointer_source, source.ranking_source])

    generated_at = ops.max_timestamp(source.source_timestamp for source in input_sources)
    allowed_positions = {str(position).upper() for position in config["population"]["positions"]}

    quality_issues: list[dict[str, Any]] = []
    upstream_quality = external_signal_document.get("quality") if isinstance(external_signal_document.get("quality"), dict) else {}
    for issue in upstream_quality.get("issues") or []:
        if isinstance(issue, dict):
            quality_issues.append({**issue, "origin": "external_signal_relevance"})

    for source in loaded_sources:
        source_id = source.definition["source_id"]
        minimum_rows = int((source.definition.get("quality") or {}).get("minimum_rows", 0))
        if source.index["row_count"] < minimum_rows:
            issue = ops.severity_issue(
                source.definition["quality"].get("row_count_severity", "error"),
                kind="unexpected_row_count",
                source_id=source_id,
                details={"actual_rows": source.index["row_count"], "minimum_rows": minimum_rows},
            )
            if issue:
                quality_issues.append(issue)

        freshness = freshness_view(source, generated_at)
        if freshness["status"] == "stale":
            quality_issues.append(
                {
                    "severity": "warning",
                    "kind": "stale_source",
                    "source": source_id,
                    "source_timestamp": freshness["source_timestamp"],
                    "age_hours_at_materialization": freshness["age_hours_at_materialization"],
                    "max_age_hours": freshness["max_age_hours"],
                }
            )
        elif freshness["status"] == "unknown":
            quality_issues.append(
                {
                    "severity": "info",
                    "kind": "unknown_source_freshness",
                    "source": source_id,
                    "source_timestamp": freshness["source_timestamp"],
                }
            )

    source_coverage: dict[str, Counter[str]] = {
        source.definition["source_id"]: Counter() for source in loaded_sources
    }
    ownership_counts: Counter[str] = Counter()
    position_counts: Counter[str] = Counter()
    population_reason_counts: Counter[str] = Counter()
    output_players: list[dict[str, Any]] = []

    for player in players:
        if not isinstance(player, dict) or player.get("ID") is None:
            continue
        player_id = str(player["ID"])
        position = str(player.get("Position") or "").upper()
        if position not in allowed_positions:
            continue

        raw_results: dict[str, dict[str, Any]] = {}
        enriched_results: dict[str, dict[str, Any]] = {}
        market: dict[str, dict[str, Any]] = {}
        for source in loaded_sources:
            definition = source.definition
            source_id = definition["source_id"]
            result, issue = ops.evaluate_source_for_player(player, source)
            raw_results[source_id] = result
            enriched = enrich_source_result(result, source, generated_at)
            enriched_results[source_id] = enriched
            if issue:
                quality_issues.append(issue)

            coverage_key = (
                "not_applicable"
                if not result["applicable"]
                else "listed"
                if result["listed"]
                else "ambiguous"
                if result.get("join_method") == "ambiguous"
                else "not_listed"
            )
            source_coverage[source_id][coverage_key] += 1
            if definition["output"]["section"] == "market":
                market[definition["output"]["key"]] = {
                    **ops.flatten_source_result(result),
                    "freshness": enriched["freshness"],
                }

        ownership_value = external_signals.ownership_for(player_id, ownership, managed_team_id)
        activity = activity_view(player_id, activity_by_player, activity_metadata)
        reasons: list[str] = []
        if ops.optional_text(player.get("TeamAbbr")):
            reasons.append("has_nfl_team")
        if ownership_value["status"] != "fantasy_free_agent":
            reasons.append("league_owned")
        if any(result.get("listed") for result in raw_results.values()):
            reasons.append("listed_in_external_source")
        if activity["listed"]:
            reasons.append("present_in_external_signal")
        if not reasons:
            continue

        for reason in reasons:
            population_reason_counts[reason] += 1
        ownership_counts[ownership_value["status"]] += 1
        position_counts[position] += 1

        redraft_adp = ops.derive_adp_view(player, catalog, loaded_sources, raw_results)
        for value in redraft_adp["formats"].values():
            source_id = value.get("source_id")
            if source_id and source_id in enriched_results:
                value["freshness"] = enriched_results[source_id]["freshness"]
        if redraft_adp.get("primary") and redraft_adp.get("primary_source_id") in enriched_results:
            redraft_adp["primary"]["freshness"] = enriched_results[redraft_adp["primary_source_id"]]["freshness"]

        projections = projection_view(loaded_sources, raw_results)
        for value in projections["providers"].values():
            source_id = value.get("source_id")
            if source_id and source_id in enriched_results:
                value["freshness"] = enriched_results[source_id]["freshness"]

        output_players.append(
            {
                "player_id": player_id,
                "name": ops.optional_text(player.get("Name")),
                "position": position,
                "nfl_team": ops.optional_text(player.get("TeamAbbr")),
                "population_reasons": reasons,
                "ownership": ownership_value,
                "app_data": {
                    "status": ops.optional_text(player.get("Status")),
                    "age": ops.optional_number(player.get("Age")),
                    "years_experience": ops.optional_number(player.get("Year")),
                    "salary": ops.optional_number(player.get("Salary")),
                    "salary_projected": ops.optional_number(player.get("SalaryProjected")),
                    "is_free_agent_source_field": ops.optional_bool(player.get("IsFreeAgent")),
                    "espn_id": ops.optional_text(player.get("ESPNID")),
                },
                "injury": ops.derive_injury_signal(player),
                "role": role_view(player),
                "source_signals": enriched_results,
                "market": market,
                "redraft_adp": redraft_adp,
                "projections": projections,
                "activity": activity,
            }
        )

    output_players.sort(
        key=lambda player: (
            player["position"],
            (player["name"] or "").casefold(),
            player["player_id"],
        )
    )

    source_records = [source_record(source) for source in input_sources]
    fingerprint_payload = {
        "config": config,
        "sources": source_records,
        "players": [
            {
                "player_id": player["player_id"],
                "population_reasons": player["population_reasons"],
                "ownership": player["ownership"],
                "source_signals": player["source_signals"],
                "activity": player["activity"],
            }
            for player in output_players
        ],
    }

    quality = {
        "status": ops.quality_status(quality_issues),
        "issue_count": len(quality_issues),
        "issues": quality_issues,
        "source_coverage": {
            source_id: dict(sorted(counter.items()))
            for source_id, counter in sorted(source_coverage.items())
        },
        "ownership": dict(sorted(ownership_counts.items())),
        "positions": dict(sorted(position_counts.items())),
        "population_reasons": dict(sorted(population_reason_counts.items())),
        "external_signal_upstream_status": upstream_quality.get("status"),
    }

    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": generated_at,
        "input_fingerprint": ops.sha256_text(ops.canonical_json(fingerprint_payload)),
        "managed_team": {
            "team_id": managed_team.get("TeamID"),
            "name": ops.optional_text(managed_team.get("Team")),
        },
        "population": {
            "player_count": len(output_players),
            "positions": sorted(allowed_positions),
            "inclusion_rule": "position is in configured fantasy positions and at least one population reason applies",
            "reason_counts": dict(sorted(population_reason_counts.items())),
        },
        "sources": source_records,
        "players": output_players,
        "quality": quality,
    }
    validate_output(result)
    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Build and validate without writing output")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = ops.load_json(config_path)
    result = build(root, config_path)
    if not args.check:
        output_path = root / config["output"]["player_signals"]
        write_json(output_path, result)
        print(f"Wrote {output_path.relative_to(root)} with {len(result['players'])} players.")
    else:
        print(
            f"Validated {len(result['players'])} players; quality={result['quality']['status']}; "
            f"issues={result['quality']['issue_count']}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
