from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import build_audit
from .combine import build_combine_files
from .common import CANONICAL_SCHEMA_VERSION, Dataset, as_int, load_json, write_json_if_changed
from .draft import build_draft_files
from .identity import build_identities
from .lifecycle import effective_partition_payload
from .mapping_history import build_historical_app_mapping_claims, extend_provider_mapping_payload
from .phase1 import build_phase1_outputs
from .provider_mappings import build_provider_mapping_payload


def _observation_season(repo_root: Path) -> int:
    league = load_json(repo_root / "public/data/League.json", {}) or {}
    season = as_int(league.get("Season"))
    if season is not None:
        return season
    metadata = load_json(repo_root / "public/data/Metadata.json", {}) or {}
    season = as_int(metadata.get("LeagueYear"))
    if season is not None:
        return season
    return datetime.now(timezone.utc).year


def _persisted_phase1_audit(phase1_audit: dict[str, Any]) -> dict[str, Any]:
    """Keep execution-only counters out of the persisted semantic audit payload."""
    persisted = dict(phase1_audit)
    persisted.pop("frozenPartitionsPreserved", None)
    return persisted


def _draft_payloads(
    repo_root: Path,
    dataset: Dataset,
    grouped: dict[int, list[dict[str, Any]]],
    observation_season: int,
    *,
    force: bool,
) -> tuple[dict[int, dict[str, Any]], int]:
    payloads: dict[int, dict[str, Any]] = {}
    preserved = 0
    for season, picks in sorted(grouped.items()):
        candidate = {
            "SchemaVersion": CANONICAL_SCHEMA_VERSION,
            "Season": season,
            "SourceDataset": dataset.id,
            "Finalized": True,
            "Picks": picks,
        }
        payload, was_preserved = effective_partition_payload(
            dataset,
            path=repo_root / "source-data/nfl/draft" / f"{season}.json",
            candidate=candidate,
            partition_season=season,
            observation_season=observation_season,
            force=force,
        )
        payloads[season] = payload
        preserved += int(was_preserved)
    return payloads, preserved


def _drafted_internal_ids(draft_payloads: dict[int, dict[str, Any]]) -> set[str]:
    return {
        pick["CanonicalPlayerID"]
        for payload in draft_payloads.values()
        for pick in payload.get("Picks", [])
        if pick.get("CanonicalPlayerID")
    }


def _combine_payloads(
    repo_root: Path,
    dataset: Dataset,
    grouped: dict[int, list[dict[str, Any]]],
    observation_season: int,
    *,
    force: bool,
) -> tuple[dict[int, dict[str, Any]], int]:
    payloads: dict[int, dict[str, Any]] = {}
    preserved = 0
    for season, records in sorted(grouped.items()):
        candidate = {
            "SchemaVersion": CANONICAL_SCHEMA_VERSION,
            "Season": season,
            "SourceDataset": dataset.id,
            "Finalized": True,
            "Records": records,
        }
        payload, was_preserved = effective_partition_payload(
            dataset,
            path=repo_root / "source-data/nfl/combine" / f"{season}.json",
            candidate=candidate,
            partition_season=season,
            observation_season=observation_season,
            force=force,
        )
        payloads[season] = payload
        preserved += int(was_preserved)
    return payloads, preserved


