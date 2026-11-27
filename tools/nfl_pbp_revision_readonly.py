#!/usr/bin/env python3
"""Read-only 2025 nflverse PBP revision byte/stream preflight (Issue #1656).

Never publishes or changes accepted Source/Derived. Both releases are pinned by
asset identity and SHA-256; a provider refresh is an explicit failure, not an
implicit acceptance. Reports only source structure, not semantic play diffs.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any

from data_roots import DATA_SOURCE_ROOT

SEASON = 2025
MANIFEST = f"{DATA_SOURCE_ROOT}/providers/nflverse/play-by-play-original/metadata-2025.json"
ARCHIVED_SHA = "2f135887790a013fd004e609e37096bb4816d5cc80b9f19122e1bad478961978"
ARCHIVED_BYTES = 19105296
ARCHIVED_ASSET_ID = 756418144
PROVIDER_ASSET_ID = 760425249
PROVIDER_SHA = "5362b392d6421f4139e9f4a76daadfa72ba5769239c325a19299a633caa35f94"
PROVIDER_BYTES = 19580656
BASENAME = "play_by_play_2025.csv.gz"
PROVIDER_URL = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/{BASENAME}"
ARCHIVED_URL = (
    "https://github.com/Lolindhir/fantasy-app/releases/download/"
    f"nfl-pbp-source-2025-{ARCHIVED_SHA[:12]}/{BASENAME}"
)


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={
        "User-Agent": "fantasy-app-pbp-revision-audit/1",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=90) as stream:
        result = json.load(stream)
    if not isinstance(result, dict):
        raise ValueError("Invalid GitHub release asset metadata")
    return result


def validate_release_asset(asset: dict[str, Any], *, asset_id: int,
                           size: int, digest: str, url: str) -> None:
    if (asset.get("id") != asset_id or asset.get("name") != BASENAME
            or asset.get("size") != size
            or asset.get("digest") != f"sha256:{digest}"
            or asset.get("state") != "uploaded"
            or asset.get("browser_download_url") != url):
        raise ValueError(f"Release asset metadata changed: asset {asset_id}")


def validate_manifest(manifest: dict[str, Any]) -> None:
    if (manifest.get("SchemaVersion") != 1
            or manifest.get("Status") != "accepted-original-byte-identity"
            or manifest.get("Season") != SEASON
            or manifest.get("UpstreamSHA256") != ARCHIVED_SHA
            or manifest.get("CompressedBytes") != ARCHIVED_BYTES
            or manifest.get("ArchiveAssetID") != ARCHIVED_ASSET_ID
            or manifest.get("ArchiveURL") != ARCHIVED_URL
            or manifest.get("SourceCompletenessCertified") is not False):
        raise ValueError("Accepted frozen 2025 Source manifest does not match the pinned revision")


def _download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={
        "User-Agent": "fantasy-app-pbp-revision-audit/1",
    })
    with urllib.request.urlopen(request, timeout=120) as source, target.open("wb") as sink:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sink.write(chunk)


def inspect_gzip(path: Path, *, expected_sha: str, expected_bytes: int) -> dict[str, Any]:
    """Verify compressed identity, full gzip CRC/EOF, CSV header and row widths.

    The compressed SHA cannot attest GZIP correctness. A full read through
    gzip.GzipFile additionally validates trailer CRC and uncompressed size.
    The second streaming pass checks CSV parseability to the physical EOF.
    """
    if (not re.fullmatch(r"[0-9a-f]{64}", expected_sha)
            or type(expected_bytes) is not int or expected_bytes <= 0):
        raise ValueError("Invalid pinned original PBP hash or size")
    if path.stat().st_size != expected_bytes:
        raise ValueError("Compressed original PBP byte length does not match pin")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        raise ValueError("Original PBP compressed SHA-256 does not match pin")
    plain = hashlib.sha256()
    plain_bytes = 0
    with gzip.open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            plain.update(chunk)
            plain_bytes += len(chunk)
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        columns = next(reader, [])
        if (not columns or any(not name for name in columns)
                or len(set(columns)) != len(columns)):
            raise ValueError("Original PBP CSV has missing/duplicate header columns")
        rows = 0
        for row in reader:
            if len(row) != len(columns):
                raise ValueError(f"Original PBP CSV row {reader.line_num} has invalid width")
            rows += 1
    if rows == 0:
        raise ValueError("Original PBP CSV has no rows")
    return {
        "CompressedSHA256": expected_sha,
        "CompressedBytes": expected_bytes,
        "GzipStreamReadToEOF": True,
        "UncompressedSHA256": plain.hexdigest(),
        "UncompressedBytes": plain_bytes,
        "SourceRows": rows,
        "CSVColumns": len(columns),
    }


def compare_files(accepted: Path, official: Path) -> dict[str, Any]:
    old = inspect_gzip(accepted, expected_sha=ARCHIVED_SHA, expected_bytes=ARCHIVED_BYTES)
    new = inspect_gzip(official, expected_sha=PROVIDER_SHA, expected_bytes=PROVIDER_BYTES)
    return {
        "SchemaVersion": 1,
        "Status": "read-only-original-streams-verified",
        "Season": SEASON,
        "Accepted": old,
        "OfficialRevision": new,
        "DecompressedCSVBytesIdentical": old["UncompressedSHA256"] == new["UncompressedSHA256"],
        "SameRowCount": old["SourceRows"] == new["SourceRows"],
        "SameColumnCount": old["CSVColumns"] == new["CSVColumns"],
        "SemanticRowOrMetricDiffCertified": False,
        "ProductionSourceChanged": False,
    }


def run(repo: Path, *, accepted_file: Path | None = None,
        revision_file: Path | None = None) -> dict[str, Any]:
    manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Invalid 2025 Source manifest structure")
    validate_manifest(manifest)
    if (accepted_file is None) != (revision_file is None):
        raise ValueError("Pass both local original files, or neither")
    if accepted_file is not None and revision_file is not None:
        return compare_files(accepted_file, revision_file)
    old_metadata = _get_json(
        f"https://api.github.com/repos/Lolindhir/fantasy-app/releases/assets/{ARCHIVED_ASSET_ID}")
    validate_release_asset(old_metadata, asset_id=ARCHIVED_ASSET_ID,
                           size=ARCHIVED_BYTES, digest=ARCHIVED_SHA, url=ARCHIVED_URL)
    new_metadata = _get_json(
        f"https://api.github.com/repos/nflverse/nflverse-data/releases/assets/{PROVIDER_ASSET_ID}")
    validate_release_asset(new_metadata, asset_id=PROVIDER_ASSET_ID,
                           size=PROVIDER_BYTES, digest=PROVIDER_SHA, url=PROVIDER_URL)
    with tempfile.TemporaryDirectory(prefix="nfl-pbp-revision-readonly-") as folder:
        original = Path(folder) / "accepted.csv.gz"
        revision = Path(folder) / "revision.csv.gz"
        _download(ARCHIVED_URL, original)
        _download(PROVIDER_URL, revision)
        return compare_files(original, revision)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--accepted-file", type=Path)
    parser.add_argument("--revision-file", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.repo_root, accepted_file=args.accepted_file,
                     revision_file=args.revision_file)
    except (OSError, ValueError, TypeError, KeyError, EOFError, csv.Error,
            UnicodeError, urllib.error.URLError) as error:
        print(f"PBP_2025_REVISION_ERROR={error}", file=sys.stderr)
        return 1
    print("PBP_2025_REVISION_REPORT_JSON=" + json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
