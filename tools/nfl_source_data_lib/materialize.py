from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import build_audit
from .common import Dataset, SCHEMA_VERSION, as_int, load_json, write_json_if_changed
from .draft import build_draft_files
from .identity import build_identities, build_provider_mapping_payload


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


def materialize(repo_root: Path, datasets: dict[str, Dataset]) -> dict[str, Any]:
    for dataset in datasets.values():
        if not dataset.raw_path.exists():
            raise FileNotFoundError(f"Cannot materialize without raw dataset: {dataset.raw_path}")

    # Build and validate every semantic payload before writing any canonical file.
    # This keeps a failed normalization from publishing a partially rebuilt state.
    canonical, ff_rows, identity_source_conflicts, provider_claims, mapping_conflicts = build_identities(
        repo_root, datasets
    )
    grouped, drafted_internal_ids = build_draft_files(datasets["nflverse.draft-picks"], canonical)
    observation_season = _observation_season(repo_root)
    provider_mapping_payload = build_provider_mapping_payload(
        repo_root,
        provider_claims,
        mapping_conflicts,
        observation_season,
    )
    audit = build_audit(
        repo_root,
        canonical,
        ff_rows,
        drafted_internal_ids,
        grouped.keys(),
        identity_source_conflicts=identity_source_conflicts,
        provider_mapping_conflicts=provider_mapping_payload.get("Conflicts", []),
    )

    identity_payload = {
        "SchemaVersion": SCHEMA_VERSION,
        "IdentityPolicy": {
            "InternalKey": "NFLPlayerID",
            "ExternalIDsAreMappings": True,
            "ProviderMappingsAreHistorical": True,
            "CurrentAppPlayerIDProvider": "Sleeper",
            "ExistingNFLPlayerIDIsStable": True,
            "NameMatchingIsAuthoritative": False,
        },
        "Players": canonical,
    }
    draft_payloads = {
        season: {
            "SchemaVersion": SCHEMA_VERSION,
            "Season": season,
            "SourceDataset": "nflverse.draft-picks",
            "Finalized": True,
            "Picks": picks,
        }
        for season, picks in sorted(grouped.items())
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
    audit_changed = write_json_if_changed(
        repo_root / "source-data/audits/nfl-source-data-audit.json", audit
    )

    return {
        "identityCount": len(canonical),
        "identityChanged": identity_changed,
        "providerMappingCount": len(provider_mapping_payload.get("Mappings", [])),
        "providerMappingConflictCount": len(provider_mapping_payload.get("Conflicts", [])),
        "providerMappingsChanged": provider_mappings_changed,
        "draftSeasonCount": len(grouped),
        "draftFilesChanged": draft_changed,
        "identitySourceMappingConflictCount": len(identity_source_conflicts),
        "auditChanged": audit_changed,
        "audit": audit,
    }
