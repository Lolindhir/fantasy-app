from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

SOURCE_TRIGGER_REASONS = {
    "relevant_source_or_heartbeat_change",
    "relevant_league_or_player_input_change",
}


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _duration_seconds(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    delta = (_parse_datetime(end) - _parse_datetime(start)).total_seconds()
    return max(0, round(delta))


def build_summary(
    *,
    event_name: str,
    trigger_reason: str,
    trigger_commit_sha: str | None,
    trigger_commit_at: str | None,
    materializer_started_at: str,
    published_at: str | None,
    published_commit_sha: str | None,
    outcome: str,
) -> str:
    queue_seconds = _duration_seconds(trigger_commit_at, materializer_started_at)
    publish_seconds = _duration_seconds(materializer_started_at, published_at)
    end_to_end_seconds = _duration_seconds(trigger_commit_at, published_at)
    source_push = event_name == "push" and trigger_reason in SOURCE_TRIGGER_REASONS

    def value(raw: object | None) -> str:
        return "n/a" if raw is None or raw == "" else str(raw)

    lines = [
        "### Fantasy Operations materialization observability",
        "",
        "Observability only; these timings never determine Freshness Gate readiness.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Outcome | `{outcome}` |",
        f"| Event | `{event_name}` |",
        f"| Trigger reason | `{trigger_reason}` |",
        f"| Source-triggered push | `{str(source_push).lower()}` |",
        f"| Trigger commit | `{value(trigger_commit_sha)}` |",
        f"| Trigger commit at | `{value(trigger_commit_at)}` |",
        f"| Materializer started at | `{materializer_started_at}` |",
        f"| Published state commit | `{value(published_commit_sha)}` |",
        f"| Published at | `{value(published_at)}` |",
        f"| Trigger → materializer start | `{value(None if queue_seconds is None else f'{queue_seconds}s')}` |",
        f"| Materializer start → published state | `{value(None if publish_seconds is None else f'{publish_seconds}s')}` |",
        f"| Trigger → published state | `{value(None if end_to_end_seconds is None else f'{end_to_end_seconds}s')}` |",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write Fantasy Operations materialization latency observability to a GitHub Actions step summary."
    )
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--trigger-reason", required=True)
    parser.add_argument("--trigger-commit-sha")
    parser.add_argument("--trigger-commit-at")
    parser.add_argument("--materializer-started-at", required=True)
    parser.add_argument("--published-at")
    parser.add_argument("--published-commit-sha")
    parser.add_argument("--outcome", choices=("published", "no_changes"), required=True)
    parser.add_argument("--summary-path", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(
        event_name=args.event_name,
        trigger_reason=args.trigger_reason,
        trigger_commit_sha=args.trigger_commit_sha,
        trigger_commit_at=args.trigger_commit_at,
        materializer_started_at=args.materializer_started_at,
        published_at=args.published_at,
        published_commit_sha=args.published_commit_sha,
        outcome=args.outcome,
    )
    path = Path(args.summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(summary)
    print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
