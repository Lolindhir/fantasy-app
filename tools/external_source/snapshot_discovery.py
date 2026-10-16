"""Read-only discovery of legacy daily and append-only intraday market snapshots.

Source evidence layouts:
    snapshots/YYYY-MM-DD/{ranking.csv,metadata.json}
    snapshots/YYYY-MM-DD/HHmmssZ-<hash8>/{ranking.csv,metadata.json}

A legacy path identifies a day, *not* an observation instant. An instant is
available only if its persisted metadata states one. The intraday directory
name is an explicit UTC observation instant; provider update time is separate.
No provider data or published Source Evidence is written by this module.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTRADAY_RE = re.compile(r"^(\d{6})Z-([0-9a-f]{8})$")
OBSERVATION_FIELDS = ("fetched_at", "ranking_fetched_at")


@dataclass(frozen=True)
class Snapshot:
    day: date
    observed_at: datetime | None
    key: str
    directory: Path
    ranking_file: Path
    metadata_file: Path

    @property
    def sort_key(self) -> tuple[str, datetime, str]:
        # Unknown legacy instants sort before known instants within their day.
        instant = self.observed_at or datetime.combine(self.day, time.min, tzinfo=timezone.utc)
        return (self.day.isoformat(), instant, self.key)


def _metadata_instant(path: Path) -> datetime | None:
    if not path.is_file():
        return None
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError(f"Snapshot metadata must be an object: {path}")
    for field in OBSERVATION_FIELDS:
        raw = metadata.get(field)
        if not isinstance(raw, str) or not raw:
            continue
        try:
            instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid snapshot observation timestamp {field} in {path}") from exc
        if instant.tzinfo is None:
            raise ValueError(f"Snapshot observation timestamp must include timezone: {path}")
        return instant.astimezone(timezone.utc)
    return None


def _snapshot(directory: Path, day: date, key: str, *, intraday: bool, ranking_name: str) -> Snapshot:
    metadata_file = directory / "metadata.json"
    ranking_file = directory / ranking_name
    if intraday:
        match = INTRADAY_RE.fullmatch(directory.name)
        if not match:
            raise ValueError(f"Invalid intraday snapshot directory: {directory}")
        clock = datetime.strptime(match.group(1), "%H%M%S").time()
        observed_at = datetime.combine(day, clock, tzinfo=timezone.utc)
        if not metadata_file.is_file():
            raise ValueError(f"Intraday snapshot metadata missing: {metadata_file}")
        # Validate metadata independently; do not replace the UTC instant in the key
        # with a provider's own updated-at timestamp.
        _metadata_instant(metadata_file)
    else:
        observed_at = _metadata_instant(metadata_file)
    return Snapshot(day, observed_at, key, directory, ranking_file, metadata_file)


def discover_snapshots(root: Path, *, ranking_name: str = "ranking.csv") -> list[Snapshot]:
    """Discover complete ranked snapshots in stable chronological order.

    Legacy fixture/snapshot metadata is optional (unknown observation instant).
    Timestamped intraday snapshots require metadata; unrelated files or folders
    are ignored. No latest.json or output files are used as history.
    """
    if not root.is_dir():
        return []
    result: list[Snapshot] = []
    for day_dir in sorted(p for p in root.iterdir() if p.is_dir() and DAY_RE.fullmatch(p.name)):
        day = date.fromisoformat(day_dir.name)
        if (day_dir / ranking_name).is_file():
            result.append(_snapshot(day_dir, day, day_dir.name, intraday=False, ranking_name=ranking_name))
        for child in sorted(day_dir.iterdir()):
            if not child.is_dir() or not INTRADAY_RE.fullmatch(child.name):
                continue
            if not (child / ranking_name).is_file():
                raise ValueError(f"Intraday snapshot ranking missing: {child / ranking_name}")
            result.append(
                _snapshot(child, day, f"{day_dir.name}/{child.name}", intraday=True, ranking_name=ranking_name)
            )
    return sorted(result, key=lambda item: item.sort_key)
