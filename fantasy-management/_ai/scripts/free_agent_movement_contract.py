#!/usr/bin/env python3
"""Build deterministic materiality-contract and evidence fingerprints for movement state."""
from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import canonical_league_ownership as canonical_ownership  # noqa: E402


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


def _canonical_scoring_evidence(
    root: Path,
    movement_source: dict[str, Any],
    movement_config: dict[str, Any],
) -> dict[str, Any]:
    canonical_cfg = _required_dict(movement_config.get("canonical_league"), "canonical_league")
    canonical_league_id = _required_text(
        canonical_cfg.get("canonical_league_id"),
        "canonical_league.canonical_league_id",
    )
    try:
        current_season = canonical_ownership.resolve_current_canonical_season(
            root,
            canonical_league_id=canonical_league_id,
        )
    except canonical_ownership.CanonicalOwnershipError as exc:
        raise MovementContractError(str(exc)) from exc

    source = _required_dict(
        movement_source.get("canonical_league_scoring"),
        "movement.source.canonical_league_scoring",
    )
    if source.get("canonical_league_id") != canonical_league_id:
        raise MovementContractError("Canonical league scoring evidence identity mismatch")
    try:
        source_season = int(source.get("season"))
    except (TypeError, ValueError) as exc:
        raise MovementContractError("Canonical league scoring evidence has invalid season") from exc
    if source_season != current_season:
        raise MovementContractError(
            f"Canonical league scoring evidence season mismatch: expected {current_season}, found {source.get('season')!r}"
        )

    relative_path = _required_text(source.get("path"), "movement.source.canonical_league_scoring.path")
    league = _required_dict(load_json(root / relative_path), "Canonical league scoring source")
    if league.get("CanonicalLeagueID") != canonical_league_id:
        raise MovementContractError("Canonical league scoring source identity mismatch")
    try:
        league_season = int(league.get("Season"))
    except (TypeError, ValueError) as exc:
        raise MovementContractError("Canonical league scoring source has invalid Season") from exc
    if league_season != current_season:
        raise MovementContractError(
            f"Canonical league scoring source season mismatch: expected {current_season}, found {league.get('Season')!r}"
        )
    scoring = _required_dict(league.get("ScoringSettings"), "Canonical league ScoringSettings")
    scoring_fingerprint = sha256_json(scoring)
    declared_fingerprint = _required_text(
        source.get("scoring_fingerprint"),
        "movement.source.canonical_league_scoring.scoring_fingerprint",
    )
    if declared_fingerprint != scoring_fingerprint:
        raise MovementContractError("Canonical league scoring evidence fingerprint mismatch")
    return {
        "canonical_league_id": canonical_league_id,
        "season": current_season,
        "path": relative_path,
        "scoring_fingerprint": scoring_fingerprint,
    }


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
        "team_source_migration": movement_config.get("team_source_migration"),
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
    canonical_scoring = _canonical_scoring_evidence(root, movement_source, movement_config)

    free_agent_source = _required_dict(movement_source.get("free_agent_signals"), "movement.source.free_agent_signals")
    player_source = _required_dict(movement_source.get("player_signals"), "movement.source.player_signals")
    evidence_payload = {
        "evaluation_date": movement_source.get("comparison_anchor_date"),
        "free_agent_input_fingerprint": free_agent_source.get("input_fingerprint"),
        "player_input_fingerprint": player_source.get("input_fingerprint"),
        "ranking_histories": movement_source.get("ranking_histories"),
        "canonical_league_scoring": canonical_scoring,
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
