"""Deterministic, side-effect-free release-to-product file plan for NFL injuries.

Constructs the exact prospective Source/Canonical/Derived bytes with complete
lineage and compares them to persisted bytes supplied by a caller. No fetch,
file write, Git operation, publication or automatic activation occurs here.
Issue #1421; historical and current ESPN pipelines remain independent.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from .injury_reports import parse_injury_report_csv
from .injury_canonical import canonicalize_injury_reports
from derived_data_lib.nfl_injuries import derive_nfl_injuries

_DATASET = "nflverse.injuries"
_RELEASE = "https://github.com/nflverse/nflverse-data/releases/tag/injuries"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _render(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def plan_release_refresh(
    release: dict[str, Any],
    *,
    season: int,
    stored_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide if an upstream season asset needs a new download.

    Pure release-metadata observer: no network, no clock and no storage.
    A missing asset is retryable, never evidence of healthy players or
    permission to overwrite the last good product with empty results.
    """
    if not isinstance(season, int) or isinstance(season, bool) or not 2012 <= season <= 2099:
        raise ValueError("Unsupported injury release season")
    if not isinstance(release, dict) or not isinstance(release.get("assets"), list):
        raise ValueError("Injury release metadata requires an assets list")
    expected_name = f"injuries_{season}.csv"
    matching = [a for a in release["assets"]
                if isinstance(a, dict) and a.get("name") == expected_name]
    if not matching:
        return {
            "Season": season, "Action": "retry-later",
            "Reason": "upstream-season-asset-not-listed",
            "SourceAsset": None,
        }
    if len(matching) != 1:
        raise ValueError(f"Multiple upstream injury release assets named {expected_name}")
    asset = matching[0]
    expected_url = (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        f"injuries/{expected_name}"
    )
    if asset.get("browser_download_url") != expected_url:
        raise ValueError("Injury release asset download URL is not the expected official URL")
    ident, updated, size = asset.get("id"), asset.get("updated_at"), asset.get("size")
    if (not isinstance(ident, int) or isinstance(ident, bool) or ident < 1
            or not isinstance(updated, str) or not updated
            or not isinstance(size, int) or isinstance(size, bool) or size <= 0):
        raise ValueError("Incomplete injury release asset identity, timestamp or size")
    digest_raw = asset.get("digest")
    digest = None
    if digest_raw is not None:
        if not isinstance(digest_raw, str) or not digest_raw.startswith("sha256:"):
            raise ValueError("Unsupported injury asset digest format")
        digest = digest_raw.removeprefix("sha256:").lower()
        if not _SHA256.fullmatch(digest):
            raise ValueError("Invalid upstream injury asset SHA-256 digest")
    known = stored_metadata or {}
    if known and (known.get("SourceDataset") != _DATASET
                  or known.get("Season") != season):
        raise ValueError("Stored injury source metadata has the wrong dataset or season")
    same_size = known.get("AssetByteSize") == size
    same_digest = digest is not None and known.get("AssetSha256") == digest
    same_revision = (known.get("ReleaseAssetId") == ident
                     and known.get("ReleaseAssetUpdatedAt") == updated
                     and same_size)
    skip = same_size and (same_digest or (digest is None and same_revision))
    return {
        "Season": season,
        "Action": "no-op" if skip else "download-and-validate",
        "Reason": ("official-sha256-and-size-unchanged" if same_digest and same_size
                   else "same-provider-revision-no-official-digest" if skip
                   else "new-or-unverified-release-revision"),
        "SourceAsset": {
            "Name": expected_name,
            "Id": ident,
            "UpdatedAt": updated,
            "ByteSize": size,
            "Sha256": digest,
            "DownloadUrl": expected_url,
        },
        "FullSourceDigestAvailable": digest is not None,
    }


