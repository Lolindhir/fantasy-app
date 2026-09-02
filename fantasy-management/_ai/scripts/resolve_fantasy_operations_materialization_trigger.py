from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime

SOURCE_INPUT_PREFIXES = (
    "fantasy-management/sources/external-rankings/",
    "fantasy-management/sources/external-signals/",
    "fantasy-management/sources/refresh-status/",
)
GENERATED_OPERATIONS_PREFIX = "fantasy-management/generated/operations/"
CORE_INPUT_PATHS = {
    "public/data/League.json",
    "public/data/Players.json",
    "public/data/Timestamps.json",
}
MATERIALIZATION_DEFINITION_PREFIXES = (
    "fantasy-management/automation/",
    "fantasy-management/_ai/scripts/",
    "fantasy-management/_ai/schemas/",
)
MATERIALIZATION_DEFINITION_PATHS = {
    "fantasy-management/_ai/operations-source-catalog.json",
    "fantasy-management/_ai/operations-source-catalog-offense-projections.json",
    "fantasy-management/_ai/operations-external-signal-catalog.json",
    "fantasy-management/_ai/schema-list.json",
    "fantasy-management/_ai/FANTASY_OPERATIONS_ARCHITECTURE.md",
    "fantasy-management/_ai/MONITORING_AND_WEEKLY_DECISIONS.md",
    ".github/workflows/materialize-fantasy-operations-inputs.yml",
}


@dataclass(frozen=True)
class TriggerDecision:
    run: bool
    reason: str


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def _is_source_input(path: str) -> bool:
    normalized = _normalize(path)
    return any(normalized.startswith(prefix) for prefix in SOURCE_INPUT_PREFIXES)


def _is_generated_operations(path: str) -> bool:
    return _normalize(path).startswith(GENERATED_OPERATIONS_PREFIX)


def _is_materialization_definition(path: str) -> bool:
    normalized = _normalize(path)
    return normalized in MATERIALIZATION_DEFINITION_PATHS or any(
        normalized.startswith(prefix) for prefix in MATERIALIZATION_DEFINITION_PREFIXES
    )


def decide(
    *,
    event_name: str,
    schedule_expression: str = "",
    changed_files: list[str] | None = None,
    now: datetime | None = None,
) -> TriggerDecision:
    if event_name == "pull_request":
        return TriggerDecision(False, "pull_request_validation_only")

    if event_name == "workflow_dispatch":
        return TriggerDecision(True, "manual_materialization")

    if event_name == "repository_dispatch":
        return TriggerDecision(True, "scheduled_central_dispatch")

    if event_name == "schedule":
        return TriggerDecision(True, "scheduled_0645_berlin_catch_up")

    if event_name != "push":
        return TriggerDecision(True, f"conservative_unknown_event_{event_name or 'empty'}")

    files = [_normalize(path) for path in (changed_files or []) if path]
    if not files:
        return TriggerDecision(True, "push_without_changed_file_context")

    if all(_is_generated_operations(path) for path in files):
        return TriggerDecision(False, "generated_operations_only_change")

    if any(_is_source_input(path) for path in files):
        return TriggerDecision(True, "relevant_source_or_heartbeat_change")

    if any(path in CORE_INPUT_PATHS for path in files):
        return TriggerDecision(True, "relevant_league_or_player_input_change")

    if any(_is_materialization_definition(path) for path in files):
        return TriggerDecision(True, "materialization_definition_change")

    return TriggerDecision(False, "irrelevant_push")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve whether Fantasy Operations materialization should run for the current workflow trigger."
    )
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--schedule-expression", default="")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument(
        "--berlin-now",
        help="Optional ISO timestamp retained for deterministic tests/debugging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.fromisoformat(args.berlin_now) if args.berlin_now else None
    decision = decide(
        event_name=args.event_name,
        schedule_expression=args.schedule_expression,
        changed_files=args.changed_file,
        now=now,
    )
    print(f"run={'true' if decision.run else 'false'}")
    print(f"reason={decision.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
