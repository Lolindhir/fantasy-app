from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import Dataset, write_json_if_changed
from .materialize import _observation_season
from .phase1 import _build_game_finality, _build_schedules

SCHEDULE_DATASET_ID = "nflverse.schedules"
GAME_FINALITY_DATASET_ID = "nflverse.game-finality"
GAME_FINALITY_SCOPE = "game-finality"
GAME_FINALITY_WRITE_SET = "source-data/nfl/game-finality/**"


def materialize_game_finality(
    repo_root: Path,
    datasets: dict[str, Dataset],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Materialize only canonical game-finality outputs from their direct evidence.

    The scoped path deliberately reuses the exact schedule and finality builders
    from the full Phase-1 materializer. Schedule candidates are evaluated only to
    obtain the validated canonical game index; schedule outputs are not written.
    No player identity, provider mapping, Draft, Combine, roster, stats or full
    NFL audit work is performed here.
    """

    required_ids = (SCHEDULE_DATASET_ID, GAME_FINALITY_DATASET_ID)
    missing_datasets = [dataset_id for dataset_id in required_ids if dataset_id not in datasets]
    if missing_datasets:
        raise ValueError(
            "Scoped game-finality materialization requires dataset(s): "
            + ", ".join(missing_datasets)
        )

    for dataset_id in required_ids:
        dataset = datasets[dataset_id]
        if not dataset.raw_path.exists():
            raise FileNotFoundError(
                f"Cannot materialize {GAME_FINALITY_SCOPE} without raw dataset: {dataset.raw_path}"
            )

    observation_season = _observation_season(repo_root)
    schedule_outputs, schedule_diagnostics, schedule_preserved, schedule_index = _build_schedules(
        repo_root,
        datasets[SCHEDULE_DATASET_ID],
        observation_season,
        force=force,
    )
    if not schedule_index:
        raise ValueError("Scoped game-finality materialization requires a non-empty schedule index")

    finality_outputs, finality_diagnostics, finality_preserved = _build_game_finality(
        repo_root,
        datasets[GAME_FINALITY_DATASET_ID],
        schedule_index,
        observation_season,
        force=force,
    )

    changed_paths: list[str] = []
    for path, payload in finality_outputs:
        try:
            relative_path = path.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"Scoped game-finality output escapes repository root: {path}") from exc
        if not relative_path.startswith("source-data/nfl/game-finality/"):
            raise ValueError(
                f"Scoped game-finality materializer produced an unexpected output path: {relative_path}"
            )
        if write_json_if_changed(path, payload):
            changed_paths.append(relative_path)

    return {
        "scope": GAME_FINALITY_SCOPE,
        "observationSeason": observation_season,
        "writeSet": [GAME_FINALITY_WRITE_SET],
        "scheduleDependency": {
            "dataset": SCHEDULE_DATASET_ID,
            "canonicalWritesSuppressed": len(schedule_outputs),
            "frozenPartitionsObserved": schedule_preserved,
            **schedule_diagnostics,
        },
        "gameFinalityDiagnostics": finality_diagnostics,
        "gameFinalityCanonicalFileCount": len(finality_outputs),
        "gameFinalityFilesChanged": len(changed_paths),
        "gameFinalityChangedPaths": changed_paths,
        "gameFinalityPartitionsPreserved": finality_preserved,
    }
