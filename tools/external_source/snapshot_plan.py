"""Pure, read-only planning for future append-only external-source snapshots.

This module does not write snapshots, alter latest pointers, change retention,
or authorize storage. #988 4A.2 activation needs the dataset-specific #190
storage/retention decision before any producer uses its planned paths.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SnapshotCollisionError(ValueError):
    """A planned immutable observation path already contains conflicting data."""


@dataclass(frozen=True)
class PlannedSnapshot:
    """A planned directory relative to the dataset's existing snapshot root."""

    key: str
    directory: Path
    ranking_file: Path
    metadata_file: Path
    semantic_sha256: str
    ranking_sha256: str
    schema_version: int

    def metadata_identity(self) -> dict[str, object]:
        """Fields the future writer must persist to prove path/content identity."""
        return {
            "snapshot_key": self.key,
            "snapshot_semantic_sha256": self.semantic_sha256,
            "ranking_sha256": self.ranking_sha256,
            "schema_version": self.schema_version,
        }


def plan_snapshot(
    snapshots_root: Path,
    *,
    observed_at: datetime,
    csv_content: str,
    schema_version: int,
) -> PlannedSnapshot:
    """Compute an immutable UTC-second + semantic-hash destination without writing.

    The complete SHA-256 binds both normalized CSV bytes and the source schema.
    Including schema_version makes a schema bump a new semantic observation even
    when CSV bytes happen to be identical. No provider-updated timestamp is
    substituted for the actual observation instant.
    """
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Snapshot observed_at must be timezone-aware")
    if type(schema_version) is not int or schema_version < 1:
        raise ValueError("Snapshot schema_version must be a positive integer")
    if not isinstance(csv_content, str) or not csv_content:
        raise ValueError("Snapshot requires nonempty normalized CSV content")
    utc = observed_at.astimezone(timezone.utc)
    ranking_sha = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()
    semantic = hashlib.sha256(
        f"schema_version={schema_version}\nranking_sha256={ranking_sha}\n".encode("ascii")
    ).hexdigest()
    day = utc.date().isoformat()
    basename = f"{utc:%H%M%S}Z-{semantic[:8]}"
    key = f"{day}/{basename}"
    directory = snapshots_root / day / basename
    return PlannedSnapshot(
        key=key,
        directory=directory,
        ranking_file=directory / "ranking.csv",
        metadata_file=directory / "metadata.json",
        semantic_sha256=semantic,
        ranking_sha256=ranking_sha,
        schema_version=schema_version,
    )


def inspect_planned_snapshot(plan: PlannedSnapshot, *, csv_content: str) -> str:
    """Read-only status: absent / identical; conflicting partial paths fail closed.

    This must run before a future append-only writer writes anything under
    the planned directory; it never mutates an old daily or intraday folder.
    A directory with incomplete or unverifiable metadata is not reused.
    """
    if not plan.directory.exists():
        return "absent"
    if not plan.directory.is_dir():
        raise SnapshotCollisionError(f"Snapshot path is not a directory: {plan.directory}")
    if not plan.ranking_file.is_file() or not plan.metadata_file.is_file():
        raise SnapshotCollisionError(f"Incomplete immutable snapshot: {plan.directory}")
    try:
        metadata = json.loads(plan.metadata_file.read_text(encoding="utf-8"))
        existing_ranking = plan.ranking_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotCollisionError(f"Unreadable immutable snapshot: {plan.directory}") from exc
    identity = plan.metadata_identity()
    if not isinstance(metadata, dict):
        raise SnapshotCollisionError(f"Invalid immutable snapshot metadata: {plan.metadata_file}")
    stored = {key: metadata.get(key) for key in identity}
    if (
        stored != identity
        or not _HEX_SHA256.fullmatch(str(metadata.get("snapshot_semantic_sha256", "")))
        or existing_ranking != csv_content
    ):
        raise SnapshotCollisionError(
            f"Immutable snapshot collision or changed content: {plan.directory}"
        )
    return "identical"
