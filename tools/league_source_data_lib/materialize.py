from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .core import canonical_league_season_id, write_json_if_changed
from .registry import LeagueDataset
from .week_structure import derive_season_week_structures, resolve_nfl_regular_season_week_ceiling

SCHEMA_VERSION = 1
REQUIRED_DATASET_IDS = {
    "sleeper.league",
    "sleeper.league-members",
    "sleeper.league-rosters",
    "sleeper.winners-bracket",
    "sleeper.losers-bracket",
    "sleeper.matchups",
    "sleeper.transactions",
    "sleeper.league-drafts",
    "sleeper.draft-detail",
    "sleeper.draft-picks",
    "sleeper.draft-traded-picks",
}


def _stable_id(prefix: str, *parts: object) -> str:
    raw = ":".join(str(part) for part in parts)
    value = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"https://github.com/Lolindhir/fantasy-app/league-source/{prefix}/{raw}",
    )
    return f"{prefix}-{value.hex}"


def canonical_member_id(canonical_league_id: str, provider_user_id: str) -> str:
    return _stable_id("clm", canonical_league_id, provider_user_id)


def canonical_roster_id(season_id: str, provider_roster_id: object) -> str:
    return _stable_id("clr", season_id, provider_roster_id)


def canonical_draft_id(season_id: str, provider_draft_id: str) -> str:
    return _stable_id("cld", season_id, provider_draft_id)


def canonical_transaction_id(season_id: str, provider_transaction_id: str) -> str:
    return _stable_id("clt", season_id, provider_transaction_id)


def canonical_matchup_id(season_id: str, week: int, provider_matchup_id: object) -> str | None:
    if provider_matchup_id is None or str(provider_matchup_id).strip() == "":
        return None
    return _stable_id("clmup", season_id, week, provider_matchup_id)


def _read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required League Source raw file is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True)
class CanonicalOutput:
    path: Path
    value: object


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
        first_raw = item.get("FirstObservedSeason")
        last_raw = item.get("LastObservedSeason")
        first = int(first_raw) if first_raw not in (None, "") else season
        last = int(last_raw) if last_raw not in (None, "") else first
        return first <= season <= last

    def resolve(self, provider: str, external_id: str, season: int) -> str | None:
        key = (provider, external_id)
        active_conflicts = [item for item in self.conflicts.get(key, []) if self._active(item, season)]
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


def _player_ref(resolver: PlayerMappingResolver, provider_player_id: object, season: int) -> dict | None:
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
    resolver: PlayerMappingResolver,
    values: object,
    season: int,
    source_label: str,
) -> list[dict]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{source_label} must be an array")
    result: list[dict] = []
    seen: set[str] = set()
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


