#!/usr/bin/env python3
"""Apply one validated observation checkpoint to the complete job state.

The helper is intentionally editorially neutral. It does not collect evidence or
make fantasy decisions. It receives a structured checkpoint produced by the
runner, applies it to the complete current state, calculates canonical material
state hashes, validates the full replacement document, and writes that document
to a local path. Repository publication remains a separate optimistic-concurrency
step using the pinned parent commit and state blob SHAs from the checkpoint.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


class StateBatchError(ValueError):
    """Raised when a checkpoint cannot be applied safely."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateBatchError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateBatchError(f"Invalid JSON in {path}: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 representation used for material-state hashes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def material_state_hash(material_state: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(material_state)).hexdigest()


def validate_against_schema(data: Any, schema_path: Path, label: str) -> None:
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError as exc:
        raise StateBatchError(
            "Python package 'jsonschema' is required for state batch validation."
        ) from exc

    schema = load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise StateBatchError(f"Invalid schema {schema_path}: {exc.message}") from exc

    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if not errors:
        return

    messages: list[str] = []
    for error in errors:
        path = ".".join(str(part) for part in error.path) or "<root>"
        messages.append(f"{label} at {path}: {error.message}")
    raise StateBatchError("\n".join(messages))


def _merge_unique(existing: Iterable[str], incoming: Iterable[str]) -> list[str]:
    return sorted({str(item) for item in existing} | {str(item) for item in incoming})


def _has_good_material_state(profile_state: dict[str, Any] | None) -> bool:
    if not profile_state:
        return False
    return bool(profile_state.get("state_hash")) and bool(
        profile_state.get("material_state")
    )


def _profile_state_from_result(
    previous: dict[str, Any] | None,
    result: dict[str, Any],
    evaluated_at: str,
) -> dict[str, Any]:
    outcome = result["outcome"]
    last_checked_at = result.get("last_checked_at") or evaluated_at
    source_fingerprints = sorted(set(result.get("source_fingerprints") or []))

    if outcome in {"baseline", "unchanged", "material_change"}:
        material_state = result.get("material_state")
        confidence = result.get("confidence")
        if not isinstance(material_state, dict) or not material_state:
            raise StateBatchError(
                f"Outcome {outcome!r} requires a non-empty material_state."
            )
        if confidence not in {"low", "medium", "high"}:
            raise StateBatchError(
                f"Outcome {outcome!r} requires confidence low, medium, or high."
            )

        calculated_hash = material_state_hash(material_state)
        supplied_hash = result.get("state_hash")
        if supplied_hash is not None and supplied_hash != calculated_hash:
            raise StateBatchError(
                "Supplied state_hash does not match canonical material_state hash."
            )

        return {
            "status": outcome,
            "last_checked_at": last_checked_at,
            "state_hash": calculated_hash,
            "material_state": material_state,
            "confidence": confidence,
            "source_fingerprints": source_fingerprints,
            "last_material_change_at": (
                result.get("last_material_change_at")
                if outcome == "material_change"
                else (previous or {}).get("last_material_change_at")
            ),
            "last_error": None,
        }

    if outcome not in {"pending", "failed", "disabled"}:
        raise StateBatchError(f"Unsupported pair outcome: {outcome!r}")

    if outcome in {"pending", "failed"} and not result.get("last_error"):
        raise StateBatchError(f"Outcome {outcome!r} requires last_error.")

    if result.get("preserve_previous_good_state", True) and _has_good_material_state(
        previous
    ):
        return {
            "status": outcome,
            "last_checked_at": last_checked_at,
            "state_hash": previous["state_hash"],
            "material_state": copy.deepcopy(previous["material_state"]),
            "confidence": previous.get("confidence"),
            "source_fingerprints": source_fingerprints,
            "last_material_change_at": previous.get("last_material_change_at"),
            "last_error": result.get("last_error"),
        }

    return {
        "status": outcome,
        "last_checked_at": last_checked_at,
        "state_hash": None,
        "material_state": {},
        "confidence": None,
        "source_fingerprints": source_fingerprints,
        "last_material_change_at": None,
        "last_error": result.get("last_error"),
    }


def _target_status(observations: dict[str, dict[str, Any]]) -> str:
    statuses = {profile_state.get("status") for profile_state in observations.values()}
    if "failed" in statuses:
        return "failed"
    if statuses & {"pending", "never_checked"}:
        return "pending"
    if statuses == {"disabled"}:
        return "disabled"
    return "active"


