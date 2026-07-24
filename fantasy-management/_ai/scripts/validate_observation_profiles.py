#!/usr/bin/env python3
"""Validate cross-field invariants for Observation Profile source bindings.

This complements validate_automation.py. JSON Schema validates binding shape;
this script validates signal references, primary-source determinism, source-type
compatibility and required repository locations.

Usage:

  python fantasy-management/_ai/scripts/validate_observation_profiles.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from validate_automation import (
    Report,
    discover_json_by_id,
    load_json,
    repo_root_from_script,
)


def validate_profile_source_bindings(
    profile_path: Path,
    profile: dict[str, Any],
    root: Path,
    report: Report,
) -> None:
    signals = profile.get("signals") or []
    signal_by_id: dict[str, dict[str, Any]] = {}

    for signal in signals:
        signal_id = str(signal.get("id", "")).strip()
        if not signal_id:
            continue
        if signal_id in signal_by_id:
            report.error(profile_path, f"Duplicate signal id {signal_id!r}.")
        else:
            signal_by_id[signal_id] = signal

    bindings = profile.get("source_bindings")
    if bindings is None:
        return

    binding_ids: set[str] = set()
    roles_by_signal: dict[str, list[str]] = {signal_id: [] for signal_id in signal_by_id}

    for binding in bindings:
        binding_id = str(binding.get("id", "")).strip()
        if binding_id in binding_ids:
            report.error(profile_path, f"Duplicate source binding id {binding_id!r}.")
        binding_ids.add(binding_id)

        role = str(binding.get("role", "")).strip()
        source_type = str(binding.get("source_type", "")).strip()
        access = binding.get("access") or {}
        access_type = str(access.get("type", "")).strip()
        location = access.get("location")
        entity_join = binding.get("entity_join") or []

        if role == "derived":
            if access_type != "derived":
                report.error(
                    profile_path,
                    f"Derived binding {binding_id!r} must use derived access.",
                )
            if entity_join:
                report.error(
                    profile_path,
                    f"Derived binding {binding_id!r} must not define entity joins.",
                )
        elif not entity_join:
            report.error(
                profile_path,
                f"Non-derived binding {binding_id!r} requires entity_join fallbacks.",
            )

        if access_type in {"repo_latest_pointer", "repo_file"}:
            repo_path = root / str(location or "")
            if not repo_path.is_file():
                report.error(
                    profile_path,
                    f"Binding {binding_id!r} references missing repository source "
                    f"{str(location)!r}.",
                )
            elif access_type == "repo_latest_pointer":
                pointer = load_json(repo_path, report)
                if not isinstance(pointer, dict):
                    report.error(
                        profile_path,
                        f"Binding {binding_id!r} latest pointer must be a JSON object.",
                    )

        for signal_id, field_selector in (binding.get("signal_mappings") or {}).items():
            signal = signal_by_id.get(signal_id)
            if signal is None:
                report.error(
                    profile_path,
                    f"Binding {binding_id!r} maps unknown signal {signal_id!r}.",
                )
                continue

            source_types = signal.get("source_types") or []
            if source_type not in source_types:
                report.error(
                    profile_path,
                    f"Binding {binding_id!r} source_type {source_type!r} is not "
                    f"allowed by signal {signal_id!r}.",
                )

            if not str(field_selector).strip():
                report.error(
                    profile_path,
                    f"Binding {binding_id!r} has an empty field selector for "
                    f"{signal_id!r}.",
                )

            roles_by_signal[signal_id].append(role)

    for signal_id, signal in signal_by_id.items():
        roles = roles_by_signal.get(signal_id) or []
        source_types = set(signal.get("source_types") or [])

        if not roles:
            report.error(
                profile_path,
                f"Profile declares source_bindings but signal {signal_id!r} is unmapped.",
            )
            continue

        primary_count = roles.count("primary")
        derived_count = roles.count("derived")

        if source_types == {"derived"}:
            if derived_count != 1:
                report.error(
                    profile_path,
                    f"Derived signal {signal_id!r} requires exactly one derived binding.",
                )
            if primary_count:
                report.error(
                    profile_path,
                    f"Derived signal {signal_id!r} cannot have a primary binding.",
                )
        else:
            if primary_count != 1:
                report.error(
                    profile_path,
                    f"Signal {signal_id!r} requires exactly one primary binding; "
                    f"found {primary_count}.",
                )


def validate_observation_profiles(root: Path | None = None) -> Report:
    root = (root or repo_root_from_script()).resolve()
    report = Report()
    automation_root = root / "fantasy-management/automation"
    schema_root = root / "fantasy-management/_ai/schemas"

    profiles = discover_json_by_id(
        automation_root / "profiles",
        schema_root / "automation-observation-profile.schema.json",
        report,
    )

    for profile_path, profile in profiles.values():
        validate_profile_source_bindings(profile_path, profile, root, report)

    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the root inferred from this script.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = validate_observation_profiles(args.root)
    if args.json:
        import json

        print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    else:
        report.print_text()
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
