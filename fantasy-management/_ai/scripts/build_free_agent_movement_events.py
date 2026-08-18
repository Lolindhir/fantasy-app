#!/usr/bin/env python3
"""Build deduplicated monitoring events from free-agent movement discovery state.

The current movement dataset is a research-state view and may keep a player listed for
multiple days while a 7/14/30-day signal remains material. This layer compares that
state with the previous successful movement dataset and emits only new, materially
changed, structural, or resolved discovery events. The first run is a silent baseline.

When both movement states carry materiality-contract and evidence fingerprints, a pure
materiality-contract change with identical evidence is treated as a silent contract
migration. If contract and evidence change together, comparison fails open and normal
events are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import free_agent_movement_contract as movement_contract  # noqa: E402

SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "free-agent-movement-events"
SOURCE_DATASET_ID = "free-agent-movement-signals"
POSITIONS = {"QB", "RB", "WR", "TE", "K"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class MovementEventMaterializationError(RuntimeError):
    """Raised when movement event materialization cannot be completed safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MovementEventMaterializationError(f"Could not load JSON from {path}: {exc}") from exc


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise MovementEventMaterializationError("Unexpected movement-event config schema version")
    source_cfg = config.get("source") if isinstance(config.get("source"), dict) else {}
    source = source_cfg.get("movement_signals")
    materiality_config = source_cfg.get("movement_materiality_config")
    output = (config.get("output") or {}).get("movement_events")
    if not isinstance(source, str) or not source:
        raise MovementEventMaterializationError("movement-event config requires source.movement_signals")
    if materiality_config is not None and (not isinstance(materiality_config, str) or not materiality_config):
        raise MovementEventMaterializationError("source.movement_materiality_config must be a non-empty string when configured")
    if not isinstance(output, str) or not output:
        raise MovementEventMaterializationError("movement-event config requires output.movement_events")


def validate_movement(value: dict[str, Any]) -> None:
    if value.get("schema_version") != 1 or value.get("dataset_id") != SOURCE_DATASET_ID:
        raise MovementEventMaterializationError("Input is not a schema-version-1 movement dataset")
    quality = value.get("quality") if isinstance(value.get("quality"), dict) else {}
    if quality.get("status") not in {"ok", "warning"}:
        raise MovementEventMaterializationError("movement input quality must be ok or warning")
    discoveries = value.get("discoveries")
    if not isinstance(discoveries, list):
        raise MovementEventMaterializationError("movement input discoveries must be an array")


