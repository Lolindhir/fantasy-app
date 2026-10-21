"""LeagueDrafts: drafts of every season from definitions, order, trades and pick results (league-history.yaml, ADR-057).

Faithful port of DraftOrderAwareUtils.psm1 (current and open drafts, completed draft history),
DraftUtils.psm1 (Get-AppliedDraftPickTrades, order resolution, status), DraftPickResultUtils.psm1
(Get-AppliedDraftPickResults) and DraftHistoryEmptyDefinitionsFix.psm1 (Add-DraftHistoryTradeHistorySafe).
The output carries only technical fields; Display* fields and the pick LeagueID are consumer concerns.

Pure functions: no file access and no clock. Dates are derived from provider timestamps only.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from .league_draft_identity import (
    DraftIdentityError,
    assert_draft_type_configs,
    completed_draft_definitions,
    draft_code,
    draft_instance,
    draft_key,
    is_complete,
    pick_key,
    provider_draft_map,
    ps_string,
    sorted_configs,
    configured_rounds_from_provider_draft,
)


class DraftBuildError(ValueError):
    """Raised when a draft cannot be built consistently (fail closed)."""


GUARD_LIMIT = 30


# --------------------------------------------------------------------------- small helpers


def _sort_key_tx(entry: dict[str, Any]) -> tuple[int, str]:
    # Effective chronology controls pick ownership transfers, not submission order.
    return (int(entry.get("EffectiveAt") or entry["CreatedAt"]), ps_string(entry["TransactionID"]).casefold())


def draft_status(provider_draft: dict[str, Any] | None) -> str:
    if provider_draft is None:
        return "Virtual"
    status = ps_string(provider_draft.get("status"))
    return {"complete": "Complete", "drafting": "Drafting", "pre_draft": "PreDraft"}.get(status, status)


def draft_type_setting(provider_draft: dict[str, Any] | None) -> str:
    if provider_draft is None:
        return "linear"
    value = provider_draft.get("type")
    if value is None or not ps_string(value).strip():
        return "linear"
    return ps_string(value)


def round_owner_order(base: list[int], round_no: int, type_setting: str) -> list[int]:
    order = list(base)
    if type_setting.strip().lower() == "snake" and round_no % 2 == 0:
        order.reverse()
    return order


def order_from_provider_draft(provider_draft: dict[str, Any]) -> list[int]:
    """Get-DraftOrderRosterIDsFromSleeperDraft: slots numerically ascending, roster IDs above zero."""
    slot_map = provider_draft.get("slot_to_roster_id")
    if not slot_map:
        return []
    return [int(slot_map[slot]) for slot in sorted(slot_map, key=lambda value: int(value)) if int(slot_map[slot]) > 0]


def _start_time_fields(provider_draft: dict[str, Any] | None) -> tuple[int | None, str | None]:
    if provider_draft is None:
        return None, None
    raw = provider_draft.get("start_time")
    if raw is None or ps_string(raw) == "":
        return None, None
    millis = int(raw)
    if millis <= 0:
        return millis, None
    moment = datetime.fromtimestamp(millis // 1000, tz=timezone.utc)
    # .NET DateTime "o": seven fractional digits (100 ns ticks) and a Z suffix.
    return millis, moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{(millis % 1000) * 10000:07d}Z"


# --------------------------------------------------------------------------- definitions


def current_and_open_definitions(
    configs: list[dict[str, Any]],
    draft_map: dict[str, dict[str, Any]],
    league_year: int,
    open_count: int,
    provider_league_id: str,
) -> list[dict[str, Any]]:
    """Get-CurrentAndOpenDraftDefinitionsOrderAware."""
    assert_draft_type_configs(configs)
    definitions: list[dict[str, Any]] = []
    for config in sorted_configs(configs):
        open_found, season, guard = 0, league_year, 0
        while open_found < open_count:
            guard += 1
            if guard > GUARD_LIMIT:
                raise DraftBuildError(f"Draft generation guard reached for draft type '{config['DraftType']}'.")
            draft_type = str(config["DraftType"])
            instance = draft_instance(config)
            key = draft_key(str(season), draft_type, instance)
            provider = draft_map.get(key)
            complete = is_complete(provider)
            if season == league_year or not complete:
                definitions.append({
                    "ProviderLeagueID": provider_league_id,
                    "Season": str(season),
                    "DraftType": draft_type,
                    "DraftInstance": instance,
                    "DraftCode": draft_code(draft_type, instance),
                    "DraftNo": int(config["DraftNo"]),
                    "DraftKey": key,
                    "DraftTypeConfig": config,
                    "ProviderDraft": provider,
                    "Path": "current",
                })
            if not complete:
                open_found += 1
            season += 1
    return sorted(definitions, key=lambda item: (int(item["Season"]), item["DraftNo"]))


def merge_definitions(current: list[dict[str, Any]], history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union by DraftKey; the current/bound definition wins. Conflicting provider bindings fail closed."""
    by_key: dict[str, dict[str, Any]] = {item["DraftKey"]: item for item in current}
    draft_ids: dict[str, str] = {}
    for item in current:
        if item["ProviderDraft"] is not None:
            draft_ids[ps_string(item["ProviderDraft"].get("draft_id"))] = item["DraftKey"]
    for item in history:
        key = item["DraftKey"]
        draft_id = ps_string(item["ProviderDraft"].get("draft_id"))
        owner_key = draft_ids.get(draft_id)
        if owner_key is not None and owner_key != key:
            raise DraftBuildError(f"Provider draft '{draft_id}' is defined as '{owner_key}' and as '{key}'.")
        existing = by_key.get(key)
        if existing is not None:
            bound = existing["ProviderDraft"]
            if bound is None or ps_string(bound.get("draft_id")) != draft_id:
                raise DraftBuildError(f"DraftKey '{key}' resolves to different provider drafts (current vs history).")
            continue
        by_key[key] = {**item, "Path": "history"}
        draft_ids[draft_id] = key
    return sorted(by_key.values(), key=lambda item: (int(item["Season"]), item["DraftNo"], item["DraftKey"]))


