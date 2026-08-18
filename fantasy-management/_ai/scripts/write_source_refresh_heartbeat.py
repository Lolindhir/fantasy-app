from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
DEFAULT_OUTPUT_DIR = Path("fantasy-management/sources/refresh-status")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def detect_content_changed(content_paths: list[str]) -> bool:
    if not content_paths:
        return False
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *content_paths],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def build_heartbeat(
    *,
    source_id: str,
    workflow: str,
    trigger: str,
    content_paths: list[str],
    content_changed: bool,
    checked_at: datetime,
) -> dict[str, object]:
    checked_utc = _as_utc(checked_at)
    checked_berlin = checked_utc.astimezone(BERLIN)
    return {
        "schema_version": 1,
        "source_id": source_id,
        "workflow": workflow,
        "status": "success",
        "checked_at": _iso_z(checked_utc),
        "berlin_date": checked_berlin.date().isoformat(),
        "trigger": trigger,
        "content_changed": content_changed,
        "content_paths": content_paths,
    }


def write_heartbeat(
    *,
    output_path: Path,
    source_id: str,
    workflow: str,
    trigger: str,
    content_paths: list[str],
    checked_at: datetime | None = None,
) -> dict[str, object]:
    heartbeat = build_heartbeat(
        source_id=source_id,
        workflow=workflow,
        trigger=trigger,
        content_paths=content_paths,
        content_changed=detect_content_changed(content_paths),
        checked_at=checked_at or _utc_now(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(heartbeat, indent=2) + "\n", encoding="utf-8")
    return heartbeat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a successful source-refresh heartbeat, including whether source content changed."
    )
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--trigger", required=True)
    parser.add_argument("--content-path", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--checked-at", help="Optional ISO timestamp for deterministic tests/debugging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{args.source_id}.json"
    checked_at = datetime.fromisoformat(args.checked_at.replace("Z", "+00:00")) if args.checked_at else None
    heartbeat = write_heartbeat(
        output_path=output,
        source_id=args.source_id,
        workflow=args.workflow,
        trigger=args.trigger,
        content_paths=args.content_path,
        checked_at=checked_at,
    )
    print(
        "Recorded successful refresh heartbeat for {} at {}; content_changed={}.".format(
            heartbeat["source_id"], heartbeat["checked_at"], heartbeat["content_changed"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
