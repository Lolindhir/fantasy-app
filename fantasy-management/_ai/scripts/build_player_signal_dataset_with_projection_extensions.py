#!/usr/bin/env python3
"""Build player signals with configured catalog extensions and league-scoring projection enrichment.

The canonical player-signal builder remains responsible for population, joins, quality,
ownership and output shape. This adapter composes declared source-catalog extensions and
enriches applicable offensive projection providers with comparable Mighty-Giants core
points calculated only from stats that both active projection providers actually publish.

Configured extension sources whose first snapshot has not been materialized yet are kept
as an explicit warning instead of making the entire Operations materialization unusable.
As soon as their latest pointer exists, they become normal active inputs automatically.

The same run may also materialize the managed-roster overview read model. That overview
keeps deterministic roster structure separate from hybrid evaluative role/security state.
"""
from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402
import build_managed_roster_overview as roster_overview  # noqa: E402
import build_player_signal_dataset as base  # noqa: E402


CORE_COMPONENTS: dict[str, list[tuple[str, str]]] = {
    "QB": [
        ("pass_yards", "pass_yd"),
        ("pass_touchdowns", "pass_td"),
        ("interceptions", "pass_int"),
        ("rush_yards", "rush_yd"),
        ("rush_touchdowns", "rush_td"),
    ],
    "RB": [
        ("rush_yards", "rush_yd"),
        ("rush_touchdowns", "rush_td"),
        ("receptions", "rec"),
        ("receiving_yards", "rec_yd"),
        ("receiving_touchdowns", "rec_td"),
    ],
    "WR": [
        ("receptions", "rec"),
        ("receiving_yards", "rec_yd"),
        ("receiving_touchdowns", "rec_td"),
        ("rush_yards", "rush_yd"),
        ("rush_touchdowns", "rush_td"),
    ],
    "TE": [
        ("receptions", "rec"),
        ("receiving_yards", "rec_yd"),
        ("receiving_touchdowns", "rec_td"),
    ],
}
EXCLUDED_SCORING_KEYS = {
    "QB": ["pass_2pt", "rush_2pt", "fum_lost"],
    "RB": ["rush_2pt", "rec_2pt", "fum_lost"],
    "WR": ["rush_2pt", "rec_2pt", "fum_lost"],
    "TE": ["rec_2pt", "fum_lost"],
}


def _score_value(scoring: dict[str, Any], key: str) -> float:
    value = ops.optional_number(scoring.get(key))
    return float(value) if value is not None else 0.0


def league_scoring_view(position: str, result: dict[str, Any], scoring: dict[str, Any]) -> dict[str, Any]:
    if position not in CORE_COMPONENTS:
        return {
            "status": "position_specific_elsewhere" if position == "K" else "not_applicable",
            "core_points": None,
            "policy": "kicker scoring is reconciled by kicker-streaming-inputs" if position == "K" else "not_applicable",
            "included_components": [],
            "excluded_nonzero_components": [],
        }
    if not result.get("listed"):
        return {
            "status": "not_listed",
            "core_points": None,
            "policy": "no league score is inferred for an unlisted provider row",
            "included_components": [],
            "excluded_nonzero_components": [],
        }

    signals = result.get("signals") if isinstance(result.get("signals"), dict) else {}
    included: list[dict[str, Any]] = []
    missing: list[str] = []
    points = 0.0
    for signal_name, scoring_key in CORE_COMPONENTS[position]:
        signal_value = ops.optional_number(signals.get(signal_name))
        if signal_value is None:
            missing.append(signal_name)
            continue
        multiplier = _score_value(scoring, scoring_key)
        contribution = float(signal_value) * multiplier
        points += contribution
        included.append(
            {
                "signal": signal_name,
                "scoring_key": scoring_key,
                "projected_stat": signal_value,
                "multiplier": multiplier,
                "points": round(contribution, 3),
            }
        )

    if missing:
        return {
            "status": "incomplete_core_stats",
            "core_points": None,
            "policy": "fail closed when a scoring-relevant core stat is missing",
            "included_components": included,
            "missing_core_stats": missing,
            "excluded_nonzero_components": [],
        }

    excluded = [
        {
            "scoring_key": key,
            "multiplier": _score_value(scoring, key),
            "reason": "not projected comparably by both active providers",
        }
        for key in EXCLUDED_SCORING_KEYS[position]
        if _score_value(scoring, key) != 0
    ]
    return {
        "status": "reconciled_core",
        "core_points": round(points, 2),
        "policy": "Mighty Giants scoring applied only to source-projected components shared across active providers; missing stats are never imputed",
        "included_components": included,
        "excluded_nonzero_components": excluded,
    }


