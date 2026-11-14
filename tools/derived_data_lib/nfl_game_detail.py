"""Pure, read-only NFL game-detail preview from existing canonical evidence.

Issue #1077. This is an additive candidate for the existing nfl-games product,
not a second product or a published contract. A long-gain projection does NOT
prove full play-by-play coverage.
"""
from __future__ import annotations

import math

from typing import Any, Mapping

_DETAIL_SCHEMA = 2
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
    player_stats: Mapping[str, Any] | None = None, snap_counts: Mapping[str, Any] | None = None,
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

    stats_rows, stats_finalized = _player_stat_rows(player_stats, season, game)
    snap_rows, snaps_finalized = _snap_rows(snap_counts, season, game)
    if stats_rows is not None and snap_rows is not None:
        stat_teams = {row["CanonicalPlayerID"]: row["Team"] for row in stats_rows}
        for row in snap_rows:
            known_team = stat_teams.get(row["CanonicalPlayerID"])
            if known_team is not None and known_team != row["Team"]:
                raise ValueError(f"Player changed team across source partitions: {game_id}")

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
        "PlayerStats": {
            "SourceDataset": _STATS_SOURCE,
            "Status": _group_status(stats_rows, game),
            "SourceFinalized": stats_finalized,
            "Players": stats_rows,
        },
        "TeamStats": {
            "SourceDataset": _STATS_SOURCE,
            "Method": "sum-of-available-player-counting-stats-not-official-boxscore",
            "Status": _group_status(stats_rows, game),
            "Teams": _team_totals(stats_rows, game),
        },
        "SnapCounts": {
            "SourceDataset": _SNAPS_SOURCE,
            "Status": _group_status(snap_rows, game),
            "SourceFinalized": snaps_finalized,
            "Players": snap_rows,
        },
    }


# Deliberately limited, additive canonical player counting statistics. These
# are provider player stat categories, not official complete team boxscores.
_PLAYER_COUNT_FIELDS = (
    "attempts", "completions", "passing_yards", "passing_tds",
    "passing_interceptions", "carries", "rushing_yards", "rushing_tds",
    "targets", "receptions", "receiving_yards", "receiving_tds",
    "def_tackles_solo", "def_interceptions", "fg_att", "fg_made",
    "pat_att", "pat_made",
)
_SNAP_FIELDS = (
    "OffenseSnaps", "OffensePct", "DefenseSnaps", "DefensePct",
    "SpecialTeamsSnaps", "SpecialTeamsPct",
)
_STATS_SOURCE = "nflverse.player-stats"
_SNAPS_SOURCE = "nflverse.snap-counts"


def _week_source(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
    dataset: str,
) -> tuple[list[Mapping[str, Any]] | None, bool | None]:
    if payload is None:
        return None, None
    if (payload.get("SchemaVersion") != 2 or payload.get("Season") != season
            or payload.get("Week") != game.get("Week")
            or payload.get("SourceDataset") != dataset
            or type(payload.get("Finalized")) is not bool):
        raise ValueError(f"{dataset}: incompatible canonical week partition")
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ValueError(f"{dataset}: missing canonical Records")
    if any(not isinstance(row, dict) for row in records):
        raise ValueError(f"{dataset}: invalid canonical player row")
    return records, payload["Finalized"]


def _player_stat_rows(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[list[dict[str, Any]] | None, bool | None]:
    source_rows, finalized = _week_source(payload, season, game, _STATS_SOURCE)
    if source_rows is None:
        return None, finalized
    game_id = game["GameID"]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        stats = row.get("Stats")
        if not isinstance(stats, dict) or not isinstance(stats.get("game_id"), str):
            raise ValueError("player-stats: missing Stats.game_id")
        if stats["game_id"] != game_id:
            continue
        cid = row.get("CanonicalPlayerID")
        team = row.get("Team")
        if (not isinstance(cid, str) or not cid or cid in seen
                or team not in (game["AwayTeam"], game["HomeTeam"])
                or row.get("OpponentTeam") != (
                    game["HomeTeam"] if team == game["AwayTeam"] else game["AwayTeam"]
                )
                or row.get("Week") != game["Week"]
                or not _valid_type(row.get("SeasonType"), game.get("GameType"))):
            raise ValueError(f"player-stats: invalid player/game identity {game_id}")
        seen.add(cid)
        counts: dict[str, int | None] = {}
        for field in _PLAYER_COUNT_FIELDS:
            value = stats.get(field)
            if value is not None and type(value) is not int:
                raise ValueError(f"player-stats: invalid {field} for {cid}")
            if value is not None and value < 0 and not field.endswith("_yards"):
                raise ValueError(f"player-stats: negative count {field} for {cid}")
            counts[field] = value
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "PlayerName": row.get("PlayerName"),
            "Position": row.get("Position"),
            "Stats": counts,
        })
    selected.sort(key=lambda r: (r["Team"], r["CanonicalPlayerID"]))
    return selected or None, finalized


def _snap_rows(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[list[dict[str, Any]] | None, bool | None]:
    source_rows, finalized = _week_source(payload, season, game, _SNAPS_SOURCE)
    if source_rows is None:
        return None, finalized
    game_id = game["GameID"]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        if row.get("GameID") != game_id:
            continue
        cid = row.get("CanonicalPlayerID")
        team = row.get("Team")
        if (not isinstance(cid, str) or not cid or cid in seen
                or team not in (game["AwayTeam"], game["HomeTeam"])
                or row.get("OpponentTeam") != (
                    game["HomeTeam"] if team == game["AwayTeam"] else game["AwayTeam"]
                )
                or row.get("Week") != game["Week"]
                or row.get("GameType") != game.get("GameType")):
            raise ValueError(f"snap-counts: invalid player/game identity {game_id}")
        seen.add(cid)
        snaps: dict[str, int | float | None] = {}
        for field in _SNAP_FIELDS:
            value = row.get(field)
            if field.endswith("Pct"):
                if (value is not None
                        and (type(value) not in (int, float)
                             or not math.isfinite(value) or value < 0 or value > 1)):
                    raise ValueError(f"snap-counts: invalid percentage {field} for {cid}")
            elif value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"snap-counts: invalid count {field} for {cid}")
            snaps[field] = value
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "PlayerName": row.get("PlayerName"),
            "Position": row.get("Position"),
            "Snaps": snaps,
        })
    selected.sort(key=lambda r: (r["Team"], r["CanonicalPlayerID"]))
    return selected or None, finalized


def _group_status(rows: list[dict[str, Any]] | None, game: Mapping[str, Any]) -> str:
    if rows is None:
        return "unavailable"
    teams = {row["Team"] for row in rows}
    return "available" if teams == {game["HomeTeam"], game["AwayTeam"]} else "partial"


def _team_totals(
    players: list[dict[str, Any]] | None, game: Mapping[str, Any],
) -> list[dict[str, Any]] | None:
    if players is None:
        return None
    teams = []
    for team in (game["AwayTeam"], game["HomeTeam"]):
        group = [row["Stats"] for row in players if row["Team"] == team]
        if not group:
            teams.append({"Team": team, "Status": "unavailable",
                          "PlayerRecordCount": None, "Stats": None})
            continue
        total: dict[str, int | None] = {}
        for field in _PLAYER_COUNT_FIELDS:
            values = [row[field] for row in group]
            total[field] = sum(values) if all(v is not None for v in values) else None
        teams.append({"Team": team, "Status": "available",
                      "PlayerRecordCount": len(group), "Stats": total})
    return teams
