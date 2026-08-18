from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
MORNING_BATCH_START_MINUTE = 5 * 60
MORNING_BATCH_END_MINUTE = 6 * 60 + 45
SCHEDULE_BY_UTC_OFFSET = {
    120: "45 4 * * *",
    60: "45 5 * * *",
}
EXTERNAL_SOURCE_PREFIXES = (
    "fantasy-management/sources/external-rankings/",
    "fantasy-management/sources/external-signals/",
    "fantasy-management/sources/refresh-status/",
)


@dataclass(frozen=True)
class TriggerDecision:
    run: bool
    reason: str


def _berlin_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(BERLIN)
    if now.tzinfo is None:
        return now.replace(tzinfo=BERLIN)
    return now.astimezone(BERLIN)


def _minute_of_day(now: datetime) -> int:
    return now.hour * 60 + now.minute


def _is_external_source_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in EXTERNAL_SOURCE_PREFIXES)


def decide(
    *,
    event_name: str,
    schedule_expression: str = "",
    changed_files: list[str] | None = None,
    now: datetime | None = None,
) -> TriggerDecision:
    current = _berlin_now(now)

    if event_name == "workflow_dispatch":
        return TriggerDecision(True, "manual_materialization")

    if event_name == "schedule":
        offset = current.utcoffset()
        if offset is None:
            return TriggerDecision(False, "berlin_utc_offset_unavailable")
        offset_minutes = int(offset.total_seconds() // 60)
        expected = SCHEDULE_BY_UTC_OFFSET.get(offset_minutes)
        if expected is None:
            return TriggerDecision(False, f"unsupported_berlin_utc_offset_{offset_minutes}")
        if schedule_expression != expected:
            return TriggerDecision(False, "inactive_dst_companion_schedule")
        return TriggerDecision(True, "scheduled_0645_berlin_consolidation")

    if event_name != "push":
        return TriggerDecision(True, f"conservative_unknown_event_{event_name or 'empty'}")

    files = [path for path in (changed_files or []) if path]
    if not files:
        return TriggerDecision(True, "push_without_changed_file_context")

    only_external_sources = all(_is_external_source_path(path) for path in files)
    if not only_external_sources:
        return TriggerDecision(True, "immediate_non_external_input_change")

    minute = _minute_of_day(current)
    if MORNING_BATCH_START_MINUTE <= minute < MORNING_BATCH_END_MINUTE:
        return TriggerDecision(False, "batched_external_source_change_before_0645")

    return TriggerDecision(True, "external_source_change_outside_morning_batch_window")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve whether Fantasy Operations materialization should run for the current workflow trigger."
    )
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--schedule-expression", default="")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument(
        "--berlin-now",
        help="Optional ISO timestamp used for deterministic tests/debugging. Converted to Europe/Berlin.",
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
