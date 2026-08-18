#!/usr/bin/env python3
"""Build position-inclusive Fantasy Operations free-agent movement discovery signals.

The builder scans the complete current fantasy-free-agent population (QB/RB/WR/TE/K),
compares the current normalized ranking/ADP/projection snapshots with historical
snapshots, derives league-relative replacement proximity, and emits only players with
research-relevant movement. It is deterministic and does not browse or recommend adds.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402
import build_player_signal_dataset_with_projection_extensions as projection_ext  # noqa: E402
import free_agent_movement_market_calibration as market_calibration  # noqa: E402

SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "free-agent-movement-signals"
FREE_AGENT_DATASET_ID = "free-agent-signals"
PLAYER_DATASET_ID = "player-signals"
POSITIONS = {"QB", "RB", "WR", "TE", "K"}
LOWER_IS_BETTER_TARGETS = {"rank", "overall_rank", "position_rank", "adp"}


class FreeAgentMovementMaterializationError(RuntimeError):
    """Raised when free-agent movement discovery cannot be materialized safely."""


@dataclass(frozen=True)
class SourceHistory:
    definition: dict[str, Any]
    current: ops.LoadedCatalogSource
    current_snapshot_date: date
    baselines: dict[int, ops.LoadedCatalogSource | None]
    baseline_dates: dict[int, str | None]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FreeAgentMovementMaterializationError(f"Could not load JSON from {path}: {exc}") from exc


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise FreeAgentMovementMaterializationError("Unexpected movement materialization config schema version")
    windows = config.get("comparison_windows_days")
    if not isinstance(windows, list) or not windows or any(not isinstance(v, int) or v <= 0 for v in windows):
        raise FreeAgentMovementMaterializationError("comparison_windows_days must contain positive integers")
    if len(windows) != len(set(windows)):
        raise FreeAgentMovementMaterializationError("comparison_windows_days must be unique")
    replacement = config.get("replacement_relevance") or {}
    quantile = replacement.get("owned_boundary_quantile")
    near_distance = replacement.get("near_distance_percentile_points")
    if not isinstance(quantile, (int, float)) or not 0 <= float(quantile) <= 1:
        raise FreeAgentMovementMaterializationError("owned_boundary_quantile must be between 0 and 1")
    if not isinstance(near_distance, (int, float)) or float(near_distance) < 0:
        raise FreeAgentMovementMaterializationError("near_distance_percentile_points must be non-negative")
    if config.get("market_value_materiality") is not None:
        try:
            market_calibration.validate_config(config.get("market_value_materiality"))
        except market_calibration.MarketCalibrationError as exc:
            raise FreeAgentMovementMaterializationError(str(exc)) from exc


def validate_source_documents(free_agents: dict[str, Any], players: dict[str, Any]) -> None:
    if free_agents.get("schema_version") != 1 or free_agents.get("dataset_id") != FREE_AGENT_DATASET_ID:
        raise FreeAgentMovementMaterializationError("Input is not a schema-version-1 free-agent-signals dataset")
    if players.get("schema_version") != 1 or players.get("dataset_id") != PLAYER_DATASET_ID:
        raise FreeAgentMovementMaterializationError("Input is not a schema-version-1 player-signals dataset")
    if (free_agents.get("quality") or {}).get("status") not in {"ok", "warning"}:
        raise FreeAgentMovementMaterializationError("free-agent-signals quality must be ok or warning")
    if (players.get("quality") or {}).get("status") not in {"ok", "warning"}:
        raise FreeAgentMovementMaterializationError("player-signals quality must be ok or warning")


def _extract_date(value: Any) -> date | None:
    text = ops.optional_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _snapshot_date(pointer: dict[str, Any], ranking_file: Path) -> date | None:
    for key in ("snapshot_date", "source_updated_date", "ranking_fetched_at", "raw_fetched_at", "fetched_at"):
        parsed = _extract_date(pointer.get(key))
        if parsed:
            return parsed
    return _extract_date(ranking_file.parent.name)


def _load_merged_catalog(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    source_cfg = config["source"]
    base_path = root / source_cfg["source_catalog"]
    base = load_json(base_path)
    ops.validate_catalog(base)
    merged = deepcopy(base)
    pending: list[dict[str, str]] = []
    for relative in source_cfg.get("source_catalog_extensions") or []:
        extension_path = root / relative
        extension = load_json(extension_path)
        ops.validate_catalog(extension)
        for definition in extension["sources"]:
            if not definition.get("active"):
                continue
            location = str((definition.get("access") or {}).get("location") or "")
            if location and (root / location).is_file():
                merged["sources"].append(definition)
            else:
                pending.append({"source_id": str(definition.get("source_id") or "unknown"), "location": location})
    ops.validate_catalog(merged)
    return merged, pending


def _historical_loaded_source(
    root: Path,
    definition: dict[str, Any],
    current: ops.LoadedCatalogSource,
    ranking_file: Path,
    snapshot_date: date,
) -> ops.LoadedCatalogSource:
    rows = ops.load_csv(ranking_file)
    ranking_source = ops.source_file(
        f"{definition['source_id']}_historical_{snapshot_date.isoformat()}",
        ranking_file,
        root,
        snapshot_date.isoformat(),
    )
    return ops.LoadedCatalogSource(
        definition=definition,
        pointer_source=current.pointer_source,
        ranking_source=ranking_source,
        rows=rows,
        index=ops.build_source_index(rows, definition["join"]["strategies"]),
    )


def _build_source_history(
    root: Path,
    definition: dict[str, Any],
    windows: list[int],
    evaluation_date: date,
) -> SourceHistory:
    current = ops.resolve_catalog_source(root, definition)
    pointer = load_json(current.pointer_source.path)
    current_date = _snapshot_date(pointer, current.ranking_source.path)
    if current_date is None:
        raise FreeAgentMovementMaterializationError(
            f"Could not determine current snapshot date for {definition['source_id']}"
        )

    current_dir = current.ranking_source.path.parent
    snapshots_root = current_dir.parent
    dated_dirs: list[tuple[date, Path]] = []
    if snapshots_root.is_dir():
        for child in snapshots_root.iterdir():
            if not child.is_dir():
                continue
            parsed = _extract_date(child.name)
            if parsed and (child / current.ranking_source.path.name).is_file():
                dated_dirs.append((parsed, child))
    dated_dirs.sort(key=lambda item: item[0])

    baselines: dict[int, ops.LoadedCatalogSource | None] = {}
    baseline_dates: dict[int, str | None] = {}
    for window in windows:
        cutoff = evaluation_date - timedelta(days=window)
        candidates = [item for item in dated_dirs if item[0] <= cutoff]
        if not candidates:
            baselines[window] = None
            baseline_dates[window] = None
            continue
        selected_date, selected_dir = candidates[-1]
        ranking_file = selected_dir / current.ranking_source.path.name
        baselines[window] = _historical_loaded_source(root, definition, current, ranking_file, selected_date)
        baseline_dates[window] = selected_date.isoformat()

    return SourceHistory(
        definition=definition,
        current=current,
        current_snapshot_date=current_date,
        baselines=baselines,
        baseline_dates=baseline_dates,
    )


def _synthetic_player(player: dict[str, Any]) -> dict[str, Any]:
    app_data = player.get("app_data") if isinstance(player.get("app_data"), dict) else {}
    return {
        "ID": str(player.get("player_id") or ""),
        "Name": player.get("name"),
        "Position": player.get("position"),
        "TeamAbbr": player.get("nfl_team"),
        "ESPNID": app_data.get("espn_id"),
    }


def _eval(player: dict[str, Any], source: ops.LoadedCatalogSource) -> dict[str, Any]:
    result, _ = ops.evaluate_source_for_player(_synthetic_player(player), source)
    return result


def _numeric_delta(current: Any, baseline: Any) -> float | None:
    cur = ops.optional_number(current)
    old = ops.optional_number(baseline)
    if cur is None or old is None:
        return None
    return round(float(cur) - float(old), 4)


def _standardized_delta(target: str, delta: float | None) -> float | None:
    if delta is None:
        return None
    return round(-delta if target in LOWER_IS_BETTER_TARGETS else delta, 4)


def _parse_position_rank(value: Any) -> int | None:
    number = ops.optional_number(value)
    if number is not None:
        return int(number)
    text = ops.optional_text(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    return int(digits) if digits else None


def _condition_value(condition: Any, signal: str, operator: str) -> Any:
    if not isinstance(condition, dict):
        return None
    if condition.get("signal") == signal and condition.get("operator") == operator:
        return condition.get("value")
    for key in ("all", "any"):
        for child in condition.get(key) or []:
            found = _condition_value(child, signal, operator)
            if found is not None:
                return found
    return None


def _criterion(profile: dict[str, Any], criterion_id: str) -> dict[str, Any]:
    for criterion in profile.get("criteria") or []:
        if criterion.get("id") == criterion_id:
            return criterion
    raise FreeAgentMovementMaterializationError(
        f"Profile {profile.get('id')} is missing required criterion {criterion_id}"
    )


def _load_thresholds(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    refs = config["materiality_profiles"]
    adp = load_json(root / refs["redraft_adp"])
    market = load_json(root / refs["market"])
    projections = load_json(root / refs["projections"])
    kicker = load_json(root / refs["kicker"])

    adp_medium = _criterion(adp, "primary-percentile-movement")
    adp_large = _criterion(adp, "large-primary-percentile-movement")
    projection_medium = _criterion(projections, "material-consensus-movement")
    projection_large = _criterion(projections, "large-consensus-movement")
    market_overall = _criterion(market, "overall-rank-movement")
    market_position = _criterion(market, "position-rank-movement")
    kicker_adp = _criterion(kicker, "material-ffc-adp-movement")
    kicker_projection = _criterion(kicker, "material-projection-consensus-movement")

    return {
        "adp": {
            "default_medium_percentile_points": _condition_value(
                adp_medium.get("condition"), "adp.primary_percentile", "absolute_delta_gte"
            ),
            "default_large_percentile_points": _condition_value(
                adp_large.get("condition"), "adp.primary_percentile", "absolute_delta_gte"
            ),
            "default_min_times_drafted": _condition_value(
                adp_medium.get("condition"), "adp.primary_times_drafted", "gte"
            ),
            "kicker_medium_percentile_points": _condition_value(
                kicker_adp.get("condition"), "kicker.ffc_percentile", "absolute_delta_gte"
            ),
            "kicker_min_times_drafted": _condition_value(
                kicker_adp.get("condition"), "kicker.ffc_times_drafted", "gte"
            ),
        },
        "market": {
            "overall_rank_places": _condition_value(
                market_overall.get("condition"), "market.dynasty_overall_rank", "absolute_delta_gte"
            ),
            "position_rank_places": _condition_value(
                market_position.get("condition"), "market.position_rank", "absolute_delta_gte"
            ),
        },
        "projections": {
            "default_medium_percentile_points": _condition_value(
                projection_medium.get("condition"), "projection.consensus_percentile", "absolute_delta_gte"
            ),
            "default_large_percentile_points": _condition_value(
                projection_large.get("condition"), "projection.consensus_percentile", "absolute_delta_gte"
            ),
            "default_min_provider_count": _condition_value(
                projection_medium.get("condition"), "projection.provider_count", "gte"
            ),
            "kicker_medium_percentile_points": _condition_value(
                kicker_projection.get("condition"), "kicker.projection_consensus_percentile", "absolute_delta_gte"
            ),
            "kicker_min_provider_count": _condition_value(
                kicker_projection.get("condition"), "kicker.projection_provider_count", "gte"
            ),
        },
    }


def _primary_adp_source(histories: dict[str, SourceHistory], position: str) -> SourceHistory | None:
    for history in histories.values():
        definition = history.definition
        if definition["output"]["section"] != "redraft_adp":
            continue
        primary = {str(v).upper() for v in (definition.get("roles") or {}).get("primary_for_positions", [])}
        if position in primary:
            return history
    return None


def _market_histories(histories: dict[str, SourceHistory], position: str) -> list[SourceHistory]:
    selected = []
    for history in histories.values():
        definition = history.definition
        if definition["output"]["section"] != "market":
            continue
        if position not in {str(v).upper() for v in definition["applicability"]["positions"]}:
            continue
        selected.append(history)
    return selected


def _projection_histories(histories: dict[str, SourceHistory], position: str) -> list[SourceHistory]:
    selected = []
    for history in histories.values():
        definition = history.definition
        if definition["output"]["section"] != "projections":
            continue
        if position not in {str(v).upper() for v in definition["applicability"]["positions"]}:
            continue
        selected.append(history)
    return selected


def _market_percentile(results: list[dict[str, Any]]) -> float | None:
    values = [
        float(value)
        for result in results
        for value in [(result.get("signals") or {}).get("percentile")]
        if result.get("listed") and ops.optional_number(value) is not None
    ]
    return round(sum(values) / len(values), 2) if values else None


def _projection_summary(results: list[dict[str, Any]]) -> tuple[float | None, int, float | None]:
    values = [
        float(value)
        for result in results
        for value in [(result.get("signals") or {}).get("percentile")]
        if result.get("listed") and ops.optional_number(value) is not None
    ]
    if not values:
        return None, 0, None
    consensus = round(sum(values) / len(values), 2)
    spread = round(max(values) - min(values), 2) if len(values) >= 2 else None
    return consensus, len(values), spread


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = index - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def _player_family_percentiles(player: dict[str, Any]) -> dict[str, float | None]:
    market = player.get("market") if isinstance(player.get("market"), dict) else {}
    market_values = []
    for provider in market.values():
        if not isinstance(provider, dict) or not provider.get("listed"):
            continue
        value = ops.optional_number(provider.get("percentile"))
        if value is not None:
            market_values.append(float(value))
    dynasty = round(float(median(market_values)), 2) if market_values else None

    adp = player.get("redraft_adp") if isinstance(player.get("redraft_adp"), dict) else {}
    primary = adp.get("primary") if isinstance(adp.get("primary"), dict) else {}
    redraft_value = ops.optional_number(primary.get("percentile")) if primary.get("listed") else None

    projections = player.get("projections") if isinstance(player.get("projections"), dict) else {}
    summary = projections.get("summary") if isinstance(projections.get("summary"), dict) else {}
    projection_value = ops.optional_number(summary.get("consensus_percentile"))

    return {
        "dynasty_market": float(dynasty) if dynasty is not None else None,
        "redraft_adp": float(redraft_value) if redraft_value is not None else None,
        "season_projection": float(projection_value) if projection_value is not None else None,
    }


def _replacement_boundaries(players: list[dict[str, Any]], quantile: float) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, list[float]]] = {
        position: {"dynasty_market": [], "redraft_adp": [], "season_projection": []}
        for position in sorted(POSITIONS)
    }
    counts: Counter[str] = Counter()
    for player in players:
        if not isinstance(player, dict):
            continue
        ownership = player.get("ownership") if isinstance(player.get("ownership"), dict) else {}
        if ownership.get("status") not in {"mighty_giants", "opponent_rostered"}:
            continue
        position = str(player.get("position") or "").upper()
        if position not in POSITIONS:
            continue
        counts[position] += 1
        for family, value in _player_family_percentiles(player).items():
            if value is not None:
                buckets[position][family].append(value)

    result: dict[str, dict[str, Any]] = {}
    for position, families in buckets.items():
        result[position] = {
            "league_owned_player_count": counts[position],
            "families": {
                family: {
                    "owned_player_count": len(values),
                    "boundary_percentile": _quantile(values, quantile),
                    "owned_floor_percentile": round(min(values), 2) if values else None,
                }
                for family, values in families.items()
            },
        }
    return result


def _replacement_relevance(
    player: dict[str, Any],
    boundaries: dict[str, dict[str, Any]],
    near_distance: float,
) -> dict[str, Any]:
    position = str(player.get("position") or "").upper()
    current = _player_family_percentiles(player)
    position_boundaries = (boundaries.get(position) or {}).get("families") or {}
    distances: dict[str, float | None] = {}
    comparable: list[float] = []
    for family, value in current.items():
        boundary = ops.optional_number((position_boundaries.get(family) or {}).get("boundary_percentile"))
        if value is None or boundary is None:
            distances[family] = None
            continue
        distance = round(float(value) - float(boundary), 2)
        distances[family] = distance
        comparable.append(distance)
    if not comparable:
        classification = "unknown"
    elif max(comparable) >= 0:
        classification = "at_or_above_rostered_boundary"
    elif max(comparable) >= -near_distance:
        classification = "near_rostered_boundary"
    else:
        classification = "below_rostered_boundary"
    return {
        "classification": classification,
        "family_percentiles": current,
        "distance_to_owned_boundary": distances,
        "near_families": [family for family, distance in distances.items() if distance is not None and distance >= -near_distance],
    }


def _adp_movement(
    player: dict[str, Any],
    history: SourceHistory | None,
    windows: list[int],
    thresholds: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[int, float | None]]:
    if history is None:
        return {"status": "not_applicable", "windows": {}}, [], [], {window: None for window in windows}
    current = _eval(player, history.current)
    current_signals = current.get("signals") or {}
    current_pct = ops.optional_number(current_signals.get("percentile"))
    current_adp = ops.optional_number(current_signals.get("adp"))
    times_drafted = ops.optional_number(current_signals.get("times_drafted"))
    position = str(player.get("position") or "").upper()
    medium_threshold = thresholds["kicker_medium_percentile_points"] if position == "K" else thresholds["default_medium_percentile_points"]
    large_threshold = None if position == "K" else thresholds["default_large_percentile_points"]
    min_drafts = thresholds["kicker_min_times_drafted"] if position == "K" else thresholds["default_min_times_drafted"]
    crossed: list[dict[str, Any]] = []
    coverage_changes: list[dict[str, Any]] = []
    family_deltas: dict[int, float | None] = {}
    window_data: dict[str, Any] = {}
    for window in windows:
        baseline_source = history.baselines.get(window)
        baseline = _eval(player, baseline_source) if baseline_source is not None else None
        baseline_signals = (baseline or {}).get("signals") or {}
        baseline_pct = ops.optional_number(baseline_signals.get("percentile"))
        delta = _numeric_delta(current_pct, baseline_pct)
        family_deltas[window] = delta
        listed_change = None if baseline is None else bool(current.get("listed")) != bool(baseline.get("listed"))
        entry = bool(baseline is not None and current.get("listed") and not baseline.get("listed"))
        if entry:
            coverage_changes.append({"family": "redraft_adp", "kind": "entered_source", "window_days": window, "source_id": history.definition["source_id"]})
        sample_ok = times_drafted is not None and min_drafts is not None and float(times_drafted) >= float(min_drafts)
        if delta is not None and medium_threshold is not None and abs(delta) >= float(medium_threshold) and sample_ok:
            severity = "high" if large_threshold is not None and abs(delta) >= float(large_threshold) else "medium"
            crossed.append({
                "family": "redraft_adp",
                "kind": "percentile_movement",
                "severity": severity,
                "window_days": window,
                "delta": delta,
                "threshold": large_threshold if severity == "high" else medium_threshold,
                "source_id": history.definition["source_id"],
            })
        window_data[str(window)] = {
            "baseline_snapshot_date": history.baseline_dates.get(window),
            "baseline_listed": None if baseline is None else bool(baseline.get("listed")),
            "baseline_percentile": baseline_pct,
            "delta_percentile": delta,
            "baseline_adp": ops.optional_number(baseline_signals.get("adp")),
            "delta_adp": _numeric_delta(current_adp, baseline_signals.get("adp")),
            "listing_changed": listed_change,
        }
    return {
        "source_id": history.definition["source_id"],
        "current_snapshot_date": history.current_snapshot_date.isoformat(),
        "current_listed": bool(current.get("listed")),
        "current_percentile": current_pct,
        "current_adp": current_adp,
        "current_times_drafted": times_drafted,
        "windows": window_data,
    }, crossed, coverage_changes, family_deltas


def _market_movement(
    player: dict[str, Any],
    histories: list[SourceHistory],
    windows: list[int],
    thresholds: dict[str, Any],
    market_value_materiality: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[int, float | None]]:
    providers: dict[str, Any] = {}
    crossed: list[dict[str, Any]] = []
    coverage_changes: list[dict[str, Any]] = []
    current_results = [_eval(player, history.current) for history in histories]
    current_family_pct = _market_percentile(current_results)
    family_deltas: dict[int, float | None] = {}

    for history, current in zip(histories, current_results):
        source_id = history.definition["source_id"]
        current_signals = current.get("signals") or {}
        provider_windows: dict[str, Any] = {}
        for window in windows:
            baseline_source = history.baselines.get(window)
            baseline = _eval(player, baseline_source) if baseline_source is not None else None
            baseline_signals = (baseline or {}).get("signals") or {}
            overall_delta = _numeric_delta(current_signals.get("overall_rank"), baseline_signals.get("overall_rank"))
            current_pos_rank = _parse_position_rank(current_signals.get("position_rank"))
            baseline_pos_rank = _parse_position_rank(baseline_signals.get("position_rank"))
            position_delta = _numeric_delta(current_pos_rank, baseline_pos_rank)
            percentile_delta = _numeric_delta(current_signals.get("percentile"), baseline_signals.get("percentile"))
            value_delta = _numeric_delta(current_signals.get("value"), baseline_signals.get("value"))
            old_value = ops.optional_number(baseline_signals.get("value"))
            value_pct_delta = None
            if value_delta is not None and old_value not in (None, 0):
                value_pct_delta = round((value_delta / float(old_value)) * 100, 2)
            tier_changed = bool(
                baseline is not None
                and current.get("listed")
                and baseline.get("listed")
                and ops.optional_text(current_signals.get("tier")) != ops.optional_text(baseline_signals.get("tier"))
            )
            entry = bool(baseline is not None and current.get("listed") and not baseline.get("listed"))
            if entry:
                coverage_changes.append({"family": "dynasty_market", "kind": "entered_source", "window_days": window, "source_id": source_id})
            if history.definition.get("source_kind") == "expert_consensus":
                if overall_delta is not None and thresholds.get("overall_rank_places") is not None and abs(overall_delta) >= float(thresholds["overall_rank_places"]):
                    crossed.append({"family": "dynasty_market", "kind": "overall_rank_movement", "severity": "medium", "window_days": window, "delta": overall_delta, "threshold": thresholds["overall_rank_places"], "source_id": source_id})
                if position_delta is not None and thresholds.get("position_rank_places") is not None and abs(position_delta) >= float(thresholds["position_rank_places"]):
                    crossed.append({"family": "dynasty_market", "kind": "position_rank_movement", "severity": "medium", "window_days": window, "delta": position_delta, "threshold": thresholds["position_rank_places"], "source_id": source_id})
            if market_value_materiality is not None:
                crossed.extend(
                    market_calibration.materiality_crossings(
                        config=market_value_materiality,
                        source_id=source_id,
                        window_days=window,
                        percentile_delta=percentile_delta,
                        value_delta=value_delta,
                        value_percent_change=value_pct_delta,
                        tier_changed=tier_changed,
                        tier_from=baseline_signals.get("tier"),
                        tier_to=current_signals.get("tier"),
                    )
                )
            elif history.definition.get("source_kind") == "expert_consensus" and tier_changed:
                crossed.append({"family": "dynasty_market", "kind": "tier_change", "severity": "high", "window_days": window, "source_id": source_id, "from": baseline_signals.get("tier"), "to": current_signals.get("tier")})
            provider_windows[str(window)] = {
                "baseline_snapshot_date": history.baseline_dates.get(window),
                "baseline_listed": None if baseline is None else bool(baseline.get("listed")),
                "delta_overall_rank": overall_delta,
                "standardized_overall_rank_delta": _standardized_delta("overall_rank", overall_delta),
                "delta_position_rank": position_delta,
                "standardized_position_rank_delta": _standardized_delta("position_rank", position_delta),
                "delta_percentile": percentile_delta,
                "delta_value": value_delta,
                "value_percent_change": value_pct_delta,
                "tier_changed": tier_changed,
            }
        providers[source_id] = {
            "source_kind": history.definition.get("source_kind"),
            "provider": history.definition.get("provider"),
            "current_snapshot_date": history.current_snapshot_date.isoformat(),
            "current_listed": bool(current.get("listed")),
            "current_overall_rank": ops.optional_number(current_signals.get("overall_rank")),
            "current_position_rank": current_signals.get("position_rank"),
            "current_percentile": ops.optional_number(current_signals.get("percentile")),
            "current_tier": current_signals.get("tier"),
            "current_value": ops.optional_number(current_signals.get("value")),
            "windows": provider_windows,
        }

    for window in windows:
        baseline_results = [
            _eval(player, history.baselines[window])
            for history in histories
            if history.baselines.get(window) is not None
        ]
        family_deltas[window] = _numeric_delta(current_family_pct, _market_percentile(baseline_results))

    return {"current_consensus_percentile": current_family_pct, "providers": providers}, crossed, coverage_changes, family_deltas


def _projection_movement(
    player: dict[str, Any],
    histories: list[SourceHistory],
    windows: list[int],
    thresholds: dict[str, Any],
    scoring: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[int, float | None]]:
    position = str(player.get("position") or "").upper()
    current_results = [_eval(player, history.current) for history in histories]
    current_consensus, current_count, current_spread = _projection_summary(current_results)
    medium_threshold = thresholds["kicker_medium_percentile_points"] if position == "K" else thresholds["default_medium_percentile_points"]
    large_threshold = None if position == "K" else thresholds["default_large_percentile_points"]
    min_providers = thresholds["kicker_min_provider_count"] if position == "K" else thresholds["default_min_provider_count"]
    crossed: list[dict[str, Any]] = []
    coverage_changes: list[dict[str, Any]] = []
    family_deltas: dict[int, float | None] = {}
    window_data: dict[str, Any] = {}
    providers: dict[str, Any] = {}

    for history, current in zip(histories, current_results):
        signals = current.get("signals") or {}
        provider_key = str(history.definition["output"]["key"])
        provider_record = providers.setdefault(provider_key, {"sources": []})
        current_core = projection_ext.league_scoring_view(position, current, scoring)
        source_windows: dict[str, Any] = {}
        for window in windows:
            baseline_source = history.baselines.get(window)
            baseline = _eval(player, baseline_source) if baseline_source is not None else None
            baseline_core = projection_ext.league_scoring_view(position, baseline, scoring) if baseline is not None else None
            source_windows[str(window)] = {
                "baseline_snapshot_date": history.baseline_dates.get(window),
                "baseline_listed": None if baseline is None else bool(baseline.get("listed")),
                "delta_percentile": _numeric_delta(signals.get("percentile"), ((baseline or {}).get("signals") or {}).get("percentile")),
                "baseline_core_points": None if baseline_core is None else baseline_core.get("core_points"),
                "delta_core_points": None if baseline_core is None else _numeric_delta(current_core.get("core_points"), baseline_core.get("core_points")),
            }
            if baseline is not None and current.get("listed") and not baseline.get("listed"):
                coverage_changes.append({"family": "season_projection", "kind": "entered_source", "window_days": window, "source_id": history.definition["source_id"]})
        provider_record["sources"].append({
            "source_id": history.definition["source_id"],
            "provider": history.definition.get("provider"),
            "current_snapshot_date": history.current_snapshot_date.isoformat(),
            "current_listed": bool(current.get("listed")),
            "current_percentile": ops.optional_number(signals.get("percentile")),
            "current_core_points": current_core.get("core_points"),
            "windows": source_windows,
        })

    for window in windows:
        baseline_results = [
            _eval(player, history.baselines[window])
            for history in histories
            if history.baselines.get(window) is not None
        ]
        baseline_consensus, baseline_count, baseline_spread = _projection_summary(baseline_results)
        delta = _numeric_delta(current_consensus, baseline_consensus)
        family_deltas[window] = delta
        enough_providers = min_providers is not None and current_count >= int(min_providers)
        if delta is not None and medium_threshold is not None and abs(delta) >= float(medium_threshold) and enough_providers:
            severity = "high" if large_threshold is not None and abs(delta) >= float(large_threshold) else "medium"
            crossed.append({"family": "season_projection", "kind": "consensus_percentile_movement", "severity": severity, "window_days": window, "delta": delta, "threshold": large_threshold if severity == "high" else medium_threshold, "provider_count": current_count})
        if baseline_count < current_count and current_count >= 2:
            coverage_changes.append({"family": "season_projection", "kind": "provider_coverage_increase", "window_days": window, "from": baseline_count, "to": current_count})
        window_data[str(window)] = {
            "baseline_consensus_percentile": baseline_consensus,
            "delta_consensus_percentile": delta,
            "baseline_provider_count": baseline_count,
            "baseline_percentile_spread": baseline_spread,
        }

    return {
        "current_consensus_percentile": current_consensus,
        "current_provider_count": current_count,
        "current_percentile_spread": current_spread,
        "providers": providers,
        "windows": window_data,
    }, crossed, coverage_changes, family_deltas


def _cross_signal_patterns(
    windows: list[int],
    family_deltas: dict[str, dict[int, float | None]],
    material_families: set[str],
    min_delta: float,
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for window in windows:
        directions: dict[str, str] = {}
        deltas: dict[str, float] = {}
        for family, values in family_deltas.items():
            delta = values.get(window)
            if delta is None or abs(delta) < min_delta:
                continue
            directions[family] = "up" if delta > 0 else "down"
            deltas[family] = delta
        if len(directions) < 2:
            continue
        ups = sorted(family for family, direction in directions.items() if direction == "up")
        downs = sorted(family for family, direction in directions.items() if direction == "down")
        if len(ups) >= 2 and material_families.intersection(ups):
            patterns.append({"kind": "confirmation_up", "window_days": window, "families": ups, "deltas": {family: deltas[family] for family in ups}})
        if len(downs) >= 2 and material_families.intersection(downs):
            patterns.append({"kind": "confirmation_down", "window_days": window, "families": downs, "deltas": {family: deltas[family] for family in downs}})
        if ups and downs and material_families.intersection(set(ups + downs)):
            patterns.append({"kind": "divergence", "window_days": window, "up_families": ups, "down_families": downs, "deltas": deltas})
    return patterns


def _activity_context(player: dict[str, Any]) -> dict[str, Any]:
    activity = player.get("activity") if isinstance(player.get("activity"), dict) else {}
    add = activity.get("add") if isinstance(activity.get("add"), dict) else {}
    drop = activity.get("drop") if isinstance(activity.get("drop"), dict) else {}
    return {
        "listed": bool(activity.get("listed")),
        "add_rank": ops.optional_number(add.get("rank")),
        "add_count": ops.optional_number(add.get("count")),
        "drop_rank": ops.optional_number(drop.get("rank")),
        "drop_count": ops.optional_number(drop.get("count")),
        "policy": "activity is corroboration/research context, not a discovery prerequisite or player-quality score",
    }


def _structural_movement(player: dict[str, Any], previous: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if previous is None:
        return {"comparison_status": "no_previous_player_baseline", "changes": []}, []
    changes: list[dict[str, Any]] = []

    def add_change(kind: str, family: str, old: Any, new: Any, severity: str = "medium") -> None:
        if old != new:
            changes.append({"family": family, "kind": kind, "severity": severity, "window_days": 1, "from": old, "to": new})

    add_change("nfl_team_change", "team_transaction", previous.get("nfl_team"), player.get("nfl_team"), "high")

    injury_now = player.get("injury") if isinstance(player.get("injury"), dict) else {}
    injury_old = previous.get("injury") if isinstance(previous.get("injury"), dict) else {}
    add_change("injury_flag_change", "injury_availability", bool(injury_old.get("is_injured")), bool(injury_now.get("is_injured")), "high" if bool(injury_now.get("is_injured")) else "medium")
    add_change("injury_designation_change", "injury_availability", injury_old.get("designation"), injury_now.get("designation"), "medium")
    add_change("return_timeline_change", "injury_availability", injury_old.get("return_date"), injury_now.get("return_date"), "medium")

    role_now = player.get("role") if isinstance(player.get("role"), dict) else {}
    role_old = previous.get("role") if isinstance(previous.get("role"), dict) else {}
    add_change("depth_chart_order_change", "role_opportunity", role_old.get("sleeper_depth_chart_order"), role_now.get("sleeper_depth_chart_order"), "medium")
    add_change("depth_chart_position_change", "role_opportunity", role_old.get("sleeper_depth_chart_position"), role_now.get("sleeper_depth_chart_position"), "medium")

    activity_now = _activity_context(player)
    activity_old = _activity_context(previous)
    activity_changes: list[dict[str, Any]] = []
    for field in ("add_rank", "add_count", "drop_rank", "drop_count"):
        if activity_old.get(field) != activity_now.get(field):
            activity_changes.append({"field": field, "from": activity_old.get(field), "to": activity_now.get(field)})

    structural = {
        "comparison_status": "compared",
        "changes": changes,
        "activity_changes": activity_changes,
    }
    return structural, changes


def _priority(
    crossed: list[dict[str, Any]],
    cross_patterns: list[dict[str, Any]],
    coverage_changes: list[dict[str, Any]],
    replacement: dict[str, Any],
    activity: dict[str, Any],
    activity_top_n: int,
) -> tuple[str | None, list[str]]:
    material_families = {str(item["family"]) for item in crossed}
    has_high = any(item.get("severity") == "high" for item in crossed)
    replacement_class = replacement.get("classification")
    reasons: list[str] = []
    if crossed:
        reasons.append("material_movement_threshold")
    if cross_patterns:
        reasons.append("cross_signal_pattern")
    if coverage_changes and replacement_class in {"at_or_above_rostered_boundary", "near_rostered_boundary"}:
        reasons.append("relevant_source_coverage_change")
    add_rank = ops.optional_number(activity.get("add_rank"))
    drop_rank = ops.optional_number(activity.get("drop_rank"))
    activity_near = (
        replacement_class in {"at_or_above_rostered_boundary", "near_rostered_boundary"}
        and ((add_rank is not None and add_rank <= activity_top_n) or (drop_rank is not None and drop_rank <= activity_top_n))
    )
    if activity_near:
        reasons.append("activity_near_replacement_boundary")

    if len(material_families) >= 2 or any(item.get("kind") == "confirmation_up" for item in cross_patterns):
        return "high", reasons
    if has_high and replacement_class != "below_rostered_boundary":
        return "high", reasons
    if crossed:
        return "medium", reasons
    if "relevant_source_coverage_change" in reasons or activity_near:
        return "medium", reasons
    return None, reasons


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version", "dataset_id", "generated_at", "input_fingerprint", "source",
        "comparison_windows_days", "materiality_thresholds", "replacement_context", "population",
        "discoveries", "quality",
    }
    missing = sorted(required - set(data))
    if missing:
        raise FreeAgentMovementMaterializationError(f"Output missing required keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION or data["dataset_id"] != DATASET_ID:
        raise FreeAgentMovementMaterializationError("Unexpected movement output identity")
    ids = [str(item.get("player_id")) for item in data["discoveries"]]
    if len(ids) != len(set(ids)):
        raise FreeAgentMovementMaterializationError("Movement output contains duplicate player IDs")
    if data["population"]["discovery_count"] != len(data["discoveries"]):
        raise FreeAgentMovementMaterializationError("Discovery count does not match discoveries array")
    if any(item.get("position") not in POSITIONS for item in data["discoveries"]):
        raise FreeAgentMovementMaterializationError("Movement output contains unsupported position")


def build(root: Path, config_path: Path, previous_free_agent_path: Path | None = None) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise FreeAgentMovementMaterializationError("Movement materialization config must be an object")
    validate_config(config)
    source_cfg = config["source"]
    free_agent_path = root / source_cfg["free_agent_signals"]
    player_path = root / source_cfg["player_signals"]
    league_path = root / source_cfg["league"]
    free_agents = load_json(free_agent_path)
    players = load_json(player_path)
    league = load_json(league_path)
    validate_source_documents(free_agents, players)
    evaluation_date = _extract_date(free_agents.get("generated_at"))
    if evaluation_date is None:
        raise FreeAgentMovementMaterializationError(
            "free-agent-signals generated_at must provide the movement evaluation date"
        )
    previous_free_agents: dict[str, Any] | None = None
    previous_by_id: dict[str, dict[str, Any]] = {}
    if previous_free_agent_path is not None and previous_free_agent_path.is_file():
        loaded_previous = load_json(previous_free_agent_path)
        if isinstance(loaded_previous, dict) and loaded_previous.get("dataset_id") == FREE_AGENT_DATASET_ID:
            previous_free_agents = loaded_previous
            previous_by_id = {
                str(item.get("player_id")): item
                for item in loaded_previous.get("players") or []
                if isinstance(item, dict) and item.get("player_id") is not None
            }
    windows = sorted(config["comparison_windows_days"])
    thresholds = _load_thresholds(root, config)
    catalog, pending_sources = _load_merged_catalog(root, config)
    market_value_materiality = config.get("market_value_materiality")
    if market_value_materiality is not None:
        catalog_source_ids = {
            str(definition.get("source_id"))
            for definition in catalog["sources"]
            if definition.get("active")
        }
        missing_calibration_sources = sorted(
            market_calibration.configured_source_ids(market_value_materiality) - catalog_source_ids
        )
        if missing_calibration_sources:
            raise FreeAgentMovementMaterializationError(
                f"Configured market calibration sources are absent from the active catalog: {missing_calibration_sources}"
            )

    histories: dict[str, SourceHistory] = {}
    history_issues: list[dict[str, Any]] = []
    for definition in catalog["sources"]:
        if not definition.get("active"):
            continue
        try:
            histories[definition["source_id"]] = _build_source_history(
                root,
                definition,
                windows,
                evaluation_date,
            )
        except (ops.MaterializationError, FreeAgentMovementMaterializationError) as exc:
            raise FreeAgentMovementMaterializationError(
                f"Could not build history for active source {definition['source_id']}: {exc}"
            ) from exc

    for source_id, history in histories.items():
        for window in windows:
            if history.baselines.get(window) is None:
                history_issues.append({"severity": "info", "kind": "history_window_unavailable", "source": source_id, "window_days": window})
    for pending in pending_sources:
        history_issues.append({"severity": "info", "kind": "configured_source_not_materialized", **pending})

    replacement_cfg = config["replacement_relevance"]
    boundaries = _replacement_boundaries(players.get("players") or [], float(replacement_cfg["owned_boundary_quantile"]))
    scoring = league.get("ScoringType") if isinstance(league.get("ScoringType"), dict) else {}
    discoveries: list[dict[str, Any]] = []
    discovery_positions: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    material_family_counts: Counter[str] = Counter()

    free_agent_players = free_agents.get("players") if isinstance(free_agents.get("players"), list) else []
    for player in free_agent_players:
        if not isinstance(player, dict):
            continue
        position = str(player.get("position") or "").upper()
        if position not in POSITIONS:
            continue
        replacement = _replacement_relevance(player, boundaries, float(replacement_cfg["near_distance_percentile_points"]))
        adp, adp_crossed, adp_coverage, adp_deltas = _adp_movement(
            player, _primary_adp_source(histories, position), windows, thresholds["adp"]
        )
        market, market_crossed, market_coverage, market_deltas = _market_movement(
            player,
            _market_histories(histories, position),
            windows,
            thresholds["market"],
            market_value_materiality,
        )
        projections, projection_crossed, projection_coverage, projection_deltas = _projection_movement(
            player, _projection_histories(histories, position), windows, thresholds["projections"], scoring
        )
        structural, structural_crossed = _structural_movement(player, previous_by_id.get(str(player.get("player_id"))))
        crossed = adp_crossed + market_crossed + projection_crossed + structural_crossed
        coverage_changes = adp_coverage + market_coverage + projection_coverage
        material_families = {str(item["family"]) for item in crossed}
        cross_patterns = _cross_signal_patterns(
            windows,
            {
                "redraft_adp": adp_deltas,
                "dynasty_market": market_deltas,
                "season_projection": projection_deltas,
            },
            material_families,
            float(config["cross_signal"]["minimum_percentile_delta_points"]),
        )
        activity = _activity_context(player)
        priority, reasons = _priority(
            crossed,
            cross_patterns,
            coverage_changes,
            replacement,
            activity,
            int(config["activity"]["near_replacement_top_n"]),
        )
        if priority is None:
            continue

        for family in material_families:
            material_family_counts[family] += 1
        discovery_positions[position] += 1
        priority_counts[priority] += 1
        discoveries.append({
            "player_id": str(player.get("player_id")),
            "name": player.get("name"),
            "position": position,
            "nfl_team": player.get("nfl_team"),
            "ownership": player.get("ownership"),
            "replacement_relevance": replacement,
            "movement": {
                "redraft_adp": adp,
                "dynasty_market": market,
                "season_projection": projections,
                "cross_signal_patterns": cross_patterns,
                "structural_day_over_day": structural,
            },
            "activity": activity,
            "materiality": {
                "research_priority": priority,
                "material_families": sorted(material_families),
                "thresholds_crossed": crossed,
                "coverage_changes": coverage_changes,
                "reasons": reasons,
                "final_roster_recommendation": None,
            },
        })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    discoveries.sort(key=lambda item: (priority_order.get(item["materiality"]["research_priority"], 9), item["position"], str(item.get("name") or "").casefold(), item["player_id"]))

    source_records = {
        source_id: {
            "source_kind": history.definition.get("source_kind"),
            "provider": history.definition.get("provider"),
            "dataset_id": history.definition.get("dataset_id"),
            "current_snapshot_date": history.current_snapshot_date.isoformat(),
            "current_ranking_path": history.current.ranking_source.relative_path,
            "baseline_snapshot_dates": {str(window): history.baseline_dates.get(window) for window in windows},
            "baseline_ranking_paths": {
                str(window): history.baselines[window].ranking_source.relative_path if history.baselines.get(window) else None
                for window in windows
            },
        }
        for source_id, history in sorted(histories.items())
    }
    fingerprint_payload = {
        "config": config,
        "evaluation_date": evaluation_date.isoformat(),
        "free_agent_input_fingerprint": free_agents.get("input_fingerprint"),
        "player_input_fingerprint": players.get("input_fingerprint"),
        "previous_free_agent_input_fingerprint": (previous_free_agents or {}).get("input_fingerprint"),
        "source_records": source_records,
        "thresholds": thresholds,
        "replacement_boundaries": boundaries,
        "discoveries": [
            {
                "player_id": item["player_id"],
                "replacement_relevance": item["replacement_relevance"],
                "movement": item["movement"],
                "activity": item["activity"],
                "materiality": item["materiality"],
            }
            for item in discoveries
        ],
    }
    source_quality = free_agents.get("quality") or {}
    quality_status = "warning" if source_quality.get("status") == "warning" else "ok"
    history_status = "partial" if history_issues else "full"
    materiality_thresholds = dict(thresholds)
    if market_value_materiality is not None:
        materiality_thresholds["market_value_materiality"] = market_value_materiality
    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": free_agents.get("generated_at"),
        "input_fingerprint": ops.sha256_text(ops.canonical_json(fingerprint_payload)),
        "source": {
            "free_agent_signals": {"path": source_cfg["free_agent_signals"], "dataset_id": FREE_AGENT_DATASET_ID, "input_fingerprint": free_agents.get("input_fingerprint")},
            "player_signals": {"path": source_cfg["player_signals"], "dataset_id": PLAYER_DATASET_ID, "input_fingerprint": players.get("input_fingerprint")},
            "league": source_cfg["league"],
            "source_catalog": source_cfg["source_catalog"],
            "source_catalog_extensions": source_cfg.get("source_catalog_extensions") or [],
            "materiality_profiles": config["materiality_profiles"],
            "comparison_anchor_date": evaluation_date.isoformat(),
            "comparison_anchor_policy": "calendar windows are anchored to the evaluation date; each source uses the last available snapshot at or before the cutoff",
            "previous_free_agent_signals": {"status": "available" if previous_free_agents is not None else "not_available", "input_fingerprint": (previous_free_agents or {}).get("input_fingerprint")},
            "ranking_histories": source_records,
        },
        "comparison_windows_days": windows,
        "materiality_thresholds": materiality_thresholds,
        "replacement_context": {
            "method": "position-specific lower-boundary proxy from current league-owned normalized family percentiles",
            "owned_boundary_quantile": replacement_cfg["owned_boundary_quantile"],
            "near_distance_percentile_points": replacement_cfg["near_distance_percentile_points"],
            "boundaries": boundaries,
            "policy": "family percentiles remain separate; dynasty market, redraft ADP and season projections are not averaged into one player value",
        },
        "population": {
            "free_agent_count": len(free_agent_players),
            "positions": sorted(POSITIONS),
            "discovery_count": len(discoveries),
            "discovery_position_counts": dict(sorted(discovery_positions.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "material_family_counts": dict(sorted(material_family_counts.items())),
            "selection_rule": "all current fantasy free agents QB/RB/WR/TE/K are evaluated; only research-relevant movement discoveries are emitted",
        },
        "discoveries": discoveries,
        "quality": {
            "status": quality_status,
            "source_quality_status": source_quality.get("status"),
            "source_issue_count": int(source_quality.get("source_issue_count") or 0),
            "history_status": history_status,
            "previous_state_status": "available" if previous_free_agents is not None else "not_available",
            "history_issue_count": len(history_issues),
            "issues": history_issues,
        },
    }
    validate_output(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--config", type=Path, default=Path("fantasy-management/automation/free-agent-movement-materialization.json"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--previous-free-agent-signals", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    previous_path = args.previous_free_agent_signals
    if previous_path is not None and not previous_path.is_absolute():
        previous_path = root / previous_path
    result = build(root, config_path, previous_path)
    if args.check:
        print(
            f"Validated {result['population']['free_agent_count']} free agents; "
            f"discoveries={result['population']['discovery_count']}; "
            f"history={result['quality']['history_status']}."
        )
        return 0
    output_path = root / config["output"]["free_agent_movement_signals"]
    write_json(output_path, result)
    print(
        f"Wrote {output_path.relative_to(root)} with {result['population']['discovery_count']} "
        f"discoveries from {result['population']['free_agent_count']} free agents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
