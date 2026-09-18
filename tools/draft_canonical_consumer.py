#!/usr/bin/env python3
"""Adapt canonical League draft data to the legacy Sleeper-shaped consumer contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Required canonical draft dependency missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def sleeper_mapping(item: dict[str, Any], value_key: str, label: str) -> str:
    mappings = item.get("ProviderMappings")
    if not isinstance(mappings, list):
        raise ValueError(f"{label} ProviderMappings must be an array")
    matches = [m for m in mappings if isinstance(m, dict) and m.get("Provider") == "Sleeper" and str(m.get(value_key) or "").strip()]
    if len(matches) != 1:
        raise ValueError(f"{label} must contain exactly one Sleeper {value_key}; found {len(matches)}")
    return str(matches[0][value_key])

def build_provider_lookup(items: Any, canonical_key: str, provider_key: str, label: str) -> dict[str, str]:
    if not isinstance(items, list):
        raise ValueError(f"{label} must be an array")
    result, reverse = {}, {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        canonical_id = str(item.get(canonical_key) or "").strip()
        if not canonical_id:
            raise ValueError(f"{label}[{index}] missing {canonical_key}")
        if canonical_id in result:
            raise ValueError(f"Duplicate {canonical_key} in {label}: {canonical_id}")
        provider_id = sleeper_mapping(item, provider_key, f"{label}[{index}]")
        if provider_id in reverse:
            raise ValueError(f"Duplicate Sleeper {provider_key} in {label}: {provider_id}")
        result[canonical_id] = provider_id
        reverse[provider_id] = canonical_id
    return result

def require_lookup(lookup: dict[str, str], key: Any, label: str) -> str:
    value = str(key or "").strip()
    if not value:
        raise ValueError(f"{label} canonical id is missing")
    if value not in lookup:
        raise ValueError(f"{label} canonical id is not mapped to Sleeper: {value}")
    return lookup[value]

def player_sleeper_id(player: Any, label: str) -> str | None:
    if player is None:
        return None
    if not isinstance(player, dict):
        raise ValueError(f"{label} Player must be an object or null")
    return sleeper_mapping(player, "ProviderPlayerID", f"{label}.Player")

def build_legacy_payload(repo_root: Path, canonical_league_id: str, season: str) -> dict[str, Any]:
    season_dir = repo_root / "source-data" / "leagues" / canonical_league_id / "seasons" / str(season)
    drafts = load_json(season_dir / "drafts.json")
    rosters = load_json(season_dir / "rosters.json")
    members = load_json(season_dir / "members.json")
    roster_provider = build_provider_lookup(rosters, "CanonicalLeagueRosterID", "ProviderRosterID", f"{canonical_league_id}/{season} rosters")
    member_provider = build_provider_lookup(members, "CanonicalLeagueMemberID", "ProviderUserID", f"{canonical_league_id}/{season} members")
    if not isinstance(drafts, list):
        raise ValueError(f"{canonical_league_id}/{season} drafts.json must be an array")
    legacy_drafts, picks_by_draft, traded_by_draft = [], {}, {}
    seen_draft_ids: set[str] = set()
    for draft_index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            raise ValueError(f"drafts[{draft_index}] must be an object")
        label = f"{canonical_league_id}/{season} drafts[{draft_index}]"
        draft_id = sleeper_mapping(draft, "ProviderDraftID", label)
        if draft_id in seen_draft_ids:
            raise ValueError(f"Duplicate Sleeper ProviderDraftID: {draft_id}")
        seen_draft_ids.add(draft_id)
        canonical_season = str(draft.get("Season") or "").strip()
        if canonical_season != str(season):
            raise ValueError(f"{label} Season '{canonical_season}' does not match requested season '{season}'")
        draft_order = {}
        for i, entry in enumerate(draft.get("DraftOrder") or []):
            provider_user_id = require_lookup(member_provider, entry.get("CanonicalLeagueMemberID"), f"{label}.DraftOrder[{i}]")
            if provider_user_id in draft_order:
                raise ValueError(f"{label} duplicate draft-order user {provider_user_id}")
            draft_order[provider_user_id] = int(entry["Slot"])
        slot_to_roster_id = {}
        for i, entry in enumerate(draft.get("SlotToRoster") or []):
            slot = str(entry.get("Slot") or "").strip()
            if not slot:
                raise ValueError(f"{label}.SlotToRoster[{i}] missing Slot")
            if slot in slot_to_roster_id:
                raise ValueError(f"{label} duplicate slot-to-roster slot {slot}")
            slot_to_roster_id[slot] = int(require_lookup(roster_provider, entry.get("CanonicalLeagueRosterID"), f"{label}.SlotToRoster[{i}]"))
        start_time = draft.get("StartTime")
        legacy_drafts.append({
            "draft_id": draft_id, "season": canonical_season, "type": draft.get("Type"),
            "status": draft.get("Status"), "start_time": start_time, "created": start_time,
            "settings": draft.get("Settings") or {}, "metadata": draft.get("Metadata") or {},
            "draft_order": draft_order, "slot_to_roster_id": slot_to_roster_id,
        })
        picks = []
        for i, pick in enumerate(draft.get("Picks") or []):
            label_pick = f"{label}.Picks[{i}]"
            picks.append({
                "draft_id": draft_id, "pick_no": int(pick["PickNo"]),
                "player_id": player_sleeper_id(pick.get("Player"), label_pick),
                "roster_id": int(require_lookup(roster_provider, pick.get("CanonicalLeagueRosterID"), label_pick)),
                "picked_by": require_lookup(member_provider, pick.get("PickedByCanonicalLeagueMemberID"), label_pick),
                "metadata": pick.get("Metadata") or {},
            })
        picks.sort(key=lambda item: int(item["pick_no"]))
        picks_by_draft[draft_id] = picks
        traded = []
        for i, trade in enumerate(draft.get("TradedPicks") or []):
            label_trade = f"{label}.TradedPicks[{i}]"
            traded.append({
                "season": str(trade.get("Season") or ""), "round": int(trade["Round"]),
                "roster_id": int(require_lookup(roster_provider, trade.get("OriginalCanonicalLeagueRosterID"), label_trade)),
                "previous_owner_id": int(require_lookup(roster_provider, trade.get("PreviousOwnerCanonicalLeagueRosterID"), label_trade)),
                "owner_id": int(require_lookup(roster_provider, trade.get("OwnerCanonicalLeagueRosterID"), label_trade)),
            })
        traded.sort(key=lambda item: (item["season"], item["round"], item["roster_id"], item["previous_owner_id"], item["owner_id"]))
        traded_by_draft[draft_id] = traded
    legacy_drafts.sort(key=lambda item: (int(item["created"] or 0), str(item["draft_id"])))
    return {"CanonicalLeagueID": canonical_league_id, "Season": str(season), "Drafts": legacy_drafts, "PicksByDraftID": picks_by_draft, "TradedPicksByDraftID": traded_by_draft}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--canonical-league-id", required=True)
    parser.add_argument("--season", required=True)
    args = parser.parse_args()
    print(json.dumps(build_legacy_payload(args.repo_root.resolve(), args.canonical_league_id, str(args.season)), separators=(",", ":"), ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
