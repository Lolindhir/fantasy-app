"""Pure canonical NFL injury-report partition builder (Issue #1421).

No network, storage, clock, league, salary, current Sleeper status or APP reads.
Keep all original report observations even when identity or schedule joins fail.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re
from typing import Any

_GSIS = re.compile(r"^00-[0-9]{7}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _claims(players: dict[str, Any]) -> tuple[dict[str, set[str]], str]:
    if not isinstance(players, dict) or not isinstance(players.get("Players"), list):
        raise ValueError("Canonical player identity payload must contain Players list")
    index: dict[str, set[str]] = defaultdict(set)
    for row in players["Players"]:
        if not isinstance(row, dict) or not row.get("CanonicalPlayerID"):
            raise ValueError("Canonical player identity row lacks CanonicalPlayerID")
        owner = str(row["CanonicalPlayerID"])
        active = (row.get("IDs") or {}).get("GSIS")
        aliases = (row.get("IDAliases") or {}).get("GSIS") or []
        if not isinstance(aliases, list):
            raise ValueError("GSIS identity aliases must be a list")
        for raw in ([active] if active is not None else []) + aliases:
            if raw is not None and _GSIS.fullmatch(str(raw)):
                index[str(raw)].add(owner)
    return index, _digest(players)


def _schedule_index(schedule: dict[str, Any] | None, season: int) -> dict[tuple[int, str, str], set[str]] | None:
    if schedule is None:
        return None
    if not isinstance(schedule, dict) or schedule.get("Season") != season or not isinstance(schedule.get("Games"), list):
        raise ValueError("Canonical schedule is missing or has wrong season")
    index: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for game in schedule["Games"]:
        week, game_type, game_id = game.get("Week"), game.get("GameType"), game.get("GameID")
        if not isinstance(week, int) or not game_type or not game_id:
            raise ValueError("Canonical schedule game has incomplete identity")
        for team in (game.get("HomeTeam"), game.get("AwayTeam")):
            if not team:
                raise ValueError("Canonical schedule game lacks team")
            index[(week, str(game_type), str(team))].add(str(game_id))
    return index


def canonicalize_injury_reports(
    parsed: dict[str, Any],
    canonical_players: dict[str, Any],
    *,
    schedule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build reproducible season/week candidates without writing them.

    The GSIS join uses the CURRENT canonical identity graph; historical
    observation/claim validity is deliberately not asserted by this lookup.
    NFL GameID is optional: unmatched reports (including cancelled games)
    are source evidence and MUST NOT be dropped.
    """
    if parsed.get("Source") != "nflverse.injuries" or parsed.get("ParserSchemaVersion") != 1:
        raise ValueError("Unexpected injury parser source or schema")
    season = parsed.get("Season")
    digest = parsed.get("AssetSha256")
    rows = parsed.get("Rows")
    if not isinstance(season, int) or not digest or not isinstance(rows, list):
        raise ValueError("Incomplete parsed injury report payload")
    if parsed.get("RowCount") != len(rows):
        raise ValueError("Parsed injury source row count does not match observations")
    claims, identity_fingerprint = _claims(canonical_players)
    games = _schedule_index(schedule, season)
    observed_game_keys: set[tuple[int, str, str]] = set()
    weeks: dict[int, list[dict[str, Any]]] = defaultdict(list)
    seen: set[int] = set()
    identity_counts = {"resolved-current-graph": 0, "unresolved": 0, "ambiguous": 0}
    game_counts = {"linked": 0, "not-found": 0, "ambiguous": 0, "not-evaluated": 0}

    for row in rows:
        ordinal, source = row.get("RowOrdinal"), row.get("Fields")
        if not isinstance(ordinal, int) or ordinal < 1 or ordinal in seen or not isinstance(source, dict):
            raise ValueError("Invalid or repeated injury source row ordinal")
        seen.add(ordinal)
        expected_key = f"sha256:{digest}:row:{ordinal}"
        if row.get("ObservationKey") != expected_key or source.get("season") != str(season):
            raise ValueError("Injury source observation provenance or season mismatch")
        try:
            week = int(source["week"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Injury report has invalid source week") from exc
        if not 1 <= week <= 22 or not source.get("game_type") or not source.get("team"):
            raise ValueError("Injury report has incomplete source game context")
        gsis = source.get("gsis_id")
        if not isinstance(gsis, str) or not _GSIS.fullmatch(gsis):
            raise ValueError("Injury report has invalid GSIS")
        owners = claims.get(gsis, set())
        identity_state = "unresolved" if not owners else ("resolved-current-graph" if len(owners) == 1 else "ambiguous")
        identity_counts[identity_state] += 1
        canonical_player_id = next(iter(owners)) if len(owners) == 1 else None
        game_key = (week, str(source["game_type"]), str(source["team"]))
        observed_game_keys.add(game_key)
        game_candidates = games.get(game_key, set()) if games is not None else set()
        game_state = ("not-evaluated" if games is None else
                      "not-found" if len(game_candidates) == 0 else
                      "linked" if len(game_candidates) == 1 else "ambiguous")
        game_counts[game_state] += 1
        weeks[week].append({
            "ObservationKey": expected_key,
            "RowOrdinal": ordinal,
            "Season": season,
            "Week": week,
            "GameType": source["game_type"],
            "SeasonType": source.get("season_type"),
            "SourceTeam": source["team"],
            "SourceIDs": {"GSIS": gsis},
            "CanonicalPlayerID": canonical_player_id,
            "IdentityResolution": identity_state,
            "GameID": next(iter(game_candidates)) if game_state == "linked" else None,
            "GameLinkState": game_state,
            "SourceModifiedRaw": source.get("date_modified"),
            "SourceModifiedAtUtc": None,
            "OriginalFields": dict(source),
        })
    # The published schedule attestation covers only facts capable of changing
    # a reported player's GameID or link state. A complete schedule digest would
    # churn whenever unrelated NFL results, kickoffs or game metadata refresh.
    # Include unmatched report team-weeks so later game corrections invalidate.
    link_fingerprint = (_digest({
        "Version": "injury-game-link-v1",
        "Season": season,
        "ObservedTeamGameCandidates": [
            {"Week": week, "GameType": game_type, "SourceTeam": team,
             "GameIDs": sorted(games.get((week, game_type, team), set()))}
            for week, game_type, team in sorted(observed_game_keys)
        ],
    }) if games is not None else None)
    partitions = []
    for week, observations in sorted(weeks.items()):
        observations.sort(key=lambda row: row["RowOrdinal"])
        partitions.append({
            "SchemaVersion": 1,
            "Season": season,
            "Week": week,
            "SourceDataset": "nflverse.injuries",
            "SourceAssetSha256": digest,
            "IdentityGraphFingerprint": identity_fingerprint,
            "IdentityTimeBasis": "current-graph-not-historical-point-in-time",
            "Completeness": "observed-rows-only-not-full-week-verification",
            "Observations": observations,
        })
    return {
        "SchemaVersion": 1,
        "Season": season,
        "SourceDataset": "nflverse.injuries",
        "SourceAssetSha256": digest,
        "IdentityGraphFingerprint": identity_fingerprint,
        "ScheduleGraphFingerprint": link_fingerprint,
        "Partitions": partitions,
        "Quality": {
            "SourceRowCount": len(rows),
            "ObservedWeekCount": len(partitions),
            "IdentityResolutionCounts": identity_counts,
            "GameLinkCounts": game_counts,
        },
    }
