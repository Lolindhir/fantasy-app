#!/usr/bin/env python3
"""Preview the Shared-Derived market-observations product from existing Source.

#988 step 4B (read-only first): deterministic dataset/season inventory and
in-memory candidate documents. This CLI deliberately has NO write/publish mode.
The future persistent data-derived writer, registry rights assessment (#190),
orchestration (#471), and FM consumer cutover are separate checkpoints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import data_derived_dir, data_source_dir  # noqa: E402
from external_source.identity import MappingIndex  # noqa: E402
from external_source.observation_adapter import (  # noqa: E402
    NeutralObservationRow,
    load_ranked_evidence,
    load_roster_activity_evidence,
    normalize_ranked_observations,
    normalize_sleeper_activity_observations,
)
from external_source.registry import dataset_dir, get_dataset, load_registry  # noqa: E402
from external_source.snapshot_discovery import Snapshot, discover_snapshots  # noqa: E402
from nfl_season_context import resolve_season_for_date  # noqa: E402

PRODUCT = "market-observations"
SCHEMA_VERSION = 1
PREVIEW_RENDERER_VERSION = 1
SLEEPER_LATEST = Path("market/roster-activity/sleeper/latest.json")


class MarketObservationError(ValueError):
    """Source evidence missing, incompatible, or inconsistent with the registry."""


def canonical_json(document: Any) -> str:
    """Stable output candidate bytes, never written to the repository."""
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def digest(document: Any) -> str:
    return hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def _relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise MarketObservationError(f"Source path outside repository: {path}") from exc


def _sleeper_instant(document: Mapping[str, Any]) -> datetime:
    value = document.get("generated_at")
    if not isinstance(value, str):
        raise MarketObservationError("Sleeper latest generated_at is missing")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketObservationError(f"Invalid Sleeper generated_at: {value}") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise MarketObservationError("Sleeper generated_at must be timezone-aware")
    return instant.astimezone(timezone.utc)


def _snapshots(repo_root: Path, dataset: Mapping[str, Any]) -> list[Snapshot]:
    return discover_snapshots(dataset_dir(repo_root, dict(dataset)) / "snapshots")


def _dataset_inventory(repo_root: Path, dataset: Mapping[str, Any]) -> dict[int, list[Snapshot]]:
    if dataset["provider"] == "sleeper":
        path = data_source_dir(repo_root) / SLEEPER_LATEST
        doc = load_roster_activity_evidence(dataset, path)
        season = resolve_season_for_date(repo_root, _sleeper_instant(doc.source_document).date().isoformat())
        return {season: []}  # current latest is one observation, not archived snapshots
    discovered = _snapshots(repo_root, dataset)
    if not discovered:
        raise MarketObservationError(f"No durable ranking Source Evidence for {dataset['id']}")
    by_season: dict[int, list[Snapshot]] = {}
    for snapshot in discovered:
        season = resolve_season_for_date(repo_root, snapshot.day.isoformat())
        by_season.setdefault(season, []).append(snapshot)
    return by_season


def inventory(repo_root: Path) -> list[dict[str, Any]]:
    """Enumerate the 19 registered dataset/season partitions from existing Source."""
    registry = load_registry(repo_root)
    result = []
    for dataset in sorted(registry["datasets"], key=lambda d: d["id"]):
        seasons = _dataset_inventory(repo_root, dataset)
        for season, snapshots in sorted(seasons.items()):
            result.append({
                "DatasetID": dataset["id"],
                "ObservationSeason": season,
                "ObservationCount": 1 if dataset["provider"] == "sleeper" else len(snapshots),
                "HistoryMode": "latest-only" if dataset["provider"] == "sleeper" else "persisted-snapshots",
            })
    return result


def _neutral_rows(rows: tuple[NeutralObservationRow, ...]) -> list[dict[str, Any]]:
    return [{
        "SourceRowNumber": r.source_row_number,
        "ProviderPlayerID": r.provider_player_id,
        "AssetType": r.asset_type,
        "CanonicalPlayerID": r.canonical_player_id,
        "IdentityStatus": r.identity_status,
        "IdentityMethod": r.identity_method,
        "ProviderValues": dict(r.provider_values),
    } for r in rows]


def _source_updated_at(metadata: Mapping[str, Any]) -> str | None:
    # Do not infer an UTC instant from a date-only provider source_updated_date.
    value = metadata.get("source_updated_at")
    if not isinstance(value, str) or not value:
        return None
    try:
        updated = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketObservationError(f"Invalid provider source_updated_at: {value}") from exc
    if updated.tzinfo is None or updated.utcoffset() is None:
        raise MarketObservationError("Provider source_updated_at missing timezone")
    return updated.astimezone(timezone.utc).isoformat()


def _ranked_observation(
    repo_root: Path, dataset: Mapping[str, Any], snapshot: Snapshot, index: MappingIndex,
) -> dict[str, Any]:
    evidence = load_ranked_evidence(dataset, snapshot)
    neutral = normalize_ranked_observations(
        repo_root, dataset, snapshot, mapping_index=index
    )
    return {
        "SnapshotID": f"{dataset['id']}:{snapshot.key}",
        "ObservedAtUtc": snapshot.observed_at.isoformat() if snapshot.observed_at else None,
        "SourceUpdatedAtUtc": _source_updated_at(evidence.source_metadata),
        "SourcePath": _relative(repo_root, snapshot.ranking_file),
        "MetadataPath": _relative(repo_root, snapshot.metadata_file),
        "SourceHash": evidence.ranking_sha256,
        "SourceSchemaVersion": evidence.source_version,
        "Rows": _neutral_rows(neutral),
    }


def _sleeper_observation(
    repo_root: Path, dataset: Mapping[str, Any], index: MappingIndex,
) -> dict[str, Any]:
    path = data_source_dir(repo_root) / SLEEPER_LATEST
    evidence = load_roster_activity_evidence(dataset, path)
    observed = _sleeper_instant(evidence.source_document)
    neutral = normalize_sleeper_activity_observations(
        repo_root, dataset, path, mapping_index=index
    )
    return {
        "SnapshotID": f"{dataset['id']}:{observed.date().isoformat()}:{evidence.source_fingerprint[:12]}",
        "ObservedAtUtc": observed.isoformat(),
        "SourceUpdatedAtUtc": None,
        "SourcePath": _relative(repo_root, path),
        "MetadataPath": None,
        "SourceHash": evidence.source_fingerprint,
        "SourceSchemaVersion": evidence.source_version,
        "Rows": _neutral_rows(neutral),
    }


def render_partition(
    repo_root: Path, dataset_id: str, season: int,
    *, mapping_index: MappingIndex | None = None,
) -> dict[str, Any]:
    """Compute candidate partition strictly from source and registry; never write it."""
    if type(season) is not int or season < 2000:
        raise MarketObservationError(f"Invalid observation season: {season}")
    dataset = get_dataset(load_registry(repo_root), dataset_id)
    partitions = _dataset_inventory(repo_root, dataset)
    if season not in partitions:
        raise MarketObservationError(f"No observed Source partition for {dataset_id}/{season}")
    index = mapping_index if mapping_index is not None else MappingIndex.load(repo_root)
    observations = (
        [_sleeper_observation(repo_root, dataset, index)]
        if dataset["provider"] == "sleeper"
        else [_ranked_observation(repo_root, dataset, s, index) for s in partitions[season]]
    )
    if not observations:
        raise MarketObservationError(f"Empty observation partition: {dataset_id}/{season}")
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "RendererVersion": PREVIEW_RENDERER_VERSION,
        "Product": PRODUCT,
        "DatasetID": dataset["id"],
        "Provider": dataset["provider"],
        "Kind": dataset["kind"],
        "ObservationSeason": season,
        "HistoryMode": "latest-only" if dataset["provider"] == "sleeper" else "persisted-snapshots",
        "Format": dataset["format"],
        "Attribution": dataset["rights"]["attribution"],
        "Rights": dataset["rights"],
        "Observations": observations,
    }


def candidate_path(repo_root: Path, dataset_id: str, season: int) -> Path:
    """Intended product location only. Never used for a write in this module."""
    registry = load_registry(repo_root)
    get_dataset(registry, dataset_id)
    return data_derived_dir(repo_root) / PRODUCT / dataset_id / f"{season}.json"


def preview_summary(repo_root: Path, dataset_id: str, season: int) -> dict[str, Any]:
    """Expose checksums and counts only; no provider content printed by CLI."""
    document = render_partition(repo_root, dataset_id, season)
    observations = document["Observations"]
    return {
        "Product": PRODUCT,
        "DatasetID": dataset_id,
        "ObservationSeason": season,
        "HistoryMode": document["HistoryMode"],
        "ObservationCount": len(observations),
        "RowCount": sum(len(o["Rows"]) for o in observations),
        "CandidateSha256": digest(document),
        "RightsStorage": document["Rights"]["storage"],
        "RightsPublication": document["Rights"]["publication"],
        "Mode": "read-only; no output file written",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory", help="List dataset/season partitions from existing Source")
    preview = sub.add_parser("preview", help="Render one partition in memory; print metadata/checksum only")
    preview.add_argument("--dataset-id", required=True)
    preview.add_argument("--season", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "inventory":
            output = inventory(args.repo_root)
        else:
            output = preview_summary(args.repo_root, args.dataset_id, args.season)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[market-observations] {exc}", file=sys.stderr)
        return 1
    print(canonical_json(output), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
