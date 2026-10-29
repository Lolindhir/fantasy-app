#!/usr/bin/env python3
"""Canonical inputs of the league-standings product (ADR-072, .ai-context/manual/league-standings.yaml).

Reads data-source/leagues/<CanonicalLeagueID>/seasons/<season>/ (league, members, rosters, brackets, matchups) and
the week basis from tools/derived_data_lib/week_finality.py. Port of CanonicalStandingUtils.psm1; fails closed on
missing files, missing or duplicate Sleeper mappings and roster/member mismatches.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.league_standings import SeasonInputs  # noqa: E402
from derived_data_lib.week_finality import resolve_week_finality  # noqa: E402

REQUIRED_FILES = ("league.json", "members.json", "rosters.json", "winners-bracket.json", "losers-bracket.json")


class StandingsSourceError(ValueError):
    """Raised when canonical inputs for the standings product are missing or inconsistent (fail closed)."""


def league_root(repo_root: Path, league_id: str) -> Path:
    return repo_root / DATA_SOURCE_ROOT / "leagues" / league_id


def manifest(repo_root: Path, league_id: str) -> dict[str, Any]:
    path = league_root(repo_root, league_id) / "manifest.json"
    if not path.is_file():
        raise StandingsSourceError(f"League manifest missing: {path}")
    return _read(path)


def manifest_seasons(data: dict[str, Any]) -> list[int]:
    return sorted(int(item["Season"]) for item in data.get("Seasons", []))


def current_season(data: dict[str, Any]) -> int:
    return int(str(data["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])


def _read(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise StandingsSourceError(f"Canonical standings source is empty: {path}")
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise StandingsSourceError(f"Could not read canonical standings source {path}: {error}") from error


def _list(payload: Any) -> list[Any]:
    if payload is None:
        return []
    return payload if isinstance(payload, list) else [payload]


def _sleeper_value(mappings: Any, name: str, label: str) -> str:
    matches = [m for m in _list(mappings) if m.get("Provider") == "Sleeper"]
    if len(matches) != 1:
        raise StandingsSourceError(f"{label} must have exactly one Sleeper provider mapping; found {len(matches)}.")
    value = str(matches[0].get(name) if matches[0].get(name) is not None else "")
    if not value.strip():
        raise StandingsSourceError(f"{label} Sleeper provider mapping is missing '{name}'.")
    return value


def _unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        if item[key] in lookup:
            raise StandingsSourceError(f"Duplicate {label} {item[key]!r}.")
        lookup[item[key]] = item
    return lookup


def build_teams(members: list[dict[str, Any]], rosters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get-CanonicalStandingTeamData: one team per roster ordered by provider roster ID."""
    member_sources = []
    for member in members:
        member_id = str(member.get("CanonicalLeagueMemberID") or "")
        if not member_id.strip():
            raise StandingsSourceError("Canonical standings member is missing CanonicalLeagueMemberID.")
        member_sources.append({
            "CanonicalLeagueMemberID": member_id,
            "ProviderUserID": _sleeper_value(member.get("ProviderMappings"), "ProviderUserID", f"Canonical member {member_id!r}"),
            "Source": member,
        })
    roster_sources = []
    for roster in rosters:
        roster_id = str(roster.get("CanonicalLeagueRosterID") or "")
        if not roster_id.strip():
            raise StandingsSourceError("Canonical standings roster is missing CanonicalLeagueRosterID.")
        member_id = str(roster.get("CanonicalLeagueMemberID") or "")
        if not member_id.strip():
            raise StandingsSourceError(f"Canonical roster {roster_id!r} is missing CanonicalLeagueMemberID.")
        owner_id = str(roster.get("ProviderOwnerUserID") or "")
        if not owner_id.strip():
            raise StandingsSourceError(f"Canonical roster {roster_id!r} is missing ProviderOwnerUserID.")
        roster_sources.append({
            "CanonicalLeagueRosterID": roster_id,
            "CanonicalLeagueMemberID": member_id,
            "ProviderRosterID": _sleeper_value(roster.get("ProviderMappings"), "ProviderRosterID", f"Canonical roster {roster_id!r}"),
            "ProviderOwnerUserID": owner_id,
            "Source": roster,
        })
    members_by_id = _unique(member_sources, "CanonicalLeagueMemberID", "CanonicalLeagueMemberID")
    _unique(member_sources, "ProviderUserID", "member ProviderUserID")
    _unique(roster_sources, "CanonicalLeagueRosterID", "CanonicalLeagueRosterID")
    _unique(roster_sources, "ProviderRosterID", "roster ProviderRosterID")
    _unique(roster_sources, "ProviderOwnerUserID", "roster ProviderOwnerUserID")
    for roster in roster_sources:
        member = members_by_id.get(roster["CanonicalLeagueMemberID"])
        if member is None:
            raise StandingsSourceError(
                f"Canonical roster {roster['CanonicalLeagueRosterID']!r} references unknown CanonicalLeagueMemberID "
                f"{roster['CanonicalLeagueMemberID']!r}.")
        if member["ProviderUserID"] != roster["ProviderOwnerUserID"]:
            raise StandingsSourceError(
                f"Canonical roster {roster['CanonicalLeagueRosterID']!r} owner mapping {roster['ProviderOwnerUserID']!r} "
                f"does not match member provider mapping {member['ProviderUserID']!r}.")

    teams = []
    for roster_source in sorted(roster_sources, key=lambda r: int(r["ProviderRosterID"])):
        member = members_by_id[roster_source["CanonicalLeagueMemberID"]]["Source"]
        roster = roster_source["Source"]
        owner = str(member.get("DisplayName") or "")
        if not owner.strip():
            raise StandingsSourceError(f"Canonical member {roster_source['CanonicalLeagueMemberID']!r} is missing DisplayName.")
        metadata = member.get("Metadata") or {}
        team_name = str(metadata.get("team_name") or "")
        team_name = f"Team {owner}" if not team_name.strip() else team_name.strip()
        owner_avatar = str(member.get("Avatar") or "").strip() or None
        team_avatar = str(metadata.get("avatar") or "").strip() or None
        settings = roster.get("Settings") or {}
        roster_meta = roster.get("Metadata") or {}
        teams.append({
            "TeamID": int(roster_source["ProviderRosterID"]),
            "CanonicalLeagueRosterID": roster_source["CanonicalLeagueRosterID"],
            "Owner": owner,
            "OwnerAvatarID": owner_avatar,
            "Team": team_name,
            "TeamAvatar": team_avatar,
            "Points": float(settings.get("fpts") or 0) + float(settings.get("fpts_decimal") or 0) / 100.0,
            "PointsAgainst": float(settings.get("fpts_against") or 0) + float(settings.get("fpts_against_decimal") or 0) / 100.0,
            "Wins": int(settings.get("wins") or 0),
            "Losses": int(settings.get("losses") or 0),
            "Ties": int(settings.get("ties") or 0),
            "Record": str(roster_meta.get("record") or ""),
            "Streak": str(roster_meta.get("streak") or ""),
        })
    return teams


