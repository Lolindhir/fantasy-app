#!/usr/bin/env python3
"""Validate and materialize the effective entity-observation state.

The historical monolithic entity-observation.json is a read-only base snapshot.
Approved interactive updates are stored as small target shards under
automation/state/entity-observation-targets/.  A shard replaces exactly one
base target.  This keeps normal writes bounded while preserving the complete
legacy baseline losslessly.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def require_pretty(path: Path, value: Any) -> None:
    expected = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        raise ValidationError(f"{path}: JSON must use canonical 2-space pretty formatting.")


def validate_profile_state(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label}: profile state must be an object.")
    required = {
        "status", "last_checked_at", "state_hash", "material_state", "confidence",
        "source_fingerprints", "last_material_change_at", "last_error",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValidationError(f"{label}: missing fields {missing}.")
    if not isinstance(value["material_state"], dict):
        raise ValidationError(f"{label}: material_state must be an object.")
    if not isinstance(value["source_fingerprints"], list):
        raise ValidationError(f"{label}: source_fingerprints must be an array.")


def validate_target(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label}: target must be an object.")
    required = {"entity_fingerprint", "target_set_ids", "last_checked_at", "status", "observations"}
    missing = sorted(required - set(value))
    if missing:
        raise ValidationError(f"{label}: missing fields {missing}.")
    if not isinstance(value["observations"], dict) or not value["observations"]:
        raise ValidationError(f"{label}: observations must be a non-empty object.")
    for profile_id, profile_state in value["observations"].items():
        validate_profile_state(profile_state, f"{label}/{profile_id}")


def effective_state(base_path: Path, shard_dir: Path) -> dict[str, Any]:
    base = load_json(base_path)
    require_pretty(base_path, base)
    if not isinstance(base, dict) or base.get("job_id") != "entity-observation":
        raise ValidationError("Base state is not the entity-observation state.")
    targets = ((base.get("job_state") or {}).get("targets"))
    if not isinstance(targets, dict):
        raise ValidationError("Base state has no job_state.targets object.")

    result = copy.deepcopy(base)
    effective_targets = result["job_state"]["targets"]
    seen_write_ids: set[str] = set()

    if not shard_dir.exists():
        return result

    for path in sorted(shard_dir.glob("*.json")):
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
        target_id = shard["target_id"]
        if target_id != path.stem:
            raise ValidationError(f"{path}: target_id must match filename stem.")
        if not isinstance(shard["base_state_revision"], int) or shard["base_state_revision"] > base.get("revision", -1):
            raise ValidationError(f"{path}: base_state_revision is newer than the base state.")
        write_id = shard["write_id"]
        if not isinstance(write_id, str) or not write_id:
            raise ValidationError(f"{path}: write_id must be a non-empty string.")
        if write_id in seen_write_ids:
            raise ValidationError(f"{path}: duplicate write_id {write_id!r}.")
        seen_write_ids.add(write_id)
        validate_target(shard["target"], str(path))

        previous = targets.get(target_id)
        if previous is not None and previous.get("entity_fingerprint") != shard["target"].get("entity_fingerprint"):
            raise ValidationError(f"{path}: entity_fingerprint differs from immutable base identity.")
        effective_targets[target_id] = copy.deepcopy(shard["target"])

    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[3]
    parser.add_argument("--base", type=Path, default=root / "fantasy-management/automation/state/entity-observation.json")
    parser.add_argument("--shards", type=Path, default=root / "fantasy-management/automation/state/entity-observation-targets")
    parser.add_argument("--dump-merged", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        merged = effective_state(args.base, args.shards)
        if args.dump_merged:
            args.dump_merged.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"OK: entity-observation base + shards valid ({len(((merged.get('job_state') or {}).get('targets') or {}))} effective targets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
