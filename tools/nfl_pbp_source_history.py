#!/usr/bin/env python3
"""Reconcile original historical nflverse PBP in the existing NFL Source writer.

No own scheduler, branch publisher or Derived reads. Discover source-backed seasons
from the canonical Source schedules and official upstream release asset inventory.
Frozen accepted originals are audited by identity, never replaced on revision.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
from typing import Any, Mapping

from nfl_source_data_lib.common import current_source_season, download, load_json, write_json_if_changed
from nfl_pbp_source_auto import (
    _DEST_REPOSITORY, _PBP_RELEASE, _SOURCE_REPOSITORY, _SOURCE_MANIFEST_DIR,
    _archive_name, _archive_tag, _archive_url, _audit, _create_release,
    _get_release, _release_asset, _sha, _upload, _verify_archive, api_json,
)

_ASSET = re.compile(r"^play_by_play_(\d{4})\.csv\.gz$")
_SHA = re.compile(r"^sha256:([0-9a-f]{64})$")
_MANIFEST = re.compile(r"^metadata-(\d{4})\.json$")


def official_inventory(token: str) -> dict[int, dict[str, Any]]:
    """List all asset pages once; validate exact year/name, size and identity."""
    release = api_json(
        f"https://api.github.com/repos/{_SOURCE_REPOSITORY}/releases/tags/{_PBP_RELEASE}",
        token,
    )
    if not isinstance(release, dict) or type(release.get("id")) is not int:
        raise ValueError("Official PBP release identity unavailable")
    found: dict[int, dict[str, Any]] = {}
    for page in range(1, 21):
        assets = api_json(
            f"https://api.github.com/repos/{_SOURCE_REPOSITORY}/releases/"
            f"{release['id']}/assets?per_page=100&page={page}", token,
        )
        if not isinstance(assets, list):
            raise ValueError("Malformed official PBP asset inventory")
        for asset in assets:
            name = str(asset.get("name") or "")
            match = _ASSET.fullmatch(name)
            if match is None:
                continue
            year = int(match.group(1))
            url = (
                f"https://github.com/{_SOURCE_REPOSITORY}/releases/download/"
                f"{_PBP_RELEASE}/{name}"
            )
            digest = asset.get("digest")
            if (year in found or type(asset.get("id")) is not int
                    or type(asset.get("size")) is not int or asset["size"] <= 0
                    or asset.get("browser_download_url") != url
                    or asset.get("state") != "uploaded"
                    or (digest is not None and not (
                        isinstance(digest, str) and _SHA.fullmatch(digest)
                    ))):
                raise ValueError(f"Invalid/duplicate official original PBP asset: {year}")
            found[year] = asset
        if len(assets) < 100:
            break
    else:
        raise ValueError("Official PBP asset inventory pagination exceeded")
    return found


def source_seasons(root: Path) -> list[int]:
    directory = root / "data-source/nfl/schedules"
    if not directory.is_dir():
        raise ValueError("Canonical Source schedule directory missing")
    seasons = sorted(int(path.stem) for path in directory.glob("[12][0-9][0-9][0-9].json"))
    if not seasons:
        raise ValueError("No canonical Source seasons")
    return seasons


def _accepted_sha(manifest: Mapping[str, Any], year: int) -> str:
    """Legacy manifests have provider SHA; a digestless asset has self-hash."""
    value = manifest.get("OriginalSHA256") or manifest.get("UpstreamSHA256")
    if (manifest.get("SchemaVersion") != 1
            or manifest.get("Status") != "accepted-original-byte-identity"
            or manifest.get("Season") != year or not isinstance(value, str)
            or not re.fullmatch("[0-9a-f]{64}", value)
            or type(manifest.get("CompressedBytes")) is not int
            or manifest["CompressedBytes"] <= 0
            or manifest.get("ArchiveURL") != _archive_url(year, value)
            or manifest.get("ReleaseTag") != _archive_tag(year, value)):
        raise ValueError(f"Invalid accepted historical PBP Source manifest: {year}")
    if manifest.get("UpstreamSHA256") is None:
        if (manifest.get("OriginalSHA256") != value
                or manifest.get("SourceDigestAuthority") != "self-sha256-official-asset-no-digest"
                or type(manifest.get("SourceAssetID")) is not int):
            raise ValueError(f"Unverifiable self-hashed historical PBP: {year}")
    return value


def plan(
    root: Path, token: str, *, limit: int = 3,
    selected: list[int] | None = None,
) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    if not token or type(limit) is not int or not 0 <= limit <= 3:
        raise ValueError("Historical PBP requires token and bounded limit (0..3)")
    current = current_source_season(root)
    official = official_inventory(token)
    canonical = [x for x in source_seasons(root) if x < current]
    manifests = root / _SOURCE_MANIFEST_DIR
    existing = {}
    if manifests.is_dir():
        for path in manifests.iterdir():
            match = _MANIFEST.fullmatch(path.name)
            if match is None:
                continue
            year = int(match.group(1))
            # The live season is owned by nfl_pbp_source_auto, not by this
            # frozen-history importer. Its manifest is always present on main.
            if year == current:
                continue
            if year not in canonical:
                raise ValueError(f"PBP Source manifest without canonical Source season: {year}")
            record = load_json(path)
            sha = _accepted_sha(record, year)
            archived = _release_asset(_get_release(token, year, sha), year)
            if archived is None:
                raise ValueError(f"Accepted historical PBP archive missing: {year}")
            _verify_archive(archived, year, sha, record["CompressedBytes"])
            existing[year] = record
    missing = sorted((x for x in canonical if x not in existing and x in official), reverse=True)
    unavailable = sorted(x for x in canonical if x not in existing and x not in official)
    revisions = []
    for year, record in sorted(existing.items()):
        if year not in official:
            revisions.append({"Season": year, "Reason": "upstream-asset-unavailable"})
            continue
        asset = official[year]
        official_sha = asset.get("digest")
        stored_sha = record.get("OriginalSHA256") or record.get("UpstreamSHA256")
        if official_sha is not None and official_sha != f"sha256:{stored_sha}":
            revisions.append({"Season": year, "Reason": "official-provider-digest-changed"})
        elif asset["size"] != record["CompressedBytes"]:
            revisions.append({"Season": year, "Reason": "official-provider-size-changed"})
        elif record.get("SourceAssetID") not in (None, asset["id"]):
            revisions.append({"Season": year, "Reason": "official-provider-asset-replaced"})
        elif (record.get("SourceAssetUpdatedAtUtc") is not None
              and asset.get("updated_at") != record["SourceAssetUpdatedAtUtc"]):
            revisions.append({"Season": year, "Reason": "official-provider-asset-metadata-revised"})
    if selected is None:
        chosen = missing[:limit]
    else:
        if (len(selected) > limit or len(set(selected)) != len(selected)
                or any(type(x) is not int or x not in canonical for x in selected)):
            raise ValueError("Explicit PBP historical batch exceeds allowed scope")
        # Pinned retries may see the selected years already accepted by a prior
        # successful Raw push. Re-verify, but never widen the pinned batch.
        if any(x not in missing and x not in existing for x in selected):
            raise ValueError("Explicit PBP historical batch is not available")
        chosen = list(selected)
    return ({
        "Status": "historical-pbp-planned",
        "CurrentSeason": current,
        "OfficialSeasons": sorted(official),
        "CanonicalSeasons": canonical,
        "AcceptedSeasons": sorted(existing),
        "MissingSeasons": missing,
        "UnavailableSeasons": unavailable,
        "FrozenRevisionReview": revisions,
        "Seasons": chosen,
        "Limit": limit,
    }, official)


def run(
    root: Path, repository: str, token: str, *,
    limit: int = 3, selected: list[int] | None = None, write: bool = False,
    pin_path: Path | None = None,
) -> dict[str, Any]:
    if repository != _DEST_REPOSITORY:
        raise ValueError("Unexpected PBP archive repository")
    if pin_path is not None and not write:
        raise ValueError("A pinned PBP historical batch is valid for write mode only")
    saved = None
    if pin_path is not None and pin_path.is_file():
        if selected is not None:
            raise ValueError("Cannot combine pinned PBP source batch with explicit seasons")
        saved = load_json(pin_path)
        if (not isinstance(saved, dict) or not isinstance(saved.get("Seasons"), list)
                or not isinstance(saved.get("Assets"), dict)):
            raise ValueError("Invalid pinned PBP source intake batch")
        selected = saved["Seasons"]
    state, official = plan(root, token, limit=limit, selected=selected)
    asset_keys = ("id", "size", "digest", "updated_at", "browser_download_url")
    pinned_assets = {
        str(year): {key: official[year].get(key) for key in asset_keys}
        for year in state["Seasons"]
    }
    if saved is not None and saved["Assets"] != pinned_assets:
        raise ValueError("Pinned historical PBP official asset identity changed during Source retry")
    if pin_path is not None and not pin_path.exists():
        pin_path.write_text(json.dumps({
            "Seasons": state["Seasons"], "Assets": pinned_assets,
        }, sort_keys=True) + "\n", encoding="utf-8")
    if not write or not state["Seasons"]:
        return {**state, "Status": "historical-pbp-preview" if not write else "historical-pbp-noop",
                "Changed": False, "NewlyAccepted": [], "BlockedSeasons": []}

    staged: list[tuple[int, dict[str, Any], Path]] = []
    blocked: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="nfl-pbp-history-") as temporary:
        root_temp = Path(temporary)
        # Each candidate is independently fail-closed. A malformed source year
        # must never authorize that year, but also must not indefinitely prevent
        # the other two proven-good years in the bounded intake from progressing.
        for year in state["Seasons"]:
            manifest = load_json(root / _SOURCE_MANIFEST_DIR / f"metadata-{year}.json")
            if manifest is not None:
                _accepted_sha(manifest, year)
                continue
            asset = official[year]
            path = root_temp / _archive_name(year)
            try:
                download(asset["browser_download_url"], path)
                digest = asset.get("digest")
                actual = _sha(path)
                if path.stat().st_size != asset["size"]:
                    raise ValueError(f"Original PBP official asset size changed: {year}")
                if digest is not None and digest != f"sha256:{actual}":
                    raise ValueError(f"Original PBP official asset digest changed: {year}")
                evidence = _audit(root, year, path, actual)
            except (OSError, ValueError, TypeError, KeyError,
                    urllib.error.URLError, EOFError, json.JSONDecodeError) as error:
                blocked.append({"Season": year, "Reason": str(error)[:300]})
                continue
            staged.append((year, {
                "SchemaVersion": 1,
                "Status": "accepted-original-byte-identity",
                "Provider": "nflverse",
                "Dataset": "nflverse.play-by-play-original",
                "Season": year,
                "SourceURL": asset["browser_download_url"],
                "SourceAssetID": asset["id"],
                "SourceAssetUpdatedAtUtc": asset.get("updated_at"),
                "UpstreamSHA256": actual if digest is not None else None,
                "OriginalSHA256": actual,
                "SourceDigestAuthority": (
                    "official-sha256" if digest is not None
                    else "self-sha256-official-asset-no-digest"
                ),
                "CompressedBytes": asset["size"],
                "License": "CC BY 4.0",
                "Attribution": "nflverse play-by-play data",
                "ReleaseRepository": repository,
                "ReleaseTag": _archive_tag(year, actual),
                "ArchiveURL": _archive_url(year, actual),
                "Audit": evidence,
                "SourceCompletenessCertified": False,
                "SnapshotRevision": 1,
                "PreviousAcceptedSHA256": None,
            }, path))
        # Release uploads may precede a Git push; they are immutable and reused
        # on retry. Manifest files are written only after all uploads verify.
        for year, metadata, path in staged:
            sha = metadata["OriginalSHA256"]
            release = _get_release(token, year, sha)
            if release is None:
                release = _create_release(token, year, sha, metadata["SourceURL"])
            archived = _release_asset(release, year)
            if archived is None:
                archived = _upload(token, release, path, year, sha, metadata["CompressedBytes"])
            _verify_archive(archived, year, sha, metadata["CompressedBytes"])
            metadata["ArchiveAssetID"] = archived["id"]
            metadata["StoredAtUtc"] = (
                datetime.now(timezone.utc).replace(microsecond=0)
                .isoformat().replace("+00:00", "Z")
            )
        for year, metadata, _ in staged:
            path = root / _SOURCE_MANIFEST_DIR / f"metadata-{year}.json"
            if not write_json_if_changed(path, metadata):
                raise ValueError(f"Historical PBP metadata unexpectedly unchanged: {year}")
        return {
            **state,
            "Status": (
                "historical-pbp-partial" if blocked and staged else
                "historical-pbp-blocked" if blocked else
                "historical-pbp-accepted"
            ),
            "Changed": bool(staged),
            "NewlyAccepted": [year for year, _, _ in staged],
            "BlockedSeasons": blocked,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repository", default=_DEST_REPOSITORY)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--seasons", help="Pinned comma-separated batch; none means empty")
    parser.add_argument("--write", action="store_true", help="Stage only approved Source manifests")
    parser.add_argument("--pin-path", type=Path, help="Runner-temp batch file, stable across Source writer retries")
    args = parser.parse_args()
    try:
        selected = None if args.seasons is None else (
            [] if args.seasons == "none" else [int(x) for x in args.seasons.split(",")]
        )
        report = run(args.repo_root.resolve(), args.repository,
                     os.environ.get("PBP_ARCHIVE_TOKEN", ""),
                     limit=args.limit, selected=selected, write=args.write,
                     pin_path=args.pin_path)
    except (OSError, ValueError, TypeError, KeyError, urllib.error.URLError,
            EOFError, json.JSONDecodeError) as error:
        print(f"nfl_pbp_source_history failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
