from __future__ import annotations

from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from .common import Dataset, load_json, write_json_if_changed
from .materialize import _observation_season
from .phase1 import _build_schedule_odds, _build_schedules

SCHEDULE_DATASET_ID = "nflverse.schedules"
ODDS_DATASET_ID = "nflverse.schedule-odds"
SCHEDULE_ODDS_SCOPE = "schedule-odds"
ODDS_WRITE_SET = f"{DATA_SOURCE_ROOT}/nfl/schedule-odds/**"


def materialize_schedule_odds(
    repo_root: Path,
    datasets: dict[str, Dataset],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Reuse full canonical builders and publish only schedule-odds.

    Fail closed if evaluated schedule evidence is not yet represented by
    the published canonical schedule: a normal full Source Sync must first
    publish that schedule revision.
    """
    missing = [key for key in (SCHEDULE_DATASET_ID, ODDS_DATASET_ID) if key not in datasets]
    if missing:
        raise ValueError("Scoped schedule-odds materialization requires datasets: " + ", ".join(missing))
    for key in (SCHEDULE_DATASET_ID, ODDS_DATASET_ID):
        if not datasets[key].raw_path.is_file():
            raise FileNotFoundError(
                f"Cannot materialize schedule-odds without raw dataset: {datasets[key].raw_path}"
            )

    observation_season = _observation_season(repo_root)
    schedule_outputs, schedule_diagnostics, _, schedule_index = _build_schedules(
        repo_root, datasets[SCHEDULE_DATASET_ID], observation_season, force=force
    )
    if not schedule_index:
        raise ValueError("Scoped schedule-odds materialization requires a non-empty schedule index")

    for path, effective in schedule_outputs:
        relative = path.relative_to(repo_root).as_posix()
        if not relative.startswith(f"{DATA_SOURCE_ROOT}/nfl/schedules/"):
            raise ValueError(f"Unexpected canonical schedule read path: {relative}")
        if load_json(path) != effective:
            raise ValueError(
                "Canonical NFL schedule is missing or stale relative to raw schedule evidence: "
                + relative
                + "; run the full NFL Source Sync before publishing odds"
            )

    odds_outputs, odds_diagnostics, preserved = _build_schedule_odds(
        repo_root, datasets[ODDS_DATASET_ID], schedule_index, observation_season, force=force
    )
    changed_paths: list[str] = []
    for path, payload in odds_outputs:
        relative = path.relative_to(repo_root).as_posix()
        if not relative.startswith(f"{DATA_SOURCE_ROOT}/nfl/schedule-odds/"):
            raise ValueError(f"Unexpected canonical Odds output path: {relative}")
        if write_json_if_changed(path, payload):
            changed_paths.append(relative)

    return {
        "scope": SCHEDULE_ODDS_SCOPE,
        "observationSeason": observation_season,
        "writeSet": [ODDS_WRITE_SET],
        "scheduleDiagnostics": schedule_diagnostics,
        "oddsDiagnostics": odds_diagnostics,
        "oddsCanonicalFileCount": len(odds_outputs),
        "oddsFilesChanged": len(changed_paths),
        "oddsChangedPaths": changed_paths,
        "oddsPartitionsPreserved": preserved,
    }
