#!/usr/bin/env python3
"""Build a lossless fully-sharded entity-observation state candidate.

This migration helper consumes the current legacy base snapshot plus any
existing target overlays, materializes the effective state, and emits:

- entity-observation-index.json (all non-target state),
- entity-observation-targets/{target_id}.json for every effective target,
- migration-manifest.json with deterministic source/result fingerprints.

Existing valid target shards whose target payload already matches the effective
state are copied byte-for-byte. This preserves approved post-base writes such as
Alec Pierce while filling all remaining legacy targets deterministically.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_observation_state_shards import ValidationError, effective_state, load_json, require_pretty, validate_target


def canonical_pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_output_shard(path: Path, index_revision: int) -> dict[str, Any]:
    shard = load_json(path)
    require_pretty(path, shard)
    if not isinstance(shard, dict):
        raise ValidationError(f"{path}: shard must be an object.")
    required = {"schema_version", "target_id", "base_state_revision", "write_id", "updated_at", "target"}
    missing = sorted(required - set(shard))
    if missing:
        raise ValidationError(f"{path}: missing fields {missing}.")
    if shard["schema_version"] != 1:
        raise ValidationError(f"{path}: unsupported schema_version.")
    if shard["target_id"] != path.stem:
        raise ValidationError(f"{path}: target_id must match filename stem.")
    if shard["base_state_revision"] != index_revision:
        raise ValidationError(
            f"{path}: migration shard base_state_revision must equal index revision {index_revision}."
        )
    if not isinstance(shard["write_id"], str) or not shard["write_id"]:
        raise ValidationError(f"{path}: write_id must be a non-empty string.")
    validate_target(shard["target"], str(path))
    return shard


def reconstruct_from_full_shards(index_path: Path, shard_dir: Path) -> dict[str, Any]:
    index = load_json(index_path)
    require_pretty(index_path, index)
    if not isinstance(index, dict) or index.get("job_id") != "entity-observation":
        raise ValidationError("Full-shard index is not the entity-observation state.")
    job_state = index.get("job_state")
    if not isinstance(job_state, dict):
        raise ValidationError("Full-shard index has no job_state object.")
    if "targets" in job_state:
        raise ValidationError("Full-shard index must not embed job_state.targets.")
    revision = index.get("revision")
    if not isinstance(revision, int):
        raise ValidationError("Full-shard index revision must be an integer.")

    result = copy.deepcopy(index)
    result["job_state"]["targets"] = {}
    seen_write_ids: set[str] = set()
    for path in sorted(shard_dir.glob("*.json")):
        shard = validate_output_shard(path, revision)
        if shard["write_id"] in seen_write_ids:
            raise ValidationError(f"{path}: duplicate write_id {shard['write_id']!r}.")
        seen_write_ids.add(shard["write_id"])
        result["job_state"]["targets"][shard["target_id"]] = copy.deepcopy(shard["target"])
    return result


def build_candidate(base_path: Path, legacy_shard_dir: Path, output_root: Path) -> dict[str, Any]:
    effective = effective_state(base_path, legacy_shard_dir)
    targets = ((effective.get("job_state") or {}).get("targets"))
    if not isinstance(targets, dict) or not targets:
        raise ValidationError("Effective legacy state has no persisted targets.")
    revision = effective.get("revision")
    if not isinstance(revision, int):
        raise ValidationError("Effective legacy state revision must be an integer.")

    if output_root.exists():
        shutil.rmtree(output_root)
    target_dir = output_root / "entity-observation-targets"
    target_dir.mkdir(parents=True, exist_ok=True)

    index = copy.deepcopy(effective)
    del index["job_state"]["targets"]
    index_path = output_root / "entity-observation-index.json"
    index_path.write_text(canonical_pretty(index), encoding="utf-8")

    preserved_existing_shards: list[str] = []
    generated_shards: list[str] = []
    for target_id, target in sorted(targets.items()):
        existing_path = legacy_shard_dir / f"{target_id}.json"
        output_path = target_dir / f"{target_id}.json"
        if existing_path.exists():
            existing = load_json(existing_path)
            require_pretty(existing_path, existing)
            if existing.get("target_id") != target_id or existing.get("target") != target:
                raise ValidationError(
                    f"{existing_path}: existing overlay does not match the effective target payload."
                )
            if existing.get("base_state_revision") != revision:
                raise ValidationError(
                    f"{existing_path}: existing overlay revision does not match migration revision {revision}."
                )
            shutil.copyfile(existing_path, output_path)
            preserved_existing_shards.append(target_id)
            continue

        validate_target(target, target_id)
        shard = {
            "schema_version": 1,
            "target_id": target_id,
            "base_state_revision": revision,
            "write_id": f"migration:full-shard:revision-{revision}:{target_id}",
            "updated_at": target["last_checked_at"],
            "target": target,
        }
        output_path.write_text(canonical_pretty(shard), encoding="utf-8")
        generated_shards.append(target_id)

    reconstructed = reconstruct_from_full_shards(index_path, target_dir)
    if reconstructed != effective:
        raise ValidationError("Losslessness check failed: reconstructed full-shard state differs from effective legacy state.")

    manifest = {
        "schema_version": 1,
        "migration": "entity-observation-full-shard",
        "source_revision": revision,
        "legacy_base_file_sha256": file_hash(base_path),
        "effective_state_sha256": canonical_hash(effective),
        "target_count": len(targets),
        "preserved_existing_shards": preserved_existing_shards,
        "generated_shards": generated_shards,
    }
    (output_root / "migration-manifest.json").write_text(canonical_pretty(manifest), encoding="utf-8")
    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[3]
    parser.add_argument(
        "--base",
        type=Path,
        default=root / "fantasy-management/automation/state/entity-observation.json",
    )
    parser.add_argument(
        "--legacy-shards",
        type=Path,
        default=root / "fantasy-management/automation/state/entity-observation-targets",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        manifest = build_candidate(args.base, args.legacy_shards, args.output_root)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        "OK: full-shard migration candidate is lossless "
        f"({manifest['target_count']} targets, "
        f"{len(manifest['preserved_existing_shards'])} existing shards preserved)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