def _resolve_member(member_by_provider: dict[str, str], value: object, source: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    provider_id = str(value).strip()
    canonical = member_by_provider.get(provider_id)
    if canonical is None:
        raise ValueError(f"{source} references unknown Sleeper user_id {provider_id}")
    return canonical


def _resolve_roster(roster_by_provider: dict[str, str], value: object, source: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    provider_id = str(value).strip()
    canonical = roster_by_provider.get(provider_id)
    if canonical is None:
        raise ValueError(f"{source} references unknown Sleeper roster_id {provider_id}")
    return canonical


def _members_and_rosters(
    canonical_league_id: str,
    season_id: str,
    members_raw: object,
    rosters_raw: object,
    resolver: PlayerMappingResolver,
    season: int,
) -> tuple[list[dict], list[dict], dict[str, str], dict[str, str]]:
    if not isinstance(members_raw, list) or not isinstance(rosters_raw, list):
        raise ValueError("Sleeper members and rosters raw datasets must be arrays")

    member_by_provider: dict[str, str] = {}
    members: list[dict] = []
    for item in members_raw:
        if not isinstance(item, dict):
            raise ValueError("Sleeper member entries must be objects")
        provider_user_id = str(item.get("user_id") or "").strip()
        if not provider_user_id:
            raise ValueError("Sleeper member user_id is required")
        if provider_user_id in member_by_provider:
            raise ValueError(f"Duplicate Sleeper member user_id: {provider_user_id}")
        canonical_id = canonical_member_id(canonical_league_id, provider_user_id)
        member_by_provider[provider_user_id] = canonical_id
        members.append(
            {
                "CanonicalLeagueMemberID": canonical_id,
                "DisplayName": item.get("display_name"),
                "Avatar": item.get("avatar"),
                "IsOwner": bool(item.get("is_owner", False)),
                "Metadata": item.get("metadata") or {},
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderUserID": provider_user_id}],
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
                f"Sleeper roster {provider_roster_id} owner_id does not resolve to one league member: "
                f"{provider_owner_id or '<missing>'}"
            )
        if provider_owner_id in owner_claims:
            raise ValueError(f"Sleeper member owns multiple rosters: {provider_owner_id}")
        owner_claims.add(provider_owner_id)
        canonical_id = canonical_roster_id(season_id, provider_roster_id)
        roster_by_provider[provider_roster_id] = canonical_id
        rosters.append(
            {
                "CanonicalLeagueRosterID": canonical_id,
                "CanonicalLeagueMemberID": member_by_provider[provider_owner_id],
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": provider_roster_id}],
                "ProviderOwnerUserID": provider_owner_id,
                "Settings": item.get("settings") or {},
                "Metadata": item.get("metadata") or {},
                "Players": _player_refs(resolver, item.get("players") or [], season, "roster.players"),
                "Reserve": _player_refs(resolver, item.get("reserve") or [], season, "roster.reserve"),
                "Taxi": _player_refs(resolver, item.get("taxi") or [], season, "roster.taxi"),
                "Starters": _player_refs(resolver, item.get("starters") or [], season, "roster.starters"),
            }
        )
    members.sort(key=lambda item: item["CanonicalLeagueMemberID"])
    rosters.sort(key=lambda item: item["CanonicalLeagueRosterID"])
    return members, rosters, member_by_provider, roster_by_provider


def _canonicalize_bracket(raw: object, roster_by_provider: dict[str, str], label: str) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"Sleeper {label} bracket must be an array")
    result: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"Sleeper {label} bracket entries must be objects")
        try:
            round_no = int(item["r"])
            match_no = int(item["m"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Sleeper {label} bracket requires numeric r and m") from exc
        key = (round_no, match_no)
        if round_no < 1 or match_no < 1 or key in seen:
            raise ValueError(f"Invalid or duplicate Sleeper {label} bracket match: {key}")
        seen.add(key)
        result.append(
            {
                "Round": round_no,
                "Match": match_no,
                "Team1CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("t1"), f"{label}.t1"),
                "Team2CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("t2"), f"{label}.t2"),
                "WinnerCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("w"), f"{label}.w"),
                "LoserCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("l"), f"{label}.l"),
                "Placement": item.get("p"),
            }
        )
    result.sort(key=lambda item: (item["Round"], item["Match"]))
    return result


def _points_entries(
    resolver: PlayerMappingResolver,
    raw_points: object,
    raw_players: object,
    season: int,
    label: str,
) -> list[dict]:
    if raw_points is None:
        return []
    result: list[dict] = []
    if isinstance(raw_points, dict):
        for provider_player_id in sorted(raw_points, key=str):
            ref = _player_ref(resolver, provider_player_id, season)
            if ref is not None:
                result.append({"Player": ref, "Points": raw_points[provider_player_id]})
        return result
    if isinstance(raw_points, list):
        if not isinstance(raw_players, list):
            raise ValueError(f"{label} parallel player list must be an array")
        if len(raw_points) != len(raw_players):
            raise ValueError(f"{label} length does not match parallel player list")
        for provider_player_id, points in zip(raw_players, raw_points):
            ref = _player_ref(resolver, provider_player_id, season)
            if ref is not None:
                result.append({"Player": ref, "Points": points})
        return result
    raise ValueError(f"{label} must be an object or array")


def _canonicalize_matchups(
    raw: object,
    season_id: str,
    roster_by_provider: dict[str, str],
    resolver: PlayerMappingResolver,
    season: int,
    week: int,
) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"Sleeper matchup week {week} must be an array")
    result: list[dict] = []
    seen_rosters: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"Sleeper matchup week {week} entries must be objects")
        provider_roster_id = str(item.get("roster_id") or "").strip()
        if not provider_roster_id:
            raise ValueError(f"Sleeper matchup week {week} roster_id is required")
        if provider_roster_id in seen_rosters:
            raise ValueError(f"Duplicate Sleeper matchup roster_id {provider_roster_id} in week {week}")
        seen_rosters.add(provider_roster_id)
        provider_matchup_id = item.get("matchup_id")
        result.append(
            {
                "CanonicalLeagueMatchupID": canonical_matchup_id(season_id, week, provider_matchup_id),
                "CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, provider_roster_id, f"matchups.week-{week}.roster_id"),
                "Week": week,
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderMatchupID": provider_matchup_id, "ProviderRosterID": provider_roster_id}],
                "Points": item.get("points"),
                "CustomPoints": item.get("custom_points"),
                "Players": _player_refs(resolver, item.get("players") or [], season, f"matchups.week-{week}.players"),
                "Starters": _player_refs(resolver, item.get("starters") or [], season, f"matchups.week-{week}.starters"),
                "PlayerPoints": _points_entries(resolver, item.get("players_points"), item.get("players") or [], season, f"matchups.week-{week}.players_points"),
                "StarterPoints": _points_entries(resolver, item.get("starters_points"), item.get("starters") or [], season, f"matchups.week-{week}.starters_points"),
            }
        )
    result.sort(key=lambda item: item["CanonicalLeagueRosterID"])
    return result


def _player_roster_moves(
    resolver: PlayerMappingResolver,
    raw: object,
    roster_by_provider: dict[str, str],
    season: int,
    label: str,
) -> list[dict]:
    if raw in (None, {}):
        return []
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    result: list[dict] = []
    for provider_player_id in sorted(raw, key=str):
        ref = _player_ref(resolver, provider_player_id, season)
        if ref is not None:
            result.append(
                {
                    "Player": ref,
                    "CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, raw[provider_player_id], f"{label}.{provider_player_id}"),
                }
            )
    return result


def _canonicalize_transaction_draft_picks(raw: object, roster_by_provider: dict[str, str], label: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    result: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        result.append(
            {
                "Season": item.get("season"),
                "Round": item.get("round"),
                "OriginalCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("roster_id"), f"{label}[{index}].roster_id"),
                "PreviousOwnerCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("previous_owner_id"), f"{label}[{index}].previous_owner_id"),
                "OwnerCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("owner_id"), f"{label}[{index}].owner_id"),
            }
        )
    return result


def _canonicalize_transactions(
    raw: object,
    season_id: str,
    member_by_provider: dict[str, str],
    roster_by_provider: dict[str, str],
    resolver: PlayerMappingResolver,
    season: int,
    week: int,
) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"Sleeper transaction week {week} must be an array")
    result: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"Sleeper transaction week {week} entries must be objects")
        provider_transaction_id = str(item.get("transaction_id") or "").strip()
        if not provider_transaction_id:
            raise ValueError(f"Sleeper transaction week {week} transaction_id is required")
        if provider_transaction_id in seen:
            raise ValueError(f"Duplicate Sleeper transaction_id {provider_transaction_id} in week {week}")
        seen.add(provider_transaction_id)
        provider_leg = item.get("leg")
        if provider_leg not in (None, "") and int(provider_leg) != week:
            raise ValueError(f"Sleeper transaction {provider_transaction_id} leg {provider_leg} does not match endpoint week {week}")
        creator_provider_id = str(item.get("creator") or "").strip() or None
        roster_values = item.get("roster_ids") or []
        if not isinstance(roster_values, list):
            raise ValueError(f"Sleeper transaction {provider_transaction_id} roster_ids must be an array")
        result.append(
            {
                "CanonicalLeagueTransactionID": canonical_transaction_id(season_id, provider_transaction_id),
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderTransactionID": provider_transaction_id}],
                "Type": item.get("type"),
                "Status": item.get("status"),
                "Week": week,
                "CreatedAt": item.get("created"),
                "CreatorCanonicalLeagueMemberID": member_by_provider.get(creator_provider_id) if creator_provider_id else None,
                "CreatorProviderUserID": creator_provider_id,
                "CanonicalLeagueRosterIDs": [_resolve_roster(roster_by_provider, value, f"transaction.{provider_transaction_id}.roster_ids") for value in roster_values],
                "Adds": _player_roster_moves(resolver, item.get("adds"), roster_by_provider, season, f"transaction.{provider_transaction_id}.adds"),
                "Drops": _player_roster_moves(resolver, item.get("drops"), roster_by_provider, season, f"transaction.{provider_transaction_id}.drops"),
                "DraftPicks": _canonicalize_transaction_draft_picks(item.get("draft_picks"), roster_by_provider, f"transaction.{provider_transaction_id}.draft_picks"),
                "Metadata": item.get("metadata") or {},
            }
        )
    result.sort(key=lambda item: item["CanonicalLeagueTransactionID"])
    return result


