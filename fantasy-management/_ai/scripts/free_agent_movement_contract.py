#!/usr/bin/env python3
"""Build deterministic materiality-contract and evidence fingerprints for movement state."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class MovementContractError(RuntimeError):
    """Raised when movement contract metadata cannot be built safely."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MovementContractError(f"Could not load JSON from {path}: {exc}") from exc


def _required_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MovementContractError(f"{field} must be an object")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MovementContractError(f"{field} must be a non-empty string")
    return value


def _file_fingerprint(root: Path, relative: str) -> str:
    value = load_json(root / relative)
    return sha256_json(value)


def annotate_movement(
    root: Path,
    movement: dict[str, Any],
    movement_config: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy of movement with deterministic contract/evidence metadata.

    The materiality contract intentionally contains only rule semantics. The evidence
    fingerprint intentionally contains only the current inputs/context used to evaluate
    those rules. Previous-free-agent state is excluded because structural changes are
    edge events and its rollover must not make an otherwise source-identical contract
    migration look like new evidence.
    """
    contract_cfg = _required_dict(movement_config.get("materiality_contract"), "materiality_contract")
    version = contract_cfg.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise MovementContractError("materiality_contract.version must be a positive integer")

    source_cfg = _required_dict(movement_config.get("source"), "source")
    movement_source = _required_dict(movement.get("source"), "movement.source")
    replacement = _required_dict(movement_config.get("replacement_relevance"), "replacement_relevance")

    contract_payload = {
        "version": version,
        "comparison_windows_days": movement.get("comparison_windows_days"),
        "materiality_thresholds": movement.get("materiality_thresholds"),
        "replacement_relevance": {
            "owned_boundary_quantile": replacement.get("owned_boundary_quantile"),
            "near_distance_percentile_points": replacement.get("near_distance_percentile_points"),
        },
        "cross_signal": movement_config.get("cross_signal"),
        "activity": movement_config.get("activity"),
    }

    catalog_paths = [
        _required_text(source_cfg.get("source_catalog"), "source.source_catalog"),
        *[
            _required_text(path, "source.source_catalog_extensions[]")
            for path in (source_cfg.get("source_catalog_extensions") or [])
        ],
    ]
    catalog_fingerprints = {
        path: _file_fingerprint(root, path)
        for path in catalog_paths
    }
    league_path = _required_text(source_cfg.get("league"), "source.league")

    free_agent_source = _required_dict(movement_source.get("free_agent_signals"), "movement.source.free_agent_signals")
    player_source = _required_dict(movement_source.get("player_signals"), "movement.source.player_signals")
    evidence_payload = {
        "evaluation_date": movement_source.get("comparison_anchor_date"),
        "free_agent_input_fingerprint": free_agent_source.get("input_fingerprint"),
        "player_input_fingerprint": player_source.get("input_fingerprint"),
        "ranking_histories": movement_source.get("ranking_histories"),
        "league_fingerprint": _file_fingerprint(root, league_path),
        "source_catalog_fingerprints": catalog_fingerprints,
        "quality_issues": (_required_dict(movement.get("quality"), "movement.quality")).get("issues"),
    }

    annotated = deepcopy(movement)
    annotated["materiality_contract"] = {
        "version": version,
        "fingerprint": sha256_json(contract_payload),
    }
    annotated["evidence"] = {
        "input_fingerprint": sha256_json(evidence_payload),
    }
    return annotated
