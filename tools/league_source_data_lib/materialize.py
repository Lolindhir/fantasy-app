from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import canonical_league_season_id, write_json_if_changed
from .registry import LeagueDataset
from .week_structure import (
    derive_season_week_structures,
    resolve_nfl_regular_season_week_ceiling,
)

SCHEMA_VERSION = 1


def _stable_id(prefix: str, *parts: object) -> str:
    raw = ":".join(str(part) for part in parts)
    value = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"https://github.com/Lolindhir/fantasy-app/league-source/{prefix}/{raw}",
    )
    return f"{prefix}-{value.hex}"


def canonical_member_id(canonical_league_id: str, provider_user_id: str) -> str:
    return _stable_id("clm", canonical_league_id, provider_user_id)


def canonical_roster_id(canonical_league_season_id_value: str, provider_roster_id: object) -> str:
    return _stable_id("clr", canonical_league_season_id_value, provider_roster_id)


def canonical_draft_id(canonical_league_season_id_value: str, provider_draft_id: str) -> str:
    return _stable_id("cld", canonical_league_season_id_value, provider_draft_id)


def canonical_transaction_id(canonical_league_season_id_value: str, provider_transaction_id: str) -> str:
    return _stable_id("clt", canonical_league_season_id_value, provider_transaction_id)


def canonical_matchup_id(
    canonical_league_season_id_value: str, week: int, provider_matchup_id: object
) -> str | None:
    if provider_matchup_id is None or str(provider_matchup_id).strip() == "":
        return None
    return _stable_id("clmup", canonical_league_season_id_value, week, provider_matchup_id)


def _read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required League Source raw file is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class PlayerMappingResolver:
    mappings: dict[tuple[str, str], list[dict[str, Any]]]
    conflicts: dict[tuple[str, str], list[dict[str, Any]]]

    @classmethod
    def load(cls, repo_root: Path) -> "PlayerMappingResolver":
        path = repo_root / "source-data/nfl/identities/provider-mappings.json"
        raw = _read_json(path)
        if not isinstance(raw, dict):
            raise ValueError(f"Player provider mappings must be an object: {path}")
        mappings: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in raw.get("Mappings", []):
            if not isinstance(item, dict):
                raise ValueError("Player provider mapping entries must be objects")
            key = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
            mappings.setdefault(key, []).append(item)
        conflicts: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in raw.get("Conflicts", []):
            if not isinstance(item, dict):
                raise ValueError("Player provider conflict entries must be objects")
            key = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
            conflicts.setdefault(key, []).append(item)
        return cls(mappings, conflicts)

    @staticmethod
    def _active(item: dict[str, Any], season: int) -> bool:
        first = int(item.get("FirstObservedSeason") or season)
        last = int(item.get("LastObservedSeason") or first)
        return first <= season <= last

    def resolve(self, provider: str, external_id: str, season: int) -> str | None:
        key = (provider, external_id)
        active_conflicts = [
            item for item in self.conflicts.get(key, []) if self._active(item, season)
        ]
        if active_conflicts:
            raise ValueError(
                f"Ambiguous player provider mapping for {provider}/{external_id} in season {season}"
            )
        candidates = {
            str(item.get("CanonicalPlayerID") or "")
            for item in self.mappings.get(key, [])
            if self._active(item, season) and str(item.get("CanonicalPlayerID") or "")
        }
        if len(candidates) > 1:
            raise ValueError(
                f"Multiple active player provider mappings for {provider}/{external_id} "
                f"in season {season}: {sorted(candidates)}"
            )
        return next(iter(candidates), None)


def _player_ref(
    resolver: PlayerMappingResolver, provider_player_id: object, season: int
) -> dict | None:
    if provider_player_id is None:
        return None
    external = str(provider_player_id).strip()
    if not external:
        return None
    return {
        "CanonicalPlayerID": resolver.resolve("Sleeper", external, season),
        "ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": external}],
    }


def _player_refs(
    resolver: PlayerMappingResolver, values: object, season: int, source_label: str
) -> list[dict]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{source_label} must be an array")
    seen: set[str] = set()
    result: list[dict] = []
    for value in values:
        external = str(value or "").strip()
        if not external:
            continue
        if external in seen:
            raise ValueError(f"Duplicate Sleeper player id {external} in {source_label}")
        seen.add(external)
        ref = _player_ref(resolver, external, season)
        if ref is not None:
            result.append(ref)
    return result


