"""Validate original nflverse PBP Source identity without reading Derived products.

This gate covers official bytes (caller-pinned digest), gzip/CSV structure,
GameID/PlayID identity and game context against canonical Source schedules.
Metric eligibility, PlayerStats reconciliation and upstream play completeness
are deliberately outside the Source acceptance contract (Issue #1077).
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from .teams import HISTORICAL_ALIAS_LAST_SEASON, PROVIDER_SPELLING_ALIASES

_REQUIRED_COLUMNS = frozenset((
    "game_id", "play_id", "season", "week", "season_type",
    "home_team", "away_team", "posteam", "defteam", "play_type",
))


def _integer(value: str | None, field: str) -> int:
    try:
        number = Decimal(str(value or "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid original PBP {field}: {value!r}") from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError(f"Invalid original PBP {field}: {value!r}")
    return int(number)


def _team_matches(observed: str, canonical: str, season: int) -> bool:
    if observed == canonical or PROVIDER_SPELLING_ALIASES.get(observed) == canonical:
        return True
    historical = HISTORICAL_ALIAS_LAST_SEASON.get(observed)
    return bool(historical and historical[0] == canonical and season <= historical[1])


def _source_schedule(root: Path, season: int) -> tuple[dict[str, dict], str]:
    path = root / DATA_SOURCE_ROOT / "nfl/schedules" / f"{season}.json"
    blob = path.read_bytes()
    data = json.loads(blob)
    if (not isinstance(data, dict)
            or data.get("SchemaVersion") != 2
            or data.get("SourceDataset") != "nflverse.schedules"
            or data.get("Season") != season
            or not isinstance(data.get("Games"), list)
            or not data["Games"]):
        raise ValueError(f"Invalid canonical Source schedule for PBP season {season}")
    indexed: dict[str, dict] = {}
    for game in data["Games"]:
        if (not isinstance(game, dict)
                or not isinstance(game.get("GameID"), str)
                or not game["GameID"]
                or type(game.get("Week")) is not int
                or not 1 <= game["Week"] <= 25
                or game.get("GameType") not in ("REG", "WC", "DIV", "CON", "SB")
                or not isinstance(game.get("HomeTeam"), str)
                or not game["HomeTeam"]
                or not isinstance(game.get("AwayTeam"), str)
                or not game["AwayTeam"]
                or game["HomeTeam"] == game["AwayTeam"]):
            raise ValueError(f"Invalid canonical Source schedule game for PBP season {season}")
        if game["GameID"] in indexed:
            raise ValueError(f"Duplicate canonical Source schedule GameID {game['GameID']}")
        indexed[game["GameID"]] = game
    return indexed, hashlib.sha256(blob).hexdigest()


def audit_original_pbp(
    root: Path, season: int, original: Path, expected_sha256: str,
) -> dict[str, Any]:
    """Read the entire original gzip; never require future PlayerStats weeks.

    Observe only games represented in the supplied original. A canonical
    schedule may include future games absent from the current PBP snapshot.
    """
    if type(season) is not int or not 1999 <= season <= 2100:
        raise ValueError("Invalid original PBP season")
    if (not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or any(char not in "0123456789abcdef" for char in expected_sha256)):
        raise ValueError("Expected original PBP SHA256 must be lowercase hex")
    games, schedule_sha = _source_schedule(root, season)
    with original.open("rb") as handle:
        actual_sha = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual_sha != expected_sha256:
        raise ValueError("Original PBP failed pinned SHA256 Source identity")
    observed: set[str] = set()
    keys: set[tuple[str, int]] = set()
    row_count = 0
    with gzip.open(original, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if (not columns or any(not column for column in columns)
                or len(columns) != len(set(columns))
                or not _REQUIRED_COLUMNS.issubset(columns)):
            raise ValueError("Original PBP missing or duplicate identity columns")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Original PBP CSV row has invalid width")
            row_count += 1
            game_id = (row["game_id"] or "").strip()
            game = games.get(game_id)
            if game is None:
                raise ValueError(f"Original PBP unknown Source GameID {game_id}")
            play_id = _integer(row["play_id"], "play_id")
            if play_id <= 0:
                raise ValueError(f"Original PBP nonpositive PlayID {game_id}/{play_id}")
            if (game_id, play_id) in keys:
                raise ValueError(f"Duplicate original PBP GameID/PlayID {game_id}/{play_id}")
            keys.add((game_id, play_id))
            if _integer(row["season"], "season") != season:
                raise ValueError(f"Original PBP wrong season for {game_id}/{play_id}")
            if _integer(row["week"], "week") != game["Week"]:
                raise ValueError(f"Original PBP mismatched Source week for {game_id}/{play_id}")
            expected_type = "REG" if game["GameType"] == "REG" else "POST"
            if row["season_type"] != expected_type:
                raise ValueError(f"Original PBP mismatched Source game type for {game_id}/{play_id}")
            if (not _team_matches(row["away_team"], game["AwayTeam"], season)
                    or not _team_matches(row["home_team"], game["HomeTeam"], season)):
                raise ValueError(f"Original PBP mismatched Source teams for {game_id}/{play_id}")
            observed.add(game_id)
    if not row_count:
        raise ValueError("Original PBP source has no plays")
    with original.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != actual_sha:
            raise ValueError("Original PBP changed during Source audit")
    return {
        "SourceRowCount": row_count,
        "ObservedGameIDs": len(observed),
        "OriginalColumnCount": len(columns),
        "UnmatchedCanonicalGameRows": 0,
        "SourceScheduleSHA256": schedule_sha,
        "SourceValidationStatus": "original-byte-and-source-game-identity-accepted",
        "UpstreamFullGameCompletenessVerified": False,
    }
