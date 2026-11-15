#!/usr/bin/env python3
"""Build and optionally stage one season of the independent NFL Injury product.

Default: read-only. Explicit --write stages only the approved year-specific
raw/canonical/derived paths in a local checkout. It never pushes, schedules,
adds a dataset to the registry, changes an App consumer, or fetches a provider.
Use existing rebuild-and-publish workflow mechanics for any future Git commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from nfl_source_data_lib.injury_product_plan import (
    build_injury_artifacts,
    classify_injury_artifacts,
    plan_release_refresh,
)

_WEEK = re.compile(r"(?:0[1-9]|1[0-9]|2[0-2])\.json")


def _assert_bounded_path(root: Path, relative: str) -> Path:
    """Reject traversal or symlinked parent paths before any read or write."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"Invalid injury artifact path: {relative}")
    cursor = root
    for component in path.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ValueError(f"Symlink within injury artifact path: {relative}")
    if not cursor.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Injury artifact escaped repository root: {relative}")
    return cursor


def read_existing_product(root: Path, proposed: dict[str, bytes], season: int) -> dict[str, bytes]:
    """Include stale canonical weeks so no previous evidence vanishes silently."""
    paths = set(proposed)
    folder = root / f"data-source/nfl/injuries/{season}"
    for week in range(1, 23):
        paths.add(f"data-source/nfl/injuries/{season}/{week:02d}.json")
    existing: dict[str, bytes] = {}
    for name in sorted(paths):
        target = _assert_bounded_path(root, name)
        if target.is_file():
            existing[name] = target.read_bytes()
    # Distinguish old unknown files from safe canonical-week files.
    if folder.is_dir():
        for target in folder.iterdir():
            if target.is_symlink() or (target.is_file() and
                    target.name != "manifest.json" and not _WEEK.fullmatch(target.name)):
                raise ValueError(f"Unexpected existing injury canonical file: {target.name}")
    return existing


def stage_injury_season(
    *,
    repo_root: Path,
    season: int,
    csv_bytes: bytes,
    players: dict[str, Any],
    schedule: dict[str, Any] | None = None,
    expected_source_sha256: str | None = None,
    release_json: dict[str, Any] | None = None,
    write: bool = False,
) -> dict[str, Any]:
    """Fail before touching any output when the candidate isn't completely valid.

    The staging transaction is a local working-tree change, not a Git commit.
    A future Git publisher must perform checkout/race reset/rebuild and commit
    its declared paths as one atomic public revision.
    """
    if not repo_root.is_dir():
        raise ValueError("Repository root must be an existing directory")
    if (not isinstance(season, int) or isinstance(season, bool)
            or not 2012 <= season <= 2099):
        raise ValueError("Unsupported NFL injury report season")
    release_asset = None
    decision = None
    if release_json is not None:
        decision = plan_release_refresh(release_json, season=season)
        if decision["Action"] == "retry-later":
            return {
                "SchemaVersion": 1, "Season": season, "WritePerformed": False,
                "Status": "upstream-not-ready", "ReleaseDecision": decision,
            }
        release_asset = decision["SourceAsset"]
    if write and not (expected_source_sha256 or release_asset):
        raise ValueError("Writing injury source requires an explicit expected digest or official release metadata")
    proposed = build_injury_artifacts(
        season=season,
        source_csv=csv_bytes,
        players=players,
        schedule=schedule,
        expected_source_sha256=expected_source_sha256,
        release_asset=release_asset,
    )
    existing = read_existing_product(repo_root, proposed, season)
    delta = classify_injury_artifacts(proposed, existing, season=season)
    result = {
        "SchemaVersion": 1,
        "Season": season,
        "WritePerformed": False,
        "Status": "no-op" if not delta["RequiresWrites"] else "changes-planned",
        "SourceAssetSha256": hashlib.sha256(csv_bytes).hexdigest(),
        "ReleaseDecision": decision,
        "ChangeSet": delta,
        "ProductVersion": "nfl-injuries-v1",
    }
    if not write or not delta["RequiresWrites"]:
        return result
    if not delta["CanAutoApply"]:
        raise ValueError("Source revision removed observed injury weeks; manual review required, no changes staged")
    # Prepare and fsync every candidate in an isolated directory before updating
    # destination files. One failing source/parser/identity/manifest check cannot
    # leave a partial candidate on disk. The surrounding Git commit is atomic.
    with tempfile.TemporaryDirectory(prefix="nfl-injuries-stage-") as work:
        staged = Path(work)
        changes = delta["New"] + delta["Changed"]
        for relative in changes:
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(proposed[relative])
        # Recheck destinations for an external concurrent edit since the read.
        for relative in changes:
            destination = _assert_bounded_path(repo_root, relative)
            old = existing.get(relative)
            if old is None:
                if destination.exists():
                    raise ValueError(f"Injury output appeared during staging: {relative}")
            elif not destination.is_file() or destination.read_bytes() != old:
                raise ValueError(f"Injury output changed during staging: {relative}")
        for relative in changes:
            destination = _assert_bounded_path(repo_root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            _assert_bounded_path(repo_root, relative)
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".injury-", dir=destination.parent, delete=False
            ) as temp:
                temp.write((staged / relative).read_bytes())
                temp.flush()
                os.fsync(temp.fileno())
                tmp_name = temp.name
            try:
                os.replace(tmp_name, destination)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
    result["WritePerformed"] = True
    result["Status"] = "staged-local-worktree"
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--season", required=True, type=int)
    ap.add_argument("--csv", required=True, type=Path, help="Previously downloaded source season CSV")
    ap.add_argument("--identities", required=True, type=Path, help="Existing canonical players.json")
    ap.add_argument("--schedule", type=Path, help="Optional existing season schedule JSON")
    ap.add_argument("--expected-sha256", help="Expected source SHA-256 obtained independently")
    ap.add_argument("--release-json", type=Path, help="Optional pre-fetched official GitHub release API JSON")
    ap.add_argument("--write", action="store_true", help="Explicitly stage candidate in local working tree")
    args = ap.parse_args(argv)
    try:
        result = stage_injury_season(
            repo_root=args.repo_root, season=args.season, csv_bytes=args.csv.read_bytes(),
            players=json.loads(args.identities.read_text(encoding="utf-8")),
            schedule=json.loads(args.schedule.read_text(encoding="utf-8")) if args.schedule else None,
            expected_source_sha256=args.expected_sha256,
            release_json=json.loads(args.release_json.read_text(encoding="utf-8")) if args.release_json else None,
            write=args.write,
        )
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"Injury season staging failed closed: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