# --------------------------------------------------------------------------- order and picks


def _standing_by_season(standings: list[dict[str, Any]], season: str) -> dict[str, Any] | None:
    matches = [item for item in standings if ps_string(item.get("Season")) == season]
    if len(matches) > 1:
        raise DraftBuildError(f"Duplicate standing identity for season '{season}'. Expected at most one standing record, found {len(matches)}.")
    return matches[0] if matches else None


def configured_order_roster_ids(config: dict[str, Any], season: str, standings: list[dict[str, Any]]) -> list[int]:
    """Get-DraftOrderRosterIDs (transitional Standings input until Issue #987)."""
    order_source = ps_string(config.get("OrderSource"))
    if order_source == "PreviousPlayoffs":
        source_season = str(int(season) - 1)
        standing = _standing_by_season(standings, source_season)
    elif order_source == "AllTime":
        source_season = season
        standing = _standing_by_season(standings, "AllTime")
    else:
        raise DraftBuildError(f"Unsupported draft order source '{order_source}' for draft type '{config.get('DraftType')}'.")
    ranking = list((standing or {}).get("Playoffs") or [])
    if not ranking:
        raise DraftBuildError(f"No ranking data found for order source '{order_source}' and source season '{source_season}'.")
    order_map = config.get("OrderMap")
    if order_map is not None:
        mapped = [row for row in ranking if ps_string(row.get("Place")) in {ps_string(k) for k in order_map}]
        lookup = {ps_string(k): int(v) for k, v in order_map.items()}
        mapped.sort(key=lambda row: lookup[ps_string(row["Place"])])
        return [int(row["TeamID"]) for row in mapped]
    descending = ps_string(config.get("Order") or "Ascending") == "Descending"
    return [int(row["TeamID"]) for row in sorted(ranking, key=lambda row: float(row["Place"]), reverse=descending)]


