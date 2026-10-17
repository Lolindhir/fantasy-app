"""Dormant append-only combined Sleeper Add/Drop Source archive writer (#988).

One immutable observation per UTC day even when ranks/counts are unchanged,
plus additional observations if the *semantic* add/drop ranking changes.
Derived comparison data is explicitly excluded. No provider fetcher, workflow,
latest pointer, App or Shared-Derived publisher invokes this module yet.

Only a future caller that independently verified private repo visibility and
dataset-specific allowed storage rights may invoke it. A private repository
does not itself grant permission to retain third-party provider data.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .sleeper_snapshot_discovery import discover_sleeper_snapshots


class SleeperArchiveAuthorizationError(PermissionError):
    """Additional Source retention is not authorized."""


class SleeperArchiveCollisionError(ValueError):
    """Immutable Source archive evidence is missing or incompatible."""


def _observed_at(doc: Mapping[str, Any]) -> datetime:
    raw = doc.get("generated_at")
    if not isinstance(raw, str):
        raise SleeperArchiveCollisionError("Sleeper Source generated_at is missing")
    try:
        observed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SleeperArchiveCollisionError("Invalid Sleeper UTC generated_at") from exc
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise SleeperArchiveCollisionError("Sleeper generated_at needs timezone")
    return observed.astimezone(timezone.utc)


def _validated_source_payload(latest: Mapping[str, Any], observed: datetime) -> tuple[str, str]:
    """Validate *all* Source rows with the same fail-closed archive reader.

    The validator is run in a disposable temporary root prior to any canonical
    archive directory creation, including for potential semantic no-ops.
    """
    doc = dict(latest)
    doc.pop("comparison", None)
    fingerprint = doc.get("semantic_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise SleeperArchiveCollisionError("Missing semantic Sleeper Source fingerprint")
    basename = f"{observed:%H%M%S}Z-{fingerprint[:8]}"
    content = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with tempfile.TemporaryDirectory(prefix="sleeper-source-check-") as temp:
        snapshots = Path(temp) / "snapshots"
        validation = snapshots / observed.date().isoformat() / basename / "observation.json"
        validation.parent.mkdir(parents=True)
        validation.write_text(content, encoding="utf-8", newline="\n")
        evidence = discover_sleeper_snapshots(snapshots)
        if len(evidence) != 1 or evidence[0].observation_file != validation:
            raise SleeperArchiveCollisionError("Invalid Sleeper Source observation")
    return basename, content


def persist_sleeper_observation(
    snapshots_root: Path,
    *,
    latest_document: Mapping[str, Any],
    storage_rights: str,
    repository_visibility: str,
) -> str:
    """Append one validated immutable combined snapshot, or return unchanged.

    'created' means a new UTC day or changed semantic fingerprint. 'unchanged'
    means another refresh in the current UTC day with the same semantic values.
    Missing/partial existing archives, future-to-past order and conflicting
    snapshot identity all fail closed. This writer never changes latest.json.
    """
    if repository_visibility != "private":
        raise SleeperArchiveAuthorizationError(
            "Verified private repository required for additional Sleeper Source retention"
        )
    if storage_rights != "allowed":
        raise SleeperArchiveAuthorizationError(
            "Dataset-specific Sleeper durable Source storage must explicitly be allowed"
        )
    observed = _observed_at(latest_document)
    basename, content = _validated_source_payload(latest_document, observed)
    fingerprint = latest_document["semantic_fingerprint"]
    previous = discover_sleeper_snapshots(snapshots_root)
    if previous:
        last = previous[-1]
        if observed < last.observed_at:
            raise SleeperArchiveCollisionError("Out-of-order Sleeper Source observation")
        last_doc = json.loads(last.observation_file.read_text(encoding="utf-8"))
        if (
            last.day == observed.date()
            and last_doc["semantic_fingerprint"] == fingerprint
        ):
            return "unchanged"

    destination = snapshots_root / observed.date().isoformat() / basename
    if destination.exists():
        existing = destination / "observation.json"
        if existing.is_file() and existing.read_text(encoding="utf-8") == content:
            return "unchanged"
        raise SleeperArchiveCollisionError(f"Immutable Sleeper path collision: {destination}")

    # Stage a complete immutable directory on the same filesystem and publish
    # only after durable content has been flushed. Atomic visibility is not an
    # authorization for concurrent branch publishes: the future producer also
    # needs a CAS-safe/retry GitHub writer under #471.
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".pending-sleeper-", dir=parent))
    try:
        staged = temporary / "observation.json"
        with staged.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            raise SleeperArchiveCollisionError(f"Sleeper path appeared during staging: {destination}")
        try:
            os.rename(temporary, destination)
        except OSError as exc:
            raise SleeperArchiveCollisionError(
                f"Sleeper archive publication collision: {destination}"
            ) from exc
        return "created"
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
