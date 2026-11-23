"""Pure assembly of the league-teams product (Issue #774, .ai-context/manual/league-teams.yaml).

League-team identity per season: for every season of the league manifest and every fantasy team (provider roster) the manager fields
(``OwnerID``, ``Owner``, ``OwnerAvatar``) and the fantasy-team fields (``TeamName``, ``TeamNameSource``, ``TeamAbbr``, ``TeamAvatar``) are kept strictly apart.
The values are a snapshot of the season's canonical Sleeper members and rosters; a later name or logo is never projected into an older season.

This module is the single implementation of the team name rule and the team abbreviation rule (contents unchanged from the former
CanonicalLeagueCoreUtils.psm1 / TeamUtils.psm1 / tools/team_abbreviation.py copies). Reads only data-source/leagues; no public/data file is an input.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT

PRODUCT = "league-teams"
SCHEMA_VERSION = 1
NAME_SOURCE_PROVIDER = "provider"
NAME_SOURCE_OWNER_FALLBACK = "owner-fallback"
# Provider fact: Sleeper serves an account avatar by its ID from this location (same value as the former AvatarUtils.psm1::Get-SleeperAvatar).
SLEEPER_AVATAR_URL = "https://sleepercdn.com/avatars/{avatar_id}"
STOP_WORDS = {"team", "the"}


class LeagueTeamsError(ValueError):
    """Incomplete or contradicting canonical member/roster evidence (fail closed)."""


# --- the two rules --------------------------------------------------------------------------------------------------------------------------------

def team_name(provider_team_name: str | None, owner: str | None) -> tuple[str | None, str | None]:
    """Display name of a fantasy team and where it comes from: the provider team name, else ``Team <Owner>``, else unknown."""
    if provider_team_name and provider_team_name.strip():
        return provider_team_name.strip(), NAME_SOURCE_PROVIDER
    if owner and owner.strip():
        return f"Team {owner.strip()}", NAME_SOURCE_OWNER_FALLBACK
    return None, None


def _normalize(name: str) -> str:
    text = name.strip()
    # (\p{Lu}+)(\p{Lu}\p{Ll}) -> "$1 $2": a run of capitals followed by a lowercase letter splits before the last capital.
    out: list[str] = []
    for index, char in enumerate(text):
        if index >= 1 and index + 1 < len(text) and char.isupper() and text[index - 1].isupper() and text[index + 1].islower():
            out.append(" ")
        out.append(char)
    text = "".join(out)
    # ([\p{Ll}\p{N}])(\p{Lu}) -> "$1 $2"
    out = []
    for index, char in enumerate(text):
        if index >= 1 and char.isupper() and (text[index - 1].islower() or text[index - 1].isnumeric()):
            out.append(" ")
        out.append(char)
    text = "".join(out)
    # [^\p{L}\p{N}]+ -> " "
    return "".join(char if char.isalpha() or char.isnumeric() else " " for char in text).strip()


def team_abbreviation(name: str | None, team_id: int | str | None) -> str:
    """Abbreviation of a team name (one word: 3 letters, two words: 2 letters + initial, more: up to three initials); T<ID> or TBD without a name."""
    try:
        fallback = f"T{int(str(team_id)):02d}"
    except (TypeError, ValueError):
        fallback = "TBD"
    if not name or not name.strip():
        return fallback
    parts = [part for part in _normalize(name).split() if part and part.lower() not in STOP_WORDS]
    if not parts:
        return fallback
    if len(parts) == 1:
        head = parts[0][:3]
        return head[0].upper() + head[1:].lower()
    if len(parts) == 2:
        prefix = parts[0][:2]
        return prefix[0].upper() + prefix[1:].lower() + parts[1][0].upper()
    return "".join(part[0].upper() for part in parts[:3])


def sleeper_avatar_url(avatar_id: Any) -> str | None:
    text = str(avatar_id or "").strip()
    return SLEEPER_AVATAR_URL.format(avatar_id=text) if text else None


# --- canonical inputs ----------------------------------------------------------------------------------------------------------------------------

def _read_list(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise LeagueTeamsError(f"Canonical league source is empty: {path}")
        payload = json.loads(text)
    except OSError as error:
        raise LeagueTeamsError(f"Canonical league source missing: {path}") from error
    except json.JSONDecodeError as error:
        raise LeagueTeamsError(f"Could not read canonical league source {path}: {error}") from error
    return payload if isinstance(payload, list) else [payload]


def _sleeper_value(mappings: Any, name: str, label: str) -> str:
    values = [str(m.get(name) or "") for m in (mappings or []) if str(m.get("Provider") or "").lower() == "sleeper"]
    values = [v for v in values if v.strip()]
    if len(values) != 1:
        raise LeagueTeamsError(f"{label} needs exactly one Sleeper {name}, found {len(values)}.")
    return values[0]


def _unique(items: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        value = item[key]
        if value in result:
            raise LeagueTeamsError(f"Duplicate {label} {value!r}.")
        result[value] = item
    return result


def season_teams(members: list[dict[str, Any]], rosters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Teams of one season from the canonical members and rosters, ordered by provider roster ID."""
    member_sources = []
    for member in members:
        member_id = str(member.get("CanonicalLeagueMemberID") or "")
        if not member_id.strip():
            raise LeagueTeamsError("Canonical member is missing CanonicalLeagueMemberID.")
        member_sources.append({
            "CanonicalLeagueMemberID": member_id,
            "ProviderUserID": _sleeper_value(member.get("ProviderMappings"), "ProviderUserID", f"Canonical member {member_id!r}"),
            "Source": member,
        })
    roster_sources = []
    for roster in rosters:
        roster_id = str(roster.get("CanonicalLeagueRosterID") or "")
        member_id = str(roster.get("CanonicalLeagueMemberID") or "")
        if not roster_id.strip() or not member_id.strip():
            raise LeagueTeamsError("Canonical roster is missing CanonicalLeagueRosterID or CanonicalLeagueMemberID.")
        owner_id = str(roster.get("ProviderOwnerUserID") or "")
        if not owner_id.strip():
            raise LeagueTeamsError(f"Canonical roster {roster_id!r} is missing ProviderOwnerUserID.")
        roster_sources.append({
            "CanonicalLeagueRosterID": roster_id,
            "CanonicalLeagueMemberID": member_id,
            "ProviderRosterID": int(_sleeper_value(roster.get("ProviderMappings"), "ProviderRosterID", f"Canonical roster {roster_id!r}")),
            "ProviderOwnerUserID": owner_id,
        })
    members_by_id = _unique(member_sources, "CanonicalLeagueMemberID", "CanonicalLeagueMemberID")
    _unique(member_sources, "ProviderUserID", "member ProviderUserID")
    _unique(roster_sources, "CanonicalLeagueRosterID", "CanonicalLeagueRosterID")
    _unique(roster_sources, "ProviderRosterID", "roster ProviderRosterID")
    _unique(roster_sources, "ProviderOwnerUserID", "roster ProviderOwnerUserID")

    teams: list[dict[str, Any]] = []
    for roster in sorted(roster_sources, key=lambda r: r["ProviderRosterID"]):
        member_source = members_by_id.get(roster["CanonicalLeagueMemberID"])
        if member_source is None:
            raise LeagueTeamsError(f"Canonical roster {roster['CanonicalLeagueRosterID']!r} references unknown CanonicalLeagueMemberID {roster['CanonicalLeagueMemberID']!r}.")
        if member_source["ProviderUserID"] != roster["ProviderOwnerUserID"]:
            raise LeagueTeamsError(
                f"Canonical roster {roster['CanonicalLeagueRosterID']!r} owner mapping {roster['ProviderOwnerUserID']!r} "
                f"does not match member provider mapping {member_source['ProviderUserID']!r}.")
        member = member_source["Source"]
        owner = str(member.get("DisplayName") or "").strip()
        if not owner:
            raise LeagueTeamsError(f"Canonical member {member_source['CanonicalLeagueMemberID']!r} is missing DisplayName.")
        metadata = member.get("Metadata") or {}
        name, source = team_name(str(metadata.get("team_name") or ""), owner)
        teams.append({
            "TeamID": roster["ProviderRosterID"],
            "CanonicalLeagueRosterID": roster["CanonicalLeagueRosterID"],
            "CanonicalLeagueMemberID": member_source["CanonicalLeagueMemberID"],
            "OwnerID": member_source["ProviderUserID"],
            "Owner": owner,
            "OwnerAvatar": sleeper_avatar_url(member.get("Avatar")),
            "TeamName": name,
            "TeamNameSource": source,
            "TeamAbbr": team_abbreviation(name, roster["ProviderRosterID"]),
            "TeamAvatar": str(metadata.get("avatar") or "").strip() or None,
        })
    return teams


def resolve(repo_root: Path, league_id: str) -> dict[str, Any]:
    """The league-teams document of one league over every manifest season (a pure function of the canonical members and rosters)."""
    import league_standings_sources as sources

    manifest = sources.manifest(repo_root, league_id)
    seasons = sources.manifest_seasons(manifest)
    root = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons"
    result = []
    for season in seasons:
        folder = root / str(season)
        result.append({
            "Season": str(season),
            "Teams": season_teams(_read_list(folder / "members.json"), _read_list(folder / "rosters.json")),
        })
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": league_id,
        "CurrentSeason": str(sources.current_season(manifest)),
        "Seasons": result,
    }
