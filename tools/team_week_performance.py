"""Consumer-neutral TeamWeekPerformance v1 derivation and persistence.

Caller must prove week finality and resolve *historical* fantasy positions and
slot eligibility before invoking this module. It deliberately does not read a
current roster, calculate fantasy scoring, or publish app-specific JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from player_week_fantasy import build_scoring_profile_identity
from weekly_lineup_optimizer import ScoredPlayer, StartingSlot, maximize_lineup
from data_roots import DATA_DERIVED_ROOT

CONTRACT_VERSION = 1
QUANTUM = Decimal("0.0001")


def _decimal(value: object, label: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Missing or invalid {label}")
    try:
        result = Decimal(str(value))
    except (ValueError, InvalidOperation) as error:
        raise ValueError(f"Invalid {label}") from error
    if not result.is_finite():
        raise ValueError(f"Non-finite {label}")
    return result


def _number(value: Decimal) -> float:
    return float(value.quantize(QUANTUM, rounding=ROUND_HALF_UP))


def _canonical_player_id(value: object, label: str) -> str:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a player reference")
    player_id = value.get("CanonicalPlayerID")
    if not isinstance(player_id, str) or not player_id.strip():
        raise ValueError(f"{label} lacks CanonicalPlayerID")
    return player_id


def _player_ids(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    result = [_canonical_player_id(value, label) for value in raw]
    if len(result) != len(set(result)):
        raise ValueError(f"{label} contains duplicate players")
    return result


def _point_map(raw: object, label: str) -> dict[str, Decimal]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    points: dict[str, Decimal] = {}
    for value in raw:
        if not isinstance(value, Mapping):
            raise ValueError(f"{label} contains invalid entry")
        player_id = _canonical_player_id(value.get("Player"), label)
        if player_id in points:
            raise ValueError(f"{label} has duplicate score for {player_id}")
        points[player_id] = _decimal(value.get("Points"), f"{label}[{player_id}].Points")
    return points


def _slot_fingerprint(slots: Sequence[StartingSlot]) -> str:
    payload = [{"SlotID": slot.slot_id,
                "EligiblePositions": sorted(slot.eligible_positions)} for slot in slots]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_team_week_performance(
    *,
    canonical_league_id: str,
    season: int,
    week: int,
    scoring_settings: Mapping[str, Any],
    slots: Sequence[StartingSlot],
    matchup_rows: Sequence[Mapping[str, Any]],
    expected_team_count: int,
    position_by_player: Mapping[str, str],
    finalized: bool,
    finality_evidence: str,
) -> dict[str, Any]:
    """Derive all-roster best ball and lineup utilization for a completed week.

    Starter, bench, taxi and IR/reserve all participate through Players.
    Ownership and scoring come from historical canonical league matchups;
    positions and slot rules are injected, not inferred from today's roster.
    """
    if not isinstance(canonical_league_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", canonical_league_id):
        raise ValueError("Invalid CanonicalLeagueID")
    if type(season) is not int or season < 1 or type(week) is not int or not 1 <= week <= 25:
        raise ValueError("Invalid Season or Week")
    if finalized is not True or not finality_evidence or not finality_evidence.strip():
        raise ValueError("Finality evidence required; a scored partition alone is insufficient")
    if not slots or len({slot.slot_id for slot in slots}) != len(slots):
        raise ValueError("Explicit unique starting slots are required")
    if any(not slot.slot_id or not slot.eligible_positions for slot in slots):
        raise ValueError("Invalid slot definition")
    if type(expected_team_count) is not int or expected_team_count < 1:
        raise ValueError("Historical league expected_team_count must be positive")
    if len(matchup_rows) != expected_team_count:
        raise ValueError(
            f"Incomplete weekly fantasy teams: expected {expected_team_count}, got {len(matchup_rows)}"
        )

    scoring_profile = build_scoring_profile_identity(canonical_league_id, season, scoring_settings)
    teams: list[dict[str, Any]] = []
    seen_rosters: set[str] = set()
    seen_players: set[str] = set()
    raw_metrics: dict[str, tuple[Decimal, Decimal | None]] = {}

    for row in matchup_rows:
        roster_id = row.get("CanonicalLeagueRosterID")
        if not isinstance(roster_id, str) or not roster_id.strip() or roster_id in seen_rosters:
            raise ValueError("Missing or duplicate CanonicalLeagueRosterID")
        seen_rosters.add(roster_id)
        if row.get("Week") != week:
            raise ValueError(f"Matchup Week mismatch for {roster_id}")
        members = _player_ids(row.get("Players"), f"{roster_id}.Players")
        starters = _player_ids(row.get("Starters"), f"{roster_id}.Starters")
        points = _point_map(row.get("PlayerPoints"), f"{roster_id}.PlayerPoints")
        starter_points = _point_map(row.get("StarterPoints"), f"{roster_id}.StarterPoints")
        if set(members) != set(points) or not set(starters).issubset(members):
            raise ValueError(f"Incomplete player/point ownership for {roster_id}")
        if set(starters) != set(starter_points):
            raise ValueError(f"Incomplete starter points for {roster_id}")
        if any(starter_points[player] != points[player] for player in starters):
            raise ValueError(f"Inconsistent starter/player scores for {roster_id}")
        if len(seen_players.intersection(members)):
            raise ValueError("Player appears on multiple fantasy teams in same week")
        seen_players.update(members)
        candidates = []
        for player_id in members:
            position = position_by_player.get(player_id)
            if not isinstance(position, str) or not position.strip():
                raise ValueError(f"Missing historical fantasy position for {player_id}")
            candidates.append(ScoredPlayer(player_id, position.strip().upper(), points[player_id]))
        # Even though the hypothetical best ball may leave slots empty, the
        # recorded lineup must admit a one-to-one assignment to historical slots.
        starter_members = [ScoredPlayer(item.player_id, item.position, Decimal(1))
                           for item in candidates if item.player_id in starter_points]
        if len(starters) > len(slots) or len(maximize_lineup(slots, starter_members).assignments) != len(starters):
            raise ValueError(f"Historical starters cannot fit lineup slots for {roster_id}")
        best_ball = maximize_lineup(slots, candidates)
        actual = sum(starter_points.values(), Decimal(0))
        if actual > best_ball.points:
            raise ValueError(f"Actual starter score exceeds all-roster maximum for {roster_id}")
        official = _decimal(row.get("Points"), f"{roster_id}.Points")
        maximum = best_ball.points
        efficiency = actual * Decimal(100) / maximum if maximum > 0 else None
        raw_metrics[roster_id] = (maximum, efficiency)
        teams.append({
            "CanonicalLeagueRosterID": roster_id,
            "ActualStarterPoints": _number(actual),
            "OfficialMatchupPoints": _number(official),
            "PotentialPoints": _number(maximum),
            "EfficiencyPercent": _number(efficiency) if efficiency is not None else None,
            "MissedPoints": _number(maximum - actual),
            "OptimalLineup": [
                {"SlotID": item.slot_id, "CanonicalPlayerID": item.player_id,
                 "Points": _number(item.points)} for item in best_ball.assignments
            ],
            "UnfilledSlotIDs": list(best_ball.unfilled_slot_ids),
        })

    teams.sort(key=lambda item: item["CanonicalLeagueRosterID"])
    manager_max = max(item[0] for item in raw_metrics.values())
    coach_max = max((item[1] for item in raw_metrics.values()
                     if item[1] is not None), default=None)
    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": canonical_league_id,
        "Season": season,
        "Week": week,
        "ScoringProfile": scoring_profile,
        "LineupDefinitionHash": _slot_fingerprint(slots),
        "FinalityEvidence": finality_evidence,
        "Teams": teams,
        "Awards": {
            "BestManagerRosterIDs": [item["CanonicalLeagueRosterID"] for item in teams
                                     if manager_max > 0 and raw_metrics[item["CanonicalLeagueRosterID"]][0] == manager_max],
            "BestCoachRosterIDs": [item["CanonicalLeagueRosterID"] for item in teams
                                   if coach_max is not None and raw_metrics[item["CanonicalLeagueRosterID"]][1] == coach_max],
        },
    }


def output_path(repo_root: Path, model: Mapping[str, Any]) -> Path:
    league_id = model.get("CanonicalLeagueID")
    season, week = model.get("Season"), model.get("Week")
    if not isinstance(league_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", league_id):
        raise ValueError("Invalid CanonicalLeagueID for output path")
    if type(season) is not int or type(week) is not int or season < 1 or not 1 <= week <= 25:
        raise ValueError("Invalid season/week for output path")
    return repo_root / DATA_DERIVED_ROOT / "team-week-performance" / league_id / str(season) / f"{week:02d}.json"


def save_team_week_performance(repo_root: Path, model: Mapping[str, Any]) -> bool:
    """Persist a stable shared-derived record; return False for a semantic no-op."""
    target = output_path(repo_root, model)
    data = (json.dumps(model, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if target.is_file() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".team-week-", suffix=".json", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return True
