#!/usr/bin/env python3
"""Stage independent phases of the historic NFL injury data product (#1421).

No network, cron, Git operations or production writer activation. A future
approved publisher may call each phase separately: Raw -> Canonical -> Derived.
Default invocation performs only a dry-run. --write changes a local working
tree under an exact per-season allowlist, not a Git branch.
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

from derived_data_lib.nfl_injuries import derive_nfl_injuries
from nfl_injuries_materialize import _assert_bounded_path
from nfl_source_data_lib.injury_reports import valid_injury_season
from nfl_source_data_lib.injury_product_plan import (
    build_injury_artifacts,
    build_injury_raw_artifacts,
    plan_release_refresh,
)

_PHASES = ("raw", "canonical", "derived")
_WEEK_FILE = re.compile(r"(?:0[1-9]|1[0-9]|2[0-2])\.json")
_SOURCE = "nflverse.injuries"


def _render(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _read_json(root: Path, relative: str) -> dict:
    path = _assert_bounded_path(root, relative)
    if not path.is_file():
        raise ValueError(f"Required injury input is missing: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid injury input object: {relative}")
    return value


def _read_source(repo_root: Path, season: int) -> tuple[bytes, dict]:
    prefix = "data-source/providers/nflverse/injuries/"
    meta = _read_json(repo_root, f"{prefix}metadata-{season}.json")
    raw_path = _assert_bounded_path(repo_root, f"{prefix}raw-{season}.csv")
    if not raw_path.is_file():
        raise ValueError("Published injury original CSV is absent")
    raw = raw_path.read_bytes()
    if (meta.get("SchemaVersion") != 1 or meta.get("SourceDataset") != _SOURCE
            or meta.get("Season") != season or not raw
            or len(raw) != meta.get("AssetByteSize")
            or hashlib.sha256(raw).hexdigest() != meta.get("AssetSha256")):
        raise ValueError("Published injury original and metadata are not coherent")
    return raw, meta


def _read_canonical(repo_root: Path, season: int) -> dict:
    root = f"data-source/nfl/injuries/{season}/"
    manifest = _read_json(repo_root, root + "manifest.json")
    if (manifest.get("SchemaVersion") != 1 or manifest.get("Season") != season
            or manifest.get("SourceDataset") != _SOURCE):
        raise ValueError("Wrong injury canonical manifest identity")
    weeks = manifest.get("ObservedWeeks")
    if (not isinstance(weeks, list) or not weeks
            or any(not isinstance(w, int) or isinstance(w, bool) or not 1 <= w <= 22 for w in weeks)
            or weeks != sorted(set(weeks)) or manifest.get("ObservedWeekCount") != len(weeks)):
        raise ValueError("Invalid injury canonical manifest week inventory")
    folder = _assert_bounded_path(repo_root, root[:-1])
    if folder.is_dir():
        actual = {int(p.stem) for p in folder.iterdir()
                  if p.is_file() and _WEEK_FILE.fullmatch(p.name)}
        if actual != set(weeks):
            raise ValueError("Canonical injury week inventory differs from manifest")
        if any(p.is_symlink() or (p.is_file() and p.name != "manifest.json"
                and not _WEEK_FILE.fullmatch(p.name)) for p in folder.iterdir()):
            raise ValueError("Unrecognized canonical injury partition in season")
    artifacts = manifest.get("ObservedWeekArtifacts")
    if (not isinstance(artifacts, list) or len(artifacts) != len(weeks)
            or [a.get("Week") for a in artifacts if isinstance(a, dict)] != weeks):
        raise ValueError("Canonical injury manifest is missing precise week artifact proofs")
    parts = []
    count = 0
    for week, artifact in zip(weeks, artifacts):
        name = f"{root}{week:02d}.json"
        path = _assert_bounded_path(repo_root, name)
        byte_string = path.read_bytes()
        if (artifact.get("Path") != name or
                artifact.get("ByteSize") != len(byte_string) or
                artifact.get("Sha256") != hashlib.sha256(byte_string).hexdigest()):
            raise ValueError(f"Canonical injury week {week} bytes differ from published manifest")
        part = json.loads(byte_string.decode("utf-8"))
        if not isinstance(part, dict):
            raise ValueError(f"Canonical injury week {week} is not an object")
        if (part.get("SchemaVersion") != 1 or part.get("Season") != season
                or part.get("Week") != week or part.get("SourceDataset") != _SOURCE
                or part.get("SourceAssetSha256") != manifest.get("SourceAssetSha256")
                or part.get("IdentityGraphFingerprint") != manifest.get("IdentityGraphFingerprint")):
            raise ValueError(f"Inconsistent injury canonical partition in week {week}")
        observations = part.get("Observations")
        if not isinstance(observations, list) or not observations:
            raise ValueError(f"Empty injury canonical partition for observed week {week}")
        count += len(observations)
        parts.append(part)
    if (manifest.get("SourceRowCount") != count or
            (manifest.get("CanonicalQuality") or {}).get("SourceRowCount") != count):
        raise ValueError("Injury canonical manifest row count differs from partitions")
    return {
        "SchemaVersion": 1, "Season": season, "SourceDataset": _SOURCE,
        "SourceAssetSha256": manifest["SourceAssetSha256"],
        "IdentityGraphFingerprint": manifest["IdentityGraphFingerprint"],
        "Partitions": parts, "Quality": manifest["CanonicalQuality"],
    }


def plan_injury_phase(
    repo_root: Path, season: int, phase: str, *,
    source_csv: bytes | None = None,
    expected_source_sha256: str | None = None,
    release_json: dict | None = None,
    players: dict | None = None,
    schedule: dict | None = None,
) -> dict[str, bytes]:
    """Source→Canonical→Derived, each restricted to its own upstream owner."""
    if not valid_injury_season(season):
        raise ValueError("Injury season must be a four-digit year")
    if phase not in _PHASES:
        raise ValueError("Unknown Injury publication phase")
    if phase == "raw":
        if source_csv is None:
            raise ValueError("Raw phase requires explicit source season CSV")
        if players is not None or schedule is not None:
            raise ValueError("Raw phase must not depend on identities or schedule")
        release_asset = None
        if release_json is not None:
            decision = plan_release_refresh(release_json, season=season)
            if decision["Action"] == "retry-later":
                raise ValueError("Upstream injury season asset not yet published")
            release_asset = decision["SourceAsset"]
        return build_injury_raw_artifacts(
            season=season, source_csv=source_csv,
            expected_source_sha256=expected_source_sha256,
            release_asset=release_asset,
        )
    if source_csv is not None or expected_source_sha256 is not None or release_json is not None:
        raise ValueError("Downstream Injury phases must read their persisted Source inputs")
    if phase == "canonical":
        if players is None:
            raise ValueError("Canonical phase requires canonical player identities")
        raw, metadata = _read_source(repo_root, season)
        whole = build_injury_artifacts(
            season=season, source_csv=raw, players=players, schedule=schedule,
            expected_source_sha256=metadata["AssetSha256"],
        )
        prefix = f"data-source/nfl/injuries/{season}/"
        return {key: val for key, val in whole.items() if key.startswith(prefix)}
    if players is not None or schedule is not None:
        raise ValueError("Derived phase consumes only canonical Injury product")
    canonical = _read_canonical(repo_root, season)
    derived = derive_nfl_injuries(canonical)
    return {f"data-derived/nfl-injuries/{season}.json": _render(derived)}


def _allowed_phase_path(phase: str, season: int, path: str) -> bool:
    if phase == "raw":
        return path in (
            f"data-source/providers/nflverse/injuries/raw-{season}.csv",
            f"data-source/providers/nflverse/injuries/metadata-{season}.json",
        )
    if phase == "derived":
        return path == f"data-derived/nfl-injuries/{season}.json"
    prefix = f"data-source/nfl/injuries/{season}/"
    return path == prefix + "manifest.json" or (
        path.startswith(prefix) and bool(_WEEK_FILE.fullmatch(path[len(prefix):]))
    )


def run_injury_phase(
    repo_root: Path, season: int, phase: str, *, write: bool = False,
    source_csv: bytes | None = None, expected_source_sha256: str | None = None,
    release_json: dict | None = None,
    players: dict | None = None, schedule: dict | None = None,
) -> dict[str, Any]:
    if not repo_root.is_dir():
        raise ValueError("Repository root must be an existing directory")
    if write and phase == "raw" and not expected_source_sha256:
        if release_json is None:
            raise ValueError("Raw source staging requires an expected verified digest")
        decision = plan_release_refresh(release_json, season=season)
        if (decision["Action"] == "retry-later" or
                not decision["SourceAsset"]["Sha256"]):
            raise ValueError("Raw source staging requires an official or independently verified digest")
    proposed = plan_injury_phase(
        repo_root, season, phase, source_csv=source_csv,
        expected_source_sha256=expected_source_sha256, release_json=release_json,
        players=players, schedule=schedule,
    )
    if not proposed or any(not _allowed_phase_path(phase, season, p) for p in proposed):
        raise ValueError("Proposed Injury artifact exceeds its phase write scope")
    expected_keys = (
        {f"data-source/providers/nflverse/injuries/raw-{season}.csv",
         f"data-source/providers/nflverse/injuries/metadata-{season}.json"} if phase == "raw" else
        {f"data-source/nfl/injuries/{season}/manifest.json"} if phase == "canonical" else
        {f"data-derived/nfl-injuries/{season}.json"}
    )
    if not expected_keys.issubset(proposed):
        raise ValueError("Injury publication phase lacks mandatory outputs")
    existing = {}
    candidates = set(proposed)
    if phase == "canonical":
        for week in range(1, 23):
            candidates.add(f"data-source/nfl/injuries/{season}/{week:02d}.json")
    for path in candidates:
        target = _assert_bounded_path(repo_root, path)
        if target.is_file():
            existing[path] = target.read_bytes()
    # An official release can be re-uploaded under a new GitHub asset ID while
    # its SHA-256 and bytes remain unchanged. Preserve the *accepted* asset's
    # original attestation instead of creating a provenance-only data commit.
    # Every current release and the full CSV have already been validated by
    # plan_injury_phase; only release-specific identity/time may be ignored.
    if phase == "raw":
        raw_name = f"data-source/providers/nflverse/injuries/raw-{season}.csv"
        metadata_name = f"data-source/providers/nflverse/injuries/metadata-{season}.json"
        if existing.get(raw_name) == proposed[raw_name] and metadata_name in existing:
            accepted = json.loads(existing[metadata_name].decode("utf-8"))
            current = json.loads(proposed[metadata_name].decode("utf-8"))
            revision_fields = {"ReleaseAssetId", "ReleaseAssetUpdatedAt"}
            if (isinstance(accepted, dict) and
                    {k: v for k, v in accepted.items() if k not in revision_fields} ==
                    {k: v for k, v in current.items() if k not in revision_fields}):
                proposed[metadata_name] = existing[metadata_name]
    stale = sorted(set(existing) - set(proposed))
    changed = sorted(p for p, v in proposed.items() if p in existing and existing[p] != v)
    new = sorted(set(proposed) - set(existing))
    unchanged = sorted(p for p in proposed if p in existing and proposed[p] == existing[p])
    result = {
        "Phase": phase, "Season": season,
        "Status": "no-op" if not new and not changed and not stale else "changes-planned",
        "Written": False, "Changed": changed, "New": new, "Unchanged": unchanged,
        "ObsoleteRequiresReview": stale,
    }
    if not write or result["Status"] == "no-op":
        return result
    if stale:
        raise ValueError("Injury publication would remove observed partitions; manual review required")
    # Prepare every file, check all prior values, then change only declared paths.
    # Source/Canonical/Derived are intentionally separate local staging phases.
    with tempfile.TemporaryDirectory(prefix=f"injuries-{phase}-") as tmp:
        temporary = Path(tmp)
        for path in new + changed:
            dest = temporary / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(proposed[path])
        for path in new + changed:
            current = _assert_bounded_path(repo_root, path)
            if path in existing:
                if not current.is_file() or current.read_bytes() != existing[path]:
                    raise ValueError("Concurrent modification of Injury phase output")
            elif current.exists():
                raise ValueError("An Injury phase output appeared during staging")
        for path in new + changed:
            current = _assert_bounded_path(repo_root, path)
            current.parent.mkdir(parents=True, exist_ok=True)
            _assert_bounded_path(repo_root, path)
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".injury-", dir=current.parent,
                delete=False,
            ) as stream:
                stream.write((temporary / path).read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
                temp_name = stream.name
            try:
                os.replace(temp_name, current)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
    result["Written"] = True
    result["Status"] = "staged-local-worktree"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--phase", choices=_PHASES, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--csv", type=Path, help="Source season CSV (raw phase only)")
    parser.add_argument("--expected-sha256", help="Expected verified origin digest (raw phase only)")
    parser.add_argument("--release-json", type=Path, help="Optional official release metadata snapshot (raw only)")
    parser.add_argument("--identities", type=Path, help="Canonical players.json (canonical phase only)")
    parser.add_argument("--schedule", type=Path, help="Optional canonical NFL season schedule")
    parser.add_argument("--write", action="store_true", help="Stage only phase's local files; never commit/push")
    args = parser.parse_args(argv)
    try:
        result = run_injury_phase(
            repo_root=args.repo_root, season=args.season, phase=args.phase, write=args.write,
            source_csv=args.csv.read_bytes() if args.csv else None,
            expected_source_sha256=args.expected_sha256,
            release_json=json.loads(args.release_json.read_text(encoding="utf-8")) if args.release_json else None,
            players=json.loads(args.identities.read_text(encoding="utf-8")) if args.identities else None,
            schedule=json.loads(args.schedule.read_text(encoding="utf-8")) if args.schedule else None,
        )
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"nfl_injuries_phase failed closed: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
