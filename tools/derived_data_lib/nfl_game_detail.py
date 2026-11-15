"""Pure, read-only NFL game-detail preview from existing canonical evidence.

Issue #1077. This is an additive candidate for the existing nfl-games product,
not a second product or a published contract. A long-gain projection does NOT
prove full play-by-play coverage.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

from typing import Any, Mapping

from .nfl_pbp_team_metrics import evaluate_team_pbp_metric_candidates

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
    pbp_rows: list[Mapping[str, str]] | None = None,
    pbp_asset_sha256: str | None = None,
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

    pbp = {
        "Coverage": "partial" if records is not None else "unavailable",
        "FullPlayByPlayAvailable": False,
        "LongGains": {
            "SourceDataset": _LONG_GAINS_SOURCE,
            "Status": "available" if records is not None else "unavailable",
            "Records": records,
        },
    }
    if pbp_rows is not None:
        pbp["OriginalPlays"] = _build_original_pbp(game, season, pbp_rows, pbp_asset_sha256)
        pbp["Coverage"] = "source-rows-unverified"
        # Even a matching season-asset hash does not establish game completeness.
        pbp["FullPlayByPlayAvailable"] = False
    elif pbp_asset_sha256 is not None:
        raise ValueError("PBP asset digest supplied without PBP rows")

    return {
        "SchemaVersion": 3 if pbp_rows is not None else _DETAIL_SCHEMA,
        "Season": season,
        "GameID": game_id,
        "Game": dict(game),
        "PlayByPlay": pbp,
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


# Full original play evidence is deliberately separate from the sparse LongGains
# projection and from the optional player-stats / snap-counts inputs.
_PBP_SOURCE = "nflverse.play-by-play"
_PBP_NULLS = {"", "NA", "N/A", "NaN", "nan", "NULL", "null"}


def _pbp_number(value: Any, name: str, *, integer: bool = False,
                required: bool = False) -> int | float | None:
    text = str(value if value is not None else "").strip()
    if text in _PBP_NULLS:
        if required:
            raise ValueError(f"Original PBP missing required {name}")
        return None
    try:
        n = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Original PBP invalid {name}: {text}") from exc
    if not n.is_finite():
        raise ValueError(f"Original PBP nonfinite {name}")
    if integer:
        if n != n.to_integral_value():
            raise ValueError(f"Original PBP nonintegral {name}")
        return int(n)
    value = float(n)
    if not math.isfinite(value):
        raise ValueError(f"Original PBP nonfinite {name}")
    return value


def _build_original_pbp(
    game: Mapping[str, Any],
    season: int,
    rows: list[Mapping[str, str]],
    asset_sha256: str | None,
) -> dict[str, Any]:
    """Pure per-GameID original-play projection, never a completeness certificate.

    All original CSV columns of each input row survive verbatim under SourceRow.
    Only the requested game's records may be passed; call-site streams the gzip.
    No player-stats, snap counts, inferred fantasy scoring or rights assumptions.
    """
    if not isinstance(rows, list) or not rows:
        raise ValueError("Original PBP has no rows for requested GameID")
    if asset_sha256 is not None and (
        len(asset_sha256) != 64 or any(c not in "0123456789abcdef" for c in asset_sha256)
    ):
        raise ValueError("Invalid original PBP SHA256 digest")
    plays: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(k, str) for k in row):
            raise ValueError("Invalid original PBP CSV row")
        if (row.get("game_id") != game.get("GameID")
                or _pbp_number(row.get("season"), "season", integer=True, required=True) != season
                or _pbp_number(row.get("week"), "week", integer=True, required=True) != game.get("Week")
                or not _valid_type(row.get("season_type"), game.get("GameType"))
                or row.get("home_team") != game.get("HomeTeam")
                or row.get("away_team") != game.get("AwayTeam")):
            raise ValueError(f"Original PBP game/season/week/type/team mismatch: {game.get('GameID')}")
        play_id = _pbp_number(row.get("play_id"), "play_id", integer=True, required=True)
        if play_id < 1 or play_id in seen:
            raise ValueError(f"Original PBP invalid or duplicate PlayID: {play_id}")
        seen.add(play_id)
        qtr = _pbp_number(row.get("qtr"), "qtr", integer=True)
        down = _pbp_number(row.get("down"), "down", integer=True)
        ydstogo = _pbp_number(row.get("ydstogo"), "ydstogo", integer=True)
        drive = _pbp_number(row.get("drive"), "drive", integer=True)
        yardline = _pbp_number(row.get("yardline_100"), "yardline_100")
        epa = _pbp_number(row.get("epa"), "epa")
        success = _pbp_number(row.get("success"), "success", integer=True)
        game_clock = _pbp_number(row.get("game_seconds_remaining"), "game_seconds_remaining")
        if (qtr is not None and not 1 <= qtr <= 7
                or down is not None and not 1 <= down <= 4
                or ydstogo is not None and not 0 <= ydstogo <= 100
                or drive is not None and drive < 0
                or yardline is not None and not 0 <= yardline <= 100
                or success is not None and success not in (0, 1)
                or game_clock is not None and game_clock < 0):
            raise ValueError(f"Original PBP impossible situation at PlayID {play_id}")
        posteam = (row.get("posteam") or "").strip()
        defteam = (row.get("defteam") or "").strip()
        if posteam not in ("", game["AwayTeam"], game["HomeTeam"]) or defteam not in (
            "", game["AwayTeam"], game["HomeTeam"]
        ):
            raise ValueError(f"Original PBP invalid possession/defense team: {play_id}")
        if posteam and defteam and posteam == defteam:
            raise ValueError(f"Original PBP same possession/defense team: {play_id}")
        plays.append({
            "PlayID": play_id,
            "Quarter": qtr,
            "Drive": drive,
            "GameSecondsRemaining": game_clock,
            "Down": down,
            "YardsToGo": ydstogo,
            "Yardline100": yardline,
            "PossessionTeam": posteam or None,
            "DefenseTeam": defteam or None,
            "PlayType": (row.get("play_type") or "").strip() or None,
            "Description": row.get("desc") or None,
            "EPA": epa,
            "Success": bool(success) if success is not None else None,
            "SourceRow": dict(row),
        })
    plays.sort(key=lambda p: p["PlayID"])
    return {
        "SourceDataset": _PBP_SOURCE,
        "SourceFormat": "csv.gz",
        "SourceAssetSHA256": asset_sha256,
        "Status": "present-unverified-completeness",
        "CompletenessVerified": False,
        "PlayCount": len(plays),
        "Plays": plays,
        "Analytics": _pbp_game_analytics(plays, game),
    }


# CP4: all metrics are derived exclusively from original PBP SourceRows.
# The nflverse 'epa', 'success' and 'third_down_converted' fields are reused;
# none is reconstituted from player stats, outcomes or schedule scores.
def _pbp_game_analytics(
    plays: list[Mapping[str, Any]], game: Mapping[str, Any],
) -> dict[str, Any]:
    def _rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    eligible: list[Mapping[str, Any]] = []
    excluded_two_point = 0
    excluded_unknown_two_point = 0
    excluded_other = 0
    unassigned = 0
    for play in plays:
        if play["PlayType"] not in ("pass", "run"):
            excluded_other += 1
            continue
        raw = play["SourceRow"]
        flag = _pbp_number(raw.get("two_point_attempt"), "two_point_attempt", integer=True)
        if flag is None:
            # Unknown membership is never treated as a confirmed normal play.
            excluded_unknown_two_point += 1
            continue
        if flag not in (0, 1):
            raise ValueError(f"Original PBP invalid two_point_attempt at PlayID {play['PlayID']}")
        if flag == 1:
            excluded_two_point += 1
            continue
        if play["PossessionTeam"] is None or play["DefenseTeam"] is None:
            unassigned += 1
            continue
        # Validate every used provider input, including nullable fields. A missing
        # field reduces a metric's denominator rather than becoming 0/False.
        yards = _pbp_number(raw.get("yards_gained"), "yards_gained")
        third = _pbp_number(raw.get("third_down_converted"), "third_down_converted",
                            integer=True)
        if third is not None and third not in (0, 1):
            raise ValueError(f"Original PBP invalid third_down_converted at PlayID {play['PlayID']}")
        eligible.append({**play, "_YardsGained": yards, "_ThirdConverted": third})

    def _metrics(subset: list[Mapping[str, Any]], *, third_down: bool = False) -> dict[str, Any]:
        # Return explicit denominators. No rows means 'unknown/no evidence',
        # not a measured zero EPA, success rate, or conversion rate.
        epa = [p["EPA"] for p in subset if p["EPA"] is not None]
        success = [p["Success"] for p in subset if p["Success"] is not None]
        yards = [p for p in subset if p["_YardsGained"] is not None]
        positive = sum(p is True for p in success)
        explosives = sum(
            p["_YardsGained"] >= (20 if p["PlayType"] == "pass" else 10)
            for p in yards
        )
        result = {
            "PlayCount": len(subset),
            "EPA": {
                "Observed": len(epa), "Missing": len(subset) - len(epa),
                "Sum": round(math.fsum(epa), 3) if epa else None,
                "PerPlay": round(math.fsum(epa) / len(epa), 4) if epa else None,
            },
            "Success": {
                "Observed": len(success), "Missing": len(subset) - len(success),
                "Successful": positive, "Rate": _rate(positive, len(success)),
            },
            "Explosive": {
                "Observed": len(yards), "Missing": len(subset) - len(yards),
                "Count": explosives, "Rate": _rate(explosives, len(yards)),
            },
        }
        if third_down:
            observed = [p["_ThirdConverted"] for p in subset if p["_ThirdConverted"] is not None]
            converted = sum(v == 1 for v in observed)
            result["Conversions"] = {
                "Observed": len(observed), "Missing": len(subset) - len(observed),
                "Converted": converted, "Rate": _rate(converted, len(observed)),
            }
        return result

    teams = (game["AwayTeam"], game["HomeTeam"])
    offense = []
    defense = []
    for team in teams:
        by_offense = [p for p in eligible if p["PossessionTeam"] == team]
        by_defense = [p for p in eligible if p["DefenseTeam"] == team]
        offense.append({
            "Team": team, "All": _metrics(by_offense),
            "Pass": _metrics([p for p in by_offense if p["PlayType"] == "pass"]),
            "Run": _metrics([p for p in by_offense if p["PlayType"] == "run"]),
            "ThirdDown": _metrics(
                [p for p in by_offense if p["Down"] == 3], third_down=True,
            ),
        })
        # Defensive values reflect the OPPOSING offense's PBP EPA and success.
        # Lower allowed offense EPA/success is better for the defense.
        defense.append({
            "Team": team, "OffenseAllowed": _metrics(by_defense),
            "ThirdDownAllowed": _metrics(
                [p for p in by_defense if p["Down"] == 3], third_down=True,
            ),
        })
    return {
        "DefinitionVersion": 1,
        "Status": "provisional-unverified-game-completeness",
        "Definitions": {
            "Eligibility": "play_type pass/run with two_point_attempt=0 and both teams identified",
            "EPA": "source epa from offense perspective; mean over non-null observed epa only",
            "Success": "source success=1 rate, non-null observed flags only",
            "Explosive": "yards_gained >=20 on pass or >=10 on run; non-null yards only",
            "ThirdDownConversion": "source third_down_converted=1 on down=3 pass/run only",
            "Rounding": "EPA sum 3 decimals, per-play and rates 4 decimals",
        },
        "SourcePlayCount": len(plays),
        "EligiblePlayCount": len(eligible),
        "ExcludedNonScrimmageCount": excluded_other,
        "ExcludedTwoPointAttemptCount": excluded_two_point,
        "ExcludedUnknownTwoPointFlagCount": excluded_unknown_two_point,
        "ExcludedUnassignedTeamCount": unassigned,
        "ByOffenseTeam": offense,
        "ByDefenseTeam": defense,
        "CatalogTeamMetricCandidates": evaluate_team_pbp_metric_candidates(plays, game),
    }
