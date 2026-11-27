#!/usr/bin/env python3
"""Automatically retain current-season nflverse original PBP in the existing NFL Source job.

The *current* season follows authoritative Source-season discovery, not a
hard-coded calendar year. Each accepted upstream revision is immutable in a
digest-addressed GitHub Release. Only the per-season Source manifest pointer
advances after an exact provider-digest and Source game/play identity audit.
The diagnostic team-metric/PlayerStats replay is downstream, not a Source gate.

Frozen seasons and accepted originals are never deleted or overwritten. No new
workflow, branch writer, schedule, credential, or Derived write scope.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import current_source_season, download, load_json, write_json_if_changed
from nfl_source_data_lib.pbp_original import audit_original_pbp

_SOURCE_REPOSITORY = "nflverse/nflverse-data"
_PBP_RELEASE = "pbp"
_DEST_REPOSITORY = "Lolindhir/fantasy-app"
_SOURCE_MANIFEST_DIR = Path(
    f"{DATA_SOURCE_ROOT}/providers/nflverse/play-by-play-original"
)
_SHA = re.compile(r"^sha256:([0-9a-f]{64})$")

def api_json(
    url: str, token: str, *, method: str = "GET",
    body: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fantasy-app-nfl-pbp-season-archive/1",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def upstream_asset(token: str, season: int) -> dict[str, Any] | None:
    """Inspect the official release asset inventory; no guessed asset IDs."""
    release = api_json(
        f"https://api.github.com/repos/{_SOURCE_REPOSITORY}/releases/tags/{_PBP_RELEASE}",
        token,
    )
    if not isinstance(release, dict) or type(release.get("id")) is not int:
        raise ValueError("Official nflverse PBP release identity unavailable")
    asset_name = f"play_by_play_{season}.csv.gz"
    matches = []
    for page in range(1, 21):
        assets = api_json(
            f"https://api.github.com/repos/{_SOURCE_REPOSITORY}/releases/"
            f"{release['id']}/assets?per_page=100&page={page}",
            token,
        )
        if not isinstance(assets, list):
            raise ValueError("Official nflverse release asset inventory malformed")
        matches.extend(x for x in assets if x.get("name") == asset_name)
        if len(assets) < 100:
            break
    else:
        raise ValueError("Official nflverse release asset inventory pagination exceeded")
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Duplicate official nflverse PBP asset")
    asset = matches[0]
    source_url = (
        f"https://github.com/{_SOURCE_REPOSITORY}/releases/download/"
        f"{_PBP_RELEASE}/{asset_name}"
    )
    digest = asset.get("digest")
    if (type(asset.get("id")) is not int or type(asset.get("size")) is not int
            or asset["size"] <= 0 or not isinstance(digest, str)
            or not _SHA.fullmatch(digest)
            or asset.get("browser_download_url") != source_url
            or asset.get("state") != "uploaded"):
        raise ValueError(f"Official PBP source asset lacks trusted identity/SHA256: {season}")
    return asset


def _archive_tag(season: int, sha: str) -> str:
    return f"nfl-pbp-source-{season}-{sha[:12]}"


def _archive_name(season: int) -> str:
    return f"play_by_play_{season}.csv.gz"


def _archive_url(season: int, sha: str) -> str:
    return (
        f"https://github.com/{_DEST_REPOSITORY}/releases/download/"
        f"{_archive_tag(season, sha)}/{_archive_name(season)}"
    )


def _get_release(token: str, season: int, sha: str) -> dict[str, Any] | None:
    url = (
        f"https://api.github.com/repos/{_DEST_REPOSITORY}/releases/tags/"
        f"{_archive_tag(season, sha)}"
    )
    try:
        return api_json(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _release_asset(release: dict[str, Any] | None, season: int) -> dict[str, Any] | None:
    matches = [
        x for x in (release or {}).get("assets", [])
        if x.get("name") == _archive_name(season)
    ]
    if len(matches) > 1:
        raise ValueError("Duplicate immutable PBP archive asset")
    return matches[0] if matches else None


def _verify_archive(asset: dict[str, Any], season: int, sha: str, size: int) -> None:
    if (asset.get("name") != _archive_name(season)
            or asset.get("size") != size
            or asset.get("digest") != f"sha256:{sha}"
            or asset.get("browser_download_url") != _archive_url(season, sha)
            or asset.get("state") != "uploaded"):
        raise ValueError(f"Immutable original PBP archive identity does not match: {season}")


def _create_release(token: str, season: int, sha: str, source_url: str) -> dict[str, Any]:
    return api_json(
        f"https://api.github.com/repos/{_DEST_REPOSITORY}/releases",
        token, method="POST",
        body={
            "tag_name": _archive_tag(season, sha),
            "target_commitish": "main",
            "name": f"Source evidence: nflverse original PBP {season} {sha[:12]}",
            "body": (
                "Unmodified nflverse play-by-play original gzip.\n"
                f"Source: {source_url}\n"
                "License CC BY 4.0. Attribution: nflverse play-by-play data.\n"
                f"SHA256: {sha}\n"
                "An observed candidate, not an upstream completeness certificate."
            ),
            "draft": False,
            "prerelease": True,
            "make_latest": "false",
        },
    )


def _upload(
    token: str, release: dict[str, Any], original: Path,
    season: int, sha: str, size: int,
) -> dict[str, Any]:
    upload_base = str(release.get("upload_url") or "").split("{", 1)[0]
    if not upload_base.startswith(
        f"https://uploads.github.com/repos/{_DEST_REPOSITORY}/releases/"
    ):
        raise ValueError("Unexpected original PBP GitHub upload endpoint")
    url = upload_base + "?name=" + urllib.parse.quote(_archive_name(season))
    request = urllib.request.Request(
        url, data=original.read_bytes(), method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/gzip",
            "User-Agent": "fantasy-app-nfl-pbp-season-archive/1",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        asset = json.load(response)
    _verify_archive(asset, season, sha, size)
    return asset


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _audit(root: Path, season: int, original: Path, sha: str) -> dict[str, Any]:
    """Source-only acceptance: no Derived index or future PlayerStats dependency."""
    return audit_original_pbp(root, season, original, sha)


def run(root: Path, repository: str, token: str, *, season: int | None = None) -> dict[str, Any]:
    """Accept and update current-season snapshots only. Prior seasons stay frozen."""
    if repository != _DEST_REPOSITORY or not token:
        raise ValueError("Missing authorized existing repository or Source token")
    current = current_source_season(root)
    target = current if season is None else season
    if type(target) is not int or target != current or not 1999 <= target <= 2100:
        raise ValueError("Live PBP auto-acceptance is allowed for current Source season only")
    manifest_path = root / _SOURCE_MANIFEST_DIR / f"metadata-{target}.json"
    previous = load_json(manifest_path)
    if previous is not None and (
        previous.get("Status") != "accepted-original-byte-identity"
        or previous.get("Season") != target
        or not isinstance(previous.get("UpstreamSHA256"), str)
        or not re.fullmatch("[0-9a-f]{64}", previous["UpstreamSHA256"])
        or type(previous.get("CompressedBytes")) is not int
        or previous.get("ArchiveURL") != _archive_url(target, previous["UpstreamSHA256"])
    ):
        raise ValueError("Previously accepted current-season PBP manifest is inconsistent")

    # Never suppress a corrupt/missing accepted archive as an ordinary no-op.
    if previous is not None:
        archived = _release_asset(
            _get_release(token, target, previous["UpstreamSHA256"]), target,
        )
        if archived is None:
            raise ValueError("Previously accepted current-season PBP archive is missing")
        _verify_archive(archived, target, previous["UpstreamSHA256"],
                        previous["CompressedBytes"])

    upstream = upstream_asset(token, target)
    if upstream is None:
        if previous is not None:
            raise ValueError("Official current-season PBP asset disappeared")
        return {"Status": "upstream-season-not-released", "Season": target, "Changed": False}
    source_sha = _SHA.fullmatch(upstream["digest"]).group(1)
    size = upstream["size"]
    if previous is not None and previous["UpstreamSHA256"] == source_sha:
        if previous["CompressedBytes"] != size:
            raise ValueError("Official unchanged digest has changed byte size")
        return {"Status": "original-current-noop", "Season": target, "Changed": False,
                "AcceptedSHA256": source_sha}
    source_url = upstream["browser_download_url"]
    with tempfile.TemporaryDirectory(prefix=f"nfl-pbp-current-{target}-") as tmp:
        original = Path(tmp) / _archive_name(target)
        download(source_url, original)
        if original.stat().st_size != size or _sha(original) != source_sha:
            raise ValueError("Original PBP does not match official asset SHA256/size")
        evidence = _audit(root, target, original, source_sha)
        # Stop an accidental near-empty reset, not legitimate row corrections.
        if previous is not None:
            old_rows = (previous.get("Audit") or {}).get("SourceRowCount")
            if type(old_rows) is int and evidence["SourceRowCount"] < old_rows // 2:
                raise ValueError("Current PBP season lost over half its source rows")
        release = _get_release(token, target, source_sha)
        if release is None:
            release = _create_release(token, target, source_sha, source_url)
        asset = _release_asset(release, target)
        if asset is None:
            asset = _upload(token, release, original, target, source_sha, size)
        _verify_archive(asset, target, source_sha, size)
        metadata = {
            "SchemaVersion": 1,
            "Status": "accepted-original-byte-identity",
            "Provider": "nflverse",
            "Dataset": "nflverse.play-by-play-original",
            "Season": target,
            "SourceURL": source_url,
            "SourceAssetID": upstream["id"],
            "SourceAssetUpdatedAtUtc": upstream.get("updated_at"),
            "UpstreamSHA256": source_sha,
            "CompressedBytes": size,
            "License": "CC BY 4.0",
            "Attribution": "nflverse play-by-play data",
            "ReleaseRepository": repository,
            "ReleaseTag": _archive_tag(target, source_sha),
            "ArchiveAssetID": asset["id"],
            "ArchiveURL": _archive_url(target, source_sha),
            "Audit": evidence,
            "SourceCompletenessCertified": False,
            "SnapshotRevision": 1 + (previous.get("SnapshotRevision", 1) if previous else 0),
            "PreviousAcceptedSHA256": previous["UpstreamSHA256"] if previous else None,
            "StoredAtUtc": datetime.now(timezone.utc).replace(
                microsecond=0,
            ).isoformat().replace("+00:00", "Z"),
        }
        changed = write_json_if_changed(manifest_path, metadata)
        return {
            "Status": "original-current-accepted",
            "Season": target,
            "Changed": changed,
            "AcceptedSHA256": source_sha,
            "SourceRowCount": evidence["SourceRowCount"],
            "ObservedGameIDs": evidence["ObservedGameIDs"],
            "SnapshotRevision": metadata["SnapshotRevision"],
        }


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
    except (
        OSError, ValueError, KeyError, TypeError, urllib.error.URLError,
        EOFError, json.JSONDecodeError,
    ) as exc:
        print(f"nfl_pbp_source_auto failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
