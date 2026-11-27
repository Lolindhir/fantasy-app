#!/usr/bin/env python3
"""Issue #1077: persist an accepted original nflverse PBP season as immutable Source evidence.

2025-only pilot. Called by the EXISTING NFL Source publisher; not a new scheduler
or writer. Large immutable gzip bytes live in a versioned GitHub Release asset,
not in the git history. A small Source manifest is committed by the existing
data-source/providers raw publisher after byte, identity and research audits.
No GameDetail/PBP metric publication occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from nfl_source_data_lib.common import download, load_json, write_json_if_changed

PILOT_SEASON = 2025
UPSTREAM_ASSET_ID = 512957609
EXPECTED_SHA256 = "2f135887790a013fd004e609e37096bb4816d5cc80b9f19122e1bad478961978"
EXPECTED_SIZE = 19105296
EXPECTED_ROWS = 48771
SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.csv.gz"
SOURCE_METADATA_URL = (
    "https://api.github.com/repos/nflverse/nflverse-data/releases/assets/512957609"
)
ARCHIVE_TAG = f"nfl-pbp-source-{PILOT_SEASON}-{EXPECTED_SHA256[:12]}"
ARCHIVE_NAME = f"play_by_play_{PILOT_SEASON}.csv.gz"
MANIFEST_PATH = (
    f"{DATA_SOURCE_ROOT}/providers/nflverse/play-by-play-original/metadata-{PILOT_SEASON}.json"
)
REQUIRED_METRICS = frozenset((
    "offensive_dropbacks_faced", "pass_attempts_faced", "rush_attempts_faced",
    "dropback_epa_per_play_allowed", "pass_epa_per_attempt_allowed",
    "rush_epa_per_play_allowed", "dropback_success_rate_allowed",
    "rush_success_rate_allowed", "pass_explosive_20_rate_allowed",
    "rush_explosive_10_rate_allowed",
))


def api_json(
    url: str, token: str, *, method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "fantasy-app-nfl-source-pbp-archive/1",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def get_release(repository: str, token: str) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{repository}/releases/tags/{ARCHIVE_TAG}"
    try:
        return api_json(url, token)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def get_asset(release: dict[str, Any] | None) -> dict[str, Any] | None:
    matches = [
        item for item in (release or {}).get("assets", [])
        if item.get("name") == ARCHIVE_NAME
    ]
    if len(matches) > 1:
        raise ValueError("Duplicate immutable original PBP release assets")
    return matches[0] if matches else None


def verify_asset(asset: dict[str, Any]) -> None:
    if (asset.get("size") != EXPECTED_SIZE
            or asset.get("digest") != f"sha256:{EXPECTED_SHA256}"
            or asset.get("state") != "uploaded"):
        raise ValueError("Published PBP release asset digest/size/status mismatch")


def upstream_evidence(token: str) -> dict[str, Any]:
    evidence = api_json(SOURCE_METADATA_URL, token)
    if (evidence.get("id") != UPSTREAM_ASSET_ID
            or evidence.get("name") != ARCHIVE_NAME
            or evidence.get("browser_download_url") != SOURCE_URL):
        raise ValueError("Official upstream nflverse PBP asset identity changed")
    return evidence


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audited_json(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, timeout=480,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            f"Read-only PBP source audit failed ({command[1]}): "
            + completed.stderr[-3000:]
        )
    return json.loads(completed.stdout)


def read_only_audits(root: Path, original: Path) -> dict[str, Any]:
    base = [sys.executable]
    source = audited_json(base + [
        "tools/nfl_pbp_metric_field_audit.py",
        "--season", str(PILOT_SEASON),
        "--pbp-csv-gz", str(original),
        "--expected-sha256", EXPECTED_SHA256,
        "--game-index-json", f"{DATA_DERIVED_ROOT}/nfl-games/2025.json",
    ], root)
    if (source.get("SourceAssetSHA256") != EXPECTED_SHA256
            or source.get("RawSeasonRowCount") != EXPECTED_ROWS
            or not source.get("GzipStreamReadToEOF")):
        raise ValueError("Original PBP header/byte/EOF/row-count audit not accepted")
    game_join = source.get("CanonicalGameContextReconciliation") or {}
    if (not game_join.get("AllObservedSourceRowsJoinCanonicalGames")
            or game_join.get("UnknownGameIDRows")
            or game_join.get("MismatchedContextRows")):
        raise ValueError("Original PBP game-context identity audit failed")
    metrics = audited_json(base + [
        "tools/nfl_pbp_team_metric_reconcile.py",
        "--season", str(PILOT_SEASON),
        "--pbp-csv-gz", str(original),
        "--expected-sha256", EXPECTED_SHA256,
    ], root)
    if (metrics.get("PBPAssetSHA256") != EXPECTED_SHA256
            or metrics.get("PBPSourceRowsScanned") != EXPECTED_ROWS):
        raise ValueError("Original PBP metric replay does not match pinned Source")
    if not REQUIRED_METRICS.issubset(set(metrics.get("TeamOnlyMetricCandidateIDs") or [])):
        raise ValueError("Missing prioritized ten research metric candidates")
    # Audits explicitly do not certify upstream completeness, nor approve metrics.
    return {
        "SourceRowCount": source["RawSeasonRowCount"],
        "ObservedGameIDs": source["DistinctGameIDs"],
        "OriginalColumnCount": source["CsvColumnCount"],
        "UnmatchedCanonicalGameRows": (
            game_join.get("UnknownGameIDRows", 0)
            + game_join.get("MismatchedContextRows", 0)
        ),
        "PBPMetricCandidateCount": len(metrics["TeamOnlyMetricCandidateIDs"]),
        "PBPMetricMVPCount": len(REQUIRED_METRICS),
        "PBPMetricValidationStatus": "research-only-not-certified-full-source",
        "UpstreamFullGameCompletenessVerified": False,
    }


def create_release(repository: str, token: str) -> dict[str, Any]:
    return api_json(
        f"https://api.github.com/repos/{repository}/releases", token,
        method="POST",
        body={
            "tag_name": ARCHIVE_TAG,
            "target_commitish": "main",
            "name": f"Source evidence: nflverse original PBP {PILOT_SEASON}",
            "body": (
                "Exact original nflverse play-by-play release bytes, unmodified.\n\n"
                f"Original: {SOURCE_URL}\n"
                "Provider: nflverse/nflverse-data; license CC BY 4.0; "
                "attribution: nflverse play-by-play data.\n"
                f"Original SHA256: {EXPECTED_SHA256}\n\n"
                "Not a published Fantasy analysis or completeness certification."
            ),
            "draft": False,
            "prerelease": True,
            "make_latest": "false",
        },
    )


def upload_asset(
    repository: str, release: dict[str, Any], original: Path, token: str,
) -> dict[str, Any]:
    # GitHub Releases are immutable by source digest; never clobber an asset.
    upload_base = release.get("upload_url", "").split("{", 1)[0]
    if not upload_base.startswith(
        f"https://uploads.github.com/repos/{repository}/releases/"
    ):
        raise ValueError("Unexpected GitHub Releases upload destination")
    url = upload_base + "?name=" + urllib.parse.quote(ARCHIVE_NAME)
    request = urllib.request.Request(
        url,
        data=original.read_bytes(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/gzip",
            "User-Agent": "fantasy-app-nfl-source-pbp-archive/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        uploaded = json.load(response)
    verify_asset(uploaded)
    return uploaded


def run(root: Path, repository: str, token: str, *, weekday: int | None = None) -> dict[str, Any]:
    """2025 pilot only; no-op on accepted unchanged original, weekly revision check."""
    if not token:
        raise ValueError("Missing existing GitHub Actions contents:write token")
    if "/" not in repository or repository != "Lolindhir/fantasy-app":
        raise ValueError("Unexpected target source-evidence repository")
    manifest_path = root / MANIFEST_PATH
    existing = load_json(manifest_path)
    if existing is not None:
        if (existing.get("UpstreamSHA256") != EXPECTED_SHA256
                or existing.get("ReleaseTag") != ARCHIVE_TAG
                or existing.get("Status") != "accepted-original-byte-identity"):
            raise ValueError("Previously accepted original PBP manifest is inconsistent")
        release = get_release(repository, token)
        asset = get_asset(release)
        if asset is None:
            raise ValueError("Persisted PBP manifest points to missing release asset")
        verify_asset(asset)
        if weekday is None:
            weekday = datetime.now(timezone.utc).weekday()
        if weekday == 0:
            upstream = upstream_evidence(token)
            if (upstream.get("digest") != f"sha256:{EXPECTED_SHA256}"
                    or upstream.get("size") != EXPECTED_SIZE):
                # Preserve frozen accepted history; do not silently replace.
                return {"Status": "upstream-revision-review-required", "Changed": False}
        return {"Status": "already-archived-verified-noop", "Changed": False}

    upstream = upstream_evidence(token)
    if (upstream.get("digest") != f"sha256:{EXPECTED_SHA256}"
            or upstream.get("size") != EXPECTED_SIZE):
        raise ValueError("Expected nflverse 2025 original changed; separate repair review")
    with tempfile.TemporaryDirectory(prefix="nfl-pbp-source-2025-") as temporary:
        original = Path(temporary) / ARCHIVE_NAME
        download(SOURCE_URL, original)
        if original.stat().st_size != EXPECTED_SIZE or sha256(original) != EXPECTED_SHA256:
            raise ValueError("Downloaded original PBP does not match official SHA256/size")
        audit = read_only_audits(root, original)
        release = get_release(repository, token)
        if release is None:
            release = create_release(repository, token)
        asset = get_asset(release)
        if asset is None:
            asset = upload_asset(repository, release, original, token)
        verify_asset(asset)
        metadata = {
            "SchemaVersion": 1,
            "Status": "accepted-original-byte-identity",
            "Provider": "nflverse",
            "Dataset": "nflverse.play-by-play-original",
            "Season": PILOT_SEASON,
            "SourceURL": SOURCE_URL,
            "SourceAssetID": UPSTREAM_ASSET_ID,
            "UpstreamSHA256": EXPECTED_SHA256,
            "CompressedBytes": EXPECTED_SIZE,
            "License": "CC BY 4.0",
            "Attribution": "nflverse play-by-play data",
            "ReleaseRepository": repository,
            "ReleaseTag": ARCHIVE_TAG,
            "ArchiveAssetID": asset["id"],
            "ArchiveURL": asset["browser_download_url"],
            "Audit": audit,
            "StoredAtUtc": datetime.now(timezone.utc).replace(
                microsecond=0
            ).isoformat().replace("+00:00", "Z"),
            "SourceCompletenessCertified": False,
            "GameDetailV2Published": False,
        }
        changed = write_json_if_changed(manifest_path, metadata)
        return {"Status": "original-archived-audited", "Changed": changed, "Audit": audit}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    try:
        result = run(
            args.repo_root.resolve(), args.repository,
            os.environ.get("PBP_ARCHIVE_TOKEN", ""),
        )
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError,
            subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"nfl_pbp_source_archive failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
