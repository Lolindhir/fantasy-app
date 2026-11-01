"""Consumer-only team display mapping for Fantasy Operations.

Names are sourced from canonical member metadata. TeamAbbr is a presentation
projection kept compatible with the existing App label convention; it is not a
shared league fact or a new domain owner. No App League.json input is used.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from canonical_league_ownership import CanonicalOwnershipError, _read_json, _require_list, _require_object


def abbreviation(name: str, team_id: int) -> str:
    """Match App TeamUtils::ConvertTo-TeamAbbreviation for human-facing labels."""
    normalized = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name.strip())
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized)
    normalized = re.sub(r"[^\w]+", " ", normalized).strip()
    parts = [p for p in normalized.split() if p.casefold() not in {"team", "the"}]
    if not parts:
        return f"T{team_id:02d}"
    if len(parts) == 1:
        word = parts[0][:3]
        return word[:1].upper() + word[1:].lower()
    if len(parts) == 2:
        word = parts[0][:2]
        return word[:1].upper() + word[1:].lower() + parts[1][:1].upper()
    return "".join(p[:1].upper() for p in parts[:3])


def enrich_from_members(
    snapshot: dict[str, Any], root: Path, *, league_id: str, season: int
) -> list[dict[str, Any]]:
    """Join the validated canonical TeamID/member bridge to member team labels."""
    if snapshot.get("CanonicalLeagueID") != league_id or snapshot.get("Season") != season:
        raise CanonicalOwnershipError("Canonical team display league or season mismatch.")
    member_path = root / "data-source/leagues" / league_id / "seasons" / str(season) / "members.json"
    members = _require_list(_read_json(member_path), "members.json")
    by_id: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(members):
        member = _require_object(raw, f"members.json[{i}]")
        member_id = member.get("CanonicalLeagueMemberID")
        if not isinstance(member_id, str) or not member_id or member_id in by_id:
            raise CanonicalOwnershipError("Invalid or duplicated canonical display member ID.")
        by_id[member_id] = member

    enriched: list[dict[str, Any]] = []
    seen: set[int] = set()
    for i, raw in enumerate(_require_list(snapshot.get("Teams"), "snapshot.Teams")):
        team = _require_object(raw, f"snapshot.Teams[{i}]")
        team_id = team.get("TeamID")
        if not isinstance(team_id, int) or isinstance(team_id, bool) or team_id <= 0 or team_id in seen:
            raise CanonicalOwnershipError("Invalid or duplicate canonical display TeamID.")
        seen.add(team_id)
        member = by_id.get(team.get("CanonicalLeagueMemberID"))
        if member is None:
            raise CanonicalOwnershipError(f"Canonical display member missing for TeamID {team_id}.")
        metadata = member.get("Metadata") or {}
        if not isinstance(metadata, dict):
            raise CanonicalOwnershipError("Canonical member display Metadata must be an object.")
        custom = metadata.get("team_name")
        owner = member.get("DisplayName")
        if custom is not None and not isinstance(custom, str):
            raise CanonicalOwnershipError("Canonical member team_name must be a string.")
        if not isinstance(owner, str) or not owner.strip():
            raise CanonicalOwnershipError("Canonical member DisplayName missing.")
        name = custom.strip() if custom and custom.strip() else f"Team {owner.strip()}"
        enriched.append({**team, "Team": name, "TeamAbbr": abbreviation(name, team_id)})
    if len(enriched) != len(by_id):
        raise CanonicalOwnershipError("Canonical display member coverage mismatch.")
    return sorted(enriched, key=lambda t: t["TeamID"])
