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
import os
from pathlib import Path
import re
import sys
import urllib.request
from typing import Any, Callable

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from nfl_injuries_materialize import _assert_bounded_path, stage_injury_season
from nfl_injuries_phase import run_injury_phase
from nfl_source_data_lib.injury_product_plan import (
    plan_release_refresh, plan_injury_history_inventory, build_injury_artifacts,
)
from nfl_source_data_lib.common import current_source_season
from nfl_source_data_lib.injury_reports import valid_injury_season

_RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/injuries"
_MAX_RELEASE_BYTES = 2_000_000
_MAX_SEASON_BYTES = 12_000_000


class _RejectAuthenticatedRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward an Actions token through a release API redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Authenticated injury release metadata API may not redirect")


def _read_https(
    url: str, limit: int, *, accept: str, token: str | None = None,
) -> bytes:
    # The Actions token may authenticate only the fixed GitHub release-metadata
    # API endpoint. Never attach it to an asset URL, mirror or arbitrary redirect.
    if token and url != _RELEASE_API:
        raise ValueError("Authenticated injury release request must target the official GitHub API")
    headers = {
        "Accept": accept,
        "User-Agent": "Lolindhir-fantasy-app-injuries/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    # For authenticated metadata, reject HTTP redirects so the bearer token
    # cannot be forwarded to another host. CSV assets remain unauthenticated.
    opener = urllib.request.build_opener(_RejectAuthenticatedRedirects()) if token else None
    response = opener.open(request, timeout=40) if opener else urllib.request.urlopen(request, timeout=40)
    with response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Upstream Injury source is implausibly large")
    return payload


def release_api() -> dict[str, Any]:
    # GitHub-hosted runners share a low unauthenticated API rate limit. Use the
    # existing scoped Actions token when provided; no new secret is required.
    token = os.environ.get("NFLVERSE_RELEASE_API_TOKEN") or None
    payload = json.loads(_read_https(
        _RELEASE_API, _MAX_RELEASE_BYTES, accept="application/vnd.github+json",
        token=token,
    ))
    if not isinstance(payload, dict):
        raise ValueError("Upstream release metadata is not a JSON object")
    return payload


def source_asset(url: str) -> bytes:
    if not url.startswith("https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_"):
        raise ValueError("Unexpected injury download URL")
    return _read_https(url, _MAX_SEASON_BYTES, accept="text/csv")



def discover_injury_history(
    *,
    repo_root: Path,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    """Inspect official inventory plus accepted local originals, read-only.

    Only the weekly intake may enumerate incomplete Raw/metadata pairs for
    repair. Other users still fail closed on incomplete stored provenance.
    """
    if not repo_root.is_dir():
        raise ValueError("Repository root does not exist")
    current = current_source_season(repo_root)
    raw_root = repo_root / f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries"
    schedules_root = repo_root / f"{DATA_SOURCE_ROOT}/nfl/schedules"
    persisted: set[int] = set()
    if raw_root.is_dir():
        for metadata_path in sorted(raw_root.glob("metadata-*.json")):
            match = re.fullmatch(r"metadata-([0-9]{4})\.json", metadata_path.name)
            if not match or not valid_injury_season(int(match.group(1))):
                raise ValueError("Unrecognized Injury source metadata filename")
            season = int(match.group(1))
            metadata_path = _assert_bounded_path(
                repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/metadata-{season}.json",
            )
            raw_path = _assert_bounded_path(
                repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/raw-{season}.csv",
            )
            if metadata_path.is_symlink() or raw_path.is_symlink():
                raise ValueError(f"Incomplete or symlinked stored Injury source season {season}")
            if not raw_path.is_file():
                if allow_incomplete and not raw_path.exists():
                    continue
                raise ValueError(f"Incomplete stored Injury source season {season}")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            source = raw_path.read_bytes()
            if (not isinstance(metadata, dict)
                    or metadata.get("SourceDataset") != "nflverse.injuries"
                    or metadata.get("Season") != season
                    or metadata.get("AssetByteSize") != len(source)
                    or metadata.get("AssetSha256") != hashlib.sha256(source).hexdigest()):
                raise ValueError(f"Stored Injury provenance failed validation for season {season}")
            persisted.add(season)
    schedules: set[int] = set()
    if schedules_root.is_dir():
        for path in schedules_root.glob("*.json"):
            if re.fullmatch(r"[0-9]{4}\.json", path.name) and path.is_file() and not path.is_symlink():
                schedules.add(int(path.stem))
    return plan_injury_history_inventory(
        fetch_release(), current_season=current,
        persisted_seasons=persisted, schedule_seasons=schedules,
    )



def preflight_next_injury_history(
    *,
    repo_root: Path,
    fetch_release: Callable[[], dict[str, Any]] = release_api,
    fetch_asset: Callable[[str], bytes] = source_asset,
) -> dict[str, Any]:
    """Read-only full original-byte audit before selecting ONE historical pilot.

    The candidate season comes solely from official release discovery. A
    previously published Raw without corresponding Derived is also eligible for
    recovery. This function has no Git, output file or publisher side effects.
    """
    release = fetch_release()
    inventory = discover_injury_history(repo_root=repo_root, fetch_release=lambda: release)
    current = inventory["CurrentSeason"]
    candidates = []
    for row in inventory["SeasonStates"]:
        season = row["Season"]
        if (season >= current or not row["OfficialSha256Available"]
                or not row["CanonicalScheduleAvailable"]):
            continue
        derived_file = _assert_bounded_path(
            repo_root, f"{DATA_DERIVED_ROOT}/nfl-injuries/{season}.json")
        if not derived_file.is_file():
            candidates.append(season)
    if not candidates:
        return {
            "Status": "no-verified-history-missing",
            "Season": None, "PublicationPerformed": False,
            "BlockedSeasons": inventory["BlockedSeasons"],
            "PersistedMissingUpstream": inventory["PersistedMissingUpstream"],
        }

    # At most one candidate in the bootstrap run. Never construct or persist a
    # static historical season list; a later invocation may resume the next one.
    season = max(candidates)
    decision = plan_release_refresh(release, season=season)
    asset = decision["SourceAsset"]
    expected_digest = asset["Sha256"]
    if not expected_digest:
        raise ValueError("Historical pilot requires the official full-asset SHA-256")
    source = fetch_asset(asset["DownloadUrl"])
    if (not isinstance(source, bytes)
            or len(source) != asset["ByteSize"]
            or hashlib.sha256(source).hexdigest() != expected_digest):
        raise ValueError("Historical pilot original bytes disagree with official SHA-256/size")
    identity_file = _assert_bounded_path(
        repo_root, f"{DATA_SOURCE_ROOT}/nfl/identities/players.json")
    schedule_file = _assert_bounded_path(
        repo_root, f"{DATA_SOURCE_ROOT}/nfl/schedules/{season}.json")
    if not identity_file.is_file() or not schedule_file.is_file():
        raise ValueError("Historical pilot lacks persisted canonical identity or schedule")
    players = json.loads(identity_file.read_text(encoding="utf-8"))
    schedule = json.loads(schedule_file.read_text(encoding="utf-8"))
    proposed = build_injury_artifacts(
        season=season, source_csv=source, players=players,
        schedule=schedule, expected_source_sha256=expected_digest,
        release_asset=asset,
    )
    manifest = json.loads(proposed[f"{DATA_SOURCE_ROOT}/nfl/injuries/{season}/manifest.json"])
    quality = manifest["CanonicalQuality"]
    identities = quality["IdentityResolutionCounts"]
    links = quality["GameLinkCounts"]
    # Preserve uncertain observations, but never silently claim this first
    # historical season passed complete cross-source linkage acceptance.
    if (identities["unresolved"] or identities["ambiguous"]
            or links["ambiguous"] or links["not-found"] or links["not-evaluated"]):
        raise ValueError(
            "Historical Injury pilot needs identity/game-link review: "
            + json.dumps(quality, sort_keys=True))
    return {
        "Status": "verified-single-season-pilot",
        "Season": season,
        "SourceAssetSha256": expected_digest,
        "SourceRowCount": manifest["SourceRowCount"],
        "ObservedWeekCount": manifest["ObservedWeekCount"],
        "Quality": quality,
        "PublicationPerformed": False,
        "BlockedSeasons": inventory["BlockedSeasons"],
    }


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
        repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/metadata-{season}.json",
    )
    raw_path = _assert_bounded_path(
        repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/raw-{season}.csv",
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
        repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/metadata-{season}.json"
    )
    raw_path = _assert_bounded_path(
        repo_root, f"{DATA_SOURCE_ROOT}/providers/nflverse/injuries/raw-{season}.csv"
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
    parser.add_argument("--season", type=int)
    parser.add_argument("--discover-history", action="store_true",
                        help="Read-only inventory from official release; no year range or data changes")
    parser.add_argument("--pilot-preflight", action="store_true",
                        help="Read-only full source/schema/identity/game-link check for one missing historical season")
    parser.add_argument("--identities", type=Path)
    parser.add_argument("--schedule", type=Path, help="Optional canonical NFL schedule")
    parser.add_argument("--write", action="store_true", help="Stage candidate files in local checkout only")
    parser.add_argument("--raw-only", action="store_true", help="Stage only provider injury source and metadata; no player identities needed")
    args = parser.parse_args(argv)
    try:
        if args.discover_history or args.pilot_preflight:
            if args.discover_history and args.pilot_preflight:
                parser.error("Select exactly one read-only history mode")
            if args.season is not None or args.identities or args.schedule or args.raw_only or args.write:
                parser.error("History discovery/preflight is read-only and accepts no season or publication inputs")
            output = (discover_injury_history(repo_root=args.repo_root)
                      if args.discover_history else
                      preflight_next_injury_history(repo_root=args.repo_root))
        elif args.season is None:
            parser.error("--season is required unless --discover-history")
        elif args.raw_only:
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