def _canonicalize_drafts(
    raw_base: Path,
    draft_index_raw: object,
    season_id: str,
    member_by_provider: dict[str, str],
    roster_by_provider: dict[str, str],
    resolver: PlayerMappingResolver,
    season: int,
) -> list[dict]:
    if not isinstance(draft_index_raw, list):
        raise ValueError("Sleeper league drafts index must be an array")
    result: list[dict] = []
    seen_drafts: set[str] = set()
    for index_item in draft_index_raw:
        if not isinstance(index_item, dict):
            raise ValueError("Sleeper league draft index entries must be objects")
        provider_draft_id = str(index_item.get("draft_id") or "").strip()
        if not provider_draft_id or provider_draft_id in seen_drafts:
            raise ValueError(f"Missing or duplicate Sleeper draft_id: {provider_draft_id!r}")
        seen_drafts.add(provider_draft_id)
        draft_dir = raw_base / "drafts" / provider_draft_id
        detail = _read_json(draft_dir / "draft.json")
        picks = _read_json(draft_dir / "picks.json")
        traded = _read_json(draft_dir / "traded-picks.json")
        if not isinstance(detail, dict):
            raise ValueError(f"Sleeper draft detail {provider_draft_id} must be an object")
        if str(detail.get("draft_id") or "").strip() != provider_draft_id:
            raise ValueError(f"Sleeper draft detail id mismatch for {provider_draft_id}")
        detail_season = detail.get("season")
        if detail_season not in (None, "") and int(detail_season) != season:
            raise ValueError(f"Sleeper draft {provider_draft_id} season does not match league season {season}")
        if not isinstance(picks, list) or not isinstance(traded, list):
            raise ValueError(f"Sleeper draft picks/traded-picks for {provider_draft_id} must be arrays")

        draft_order_raw = detail.get("draft_order") or {}
        if not isinstance(draft_order_raw, dict):
            raise ValueError(f"Sleeper draft {provider_draft_id} draft_order must be an object")
        draft_order = [
            {"CanonicalLeagueMemberID": _resolve_member(member_by_provider, provider_user_id, f"draft.{provider_draft_id}.draft_order"), "Slot": slot}
            for provider_user_id, slot in sorted(draft_order_raw.items(), key=lambda pair: str(pair[0]))
        ]

        slot_to_roster_raw = detail.get("slot_to_roster_id") or {}
        if not isinstance(slot_to_roster_raw, dict):
            raise ValueError(f"Sleeper draft {provider_draft_id} slot_to_roster_id must be an object")
        slot_to_roster = [
            {"Slot": slot, "CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, provider_roster_id, f"draft.{provider_draft_id}.slot_to_roster_id")}
            for slot, provider_roster_id in sorted(slot_to_roster_raw.items(), key=lambda pair: str(pair[0]))
        ]

        canonical_picks: list[dict] = []
        seen_pick_no: set[int] = set()
        for pick in picks:
            if not isinstance(pick, dict):
                raise ValueError(f"Sleeper draft {provider_draft_id} pick entries must be objects")
            try:
                pick_no = int(pick.get("pick_no"))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Sleeper draft {provider_draft_id} pick_no is invalid") from exc
            if pick_no < 1 or pick_no in seen_pick_no:
                raise ValueError(f"Invalid or duplicate pick_no {pick_no} for draft {provider_draft_id}")
            seen_pick_no.add(pick_no)
            canonical_picks.append(
                {
                    "PickNo": pick_no,
                    "Player": _player_ref(resolver, pick.get("player_id"), season),
                    "CanonicalLeagueRosterID": _resolve_roster(roster_by_provider, pick.get("roster_id"), f"draft.{provider_draft_id}.pick.{pick_no}.roster_id"),
                    "PickedByCanonicalLeagueMemberID": _resolve_member(member_by_provider, pick.get("picked_by"), f"draft.{provider_draft_id}.pick.{pick_no}.picked_by"),
                    "Metadata": pick.get("metadata") or {},
                }
            )
        canonical_picks.sort(key=lambda item: item["PickNo"])

        canonical_traded: list[dict] = []
        for traded_index, item in enumerate(traded):
            if not isinstance(item, dict):
                raise ValueError(f"Sleeper draft {provider_draft_id} traded-pick entries must be objects")
            canonical_traded.append(
                {
                    "Season": item.get("season"),
                    "Round": item.get("round"),
                    "OriginalCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("roster_id"), f"draft.{provider_draft_id}.traded[{traded_index}].roster_id"),
                    "PreviousOwnerCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("previous_owner_id"), f"draft.{provider_draft_id}.traded[{traded_index}].previous_owner_id"),
                    "OwnerCanonicalLeagueRosterID": _resolve_roster(roster_by_provider, item.get("owner_id"), f"draft.{provider_draft_id}.traded[{traded_index}].owner_id"),
                }
            )

        result.append(
            {
                "CanonicalLeagueDraftID": canonical_draft_id(season_id, provider_draft_id),
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderDraftID": provider_draft_id}],
                "Season": season,
                "Status": detail.get("status"),
                "Type": detail.get("type"),
                "StartTime": detail.get("start_time"),
                "Settings": detail.get("settings") or {},
                "Metadata": detail.get("metadata") or {},
                "DraftOrder": draft_order,
                "SlotToRoster": slot_to_roster,
                "Picks": canonical_picks,
                "TradedPicks": canonical_traded,
            }
        )
    result.sort(key=lambda item: item["CanonicalLeagueDraftID"])
    return result


def _manifest(repo_root: Path, canonical_league_id: str) -> dict:
    path = repo_root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"League manifest must be an object: {path}")
    if str(raw.get("CanonicalLeagueID") or "") != canonical_league_id:
        raise ValueError(f"League manifest CanonicalLeagueID mismatch: {path}")
    if str(raw.get("Provider") or "") != "Sleeper":
        raise ValueError("Canonical League materializer currently supports Sleeper only")
    seasons = raw.get("Seasons")
    if not isinstance(seasons, list) or not seasons:
        raise ValueError(f"League manifest Seasons must be a non-empty array: {path}")
    return raw


