"""Matchup context for one league, season and instant (ADR-075, Issue #1199 section 3).

Pure-function port of ``MatchupReadModelCore.ps1``: the season ``Matchups`` read model (pairings in neutral order, effective
scores, the per-matchup ``CompletionState``, results, stage, first kickoff and ``Summary``). The core
(``build_matchups_model``) reads the canonical inputs below ``repo_root`` (league source, matchup weeks, NFL schedule, game
finality, weekly rosters) and takes the neutral team order, the Decision Windows facts of the active week and the instant as
explicit arguments. ``public/data`` is never an input. Nothing is persisted; the instant is an explicit input.

``CompletionState`` (open | final | unknown per matchup) is not "week final" (ADR-071); see ``matchup-context.yaml``.
Later steps add the FantasyGameContext, the history, the projections and the resolver on top of this model.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT

UTC = timezone.utc
EASTERN = ZoneInfo("America/New_York")
NON_STARTER_POSITIONS = ("BN", "IR", "TAXI", "RESERVE")


class MatchupContextError(ValueError):
    """Missing or contradicting matchup input (fail closed)."""


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers (semantics of the PowerShell Get-MrmValue / Get-MrmCollection)


def value_of(obj: Any, *names: str) -> Any:
    """Value of the first name that is present on ``obj`` (even when it is null); None when none is present."""
    if not isinstance(obj, dict):
        return None
    for name in names:
        if name in obj:
            return obj[name]
    return None


def collection(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
        return [value]
    return list(value)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def to_int(value: Any) -> int:
    """PowerShell ``[int]$value``: null is 0, numeric text and numbers convert, anything else fails."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    try:
        return int(float(str(value))) if not isinstance(value, int) else value
    except ValueError as exc:
        raise MatchupContextError(f"Cannot convert '{value}' to an integer.") from exc