def apply_checkpoint(
    state: dict[str, Any], checkpoint: dict[str, Any]
) -> dict[str, Any]:
    """Return the complete replacement state for one successful checkpoint."""

    if state.get("job_id") != checkpoint.get("job_id"):
        raise StateBatchError(
            f"Checkpoint job_id {checkpoint.get('job_id')!r} does not match "
            f"state job_id {state.get('job_id')!r}."
        )
    if state.get("revision") != checkpoint.get("expected_revision"):
        raise StateBatchError(
            f"Expected revision {checkpoint.get('expected_revision')}, "
            f"found {state.get('revision')}."
        )
    if checkpoint.get("status_after") == "pending" and not checkpoint.get(
        "pending_after"
    ):
        raise StateBatchError("status_after 'pending' requires pending_after true.")
    if checkpoint.get("status_after") in {"idle", "succeeded"} and checkpoint.get(
        "pending_after"
    ):
        raise StateBatchError(
            f"status_after {checkpoint.get('status_after')!r} requires "
            "pending_after false."
        )
    if checkpoint.get("mode") == "bootstrap" and any(
        pair.get("outcome") == "material_change"
        for pair in checkpoint.get("pair_results") or []
    ):
        raise StateBatchError(
            "Bootstrap State-only checkpoints cannot contain material_change outcomes; "
            "publish those through the atomic State + JSON event + Markdown "
            "event bundle."
        )

    result = copy.deepcopy(state)
    evaluated_at = checkpoint["evaluated_at"]
    targets = result.setdefault("job_state", {}).setdefault("targets", {})
    target_sets = result["job_state"].setdefault("target_sets", {})

    seen_pairs: set[tuple[str, str]] = set()
    touched_targets: set[str] = set()

    for pair in checkpoint["pair_results"]:
        target_id = pair["target_id"]
        profile_id = pair["profile_id"]
        pair_key = (target_id, profile_id)
        if pair_key in seen_pairs:
            raise StateBatchError(
                f"Checkpoint contains duplicate pair {target_id}/{profile_id}."
            )
        seen_pairs.add(pair_key)
        touched_targets.add(target_id)

        target = targets.get(target_id)
        if target is None:
            target = {
                "entity_fingerprint": pair["entity_fingerprint"],
                "target_set_ids": sorted(set(pair["target_set_ids"])),
                "last_checked_at": evaluated_at,
                "status": "pending",
                "observations": {},
            }
            targets[target_id] = target
        else:
            if target.get("entity_fingerprint") != pair["entity_fingerprint"]:
                raise StateBatchError(
                    f"Entity fingerprint changed for {target_id!r}: "
                    f"{target.get('entity_fingerprint')!r} -> "
                    f"{pair['entity_fingerprint']!r}."
                )
            target["target_set_ids"] = _merge_unique(
                target.get("target_set_ids") or [],
                pair["target_set_ids"],
            )

        observations = target.setdefault("observations", {})
        previous = observations.get(profile_id)
        observations[profile_id] = _profile_state_from_result(
            previous,
            pair,
            evaluated_at,
        )
        target["last_checked_at"] = pair.get("last_checked_at") or evaluated_at

    for target_id in touched_targets:
        target = targets[target_id]
        target["status"] = _target_status(target.get("observations") or {})

    for target_set_id, update in (checkpoint.get("target_set_updates") or {}).items():
        target_sets[target_set_id] = {
            "last_resolved_at": update.get("last_resolved_at") or evaluated_at,
            "resolved_target_ids": sorted(set(update["resolved_target_ids"])),
        }

    result["revision"] = state["revision"] + 1
    result["status"] = checkpoint["status_after"]
    result["pending"] = checkpoint["pending_after"]
    result["last_evaluated_at"] = evaluated_at
    result["last_successful_run"] = evaluated_at
    result["last_processed_key"] = checkpoint["checkpoint_id"]
    result["last_error"] = checkpoint.get("job_error_after")

    fingerprints = result.setdefault("last_input_fingerprints", {})
    fingerprints.update(checkpoint.get("input_fingerprints") or {})

    recent_events = list(result.get("recent_events") or [])
    recent_events.append(checkpoint["recent_event"])
    keep_recent = checkpoint.get("keep_recent_events", 20)
    result["recent_events"] = recent_events[-keep_recent:] if keep_recent else []

    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--state-schema", type=Path, required=True)
    parser.add_argument("--checkpoint-schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print a compact machine-readable summary after writing the output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        state = load_json(args.state)
        checkpoint = load_json(args.checkpoint)
        validate_against_schema(checkpoint, args.checkpoint_schema, "checkpoint")
        validate_against_schema(state, args.state_schema, "input state")
        replacement = apply_checkpoint(state, checkpoint)
        validate_against_schema(replacement, args.state_schema, "replacement state")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(replacement, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except StateBatchError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.summary_json:
        print(
            json.dumps(
                {
                    "job_id": replacement["job_id"],
                    "revision_before": state["revision"],
                    "revision_after": replacement["revision"],
                    "checkpoint_id": checkpoint["checkpoint_id"],
                    "pairs_applied": len(checkpoint["pair_results"]),
                    "status_after": replacement["status"],
                    "pending_after": replacement["pending"],
                    "output": str(args.output),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