def materialize(repo_root: Path, datasets: dict[str, Dataset], *, force: bool = False) -> dict[str, Any]:
    for dataset in datasets.values():
        if dataset.is_season_partitioned:
            continue
        if not dataset.raw_path.exists():
            raise FileNotFoundError(f"Cannot materialize without raw dataset: {dataset.raw_path}")

    canonical, ff_rows, identity_source_conflicts, provider_claims, mapping_conflicts = (
        build_identities(repo_root, datasets)
    )
    observation_season = _observation_season(repo_root)

    draft_dataset = datasets["nflverse.draft-picks"]
    draft_grouped, _ = build_draft_files(draft_dataset, canonical)
    draft_payloads, draft_partitions_preserved = _draft_payloads(
        repo_root,
        draft_dataset,
        draft_grouped,
        observation_season,
        force=force,
    )
    drafted_internal_ids = _drafted_internal_ids(draft_payloads)

    provider_mapping_payload = build_provider_mapping_payload(
        repo_root,
        provider_claims,
        mapping_conflicts,
        observation_season,
    )
    historical_claims, historical_resolution_conflicts, historical_mapping_stats = (
        build_historical_app_mapping_claims(repo_root, canonical)
    )
    provider_mapping_payload = extend_provider_mapping_payload(
        provider_mapping_payload,
        historical_claims,
        historical_resolution_conflicts,
    )

    combine_payloads: dict[int, dict[str, Any]] = {}
    combine_conflicts: list[dict[str, Any]] = []
    combine_partitions_preserved = 0
    combine_dataset = datasets.get("nflverse.combine")
    if combine_dataset is not None:
        combine_grouped, combine_conflicts = build_combine_files(
            combine_dataset,
            canonical,
            draft_payloads,
        )
        combine_payloads, combine_partitions_preserved = _combine_payloads(
            repo_root,
            combine_dataset,
            combine_grouped,
            observation_season,
            force=force,
        )

    phase1_outputs, phase1_audit, phase1_partitions_preserved = build_phase1_outputs(
        repo_root,
        datasets,
        canonical,
        observation_season,
        force=force,
    )

    audit = build_audit(
        repo_root,
        canonical,
        ff_rows,
        drafted_internal_ids,
        draft_payloads.keys(),
        identity_source_conflicts=identity_source_conflicts,
        provider_mapping_conflicts=provider_mapping_payload.get("Conflicts", []),
        historical_mapping_stats=historical_mapping_stats,
        historical_resolution_conflicts=provider_mapping_payload.get("HistoricalResolutionConflicts", []),
        combine_payloads=combine_payloads,
        combine_draft_link_conflicts=combine_conflicts,
    )
    audit["phase1Datasets"] = _persisted_phase1_audit(phase1_audit)

    identity_payload = {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "IdentityPolicy": {
            "InternalKey": "CanonicalPlayerID",
            "CanonicalPlayerIDNamespace": "fantasy-app",
            "CanonicalPlayerIDIsApplicationDefined": True,
            "ExternalIDsAreMappings": True,
            "ProviderMappingsAreHistorical": True,
            "CurrentAppPlayerIDProvider": "Sleeper",
            "ExistingCanonicalPlayerIDIsStable": True,
            "NameMatchingIsAuthoritative": False,
        },
        "Players": canonical,
    }

    identity_changed = write_json_if_changed(
        repo_root / "source-data/nfl/identities/players.json", identity_payload
    )
    provider_mappings_changed = write_json_if_changed(
        repo_root / "source-data/nfl/identities/provider-mappings.json", provider_mapping_payload
    )
    draft_changed = 0
    for season, payload in draft_payloads.items():
        if write_json_if_changed(repo_root / "source-data/nfl/draft" / f"{season}.json", payload):
            draft_changed += 1
    combine_changed = 0
    for season, payload in combine_payloads.items():
        if write_json_if_changed(repo_root / "source-data/nfl/combine" / f"{season}.json", payload):
            combine_changed += 1
    phase1_changed = 0
    for path, payload in phase1_outputs:
        if write_json_if_changed(path, payload):
            phase1_changed += 1
    audit_changed = write_json_if_changed(
        repo_root / "source-data/audits/nfl-source-data-audit.json", audit
    )

    return {
        "identityCount": len(canonical),
        "identityChanged": identity_changed,
        "providerMappingCount": len(provider_mapping_payload.get("Mappings", [])),
        "providerMappingConflictCount": len(provider_mapping_payload.get("Conflicts", [])),
        "historicalMappingObservationCount": len(historical_claims),
        "historicalResolutionConflictCount": len(
            provider_mapping_payload.get("HistoricalResolutionConflicts", [])
        ),
        "providerMappingsChanged": provider_mappings_changed,
        "draftSeasonCount": len(draft_payloads),
        "draftFilesChanged": draft_changed,
        "draftPartitionsPreserved": draft_partitions_preserved,
        "combineSeasonCount": len(combine_payloads),
        "combineFilesChanged": combine_changed,
        "combinePartitionsPreserved": combine_partitions_preserved,
        "combineDraftLinkConflictCount": len(combine_conflicts),
        "phase1CanonicalFileCount": len(phase1_outputs),
        "phase1FilesChanged": phase1_changed,
        "phase1PartitionsPreserved": phase1_partitions_preserved,
        "identitySourceMappingConflictCount": len(identity_source_conflicts),
        "auditChanged": audit_changed,
        "audit": audit,
    }
