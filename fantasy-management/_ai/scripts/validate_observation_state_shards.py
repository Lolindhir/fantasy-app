#!/usr/bin/env python3
"""Validate the fully sharded entity-observation durable state."""
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
        raise ValidationError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def require_pretty(path: Path, value: Any) -> None:
    expected = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        raise ValidationError(f"{path}: expected canonical pretty JSON with one trailing newline.")


def validate_profile_state(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: profile state must be an object.")
    required = {
        "status", "last_checked_at", "state_hash", "material_state", "confidence",
        "source_fingerprints", "last_material_change_at", "last_error",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValidationError(f"{context}: missing profile fields {missing}.")
    if not isinstance(value["material_state"], dict):
        raise ValidationError(f"{context}: material_state must be an object.")
    if not isinstance(value["source_fingerprints"], list):
        raise ValidationError(f"{context}: source_fingerprints must be an array.")


def validate_target(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: target must be an object.")
    required = {"entity_fingerprint", "target_set_ids", "last_checked_at", "status", "observations"}
    missing = sorted(required - set(value))
    if missing:
        raise ValidationError(f"{context}: missing target fields {missing}.")
    if not isinstance(value["entity_fingerprint"], str) or not value["entity_fingerprint"]:
        raise ValidationError(f"{context}: entity_fingerprint must be non-empty.")
    if not isinstance(value["target_set_ids"], list) or not value["target_set_ids"]:
        raise ValidationError(f"{context}: target_set_ids must be a non-empty array.")
    observations = value["observations"]
    if not isinstance(observations, dict) or not observations:
        raise ValidationError(f"{context}: observations must be a non-empty object.")
    for profile_id, profile_state in observations.items():
        validate_profile_state(profile_state, f"{context}.observations.{profile_id}")


def effective_state(header_path: Path, shard_dir: Path) -> dict[str, Any]:
    header = load_json(header_path)
    require_pretty(header_path, header)
    if not isinstance(header, dict) or header.get("job_id") != "entity-observation":
        raise ValidationError(f"{header_path}: expected entity-observation State header.")
    revision = header.get("revision")
    if not isinstance(revision, int):
        raise ValidationError(f"{header_path}: revision must be an integer.")
    job_state = header.get("job_state")
    if not isinstance(job_state, dict):
        raise ValidationError(f"{header_path}: job_state must be an object.")
    embedded_targets = job_state.get("targets")
    if embedded_targets != {}:
        raise ValidationError(
            f"{header_path}: fully sharded storage requires job_state.targets to be an empty object."
        )
    target_sets = job_state.get("target_sets")
    if not isinstance(target_sets, dict):
        raise ValidationError(f"{header_path}: job_state.target_sets must be an object.")
    if not shard_dir.is_dir():
        raise ValidationError(f"Missing target shard directory: {shard_dir}")

    result = copy.deepcopy(header)
    result["job_state"]["targets"] = {}
    seen_write_ids: set[str] = set()
    seen_fingerprints: dict[str, str] = {}
    shard_paths = sorted(shard_dir.glob("*.json"))
    if not shard_paths:
        raise ValidationError(f"{shard_dir}: at least one target shard is required.")

    for path in shard_paths:
        shard = load_json(path)
        require_pretty(path, shard)
        if not isinstance(shard, dict):
            raise ValidationError(f"{path}: shard must be an object.")
        required = {"schema_version", "target_id", "base_state_revision", "write_id", "updated_at", "target"}
        missing = sorted(required - set(shard))
        if missing:
            raise ValidationError(f"{path}: missing shard fields {missing}.")
        if shard["schema_version"] != 1:
            raise ValidationError(f"{path}: unsupported schema_version.")
        target_id = shard["target_id"]
        if target_id != path.stem:
            raise ValidationError(f"{path}: target_id must match filename stem.")
        if shard["base_state_revision"] != revision:
            raise ValidationError(
                f"{path}: base_state_revision must equal State header revision {revision}."
            )
        write_id = shard["write_id"]
        if not isinstance(write_id, str) or not write_id:
            raise ValidationError(f"{path}: write_id must be a non-empty string.")
        if write_id in seen_write_ids:
            raise ValidationError(f"{path}: duplicate write_id {write_id!r}.")
        seen_write_ids.add(write_id)
        validate_target(shard["target"], str(path))
        fingerprint = shard["target"]["entity_fingerprint"]
        other = seen_fingerprints.get(fingerprint)
        if other is not None and other != target_id:
            raise ValidationError(
                f"{path}: entity_fingerprint {fingerprint!r} is already used by target {other!r}."
            )
        seen_fingerprints[fingerprint] = target_id
        unknown_sets = sorted(set(shard["target"]["target_set_ids"]) - set(target_sets))
        if unknown_sets:
            raise ValidationError(f"{path}: target references unknown target sets {unknown_sets}.")
        result["job_state"]["targets"][target_id] = copy.deepcopy(shard["target"])
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        type=Path,
        default=root / "fantasy-management/automation/state/entity-observation.json",
    )
    parser.add_argument(
        "--shards",
        type=Path,
        default=root / "fantasy-management/automation/state/entity-observation-targets",
    )
    parser.add_argument("--dump-merged", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        merged = effective_state(args.state, args.shards)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.dump_merged:
        args.dump_merged.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    count = len(merged["job_state"]["targets"])
    print(f"OK: entity-observation full-shard State is valid ({count} targets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