def _provider_roster_ids(rosters: list[dict[str, Any]]) -> dict[str, int]:
    return {r["CanonicalLeagueRosterID"]: int(_sleeper_value(r.get("ProviderMappings"), "ProviderRosterID", "roster")) for r in rosters}


def convert_bracket(matches: list[dict[str, Any]], roster_ids: dict[str, int]) -> list[dict[str, Any]]:
    """ConvertTo-CanonicalStandingLegacyBracket: canonical roster references -> legacy match with provider roster IDs."""
    def resolve(value: Any) -> int | None:
        if value is None or not str(value).strip():
            return None
        if value not in roster_ids:
            raise StandingsSourceError(f"Canonical bracket references unknown roster {value!r}.")
        return roster_ids[value]

    return [
        {
            "r": match.get("Round"), "m": match.get("Match"),
            "t1": resolve(match.get("Team1CanonicalLeagueRosterID")), "t2": resolve(match.get("Team2CanonicalLeagueRosterID")),
            "w": resolve(match.get("WinnerCanonicalLeagueRosterID")), "l": resolve(match.get("LoserCanonicalLeagueRosterID")),
            "p": match.get("Placement"),
        }
        for match in matches
    ]


def weekly_matchups(season_dir: Path, max_week: int) -> list[dict[str, Any]]:
    """Per-week matchup facts of the regular season; weeks without a file are omitted (movement then stops there)."""
    weeks = []
    for week in range(1, max_week + 1):
        path = season_dir / "matchups" / f"week-{week}.json"
        if not path.is_file():
            continue
        entries = []
        for matchup in _list(_read(path)):
            mapping = next((m for m in matchup.get("ProviderMappings") or [] if m.get("Provider") == "Sleeper"), None)
            if mapping is None:
                continue
            entries.append({
                "TeamID": int(mapping["ProviderRosterID"]),
                "MatchupID": mapping.get("ProviderMatchupID"),
                "Points": matchup.get("Points"),
            })
        weeks.append({"Week": week, "Entries": entries})
    return weeks


def load_season_inputs(repo_root: Path, league_id: str, season: int, current: int) -> SeasonInputs:
    season_dir = league_root(repo_root, league_id) / "seasons" / str(season)
    if not season_dir.is_dir():
        raise StandingsSourceError(f"Canonical League season directory missing at {season_dir}.")
    for name in REQUIRED_FILES:
        if not (season_dir / name).is_file():
            raise StandingsSourceError(f"Canonical standings source {name!r} missing for {league_id}/{season}.")
    league = _read(season_dir / "league.json")
    if str(league.get("Season")) != str(season):
        raise StandingsSourceError(f"Canonical standings season mismatch: requested {season}, league.json contains {league.get('Season')}.")
    status = str(league.get("Status"))
    completed = status == "complete"
    if not completed and season != current:
        raise StandingsSourceError(f"Canonical standings accept only the current season {current} in progress; {league_id}/{season} has status {status!r}.")
    playoff_start = int((league.get("Settings") or {}).get("playoff_week_start") or 0)
    if playoff_start <= 1:
        raise StandingsSourceError(f"Canonical standings source for {league_id}/{season} has invalid playoff_week_start {playoff_start}.")

    members, rosters = _list(_read(season_dir / "members.json")), _list(_read(season_dir / "rosters.json"))
    roster_ids = _provider_roster_ids(rosters)
    games = playoff_start - 1
    finality = resolve_week_finality(repo_root, league_id, season)
    return SeasonInputs(
        league_id=league_id,
        season=season,
        league_status=status,
        is_completed=completed,
        regular_season_games=games,
        league_scored_week=int(finality["LeagueScoredWeek"]),
        teams=build_teams(members, rosters),
        winners_bracket=convert_bracket(_list(_read(season_dir / "winners-bracket.json")), roster_ids),
        losers_bracket=convert_bracket(_list(_read(season_dir / "losers-bracket.json")), roster_ids),
        weekly_matchups=weekly_matchups(season_dir, games),
    )
