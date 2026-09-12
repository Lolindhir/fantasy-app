from __future__ import annotations

from copy import deepcopy
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


def _player_stats_identity_only_enrichment(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    """Allow null -> CanonicalPlayerID enrichment without reopening frozen facts.

    Historical stat facts stay immutable. A later identity bridge may only repair a
    frozen partition when every non-identity byte of the semantic payload is still
    equal and no existing non-null CanonicalPlayerID would change.
    """

    if candidate.get("SourceDataset") != "nflverse.player-stats":
        return False
    existing_records = existing.get("Records")
    candidate_records = candidate.get("Records")
    if not isinstance(existing_records, list) or not isinstance(candidate_records, list):
        return False
    if len(existing_records) != len(candidate_records):
        return False

    existing_without_ids = deepcopy(existing)
    candidate_without_ids = deepcopy(candidate)
    changed = False
    for old_record, new_record, old_copy, new_copy in zip(
        existing_records,
        candidate_records,
        existing_without_ids["Records"],
        candidate_without_ids["Records"],
        strict=True,
    ):
        if not isinstance(old_record, dict) or not isinstance(new_record, dict):
            return False
        old_id = old_record.get("CanonicalPlayerID")
        new_id = new_record.get("CanonicalPlayerID")
        if old_id not in (None, "") and old_id != new_id:
            return False
        if old_id in (None, "") and new_id not in (None, ""):
            changed = True
        old_copy.pop("CanonicalPlayerID", None)
        new_copy.pop("CanonicalPlayerID", None)

    return changed and existing_without_ids == candidate_without_ids


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
        if isinstance(existing, dict) and _player_stats_identity_only_enrichment(existing, candidate):
            return candidate, False
        return existing, True
    return candidate, False