def build_injury_raw_artifacts(
    *,
    season: int,
    source_csv: bytes,
    expected_source_sha256: str | None = None,
    release_asset: Mapping[str, Any] | None = None,
) -> dict[str, bytes]:
    """Validate a source season and produce ONLY provider raw + provenance.

    This source owner deliberately requires no canonical player identity, NFL
    schedule, Derived builder, or App/league input.
    """
    actual_digest = _sha256(source_csv)
    if expected_source_sha256 is not None:
        expected = expected_source_sha256.lower().removeprefix("sha256:")
        if not _SHA256.fullmatch(expected):
            raise ValueError("Expected injury source digest must be SHA-256 hex")
        if actual_digest != expected:
            raise ValueError("Injury source digest does not match expected asset")
    release_id = None
    release_updated = None
    if release_asset is not None:
        release_id = release_asset.get("Id")
        release_updated = release_asset.get("UpdatedAt")
        upstream_size = release_asset.get("ByteSize")
        upstream_digest = release_asset.get("Sha256")
        expected_url = (
            "https://github.com/nflverse/nflverse-data/releases/download/"
            f"injuries/injuries_{season}.csv"
        )
        if (release_asset.get("Name") != f"injuries_{season}.csv"
                or release_asset.get("DownloadUrl") != expected_url
                or not isinstance(release_id, int) or isinstance(release_id, bool)
                or release_id < 1 or not isinstance(release_updated, str)
                or not release_updated or upstream_size != len(source_csv)):
            raise ValueError("Injury source bytes mismatch provided release asset metadata")
        if upstream_digest is not None and upstream_digest != actual_digest:
            raise ValueError("Downloaded injury source digest differs from release asset")
    parsed = parse_injury_report_csv(source_csv, season=season)
    if not parsed["Rows"]:
        raise ValueError("Empty injury report is not evidence of a healthy or complete season")
    raw_path = f"data-source/providers/nflverse/injuries/raw-{season}.csv"
    metadata_path = f"data-source/providers/nflverse/injuries/metadata-{season}.json"
    target: dict[str, bytes] = {raw_path: source_csv}
    target[metadata_path] = _render({
        "SchemaVersion": 1,
        "SourceDataset": _DATASET,
        "Season": season,
        "SourceUrl": f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv",
        "SourceRelease": _RELEASE,
        "AssetSha256": actual_digest,
        "AssetByteSize": len(source_csv),
        "AssetDigestVerification": (
            "matched-expected-digest" if expected_source_sha256 else
            "matched-provided-release-digest" if release_asset is not None
            and release_asset.get("Sha256") is not None else
            "self-hash-only-not-officially-verified"
        ),
        "ReleaseAssetId": release_id,
        "ReleaseAssetUpdatedAt": release_updated,
        "ReportRowCount": parsed["RowCount"],
        "SourceSchema": parsed["SourceSchema"],
        "OriginalAssetBytesRetained": True,
        "SnapshotSemantics": "retrospective-asset-revision-not-prekickoff",
    })
    return dict(sorted(target.items()))


