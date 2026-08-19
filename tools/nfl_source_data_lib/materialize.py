from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import build_audit
from .common import Dataset, SCHEMA_VERSION, utc_now, write_json_if_changed
from .draft import build_draft_files
from .identity import build_identities


def materialize(repo_root: Path, datasets: dict[str, Dataset]) -> dict[str, Any]:
    for dataset in datasets.values():
        if not dataset.raw_path.exists():
            raise FileNotFoundError(f"Cannot materialize without raw dataset: {dataset.raw_path}")
    canonical, ff_rows, identity_source_conflicts = build_identities(repo_root, datasets)
    identity_payload = {
        "SchemaVersion": SCHEMA_VERSION, "GeneratedAtUtc": utc_now(),
        "IdentityPolicy": {"InternalKey": "NFLPlayerID", "ExternalIDsAreMappings": True,
                           "ExistingNFLPlayerIDIsStable": True, "NameMatchingIsAuthoritative": False},
        "Players": canonical,
    }
    identity_changed = write_json_if_changed(repo_root / "source-data/nfl/identities/players.json", identity_payload)
    grouped, drafted_internal_ids = build_draft_files(datasets["nflverse.draft-picks"], canonical)
    draft_changed = 0
    for season, picks in sorted(grouped.items()):
        payload = {"SchemaVersion": SCHEMA_VERSION, "Season": season,
                   "SourceDataset": "nflverse.draft-picks", "Finalized": True, "Picks": picks}
        if write_json_if_changed(repo_root / "source-data/nfl/draft" / f"{season}.json", payload):
            draft_changed += 1
    audit = build_audit(
        repo_root,
        canonical,
        ff_rows,
        drafted_internal_ids,
        grouped.keys(),
        identity_source_conflicts=identity_source_conflicts,
    )
    audit_changed = write_json_if_changed(repo_root / "source-data/audits/nfl-source-data-audit.json", audit)
    return {"identityCount": len(canonical), "identityChanged": identity_changed,
            "draftSeasonCount": len(grouped), "draftFilesChanged": draft_changed,
            "identitySourceMappingConflictCount": len(identity_source_conflicts),
            "auditChanged": audit_changed, "audit": audit}
