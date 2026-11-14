"""Pure, read-only NFL game-detail preview from existing canonical evidence.

Issue #1077. This is an additive candidate for the existing nfl-games product,
not a second product or a published contract. A long-gain projection does NOT
prove full play-by-play coverage.
"""
from __future__ import annotations

from typing import Any, Mapping

_DETAIL_SCHEMA = 1
_LONG_GAINS_SOURCE = "nflverse.player-game-long-gains"
_GAIN_TYPES = {"LongReception", "LongRush"}
_POST_TYPES = {"WC", "DIV", "CON", "SB"}


def _season_index(index: Mapping[str, Any]) -> tuple[int, dict[str, Mapping[str, Any]]]:
    season = index.get("Season")
    if index.get("SchemaVersion") != 1 or type(season) is not int or season < 1999:
        raise ValueError("Invalid nfl-games season index")
    games = index.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError("Invalid nfl-games games")
    result: dict[str, Mapping[str, Any]] = {}
    for row in games:
        if not isinstance(row, dict) or not isinstance(row.get("GameID"), str):
            raise ValueError("Invalid nfl-games game row")
        game_id = row["GameID"]
        if game_id in result or not game_id.startswith(f"{season}_"):
            raise ValueError(f"Duplicate or invalid GameID: {game_id}")
        result[game_id] = row
    return season, result


def _valid_type(source_type: Any, game_type: Any) -> bool:
    return (source_type == "REG" and game_type == "REG") or (
        source_type == "POST" and game_type in _POST_TYPES
    )


def build_nfl_game_detail(
    index: Mapping[str, Any], game_id: str, long_gains: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one game detail without writes or invented full-PBP statistics.

    A missing long-gains season or a game omitted from its coverage is
    unavailable, NOT zero. A known covered game with no long-gain records
    has an empty list for this specific projection only.
    """
    season, indexed = _season_index(index)
    if game_id not in indexed:
        raise ValueError(f"GameID not found in canonical nfl-games index: {game_id}")
    game = indexed[game_id]
    records: list[dict[str, Any]] | None = None

    if long_gains is not None:
        if (long_gains.get("SchemaVersion") != 2
                or long_gains.get("Season") != season
                or long_gains.get("SourceDataset") != _LONG_GAINS_SOURCE):
            raise ValueError("Incompatible canonical long-gains partition")
        available = long_gains.get("Games")
        source_records = long_gains.get("Records")
        if not isinstance(available, list) or not isinstance(source_records, list):
            raise ValueError("Malformed canonical long-gains partition")
        available_ids: set[str] = set()
        for row in available:
            if not isinstance(row, dict) or not isinstance(row.get("GameID"), str):
                raise ValueError("Invalid long-gains game")
            key = row["GameID"]
            if key in available_ids:
                raise ValueError(f"Duplicate long-gains GameID: {key}")
            available_ids.add(key)
            known = indexed.get(key)
            if (known is None or row.get("Week") != known.get("Week")
                    or not _valid_type(row.get("SeasonType"), known.get("GameType"))):
                raise ValueError(f"Unknown or inconsistent long-gains game: {key}")
        selected: list[dict[str, Any]] = []
        selected_keys: set[tuple[str, str, str]] = set()
        for row in source_records:
            if not isinstance(row, dict):
                raise ValueError("Invalid long-gains record")
            record_game = row.get("GameID")
            if record_game not in available_ids:
                raise ValueError(f"Long-gains record without available game: {record_game}")
            if record_game != game_id:
                continue
            if (row.get("Week") != game.get("Week")
                    or not _valid_type(row.get("SeasonType"), game.get("GameType"))):
                raise ValueError(f"Inconsistent long-gains record: {game_id}")
            player = row.get("CanonicalPlayerID")
            gain_type = row.get("GainType")
            yards = row.get("Yards")
            play_id = row.get("PlayID")
            if (not isinstance(player, str) or not player or gain_type not in _GAIN_TYPES
                    or type(yards) is not int or type(play_id) is not int or play_id < 0):
                raise ValueError(f"Invalid long-gains player/play evidence: {game_id}")
            key = (record_game, player, gain_type)
            if key in selected_keys:
                raise ValueError(f"Duplicate long-gains player/gain type: {game_id}")
            selected_keys.add(key)
            team = row.get("Team")
            if team not in (game.get("AwayTeam"), game.get("HomeTeam")):
                raise ValueError(f"Invalid long-gains player team: {game_id}")
            selected.append({
                "CanonicalPlayerID": player,
                "Team": team,
                "GainType": gain_type,
                "Yards": yards,
                "PlayID": play_id,
            })
        if game_id in available_ids:
            records = sorted(selected, key=lambda r: (r["Team"], r["GainType"], r["CanonicalPlayerID"]))

    return {
        "SchemaVersion": _DETAIL_SCHEMA,
        "Season": season,
        "GameID": game_id,
        "Game": dict(game),
        "PlayByPlay": {
            "Coverage": "partial" if records is not None else "unavailable",
            "FullPlayByPlayAvailable": False,
            "LongGains": {
                "SourceDataset": _LONG_GAINS_SOURCE,
                "Status": "available" if records is not None else "unavailable",
                "Records": records,
            },
        },
    }