def _annotate_current(root: Path, config: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    source_cfg = config.get("source") if isinstance(config.get("source"), dict) else {}
    relative = source_cfg.get("movement_materiality_config")
    if not relative:
        return current
    movement_config = load_json(root / str(relative))
    if not isinstance(movement_config, dict):
        raise MovementEventMaterializationError("movement materiality config must be an object")
    try:
        return movement_contract.annotate_movement(root, current, movement_config)
    except movement_contract.MovementContractError as exc:
        raise MovementEventMaterializationError(str(exc)) from exc


def _metadata_fingerprints(value: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    contract = value.get("materiality_contract") if isinstance(value.get("materiality_contract"), dict) else {}
    evidence = value.get("evidence") if isinstance(value.get("evidence"), dict) else {}
    contract_fingerprint = contract.get("fingerprint")
    evidence_fingerprint = evidence.get("input_fingerprint")
    if not isinstance(contract_fingerprint, str) or len(contract_fingerprint) != 64:
        contract_fingerprint = None
    if not isinstance(evidence_fingerprint, str) or len(evidence_fingerprint) != 64:
        evidence_fingerprint = None
    return contract_fingerprint, evidence_fingerprint


def _direction(delta: Any, kind: str) -> str | None:
    if not isinstance(delta, (int, float)):
        return None
    if delta == 0:
        return "flat"
    lower_is_better = kind in {"overall_rank_movement", "position_rank_movement"}
    improving = delta < 0 if lower_is_better else delta > 0
    return "up" if improving else "down"


def _threshold_state(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    materiality = discovery.get("materiality") if isinstance(discovery.get("materiality"), dict) else {}
    normalized: set[tuple[str, str, str, str | None]] = set()
    for item in materiality.get("thresholds_crossed") or []:
        if not isinstance(item, dict):
            continue
        family = str(item.get("family") or "unknown")
        if family in {"injury_availability", "team_transaction", "role_opportunity"}:
            # Structural changes are edge events. Their disappearance on the next run
            # must not manufacture a second "resolved" movement event.
            continue
        kind = str(item.get("kind") or "unknown")
        severity = str(item.get("severity") or "medium")
        normalized.add((family, kind, severity, _direction(item.get("delta"), kind)))
    return [
        {"family": family, "kind": kind, "severity": severity, "direction": direction}
        for family, kind, severity, direction in sorted(normalized)
    ]


def _cross_signal_state(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    movement = discovery.get("movement") if isinstance(discovery.get("movement"), dict) else {}
    normalized: set[str] = set()
    records: dict[str, dict[str, Any]] = {}
    for item in movement.get("cross_signal_patterns") or []:
        if not isinstance(item, dict):
            continue
        record = {
            "kind": item.get("kind"),
            "families": sorted(str(value) for value in (item.get("families") or [])),
            "up_families": sorted(str(value) for value in (item.get("up_families") or [])),
            "down_families": sorted(str(value) for value in (item.get("down_families") or [])),
        }
        key = canonical_json(record)
        normalized.add(key)
        records[key] = record
    return [records[key] for key in sorted(normalized)]


def _coverage_state(discovery: dict[str, Any]) -> list[dict[str, str]]:
    materiality = discovery.get("materiality") if isinstance(discovery.get("materiality"), dict) else {}
    normalized: set[tuple[str, str]] = set()
    for item in materiality.get("coverage_changes") or []:
        if not isinstance(item, dict):
            continue
        normalized.add((str(item.get("family") or "unknown"), str(item.get("kind") or "unknown")))
    return [{"family": family, "kind": kind} for family, kind in sorted(normalized)]


def _structural_changes(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    movement = discovery.get("movement") if isinstance(discovery.get("movement"), dict) else {}
    structural = movement.get("structural_day_over_day") if isinstance(movement.get("structural_day_over_day"), dict) else {}
    result = []
    for item in structural.get("changes") or []:
        if not isinstance(item, dict):
            continue
        result.append({
            "family": item.get("family"),
            "kind": item.get("kind"),
            "severity": item.get("severity"),
            "from": item.get("from"),
            "to": item.get("to"),
        })
    return result


def material_state(discovery: dict[str, Any]) -> dict[str, Any]:
    materiality = discovery.get("materiality") if isinstance(discovery.get("materiality"), dict) else {}
    replacement = discovery.get("replacement_relevance") if isinstance(discovery.get("replacement_relevance"), dict) else {}
    non_structural_families = sorted(
        str(value)
        for value in (materiality.get("material_families") or [])
        if str(value) not in {"injury_availability", "team_transaction", "role_opportunity"}
    )
    return {
        "research_priority": materiality.get("research_priority"),
        "material_families": non_structural_families,
        "replacement_classification": replacement.get("classification"),
        "thresholds": _threshold_state(discovery),
        "coverage": _coverage_state(discovery),
        "cross_signal": _cross_signal_state(discovery),
    }


def _dimensions(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return sorted(key for key in current if current.get(key) != previous.get(key))


def _event_priority(event_type: str, current_priority: str | None, previous_priority: str | None, structural: list[dict[str, Any]]) -> str:
    if any(item.get("severity") == "high" for item in structural):
        return "high"
    if event_type in {"new", "changed", "structural_change"} and current_priority in PRIORITY_ORDER:
        return str(current_priority)
    if event_type == "resolved" and previous_priority == "high":
        return "medium"
    return "low"


def _event(
    event_type: str,
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    anchor = current or previous or {}
    current_state = material_state(current) if current is not None else None
    previous_state = material_state(previous) if previous is not None else None
    structural = _structural_changes(current) if current is not None else []
    if current_state is not None and previous_state is not None:
        changed_dimensions = _dimensions(previous_state, current_state)
    elif current_state is not None:
        changed_dimensions = ["new_discovery"]
    else:
        changed_dimensions = ["resolved_discovery"]
    if structural:
        changed_dimensions = sorted(set(changed_dimensions + ["structural_change"]))

    current_materiality = (current or {}).get("materiality") if isinstance((current or {}).get("materiality"), dict) else {}
    previous_materiality = (previous or {}).get("materiality") if isinstance((previous or {}).get("materiality"), dict) else {}
    current_replacement = (current or {}).get("replacement_relevance") if isinstance((current or {}).get("replacement_relevance"), dict) else {}
    previous_replacement = (previous or {}).get("replacement_relevance") if isinstance((previous or {}).get("replacement_relevance"), dict) else {}
    current_priority = current_materiality.get("research_priority")
    previous_priority = previous_materiality.get("research_priority")

    return {
        "player_id": str(anchor.get("player_id")),
        "name": anchor.get("name"),
        "position": anchor.get("position"),
        "event_type": event_type,
        "event_priority": _event_priority(event_type, current_priority, previous_priority, structural),
        "current_research_priority": current_priority,
        "previous_research_priority": previous_priority,
        "current_state_hash": sha256_json(current_state) if current_state is not None else None,
        "previous_state_hash": sha256_json(previous_state) if previous_state is not None else None,
        "changed_dimensions": changed_dimensions,
        "current_material_families": sorted(str(value) for value in (current_materiality.get("material_families") or [])),
        "previous_material_families": sorted(str(value) for value in (previous_materiality.get("material_families") or [])),
        "current_replacement_classification": current_replacement.get("classification"),
        "previous_replacement_classification": previous_replacement.get("classification"),
        "threshold_summary": _threshold_state(current) if current is not None else _threshold_state(previous or {}),
        "cross_signal_summary": _cross_signal_state(current) if current is not None else _cross_signal_state(previous or {}),
        "structural_changes": structural,
        "final_roster_recommendation": None,
    }


def _comparison_events(
    current_by_id: dict[str, dict[str, Any]],
    previous_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for player_id, current_item in current_by_id.items():
        previous_item = previous_by_id.get(player_id)
        structural = _structural_changes(current_item)
        if previous_item is None:
            events.append(_event("new", current_item, None))
            continue
        current_state = material_state(current_item)
        previous_state = material_state(previous_item)
        if current_state != previous_state:
            events.append(_event("changed", current_item, previous_item))
        elif structural:
            events.append(_event("structural_change", current_item, previous_item))

    for player_id, previous_item in previous_by_id.items():
        if player_id not in current_by_id:
            events.append(_event("resolved", None, previous_item))
    return events


def validate_output(value: dict[str, Any]) -> None:
    required = {"schema_version", "dataset_id", "generated_at", "input_fingerprint", "source", "population", "contract_migration", "events", "quality"}
    missing = sorted(required - set(value))
    if missing:
        raise MovementEventMaterializationError(f"Output missing required keys: {missing}")
    if value["schema_version"] != SCHEMA_VERSION or value["dataset_id"] != DATASET_ID:
        raise MovementEventMaterializationError("Unexpected movement-event output identity")
    events = value["events"]
    if value["population"]["event_count"] != len(events):
        raise MovementEventMaterializationError("event_count does not match events array")
    if any(event.get("position") not in POSITIONS for event in events):
        raise MovementEventMaterializationError("movement event contains unsupported position")


def build(root: Path, config_path: Path, previous_path: Path | None = None) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise MovementEventMaterializationError("movement-event config must be an object")
    validate_config(config)
    current_path = root / config["source"]["movement_signals"]
    current = load_json(current_path)
    if not isinstance(current, dict):
        raise MovementEventMaterializationError("movement input must be an object")
    validate_movement(current)
    current = _annotate_current(root, config, current)

    previous: dict[str, Any] | None = None
    if previous_path is not None and previous_path.is_file():
        candidate = load_json(previous_path)
        if isinstance(candidate, dict) and candidate.get("dataset_id") == SOURCE_DATASET_ID:
            validate_movement(candidate)
            previous = candidate

    current_by_id = {
        str(item.get("player_id")): item
        for item in current.get("discoveries") or []
        if isinstance(item, dict) and item.get("player_id") is not None
    }
    previous_by_id = {
        str(item.get("player_id")): item
        for item in (previous or {}).get("discoveries") or []
        if isinstance(item, dict) and item.get("player_id") is not None
    }

    candidate_events = _comparison_events(current_by_id, previous_by_id) if previous is not None else []
    baseline_mode = "initial_baseline" if previous is None else "comparison"
    events = candidate_events

    current_contract, current_evidence = _metadata_fingerprints(current)
    previous_contract, previous_evidence = _metadata_fingerprints(previous)
    contract_changed: bool | None = None
    evidence_changed: bool | None = None
    migration_status = "not_applicable" if previous is None else "metadata_unavailable"
    suppressed_event_count = 0
    suppressed_event_type_counts: dict[str, int] = {}

    if previous is not None and all((current_contract, current_evidence, previous_contract, previous_evidence)):
        contract_changed = current_contract != previous_contract
        evidence_changed = current_evidence != previous_evidence
        if not contract_changed:
            migration_status = "not_needed"
        elif not evidence_changed:
            migration_status = "silent_rebaseline"
            baseline_mode = "contract_migration"
            suppressed_event_count = len(candidate_events)
            suppressed_event_type_counts = dict(sorted(Counter(str(event["event_type"]) for event in candidate_events).items()))
            events = []
        else:
            migration_status = "fail_open_evidence_changed"
            baseline_mode = "contract_migration_with_evidence_change"

    events.sort(
        key=lambda event: (
            PRIORITY_ORDER.get(str(event.get("event_priority")), 9),
            str(event.get("position")),
            str(event.get("name") or "").casefold(),
            str(event.get("player_id")),
        )
    )
    type_counts = Counter(str(event["event_type"]) for event in events)
    priority_counts = Counter(str(event["event_priority"]) for event in events)
    movement_quality = current.get("quality") if isinstance(current.get("quality"), dict) else {}
    quality_status = "warning" if movement_quality.get("status") == "warning" else "ok"
    if migration_status == "fail_open_evidence_changed":
        quality_status = "warning"

    migration = {
        "status": migration_status,
        "current_materiality_contract_fingerprint": current_contract,
        "previous_materiality_contract_fingerprint": previous_contract,
        "current_evidence_fingerprint": current_evidence,
        "previous_evidence_fingerprint": previous_evidence,
        "contract_changed": contract_changed,
        "evidence_changed": evidence_changed,
        "comparison_event_count_before_suppression": len(candidate_events),
        "suppressed_event_count": suppressed_event_count,
        "suppressed_event_type_counts": suppressed_event_type_counts,
    }

    fingerprint_payload = {
        "config": config,
        "current_fingerprint": current.get("input_fingerprint"),
        "previous_fingerprint": (previous or {}).get("input_fingerprint"),
        "contract_migration": migration,
        "events": events,
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": current.get("generated_at"),
        "input_fingerprint": sha256_json(fingerprint_payload),
        "source": {
            "movement_signals": {
                "path": config["source"]["movement_signals"],
                "dataset_id": SOURCE_DATASET_ID,
                "input_fingerprint": current.get("input_fingerprint"),
            },
            "previous_movement_signals": {
                "status": "available" if previous is not None else "not_available",
                "input_fingerprint": (previous or {}).get("input_fingerprint"),
            },
            "comparison_policy": "stable material state ignores window churn; pure materiality-contract migrations with identical evidence are silently rebaselined; contract plus evidence changes fail open",
        },
        "population": {
            "positions": sorted(POSITIONS),
            "current_discovery_count": len(current_by_id),
            "previous_discovery_count": len(previous_by_id),
            "event_count": len(events),
            "event_type_counts": dict(sorted(type_counts.items())),
            "event_priority_counts": dict(sorted(priority_counts.items())),
            "baseline_mode": baseline_mode,
        },
        "contract_migration": migration,
        "events": events,
        "quality": {
            "status": quality_status,
            "movement_quality_status": movement_quality.get("status"),
            "previous_state_status": "available" if previous is not None else "not_available",
            "migration_status": migration_status,
        },
    }
    validate_output(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--config", type=Path, default=Path("fantasy-management/automation/free-agent-movement-event-materialization.json"))
    parser.add_argument("--previous-movement-signals", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    previous_path = args.previous_movement_signals
    if previous_path is not None and not previous_path.is_absolute():
        previous_path = root / previous_path
    config = load_json(config_path)
    validate_config(config)

    current_path = root / config["source"]["movement_signals"]
    current = load_json(current_path)
    if not isinstance(current, dict):
        raise MovementEventMaterializationError("movement input must be an object")
    validate_movement(current)
    annotated_current = _annotate_current(root, config, current)
    if annotated_current != current:
        write_json(current_path, annotated_current)

    result = build(root, config_path, previous_path)
    if args.check:
        print(
            f"Validated movement events: baseline={result['population']['baseline_mode']}; "
            f"migration={result['contract_migration']['status']}; "
            f"current={result['population']['current_discovery_count']}; events={result['population']['event_count']}."
        )
        return 0
    output_path = root / config["output"]["movement_events"]
    write_json(output_path, result)
    print(
        "Wrote {} with {} events from {} current discoveries; baseline={}; migration={}; types={}; priorities={}.".format(
            output_path.relative_to(root),
            result["population"]["event_count"],
            result["population"]["current_discovery_count"],
            result["population"]["baseline_mode"],
            result["contract_migration"]["status"],
            result["population"]["event_type_counts"],
            result["population"]["event_priority_counts"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
