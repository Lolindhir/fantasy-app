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

PLAYER_GAME_LONG_GAINS_PROJECTION_ID = "nflverse-player-game-long-gains"
PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION = 1

# One projected record per player and game and gain type: the provider play row with the
# maximum yards (lowest play_id on ties). Games lists every game present in the upstream
# play-by-play so that "no record" stays distinguishable from "game not published".
PLAYER_GAME_LONG_GAINS_FIELDS = (
    "season",
    "season_type",
    "week",
    "game_id",
    "gain_type",
    "player_id",
    "team",
    "play_id",
    "yards",
)

_LONG_GAINS_SOURCE_FIELDS = (
    "season",
    "season_type",
    "week",
    "game_id",
    "play_id",
    "home_team",
    "away_team",
    "posteam",
    "two_point_attempt",
    "complete_pass",
    "rusher_player_id",
    "rushing_yards",
    "receiver_player_id",
    "receiving_yards",
)

SUPPORTED_SOURCE_PROJECTIONS = {
    (SPECIAL_TEAMS_FUMBLE_PROJECTION_ID, SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION): "csv.gz",
    (PLAYER_GAME_LONG_GAINS_PROJECTION_ID, PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION): "csv.gz",
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


def _int_or_none(value: Any) -> int | None:
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number == int(number) else None


def project_player_game_long_gains(upstream_path: Path, output_path: Path) -> dict[str, Any]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    games: dict[str, dict[str, str]] = {}
    source_rows = 0
    with gzip.open(upstream_path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(_LONG_GAINS_SOURCE_FIELDS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(
                "nflverse PBP is missing fields required for player-game long-gains projection: "
                + ", ".join(missing)
            )
        for row in reader:
            source_rows += 1
            game_id = (row.get("game_id") or "").strip()
            if not game_id:
                continue
            games.setdefault(
                game_id,
                {
                    "game_id": game_id,
                    "season_type": (row.get("season_type") or "").strip(),
                    "week": (row.get("week") or "").strip(),
                    "home_team": (row.get("home_team") or "").strip(),
                    "away_team": (row.get("away_team") or "").strip(),
                },
            )
            # Two-point attempts are not regular plays from scrimmage for long-gain statistics.
            if _is_one(row.get("two_point_attempt")):
                continue
            play_id = _int_or_none(row.get("play_id"))
            if play_id is None:
                continue
            candidates = []
            rusher = (row.get("rusher_player_id") or "").strip()
            rushing_yards = _int_or_none(row.get("rushing_yards"))
            if rusher and rushing_yards is not None:
                candidates.append(("rush", rusher, rushing_yards))
            receiver = (row.get("receiver_player_id") or "").strip()
            receiving_yards = _int_or_none(row.get("receiving_yards"))
            if receiver and receiving_yards is not None and _is_one(row.get("complete_pass")):
                candidates.append(("reception", receiver, receiving_yards))
            for gain_type, player_id, yards in candidates:
                key = (game_id, gain_type, player_id)
                current = best.get(key)
                if current is None or (yards, -play_id) > (current["yards"], -current["play_id"]):
                    best[key] = {
                        "season": (row.get("season") or "").strip(),
                        "season_type": (row.get("season_type") or "").strip(),
                        "week": (row.get("week") or "").strip(),
                        "game_id": game_id,
                        "gain_type": gain_type,
                        "player_id": player_id,
                        "team": (row.get("posteam") or "").strip(),
                        "play_id": play_id,
                        "yards": yards,
                    }

    records = sorted(
        best.values(),
        key=lambda item: (item["game_id"], item["gain_type"], item["player_id"]),
    )
    game_rows = sorted(games.values(), key=lambda item: item["game_id"])
    payload = {
        "SchemaVersion": 1,
        "Projection": {
            "ID": PLAYER_GAME_LONG_GAINS_PROJECTION_ID,
            "Version": PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION,
        },
        "Columns": list(PLAYER_GAME_LONG_GAINS_FIELDS),
        "Games": game_rows,
        "Records": records,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "sourceRowCount": source_rows,
        "gameCount": len(game_rows),
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
    if key == (
        PLAYER_GAME_LONG_GAINS_PROJECTION_ID,
        PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION,
    ):
        return project_player_game_long_gains(upstream_path, output_path)
    raise ValueError(
        f"Unsupported source projection: id={projection_id} version={projection_version}"
    )