def projection_view_factory(scoring: dict[str, Any]):
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
            if not result.get("applicable"):
                continue
            key = definition["output"]["key"]
            position = str((definition.get("format_context") or {}).get("position_scope") or "").upper()
            provider_view = ops.flatten_source_result(result)
            provider_view["league_scoring"] = league_scoring_view(position, result, scoring)
            providers[key] = provider_view
            percentile_value = (result.get("signals") or {}).get("percentile")
            if result.get("listed") and percentile_value is not None:
                listed_percentiles.append(float(percentile_value))

        consensus_percentile = round(sum(listed_percentiles) / len(listed_percentiles), 2) if listed_percentiles else None
        percentile_spread = round(max(listed_percentiles) - min(listed_percentiles), 2) if len(listed_percentiles) >= 2 else None
        return {
            "providers": providers,
            "summary": {
                "applicable_provider_count": len(providers),
                "listed_provider_count": sum(1 for value in providers.values() if value["listed"]),
                "consensus_percentile": consensus_percentile,
                "percentile_spread": percentile_spread,
                "provider_fantasy_points_policy": "kept_separate_not_averaged",
            },
        }

    return projection_view


def _extension_source_is_materialized(root: Path, definition: dict[str, Any]) -> bool:
    access = definition.get("access") if isinstance(definition.get("access"), dict) else {}
    location = access.get("location")
    return isinstance(location, str) and bool(location) and (root / location).is_file()


def build(root: Path, config_path: Path) -> dict[str, Any]:
    real_load_json = ops.load_json
    config = real_load_json(config_path)
    base_catalog_path = root / config["source_catalog"]
    extension_paths = [root / value for value in config.get("source_catalog_extensions") or []]
    base_catalog = real_load_json(base_catalog_path)
    ops.validate_catalog(base_catalog)

    merged_catalog = deepcopy(base_catalog)
    extension_source_records: list[ops.SourceFile] = []
    pending_sources: list[dict[str, str]] = []
    for index, extension_path in enumerate(extension_paths, start=1):
        extension = real_load_json(extension_path)
        ops.validate_catalog(extension)
        extension_source_records.append(
            ops.source_file(f"operations_source_catalog_extension_{index}", extension_path, root)
        )
        for definition in extension["sources"]:
            if not definition.get("active"):
                continue
            if _extension_source_is_materialized(root, definition):
                merged_catalog["sources"].append(definition)
            else:
                pending_sources.append(
                    {
                        "source_id": str(definition.get("source_id") or "unknown"),
                        "location": str((definition.get("access") or {}).get("location") or ""),
                    }
                )
    ops.validate_catalog(merged_catalog)

    league = real_load_json(root / config["sources"]["league"])
    scoring = league.get("ScoringType") if isinstance(league.get("ScoringType"), dict) else {}

    def load_json_with_merged_catalog(path: Path) -> Any:
        if Path(path).resolve() == base_catalog_path.resolve():
            return merged_catalog
        return real_load_json(path)

    original_load_json = ops.load_json
    original_projection_view = base.projection_view
    ops.load_json = load_json_with_merged_catalog
    base.projection_view = projection_view_factory(scoring)
    try:
        result = base.build(root, config_path)
    finally:
        ops.load_json = original_load_json
        base.projection_view = original_projection_view

    for pending in pending_sources:
        result["quality"]["issues"].append(
            {
                "severity": "warning",
                "kind": "configured_projection_source_not_materialized",
                "source": pending["source_id"],
                "location": pending["location"],
            }
        )
    if pending_sources:
        result["quality"]["issue_count"] = len(result["quality"]["issues"])
        result["quality"]["status"] = ops.quality_status(result["quality"]["issues"])

    if extension_source_records:
        result["sources"].extend(base.source_record(source) for source in extension_source_records)

    fingerprint_payload = {
        "config": config,
        "sources": result["sources"],
        "players": [
            {
                "player_id": player["player_id"],
                "population_reasons": player["population_reasons"],
                "ownership": player["ownership"],
                "source_signals": player["source_signals"],
                "activity": player["activity"],
            }
            for player in result["players"]
        ],
        "pending_extension_sources": pending_sources,
    }
    result["input_fingerprint"] = ops.sha256_text(ops.canonical_json(fingerprint_payload))
    base.validate_output(result)
    return result


def materialize_managed_roster_overview(root: Path, config: dict[str, Any]) -> list[str]:
    overview_config_value = config.get("managed_roster_overview_config")
    if not overview_config_value:
        return []
    overview_config_path = root / str(overview_config_value)
    overview = roster_overview.build(root, overview_config_path)
    return roster_overview.write_outputs(root, overview_config_path, overview)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/player-signal-materialization.json"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = ops.load_json(config_path)
    result = build(root, config_path)
    if args.check:
        print(
            f"Validated {len(result['players'])} players; quality={result['quality']['status']}; "
            f"issues={result['quality']['issue_count']}."
        )
        if config.get("managed_roster_overview_config"):
            overview_config_path = root / str(config["managed_roster_overview_config"])
            overview = roster_overview.build(root, overview_config_path)
            print(
                "Validated managed roster overview: players={}; quality={}; unclassified={}.".format(
                    len(overview["players"]),
                    overview["quality"]["status"],
                    overview["evaluation"]["unclassified_count"],
                )
            )
        return 0
    output_path = root / config["output"]["player_signals"]
    base.write_json(output_path, result)
    print(f"Wrote {output_path.relative_to(root)} with {len(result['players'])} players.")
    changed = materialize_managed_roster_overview(root, config)
    if changed:
        print("Updated managed roster overview:")
        for path in changed:
            print(f"- {path}")
    elif config.get("managed_roster_overview_config"):
        print("No managed roster overview changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
