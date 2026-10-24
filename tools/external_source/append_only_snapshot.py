"""Dormant immutable ranked market snapshot writer (#988, 4A.2).

This module is NOT connected to a provider fetcher, GitHub Action, scheduler,
or production publication path. Only *verified* private repository operation
and dataset-specific permitted storage authorize a call; private visibility
alone is never a license. Callers must independently verify visibility and
rights before providing those attestations, and still own semantic-change
gating and latest-pointer publication. Tests use synthetic temporary roots.

Existing legacy daily Source evidence is immutable and never modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .snapshot_plan import (
    PlannedSnapshot,
    SnapshotCollisionError,
    inspect_planned_snapshot,
)


class ArchiveAuthorizationError(PermissionError):
    """Source retention or repository visibility does not permit archiving."""


class ArchiveWriteError(ValueError):
    """Invalid or conflicting immutable Source evidence."""


def _authorize(*, storage_rights: str, repository_visibility: str) -> None:
    if repository_visibility != "private":
        raise ArchiveAuthorizationError(
            "Append-only Source history requires a verified private repository"
        )
    if storage_rights != "allowed":
        raise ArchiveAuthorizationError(
            "Dataset-specific durable Source storage rights must be explicitly allowed"
        )


def _metadata(
    plan: PlannedSnapshot,
    csv_content: str,
    source_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(source_metadata, Mapping):
        raise ArchiveWriteError("Source metadata must be an object")
    if source_metadata.get("schema_version") != plan.schema_version:
        raise ArchiveWriteError("Source schema version differs from planned snapshot")
    snapshot = source_metadata.get("snapshot")
    if not isinstance(snapshot, Mapping):
        raise ArchiveWriteError("Source metadata.snapshot is required")
    if snapshot.get("ranking_sha256") != plan.ranking_sha256:
        raise ArchiveWriteError("Source metadata ranking hash differs from planned content")
    if not source_metadata.get("ranking_id"):
        raise ArchiveWriteError("Source metadata ranking_id is required")
    if not source_metadata.get("fetched_at"):
        raise ArchiveWriteError("Source metadata fetched_at is required")
    if hashlib.sha256(csv_content.encode("utf-8")).hexdigest() != plan.ranking_sha256:
        raise ArchiveWriteError("Planned Source bytes do not match original ranking content")
    expected = plan.metadata_identity()
    for key, value in expected.items():
        if key in source_metadata and source_metadata[key] != value:
            raise ArchiveWriteError(f"Conflicting immutable metadata identity: {key}")
    combined = dict(source_metadata)
    combined.update(expected)
    # JSON serialization catches incompatible provider payloads *before*
    # reserving any new directory in the canonical snapshots tree.
    try:
        json.dumps(combined, allow_nan=False, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ArchiveWriteError("Source metadata is not stable JSON") from exc
    return combined


def persist_ranked_snapshot(
    plan: PlannedSnapshot,
    *,
    csv_content: str,
    source_metadata: Mapping[str, Any],
    storage_rights: str,
    repository_visibility: str,
) -> str:
    """Return 'created'/'identical'; fail closed on partial or changed evidence.

    Requires private visibility and explicit dataset storage permission, both
    verified by the future caller. Never writes latest.json, existing daily
    paths, raw-latest.json, public/data, or data-derived. Provider code must
    avoid invoking this for semantic no-ops. Temporary staging stays hidden
    from snapshot discovery; rename exposes a complete directory together.
    On any collision or interruption, no existing Source directory is edited.
    """
    _authorize(
        storage_rights=storage_rights,
        repository_visibility=repository_visibility,
    )
    metadata = _metadata(plan, csv_content, source_metadata)
    result = inspect_planned_snapshot(plan, csv_content=csv_content)
    if result == "identical":
        persisted = json.loads(plan.metadata_file.read_text(encoding="utf-8"))
        if persisted != metadata:
            raise SnapshotCollisionError(
                f"Immutable Source metadata mismatch on replay: {plan.metadata_file}"
            )
        return "identical"

    parent = plan.directory.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".pending-market-", dir=parent))
    try:
        ranking = temporary / "ranking.csv"
        metadata_file = temporary / "metadata.json"
        with ranking.open("x", encoding="utf-8", newline="") as stream:
            stream.write(csv_content)
            stream.flush()
            os.fsync(stream.fileno())
        with metadata_file.open("x", encoding="utf-8", newline="") as stream:
            stream.write(json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        # Recheck before publishing the complete immutable directory. If a
        # concurrent writer won the race, a non-empty existing destination
        # must never be replaced or silently treated as equivalent.
        if plan.directory.exists():
            raise SnapshotCollisionError(
                f"Immutable snapshot path appeared during staging: {plan.directory}"
            )
        try:
            os.rename(temporary, plan.directory)
        except OSError as exc:
            raise SnapshotCollisionError(
                f"Immutable snapshot publication collision: {plan.directory}"
            ) from exc
        return "created"
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
