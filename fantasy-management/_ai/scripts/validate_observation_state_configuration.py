#!/usr/bin/env python3
"""Validate fully-sharded entity-observation targets against active config.

The generic automation validator validates jobs, profiles, target sets and the
bounded global state header.  This companion check materializes the canonical
Target-Shard state and reuses the same cross-file target/profile validation so
moving target payloads out of the global header does not weaken validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import validate_automation as automation
import validate_observation_state_shards as shards


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    automation_root = root / "fantasy-management/automation"
    schema_root = root / "fantasy-management/_ai/schemas"
    report = automation.Report()

    profiles = automation.discover_json_by_id(
        automation_root / "profiles",
        schema_root / "automation-observation-profile.schema.json",
        report,
    )
    target_sets = automation.discover_json_by_id(
        automation_root / "target-sets",
        schema_root / "automation-target-set.schema.json",
        report,
    )
    manual_targets, selector_contracts = automation.validate_target_sets(
        target_sets,
        profiles,
        report,
    )

    try:
        effective = shards.effective_state(
            automation_root / "state/entity-observation.json",
            automation_root / "state/entity-observation-targets",
        )
    except shards.ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    state_targets = ((effective.get("job_state") or {}).get("targets") or {})
    automation.validate_observation_state_targets(
        state_targets,
        manual_targets,
        selector_contracts,
        report,
        automation_root / "state/entity-observation-targets",
    )

    report.print_text()
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
