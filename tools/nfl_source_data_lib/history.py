from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .common import Dataset

HISTORICAL_BANDS = {
    "nflverse.rosters": {"start": 1999, "canonical": "rosters"},
    "nflverse.weekly-rosters": {"start": 2002, "canonical": "weekly-rosters"},
    "nflverse.player-stats": {"start": 1999, "canonical": "player-stats"},
    "nflverse.snap-counts": {
        "start": 2012,
        "canonical": "snap-counts",
        "knownUnavailable": {
            2012: (
                "Current nflverse snap_counts_2012 release asset is schema-only with zero data rows; "
                "verified 2026-09-08. Missing snap facts remain unavailable, never zero."
            ),
        },
    },
}


def known_unavailable_reason(dataset_id: str, season: int) -> str | None:
    policy = HISTORICAL_BANDS.get(dataset_id) or {}
    unavailable = policy.get("knownUnavailable") or {}
    reason = unavailable.get(season)
    return str(reason) if reason else None


def select_missing_historical_partitions(
    repo_root: Path,
    datasets: Iterable[Dataset],
    *,
    current_season: int,
    limit: int,
) -> list[tuple[str, int]]:
    """Select a bounded newest-first batch of missing required historical raw partitions."""
    if limit < 0:
        raise ValueError("Historical backfill limit must be >= 0")
    if limit == 0:
        return []

    eligible = [
        dataset
        for dataset in datasets
        if dataset.is_season_partitioned and dataset.id in HISTORICAL_BANDS
    ]
    if not eligible:
        return []

    earliest = min(int(HISTORICAL_BANDS[dataset.id]["start"]) for dataset in eligible)
    selected: list[tuple[str, int]] = []
    for season in range(current_season - 1, earliest - 1, -1):
        for dataset in eligible:
            start = int(HISTORICAL_BANDS[dataset.id]["start"])
            if season < start or known_unavailable_reason(dataset.id, season):
                continue
            raw_path = dataset.raw_path_for(season)
            if not raw_path.is_absolute():
                raw_path = repo_root / raw_path
            if raw_path.exists():
                continue
            selected.append((dataset.id, season))
            if len(selected) >= limit:
                return selected
    return selected