def _registry_guard(registry: Iterable[LeagueDataset]) -> None:
    ids = {item.id for item in registry}
    missing = REQUIRED_DATASET_IDS - ids
    if missing:
        raise ValueError(f"League registry is missing required canonical inputs: {sorted(missing)}")


def plan_canonical_materialization(
    repo_root: Path,
    canonical_league_id: str,
    registry: Iterable[LeagueDataset],
    resolver: PlayerMappingResolver,
) -> list[CanonicalOutput]:
    _registry_guard(registry)
    manifest = _manifest(repo_root, canonical_league_id)
    contexts: list[dict[str, Any]] = []
    seen_seasons: set[int] = set()

    for season_entry in sorted(manifest["Seasons"], key=lambda item: int(item["Season"])):
        if not isinstance(season_entry, dict):
            raise ValueError("League manifest season entries must be objects")
        season = int(season_entry["Season"])
        if season in seen_seasons:
            raise ValueError(f"Duplicate season {season} in league manifest")
        seen_seasons.add(season)
        season_id = str(season_entry.get("CanonicalLeagueSeasonID") or "")
        expected_season_id = canonical_league_season_id(canonical_league_id, season)
        if season_id != expected_season_id:
            raise ValueError(
                f"CanonicalLeagueSeasonID mismatch for {canonical_league_id}/{season}: "
                f"{season_id or '<missing>'} != {expected_season_id}"
            )
        mappings = season_entry.get("ProviderMappings")
        if not isinstance(mappings, list):
            raise ValueError(f"ProviderMappings must be an array for season {season}")
        sleeper = [mapping for mapping in mappings if isinstance(mapping, dict) and mapping.get("Provider") == "Sleeper"]
        if len(sleeper) != 1:
            raise ValueError(f"Expected exactly one Sleeper mapping for {canonical_league_id}/{season}")
        provider_mapping = sleeper[0]
        provider_league_id = str(provider_mapping.get("ProviderLeagueID") or "").strip()
        if not provider_league_id:
            raise ValueError(f"Sleeper ProviderLeagueID is required for {canonical_league_id}/{season}")
        raw_base = repo_root / "source-data" / "providers" / "sleeper" / "leagues" / provider_league_id
        league_raw = _read_json(raw_base / "league.json")
        members_raw = _read_json(raw_base / "members.json")
        rosters_raw = _read_json(raw_base / "rosters.json")
        winners_raw = _read_json(raw_base / "winners-bracket.json")
        losers_raw = _read_json(raw_base / "losers-bracket.json")
        draft_index_raw = _read_json(raw_base / "drafts" / "index.json")
        if not isinstance(league_raw, dict):
            raise ValueError(f"Sleeper league raw must be an object for {provider_league_id}")
        if str(league_raw.get("league_id") or "") != provider_league_id:
            raise ValueError(f"Sleeper league raw id mismatch for {provider_league_id}")
        if int(league_raw.get("season")) != season:
            raise ValueError(f"Sleeper league raw season mismatch for {provider_league_id}")

        week_ceiling = resolve_nfl_regular_season_week_ceiling(repo_root, season)
        matchup_by_week = {week: _read_json(raw_base / "matchups" / f"week-{week}.json") for week in range(1, week_ceiling + 1)}
        transaction_by_week = {week: _read_json(raw_base / "transactions" / f"week-{week}.json") for week in range(1, week_ceiling + 1)}
        contexts.append(
            {
                "Season": season,
                "SeasonID": season_id,
                "SeasonEntry": season_entry,
                "ProviderMapping": provider_mapping,
                "ProviderLeagueID": provider_league_id,
                "RawBase": raw_base,
                "LeagueRaw": league_raw,
                "MembersRaw": members_raw,
                "RostersRaw": rosters_raw,
                "WinnersRaw": winners_raw,
                "LosersRaw": losers_raw,
                "DraftIndexRaw": draft_index_raw,
                "WeekCeiling": week_ceiling,
                "MatchupByWeek": matchup_by_week,
                "TransactionByWeek": transaction_by_week,
            }
        )

    structures = derive_season_week_structures(
        [(context["LeagueRaw"], context["WinnersRaw"], context["MatchupByWeek"], context["WeekCeiling"]) for context in contexts]
    )
    structure_by_season = {int(item["Season"]): item for item in structures}
    if set(structure_by_season) != seen_seasons:
        raise ValueError("WeekStructure seasons do not match league manifest seasons")

    outputs: list[CanonicalOutput] = []
    seen_paths: set[Path] = set()
    for context in contexts:
        season = context["Season"]
        season_id = context["SeasonID"]
        season_entry = context["SeasonEntry"]
        provider_mapping = context["ProviderMapping"]
        league_raw = context["LeagueRaw"]
        season_root = repo_root / "source-data" / "leagues" / canonical_league_id / "seasons" / str(season)

        members, rosters, member_by_provider, roster_by_provider = _members_and_rosters(
            canonical_league_id, season_id, context["MembersRaw"], context["RostersRaw"], resolver, season
        )
        winners = _canonicalize_bracket(context["WinnersRaw"], roster_by_provider, "winners")
        losers = _canonicalize_bracket(context["LosersRaw"], roster_by_provider, "losers")
        drafts = _canonicalize_drafts(
            context["RawBase"], context["DraftIndexRaw"], season_id, member_by_provider, roster_by_provider, resolver, season
        )

        league = {
            "schemaVersion": SCHEMA_VERSION,
            "CanonicalLeagueID": canonical_league_id,
            "CanonicalLeagueSeasonID": season_id,
            "PreviousCanonicalLeagueSeasonID": season_entry.get("PreviousCanonicalLeagueSeasonID"),
            "Season": season,
            "Name": league_raw.get("name"),
            "Status": league_raw.get("status"),
            "SeasonType": league_raw.get("season_type"),
            "Avatar": league_raw.get("avatar"),
            "Settings": league_raw.get("settings") or {},
            "ScoringSettings": league_raw.get("scoring_settings") or {},
            "RosterPositions": league_raw.get("roster_positions") or [],
            "WeekStructure": structure_by_season[season],
            "ProviderMappings": season_entry.get("ProviderMappings") or [],
            "ProviderLineageEvidence": {"PreviousProviderLeagueID": provider_mapping.get("PreviousProviderLeagueID")},
        }

        season_outputs = [
            CanonicalOutput(season_root / "league.json", league),
            CanonicalOutput(season_root / "members.json", members),
            CanonicalOutput(season_root / "rosters.json", rosters),
            CanonicalOutput(season_root / "winners-bracket.json", winners),
            CanonicalOutput(season_root / "losers-bracket.json", losers),
            CanonicalOutput(season_root / "drafts.json", drafts),
        ]
        for week in range(1, context["WeekCeiling"] + 1):
            season_outputs.append(
                CanonicalOutput(
                    season_root / "matchups" / f"week-{week}.json",
                    _canonicalize_matchups(context["MatchupByWeek"][week], season_id, roster_by_provider, resolver, season, week),
                )
            )
            season_outputs.append(
                CanonicalOutput(
                    season_root / "transactions" / f"week-{week}.json",
                    _canonicalize_transactions(context["TransactionByWeek"][week], season_id, member_by_provider, roster_by_provider, resolver, season, week),
                )
            )
        for output in season_outputs:
            if output.path in seen_paths:
                raise ValueError(f"Canonical League output path collision: {output.path}")
            seen_paths.add(output.path)
            outputs.append(output)

    return sorted(outputs, key=lambda output: str(output.path))


def persist_canonical_outputs(outputs: Iterable[CanonicalOutput]) -> dict[str, int]:
    values = list(outputs)
    changed = sum(write_json_if_changed(output.path, output.value) for output in values)
    return {"CanonicalFiles": len(values), "CanonicalFilesChanged": changed}
