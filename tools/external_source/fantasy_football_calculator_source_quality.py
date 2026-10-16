"""Phase-aware source-quality evaluation for Fantasy Football Calculator datasets."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from external_source.fantasy_football_calculator_adp_core import provider_dir

USABLE_STATUSES = {"usable", "reduced_coverage"}


class FantasyFootballCalculatorQualityError(RuntimeError):
    """Raised when the FFC source-quality contract is invalid."""


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = provider_dir(repo_root) / "source-contract.json"
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FantasyFootballCalculatorQualityError(
            f"Unable to load FFC source contract: {path}"
        ) from exc
    if contract.get("schema_version") != 1 or contract.get("source_id") != "fantasy-football-calculator":
        raise FantasyFootballCalculatorQualityError("Invalid FFC source contract header")
    datasets = contract.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise FantasyFootballCalculatorQualityError("FFC source contract has no datasets")
    return contract


def evaluate_dataset_coverage(
    contract: dict[str, Any],
    *,
    dataset_id: str,
    phase: str,
    observed_rows: int,
) -> dict[str, Any]:
    datasets = contract.get("datasets") or {}
    policy = datasets.get(dataset_id)
    if not isinstance(policy, dict):
        raise FantasyFootballCalculatorQualityError(
            f"Missing FFC quality policy for {dataset_id}"
        )
    minimum = int(policy.get("minimum_usable_rows", -1))
    expected = int(policy.get("expected_minimum_rows", -1))
    override = (policy.get("phase_overrides") or {}).get(phase) or {}
    expected = int(override.get("expected_minimum_rows", expected))
    if minimum < 0 or expected < minimum:
        raise FantasyFootballCalculatorQualityError(
            f"Invalid FFC quality thresholds for {dataset_id}: "
            f"minimum={minimum}, expected={expected}"
        )
    if observed_rows < minimum:
        status = "insufficient_coverage"
    elif observed_rows < expected:
        status = "reduced_coverage"
    else:
        status = "usable"
    return {
        "coverage_status": status,
        "observed_rows": observed_rows,
        "minimum_usable_rows": minimum,
        "expected_minimum_rows": expected,
        "publishable": status in USABLE_STATUSES,
    }


def observation_path(repo_root: Path) -> Path:
    return provider_dir(repo_root) / "observation.json"


def write_observation(repo_root: Path, payload: dict[str, Any]) -> Path:
    path = observation_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path
