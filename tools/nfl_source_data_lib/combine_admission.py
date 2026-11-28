"""Read-only, isolated Combine admission planning for #1618 M2b.

Git is the accepted state. The provider registry and Raw metadata remain their
existing Source Evidence contracts. No production caller, write or admission
artifact is introduced here.
"""
from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from canonical_routing import (
    AcceptedSnapshot, COMBINE_DATASET, FamilyRouting, preflight_accepted_combine,
)
from data_roots import DATA_SOURCE_ROOT
from .combine import build_combine_files
from .common import Dataset, load_registry

_PROVIDER_DATASET = "nflverse.combine"
_REGISTRY = Path(DATA_SOURCE_ROOT, "registry.json")


@dataclass(frozen=True)
class CombineAdmissionPlan:
    snapshot: AcceptedSnapshot
    dataset: Dataset
    paths: Mapping[int, Path]
    grouped: dict[int, list[dict[str, Any]]]
    conflicts: list[dict[str, Any]]
    new_seasons: frozenset[int]
    source_sha256: str

    def revalidate_inputs(self) -> None:
        """Recheck the same commit, routes and source bytes before shadow writes."""
        preflight_accepted_combine(
            self.snapshot.root, self.snapshot.commit, self.snapshot.routing,
        )
        _verify_source(self.snapshot, self.dataset)


def _verify_source(snapshot: AcceptedSnapshot, dataset: Dataset) -> tuple[Counter[int], str, int]:
    snapshot.read_tracked_file(_REGISTRY)
    registered = [item for item in load_registry(snapshot.root) if item.id == _PROVIDER_DATASET]
    if registered != [dataset]:
        raise ValueError("Combine dataset does not match the accepted provider registry")
    if (dataset.source_mode != "fixed" or dataset.source_format != "csv"
            or dataset.refresh_policy != "discover-new-partitions"
            or dataset.lifecycle_class != "immutable-history"
            or dataset.partition_key != "season"
            or dataset.finalization_policy != "freeze-prior-seasons"
            or dataset.repair_policy != "explicit-force"
            or not dataset.materialize):
        raise ValueError("Unsupported Combine admission lifecycle")

    raw = snapshot.read_tracked_file(dataset.raw_path.relative_to(snapshot.root))
    meta = json.loads(snapshot.read_tracked_file(dataset.metadata_path.relative_to(snapshot.root)))
    digest = hashlib.sha256(raw).hexdigest()
    expected = {
        "dataset": dataset.id,
        "provider": dataset.provider,
        "upstream": dataset.upstream,
        "sourceUrl": dataset.source_url,
        "sourceFormat": dataset.source_format,
        "contentHashSha256": digest,
        "kind": dataset.kind,
        "refreshPolicy": dataset.refresh_policy,
        "retentionPolicy": dataset.retention_policy,
        "lifecycle": {
            "class": dataset.lifecycle_class, "partitionKey": dataset.partition_key,
            "finalization": dataset.finalization_policy, "repairPolicy": dataset.repair_policy,
        },
    }
    if (not isinstance(meta, dict) or any(meta.get(key) != value for key, value in expected.items())
            or meta.get("sourceMode", "fixed") != "fixed"
            or meta.get("availabilityStatus", "available") != "available"):
        raise ValueError("Combine Raw metadata does not attest the accepted source revision")
    retrieved = datetime.fromisoformat(meta["retrievedAtUtc"].replace("Z", "+00:00"))
    if retrieved.utcoffset() is None:
        raise ValueError("Combine source observation timestamp is not timezone-aware")

    rows = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    header = next(rows, [])
    if (header != meta.get("columns") or len(header) != len(set(header))
            or not set(dataset.required_columns) <= set(header) or "season" not in header):
        raise ValueError("Combine source column evidence is invalid")
    season_column = header.index("season")
    counts: Counter[int] = Counter()
    for row in rows:
        if len(row) != len(header) or not re.fullmatch(r"[1-9][0-9]{3}", row[season_column]):
            raise ValueError("Invalid Combine source row width or season")
        counts[int(row[season_column])] += 1
    count = sum(counts.values())
    if (type(meta.get("rowCount")) is not int or count != meta["rowCount"]
            or count < dataset.minimum_rows):
        raise ValueError("Combine source row coverage does not match accepted metadata")
    return counts, digest, retrieved.year


def plan_combine_shadow(
    repo_root: Path, base_commit: str, routing: FamilyRouting,
    canonical: list[dict[str, Any]], draft_payloads: dict[int, dict[str, Any]],
    *, approved_new_seasons: frozenset[int] = frozenset(),
) -> CombineAdmissionPlan:
    """Plan a shadow only; explicit new-season scope cannot replace evidence.

    Reuse the normalizer for identity and Draft semantics (including explicit
    unresolved/ambiguous states). Every Raw row must have a normalized record.
    No publication rights are granted by this function or its scope parameter.
    """
    snapshot = preflight_accepted_combine(repo_root, base_commit, routing)
    snapshot.read_tracked_file(_REGISTRY)
    registered = [item for item in load_registry(snapshot.root) if item.id == _PROVIDER_DATASET]
    if len(registered) != 1:
        raise ValueError("Missing or ambiguous Combine provider registry entry")
    dataset = registered[0]
    counts, digest, observation_year = _verify_source(snapshot, dataset)
    grouped, conflicts = build_combine_files(dataset, canonical, draft_payloads)
    if {season: len(records) for season, records in grouped.items()} != dict(counts):
        raise ValueError("Combine normalization does not preserve source season coverage")
    existing = set(snapshot.partitions)
    if not existing <= grouped.keys():
        raise ValueError("Accepted Combine season is missing from source candidates")
    new = frozenset(grouped.keys() - existing)
    if (type(approved_new_seasons) is not frozenset
            or any(type(season) is not int for season in approved_new_seasons)
            or new != approved_new_seasons):
        raise ValueError("New Combine seasons require exact approved shadow scope")
    if any(season > observation_year for season in new):
        raise ValueError("New Combine season is later than the source observation")
    paths = {season: snapshot.path_for(season) for season in existing}
    paths.update({season: snapshot.root / routing.relative_path(COMBINE_DATASET, season)
                  for season in new})
    plan = CombineAdmissionPlan(
        snapshot, dataset, MappingProxyType(paths), grouped, conflicts, new, digest,
    )
    plan.revalidate_inputs()
    return plan
