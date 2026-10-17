"""Read-only discovery of immutable combined Sleeper add/drop Source history.

Expected future 4A.3 layout:
  data-source/market/roster-activity/sleeper/snapshots/
    YYYY-MM-DD/HHmmssZ-<sha8>/observation.json

This reader validates observed UTC time against its directory and makes no
synthetic backfill from latest.json or Git history. Snapshots are combined
Source facts; each registered add/drop dataset is a *view* of one observation.
No writer, provider fetch or production archival activation is provided here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INTRADAY = re.compile(r"^(\d{6})Z-([0-9a-f]{8})$")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SleeperSnapshot:
    day: date
    observed_at: datetime
    key: str
    observation_file: Path


def discover_sleeper_snapshots(root: Path) -> list[SleeperSnapshot]:
    """Enumerate only complete and timestamp-valid combined Source snapshots."""
    if not root.exists():
        return []
    if not root.is_dir():
        raise ValueError(f"Sleeper snapshot root must be a directory: {root}")
    snapshots: list[SleeperSnapshot] = []
    for day_dir in sorted(root.iterdir()):
        if not day_dir.is_dir() or not _DAY.fullmatch(day_dir.name):
            continue
        day = date.fromisoformat(day_dir.name)
        for entry in sorted(day_dir.iterdir()):
            if not entry.is_dir() or not _INTRADAY.fullmatch(entry.name):
                continue
            match = _INTRADAY.fullmatch(entry.name)
            assert match is not None
            file = entry / "observation.json"
            if not file.is_file():
                raise ValueError(f"Missing immutable Sleeper observation: {file}")
            try:
                doc = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid immutable Sleeper observation: {file}") from exc
            if not isinstance(doc, dict):
                raise ValueError(f"Sleeper observation must be an object: {file}")
            if doc.get("provider") != "sleeper" or doc.get("signal_kind") != "roster_activity":
                raise ValueError(f"Sleeper snapshot provider/signal mismatch: {file}")
            if type(doc.get("schema_version")) is not int or doc["schema_version"] != 1:
                raise ValueError(f"Unsupported Sleeper snapshot schema version: {file}")
            if "comparison" in doc:
                raise ValueError(f"Derived consumer comparison leaked into Sleeper Source: {file}")
            semantic = doc.get("semantic_fingerprint")
            if not isinstance(semantic, str) or not _FINGERPRINT.fullmatch(semantic):
                raise ValueError(f"Missing Sleeper Source fingerprint: {file}")
            if semantic[:8] != match.group(2):
                raise ValueError(f"Sleeper path/source fingerprint mismatch: {file}")
            stamp = doc.get("generated_at")
            if not isinstance(stamp, str):
                raise ValueError(f"Sleeper observation timestamp missing: {file}")
            try:
                observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"Invalid Sleeper observation timestamp: {file}") from exc
            if observed.tzinfo is None or observed.utcoffset() is None:
                raise ValueError(f"Sleeper observation timestamp lacks offset: {file}")
            observed = observed.astimezone(timezone.utc)
            if observed.date() != day or observed.strftime("%H%M%S") != match.group(1):
                raise ValueError(f"Sleeper path/UTC observation time mismatch: {file}")
            snapshots.append(
                SleeperSnapshot(day, observed, f"{day_dir.name}/{entry.name}", file)
            )
    return sorted(snapshots, key=lambda x: (x.observed_at, x.key))
