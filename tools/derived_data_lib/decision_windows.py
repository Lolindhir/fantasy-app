"""Decision Windows for one league, season and instant (ADR-074, Issue #1199 section 2).

Pure-function port of ``DecisionWindowUtils.psm1``: exact-kickoff windows, player lock facts, objective team lineup evaluations
and the next-week lookahead. The derivation core (``build_base_model``) takes explicit data only; ``resolve_base`` reads the
canonical inputs (league source, rosters, Sleeper snapshot with the team registry, NFL schedule with game finality, lifecycle).
``public/data`` and the previous ``DecisionWindows.json`` are never inputs. Nothing is persisted; the instant is an explicit input.

Later steps of the issue add Fantasy Relevance, scoring availability, repairability and the scoring path on top of this base.
Contract: ``.ai-context/manual/decision-windows.yaml``.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from league_metadata import LeagueMetadataError, data_meta_root, load_league_metadata, model_for
from nfl_source_data_lib.teams import NflTeamRegistry, NflTeamRegistryError
from schedule_archive import ScheduleArchiveError, build_schedule

from .league_lifecycle import LifecycleError, parse_instant, resolve_lifecycle
from .models.registry import UnknownModelError, get_model

UTC = timezone.utc
SCHEMA_VERSION = 1


class DecisionWindowsError(ValueError):
    """Missing or contradicting Decision Windows input (fail closed)."""


# ---------------------------------------------------------------------------------------------------------------------
# Helpers shared by the derivation core


def utc_text(value: Any) -> str:
    """ISO instant (Z or offset; no zone means UTC) as ``yyyy-MM-ddTHH:mm:ssZ``."""
    try:
        moment = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionWindowsError(f"Decision Window schedule contains invalid StartsAtUtc '{value}'.") from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _collection(value: Any) -> tuple[bool, list[Any]]:
    if value is None:
        return True, []
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
        return False, []
    return True, list(value)


def _player_id(value: Any) -> tuple[str, str | None]:
    """(state, id): state is empty, malformed or valid; Sleeper marks an unfilled slot as '0'."""
    if value is None:
        return "empty", None
    if isinstance(value, (list, tuple, set, dict)):
        return "malformed", None
    text = str(value).strip()
    if text == "" or text == "0":
        return "empty", None
    return "valid", text


def _issue(code: str, state: str, player_id: str | None = None, count: int | None = None) -> dict[str, Any]:
    return {"Code": code, "State": state, "PlayerID": player_id, "Count": count}


def _evaluation_state(issues: list[dict[str, Any]]) -> str:
    states = {issue["State"] for issue in issues}
    for state in ("unknown", "action-required", "review"):
        if state in states:
            return state
    return "ready"


def _issue_key(issue: dict[str, Any]) -> tuple[Any, ...]:
    player = issue["PlayerID"]
    count = issue["Count"]
    return (
        issue["Code"].lower(),
        (0, "") if player is None else (1, player.lower()),
        (0, 0) if count is None else (1, count),
    )


def _unique_sorted_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for issue in sorted(issues, key=_issue_key):
        seen.setdefault(_issue_key(issue), issue)
    return list(seen.values())


def make_team_key(registry: NflTeamRegistry | None) -> Callable[[Any], str | None]:
    """Canonical team join key (abbreviation, provider spelling or legacy ID); an unknown value joins as itself."""

    def team_key(value: Any) -> str | None:
        if _blank(value):
            return None
        text = str(value).strip()
        if registry is None:
            return text
        try:
            return registry.resolve(text)
        except NflTeamRegistryError:
            return text

    return team_key


# ---------------------------------------------------------------------------------------------------------------------
# Derivation core (port of Get-DecisionWindowFacts / New-DecisionWindowsReadModel)


def _normalize_games(schedule_games: list[dict[str, Any]], team_key: Callable[[Any], str | None]) -> tuple[list[dict[str, Any]], set[str]]:
    games: list[dict[str, Any]] = []
    game_ids: set[str] = set()
    known_teams: set[str] = set()
    for game in schedule_games:
        if game is None:
            raise DecisionWindowsError("Decision Window schedule contains a null game.")
        game_id = str(game.get("GameID") or "").strip()
        home = str(game.get("HomeTeamID") or "").strip()
        away = str(game.get("AwayTeamID") or "").strip()
        if not game_id:
            raise DecisionWindowsError("Decision Window schedule contains a game without GameID.")
        if not home or not away:
            raise DecisionWindowsError(f"Decision Window game '{game_id}' is missing a stable home/away team identity.")
        if game_id in game_ids:
            raise DecisionWindowsError(f"Decision Window schedule contains duplicate GameID '{game_id}'.")
        if game.get("Week") is None:
            raise DecisionWindowsError(f"Decision Window game '{game_id}' is missing Week.")
        try:
            week = int(game["Week"])
        except (TypeError, ValueError) as exc:
            raise DecisionWindowsError(f"Decision Window game '{game_id}' has invalid Week '{game['Week']}'.") from exc
        games.append({
            "GameID": game_id,
            "Week": week,
            "StartsAtUtc": utc_text(game.get("StartsAtUtc")),
            "AwayTeamID": away,
            "AwayTeamAbbr": None if _blank(game.get("AwayTeamAbbr")) else str(game["AwayTeamAbbr"]).strip(),
            "HomeTeamID": home,
            "HomeTeamAbbr": None if _blank(game.get("HomeTeamAbbr")) else str(game["HomeTeamAbbr"]).strip(),
        })
        game_ids.add(game_id)
        known_teams.add(team_key(home))
        known_teams.add(team_key(away))
    return games, known_teams


def derive_facts(
    season: str,
    week: int,
    schedule_games: list[dict[str, Any]],
    rosters: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    expected_starter_count: int,
    team_key: Callable[[Any], str | None],
) -> dict[str, Any]:
    """Windows, player lock facts and team lineup evaluations of one lineup week."""
    if not str(season).strip():
        raise DecisionWindowsError("Decision Window derivation requires Season.")
    if week < 0:
        raise DecisionWindowsError("Decision Window derivation requires a non-negative Week.")
    if not 0 <= expected_starter_count <= 100:
        raise DecisionWindowsError("ExpectedStarterCount must be between 0 and 100.")

    games, known_teams = _normalize_games(schedule_games, team_key)
    week_games = sorted((g for g in games if g["Week"] == week), key=lambda g: (g["StartsAtUtc"], g["GameID"]))
    games_by_team: dict[str, list[dict[str, Any]]] = {}
    for game in week_games:
        for team in (team_key(game["HomeTeamID"]), team_key(game["AwayTeamID"])):
            games_by_team.setdefault(team, []).append(game)

    windows: list[dict[str, Any]] = []
    window_by_id: dict[str, dict[str, Any]] = {}
    for starts_at in sorted({g["StartsAtUtc"] for g in week_games}):
        group = [g for g in week_games if g["StartsAtUtc"] == starts_at]
        window = {
            "DecisionWindowID": starts_at,
            "Week": week,
            "StartsAtUtc": starts_at,
            "Games": [
                {k: g[k] for k in ("GameID", "Week", "AwayTeamID", "AwayTeamAbbr", "HomeTeamID", "HomeTeamAbbr")}
                for g in sorted(group, key=lambda g: g["GameID"])
            ],
            "ParticipatingNFLTeamIDs": sorted({t for g in group for t in (g["AwayTeamID"], g["HomeTeamID"])}, key=str.lower),
            "FantasyContextState": "available",
            "AffectedFantasyTeams": [],
        }
        windows.append(window)
        window_by_id[starts_at] = window

    assignment_by_player: dict[str, str | None] = {}
    ambiguous: set[str] = set()
    for assignment in assignments:
        if assignment is None:
            raise DecisionWindowsError("Decision Window player-team assignments contain a null record.")
        state, player_id = _player_id(assignment.get("PlayerID"))
        if state != "valid":
            raise DecisionWindowsError("Decision Window player-team assignment is missing a valid PlayerID.")
        if "NFLTeamID" not in assignment:
            raise DecisionWindowsError(f"Decision Window player-team assignment for '{player_id}' is missing NFLTeamID.")
        team = None if _blank(assignment["NFLTeamID"]) else str(assignment["NFLTeamID"]).strip()
        if player_id in assignment_by_player or player_id in ambiguous:
            assignment_by_player.pop(player_id, None)
            ambiguous.add(player_id)
            continue
        assignment_by_player[player_id] = team

    team_ids: set[str] = set()
    owner_by_player: dict[str, str] = {}
    lock_facts: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    affected: dict[tuple[str, str], dict[str, Any]] = {}

    for roster in rosters:
        if roster is None:
            raise DecisionWindowsError("Decision Window fantasy rosters contain a null record.")
        fantasy_key = str(roster.get("FantasyTeamID") if roster.get("FantasyTeamID") is not None else "").strip()
        if not fantasy_key:
            raise DecisionWindowsError("Decision Window fantasy roster is missing FantasyTeamID.")
        if fantasy_key in team_ids:
            raise DecisionWindowsError(f"Decision Window fantasy rosters contain duplicate FantasyTeamID '{fantasy_key}'.")
        team_ids.add(fantasy_key)

        issues: list[dict[str, Any]] = []
        roster_valid, roster_items = _collection(roster["PlayerIDs"]) if "PlayerIDs" in roster else (False, [])
        starter_valid, starter_items = _collection(roster["StarterIDs"]) if "StarterIDs" in roster else (False, [])
        if not roster_valid:
            issues.append(_issue("MALFORMED_ROSTER_STRUCTURE", "unknown"))
        if not starter_valid:
            issues.append(_issue("MALFORMED_STARTER_STRUCTURE", "unknown"))

        roster_ids: list[str] = []
        roster_seen: set[str] = set()
        for raw in roster_items:
            state, player_id = _player_id(raw)
            if state != "valid":
                issues.append(_issue("MALFORMED_ROSTER_PLAYER", "unknown"))
                continue
            if player_id in roster_seen:
                issues.append(_issue("DUPLICATE_ROSTER_PLAYER", "unknown", player_id))
                continue
            roster_seen.add(player_id)
            roster_ids.append(player_id)
            if player_id in owner_by_player and owner_by_player[player_id] != fantasy_key:
                raise DecisionWindowsError(f"Decision Window roster evidence assigns PlayerID '{player_id}' to multiple fantasy teams.")
            owner_by_player[player_id] = fantasy_key

        starter_ids: list[str] = []
        starter_seen: set[str] = set()
        for raw in starter_items:
            state, player_id = _player_id(raw)
            if state == "empty":
                continue
            if state != "valid":
                issues.append(_issue("MALFORMED_STARTER_PLAYER", "unknown"))
                continue
            if player_id in starter_seen:
                issues.append(_issue("DUPLICATE_STARTER", "unknown", player_id))
                continue
            starter_seen.add(player_id)
            starter_ids.append(player_id)
            if player_id not in roster_seen:
                issues.append(_issue("STARTER_NOT_IN_ROSTER", "unknown", player_id))

        starter_count = len(starter_ids)
        if starter_count < expected_starter_count:
            issues.append(_issue("OPEN_STARTER_SLOT", "action-required", count=expected_starter_count - starter_count))
        elif starter_count > expected_starter_count:
            issues.append(_issue("STARTER_COUNT_OVERFLOW", "unknown", count=starter_count - expected_starter_count))

        for player_id in roster_ids:
            is_starter = player_id in starter_seen
            nfl_team = None
            kind = "unknown"
            game_id = window_id = starts_at = None
            if player_id in ambiguous or player_id not in assignment_by_player:
                kind = "unknown"
            else:
                nfl_team = assignment_by_player[player_id]
                if _blank(nfl_team):
                    kind = "no-team"
                elif team_key(nfl_team) not in known_teams:
                    kind = "unknown"
                elif team_key(nfl_team) not in games_by_team:
                    kind = "bye"
                else:
                    candidates = games_by_team[team_key(nfl_team)]
                    if len(candidates) != 1:
                        kind = "unknown"
                    else:
                        kind = "scheduled"
                        game_id = candidates[0]["GameID"]
                        starts_at = candidates[0]["StartsAtUtc"]
                        window_id = starts_at

            lock_facts.append({
                "FantasyTeamID": roster["FantasyTeamID"],
                "PlayerID": player_id,
                "NFLTeamID": nfl_team,
                "Kind": kind,
                "GameID": game_id,
                "DecisionWindowID": window_id,
                "StartsAtUtc": starts_at,
                "IsStarter": is_starter,
            })

            if kind == "unknown":
                issues.append(_issue("STARTER_LOCK_UNKNOWN" if is_starter else "UNRESOLVED_ROSTER_PLAYER", "unknown", player_id))
            elif is_starter and kind == "bye":
                issues.append(_issue("STARTER_ON_BYE", "action-required", player_id))
            elif is_starter and kind == "no-team":
                issues.append(_issue("STARTER_WITHOUT_NFL_TEAM", "review", player_id))

            if kind == "scheduled":
                entry = affected.setdefault(
                    (window_id, fantasy_key),
                    {"WindowID": window_id, "FantasyTeamID": roster["FantasyTeamID"], "Players": []},
                )
                entry["Players"].append({"PlayerID": player_id, "NFLTeamID": nfl_team, "GameID": game_id, "IsStarter": is_starter})

        unique = _unique_sorted_issues(issues)
        evaluations.append({
            "FantasyTeamID": roster["FantasyTeamID"],
            "State": _evaluation_state(unique),
            "ExpectedStarterCount": expected_starter_count,
            "StarterCount": starter_count,
            "OpenStarterSlots": max(0, expected_starter_count - starter_count),
            "Issues": unique,
        })

    for (window_id, _team), entry in sorted(affected.items(), key=lambda item: (item[0][0], item[0][1])):
        if window_id not in window_by_id:
            raise DecisionWindowsError(f"Decision Window association references missing window '{window_id}'.")
        players = sorted(entry["Players"], key=lambda p: p["PlayerID"].lower())
        window_by_id[window_id]["AffectedFantasyTeams"].append({
            "FantasyTeamID": entry["FantasyTeamID"],
            "AffectedRosteredPlayerCount": len(players),
            "AffectedStarterCount": sum(1 for p in players if p["IsStarter"]),
            "Players": players,
        })
    for window in windows:
        window["AffectedFantasyTeams"].sort(key=lambda t: str(t["FantasyTeamID"]))

    return {
        "Season": season,
        "Week": week,
        "DecisionWindows": sorted(windows, key=lambda w: w["StartsAtUtc"]),
        "PlayerLockFacts": sorted(lock_facts, key=lambda f: (str(f["FantasyTeamID"]), f["PlayerID"].lower())),
        "TeamLineupEvaluations": sorted(evaluations, key=lambda e: str(e["FantasyTeamID"])),
    }


def _pending_window(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "DecisionWindowID": window["DecisionWindowID"],
        "Week": window["Week"],
        "StartsAtUtc": window["StartsAtUtc"],
        "Games": window["Games"],
        "ParticipatingNFLTeamIDs": window["ParticipatingNFLTeamIDs"],
        "FantasyContextState": "pending",
        "AffectedFantasyTeams": [],
    }


def _lookahead(season: str, week: int, schedule_games: list[dict[str, Any]], team_key: Callable[[Any], str | None]) -> dict[str, Any] | None:
    nxt = derive_facts(season, week, schedule_games, [], [], 0, team_key)
    return _pending_window(nxt["DecisionWindows"][0]) if nxt["DecisionWindows"] else None


def build_base_model(
    league_id: Any,
    season: str,
    lineup_week: int,
    last_lineup_week: int,
    schedule_games: list[dict[str, Any]],
    rosters: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    expected_starter_count: int,
    team_key: Callable[[Any], str | None],
) -> dict[str, Any]:
    """Port of New-DecisionWindowsReadModel (SchemaVersion 1 base, before Relevance/Availability/Repairability)."""
    if last_lineup_week < 1:
        raise DecisionWindowsError("LastLineupWeek must be positive.")

    if lineup_week < 1 or lineup_week > last_lineup_week:
        pending = [
            {
                "FantasyTeamID": roster["FantasyTeamID"],
                "State": "pending",
                "ExpectedStarterCount": expected_starter_count,
                "StarterCount": None,
                "OpenStarterSlots": None,
                "Issues": [],
            }
            for roster in sorted(rosters, key=lambda r: str(r["FantasyTeamID"]))
        ]
        return {
            "SchemaVersion": SCHEMA_VERSION,
            "LeagueID": league_id,
            "Season": season,
            "LineupWeek": lineup_week,
            "LastLineupWeek": last_lineup_week,
            "DecisionWindows": [],
            "LookaheadDecisionWindow": _lookahead(season, 1, schedule_games, team_key) if lineup_week < 1 else None,
            "PlayerLockFacts": [],
            "TeamLineupEvaluations": pending,
        }

    current = derive_facts(season, lineup_week, schedule_games, rosters, assignments, expected_starter_count, team_key)
    lookahead = _lookahead(season, lineup_week + 1, schedule_games, team_key) if lineup_week < last_lineup_week else None
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "LeagueID": league_id,
        "Season": season,
        "LineupWeek": lineup_week,
        "LastLineupWeek": last_lineup_week,
        "DecisionWindows": current["DecisionWindows"],
        "LookaheadDecisionWindow": lookahead,
        "PlayerLockFacts": current["PlayerLockFacts"],
        "TeamLineupEvaluations": current["TeamLineupEvaluations"],
    }


# ---------------------------------------------------------------------------------------------------------------------
# Fantasy Relevance and participant scoring path (port of FantasyRelevanceV2Utils / ParticipantScoringPathDecisionUtils)

_FLEX_ELIGIBILITY = {
    "FLEX": ("RB", "WR", "TE"),
    "SUPER_FLEX": ("QB", "RB", "WR", "TE"),
    "WRRB_FLEX": ("WR", "RB"),
    "REC_FLEX": ("WR", "TE"),
}
RELEVANCE_VERSION = 3


def slot_definitions(roster_positions: Any) -> list[dict[str, Any]]:
    """Starting slots in lineup order (bench excluded) with per-type ordinals."""
    if roster_positions is None or len(roster_positions) == 0:
        raise DecisionWindowsError("Fantasy Relevance requires league roster_positions.")
    occurrences: dict[str, int] = {}
    result: list[dict[str, Any]] = []
    for raw in roster_positions:
        if _blank(raw):
            continue
        slot_type = str(raw).strip().upper()
        if slot_type == "BN":
            continue
        occurrences[slot_type] = occurrences.get(slot_type, 0) + 1
        result.append({
            "SlotID": f"{slot_type}-{occurrences[slot_type]}",
            "SlotType": slot_type,
            "SlotOrdinal": occurrences[slot_type],
            "SlotIndex": len(result),
        })
    if not result:
        raise DecisionWindowsError("Fantasy Relevance could not derive starting slots from roster_positions.")
    return result


def slot_eligible(position: str | None, slot_type: str) -> bool:
    if _blank(position):
        return False
    key = str(position).strip().upper()
    slot = slot_type.strip().upper()
    if slot in _FLEX_ELIGIBILITY:
        return key in _FLEX_ELIGIBILITY[slot]
    return key == slot


def game_state(lock: dict[str, Any] | None, game_status: str | None, at_utc: datetime) -> str:
    """bye | completed | locked-active | unlocked | unknown for one player lock fact at ``at_utc``."""
    kind = None if lock is None else lock.get("Kind")
    if kind == "bye":
        return "bye"
    if kind != "scheduled":
        return "unknown"
    if not _blank(game_status) and re.match(r"^Final", str(game_status), re.IGNORECASE):
        return "completed"
    if _blank(lock.get("StartsAtUtc")):
        return "unknown"
    starts_at = datetime.strptime(utc_text(lock["StartsAtUtc"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return "locked-active" if starts_at <= at_utc.astimezone(UTC) else "unlocked"


def _valid_ids(values: Any) -> list[str]:
    seen: list[str] = []
    for value in values or []:
        state, player_id = _player_id(value)
        if state == "valid" and player_id not in seen:
            seen.append(player_id)
    return seen


def add_relevance(
    model: dict[str, Any],
    roster_positions: Any,
    rosters: list[dict[str, Any]],
    positions: dict[str, str | None],
    status_by_game: dict[str, str],
    at_utc: datetime,
) -> dict[str, Any]:
    """Port of Add-FantasyRelevanceDecisionFacts: slot states, player placements and team counts at ``at_utc``."""
    definitions = slot_definitions(roster_positions)
    lock_by_team_player = {(str(l["FantasyTeamID"]), l["PlayerID"]): l for l in model["PlayerLockFacts"]}
    teams: list[dict[str, Any]] = []
    for roster in sorted(rosters, key=lambda r: str(r["FantasyTeamID"]).lower()):
        team_id = str(roster["FantasyTeamID"])
        roster_ids = _valid_ids(roster.get("PlayerIDs"))
        starter_raw = list(roster.get("StarterSlots") if roster.get("StarterSlots") is not None else roster.get("StarterIDs") or [])
        starter_ids = _valid_ids(starter_raw)
        ir_ids = _valid_ids(roster.get("ReserveIDs"))
        taxi_ids = _valid_ids(roster.get("TaxiIDs"))
        for starter_id in starter_ids:
            if starter_id in ir_ids or starter_id in taxi_ids:
                raise DecisionWindowsError(f"Fantasy Relevance team '{team_id}' has starter '{starter_id}' outside Active Roster.")
        if len(starter_raw) > len(definitions):
            raise DecisionWindowsError(f"Fantasy Relevance team '{team_id}' has more starter entries than starting slots.")

        def lock_of(player_id: str | None) -> dict[str, Any] | None:
            return None if player_id is None else lock_by_team_player.get((team_id, player_id))

        slot_states: list[dict[str, Any]] = []
        slot_by_starter: dict[str, dict[str, Any]] = {}
        for index, definition in enumerate(definitions):
            starter_id = _player_id(starter_raw[index])[1] if index < len(starter_raw) else None
            lock = lock_of(starter_id)
            status = status_by_game.get(str(lock["GameID"])) if lock is not None and not _blank(lock.get("GameID")) else None
            state = "unlocked" if starter_id is None else game_state(lock, status, at_utc)
            slot = {
                **definition,
                "CurrentStarterID": starter_id,
                "State": state,
                "GameID": None if lock is None else lock.get("GameID"),
                "DecisionWindowID": None if lock is None else lock.get("DecisionWindowID"),
                "StartsAtUtc": None if lock is None else lock.get("StartsAtUtc"),
            }
            slot_states.append(slot)
            if starter_id is not None:
                slot_by_starter[starter_id] = slot

        bench_ids = [p for p in roster_ids if p not in starter_ids and p not in ir_ids and p not in taxi_ids]
        mutable = [s for s in slot_states if s["State"] == "unlocked"]
        players: list[dict[str, Any]] = []
        for player_id in roster_ids:
            placement = "starter" if player_id in starter_ids else "ir" if player_id in ir_ids else "taxi" if player_id in taxi_ids else "bench"
            position = positions.get(player_id)
            position = None if _blank(position) else str(position).strip().upper()
            lock = lock_of(player_id)
            status = status_by_game.get(str(lock["GameID"])) if lock is not None and not _blank(lock.get("GameID")) else None
            state = game_state(lock, status, at_utc)
            eligible: list[str] = []
            if placement == "bench" and state == "unlocked":
                for slot in mutable:
                    if slot_eligible(position, slot["SlotType"]) and slot["SlotID"] not in eligible:
                        eligible.append(slot["SlotID"])
            bench_candidate = placement == "bench" and len(eligible) > 0
            lineup_slot = slot_by_starter.get(player_id) if placement == "starter" else None
            players.append({
                "PlayerID": player_id,
                "Placement": placement,
                "Position": position,
                "GameState": state,
                "GameID": None if lock is None else lock.get("GameID"),
                "DecisionWindowID": None if lock is None else lock.get("DecisionWindowID"),
                "StartsAtUtc": None if lock is None else lock.get("StartsAtUtc"),
                "LineupSlotID": None if lineup_slot is None else lineup_slot["SlotID"],
                "LineupSlotType": None if lineup_slot is None else lineup_slot["SlotType"],
                "EligibleUnlockedSlotIDs": eligible,
                "IsBenchCandidate": bench_candidate,
                "HasDirectScoringPath": placement == "starter" and state in ("unlocked", "locked-active"),
                "HasAlternativePath": bench_candidate,
            })

        def starters_in(state: str) -> int:
            return sum(1 for p in players if p["Placement"] == "starter" and p["GameState"] == state)

        teams.append({
            "FantasyTeamID": team_id,
            "ActiveRosterPlayerCount": len(starter_ids) + len(bench_ids),
            "StarterCount": len(starter_ids),
            "BenchCount": len(bench_ids),
            "IRCount": len(ir_ids),
            "TaxiCount": len(taxi_ids),
            "UnlockedStarterCount": starters_in("unlocked"),
            "LockedActiveStarterCount": starters_in("locked-active"),
            "CompletedStarterCount": starters_in("completed"),
            "EligibleBenchCandidateCount": sum(1 for p in players if p["IsBenchCandidate"]),
            "HasRemainingScoringPath": any(p["HasDirectScoringPath"] or p["HasAlternativePath"] for p in players),
            "Slots": slot_states,
            "Players": sorted(players, key=lambda p: (p["Placement"].lower(), p["PlayerID"].lower())),
        })
    model["FantasyRelevance"] = {"Version": 1, "SlotDefinitions": definitions, "Teams": teams}
    model["SchemaVersion"] = max(2, int(model["SchemaVersion"]))
    return model


_AVAILABILITY_STATES = {"OUT": "out", "QUESTIONABLE": "uncertain", "DOUBTFUL": "uncertain", "ACTIVE": "available"}
AVAILABILITY_VERSION = 4


def _availability_state(provider_status: str | None) -> str:
    return _AVAILABILITY_STATES.get((provider_status or "").strip().upper(), "unknown")


def _utc_or_none(value: Any) -> str | None:
    if _blank(value):
        return None
    try:
        return utc_text(value)
    except DecisionWindowsError:
        return None


def scoring_availability_observations(
    season: int,
    rosters: list[dict[str, Any]],
    known_players: set[str],
    identities: list[dict[str, Any]],
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Port of Get-CanonicalScoringAvailabilityObservations for the starters of all teams.

    ``FirstObservedAtUtc`` (and its alias ``ObservedAtUtc``) is the snapshot's ``StatusSinceUtc``: the instant since when the
    provider status holds, so no earlier published file is read back (ADR-074 D2). A missing, unreadable or other-season snapshot,
    a missing row or an unknown status leaves the availability unknown; unavailability is never synthesized.
    """
    espn_by_sleeper: dict[str, str] = {}
    ambiguous_sleeper: set[str] = set()
    ambiguous_espn: set[str] = set()
    for identity in identities:
        ids = identity.get("IDs") if isinstance(identity, dict) else None
        if not isinstance(ids, dict):
            continue
        sleeper_state, sleeper_id = _player_id(ids.get("Sleeper"))
        espn_state, espn_id = _player_id(ids.get("ESPN"))
        if sleeper_id is None or espn_id is None:
            continue
        if sleeper_id in espn_by_sleeper and espn_by_sleeper[sleeper_id] != espn_id:
            ambiguous_sleeper.add(sleeper_id)
            continue
        if any(v == espn_id and k != sleeper_id for k, v in espn_by_sleeper.items()):
            ambiguous_espn.add(espn_id)
            continue
        espn_by_sleeper[sleeper_id] = espn_id
    for sleeper_id in ambiguous_sleeper:
        espn_by_sleeper.pop(sleeper_id, None)
    for espn_id in ambiguous_espn:
        for sleeper_id in [k for k, v in espn_by_sleeper.items() if v == espn_id]:
            del espn_by_sleeper[sleeper_id]

    target_by_espn: dict[str, str] = {}
    for roster in rosters:
        for raw in roster.get("StarterIDs") or []:
            starter_id = _player_id(raw)[1]
            if starter_id is None or starter_id not in known_players or starter_id not in espn_by_sleeper:
                continue
            target_by_espn[espn_by_sleeper[starter_id]] = starter_id
    if not target_by_espn or snapshot is None:
        return []
    try:
        if int(snapshot.get("Season")) != season:
            return []
    except (TypeError, ValueError):
        return []
    rows = {str(row.get("ESPNPlayerID") or "").strip(): row for row in snapshot.get("Players") or [] if isinstance(row, dict)}
    observations = []
    for espn_id in sorted(target_by_espn, key=str.lower):
        row = rows.get(espn_id)
        if row is None:
            continue
        status = str(row.get("ProviderStatus") or "").strip()
        since = _utc_or_none(row.get("StatusSinceUtc"))
        observations.append({
            "PlayerID": target_by_espn[espn_id],
            "ESPNPlayerID": espn_id,
            "State": _availability_state(status),
            "ProviderStatus": status.upper() if status else None,
            "Source": "ESPN",
            "FirstObservedAtUtc": since,
            "ObservedAtUtc": since,
        })
    return observations


