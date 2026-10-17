"""Source-only, no-write odds candidate preflight for #471.

Reuses the registered nflverse projection and existing canonical phase-1 odds
builder. All outputs are kept in memory; does not update raw CSV, canonical
partitions, metadata, derived data or the main Git branch.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import load_json, load_registry
from nfl_source_data_lib.phase1 import _build_schedule_odds
from nfl_source_data_lib.source_projection import project_schedule_odds
from odds_observation_buffer import read_upstream_lines

DATASET_ID = "nflverse.schedule-odds"


def source_candidate(
    root: Path,
    upstream_csv: Path,
    season: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute full season canonical odds from upstream CSV without writes.

    Includes bookmaker price fields as Source evidence. The caller decides
    significance for the NFL Game consumer exclusively using Spread/Total.
    """
    dataset = next((d for d in load_registry(root) if d.id == DATASET_ID), None)
    if dataset is None:
        raise ValueError("Canonical odds source registry dataset is unavailable")
    schedules = root / DATA_SOURCE_ROOT / "nfl" / "schedules"
    schedule_index: dict[str, dict[str, Any]] = {}
    for path in sorted(schedules.glob("*.json")):
        document = load_json(path)
        if not isinstance(document, dict) or not isinstance(document.get("Games"), list):
            raise ValueError(f"Invalid canonical schedule partition: {path}")
        for game in document["Games"]:
            key = game.get("GameID")
            if key in schedule_index:
                raise ValueError(f"Duplicate canonical GameID: {key}")
            schedule_index[key] = {
                "Season": document["Season"],
                "GameType": game["GameType"],
                "Week": game["Week"],
            }
    if not schedule_index:
        raise ValueError("No canonical schedules to validate odds against")
    expected = {key for key in schedule_index if key.startswith(f"{season}_")}
    read_upstream_lines(upstream_csv, season, expected)
    with tempfile.TemporaryDirectory(prefix="scoped-odds-preflight-") as temp:
        projected = Path(temp) / "odds-projected.csv"
        project_schedule_odds(upstream_csv, projected)
        temp_dataset = replace(dataset, raw_path=projected)
        partitions, audit, _ = _build_schedule_odds(
            root, temp_dataset, schedule_index, observation_season=season, force=False
        )
    matching = [payload for path, payload in partitions if path.name == f"{season}.json"]
    if len(matching) != 1:
        raise ValueError("Expected exactly one current-season canonical odds candidate")
    return matching[0], audit
