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


def build_injury_artifacts(
    *,
    season: int,
    source_csv: bytes,
    players: dict[str, Any],
    schedule: dict[str, Any] | None = None,
    expected_source_sha256: str | None = None,
) -> dict[str, bytes]:
    """Generate intended bytes, never write them to disk.

    The returned paths are prospective and do not imply producer activation.
    Source original-asset verification is distinct from merely hashing bytes.
    """
    actual_digest = _sha256(source_csv)
    if expected_source_sha256 is not None:
        expected = expected_source_sha256.lower().removeprefix("sha256:")
        if not _SHA256.fullmatch(expected):
            raise ValueError("Expected injury source digest must be SHA-256 hex")
        if actual_digest != expected:
            raise ValueError("Injury source digest does not match expected asset")
    parsed = parse_injury_report_csv(source_csv, season=season)
    if not parsed["Rows"]:
        raise ValueError("Empty injury report is not evidence of a healthy or complete season")
    canonical = canonicalize_injury_reports(parsed, players, schedule=schedule)
    derived = derive_nfl_injuries(canonical)
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
            "matched-expected-digest" if expected_source_sha256 else "self-hash-only-not-officially-verified"
        ),
        "ReportRowCount": parsed["RowCount"],
        "SourceSchema": parsed["SourceSchema"],
        "OriginalAssetBytesRetained": True,
        "SnapshotSemantics": "retrospective-asset-revision-not-prekickoff",
    })
    weeks: list[int] = []
    for partition in canonical["Partitions"]:
        week = partition["Week"]
        weeks.append(week)
        path = f"data-source/nfl/injuries/{season}/{week:02d}.json"
        target[path] = _render(partition)
    target[f"data-source/nfl/injuries/{season}/manifest.json"] = _render({
        "SchemaVersion": 1,
        "SourceDataset": _DATASET,
        "Season": season,
        "SourceAssetSha256": actual_digest,
        "IdentityGraphFingerprint": canonical["IdentityGraphFingerprint"],
        "IdentityTimeBasis": "current-graph-not-historical-point-in-time",
        "ObservedWeeks": weeks,
        "ObservedWeekCount": len(weeks),
        "SourceRowCount": parsed["RowCount"],
        "CanonicalQuality": canonical["Quality"],
        "ScheduleWasEvaluated": schedule is not None,
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
    if not isinstance(season, int) or isinstance(season, bool) or not 2012 <= season <= 2026:
        raise ValueError("Unsupported injury partition season")
    raw_prefix = "data-source/providers/nflverse/injuries/"
    canonical_prefix = f"data-source/nfl/injuries/{season}/"
    derived_path = f"data-derived/nfl-injuries/{season}.json"
    expected_raw = {f"{raw_prefix}raw-{season}.csv", f"{raw_prefix}metadata-{season}.json"}
    allowed = lambda p: p in expected_raw or p.startswith(canonical_prefix) or p == derived_path
    for path, content in [*proposed.items(), *existing.items()]:
        if not isinstance(path, str) or not allowed(path):
            raise ValueError(f"Outside the selected injury product write scope: {path}")
        if not isinstance(content, bytes):
            raise TypeError(f"Artifact content must be bytes: {path}")
    if not proposed:
        raise ValueError("Cannot publish a product without any output artifacts")
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