def projected_picks(
    key: str, season: str, draft_type: str, instance: int, code: str,
    rounds: int, team_ids: list[int], exact: bool, type_setting: str,
) -> list[dict[str, Any]]:
    """New-ProjectedDraftPicksOrderAware (without LeagueID and DisplayPick)."""
    picks: list[dict[str, Any]] = []
    for round_no in range(1, rounds + 1):
        owners = round_owner_order(team_ids, round_no, type_setting) if exact else list(team_ids)
        for index, owner in enumerate(owners):
            position = index + 1 if exact else None
            overall = (round_no - 1) * len(team_ids) + position if exact else None
            picks.append({
                "PickKey": pick_key(key, round_no, owner),
                "DraftKey": key,
                "Season": season,
                "DraftType": draft_type,
                "DraftInstance": instance,
                "DraftCode": code,
                "Round": round_no,
                "PositionInRound": position,
                "OverallPick": overall,
                "OriginalOwnerRosterID": int(owner),
                "CurrentOwnerRosterID": int(owner),
                "WasTraded": False,
                "IsCurrentlyTraded": False,
                "TradeSource": None,
                "TradeHistory": [],
                "PlayerID": None,
                "PlayerName": None,
                "Status": "Open",
                "SleeperPickNo": None,
                "SleeperPickedBy": None,
            })
    return picks


def _history_entry(transaction: dict[str, Any], movement: dict[str, Any]) -> dict[str, Any]:
    return {
        "TransactionID": ps_string(transaction["TransactionID"]),
        "Source": ps_string(transaction.get("Source")),
        "CreatedAt": int(transaction["CreatedAt"]),
        "EffectiveAt": int(transaction.get("EffectiveAt") or transaction["CreatedAt"]),
        "CreatedDate": ps_string(transaction.get("CreatedDate")),
        "DraftSource": ps_string(movement.get("DraftSource")),
        "PreviousOwnerRosterID": int(movement["PreviousOwnerRosterID"]),
        "NewOwnerRosterID": int(movement["NewOwnerRosterID"]),
    }


def apply_pick_trades(picks: list[dict[str, Any]], transactions: list[dict[str, Any]], key: str) -> None:
    """Get-AppliedDraftPickTrades. A movement naming a pick that does not exist fails closed (league-history.yaml)."""
    by_key: dict[str, dict[str, Any]] = {}
    for pick in picks:
        if pick["PickKey"] in by_key:
            raise DraftBuildError(f"Duplicate PickKey '{pick['PickKey']}' in generated picks for draft '{key}'.")
        by_key[pick["PickKey"]] = pick
    movements: list[dict[str, Any]] = []
    for transaction in transactions:
        if ps_string(transaction.get("Status")) != "complete":
            continue
        for movement in transaction.get("DraftPicks") or []:
            if ps_string(movement.get("DraftKey")) != key:
                continue
            if movement.get("OriginalOwnerRosterID") is None:
                raise DraftBuildError(f"Draft pick movement in transaction '{transaction['TransactionID']}' has no OriginalOwnerRosterID.")
            movements.append({
                **_history_entry(transaction, movement),
                "Round": int(movement["Round"]),
                "OriginalOwnerRosterID": int(movement["OriginalOwnerRosterID"]),
            })
    movements.sort(key=_sort_key_tx)
    for movement in movements:
        target_key = pick_key(key, movement["Round"], movement["OriginalOwnerRosterID"])
        target = by_key.get(target_key)
        if target is None:
            raise DraftBuildError(f"Could not find pick '{target_key}' for transaction '{movement['TransactionID']}'.")
        target["CurrentOwnerRosterID"] = movement["NewOwnerRosterID"]
        target["WasTraded"] = True
        target["IsCurrentlyTraded"] = target["CurrentOwnerRosterID"] != target["OriginalOwnerRosterID"]
        target["TradeSource"] = movement["Source"]
        target["TradeHistory"].append({k: movement[k] for k in (
            "TransactionID", "Source", "CreatedAt", "EffectiveAt", "CreatedDate", "DraftSource", "PreviousOwnerRosterID", "NewOwnerRosterID")})
    for pick in picks:
        pick["IsCurrentlyTraded"] = pick["CurrentOwnerRosterID"] != pick["OriginalOwnerRosterID"]