def add_availability(model: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Port of Add-PlayerScoringAvailabilityDecisionFacts: per-slot and per-player availability and the OUT path rule."""
    relevance = model.get("FantasyRelevance")
    if relevance is None:
        return model
    by_player = {o["PlayerID"]: o for o in observations}
    for team in relevance["Teams"]:
        slot_by_starter = {}
        for slot in team["Slots"]:
            if slot["CurrentStarterID"] is not None:
                slot_by_starter[slot["CurrentStarterID"]] = slot
            slot["ScoringAvailability"] = None
        for player in team["Players"]:
            observation = by_player.get(player["PlayerID"])
            if observation is None:
                availability = {"State": "unknown", "ProviderStatus": None, "Source": "ESPN", "FirstObservedAtUtc": None, "ObservedAtUtc": None}
            else:
                availability = {key: observation[key] for key in ("State", "ProviderStatus", "Source", "FirstObservedAtUtc", "ObservedAtUtc")}
            player["ScoringAvailability"] = availability
            if player["PlayerID"] in slot_by_starter:
                slot_by_starter[player["PlayerID"]]["ScoringAvailability"] = availability
            if player["Placement"] == "starter" and availability["State"] == "out" and player["GameState"] != "completed":
                player["HasDirectScoringPath"] = False
        players = team["Players"]

        def counted(state: str) -> int:
            return sum(1 for p in players if p["Placement"] == "starter" and p["GameState"] == state and p["HasDirectScoringPath"])

        team["UnlockedStarterCount"] = counted("unlocked")
        team["LockedActiveStarterCount"] = counted("locked-active")
        team["HasRemainingScoringPath"] = any(p["HasDirectScoringPath"] or p["HasAlternativePath"] for p in players)
    model["ScoringAvailabilityObservations"] = list(observations)
    relevance["Version"] = max(AVAILABILITY_VERSION, int(relevance["Version"]))
    model["SchemaVersion"] = max(3, int(model["SchemaVersion"]))
    return model


def _repairability(problem_code: str, resolved: dict[str, Any]) -> dict[str, Any]:
    return {
        "ProblemCode": problem_code,
        "State": resolved["State"],
        "Path": resolved["Path"],
        "ReasonCode": resolved["ReasonCode"],
        "InternalCandidateCount": resolved["InternalCandidateCount"],
        "ExternalCandidateCount": resolved["ExternalCandidateCount"],
    }


def add_repairability(
    model: dict[str, Any],
    repairability_model: Any,
    rosters: list[dict[str, Any]],
    players: list[dict[str, Any]],
    games: list[dict[str, Any]],
    acquisition: dict[str, Any] | None,
    team_key: Callable[[Any], str | None],
    at_utc: datetime,
) -> dict[str, Any]:
    """Port of Add-LineupRepairabilityDecisionFacts: Repairability per problem slot using the model chosen in data-meta."""
    relevance = model.get("FantasyRelevance")
    if relevance is None or model.get("LineupWeek") is None:
        return model
    lineup_week = int(model["LineupWeek"])
    locks = {(str(l["FantasyTeamID"]).strip(), l["PlayerID"]): l for l in model["PlayerLockFacts"]}
    evaluations = {str(e["FantasyTeamID"]).strip(): e for e in model["TeamLineupEvaluations"]}
    owned = {p for roster in rosters for p in _valid_ids(roster.get("PlayerIDs"))}
    eligible = slot_eligible
    unknown = {"State": "unknown", "Path": None, "ReasonCode": "LINEUP_EVIDENCE_UNKNOWN", "InternalCandidateCount": 0, "ExternalCandidateCount": 0}
    locked_unavailable = {"State": "irreparable", "Path": None, "ReasonCode": "NO_LEGAL_REPAIR_PATH", "InternalCandidateCount": 0, "ExternalCandidateCount": 0}

    def kind_of(team_id: str, player_id: str) -> str:
        lock = locks.get((team_id, player_id))
        return "unknown" if lock is None else str(lock.get("Kind") or "")

    for team_state in relevance["Teams"]:
        team_id = str(team_state["FantasyTeamID"]).strip()
        if not team_id:
            continue
        slots = team_state["Slots"]
        for slot in slots:
            slot["Repairability"] = None

        problems: dict[str, str] = {}
        for slot in slots:
            slot_id = str(slot["SlotID"])
            if not slot_id.strip():
                continue
            starter_id = _player_id(slot["CurrentStarterID"])[1]
            if starter_id is None:
                problems[slot_id] = "OPEN_STARTER_SLOT"
                continue
            if (slot.get("ScoringAvailability") or {}).get("State") == "out":
                problems[slot_id] = "STARTER_UNAVAILABLE"
                continue
            if kind_of(team_id, starter_id) == "bye":
                problems[slot_id] = "STARTER_ON_BYE"
        if not problems:
            continue

        evaluation = evaluations.get(team_id)
        evaluation_state = "unknown" if evaluation is None else str(evaluation.get("State") or "")
        if evaluation_state in ("unknown", "review"):
            for slot in slots:
                slot_id = str(slot["SlotID"])
                if slot_id in problems:
                    fixed = problems[slot_id] == "STARTER_UNAVAILABLE" and slot["State"] in ("locked-active", "completed")
                    slot["Repairability"] = _repairability(problems[slot_id], locked_unavailable if fixed else unknown)
            continue

        mutable_slots: list[dict[str, Any]] = []
        mutable_ids: set[str] = set()
        for slot in slots:
            slot_id = str(slot["SlotID"])
            starter_id = _player_id(slot["CurrentStarterID"])[1]
            mutable = starter_id is None
            if not mutable:
                mutable = (
                    kind_of(team_id, starter_id) == "bye"
                    or slot["State"] == "unlocked"
                    or (problems.get(slot_id) == "STARTER_UNAVAILABLE" and slot["State"] not in ("locked-active", "completed"))
                )
            if mutable:
                mutable_slots.append(slot)
                mutable_ids.add(slot_id)

        internal: list[dict[str, Any]] = []
        internal_unknown = False
        for player in team_state["Players"]:
            if player["Placement"] not in ("starter", "bench"):
                continue
            player_id = _player_id(player["PlayerID"])[1]
            if player_id is None:
                continue
            if player["Placement"] == "starter":
                lineup_slot = str(player.get("LineupSlotID") or "")
                if not lineup_slot.strip() or lineup_slot not in mutable_ids:
                    continue
            position = "" if _blank(player.get("Position")) else str(player["Position"]).strip().upper()
            if (player.get("ScoringAvailability") or {}).get("State") == "out":
                continue
            kind = kind_of(team_id, player_id)
            relevant = bool(position) and any(eligible(position, str(slot["SlotType"])) for slot in mutable_slots)
            if kind == "scheduled" and player["GameState"] == "unlocked":
                if not position:
                    internal_unknown = True
                elif relevant:
                    internal.append({"PlayerID": player_id, "Position": position})
            elif kind == "unknown" and (not position or relevant):
                internal_unknown = True

        external = repairability_model.external_evidence(
            players, owned, games, mutable_slots, acquisition, lineup_week, at_utc, team_key, eligible
        )
        resolved = repairability_model.resolve_state(
            mutable_slots, internal, external["Candidates"], internal_unknown,
            external["State"], bool(external["PlayerEvidenceUnknown"]), eligible,
        )
        for slot in slots:
            slot_id = str(slot["SlotID"])
            if slot_id in problems:
                fixed = problems[slot_id] == "STARTER_UNAVAILABLE" and slot["State"] in ("locked-active", "completed")
                slot["Repairability"] = _repairability(problems[slot_id], locked_unavailable if fixed else resolved)
    relevance["Version"] = max(2, int(relevance["Version"]))
    return model


def remaining_scoring_path_state(team_state: dict[str, Any], evaluation: dict[str, Any] | None) -> str:
    """open | unknown | none: whether the team can still score through a starter, a bench candidate or a repair."""
    has_path = team_state.get("HasRemainingScoringPath")
    slots = team_state.get("Slots") or []

    def repairability_state(slot: dict[str, Any]) -> str | None:
        repairability = slot.get("Repairability")
        return None if not isinstance(repairability, dict) else repairability.get("State")

    if has_path is True or any(repairability_state(slot) == "repairable" for slot in slots):
        return "open"
    if has_path is None:
        return "unknown"
    if evaluation is None or evaluation.get("State") in ("unknown", "review"):
        return "unknown"
    for slot in slots:
        if slot.get("State") == "unknown" or repairability_state(slot) == "unknown":
            return "unknown"
    return "none"


def add_scoring_path(model: dict[str, Any]) -> dict[str, Any]:
    """Port of Add-ParticipantScoringPathDecisionFacts: RemainingScoringPathState per team (runs after availability and repairability)."""
    relevance = model.get("FantasyRelevance")
    if relevance is None:
        return model
    evaluations = {str(e["FantasyTeamID"]).strip(): e for e in model["TeamLineupEvaluations"] if e is not None}
    for team_state in relevance["Teams"]:
        team_state["RemainingScoringPathState"] = remaining_scoring_path_state(team_state, evaluations.get(str(team_state["FantasyTeamID"]).strip()))
    relevance["Version"] = max(RELEVANCE_VERSION, int(relevance["Version"]))
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Input adapters (canonical facts -> derivation inputs)

_WEEK_LABEL = re.compile(r"^Week\s+(\d+)$")


def schedule_games(records: list[dict[str, Any]], season: str, lineup_week: int, last_lineup_week: int) -> list[dict[str, Any]]:
    """Port of the schedule adapter of New-CurrentLeagueDecisionWindowsReadModel (App schedule records -> games)."""
    required: set[int] = set()
    if lineup_week < 1:
        required.add(1)
    elif lineup_week <= last_lineup_week:
        required.add(lineup_week)
        if lineup_week < last_lineup_week:
            required.add(lineup_week + 1)

    games: list[dict[str, Any]] = []
    for record in records:
        if record is None:
            continue
        if not _blank(record.get("season")) and str(record["season"]) != season:
            continue
        match = _WEEK_LABEL.match(str(record.get("gameWeek") or ""))
        if not match:
            continue
        week = int(match.group(1))
        game_id = str(record.get("gameID") or "")
        if not game_id.strip():
            raise DecisionWindowsError("Current Decision Window schedule adapter found a regular-season game without gameID.")
        if _blank(record.get("teamIDHome")) or _blank(record.get("teamIDAway")):
            raise DecisionWindowsError(f"Current Decision Window schedule adapter found game '{game_id}' without stable team IDs.")
        is_required = week in required
        if _blank(record.get("gameTime_epoch")):
            if is_required:
                raise DecisionWindowsError(f"Current Decision Window schedule adapter found game '{game_id}' without gameTime_epoch.")
            continue
        try:
            starts = datetime.fromtimestamp(int(float(str(record["gameTime_epoch"]))), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError, OSError) as exc:
            if is_required:
                raise DecisionWindowsError(f"Current Decision Window schedule adapter could not parse gameTime_epoch for '{game_id}'.") from exc
            continue
        games.append({
            "GameID": game_id,
            "Week": week,
            "StartsAtUtc": starts,
            "AwayTeamID": str(record["teamIDAway"]),
            "AwayTeamAbbr": None if _blank(record.get("away")) else str(record["away"]),
            "HomeTeamID": str(record["teamIDHome"]),
            "HomeTeamAbbr": None if _blank(record.get("home")) else str(record["home"]),
        })
    return games


def expected_starter_count(roster_positions: Any) -> int:
    """Non-bench roster positions; fail closed without a positive count."""
    if roster_positions is None:
        raise DecisionWindowsError("Current Decision Window adapter requires league roster_positions.")
    count = sum(1 for p in roster_positions if not _blank(p) and str(p).strip().upper() != "BN")
    if count <= 0:
        raise DecisionWindowsError("Current Decision Window adapter could not derive a positive expected starter count from roster_positions.")
    return count


def _sleeper_mapping(mappings: Any, label: str, field: str) -> str:
    found = [m for m in (mappings or []) if str(m.get("Provider", "")).lower() == "sleeper"]
    if len(found) != 1 or _blank(found[0].get(field)):
        raise DecisionWindowsError(f"{label} needs exactly one Sleeper mapping with {field}.")
    return str(found[0][field])


def _read(path: Path, what: str) -> Any:
    if not path.is_file():
        raise DecisionWindowsError(f"{what} missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise DecisionWindowsError(f"{what} is not valid JSON: {path}: {exc}") from exc


def rosters_from_canonical(rosters: Any, label: str) -> list[dict[str, Any]]:
    """Canonical rosters.json -> fantasy rosters keyed by the provider roster ID (the App TeamID), ordered by it."""
    if not isinstance(rosters, list):
        raise DecisionWindowsError(f"{label} rosters are not a list.")

    def provider_ids(players: Any, roster_label: str) -> list[str]:
        ids = []
        for index, player in enumerate(players or []):
            if not isinstance(player, dict) or _blank(player.get("CanonicalPlayerID")):
                raise DecisionWindowsError(f"{roster_label} contains a player reference without CanonicalPlayerID at index {index}.")
            ids.append(_sleeper_mapping(player.get("ProviderMappings"), f"{roster_label} player '{player['CanonicalPlayerID']}'", "ProviderPlayerID"))
        return ids

    result = []
    for roster in rosters:
        roster_label = f"{label} roster '{roster.get('CanonicalLeagueRosterID')}'"
        team_id = int(_sleeper_mapping(roster.get("ProviderMappings"), roster_label, "ProviderRosterID"))
        result.append({
            "FantasyTeamID": team_id,
            "PlayerIDs": provider_ids(roster.get("Players"), roster_label),
            "StarterIDs": provider_ids(roster.get("Starters"), roster_label),
            "ReserveIDs": provider_ids(roster.get("Reserve"), roster_label),
            "TaxiIDs": provider_ids(roster.get("Taxi"), roster_label),
        })
    result.sort(key=lambda r: r["FantasyTeamID"])
    return result


def _epoch_utc(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(float(str(value))), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError, OSError):
        return None


def _ordered_starter_slots(repo_root: Path, provider_league_id: str, rosters: list[dict[str, Any]]) -> None:
    """Attach ``StarterSlots`` (lineup order, None for an unfilled slot) from the raw Sleeper roster evidence.

    The canonical rosters drop Sleeper's "0" placeholders and with them the slot positions, which the lineup order needs. The raw
    provider snapshot under data-source keeps them; it is cross-checked against the canonical starters and never replaces them.
    """
    path = repo_root / DATA_SOURCE_ROOT / "providers" / "sleeper" / "leagues" / provider_league_id / "rosters.json"
    raw = _read(path, "Raw Sleeper rosters")
    if not isinstance(raw, list):
        raise DecisionWindowsError(f"Raw Sleeper rosters are not a list: {path}")
    by_roster = {str(item.get("roster_id")): item for item in raw if isinstance(item, dict)}
    for roster in rosters:
        item = by_roster.get(str(roster["FantasyTeamID"]))
        if item is None:
            raise DecisionWindowsError(f"Raw Sleeper rosters lack roster {roster['FantasyTeamID']}: {path}")
        slots = [_player_id(value)[1] for value in item.get("starters") or []]
        if sorted(p for p in slots if p is not None) != sorted(roster["StarterIDs"]):
            raise DecisionWindowsError(f"Raw Sleeper starters of roster {roster['FantasyTeamID']} contradict the canonical rosters.")
        roster["StarterSlots"] = slots


def _inputs(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    if at_utc.tzinfo is None:
        raise DecisionWindowsError("AtUtc must be timezone-aware")
    from players_population import PopulationError, build_population  # local: heavy import, only the resolver needs it

    try:
        lifecycle = resolve_lifecycle(repo_root, league_id, season, at_utc)
    except LifecycleError as exc:
        raise DecisionWindowsError(str(exc)) from exc
    base = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    league = _read(base / "league.json", "Canonical league source")
    provider_league_id = _sleeper_mapping(league.get("ProviderMappings"), f"Canonical league '{league_id}/{season}'", "ProviderLeagueID")
    if lifecycle["LineupWeek"] is None:
        raise DecisionWindowsError("Current Decision Window adapter requires fantasy-platform settings.leg.")
    rosters = rosters_from_canonical(_read(base / "rosters.json", "Canonical rosters"), f"Canonical league '{league_id}/{season}'")
    _ordered_starter_slots(repo_root, provider_league_id, rosters)

    try:
        records = build_schedule(repo_root, season, {"REG"})
        population = build_population(repo_root, league_id, season)
    except (ScheduleArchiveError, PopulationError, OSError, KeyError) as exc:
        raise DecisionWindowsError(f"Decision Window input unusable: {exc}") from exc
    identities = _read(repo_root / DATA_SOURCE_ROOT / "nfl" / "identities" / "players.json", "Canonical player identities").get("Players")
    snapshot_path = repo_root / DATA_SOURCE_ROOT / "nfl" / "player-availability" / "espn.json"
    try:
        availability_snapshot = _read(snapshot_path, "Canonical player-availability snapshot") if snapshot_path.is_file() else None
    except DecisionWindowsError:
        availability_snapshot = None  # unreadable snapshot: availability stays unknown
    try:
        repairability_model = get_model(model_for(load_league_metadata(league_id, data_meta_root(repo_root)), season, "Repairability"), "repairability")
    except (LeagueMetadataError, UnknownModelError) as exc:
        raise DecisionWindowsError(str(exc)) from exc
    acquisition = repairability_model.resolve_acquisition(bool(lifecycle["WaiversOpen"]), lifecycle["NextWaiverRun"])
    games = []
    for record in records:
        match = _WEEK_LABEL.match(str(record.get("gameWeek") or ""))
        if not match:
            continue
        games.append({
            "Week": int(match.group(1)),
            "HomeTeamID": record.get("teamIDHome"),
            "AwayTeamID": record.get("teamIDAway"),
            "StartsAtUtc": None if _blank(record.get("gameTime_epoch")) else _epoch_utc(record["gameTime_epoch"]),
            "Status": str(record.get("gameStatus") or ""),
        })
    return {
        "repairability_model": repairability_model,
        "acquisition": acquisition,
        "games": games,
        "players": [{"PlayerID": p["SleeperID"], "Position": p.get("Position"), "TeamID": p["TeamID"]} for p in population["Players"]],
        "identities": identities if isinstance(identities, list) else [],
        "availability_snapshot": availability_snapshot,
        "provider_league_id": provider_league_id,
        "lineup_week": int(lifecycle["LineupWeek"]),
        "last_week": int(lifecycle["LastLeagueWeek"]),
        "roster_positions": league.get("RosterPositions"),
        "rosters": rosters,
        "records": records,
        "positions": {p["SleeperID"]: p.get("Position") for p in population["Players"]},
        "assignments": [{"PlayerID": p["SleeperID"], "NFLTeamID": p["TeamID"]} for p in population["Players"]],
        "team_key": make_team_key(NflTeamRegistry.load(repo_root)),
    }


def _base_from_inputs(inputs: dict[str, Any], season: int) -> dict[str, Any]:
    return build_base_model(
        inputs["provider_league_id"],
        str(season),
        inputs["lineup_week"],
        inputs["last_week"],
        schedule_games(inputs["records"], str(season), inputs["lineup_week"], inputs["last_week"]),
        inputs["rosters"],
        inputs["assignments"],
        expected_starter_count(inputs["roster_positions"]),
        inputs["team_key"],
    )


def resolve_base(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """Base Decision Windows (windows, locks, lineup evaluations, lookahead) at ``at_utc``; computed, never persisted."""
    return _base_from_inputs(_inputs(repo_root, league_id, season, at_utc), season)


def resolve(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """Decision Windows with Fantasy Relevance and the scoring path at ``at_utc`` plus ``AsOfUtc``; computed, never persisted."""
    model = _resolve_model(repo_root, league_id, season, at_utc)
    model["AsOfUtc"] = utc_text(at_utc)
    return model


def _resolve_model(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    inputs = _inputs(repo_root, league_id, season, at_utc)
    model = _base_from_inputs(inputs, season)
    if inputs["lineup_week"] < 1 or inputs["lineup_week"] > inputs["last_week"]:
        return model
    status_by_game = {str(r["gameID"]): str(r.get("gameStatus") or "") for r in inputs["records"] if r.get("gameID")}
    add_relevance(model, inputs["roster_positions"], inputs["rosters"], inputs["positions"], status_by_game, at_utc)
    observations = scoring_availability_observations(
        season, inputs["rosters"], set(inputs["positions"]), inputs["identities"], inputs["availability_snapshot"]
    )
    add_availability(model, observations)
    add_repairability(
        model, inputs["repairability_model"], inputs["rosters"], inputs["players"], inputs["games"], inputs["acquisition"],
        inputs["team_key"], at_utc,
    )
    return add_scoring_path(model)


__all__ = [
    "DecisionWindowsError", "add_availability", "add_relevance", "add_repairability", "add_scoring_path", "scoring_availability_observations", "build_base_model", "game_state", "remaining_scoring_path_state",
    "slot_definitions", "slot_eligible", "derive_facts", "expected_starter_count", "make_team_key", "parse_instant",
    "resolve", "resolve_base", "rosters_from_canonical", "schedule_games", "utc_text",
]
