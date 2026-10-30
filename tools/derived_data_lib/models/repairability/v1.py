"""repairability-v1: can an objective lineup problem still be repaired before the lock boundaries (ADR-074, Issue #1199).

Exact port of LineupRepairabilityUtils.psm1, LineupRepairabilityEvidenceUtils.psm1 and AcquisitionCapabilityUtils.psm1; no new
rule. The model bundles the matching rules with the temporary acquisition policy ``acquisition-waiver-only-v1`` (the Issue #493
bridge): external adds are waiver claims only, a claim is actionable only when the next waiver run lies strictly before the
candidate's kickoff, immediate free-agent adds and trade repairs do not exist. Issue #492 lands as ``repairability-v2``.

A model is a pure function of its explicit inputs: it reads no files and never the clock; the instant is an input. Slot
eligibility is passed in as a callable so the provider-neutral slot rules stay with the Decision Windows function.
Immutable after its first productive use; any change is ``repairability-v2``.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

MODEL_ID = "repairability-v1"
KIND = "repairability"

PARAMS = MappingProxyType({
    "AcquisitionPolicy": "acquisition-waiver-only-v1",
    "ExternalAcquisitionMode": "waiver-only",
    "ImmediateFreeAgentAddsAllowed": False,
    "TradeRepairAllowed": False,
})

UTC = timezone.utc
Eligible = Callable[[str | None, str], bool]


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def parse_utc(value: Any) -> datetime | None:
    """ISO instant (no zone means UTC) as an aware UTC datetime; None for blank or unparsable text."""
    if _blank(value):
        return None
    try:
        moment = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return (moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment).astimezone(UTC)


def resolve_acquisition(waivers_open: bool | None, next_waiver_run: str | None) -> dict[str, Any]:
    """Acquisition capability under the waiver-only bridge; conflicting or missing timing evidence is ``unknown``."""
    run = parse_utc(next_waiver_run)
    timing = "missing" if _blank(next_waiver_run) else "known" if run is not None else "invalid"
    state = "known"
    if waivers_open is None:
        state = "unknown"
    elif waivers_open:
        if timing != "known":
            state = "unknown"
    elif timing == "known":
        state = "unknown"  # a future run contradicts "adds unavailable"; neither fact is preferred
    allowed = None if waivers_open is None else bool(waivers_open)
    return {
        "State": state,
        "ExternalAcquisitionMode": PARAMS["ExternalAcquisitionMode"],
        "ExternalAddsAllowed": allowed,
        "ImmediateFreeAgentAddsAllowed": PARAMS["ImmediateFreeAgentAddsAllowed"],
        "WaiverAddsAllowed": allowed,
        "NextWaiverRun": run.strftime("%Y-%m-%dT%H:%M:%SZ") if state == "known" and allowed and run is not None else None,
        "TradeRepairAllowed": PARAMS["TradeRepairAllowed"],
    }


def complete_assignment(slots: list[dict[str, Any]], candidates: list[dict[str, Any]], eligible: Eligible) -> bool:
    """True when every slot can get its own eligible candidate (bipartite matching with augmenting paths)."""
    if not slots:
        return True
    by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        player_id = str(candidate["PlayerID"]).strip()
        if not player_id:
            continue
        if player_id in by_id:
            raise ValueError(f"Duplicate repairability candidate '{player_id}'.")
        by_id[player_id] = candidate
    if len(by_id) < len(slots):
        return False

    options: dict[str, list[str]] = {}
    for slot in slots:
        slot_id, slot_type = str(slot["SlotID"]), str(slot["SlotType"])
        if not slot_id.strip() or not slot_type.strip():
            raise ValueError("Repairability requires SlotID and SlotType.")
        options[slot_id] = sorted((p for p in by_id if eligible(by_id[p].get("Position"), slot_type)), key=str.lower)
        if not options[slot_id]:
            return False

    matched: dict[str, str] = {}

    def augment(slot_id: str, visited: set[str]) -> bool:
        for player_id in options[slot_id]:
            if player_id in visited:
                continue
            visited.add(player_id)
            if player_id not in matched or augment(matched[player_id], visited):
                matched[player_id] = slot_id
                return True
        return False

    for slot in sorted(slots, key=lambda s: (len(options[str(s["SlotID"])]), str(s["SlotID"]).lower())):
        if not augment(str(slot["SlotID"]), set()):
            return False
    return True


def resolve_state(
    mutable_slots: list[dict[str, Any]],
    internal: list[dict[str, Any]],
    external: list[dict[str, Any]],
    internal_unknown: bool,
    external_state: str,
    external_player_unknown: bool,
    eligible: Eligible,
) -> dict[str, Any]:
    """repairable | irreparable | unknown with Path and ReasonCode for the mutable slots of one team."""
    if not mutable_slots:
        state, path, reason = "unknown", None, "LINEUP_EVIDENCE_UNKNOWN"
    elif complete_assignment(mutable_slots, internal, eligible):
        state, path, reason = "repairable", "internal-roster", "INTERNAL_ASSIGNMENT_AVAILABLE"
    elif external_state == "available" and complete_assignment(mutable_slots, internal + external, eligible):
        state, path, reason = "repairable", "external-acquisition", "EXTERNAL_ACQUISITION_ASSIGNMENT_AVAILABLE"
    elif internal_unknown:
        state, path, reason = "unknown", None, "LINEUP_EVIDENCE_UNKNOWN"
    elif external_state == "unknown":
        state, path, reason = "unknown", None, "ACQUISITION_EVIDENCE_UNKNOWN"
    elif external_state == "available" and external_player_unknown:
        state, path, reason = "unknown", None, "EXTERNAL_PLAYER_EVIDENCE_UNKNOWN"
    else:
        state, path, reason = "irreparable", None, "NO_LEGAL_REPAIR_PATH"
    return {
        "State": state,
        "Path": path,
        "ReasonCode": reason,
        "InternalCandidateCount": len(internal),
        "ExternalCandidateCount": len(external),
    }


def external_evidence(
    players: list[dict[str, Any]],
    owned_ids: set[str],
    games: list[dict[str, Any]],
    mutable_slots: list[dict[str, Any]],
    acquisition: dict[str, Any] | None,
    lineup_week: int,
    at_utc: datetime,
    team_key: Callable[[Any], str | None],
    eligible: Eligible,
) -> dict[str, Any]:
    """Unrostered players a waiver claim could still bring in before their kickoff.

    ``players`` carry PlayerID, Position and TeamID; ``games`` carry Week, HomeTeamID, AwayTeamID, StartsAtUtc and Status.
    """
    state, next_run = "unknown", None
    if acquisition is not None and acquisition.get("State") == "known":
        allowed = acquisition.get("ExternalAddsAllowed")
        if allowed is None:
            state = "unknown"
        elif not allowed:
            state = "unavailable"
        else:
            next_run = parse_utc(acquisition.get("NextWaiverRun"))
            state = "available" if next_run is not None else "unknown"
    if state != "available":
        return {"State": state, "Candidates": [], "PlayerEvidenceUnknown": False}

    known_teams: set[str] = set()
    games_by_team: dict[str, list[dict[str, Any]]] = {}
    for game in games:
        keys = [team_key(game.get("HomeTeamID")), team_key(game.get("AwayTeamID"))]
        known_teams.update(k for k in keys if not _blank(k))
        if game.get("Week") != lineup_week:
            continue
        for key in keys:
            if not _blank(key):
                games_by_team.setdefault(key, []).append(game)

    by_id: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    for player in players:
        player_id = player.get("PlayerID")
        if _blank(player_id):
            continue
        if player_id in by_id or player_id in ambiguous:
            by_id.pop(player_id, None)
            ambiguous.add(player_id)
        else:
            by_id[player_id] = player
    evidence_unknown = bool(ambiguous)

    candidates: list[dict[str, Any]] = []
    for player_id in sorted(by_id, key=str.lower):
        if player_id in owned_ids:
            continue
        player = by_id[player_id]
        position = "" if _blank(player.get("Position")) else str(player["Position"]).strip().upper()
        if position and not any(eligible(position, str(slot["SlotType"])) for slot in mutable_slots):
            continue
        nfl_team = team_key(player.get("TeamID"))
        if _blank(nfl_team):
            continue
        if nfl_team not in known_teams:
            evidence_unknown = True
            continue
        team_games = games_by_team.get(nfl_team, [])
        if not team_games:
            continue
        if len(team_games) != 1:
            evidence_unknown = True
            continue
        game = team_games[0]
        start = parse_utc(game.get("StartsAtUtc"))
        if start is None:
            evidence_unknown = True
            continue
        status = str(game.get("Status") or "")
        if status.lower().startswith("final") or start <= at_utc.astimezone(UTC) or next_run >= start:
            continue
        if not position:
            evidence_unknown = True
            continue
        candidates.append({"PlayerID": player_id, "Position": position})
    return {"State": state, "Candidates": candidates, "PlayerEvidenceUnknown": evidence_unknown}