def _member_and_roster_maps(
    canonical_league_id: str,
    season_id: str,
    members_raw: object,
    rosters_raw: object,
) -> tuple[list[dict], list[dict], dict[str, str], dict[str, str]]:
    if not isinstance(members_raw, list) or not isinstance(rosters_raw, list):
        raise ValueError("Sleeper members and rosters raw datasets must be arrays")

    member_by_provider: dict[str, str] = {}
    members: list[dict] = []
    for item in members_raw:
        if not isinstance(item, dict):
            raise ValueError("Sleeper member entries must be objects")
        provider_id = str(item.get("user_id") or "").strip()
        if not provider_id:
            raise ValueError("Sleeper member user_id is required")
        if provider_id in member_by_provider:
            raise ValueError(f"Duplicate Sleeper member user_id: {provider_id}")
        member_id = canonical_member_id(canonical_league_id, provider_id)
        member_by_provider[provider_id] = member_id
        members.append(
            {
                "CanonicalLeagueMemberID": member_id,
                "DisplayName": item.get("display_name"),
                "Avatar": item.get("avatar"),
                "IsOwner": bool(item.get("is_owner", False)),
                "Metadata": item.get("metadata") or {},
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderUserID": provider_id}],
            }
        )

    roster_by_provider: dict[str, str] = {}
    owner_claims: set[str] = set()
    rosters: list[dict] = []
    for item in rosters_raw:
        if not isinstance(item, dict):
            raise ValueError("Sleeper roster entries must be objects")
        provider_roster_id = str(item.get("roster_id") or "").strip()
        provider_owner_id = str(item.get("owner_id") or "").strip()
        if not provider_roster_id:
            raise ValueError("Sleeper roster roster_id is required")
        if provider_roster_id in roster_by_provider:
            raise ValueError(f"Duplicate Sleeper roster_id: {provider_roster_id}")
        if not provider_owner_id or provider_owner_id not in member_by_provider:
            raise ValueError(
                f"Sleeper roster {provider_roster_id} owner_id does not resolve to "
                f"one league member: {provider_owner_id or '<missing>'}"
            )
        if provider_owner_id in owner_claims:
            raise ValueError(f"Sleeper member owns multiple rosters: {provider_owner_id}")
        owner_claims.add(provider_owner_id)
        roster_id = canonical_roster_id(season_id, provider_roster_id)
        roster_by_provider[provider_roster_id] = roster_id
        rosters.append(
            {
                "CanonicalLeagueRosterID": roster_id,
                "CanonicalLeagueMemberID": member_by_provider[provider_owner_id],
                "ProviderMappings": [
                    {"Provider": "Sleeper", "ProviderRosterID": provider_roster_id}
                ],
                "ProviderOwnerUserID": provider_owner_id,
                "Settings": item.get("settings") or {},
                "Metadata": item.get("metadata") or {},
                "_rawPlayers": item.get("players") or [],
                "_rawReserve": item.get("reserve") or [],
                "_rawTaxi": item.get("taxi") or [],
                "_rawStarters": item.get("starters") or [],
            }
        )
    members.sort(key=lambda item: item["CanonicalLeagueMemberID"])
    rosters.sort(key=lambda item: item["CanonicalLeagueRosterID"])
    return members, rosters, member_by_provider, roster_by_provider


def _resolve_member(
    member_by_provider: dict[str, str], value: object, source: str
) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    provider_id = str(value).strip()
    canonical = member_by_provider.get(provider_id)
    if canonical is None:
        raise ValueError(f"{source} references unknown Sleeper user_id {provider_id}")
    return canonical


def _resolve_roster(
    roster_by_provider: dict[str, str], value: object, source: str
) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    provider_id = str(value).strip()
    canonical = roster_by_provider.get(provider_id)
    if canonical is None:
        raise ValueError(f"{source} references unknown Sleeper roster_id {provider_id}")
    return canonical


def _canonicalize_rosters(
    rosters: list[dict], resolver: PlayerMappingResolver, season: int
) -> list[dict]:
    result: list[dict] = []
    for item in rosters:
        result.append(
            {
                key: value
                for key, value in item.items()
                if not key.startswith("_raw")
            }
        )
        result[-1].update(
            {
                "Players": _player_refs(
                    resolver, item["_rawPlayers"], season, "roster.players"
                ),
                "Reserve": _player_refs(
                    resolver, item["_rawReserve"], season, "roster.reserve"
                ),
                "Taxi": _player_refs(
                    resolver, item["_rawTaxi"], season, "roster.taxi"
                ),
                "Starters": _player_refs(
                    resolver, item["_rawStarters"], season, "roster.starters"
                ),
            }
        )
    return result


def _canonicalize_bracket(
    raw: object, roster_by_provider: dict[str, str], label: str
) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"Sleeper {label} bracket must be an array")
    result: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"Sleeper {label} bracket entries must be objects")
        try:
            round_no = int(item["