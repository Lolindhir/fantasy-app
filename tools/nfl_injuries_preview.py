#!/usr/bin/env python3
"""Offline-only preview of the proposed historical NFL Injury Data Product.

Reads explicitly supplied input files. Never fetches, caches, writes to the
repository, updates Source Registry, or publishes Source/Derived/App data.
This is NOT a production materializer (Issue #1421).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from nfl_source_data_lib.injury_reports import parse_injury_report_csv
from nfl_source_data_lib.injury_canonical import canonicalize_injury_reports
from derived_data_lib.nfl_injuries import derive_nfl_injuries
from nfl_source_data_lib.injury_product_plan import build_injury_artifacts, classify_injury_artifacts


def preview(
    *,
    csv_bytes: bytes,
    season: int,
    identities: dict,
    schedule: dict | None = None,
    expected_sha256: str | None = None,
    mode: str = "summary",
) -> dict:
    digest = hashlib.sha256(csv_bytes).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError(f"Source CSV SHA-256 mismatch: actual={digest}, expected={expected_sha256}")
    parsed = parse_injury_report_csv(csv_bytes, season=season)
    canonical = canonicalize_injury_reports(parsed, identities, schedule=schedule)
    derived = derive_nfl_injuries(canonical)
    provenance = {
        "InputVerification": "matched-provided-sha256" if expected_sha256 else "not-independently-verified",
        "SourceAssetSha256": digest,
        "HistoricalPointInTimeProof": False,
        "PublicationEnabled": False,
    }
    if mode == "canonical":
        return {"PreviewOnly": True, "Provenance": provenance, "Canonical": canonical}
    if mode == "derived":
        return {"PreviewOnly": True, "Provenance": provenance, "Derived": derived}
    if mode != "summary":
        raise ValueError("Preview mode must be summary, canonical or derived")
    return {
        "PreviewOnly": True,
        "Provenance": provenance,
        "Product": derived["Product"],
        "ProductVersion": derived["ProductVersion"],
        "Season": season,
        "SourceQuality": canonical["Quality"],
        "DerivedQuality": derived["Quality"],
        "SamplePlayerWeeks": derived["ObservedPlayerWeeks"][:3],
        "SampleTrajectories": derived["ObservedReasonTrajectories"][:3],
        "Interpretation": {
            "MissingReports": derived["MissingReportMeaning"],
            "TemporalEvidence": derived["TemporalEvidence"],
            "NoGamesMissedOrHealthyInference": True,
        },
    }


def plan_preview(
    *,
    csv_bytes: bytes,
    season: int,
    identities: dict,
    schedule: dict | None = None,
    expected_sha256: str | None = None,
    compare_root: Path | None = None,
) -> dict:
    """Read-only proposed Source/Canonical/Derived outputs and exact no-op diff."""
    artifacts = build_injury_artifacts(
        season=season, source_csv=csv_bytes, players=identities,
        schedule=schedule, expected_source_sha256=expected_sha256,
    )
    existing: dict[str, bytes] = {}
    if compare_root is not None:
        for relative in artifacts:
            candidate = compare_root / relative
            if candidate.is_file():
                existing[relative] = candidate.read_bytes()
        # An upstream correction can remove an entire previously observed week.
        # Expose it as a blocking candidate; NEVER silently delete it.
        folder = compare_root / f"{DATA_SOURCE_ROOT}/nfl/injuries/{season}"
        for week in range(1, 23):
            relative = f"{DATA_SOURCE_ROOT}/nfl/injuries/{season}/{week:02d}.json"
            candidate = folder / f"{week:02d}.json"
            if relative not in artifacts and candidate.is_file():
                existing[relative] = candidate.read_bytes()
    change_set = classify_injury_artifacts(artifacts, existing, season=season)
    return {
        "PreviewOnly": True,
        "PublicationEnabled": False,
        "SourceAssetSha256": hashlib.sha256(csv_bytes).hexdigest(),
        "SourceDigestVerifiedAgainstProvidedValue": expected_sha256 is not None,
        "ComparisonBasis": "provided-existing-root" if compare_root else "empty-preview-baseline",
        "ProductVersion": "nfl-injuries-v1",
        "PlannedArtifacts": [
            {"Path": path, "Bytes": len(value),
             "Sha256": hashlib.sha256(value).hexdigest()}
            for path, value in artifacts.items()
        ],
        "ChangeSet": change_set,
        "RawMetadata": json.loads(
            artifacts[f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/metadata-{season}.json"]
        ),
        "CanonicalManifest": json.loads(
            artifacts[f"{DATA_SOURCE_ROOT}/nfl/injuries/{season}/manifest.json"]
        ),
        "DerivedQuality": json.loads(
            artifacts[f"{DATA_DERIVED_ROOT}/nfl-injuries/{season}.json"]
        )["Quality"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--csv", type=Path, required=True, help="Existing local original-style season CSV")
    parser.add_argument("--identities", type=Path, required=True, help="Canonical players.json")
    parser.add_argument("--schedule", type=Path, help="Optional canonical NFL schedule season JSON")
    parser.add_argument("--expected-sha256", help="Expected source digest from separately verified origin")
    parser.add_argument("--mode", choices=("summary", "canonical", "derived", "plan"), default="summary")
    parser.add_argument("--compare-root", type=Path, help="Optional local existing-output tree (read-only)")
    args = parser.parse_args()
    identities = json.loads(args.identities.read_text(encoding="utf-8"))
    schedule = json.loads(args.schedule.read_text(encoding="utf-8")) if args.schedule else None
    if args.mode == "plan":
        payload = plan_preview(
            csv_bytes=args.csv.read_bytes(), season=args.season, identities=identities,
            schedule=schedule, expected_sha256=args.expected_sha256,
            compare_root=args.compare_root,
        )
    else:
        if args.compare_root is not None:
            parser.error("--compare-root is only valid with --mode plan")
        payload = preview(
            csv_bytes=args.csv.read_bytes(), season=args.season, identities=identities,
            schedule=schedule, expected_sha256=args.expected_sha256, mode=args.mode,
        )
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
