#!/usr/bin/env python3
"""Source-revision-aware NFL injury ingestion, without any Git or scheduler side effects.

The existing ESPN ten-minute availability producer remains independent.
This runner reads the official nflverse injury release metadata, downloads only
when necessary, verifies the bytes and stages the season via the bounded local
materializer. Default: inspect only. A future approved existing workflow may
invoke --write under its own rebuild/retry and publication path guard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from typing import Any, Callable

from nfl_injuries_materialize import _assert_bounded_path, stage_injury_season
from nfl_injuries_phase import run_injury_phase
from nfl_source_data_lib.injury_product_plan import plan_release_refresh

_RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/injuries"
_MAX_RELEASE_BYTES = 2_000_000
_MAX_SEASON_BYTES = 12_000_000


def _read_https(url: str, limit: int, *, accept: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "Lolindhir-fantasy-app-injuries/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Upstream Injury source is implausibly large")
    return payload


def release_api() -> dict[str, Any]:
    payload = json.loads(_read_https(
        _RELEASE_API, _MAX_RELEASE_BYTES, accept="application/vnd.github+json"
    ))
    if not isinstance(payload, dict):
        raise ValueError("Upstream release metadata is not a JSON object")
    return payload


def source_asset(url: str) -> bytes:
    if not url.startswith("https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_"):
        raise ValueError("Unexpected injury download URL")
    return _read_https(url, _MAX_SEASON_BYTES, accept="text/csv")


def refresh_injury_raw(
    *,
    repo_root: Path,
    season: int,
    write: bool = False,
    current_season: int | None = None,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    fetch_asset: Callable[[str], bytes] = source_asset,
) -> dict[str, Any]:
    """Only the nflverse Injury Raw/metadata owner; no identity/Derived writes.

    Missing or corrupt official release evidence is a retriable failure, never
    an empty replacement. Source bytes must match the official SHA-256 digest.
    """
    if not repo_root.is_dir():
        raise ValueError("Repository root does not exist")
    metadata_path = _assert_bounded_path(
        repo_root, f"data-source/providers/nflverse/injuries/metadata-{season}.json",
    )
    raw_path = _assert_bounded_path(
        repo_root, f"data-source/providers/nflverse/injuries/raw-{season}.csv",
    )
    known = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else None
    release = fetch_release()
    decision = plan_release_refresh(release, season=season, stored_metadata=known)
    if decision["Action"] == "retry-later":
        raise ValueError("Official injury release season asset not yet available; retry later")
    if (current_season is not None and season < current_season
            and (metadata_path.exists() or raw_path.exists())
            and decision["Action"] != "no-op"):
        raise ValueError("Historical Injury Source revision is frozen; manual repair approval required")
    asset = decision["SourceAsset"]
    digest = asset["Sha256"]
    if digest is None:
        raise ValueError("Official injury asset lacks verified SHA-256; do not publish unverified raw")
    reuse = decision["Action"] == "no-op" and raw_path.is_file()
    if reuse:
        candidate = raw_path.read_bytes()
        if (known is None or
                hashlib.sha256(candidate).hexdigest() != known.get("AssetSha256") or
                len(candidate) != known.get("AssetByteSize")):
            raise ValueError("Cached injury raw conflicts with stored provenance")
    else:
        candidate = fetch_asset(asset["DownloadUrl"])
    if (not isinstance(candidate, bytes) or len(candidate) != asset["ByteSize"]
            or hashlib.sha256(candidate).hexdigest() != digest):
        raise ValueError("Official injury release bytes failed SHA-256 and size verification")
    result = run_injury_phase(
        repo_root, season, "raw", source_csv=candidate,
        release_json=release, write=write,
    )
    result["Downloaded"] = not reuse
    result["SourceAssetSha256"] = digest
    result["ReleaseDecision"] = decision["Action"]
    return result


def refresh_injury_season(
    *,
    repo_root: Path,
    season: int,
    players: dict[str, Any],
    schedule: dict[str, Any] | None = None,
    write: bool = False,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    fetch_asset: Callable[[str], bytes] = source_asset,
) -> dict[str, Any]:
    """Refresh from real release metadata; reuse local CSV if its bytes match.

    Even an unchanged upstream CSV may require re-derivation due to identity
    or schedule input changes, so no-op is decided by the final artifact delta.
    """
    release = fetch_release()
    metadata_path = _assert_bounded_path(
        repo_root, f"data-source/providers/nflverse/injuries/metadata-{season}.json"
    )
    raw_path = _assert_bounded_path(
        repo_root, f"data-source/providers/nflverse/injuries/raw-{season}.csv"
    )
    stored_metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else None
    decision = plan_release_refresh(release, season=season, stored_metadata=stored_metadata)
    if decision["Action"] == "retry-later":
        return {
            "SchemaVersion": 1, "Season": season, "Status": "upstream-not-ready",
            "WritePerformed": False, "Downloaded": False, "ReleaseDecision": decision,
        }
    asset = decision["SourceAsset"]
    expected_digest = asset["Sha256"]
    reused = decision["Action"] == "no-op" and raw_path.is_file()
    if reused:
        if raw_path.is_symlink() or metadata_path.is_symlink():
            raise ValueError("Persisted injury source must not be a symlink")
        csv_bytes = raw_path.read_bytes()
        if (stored_metadata is None or
            hashlib.sha256(csv_bytes).hexdigest() != stored_metadata.get("AssetSha256") or
            len(csv_bytes) != stored_metadata.get("AssetByteSize")):
            raise ValueError("Persisted injury raw source digest/size disagrees with metadata")
    else:
        csv_bytes = fetch_asset(asset["DownloadUrl"])
    if not isinstance(csv_bytes, bytes) or not csv_bytes:
        raise ValueError("Downloaded or cached injury CSV is empty")
    if len(csv_bytes) != asset["ByteSize"]:
        raise ValueError("Injury asset size differs from official release")
    if expected_digest is not None and hashlib.sha256(csv_bytes).hexdigest() != expected_digest:
        raise ValueError("Injury asset SHA-256 differs from official release")
    output = stage_injury_season(
        repo_root=repo_root, season=season, csv_bytes=csv_bytes,
        players=players, schedule=schedule,
        release_json=release, write=write,
    )
    output["Downloaded"] = not reused
    output["ReleaseDecision"] = decision
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--identities", type=Path)
    parser.add_argument("--schedule", type=Path, help="Optional canonical NFL schedule")
    parser.add_argument("--write", action="store_true", help="Stage candidate files in local checkout only")
    parser.add_argument("--raw-only", action="store_true", help="Stage only provider injury source and metadata; no player identities needed")
    args = parser.parse_args(argv)
    try:
        if args.raw_only:
            if args.identities or args.schedule:
                parser.error("--raw-only does not accept identity or schedule inputs")
            output = refresh_injury_raw(
                repo_root=args.repo_root, season=args.season, write=args.write,
            )
        else:
            if args.identities is None:
                parser.error("--identities is required without --raw-only")
            output = refresh_injury_season(
                repo_root=args.repo_root, season=args.season,
                players=json.loads(args.identities.read_text(encoding="utf-8")),
                schedule=json.loads(args.schedule.read_text(encoding="utf-8")) if args.schedule else None,
                write=args.write,
            )
    except (ValueError, OSError, KeyError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Injury release refresh failed closed: {error}", file=sys.stderr)
        return 2
    json.dump(output, sys.stdout, sort_keys=True, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