def _player_name(provider_pick: dict[str, Any]) -> str | None:
    metadata = provider_pick.get("metadata")
    if metadata is None:
        return None
    first, last, full = (ps_string(metadata.get(name)) for name in ("first_name", "last_name", "full_name"))
    name = " ".join(part for part in (first, last) if part.strip()).strip()
    if name.strip():
        return name
    if full.strip():
        return full.strip()
    return None


def apply_pick_results(picks: list[dict[str, Any]], provider_picks: list[dict[str, Any]], draft_id: str) -> None:
    """Get-AppliedDraftPickResults. A provider pick that maps to no generated pick fails closed."""
    by_overall = {int(pick["OverallPick"]): pick for pick in picks if pick["OverallPick"] is not None}
    for provider_pick in provider_picks:
        pick_no = provider_pick.get("pick_no")
        if pick_no is None or ps_string(pick_no).strip() == "":
            continue
        overall = int(pick_no)
        target = by_overall.get(overall)
        if target is None:
            raise DraftBuildError(f"Could not map provider pick_no '{overall}' from draft '{draft_id}' to generated draft picks.")
        target["SleeperPickNo"] = overall
        target["SleeperPickedBy"] = ps_string(provider_pick.get("picked_by"))
        roster = provider_pick.get("roster_id")
        if roster is not None and ps_string(roster).strip() != "":
            target["CurrentOwnerRosterID"] = int(roster)
            traded = target["OriginalOwnerRosterID"] != target["CurrentOwnerRosterID"]
            target["WasTraded"] = bool(target["WasTraded"]) or traded
            target["IsCurrentlyTraded"] = traded
            if traded and not ps_string(target["TradeSource"]).strip():
                target["TradeSource"] = "SleeperDraftPick"
        player = provider_pick.get("player_id")
        if player is not None and ps_string(player).strip() != "":
            target["PlayerID"] = ps_string(player)
            target["PlayerName"] = _player_name(provider_pick)
            target["Status"] = "Picked"


def history_rounds(provider_draft: dict[str, Any], provider_picks: list[dict[str, Any]], team_count: int, fallback: int) -> int:
    """Get-DraftHistoryRounds."""
    candidates: list[int] = []
    configured = configured_rounds_from_provider_draft(provider_draft)
    if configured is not None and configured > 0:
        candidates.append(configured)
    rounds = [int(p["round"]) for p in provider_picks if p.get("round") is not None]
    if rounds and max(rounds) > 0:
        candidates.append(max(rounds))
    if team_count > 0:
        numbers = [int(p["pick_no"]) for p in provider_picks if p.get("pick_no") is not None]
        if numbers and max(numbers) > 0:
            candidates.append(math.ceil(max(numbers) / team_count))
    if fallback > 0:
        candidates.append(fallback)
    positive = [value for value in candidates if value > 0]
    return max(positive) if positive else 0


