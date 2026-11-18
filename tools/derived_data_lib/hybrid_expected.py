"""CP2 shadow preview: locked starters plus remaining weekly best-ball × actual coach efficiency.

This is *not* the active MatchupProjections team-range or win-probability method.
Decision Windows owns slot eligibility/locks; PlayerWeekFantasy owns projected points;
TeamWeekPerformance -> season-statistics owns observed manager efficiency.
The optimizer is the existing globally constrained weekly_lineup_optimizer.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from derived_data_lib.decision_windows import slot_eligible
from weekly_lineup_optimizer import ScoredPlayer, StartingSlot, maximize_lineup

METHOD_ID = "weekly-hybrid-actual-efficiency-preview-v1"
POOL_BASIS = "active-roster-only"
PARTICIPATION_BASIS = "conditional-on-participation"
# Candidate positions cover the standard fantasy slots even if the current roster
# lacks one. Actual slot eligibility is *always* checked by Decision Windows.
KNOWN_POSITIONS = frozenset(("QB", "RB", "WR", "TE", "K", "DEF", "DL", "LB", "DB", "IDP"))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _empty(state: str, reason: str | None, efficiency: float | None, through_week: int | None) -> dict[str, Any]:
    return {
        "Method": METHOD_ID,
        "State": state,
        "Reason": reason,
        "PoolBasis": POOL_BASIS,
        "ParticipationBasis": PARTICIPATION_BASIS,
        "SourceThroughWeek": through_week,
        "ManagerEfficiencyPercent": efficiency,
        "ExpectedPoints": None,
        "LockedProjectedPoints": 0.0,
        "LockedActualPoints": 0.0,
        "RemainingBestBallPoints": None,
        "LockedStarterPlayerIDs": [],
        "OptimalRemainingPlayerIDs": [],
        "UnfilledSlotIDs": [],
        "ExcludedPlayerCounts": {},
        "ConditionalAvailabilityPlayerIDs": [],
    }


def build_team_preview(
    team: Mapping[str, Any],
    definitions: list[Mapping[str, Any]],
    projections: Mapping[str, Mapping[str, Any]],
    starter_evidence: Mapping[str, Mapping[str, Any]],
    *,
    manager_efficiency_percent: Any,
    source_through_week: Any,
) -> dict[str, Any]:
    """Preview one team at a supplied Decision-Windows instant (no clock/file reads).

    A current active-roster player whose game has not locked may be reselected,
    irrespective of his current starter/bench position. A locked starter is fixed
    to his existing slot, whereas a locked bench player cannot compete. Only
    remaining slots are optimized and weighted by historical actual efficiency.
    Missing mandatory slots and contradictory lock/final evidence never yield a
    complete ExpectedPoints value. IR and Taxi are conditional roster-move options
    and intentionally *not* silently treated as instantly activatable.
    """
    eff = _number(manager_efficiency_percent)
    through = source_through_week if type(source_through_week) is int and source_through_week > 0 else None
    base = _empty("unavailable", "invalid-input", eff, through)
    if not isinstance(team, Mapping) or not isinstance(definitions, list):
        return base
    slots = team.get("Slots")
    players = team.get("Players")
    if not isinstance(slots, list) or not isinstance(players, list) or not definitions:
        return base

    slot_ids = [s.get("SlotID") for s in slots if isinstance(s, Mapping)]
    canonical_ids = [s.get("SlotID") for s in definitions if isinstance(s, Mapping)]
    if (len(slot_ids) != len(slots) or len(canonical_ids) != len(definitions)
            or len(set(slot_ids)) != len(slots) or slot_ids != canonical_ids
            or any(not isinstance(s.get("SlotType"), str) for s in slots)):
        base["Reason"] = "inconsistent-slot-definitions"
        return base

    by_id: dict[str, Mapping[str, Any]] = {}
    for player in players:
        if not isinstance(player, Mapping) or player.get("PlayerID") is None:
            base["Reason"] = "invalid-player-evidence"
            return base
        pid = str(player["PlayerID"])
        if not pid or pid in by_id:
            base["Reason"] = "duplicate-or-blank-player-id"
            return base
        by_id[pid] = player

    fixed_ids: set[str] = set()
    fixed_projected = 0.0
    fixed_actual = 0.0
    free_slots = []
    for slot in slots:
        state = slot.get("State")
        if state in ("unlocked", "bye"):
            free_slots.append(slot)
            continue
        if state not in ("locked-active", "completed"):
            base["Reason"] = "unknown-slot-lock-state"
            return base
        raw_id = slot.get("CurrentStarterID")
        if raw_id is None:
            base["Reason"] = "locked-slot-without-starter"
            return base
        pid = str(raw_id)
        player = by_id.get(pid)
        if (player is None or player.get("Placement") != "starter"
                or player.get("LineupSlotID") != slot["SlotID"]
                or player.get("GameState") != state or pid in fixed_ids):
            base["Reason"] = "contradictory-locked-starter"
            return base
        fixed_ids.add(pid)
        evidence = starter_evidence.get(pid)
        if not isinstance(evidence, Mapping):
            base["Reason"] = "missing-locked-starter-evidence"
            return base
        if state == "completed":
            actual = _number(evidence.get("points")) if evidence.get("final") is True else None
            if actual is None:
                base["Reason"] = "missing-final-starter-points"
                return base
            fixed_actual += actual
        else:
            if evidence.get("final") is True:
                base["Reason"] = "contradictory-active-game-finality"
                return base
            if player.get("ScoringAvailability", {}).get("State") == "out":
                # A locked OUT starter is still irrevocably occupying his slot.
                fixed_projected += 0.0
            else:
                projection = projections.get(pid)
                points = (_number(projection.get("Points")) if isinstance(projection, Mapping)
                          and projection.get("Status") == "available" else None)
                if points is None:
                    base["Reason"] = "missing-locked-starter-projection"
                    return base
                fixed_projected += points

    base["LockedStarterPlayerIDs"] = sorted(fixed_ids)
    base["LockedActualPoints"] = round(fixed_actual, 4)
    base["LockedProjectedPoints"] = round(fixed_projected, 4)

    counts: dict[str, int] = {}
    candidates: list[ScoredPlayer] = []
    conditional_ids: set[str] = set()
    for pid, player in sorted(by_id.items()):
        placement = player.get("Placement")
        if placement not in ("starter", "bench"):
            reason = "taxi" if placement == "taxi" else "ir" if placement == "ir" else "unknown-placement"
        elif player.get("GameState") in ("locked-active", "completed"):
            reason = "locked-starter" if pid in fixed_ids else "locked-bench"
        elif player.get("GameState") == "bye":
            reason = "bye"
        elif player.get("GameState") != "unlocked":
            reason = "unknown-game"
        elif not isinstance(player.get("Position"), str) or not player["Position"].strip():
            reason = "unknown-position"
        elif (isinstance(player.get("ScoringAvailability"), Mapping)
              and player["ScoringAvailability"].get("State") == "out"):
            reason = "confirmed-out"
        else:
            projection = projections.get(pid)
            points = (_number(projection.get("Points")) if isinstance(projection, Mapping)
                      and projection.get("Status") == "available" else None)
            if points is None:
                reason = "missing-projection"
            else:
                position = player["Position"].strip().upper()
                candidates.append(ScoredPlayer(pid, position, points))
                status = player.get("ScoringAvailability")
                if not isinstance(status, Mapping) or status.get("State") in (None, "unknown", "uncertain"):
                    conditional_ids.add(pid)
                continue
        counts[reason] = counts.get(reason, 0) + 1
    base["ExcludedPlayerCounts"] = dict(sorted(counts.items()))

    position_universe = KNOWN_POSITIONS.union(p.position for p in candidates)
    opt_slots = []
    for slot in free_slots:
        accepted = frozenset(p for p in position_universe if slot_eligible(p, slot["SlotType"]))
        if not accepted:
            base["Reason"] = "unsupported-slot-eligibility"
            return base
        opt_slots.append(StartingSlot(str(slot["SlotID"]), accepted))

    optimal = maximize_lineup(opt_slots, candidates) if opt_slots else None
    selected = [] if optimal is None else [a.player_id for a in optimal.assignments]
    base["OptimalRemainingPlayerIDs"] = selected
    base["ConditionalAvailabilityPlayerIDs"] = sorted(set(selected).intersection(conditional_ids))
    base["UnfilledSlotIDs"] = [] if optimal is None else list(optimal.unfilled_slot_ids)
    remaining = 0.0 if optimal is None else float(optimal.points)
    base["RemainingBestBallPoints"] = round(remaining, 4)

    if base["UnfilledSlotIDs"]:
        base["State"] = "incomplete"
        base["Reason"] = "unfilled-required-slots"
    elif free_slots and (eff is None or not 0 <= eff <= 100 or through is None):
        base["State"] = "unavailable"
        base["Reason"] = "missing-or-invalid-historical-efficiency"
    else:
        # Fixed points are never discounted by coach efficiency.
        expected = fixed_actual + fixed_projected + remaining * (eff or 0.0) / 100.0
        base["State"] = "available"
        base["Reason"] = None
        base["ExpectedPoints"] = round(expected, 4)
    return base