def _read(path: Path, what: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise MatchupContextError(f"{what} not found at {path}.") from exc
    if not text.strip():
        raise MatchupContextError(f"{what} is empty at {path}.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise MatchupContextError(f"{what} at {path} is not valid JSON: {exc}") from exc


def parse_instant_text(text: str) -> datetime:
    moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------------------------------------------------
# Identity and ordering


def fantasy_matchup_id(season: str, week: int, team_ids: list[Any]) -> str:
    """``fgm-`` plus the first 24 hex digits of SHA-256 over ``season|week|team|team`` (New-FantasyGameContextMatchupID)."""
    teams = sorted(str(t).strip() for t in team_ids)
    if len(teams) != 2 or any(t == "" for t in teams):
        raise MatchupContextError("Fantasy matchup identity requires exactly two stable fantasy team IDs.")
    material = f"{season}|{week}|{'|'.join(teams)}"
    return "fgm-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def neutral_order_index(all_time_overall: Iterable[dict[str, Any]]) -> dict[str, int]:
    """TeamID (text) to position in the All-Time Overall order, lowest place first (Get-FantasyTeamNeutralOrderIndex)."""
    entries: list[tuple[str, int]] = []
    seen: set[str] = set()
    by_place: dict[int, str] = {}
    for standing in all_time_overall:
        team_id = _text(value_of(standing, "TeamID")).strip()
        if team_id == "":
            raise MatchupContextError("All-Time Overall neutral order contains a standing without TeamID.")
        try:
            place = int(str(value_of(standing, "Place")))
        except ValueError:
            place = 0
        if place <= 0 or place >= 999:
            raise MatchupContextError(f"Fantasy team '{team_id}' has no resolved All-Time Overall place for neutral ordering.")
        if team_id in seen:
            raise MatchupContextError(f"Duplicate fantasy TeamID '{team_id}' in All-Time Overall neutral order.")
        if place in by_place:
            raise MatchupContextError(
                f"All-Time Overall neutral order is not fully resolved: place {place} is shared by teams {by_place[place]} and {team_id}."
            )
        seen.add(team_id)
        by_place[place] = team_id
        entries.append((team_id, place))
    if not entries:
        raise MatchupContextError("All-Time Overall neutral order is empty.")
    return {team_id: position for position, (team_id, _) in enumerate(sorted(entries, key=lambda entry: entry[1]))}


def participant_order_from_standings(product: dict[str, Any]) -> dict[str, int]:
    """Neutral order of the league-standings product of the season (AllTime through that season, Overall)."""
    playoffs = collection(value_of(value_of(product, "AllTime"), "Playoffs"))
    if not playoffs:
        raise MatchupContextError(f"Matchups {value_of(product, 'Season')} cannot resolve the All-Time Overall Standings order.")
    return neutral_order_index(playoffs)


# ---------------------------------------------------------------------------------------------------------------------
# Canonical matchup rows


def sleeper_mapping(row: Any) -> dict[str, Any] | None:
    for mapping in collection(value_of(row, "ProviderMappings")):
        if _text(value_of(mapping, "Provider")) == "Sleeper":
            return mapping
    return None


def row_team_id(row: Any) -> int | str | None:
    mapping = sleeper_mapping(row)
    value = value_of(mapping, "ProviderRosterID") if mapping is not None else value_of(row, "roster_id", "RosterID", "TeamID", "FantasyTeamID")
    if _blank(value):
        return None
    try:
        return int(str(value))
    except ValueError:
        return str(value)


def provider_matchup_id(row: Any) -> str | None:
    mapping = sleeper_mapping(row)
    if mapping is not None:
        value = value_of(mapping, "ProviderMatchupID")
        if value is not None:
            return str(value)
    value = value_of(row, "matchup_id", "MatchupID")
    return None if value is None else str(value)


def effective_score(row: Any) -> dict[str, Any]:
    custom = value_of(row, "custom_points", "CustomPoints")
    if custom is not None and not _blank(custom):
        return {"Points": float(custom), "ScoreKind": "adjusted"}
    points = value_of(row, "points", "Points")
    if points is None or _blank(points):
        return {"Points": None, "ScoreKind": "standard"}
    return {"Points": float(points), "ScoreKind": "standard"}


def _live_row_map(rows: list[Any]) -> tuple[dict[str, Any], set[str]]:
    mapping: dict[str, Any] = {}
    conflicts: set[str] = set()
    for row in rows:
        team_id = row_team_id(row)
        if team_id is None:
            continue
        key = str(team_id)
        if key in mapping:
            conflicts.add(key)
            continue
        mapping[key] = row
    return mapping, conflicts


def canonical_pairings(
    season: int, week: int, rows: list[Any], participant_order: dict[str, int], live_rows: list[Any] | None = None
) -> tuple[list[dict[str, Any]], bool]:
    """Pairings of one week sorted by FantasyMatchupID and whether malformed pairing evidence was found."""
    live, live_conflicts = _live_row_map(live_rows or [])
    malformed = False
    groups: dict[str, list[Any]] = {}
    for row in rows:
        canonical_id = _text(value_of(row, "CanonicalLeagueMatchupID"))
        provider_id = provider_matchup_id(row)
        if not _blank(canonical_id):
            group_key = f"canonical:{canonical_id}"
        elif not _blank(provider_id):
            group_key = f"provider:{provider_id}"
        else:
            malformed = True
            continue
        groups.setdefault(group_key, []).append(row)

    result: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        participants: list[dict[str, Any]] = []
        score_unknown = False
        seen: set[str] = set()
        for row in groups[group_key]:
            team_id = row_team_id(row)
            if team_id is None:
                score_unknown = True
                continue
            team_key = str(team_id)
            if team_key in seen:
                score_unknown = True
                continue
            seen.add(team_key)
            if team_key not in participant_order:
                raise MatchupContextError(f"Matchups {season} Week {week} cannot order TeamID {team_key} from All-Time Overall Standings.")
            score_row = row
            if team_key in live_conflicts:
                score_unknown = True
            elif team_key in live:
                live_row = live[team_key]
                canonical_provider = provider_matchup_id(row)
                live_provider = provider_matchup_id(live_row)
                if not _blank(canonical_provider) and not _blank(live_provider) and canonical_provider != live_provider:
                    score_unknown = True
                else:
                    score_row = live_row
            score = effective_score(score_row)
            participants.append(
                {
                    "TeamID": team_id,
                    "Points": score["Points"],
                    "ScoreKind": score["ScoreKind"],
                    "Order": participant_order[team_key],
                    "SourceRow": row,
                }
            )
        if len(participants) != 2:
            malformed = True
            continue
        participants.sort(key=lambda p: p["Order"])
        result.append(
            {
                "FantasyMatchupID": fantasy_matchup_id(str(season), week, [p["TeamID"] for p in participants]),
                "Participants": participants,
                "ScoreEvidenceUnknown": score_unknown,
            }
        )
    result.sort(key=lambda p: p["FantasyMatchupID"])
    return result, malformed


def current_matchup_rows(repo_root: Path, league_id: str, season: int, week: int) -> list[dict[str, Any]]:
    """Strictly validated current-week rows in the legacy Sleeper shape (Get-CanonicalCurrentMatchupRows); raises on any defect."""
    if season < 1 or week < 1:
        raise MatchupContextError("Canonical current matchup Season and Week must be positive.")
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "matchups" / f"week-{week}.json"
    payload = _read(path, f"Canonical current matchup source for {league_id}/{season} Week {week}")
    rows = payload if isinstance(payload, list) else [payload]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        legacy = _legacy_row(row, week)
        key = str(legacy["roster_id"])
        if key in seen:
            raise MatchupContextError(f"Canonical current matchup source contains duplicate Sleeper roster_id '{key}'.")
        seen.add(key)
        result.append(legacy)
    return sorted(result, key=lambda r: int(r["roster_id"]))


def _sleeper_mapping_strict(mappings: Any, label: str) -> dict[str, Any]:
    found = [m for m in collection(mappings) if _text(value_of(m, "Provider")) == "Sleeper"]
    if len(found) != 1:
        raise MatchupContextError(f"{label} must contain exactly one Sleeper provider mapping; found {len(found)}.")
    return found[0]


def _provider_player_id(player_ref: Any, label: str) -> str:
    if player_ref is None:
        raise MatchupContextError(f"{label} is missing a player reference.")
    mapping = _sleeper_mapping_strict(value_of(player_ref, "ProviderMappings"), label)
    player_id = _text(value_of(mapping, "ProviderPlayerID"))
    if player_id.strip() == "":
        raise MatchupContextError(f"{label} Sleeper mapping is missing ProviderPlayerID.")
    return player_id.strip()


def _point_map(entries: Any, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for entry in collection(entries):
        if entry is None:
            continue
        player_id = _provider_player_id(value_of(entry, "Player"), f"{label}.Player")
        if player_id in result:
            raise MatchupContextError(f"{label} contains duplicate Sleeper PlayerID '{player_id}'.")
        result[player_id] = value_of(entry, "Points")
    return result


def _legacy_row(row: Any, week: int) -> dict[str, Any]:
    row_week = to_int(value_of(row, "Week"))
    if row_week != week:
        raise MatchupContextError(f"Canonical matchup row Week '{row_week}' does not match requested Week '{week}'.")
    mapping = _sleeper_mapping_strict(value_of(row, "ProviderMappings"), f"Canonical matchup Week {week}")
    roster_text = _text(value_of(mapping, "ProviderRosterID"))
    try:
        roster_id = int(roster_text)
    except ValueError:
        roster_id = 0
    if roster_id < 1:
        raise MatchupContextError(f"Canonical matchup Week {week} has invalid Sleeper ProviderRosterID '{roster_text}'.")
    matchup_value = value_of(mapping, "ProviderMatchupID")
    matchup_id = None
    if matchup_value is not None and not _blank(matchup_value):
        try:
            matchup_id = int(str(matchup_value))
        except ValueError:
            matchup_id = 0
        if matchup_id < 1:
            raise MatchupContextError(f"Canonical matchup Week {week} roster {roster_id} has invalid Sleeper ProviderMatchupID '{matchup_value}'.")
    label = f"Canonical matchup Week {week} roster {roster_id}"
    players = [_provider_player_id(p, f"{label} Players") for p in collection(value_of(row, "Players"))]
    if len(set(players)) != len(players):
        raise MatchupContextError(f"{label} contains duplicate Players.")
    starters = [_provider_player_id(p, f"{label} Starters") for p in collection(value_of(row, "Starters"))]
    if len(set(starters)) != len(starters):
        raise MatchupContextError(f"{label} contains duplicate Starters.")
    for starter_id in starters:
        if starter_id not in players:
            raise MatchupContextError(f"{label} starter '{starter_id}' is outside Players.")
    player_points = _point_map(value_of(row, "PlayerPoints"), f"{label} PlayerPoints")
    starter_points_map = _point_map(value_of(row, "StarterPoints"), f"{label} StarterPoints")
    starter_points = []
    for starter_id in starters:
        if starter_id in starter_points_map:
            starter_points.append(starter_points_map[starter_id])
        elif starter_id in player_points:
            starter_points.append(player_points[starter_id])
        else:
            raise MatchupContextError(f"{label} has no score evidence for starter '{starter_id}'.")
    return {
        "custom_points": value_of(row, "CustomPoints"),
        "matchup_id": matchup_id,
        "players": players,
        "players_points": player_points,
        "points": value_of(row, "Points"),
        "roster_id": roster_id,
        "starters": starters,
        "starters_points": starter_points,
    }


# ---------------------------------------------------------------------------------------------------------------------
# NFL schedule, finality and weekly roster evidence


def kickoff_utc(game: Any) -> str | None:
    """Eastern wall-clock GameDay/GameTime of a canonical schedule game as ``yyyy-MM-ddTHH:mm:ssZ``."""
    day = _text(value_of(game, "GameDay"))
    time = _text(value_of(game, "GameTime"))
    if day.strip() == "" or time.strip() == "":
        return None
    try:
        parsed = datetime.strptime(f"{day} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=EASTERN).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def schedule_games(repo_root: Path, season: int) -> list[dict[str, Any]]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json"
    if not path.is_file():
        raise MatchupContextError(f"Canonical NFL schedule not found for Matchups {season} at {path}.")
    document = _read(path, "Canonical NFL schedule")
    return [g for g in collection(value_of(document, "Games")) if _blank(value_of(g, "GameType")) or _text(value_of(g, "GameType")) == "REG"]


def finality_map(repo_root: Path, season: int) -> dict[str, Any] | None:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "game-finality" / f"{season}.json"
    if not path.is_file():
        return None
    result: dict[str, Any] = {}
    for game in collection(value_of(_read(path, "Canonical NFL game finality"), "Games")):
        game_id = _text(value_of(game, "GameID"))
        if game_id.strip() == "":
            continue
        if game_id in result:
            raise MatchupContextError(f"Duplicate canonical NFL finality GameID '{game_id}' for season {season}.")
        result[game_id] = value_of(game, "Final")
    return result


def canonical_player_id(player: Any) -> str | None:
    if not isinstance(player, dict):
        return None
    value = value_of(player, "CanonicalPlayerID")
    return None if _blank(value) else str(value).strip()


def _row_team_abbr(team_ref: Any, direct: Any) -> Any:
    """Team abbreviation of a roster record or nested player (the order of the PowerShell fallbacks)."""
    abbr = direct
    if _blank(abbr) and isinstance(team_ref, str):
        abbr = team_ref
    elif team_ref is not None and not isinstance(team_ref, str):
        abbr = value_of(team_ref, "TeamAbbr", "TeamAbv", "Abbr")
    return abbr


def weekly_assignment_map(repo_root: Path, season: int, week: int) -> dict[str, list[str]] | None:
    """CanonicalPlayerID to the sorted NFL team abbreviations of the player in that week (None when the roster is missing)."""
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "weekly-rosters" / str(season) / f"{week:02d}.json"
    if not path.is_file():
        return None
    document = _read(path, "Canonical weekly roster")
    records = value_of(document, "Records", "Rows", "Rosters", "Players", "Data")
    if records is not None:
        rows = collection(records)
    elif isinstance(document, list):
        rows = list(document)
    else:
        rows = []
    assignments: dict[str, list[str]] = {}
    for row in rows:
        player_ref = value_of(row, "Player")
        player = player_ref if player_ref is not None else row
        canonical_id = canonical_player_id(player)
        if canonical_id is None:
            continue
        abbr = _row_team_abbr(value_of(row, "Team"), value_of(row, "TeamAbbr", "TeamAbv"))
        if _blank(abbr) and player_ref is not None:
            abbr = _row_team_abbr(value_of(player_ref, "Team"), value_of(player_ref, "TeamAbbr", "TeamAbv"))
        if _blank(abbr):
            continue
        assignments.setdefault(canonical_id, []).append(str(abbr).strip().upper())
    return {key: sorted(set(teams)) for key, teams in assignments.items()}


# ---------------------------------------------------------------------------------------------------------------------
# CompletionState


def starter_game_resolution(
    starter: Any, week_games: list[dict[str, Any]], assignments: dict[str, list[str]] | None, finality: dict[str, Any] | None
) -> str:
    """open | final | unknown for the single NFL game of one starter (Get-MrmStarterGameResolution)."""
    if finality is None or assignments is None:
        return "unknown"
    player = value_of(starter, "Player")
    canonical_id = _text(value_of(player, "CanonicalPlayerID"))
    teams: list[str] = []
    if canonical_id.strip() != "" and canonical_id in assignments:
        teams.extend(assignments[canonical_id])
    for mapping in collection(value_of(player, "ProviderMappings")):
        if _text(value_of(mapping, "Provider")) != "Sleeper":
            continue
        provider_id = _text(value_of(mapping, "ProviderPlayerID")).strip().upper()
        if re.fullmatch(r"[A-Z]{2,3}", provider_id):
            teams.append(provider_id)
    teams = sorted(set(teams))
    if not teams:
        return "unknown"
    candidates: dict[str, dict[str, Any]] = {}
    for game in week_games:
        away = _text(value_of(game, "AwayTeam")).strip().upper()
        home = _text(value_of(game, "HomeTeam")).strip().upper()
        if away in teams or home in teams:
            candidates.setdefault(_text(value_of(game, "GameID")).lower(), game)
    if len(candidates) != 1:
        return "unknown"
    game_id = _text(value_of(next(iter(candidates.values())), "GameID"))
    if game_id.strip() == "" or game_id not in finality or finality[game_id] is None:
        return "unknown"
    return "final" if bool(finality[game_id]) else "open"


def expected_starter_count(league_source: Any) -> int:
    positions = collection(value_of(league_source, "RosterPositions"))
    return len([p for p in positions if str(p).upper() not in NON_STARTER_POSITIONS])


def active_completion_state(team_ids: list[Any], decision_facts: Any) -> str:
    """CompletionState of a matchup in the active lineup week from the Decision Windows facts (Resolve-MrmActiveCompletionState)."""
    relevance = value_of(decision_facts, "FantasyRelevance")
    if relevance is None:
        return "unknown"
    states: dict[str, Any] = {}
    for team in collection(value_of(relevance, "Teams")):
        team_id = value_of(team, "FantasyTeamID")
        if team_id is not None:
            states[str(team_id)] = team
    evaluations: dict[str, Any] = {}
    for evaluation in collection(value_of(decision_facts, "TeamLineupEvaluations")):
        team_id = value_of(evaluation, "FantasyTeamID")
        if team_id is not None:
            evaluations[str(team_id)] = evaluation

    unknown = False
    for team_id in team_ids:
        key = str(team_id)
        if key not in states:
            unknown = True
            continue
        state = states[key]
        has_path = value_of(state, "HasRemainingScoringPath")
        slots = collection(value_of(state, "Slots"))
        repairable = any(_text(value_of(value_of(slot, "Repairability"), "State")) == "repairable" for slot in slots)
        if has_path is True or repairable:
            return "open"
        if has_path is None:
            unknown = True
        if key not in evaluations:
            unknown = True
        elif _text(value_of(evaluations[key], "State")) in ("unknown", "review"):
            unknown = True
        for slot in slots:
            if _text(value_of(slot, "State")) == "unknown":
                unknown = True
            repairability = value_of(slot, "Repairability")
            if repairability is not None and _text(value_of(repairability, "State")) == "unknown":
                unknown = True
    return "unknown" if unknown else "final"


def non_active_completion_state(
    pairing: dict[str, Any],
    league_source: Any,
    week_games: list[dict[str, Any]],
    assignments: dict[str, list[str]] | None,
    finality: dict[str, Any] | None,
    first_kickoff: str | None,
    at_utc: datetime,
) -> str:
    """CompletionState of a matchup outside the active lineup week (Resolve-MrmNonActiveCompletionState)."""
    if not _blank(first_kickoff):
        try:
            started = parse_instant_text(first_kickoff) <= at_utc
        except ValueError:
            return "unknown"
        if not started:
            evidence = sum(len(collection(value_of(p["SourceRow"], "StarterPoints"))) for p in pairing["Participants"])
            return "open" if evidence > 0 else "unknown"

    expected = expected_starter_count(league_source)
    if expected <= 0:
        return "unknown"
    unknown = False
    for participant in pairing["Participants"]:
        starters = collection(value_of(participant["SourceRow"], "StarterPoints"))
        empty = value_of(participant["SourceRow"], "EmptyStarterSlots")
        if empty is None:
            empty = 0
        # Only an explicit canonical integer from a provider "0" slot counts as empty; anything else stays unknown.
        if isinstance(empty, bool) or not isinstance(empty, int) or empty < 0 or empty > expected:
            unknown = True
        elif len(starters) + empty != expected:
            unknown = True
        for starter in starters:
            resolution = starter_game_resolution(starter, week_games, assignments, finality)
            if resolution == "open":
                return "open"
            if resolution == "unknown":
                unknown = True
    return "unknown" if unknown else "final"


def known_last_week(league_source: Any) -> int:
    structure = value_of(league_source, "WeekStructure")
    settings = value_of(league_source, "Settings")
    expected_last = to_int(value_of(structure, "ExpectedLastLeagueWeek"))
    if expected_last <= 0:
        expected_last = to_int(value_of(structure, "FinalLeagueWeek"))
    if expected_last <= 0:
        expected_last = to_int(value_of(settings, "last_scored_leg"))
    if expected_last <= 0:
        raise MatchupContextError("Cannot resolve the last fantasy league week.")
    if _text(value_of(league_source, "Status")) == "complete":
        final = to_int(value_of(structure, "FinalLeagueWeek"))
        return min(final, expected_last) if final > 0 else expected_last
    playoff_start = to_int(value_of(structure, "PlayoffStartWeek"))
    if playoff_start <= 0:
        playoff_start = to_int(value_of(settings, "playoff_week_start"))
    if playoff_start <= 0:
        return expected_last
    leg = to_int(value_of(settings, "leg"))
    if leg < playoff_start:
        return min(playoff_start - 1, expected_last)
    if to_int(value_of(structure, "PlayoffRoundType")) == 2:
        round_start = playoff_start + ((leg - playoff_start) // 2) * 2
        return min(round_start + 1, expected_last)
    return min(leg, expected_last)


# ---------------------------------------------------------------------------------------------------------------------
# Season model


def build_matchups_model(
    repo_root: Path,
    league_id: str,
    season: int,
    participant_order: dict[str, int],
    at_utc: datetime,
    decision_facts: Any = None,
    live_rows: list[Any] | None = None,
    live_week: int = 0,
    active_score_evidence_available: bool = True,
) -> dict[str, Any]:
    """The season ``Matchups`` read model at ``at_utc`` (New-MatchupSeasonReadModel).

    ``decision_facts`` are the Decision Windows of the active lineup week (None for a completed season). ``live_rows`` are the
    strict current-week rows of ``live_week`` and apply to the active week only.
    """
    if at_utc.tzinfo is None:
        raise MatchupContextError("AtUtc must be timezone-aware")
    live_rows = live_rows or []
    season_dir = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    league_file = season_dir / "league.json"
    matchup_dir = season_dir / "matchups"
    if not league_file.is_file() or not matchup_dir.is_dir():
        raise MatchupContextError(f"Canonical league matchup source is incomplete for {league_id} season {season}.")
    league_source = _read(league_file, "Canonical league source")
    games = schedule_games(repo_root, season)
    finality = finality_map(repo_root, season)
    last_week = known_last_week(league_source)
    structure = value_of(league_source, "WeekStructure")
    settings = value_of(league_source, "Settings")
    start_week = to_int(value_of(structure, "StartWeek"))
    if start_week <= 0:
        start_week = to_int(value_of(settings, "start_week"))
    if start_week <= 0:
        start_week = 1
    playoff_start = to_int(value_of(structure, "PlayoffStartWeek"))
    if playoff_start <= 0:
        playoff_start = to_int(value_of(settings, "playoff_week_start"))

    decision_season = _text(value_of(decision_facts, "Season"))
    active_week = to_int(value_of(decision_facts, "LineupWeek")) if decision_facts is not None and decision_season == str(season) else 0
    if live_rows and live_week <= 0:
        raise MatchupContextError("LiveMatchupWeek is required when LiveMatchupRows are supplied.")

    weeks: list[dict[str, Any]] = []
    for week in range(start_week, last_week + 1):
        week_games = [g for g in games if to_int(value_of(g, "Week")) == week]
        kickoffs = sorted(k for k in (kickoff_utc(g) for g in week_games) if k)
        first_kickoff = kickoffs[0] if kickoffs else None
        matchup_file = matchup_dir / f"week-{week}.json"
        if matchup_file.is_file():
            payload = _read(matchup_file, f"Canonical matchups week {week}")
            rows = payload if isinstance(payload, list) else [payload]
        else:
            rows = []
        week_live_rows = live_rows if (week == active_week and week == live_week) else []
        pairings, malformed = canonical_pairings(season, week, rows, participant_order, week_live_rows)
        if week == active_week and not active_score_evidence_available:
            for pairing in pairings:
                pairing["ScoreEvidenceUnknown"] = True
        assignments = None
        if week != active_week and not _blank(first_kickoff):
            try:
                if parse_instant_text(first_kickoff) <= at_utc:
                    assignments = weekly_assignment_map(repo_root, season, week)
            except ValueError:
                pass

        views: list[dict[str, Any]] = []
        for pairing in pairings:
            team_ids = [p["TeamID"] for p in pairing["Participants"]]
            if week == active_week and decision_facts is not None:
                completion = active_completion_state(team_ids, decision_facts)
            else:
                completion = non_active_completion_state(pairing, league_source, week_games, assignments, finality, first_kickoff, at_utc)
            if pairing["ScoreEvidenceUnknown"] and completion == "final":
                completion = "unknown"
            if completion == "final" and any(p["Points"] is None for p in pairing["Participants"]):
                completion = "unknown"
            participants = [{"TeamID": p["TeamID"], "Points": p["Points"], "ScoreKind": p["ScoreKind"]} for p in pairing["Participants"]]
            view: dict[str, Any] = {
                "FantasyMatchupID": pairing["FantasyMatchupID"],
                "Participants": participants,
                "CompletionState": completion,
                "Result": None,
            }
            if completion == "final":
                left, right = participants
                if float(left["Points"]) == float(right["Points"]):
                    view["Result"] = {"Type": "tie", "WinnerTeamID": None}
                else:
                    winner = left["TeamID"] if float(left["Points"]) > float(right["Points"]) else right["TeamID"]
                    view["Result"] = {"Type": "win", "WinnerTeamID": winner}
            views.append(view)

        if not views:
            week_completion = "unknown"
        elif any(v["CompletionState"] == "open" for v in views):
            week_completion = "open"
        elif malformed or any(v["CompletionState"] == "unknown" for v in views):
            week_completion = "unknown"
        else:
            week_completion = "final"
        weeks.append(
            {
                "Week": week,
                "Stage": "playoffs" if playoff_start > 0 and week >= playoff_start else "regular-season",
                "FirstKickoffUtc": first_kickoff,
                "CompletionState": week_completion,
                "Matchups": sorted(views, key=lambda v: v["FantasyMatchupID"]),
            }
        )

    completed = [w["Week"] for w in weeks if w["CompletionState"] == "final"]
    last_completed = max(completed) if completed else None
    upcoming = [
        w["Week"]
        for w in weeks
        if (last_completed is None or w["Week"] > last_completed) and w["CompletionState"] != "final" and w["Matchups"]
    ]
    return {
        "SchemaVersion": 1,
        "Season": str(season),
        "Weeks": weeks,
        "Summary": {"LastCompletedWeek": last_completed, "ActiveOrNextWeek": min(upcoming) if upcoming else None},
    }


# ---------------------------------------------------------------------------------------------------------------------
# Resolver


def matchup_load_week(decision_facts: Any, last_league_week: int, league_complete: bool) -> int:
    """The week whose current matchup rows are loaded (Resolve-FantasyMatchupLoadWeek): the lineup week capped at the last league week."""
    if league_complete or last_league_week <= 0 or decision_facts is None:
        return 0
    lineup = to_int(value_of(decision_facts, "LineupWeek"))
    return 0 if lineup <= 0 else min(lineup, last_league_week)


def standings_product(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    path = repo_root / DATA_DERIVED_ROOT / "league-standings" / league_id / f"{season}.json"
    return _read(path, "league-standings product")


def resolve_matchups(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """The season ``Matchups`` model at ``at_utc``; computed, never persisted.

    The current league season uses the Decision Windows of the lineup week (active-week completion) and the strict current rows;
    every other season is history (no Decision Windows, completion from starter games and weekly rosters).
    """
    from league_standings_sources import StandingsSourceError, current_season, manifest

    from .decision_windows import DecisionWindowsError, resolve as resolve_decision_windows
    from .league_lifecycle import LifecycleError, resolve_lifecycle

    if at_utc.tzinfo is None:
        raise MatchupContextError("AtUtc must be timezone-aware")
    try:
        current = current_season(manifest(repo_root, league_id))
    except (StandingsSourceError, KeyError, ValueError) as exc:
        raise MatchupContextError(str(exc)) from exc
    order = participant_order_from_standings(standings_product(repo_root, league_id, season))
    if season != current:
        return build_matchups_model(repo_root, league_id, season, order, at_utc)
    try:
        decision_facts = resolve_decision_windows(repo_root, league_id, season, at_utc)
        lifecycle = resolve_lifecycle(repo_root, league_id, season, at_utc)
    except (DecisionWindowsError, LifecycleError) as exc:
        raise MatchupContextError(str(exc)) from exc
    league = _read(repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json", "Canonical league source")
    week = matchup_load_week(decision_facts, int(lifecycle["LastLeagueWeek"]), _text(value_of(league, "Status")) == "complete")
    rows: list[Any] = []
    evidence = week <= 0
    if week > 0:
        try:
            rows = current_matchup_rows(repo_root, league_id, season, week)
            evidence = True
        except MatchupContextError:
            rows, evidence = [], False
    return build_matchups_model(repo_root, league_id, season, order, at_utc, decision_facts, rows, week, evidence)


__all__ = [
    "matchup_load_week", "resolve_matchups", "standings_product",
    "MatchupContextError", "active_completion_state", "build_matchups_model", "canonical_pairings", "current_matchup_rows",
    "effective_score", "expected_starter_count", "fantasy_matchup_id", "finality_map", "kickoff_utc", "known_last_week",
    "neutral_order_index", "non_active_completion_state", "participant_order_from_standings", "schedule_games",
    "starter_game_resolution", "weekly_assignment_map",
]
