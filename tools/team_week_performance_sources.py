"""Fail-closed canonical input adapter for reusable TeamWeekPerformance.

This adapter does not publish data. It avoids inferring historical roster
positions from mutable current-season player data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from weekly_lineup_optimizer import StartingSlot
from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.decision_windows import DecisionWindowsError, slot_definitions, slot_eligible


class WeekSourceNotReady(ValueError):
    """The inputs cannot support a reproducible weekly award yet."""


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise WeekSourceNotReady(f"Required canonical source is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WeekSourceNotReady(f"Invalid canonical source: {path}") from exc


def _league_source(repo_root: Path, league_id: str, season: int) -> tuple[Path, dict]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", league_id):
        raise ValueError("Invalid canonical league ID")
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json"
    league = _read_json(path)
    if not isinstance(league, dict) or league.get("CanonicalLeagueID") != league_id or league.get("Season") != season:
        raise WeekSourceNotReady(f"Canonical league/season identity mismatch: {path}")
    if not isinstance(league.get("RosterPositions"), list) or not isinstance(league.get("ScoringSettings"), dict):
        raise WeekSourceNotReady("Canonical league is missing RosterPositions or ScoringSettings")
    return path, league


def validate_final_week(
    repo_root: Path, league: dict, season: int, week: int,
    *, nfl_finality: Callable[..., tuple[bool, set[str]]] | None = None,
) -> str:
    """Use canonical NFL week finality AND historical Sleeper scored-week scope.

    The league provider's LastScoredLeg is a distinct, required gate: a final
    NFL week may not yet have official finalized fantasy league scores.
    """
    if type(week) is not int or week < 1:
        raise ValueError("Week must be a positive integer")
    structure = league.get("WeekStructure")
    if not isinstance(structure, dict) or structure.get("Season") != season:
        raise WeekSourceNotReady("Missing season-correct league WeekStructure")
    first = structure.get("StartWeek")
    ceiling = structure.get("ExpectedLastLeagueWeek")
    scored = structure.get("LastScoredLeg")
    if any(type(value) is not int for value in (first, ceiling, scored)):
        raise WeekSourceNotReady("League start/end/scored week must be explicit integers")
    if not first <= week <= ceiling or week > scored:
        raise WeekSourceNotReady(f"League scoring week {week} is not final (last scored {scored})")
    if nfl_finality is None:
        # Reuse the accepted, validated canonical NFL finality reader; do not
        # reinterpret score presence, elapsed time or app readmodel 'unknown'.
        from player_week_fantasy_materialize import _week_finality
        nfl_finality = _week_finality
    complete, game_ids = nfl_finality(repo_root, season=season, week=week)
    if complete is not True or not game_ids:
        raise WeekSourceNotReady(f"NFL regular season week {season}/{week} is not final")
    return f"{DATA_SOURCE_ROOT}/nfl/game-finality/{season}.json:REG-W{week};league:scored-week-confirmed"


def resolve_week_positions(
    repo_root: Path, season: int, week: int, matchup_rows: list[dict],
) -> dict[str, str]:
    """Resolve season-correct natural positions for ALL fantasy matchup players.

    The canonical target-week NFL roster is primary. Missing IR/Taxi/bye players
    can use earlier NFL weekly roster partitions in the SAME season, a
    finalized same-season roster, then consistent finalized PRIOR NFL seasons.
    Never use mutable current player profiles or unfinalized season rosters.
    """
    path = repo_root / DATA_SOURCE_ROOT / "nfl/weekly-rosters" / str(season) / f"{week:02d}.json"
    payload = _read_json(path)
    if not isinstance(payload, dict) or payload.get("Season") != season or payload.get("Week") != week:
        raise WeekSourceNotReady(f"NFL weekly roster season/week mismatch: {path}")
    rows = payload.get("Records")
    if not isinstance(rows, list):
        raise WeekSourceNotReady(f"Missing weekly NFL Records: {path}")
    positions: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise WeekSourceNotReady(f"Invalid weekly NFL player row: {path}")
        player_id, position = row.get("CanonicalPlayerID"), row.get("Position")
        if not isinstance(player_id, str) or not player_id or not isinstance(position, str) or not position.strip():
            continue
        position = position.upper().strip()
        if player_id in positions and positions[player_id] != position:
            raise WeekSourceNotReady(f"Conflicting historical positions for {player_id}")
        positions[player_id] = position
    owned = set()
    for team in matchup_rows:
        for ref in team.get("Players", []):
            player_id = ref.get("CanonicalPlayerID") if isinstance(ref, dict) else None
            if not isinstance(player_id, str) or not player_id:
                raise WeekSourceNotReady("Invalid historical fantasy roster player reference")
            owned.add(player_id)
    missing = owned - positions.keys()
    if missing:
        # Earlier weeks are immutable historical evidence for the same season.
        # Inspect every earlier week, not merely the nearest row, so conflicting
        # historical position changes cannot be silently masked.
        prior_positions: dict[str, str] = {}
        for prior_week in range(1, week):
            prior_path = path.parent / f"{prior_week:02d}.json"
            if not prior_path.is_file():
                continue
            prior_doc = _read_json(prior_path)
            if (not isinstance(prior_doc, dict) or prior_doc.get("Season") != season
                    or prior_doc.get("Week") != prior_week or not isinstance(prior_doc.get("Records"), list)):
                raise WeekSourceNotReady(f"Invalid prior-week NFL roster identity: {prior_path}")
            for row in prior_doc["Records"]:
                if not isinstance(row, dict):
                    raise WeekSourceNotReady(f"Invalid prior-week NFL roster row: {prior_path}")
                player_id, position = row.get("CanonicalPlayerID"), row.get("Position")
                if player_id not in missing or not isinstance(position, str) or not position.strip():
                    continue
                position = position.strip().upper()
                if player_id in prior_positions and prior_positions[player_id] != position:
                    raise WeekSourceNotReady(f"Conflicting prior-week historical positions for {player_id}")
                prior_positions[player_id] = position
        positions.update(prior_positions)
        missing = owned - positions.keys()
    if missing:
        # A finalized season roster is historical (not a mutable current-state
        # snapshot); its season-scoped position can fill unmatched inactive rows.
        season_path = repo_root / DATA_SOURCE_ROOT / "nfl/rosters" / f"{season}.json"
        if season_path.is_file():
            season_doc = _read_json(season_path)
            if not isinstance(season_doc, dict) or season_doc.get("Season") != season:
                raise WeekSourceNotReady(f"NFL season roster identity mismatch: {season_path}")
            if season_doc.get("Finalized") is True:
                records = season_doc.get("Records")
                if not isinstance(records, list):
                    raise WeekSourceNotReady(f"Finalized season roster missing Records: {season_path}")
                for row in records:
                    if not isinstance(row, dict):
                        raise WeekSourceNotReady(f"Invalid NFL season roster row: {season_path}")
                    player_id, position = row.get("CanonicalPlayerID"), row.get("Position")
                    if player_id not in missing or not isinstance(position, str) or not position.strip():
                        continue
                    position = position.strip().upper()
                    if player_id in positions and positions[player_id] != position:
                        raise WeekSourceNotReady(f"Conflicting finalized season positions for {player_id}")
                    positions[player_id] = position
    missing = owned - positions.keys()
    if missing:
        # A prior *completed* NFL season is immutable historical evidence, even
        # for a player who has no current-season NFL roster row (e.g. IR).
        # Match by CanonicalPlayerID and reject disagreements across years.
        historical_positions: dict[str, str] = {}
        historical_dir = repo_root / DATA_SOURCE_ROOT / "nfl/rosters"
        if historical_dir.is_dir():
            for prior_path in sorted(historical_dir.glob("*.json")):
                if not prior_path.stem.isdecimal():
                    continue
                prior_season = int(prior_path.stem)
                if prior_season >= season:
                    continue
                prior_doc = _read_json(prior_path)
                if not isinstance(prior_doc, dict) or prior_doc.get("Season") != prior_season:
                    raise WeekSourceNotReady(f"Historical NFL roster identity mismatch: {prior_path}")
                if prior_doc.get("Finalized") is not True:
                    continue
                prior_rows = prior_doc.get("Records")
                if not isinstance(prior_rows, list):
                    raise WeekSourceNotReady(f"Finalized historical NFL roster missing Records: {prior_path}")
                for row in prior_rows:
                    if not isinstance(row, dict):
                        raise WeekSourceNotReady(f"Invalid historical NFL roster row: {prior_path}")
                    player_id, position = row.get("CanonicalPlayerID"), row.get("Position")
                    if player_id not in missing or not isinstance(position, str) or not position.strip():
                        continue
                    position = position.strip().upper()
                    if player_id in historical_positions and historical_positions[player_id] != position:
                        raise WeekSourceNotReady(
                            f"Conflicting finalized prior-season positions for {player_id}"
                        )
                    historical_positions[player_id] = position
        positions.update(historical_positions)
    missing = sorted(owned - positions.keys())
    if missing:
        raise WeekSourceNotReady(
            f"Missing historical week {season}/{week} fantasy positions for "
            f"{len(missing)} of {len(owned)} roster players (first IDs: {missing[:5]}). "
            "No verified historical position; do not substitute current player profiles."
        )
    return {player_id: positions[player_id] for player_id in sorted(owned)}

def resolve_slots_from_league(roster_positions: list[Any], positions: dict[str, str]) -> list[StartingSlot]:
    """Resolve historical lineup slots with central Fantasy Relevance Python rules.

    Include standard fantasy positions for unpopulated slots, matching the old
    PowerShell adapter, without duplicating any FLEX or eligibility rules.
    """
    try:
        definitions = slot_definitions(roster_positions)
    except (DecisionWindowsError, TypeError, AttributeError) as exc:
        raise WeekSourceNotReady(f"Cannot resolve canonical starting slots: {exc}") from exc
    universe = sorted(
        {position.strip().upper() for position in positions.values()
         if isinstance(position, str) and position.strip()}
        | {"QB", "RB", "WR", "TE", "K"}
    )
    slots = []
    for definition in definitions:
        allowed = frozenset(pos for pos in universe if slot_eligible(pos, definition["SlotType"]))
        if not allowed:
            raise WeekSourceNotReady(f"Slot '{definition['SlotID']}' has no eligible position in supplied universe")
        slots.append(StartingSlot(definition["SlotID"], allowed))
    return slots

def load_verified_week_inputs(
    repo_root: Path, canonical_league_id: str, season: int, week: int,
    *, nfl_finality: Callable[..., tuple[bool, set[str]]] | None = None,
) -> dict[str, Any]:
    """Assemble, but do NOT publish, verified canonical team-week inputs.

    The canonical matchup week's Players are the authoritative fantasy-team
    candidate pool (ADR-036); no intraweek transfer replay is required for
    this deliberately week-scoped award. This adapter does not call the JSON
    writer; unresolved historical positions or week finality fail closed.
    """
    _, league = _league_source(repo_root, canonical_league_id, season)
    evidence = validate_final_week(repo_root, league, season, week, nfl_finality=nfl_finality)
    matchups = _read_json(
        repo_root / DATA_SOURCE_ROOT / "leagues" / canonical_league_id / "seasons" / str(season)
        / "matchups" / f"week-{week}.json"
    )
    if not isinstance(matchups, list) or not matchups:
        raise WeekSourceNotReady("Missing canonical fantasy team matchup rows")
    league_settings = league.get("Settings")
    expected_teams = league_settings.get("num_teams") if isinstance(league_settings, dict) else None
    if type(expected_teams) is not int or expected_teams < 1:
        raise WeekSourceNotReady("Missing valid historical league Settings.num_teams")
    if len(matchups) != expected_teams:
        raise WeekSourceNotReady(
            f"Incomplete weekly fantasy team population: expected {expected_teams}, got {len(matchups)}"
        )
    positions = resolve_week_positions(repo_root, season, week, matchups)
    slots = resolve_slots_from_league(league["RosterPositions"], positions)
    return {
        "canonical_league_id": canonical_league_id,
        "season": season,
        "week": week,
        "scoring_settings": league["ScoringSettings"],
        "slots": slots,
        "matchup_rows": matchups,
        "expected_team_count": expected_teams,
        "position_by_player": positions,
        "finalized": True,
        "finality_evidence": evidence,
    }
