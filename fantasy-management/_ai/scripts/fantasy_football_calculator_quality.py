"""Season-aware coverage policy for Fantasy Football Calculator datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_PHASES = {
    "pre_regular_season",
    "regular_season",
    "post_regular_season",
}
VALID_STATUSES = {
    "usable",
    "reduced_coverage",
    "insufficient_coverage",
    "inactive_for_phase",
}


class FfcQualityPolicyError(RuntimeError):
    """Raised when the FFC source-quality policy is missing or invalid."""


def load_quality_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FfcQualityPolicyError(f"FFC quality policy is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FfcQualityPolicyError(f"FFC quality policy is invalid JSON: {path}") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise FfcQualityPolicyError("Unexpected FFC quality policy schema version")
    if policy.get("source_id") != "fantasy-football-calculator":
        raise FfcQualityPolicyError("Unexpected FFC quality policy source_id")
    datasets = policy.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise FfcQualityPolicyError("FFC quality policy has no datasets")
    for dataset_id, definition in datasets.items():
        phases = definition.get("phases") if isinstance(definition, dict) else None
        if not isinstance(phases, dict) or set(phases) != VALID_PHASES:
            raise FfcQualityPolicyError(
                f"FFC quality policy {dataset_id} must define exactly {sorted(VALID_PHASES)}"
            )
        for phase, phase_policy in phases.items():
            if not isinstance(phase_policy, dict):
                raise FfcQualityPolicyError(
                    f"FFC quality policy {dataset_id}/{phase} is invalid"
                )
            active = phase_policy.get("active")
            expected = phase_policy.get("expected_minimum_rows")
            minimum = phase_policy.get("minimum_usable_rows")
            if not isinstance(active, bool):
                raise FfcQualityPolicyError(
                    f"FFC quality policy {dataset_id}/{phase} has invalid active"
                )
            if (
                not isinstance(expected, int)
                or not isinstance(minimum, int)
                or expected < 0
                or minimum < 0
                or expected < minimum
            ):
                raise FfcQualityPolicyError(
                    f"FFC quality policy {dataset_id}/{phase} has invalid row thresholds"
                )
    return policy


def evaluate_dataset_coverage(
    policy: dict[str, Any],
    *,
    dataset_id: str,
    phase: str,
    row_count: int,
) -> dict[str, Any]:
    if phase not in VALID_PHASES:
        raise FfcQualityPolicyError(f"Unsupported NFL season phase: {phase}")
    datasets = policy.get("datasets") or {}
    definition = datasets.get(dataset_id)
    if not isinstance(definition, dict):
        raise FfcQualityPolicyError(f"FFC quality policy has no dataset {dataset_id}")
    phase_policy = (definition.get("phases") or {}).get(phase)
    if not isinstance(phase_policy, dict):
        raise FfcQualityPolicyError(
            f"FFC quality policy has no phase {phase} for {dataset_id}"
        )
    if row_count < 0:
        raise FfcQualityPolicyError("row_count must not be negative")

    active = bool(phase_policy["active"])
    expected = int(phase_policy["expected_minimum_rows"])
    minimum = int(phase_policy["minimum_usable_rows"])
    if not active:
        status = "inactive_for_phase"
        usable = False
    elif row_count < minimum:
        status = "insufficient_coverage"
        usable = False
    elif row_count < expected:
        status = "reduced_coverage"
        usable = True
    else:
        status = "usable"
        usable = True

    return {
        "status": status,
        "usable": usable,
        "active": active,
        "observed_rows": row_count,
        "expected_minimum_rows": expected,
        "minimum_usable_rows": minimum,
    }