def add_history_trade_history(drafts: list[dict[str, Any]], transactions: list[dict[str, Any]]) -> None:
    """Add-DraftHistoryTradeHistorySafe: complete TradeHistory of completed drafts from all transactions."""
    for draft in drafts:
        by_key = {pick["PickKey"]: pick for pick in draft["Picks"]}
        for transaction in transactions:
            if ps_string(transaction.get("Status")) != "complete":
                continue
            for movement in transaction.get("DraftPicks") or []:
                if ps_string(movement.get("DraftKey")) != draft["DraftKey"]:
                    continue
                if movement.get("Round") is None or movement.get("OriginalOwnerRosterID") is None:
                    continue
                target = by_key.get(pick_key(draft["DraftKey"], int(movement["Round"]), int(movement["OriginalOwnerRosterID"])))
                if target is None:
                    continue
                history = list(target["TradeHistory"])
                exists = any(
                    ps_string(entry["TransactionID"]) == ps_string(transaction["TransactionID"])
                    and int(entry["PreviousOwnerRosterID"]) == int(movement["PreviousOwnerRosterID"])
                    and int(entry["NewOwnerRosterID"]) == int(movement["NewOwnerRosterID"])
                    for entry in history
                )
                if not exists:
                    history.append(_history_entry(transaction, movement))
                target["TradeHistory"] = sorted(history, key=_sort_key_tx)
                if target["TradeHistory"]:
                    target["WasTraded"] = True
                    target["IsCurrentlyTraded"] = target["CurrentOwnerRosterID"] != target["OriginalOwnerRosterID"]
                    if not ps_string(target["TradeSource"]).strip():
                        target["TradeSource"] = ps_string(transaction.get("Source"))


# --------------------------------------------------------------------------- draft output


def _base_draft(definition: dict[str, Any], provider: dict[str, Any] | None) -> dict[str, Any]:
    start, start_utc = _start_time_fields(provider)
    return {
        "ProviderLeagueID": definition["ProviderLeagueID"],
        "DraftKey": definition["DraftKey"],
        "Season": definition["Season"],
        "DraftType": definition["DraftType"],
        "DraftInstance": int(definition["DraftInstance"]),
        "DraftCode": definition["DraftCode"],
        "DraftNo": int(definition["DraftNo"]),
        "DraftSource": "Sleeper" if provider is not None else "Virtual",
        "SleeperDraftID": ps_string(provider.get("draft_id")) if provider is not None else None,
        "SleeperStatus": ps_string(provider.get("status")) if provider is not None else None,
        "SleeperStartTime": start,
        "DraftStartTimeUtc": start_utc,
        "Status": draft_status(provider),
    }


