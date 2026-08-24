from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import CANONICAL_SCHEMA_VERSION, Dataset, load_json, normalize_legacy_canonical_player_fields


def partition_is_frozen(
    dataset: Dataset,
    *,
    partition_season: int,
    observation_season: int,
    existing_payload: dict[str, Any] | None,
) -> bool:
    if not existing_payload:
        return False
    policy = dataset.finalization_policy
    if policy == "freeze-existing-partitions":
        return bool(existing_payload.get("Finalized", True))
    if policy == "freeze-prior-seasons":
        return partition_season < observation_season and bool(existing_payload.get("Finalized", True))
    return False


def effective_partition_payload(
    dataset: Dataset,
    *,
    path: Path,
    candidate: dict[str, Any],
    partition_season: int,
    observation_season: int,
    force: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Return the payload to publish and whether a frozen existing partition was preserved."""
    existing = load_json(path)
    if isinstance(existing, dict):
        existing = normalize_legacy_canonical_player_fields(existing)
        if int(existing.get("SchemaVersion") or 1) < CANONICAL_SCHEMA_VERSION:
            existing["SchemaVersion"] = CANONICAL_SCHEMA_VERSION
    if force:
        return candidate, False
    if partition_is_frozen(
        dataset,
        partition_season=partition_season,
        observation_season=observation_season,
        existing_payload=existing if isinstance(existing, dict) else None,
    ):
        return existing, True
    return candidate, False
