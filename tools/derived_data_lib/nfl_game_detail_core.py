"""Read-only candidate for the existing nfl-games per-GameID Derived product.

Issue #1077. This *does not* persist or publish game details. It combines the
existing canonical game index, canonical weekly PlayerStats and SnapCounts,
reusing the approved pure game-stat and team-snap calculations. Group-level
identity holds remain visible: a missing player identity blocks player-based
team stats, but cannot erase independently supported team snap totals.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from .nfl_game_detail import (
    _PLAYER_COUNT_FIELDS,
    _SNAP_FIELDS,
    _SNAPS_SOURCE,
    _STATS_SOURCE,
    _group_status,
    _player_stat_rows,
    _season_index,
    _team_totals,
    _valid_type,
    _week_source,
)
from .nfl_franchise_aliases import reconcile_game_team
from .nfl_team_snap_usage import infer_team_snap_volumes

_DEFINITION_VERSION = 1


def _selected_stats(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[list[dict[str, Any]] | None, bool | None, list[Mapping[str, Any]], int, str, int, int]:
    rows, finalized = _week_source(payload, season, game, _STATS_SOURCE)
    if rows is None:
        return None, None, [], 0, "unavailable", 0, 0
    selected: list[Mapping[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    unresolved = 0
    aliases = 0
    missing_context = 0
    for row in rows:
        stats = row.get("Stats")
        if not isinstance(stats, dict) or not isinstance(stats.get("game_id"), str):
            raise ValueError("player-stats: missing Stats.game_id")
        if stats["game_id"] != game["GameID"]:
            continue
        team, opponent = row.get("Team"), row.get("OpponentTeam")
        canonical = reconcile_game_team(
            team, opponent, game["AwayTeam"], game["HomeTeam"], season,
        )
        if (row.get("Week") != game["Week"]
                or not _valid_type(row.get("SeasonType"), game["GameType"])
                or (canonical is None and team is not None and opponent is not None)):
            raise ValueError(
                f"player-stats: invalid game/team/week/type for {game['GameID']}: "
                f"team={team!r}, opp={opponent!r}, "
                f"week={row.get('Week')!r}, type={row.get('SeasonType')!r}, "
                f"expected {game['AwayTeam']}/{game['HomeTeam']} {game['Week']} {game['GameType']}"
            )
        # A genuinely missing team/opponent context blocks the entire
        # player-sum group, but must not suppress independent team snaps.
        if canonical is None:
            missing_context += 1
            other = None
        else:
            other = game["HomeTeam"] if canonical == game["AwayTeam"] else game["AwayTeam"]
            if team != canonical or opponent != other:
                aliases += 1
        cid = row.get("CanonicalPlayerID")
        if not isinstance(cid, str) or not cid:
            unresolved += 1
        elif cid in seen:
            raise ValueError("player-stats: duplicated canonical player in game")
        else:
            seen.add(cid)
        for field in _PLAYER_COUNT_FIELDS:
            value = stats.get(field)
            if value is not None and (
                type(value) is not int or
                (value < 0 and not field.endswith("_yards"))
            ):
                raise ValueError(f"player-stats: invalid counting field {field}")
        # The versioned fingerprint only depends on fields actually consumed by
        # the v1 team-stats model. Raw provider records may contain unrelated
        # nonfinite floats (e.g. historical EPA) and must not force a rebuild.
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "OpponentTeam": opponent,
            "Week": row.get("Week"),
            "SeasonType": row.get("SeasonType"),
            "Stats": {field: stats.get(field) for field in _PLAYER_COUNT_FIELDS},
        })
        normalized.append({**row, "Team": canonical, "OpponentTeam": other})
    if missing_context:
        return (None, finalized, selected, unresolved,
                "blocked-missing-team-context", aliases, missing_context)
    if unresolved:
        return (None, finalized, selected, unresolved,
                "blocked-unresolved-player-identity", aliases, 0)
    # Reuse the canonical player validator and additive team totals, now with
    # narrowly validated era-specific franchise spelling in a temporary copy.
    sanitized = {**payload, "Records": normalized}
    validated, _ = _player_stat_rows(sanitized, season, game)
    return validated, finalized, selected, 0, _group_status(validated, game), aliases, 0


def _selected_snap_counts(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[list[dict[str, Any]] | None, bool | None, list[Mapping[str, Any]], int, str, int]:
    rows, finalized = _week_source(payload, season, game, _SNAPS_SOURCE)
    if rows is None:
        return None, None, [], 0, "unavailable", 0
    selected: list[Mapping[str, Any]] = []
    team_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    unresolved = 0
    aliases = 0
    for row in rows:
        if row.get("GameID") != game["GameID"]:
            continue
        team, opponent = row.get("Team"), row.get("OpponentTeam")
        canonical = reconcile_game_team(
            team, opponent, game["AwayTeam"], game["HomeTeam"], season,
        )
        if (canonical is None
                or row.get("Week") != game["Week"]
                or row.get("GameType") != game["GameType"]):
            raise ValueError(
                f"snap-counts: invalid game/team/week/type for {game['GameID']}: "
                f"team={team!r}, opp={opponent!r}"
            )
        other = game["HomeTeam"] if canonical == game["AwayTeam"] else game["AwayTeam"]
        if team != canonical or opponent != other:
            aliases += 1
        cid = row.get("CanonicalPlayerID")
        if not isinstance(cid, str) or not cid:
            unresolved += 1
        elif cid in seen:
            raise ValueError("snap-counts: duplicated canonical player in game")
        else:
            seen.add(cid)
        snaps: dict[str, int | float | None] = {}
        for field in _SNAP_FIELDS:
            value = row.get(field)
            if field.endswith("Pct"):
                if (value is not None
                        and (type(value) not in (int, float)
                             or not math.isfinite(value)
                             or not 0 <= value <= 1)):
                    raise ValueError(f"snap-counts: invalid percentage {field}")
            elif value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"snap-counts: invalid count {field}")
            snaps[field] = value
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "OpponentTeam": opponent,
            "Week": row.get("Week"),
            "GameType": row.get("GameType"),
            "Snaps": snaps,
        })
        team_rows.append({"Team": canonical, "Snaps": snaps})
    if not selected:
        return None, finalized, selected, 0, "unavailable", 0
    all_teams = {row["Team"] for row in team_rows}
    status = ("available" if all_teams == {game["AwayTeam"], game["HomeTeam"]}
              else "partial")
    return team_rows, finalized, selected, unresolved, status, aliases


def _digest(selected: dict[str, Any]) -> str:
    """Only this GameID's evidence affects the digest, not neighboring games."""
    # Selected rows are semantically unordered; do not depend on weekly Source order.
    values = {
        **selected,
        "PlayerStatsRows": sorted(
            selected["PlayerStatsRows"], key=lambda row: json.dumps(
                row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            )
        ),
        "SnapCountsRows": sorted(
            selected["SnapCountsRows"], key=lambda row: json.dumps(
                row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            )
        ),
    }
    encoded = json.dumps(values, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_nfl_game_detail_core(
    index: Mapping[str, Any], game_id: str,
    player_stats: Mapping[str, Any] | None = None,
    snap_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a compact game/team-only v1 candidate with no source mutations."""
    season, games = _season_index(index)
    game = games.get(game_id)
    if game is None:
        raise ValueError(f"GameID not found in canonical nfl-games index: {game_id}")
    stat_players, stats_finalized, stat_raw, stat_holds, stats_status, stat_aliases, stat_missing_context = _selected_stats(
        player_stats, season, game,
    )
    team_snap_rows, snaps_finalized, snap_raw, snap_holds, snap_status, snap_aliases = _selected_snap_counts(
        snap_counts, season, game,
    )
    team_snap_totals = infer_team_snap_volumes(
        team_snap_rows, game["AwayTeam"], game["HomeTeam"],
    )
    input_digest = _digest({
        "SchemaVersion": 1,
        "DefinitionVersion": _DEFINITION_VERSION,
        "Game": dict(game),
        "PlayerStatsFinalized": stats_finalized,
        "PlayerStatsRows": stat_raw,
        "SnapCountsFinalized": snaps_finalized,
        "SnapCountsRows": snap_raw,
    })
    return {
        "SchemaVersion": 1,
        "Product": "nfl-games",
        "DetailDefinitionVersion": _DEFINITION_VERSION,
        "Season": season,
        "GameID": game_id,
        "Game": dict(game),
        "TeamStats": {
            "SourceDataset": _STATS_SOURCE,
            "Status": stats_status,
            "SourceFinalized": stats_finalized,
            "UnresolvedPlayerIdentityRows": stat_holds,
            "HistoricalFranchiseAliasRows": stat_aliases,
            "MissingTeamContextRows": stat_missing_context,
            "Method": "sum-of-valid-canonical-player-counting-stats-not-official-boxscore",
            "Teams": _team_totals(stat_players, game),
        },
        "SnapCounts": {
            "SourceDataset": _SNAPS_SOURCE,
            "Status": snap_status,
            "SourceFinalized": snaps_finalized,
            "UnresolvedPlayerIdentityRows": snap_holds,
            "HistoricalFranchiseAliasRows": snap_aliases,
            "Method": "unique-integer-denominator-from-rounded-player-percentages",
            "TeamTotalsOfficiallyVerified": False,
            "Teams": team_snap_totals,
        },
        "Coverage": {
            "GameIndex": "available",
            "TeamStats": stats_status,
            "TeamSnapCounts": snap_status,
            "PlayByPlay": "not-in-core-v1",
            "FullPlayByPlayAvailable": False,
        },
        "Derivation": {
            "DefinitionVersion": _DEFINITION_VERSION,
            "InputFingerprintSHA256": input_digest,
        },
    }