def build_injury_artifacts(
    *,
    season: int,
    source_csv: bytes,
    players: dict[str, Any],
    schedule: dict[str, Any] | None = None,
    expected_source_sha256: str | None = None,
    release_asset: Mapping[str, Any] | None = None,
) -> dict[str, bytes]:
    """Generate intended bytes, never write them to disk.

    The returned paths are prospective and do not imply producer activation.
    Source original-asset verification is distinct from merely hashing bytes.
    """
    target = build_injury_raw_artifacts(
        season=season, source_csv=source_csv,
        expected_source_sha256=expected_source_sha256, release_asset=release_asset,
    )
    parsed = parse_injury_report_csv(source_csv, season=season)
    canonical = canonicalize_injury_reports(parsed, players, schedule=schedule)
    derived = derive_nfl_injuries(canonical)
    actual_digest = parsed["AssetSha256"]
    weeks: list[int] = []
    week_artifacts: list[dict[str, Any]] = []
    for partition in canonical["Partitions"]:
        week = partition["Week"]
        weeks.append(week)
        path = f"data-source/nfl/injuries/{season}/{week:02d}.json"
        encoded = _render(partition)
        target[path] = encoded
        week_artifacts.append({
            "Week": week, "Path": path,
            "ByteSize": len(encoded), "Sha256": _sha256(encoded),
        })
    target[f"data-source/nfl/injuries/{season}/manifest.json"] = _render({
        "SchemaVersion": 1,
        "SourceDataset": _DATASET,
        "Season": season,
        "SourceAssetSha256": actual_digest,
        "IdentityGraphFingerprint": canonical["IdentityGraphFingerprint"],
        "IdentityTimeBasis": "current-graph-not-historical-point-in-time",
        "ObservedWeeks": weeks,
        "ObservedWeekArtifacts": week_artifacts,
        "ObservedWeekCount": len(weeks),
        "SourceRowCount": parsed["RowCount"],
        "CanonicalQuality": canonical["Quality"],
        "ScheduleWasEvaluated": schedule is not None,
        "ScheduleGraphFingerprint": canonical["ScheduleGraphFingerprint"],
        "Completeness": "observed-report-partitions-only",
    })
    target[f"data-derived/nfl-injuries/{season}.json"] = _render(derived)
    return dict(sorted(target.items()))


def classify_injury_artifacts(
    proposed: Mapping[str, bytes],
    existing: Mapping[str, bytes],
    *,
    season: int,
) -> dict[str, Any]:
    """Preview planned writes/no-ops and stale output candidates.

    We do not authorize removal: an obsolete partition is a blocking review
    finding, never an instruction to delete automatically.
    """
    if not isinstance(season, int) or isinstance(season, bool) or not 2012 <= season <= 2099:
        raise ValueError("Unsupported injury partition season")
    raw_prefix = "data-source/providers/nflverse/injuries/"
    canonical_prefix = f"data-source/nfl/injuries/{season}/"
    derived_path = f"data-derived/nfl-injuries/{season}.json"
    expected_raw = {f"{raw_prefix}raw-{season}.csv", f"{raw_prefix}metadata-{season}.json"}
    manifest_path = f"{canonical_prefix}manifest.json"

    def allowed(path: str) -> bool:
        if path in expected_raw or path in (manifest_path, derived_path):
            return True
        if not path.startswith(canonical_prefix):
            return False
        partition_name = path.removeprefix(canonical_prefix)
        if not re.fullmatch(r"(?:0[1-9]|1[0-9]|2[0-2])\.json", partition_name):
            return False
        return True
    for path, content in [*proposed.items(), *existing.items()]:
        if not isinstance(path, str) or not allowed(path):
            raise ValueError(f"Outside the selected injury product write scope: {path}")
        if not isinstance(content, bytes):
            raise TypeError(f"Artifact content must be bytes: {path}")
    required = expected_raw | {manifest_path, derived_path}
    missing = sorted(required - set(proposed))
    week_paths = [path for path in proposed
                  if path.startswith(canonical_prefix) and path != manifest_path]
    if missing or not week_paths:
        raise ValueError(f"Incomplete injury product plan: missing={missing}, weekPartitions={len(week_paths)}")
    changed = sorted(path for path, data in proposed.items()
                     if path in existing and existing[path] != data)
    new = sorted(set(proposed) - set(existing))
    unchanged = sorted(path for path, data in proposed.items()
                       if path in existing and existing[path] == data)
    obsolete = sorted(set(existing) - set(proposed))
    return {
        "SchemaVersion": 1,
        "Season": season,
        "SourceDataset": _DATASET,
        "New": new,
        "Changed": changed,
        "Unchanged": unchanged,
        "ObsoleteRequiresReview": obsolete,
        "RequiresWrites": bool(new or changed or obsolete),
        "CanAutoApply": not obsolete,
        "PublicationPerformed": False,
    }
