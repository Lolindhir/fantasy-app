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
from nfl_source_data_lib.teams import NflTeamRegistry, NflTeamRegistryError
from schedule_archive import ScheduleArchiveError, build_schedule

from .league_lifecycle import LifecycleError, parse_instant, resolve_lifecycle

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
        })
    result.sort(key=lambda r: r["FantasyTeamID"])
    return result


def resolve_base(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """Base Decision Windows (windows, locks, lineup evaluations, lookahead) at ``at_utc``; computed, never persisted."""
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
    lineup_week = int(lifecycle["LineupWeek"])
    last_week = int(lifecycle["LastLeagueWeek"])
    starters = expected_starter_count(league.get("RosterPositions"))
    rosters = rosters_from_canonical(_read(base / "rosters.json", "Canonical rosters"), f"Canonical league '{league_id}/{season}'")

    try:
        records = build_schedule(repo_root, season, {"REG"})
        population = build_population(repo_root, league_id, season)
    except (ScheduleArchiveError, PopulationError, OSError, KeyError) as exc:
        raise DecisionWindowsError(f"Decision Window input unusable: {exc}") from exc
    assignments = [{"PlayerID": p["SleeperID"], "NFLTeamID": p["TeamID"]} for p in population["Players"]]

    return build_base_model(
        provider_league_id,
        str(season),
        lineup_week,
        last_week,
        schedule_games(records, str(season), lineup_week, last_week),
        rosters,
        assignments,
        starters,
        make_team_key(NflTeamRegistry.load(repo_root)),
    )


__all__ = [
    "DecisionWindowsError", "build_base_model", "derive_facts", "expected_starter_count", "make_team_key", "parse_instant",
    "resolve_base", "rosters_from_canonical", "schedule_games", "utc_text",
]
