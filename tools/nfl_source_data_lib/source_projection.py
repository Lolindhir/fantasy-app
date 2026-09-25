from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any

SPECIAL_TEAMS_FUMBLE_PROJECTION_ID = "nflverse-special-teams-fumble-events"
SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION = 1

SPECIAL_TEAMS_PLAY_TYPES = {"extra_point", "field_goal", "kickoff", "punt"}

SPECIAL_TEAMS_FUMBLE_FIELDS = (
    "season",
    "season_type",
    "week",
    "game_id",
    "play_id",
    "play_type",
    "special",
    "home_team",
    "away_team",
    "forced_fumble_player_1_team",
    "forced_fumble_player_1_player_id",
    "forced_fumble_player_2_team",
    "forced_fumble_player_2_player_id",
    "fumbled_1_team",
    "fumbled_2_team",
    "fumble_recovery_1_team",
    "fumble_recovery_1_player_id",
    "fumble_recovery_2_team",
    "fumble_recovery_2_player_id",
)

_EVENT_PLAYER_FIELDS = (
    "forced_fumble_player_1_player_id",
    "forced_fumble_player_2_player_id",
    "fumble_recovery_1_player_id",
    "fumble_recovery_2_player_id",
)

SUPPORTED_SOURCE_PROJECTIONS = {
    (SPECIAL_TEAMS_FUMBLE_PROJECTION_ID, SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION): "csv.gz",
}


def _is_one(value: Any) -> bool:
    try:
        return float(str(value).strip()) == 1.0
    except (TypeError, ValueError):
        return False


def _has_event_player(row: dict[str, str]) -> bool:
    return any((row.get(field) or "").strip() for field in _EVENT_PLAYER_FIELDS)


def project_special_teams_fumble_events(upstream_path: Path, output_path: Path) -> dict[str, Any]:
    records: list[dict[str, str]] = []
    with gzip.open(upstream_path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(set(SPECIAL_TEAMS_FUMBLE_FIELDS) - columns)
        if missing:
            raise ValueError(
                "nflverse PBP is missing fields required for special-teams fumble projection: "
                + ", ".join(missing)
            )

        source_rows = 0
        special_rows = 0
        for row in reader:
            source_rows += 1
            if not _is_one(row.get("special")):
                continue
            special_rows += 1
            if not _has_event_player(row):
                continue
            play_type = (row.get("play_type") or "").strip()
            if play_type not in SPECIAL_TEAMS_PLAY_TYPES:
                raise ValueError(
                    "nflverse PBP marked an unsupported play_type as special for a fumble event: "
                    f"{play_type or '<missing>'} game={row.get('game_id')} play={row.get('play_id')}"
                )
            records.append({field: row.get(field, "") for field in SPECIAL_TEAMS_FUMBLE_FIELDS})

    records.sort(
        key=lambda row: (
            row.get("season") or "",
            row.get("week") or "",
            row.get("game_id") or "",
            row.get("play_id") or "",
        )
    )
    payload = {
        "SchemaVersion": 1,
        "Projection": {
            "ID": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
            "Version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
        },
        "Columns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
        "Records": records,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "sourceRowCount": source_rows,
        "specialTeamsRowCount": special_rows,
        "projectedRowCount": len(records),
    }


def project_source(
    projection_id: str,
    projection_version: int,
    upstream_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    key = (projection_id, projection_version)
    if key == (
        SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
        SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
    ):
        return project_special_teams_fumble_events(upstream_path, output_path)
    raise ValueError(
        f"Unsupported source projection: id={projection_id} version={projection_version}"
    )