def build_current_draft(
    definition: dict[str, Any],
    league_year: int,
    team_ids: list[int],
    standings_loader: Callable[[], list[dict[str, Any]]] | None,
    transactions: list[dict[str, Any]],
    provider_picks: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    """New-DraftOutputOrderAware."""
    provider = definition["ProviderDraft"]
    config = definition["DraftTypeConfig"]
    season = definition["Season"]
    exact = int(season) == league_year
    setting = draft_type_setting(provider)
    if exact:
        order = order_from_provider_draft(provider) if provider is not None else []
        if order:
            teams, order_source, pick_source = order, "Sleeper", "GeneratedFromSleeperOrderAndTrades"
        else:
            if standings_loader is None:
                raise DraftBuildError(f"Draft '{definition['DraftKey']}' needs the transitional Standings input, but none is available.")
            teams = configured_order_roster_ids(config, season, standings_loader())
            order_source, pick_source = ps_string(config.get("OrderSource")), "GeneratedFromConfiguredOrderAndTrades"
    else:
        teams = sorted(team_ids)
        order_source, pick_source = "UnknownFuture", "GeneratedFromRoundOnlyAndTrades"
    if not teams:
        raise DraftBuildError(f"No teams found for draft '{definition['DraftKey']}'.")
    rounds = int(config["Rounds"])
    picks = projected_picks(
        definition["DraftKey"], season, definition["DraftType"], int(definition["DraftInstance"]),
        definition["DraftCode"], rounds, teams, exact, setting,
    )
    apply_pick_trades(picks, transactions, definition["DraftKey"])
    if provider is not None and exact:
        results = provider_picks(provider)
        if results:
            apply_pick_results(picks, results, ps_string(provider.get("draft_id")))
            pick_source = "GeneratedFromSleeperOrderTradesAndResults"
    draft = _base_draft(definition, provider)
    draft.update({
        "PickSource": pick_source,
        "OrderSource": order_source,
        "OrderMode": "Exact" if exact else "RoundOnly",
        "Settings": {"Rounds": rounds, "Teams": len(teams), "Type": setting},
        "Picks": picks,
    })
    return draft


def build_history_draft(
    definition: dict[str, Any],
    transactions: list[dict[str, Any]],
    provider_picks: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    """New-DraftHistoryOutputOrderAware."""
    provider = definition["ProviderDraft"]
    key = definition["DraftKey"]
    teams = order_from_provider_draft(provider)
    results = provider_picks(provider)
    setting = draft_type_setting(provider)
    if not teams:
        raise DraftBuildError(f"No Sleeper draft order found for completed draft '{key}'.")
    rounds = history_rounds(provider, results, len(teams), int(definition["DraftTypeConfig"].get("Rounds") or 0))
    if rounds <= 0:
        raise DraftBuildError(f"No valid round count found for completed draft '{key}'.")
    picks = projected_picks(
        key, definition["Season"], definition["DraftType"], int(definition["DraftInstance"]),
        definition["DraftCode"], rounds, teams, True, setting,
    )
    apply_pick_trades(picks, transactions, key)
    apply_pick_results(picks, results, ps_string(provider.get("draft_id")))
    draft = _base_draft(definition, provider)
    draft.update({
        "PickSource": "GeneratedFromSleeperOrderTradesAndResults",
        "OrderSource": "Sleeper",
        "OrderMode": "Exact",
        "Settings": {"Rounds": rounds, "Teams": len(teams), "Type": setting},
        "Picks": picks,
    })
    return draft


def build_drafts(
    *,
    league_year: int,
    seasons: list[int],
    provider_league_ids: dict[int, str],
    configs: list[dict[str, Any]],
    open_count: int,
    team_ids: list[int],
    standings_loader: Callable[[], list[dict[str, Any]]] | None,
    payloads: dict[int, dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """All drafts of the league: completed history, current season and open future drafts."""
    assert_draft_type_configs(configs)

    def provider_picks(provider: dict[str, Any]) -> list[dict[str, Any]]:
        draft_id = ps_string(provider.get("draft_id"))
        if not draft_id.strip():
            return []
        season = int(ps_string(provider.get("season")))
        container = (payloads.get(season) or {}).get("PicksByDraftID") or {}
        if draft_id not in container:
            raise DraftBuildError(f"Canonical draft payload 'PicksByDraftID' has no entry for draft '{draft_id}' / season '{season}'.")
        return list(container[draft_id])

    year_payload = payloads.get(league_year) or {}
    draft_map = provider_draft_map(configs, list(year_payload.get("Drafts") or []))
    current = current_and_open_definitions(configs, draft_map, league_year, open_count, provider_league_ids[league_year])
    history: list[dict[str, Any]] = []
    for season in sorted(seasons):
        history.extend(completed_draft_definitions(
            str(season), list((payloads.get(season) or {}).get("Drafts") or []), configs, provider_league_ids.get(season)
        ))
    drafts: list[dict[str, Any]] = []
    history_drafts: dict[str, list[dict[str, Any]]] = {}
    for definition in merge_definitions(current, history):
        if definition["Path"] == "current":
            drafts.append(build_current_draft(definition, league_year, team_ids, standings_loader, transactions, provider_picks))
        else:
            built = build_history_draft(definition, transactions, provider_picks)
            history_drafts.setdefault(definition["Season"], []).append(built)
            drafts.append(built)
    for season_drafts in history_drafts.values():
        add_history_trade_history(sorted(season_drafts, key=lambda d: (d["DraftNo"], d["DraftKey"])), transactions)
    seen: set[str] = set()
    for draft in drafts:
        if draft["DraftKey"] in seen:
            raise DraftBuildError(f"Duplicate DraftKey '{draft['DraftKey']}'.")
        seen.add(draft["DraftKey"])
    return sorted(drafts, key=lambda d: (int(d["Season"]), d["DraftNo"], d["DraftKey"]))


__all__ = ["DraftBuildError", "DraftIdentityError", "build_drafts"]
