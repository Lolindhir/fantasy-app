"""LeagueTransactions: manual overlay, draft-pick identity resolution and pick-result enrichment.

Faithful port of the transaction side of the PowerShell rebuild (league-history.yaml, ADR-057):
CanonicalTransactionUtils.psm1 (Merge-CanonicalTransactionsWithManual), TransactionUtils.psm1
(Get-TransactionOutput, Get-ManualTransactionID, Get-SortedTransactions),
TransactionDraftPickEnrichmentUtils.psm1 (identity resolution and pick-result enrichment) and
HistoricalTransactionDraftPickIdentityUtils.psm1 (completed-draft contexts).

All functions work on plain dicts with the key order of the current Transactions.json entries and
mutate transactions in place where the PowerShell code does, because the ADR-026 stages hand the same
objects from one stage to the next. Nothing here reads a file or the clock.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from .league_draft_identity import (
    DraftIdentityError,
    draft_code,
    draft_instance,
    draft_key,
    identity_from_key,
    pick_key,
    ps_string,
)


class TransactionHistoryError(ValueError):
    """Raised when transaction facts, the manual overlay or pick identities are inconsistent (fail closed)."""


# ------------------------------------------------------------------------------ helpers


def _pick_sort_key(pick: dict[str, Any]) -> tuple[Any, ...]:
    return (
        ps_string(pick.get("Season")),
        int(pick["Round"]),
        int(pick["OriginalOwnerRosterID"]),
        int(pick["PreviousOwnerRosterID"]),
        int(pick["NewOwnerRosterID"]),
    )


def effective_at(transaction: dict[str, Any]) -> int:
    """One authoritative occurrence time: provider status transition, else submission/manual date.

    StatusUpdatedAt exists only in the canonical-to-derived adapter. A missing,
    zero or malformed historical provider value falls back to CreatedAt; never
    substitute the current build clock or infer a completion time.
    """
    updated = transaction.get("StatusUpdatedAt")
    if type(updated) is int and updated > 0:
        return updated
    return int(transaction["CreatedAt"])


def sort_transactions(transactions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chronological by EffectiveAt, with TransactionID as deterministic tie-breaker."""
    return sorted(
        transactions,
        key=lambda item: (ps_string(item["Season"]), int(item.get("EffectiveAt") or effective_at(item)), ps_string(item["TransactionID"])),
        reverse=True,
    )


def assert_unique_transaction_ids(transactions: Iterable[dict[str, Any]], label: str) -> None:
    seen: dict[str, dict[str, Any]] = {}
    for item in transactions:
        key = ps_string(item.get("TransactionID")).strip()
        if not key:
            raise TransactionHistoryError(f"{label} contains a record with missing TransactionID.")
        if key in seen:
            raise TransactionHistoryError(f"Duplicate TransactionID '{key}' in {label}.")
        seen[key] = item


def created_date(created_at: int) -> str | None:
    if not created_at:
        return None
    return datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def unix_milliseconds_from_date(date: str | None) -> int:
    """DateTimeUtils.psm1::ConvertTo-UnixMillisecondsFromDateString (yyyy-MM-dd at 00:00 UTC); invalid input fails closed."""
    if date is None or not str(date).strip():
        return 0
    try:
        parsed = datetime.strptime(str(date), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise TransactionHistoryError(f"Manual transaction date '{date}' is not yyyy-MM-dd.") from error
    return int(parsed.timestamp() * 1000)


# --------------------------------------------------------------------------- manual overlay


def _owner_id(owners: dict[str, int], name: Any) -> int:
    key = ps_string(name)
    if key not in owners:
        raise TransactionHistoryError(f"Owner '{key}' not found in the league metadata Owners.")
    return int(owners[key])


def manual_transaction_id(manual: dict[str, Any], owners: dict[str, int]) -> str:
    """TransactionUtils.psm1::Get-ManualTransactionID. The pick Season is empty for overlay picks (they carry a DraftKey)."""
    pick_parts = [
        f"{ps_string(pick.get('Season'))}-R{ps_string(pick.get('Round'))}-O{_owner_id(owners, pick.get('Original'))}"
        f"-F{_owner_id(owners, pick.get('From'))}-T{_owner_id(owners, pick.get('To'))}"
        for pick in manual.get("Picks") or []
    ]
    raw = f"{ps_string(manual.get('Season'))}|{ps_string(manual.get('Date'))}|{'|'.join(pick_parts)}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest().upper()[:12]
    return f"Manual_{ps_string(manual.get('Season'))}_{digest}"


def manual_pick(manual_pick_entry: dict[str, Any], owners: dict[str, int], configs: list[dict[str, Any]]) -> dict[str, Any]:
    """DraftUtils.psm1::Get-DraftPickOutputFromManual."""
    key = ps_string(manual_pick_entry.get("DraftKey"))
    if not key.strip():
        raise TransactionHistoryError("Manual transaction picks must define an explicit DraftKey.")
    try:
        identity = identity_from_key(key, configs)
    except DraftIdentityError as error:
        raise TransactionHistoryError(str(error)) from error
    return {
        "DraftType": identity["DraftType"],
        "DraftInstance": int(identity["DraftInstance"]),
        "DraftCode": identity["DraftCode"],
        "DraftSource": "Manual",
        "DraftKey": identity["DraftKey"],
        "Season": ps_string(identity["Season"]),
        "Round": int(manual_pick_entry["Round"]),
        "OriginalOwnerRosterID": _owner_id(owners, manual_pick_entry.get("Original")),
        "PreviousOwnerRosterID": _owner_id(owners, manual_pick_entry.get("From")),
        "NewOwnerRosterID": _owner_id(owners, manual_pick_entry.get("To")),
    }


def _roster_ids(adds: dict[str, int], drops: dict[str, int], picks: list[dict[str, Any]]) -> list[int]:
    values: list[Any] = list(adds.values()) + list(drops.values())
    values += [pick["PreviousOwnerRosterID"] for pick in picks]
    values += [pick["NewOwnerRosterID"] for pick in picks]
    return sorted({int(value) for value in values if value is not None and value != ""})


def manual_only_transaction(manual: dict[str, Any], season: str, owners: dict[str, int], configs: list[dict[str, Any]]) -> dict[str, Any]:
    """TransactionUtils.psm1::Get-TransactionOutput for an overlay row without a Sleeper binding."""
    picks = sorted((manual_pick(pick, owners, configs) for pick in manual.get("Picks") or []), key=_pick_sort_key)
    created_at = unix_milliseconds_from_date(manual.get("Date")) if manual.get("Date") else 0
    return {
        "Source": "Manual",
        "TransactionID": manual_transaction_id(manual, owners),
        "Type": "trade",
        "Status": "complete",
        "Season": season,
        "Week": int(manual["Week"]) if manual.get("Week") else 0,
        "CreatedAt": created_at,
        "CreatedDate": created_date(created_at),
        "RosterIDs": _roster_ids({}, {}, picks),
        "Adds": {},
        "Drops": {},
        "DraftPicks": picks,
        "Notes": None,
    }


def merge_manual_overlay(
    canonical: list[dict[str, Any]],
    manual_rows: list[dict[str, Any]],
    season: str,
    owners: dict[str, int],
    configs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """CanonicalTransactionUtils.psm1::Merge-CanonicalTransactionsWithManual."""
    rows = [row for row in manual_rows if ps_string(row.get("Season")) == season]
    bindings: dict[str, dict[str, Any]] = {}
    for row in rows:
        bound = ps_string(row.get("SleeperTransactionID")).strip()
        if not bound:
            continue
        if bound in bindings:
            raise TransactionHistoryError(f"Duplicate SleeperTransactionID '{bound}' in manual transaction bindings for season {season}.")
        bindings[bound] = row
    canonical_ids = {ps_string(item["TransactionID"]) for item in canonical}
    for bound in bindings:
        if bound not in canonical_ids:
            raise TransactionHistoryError(f"Manual transaction binding '{bound}' for season {season} has no canonical transaction.")

    result: list[dict[str, Any]] = []
    for transaction in canonical:
        row = bindings.get(ps_string(transaction["TransactionID"]))
        if row is not None:
            transaction["Source"] = "Sleeper_Manual"
            picks = list(transaction["DraftPicks"]) + [manual_pick(pick, owners, configs) for pick in row.get("Picks") or []]
            transaction["DraftPicks"] = sorted(picks, key=_pick_sort_key)
            transaction["RosterIDs"] = _roster_ids(transaction["Adds"], transaction["Drops"], transaction["DraftPicks"])
        result.append(transaction)
    for row in rows:
        if ps_string(row.get("SleeperTransactionID")).strip():
            continue
        result.append(manual_only_transaction(row, season, owners, configs))

    for transaction in result:
        transaction["EffectiveAt"] = effective_at(transaction)
        # Only one principal chronology field is persisted in Shared Derived;
        # CreatedAt / CreatedDate remain submission-time provenance.
        transaction.pop("StatusUpdatedAt", None)
    result = sort_transactions(result)
    assert_unique_transaction_ids(result, f"canonical plus manual transactions for season {season}")
    return result


# ------------------------------------------------------- draft identity of transaction picks


def _set(target: dict[str, Any], name: str, value: Any) -> None:
    target[name] = value


def _movement_match(transaction_pick: dict[str, Any], traded: dict[str, Any], *, require_movement: bool) -> bool:
    if ps_string(traded.get("season")) != ps_string(transaction_pick["Season"]):
        return False
    if traded.get("round") is None or int(traded["round"]) != int(transaction_pick["Round"]):
        return False
    if traded.get("roster_id") is None or int(traded["roster_id"]) != int(transaction_pick["OriginalOwnerRosterID"]):
        return False
    if not require_movement:
        return True
    previous, new = traded.get("previous_owner_id"), traded.get("owner_id")
    return (
        previous is not None
        and new is not None
        and int(previous) == int(transaction_pick["PreviousOwnerRosterID"])
        and int(new) == int(transaction_pick["NewOwnerRosterID"])
    )


def _same_movement(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        ps_string(left["Season"]) == ps_string(right["Season"])
        and int(left["Round"]) == int(right["Round"])
        and int(left["OriginalOwnerRosterID"]) == int(right["OriginalOwnerRosterID"])
        and int(left["PreviousOwnerRosterID"]) == int(right["PreviousOwnerRosterID"])
        and int(left["NewOwnerRosterID"]) == int(right["NewOwnerRosterID"])
    )


def _claimed_draft_keys(transaction: dict[str, Any], sleeper_pick: dict[str, Any]) -> list[str]:
    claimed = set()
    for other in transaction["DraftPicks"]:
        if other is sleeper_pick or ps_string(other.get("DraftSource")) == "Sleeper":
            continue
        if not _same_movement(sleeper_pick, other):
            continue
        key = ps_string(other.get("DraftKey"))
        if key.strip():
            claimed.add(key)
    return sorted(claimed)


def _unique_by_draft_key(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for context in sorted(contexts, key=lambda item: item["DraftKey"]):
        unique.setdefault(context["DraftKey"], context)
    return list(unique.values())


def _context_candidates(transaction_pick: dict[str, Any], contexts: list[dict[str, Any]], excluded: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exact: list[dict[str, Any]] = []
    identity: list[dict[str, Any]] = []
    for context in contexts:
        if context["DraftKey"] in excluded:
            continue
        has_exact = has_identity = False
        for traded in context["TradedPicks"]:
            if _movement_match(transaction_pick, traded, require_movement=True):
                has_exact = True
                break
            if _movement_match(transaction_pick, traded, require_movement=False):
                has_identity = True
        if has_exact:
            exact.append(context)
        elif has_identity:
            identity.append(context)
    return _unique_by_draft_key(exact), _unique_by_draft_key(identity)


def _future_pool_config(configs: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [config for config in configs if config.get("SleeperFuturePickPool") is True]
    if len(matches) > 1:
        identities = ", ".join(draft_code(str(config["DraftType"]), draft_instance(config)) for config in matches)
        raise TransactionHistoryError(
            f"Multiple draft instances are configured as SleeperFuturePickPool: [{identities}]. "
            "At most one configured draft instance may own Sleeper future picks."
        )
    return matches[0] if matches else None


def _future_context(transaction_pick: dict[str, Any], excluded: list[str], configs: list[dict[str, Any]], league_year: int) -> dict[str, Any] | None:
    try:
        season_number = int(ps_string(transaction_pick["Season"]))
    except ValueError:
        return None
    if season_number <= league_year:
        return None
    config = _future_pool_config(configs)
    if config is None:
        return None
    draft_type = str(config["DraftType"])
    instance = draft_instance(config)
    key = draft_key(ps_string(transaction_pick["Season"]), draft_type, instance)
    if key in excluded:
        return None
    return {
        "Season": ps_string(transaction_pick["Season"]),
        "DraftType": draft_type,
        "DraftInstance": instance,
        "DraftCode": draft_code(draft_type, instance),
        "DraftKey": key,
        "SleeperDraftID": None,
        "TradedPicks": [],
    }


def resolve_pick_identities(
    transactions: list[dict[str, Any]],
    contexts: list[dict[str, Any]],
    configs: list[dict[str, Any]],
    league_year: int,
) -> list[dict[str, Any]]:
    """Resolve-TransactionDraftPickTypesFromContexts: mutate provider picks in place, return the unresolved ones.

    The PowerShell code only warns for an unresolved pick and keeps the previous stage's value; the caller
    decides whether to fail closed (the report names transaction, season, round, original owner and candidates).
    """
    unresolved: list[dict[str, Any]] = []
    for transaction in transactions:
        for pick in transaction["DraftPicks"]:
            if ps_string(pick.get("DraftSource")) != "Sleeper":
                continue
            claimed = _claimed_draft_keys(transaction, pick)
            exact, identity = _context_candidates(pick, contexts, claimed)
            context: dict[str, Any] | None = None
            if len(exact) == 1:
                context = exact[0]
            elif len(exact) == 0 and len(identity) == 1:
                context = identity[0]
            if context is None and not exact and not identity:
                context = _future_context(pick, claimed, configs, league_year)
            if context is None:
                unresolved.append({
                    "TransactionID": transaction["TransactionID"],
                    "Season": pick["Season"],
                    "Round": pick["Round"],
                    "OriginalOwnerRosterID": pick["OriginalOwnerRosterID"],
                    "Candidates": [item["DraftKey"] for item in (exact or identity)],
                    "ClaimedSiblingDraftKeys": claimed,
                })
                continue
            _set(pick, "DraftType", str(context["DraftType"]))
            _set(pick, "DraftInstance", int(context["DraftInstance"]))
            _set(pick, "DraftCode", str(context["DraftCode"]))
            _set(pick, "DraftKey", str(context["DraftKey"]))
            _set(pick, "SleeperDraftID", context["SleeperDraftID"])
    return unresolved


# ----------------------------------------------------------------- pick-result enrichment


def _result_comparable(candidate: dict[str, Any]) -> str:
    draft, pick = candidate["Draft"], candidate["Pick"]
    return json.dumps({
        "DraftKey": ps_string(draft.get("DraftKey")),
        "DraftType": ps_string(draft.get("DraftType")),
        "DraftInstance": draft.get("DraftInstance"),
        "DraftCode": ps_string(draft.get("DraftCode")),
        "SleeperDraftID": draft.get("SleeperDraftID"),
        "PickKey": ps_string(pick.get("PickKey")),
        "Season": ps_string(pick.get("Season")),
        "Round": pick.get("Round"),
        "PositionInRound": pick.get("PositionInRound"),
        "OverallPick": pick.get("OverallPick"),
        "PlayerID": pick.get("PlayerID"),
        "PlayerName": pick.get("PlayerName"),
        "Status": pick.get("Status"),
        "SleeperPickNo": pick.get("SleeperPickNo"),
    }, sort_keys=True)


def _unique_result_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[str, dict[str, Any]] = {}
    comparable: dict[str, str] = {}
    for candidate in candidates:
        draft_key_value, pick_key_value = ps_string(candidate["Draft"].get("DraftKey")), ps_string(candidate["Pick"].get("PickKey"))
        if not draft_key_value.strip() or not pick_key_value.strip():
            raise TransactionHistoryError("Generated draft result candidate has an incomplete DraftKey/PickKey identity.")
        identity = f"{draft_key_value}|{pick_key_value}"
        value = _result_comparable(candidate)
        if identity in by_identity:
            if comparable[identity] != value:
                raise TransactionHistoryError(f"Conflicting duplicate generated draft-pick identity '{identity}'.")
            continue
        by_identity[identity] = candidate
        comparable[identity] = value
    return [by_identity[name] for name in sorted(by_identity)]


def _result_candidates(transaction: dict[str, Any], transaction_pick: dict[str, Any], drafts: list[dict[str, Any]], *, require_trade_history: bool) -> list[dict[str, Any]]:
    candidates = []
    for draft in drafts:
        for draft_pick in draft["Picks"]:
            if require_trade_history:
                is_candidate = any(
                    ps_string(entry.get("TransactionID")) == ps_string(transaction["TransactionID"])
                    and int(entry["PreviousOwnerRosterID"]) == int(transaction_pick["PreviousOwnerRosterID"])
                    and int(entry["NewOwnerRosterID"]) == int(transaction_pick["NewOwnerRosterID"])
                    for entry in draft_pick.get("TradeHistory") or []
                )
            else:
                is_candidate = (
                    ps_string(draft_pick.get("Season")) == ps_string(transaction_pick["Season"])
                    and int(draft_pick["Round"]) == int(transaction_pick["Round"])
                    and int(draft_pick["OriginalOwnerRosterID"]) == int(transaction_pick["OriginalOwnerRosterID"])
                )
            if is_candidate:
                candidates.append({"Draft": draft, "Pick": draft_pick})
    return _unique_result_candidates(candidates)


def _select_result(candidates: list[dict[str, Any]], transaction_pick: dict[str, Any]) -> dict[str, Any] | None:
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None
    for field, draft_field in (("SleeperDraftID", "SleeperDraftID"), ("DraftKey", "DraftKey"), ("DraftCode", "DraftCode"), ("DraftType", "DraftType")):
        wanted = ps_string(transaction_pick.get(field))
        if not wanted.strip():
            continue
        matches = [item for item in candidates if ps_string(item["Draft"].get(draft_field)) == wanted]
        if len(matches) == 1:
            return matches[0]
    return None


def enrich_pick_details(transactions: list[dict[str, Any]], drafts: list[dict[str, Any]]) -> None:
    """Add-TransactionDraftPickDetailsFromDrafts (DisplayPick is a consumer field and not written)."""
    for transaction in transactions:
        for pick in transaction["DraftPicks"]:
            match = _select_result(_result_candidates(transaction, pick, drafts, require_trade_history=True), pick)
            if match is None:
                match = _select_result(_result_candidates(transaction, pick, drafts, require_trade_history=False), pick)
            if match is None:
                continue
            draft, draft_pick = match["Draft"], match["Pick"]
            _set(pick, "DraftType", ps_string(draft["DraftType"]))
            _set(pick, "DraftInstance", int(draft["DraftInstance"]))
            _set(pick, "DraftCode", ps_string(draft["DraftCode"]))
            _set(pick, "DraftKey", ps_string(draft["DraftKey"]))
            _set(pick, "SleeperDraftID", draft.get("SleeperDraftID"))
            _set(pick, "PickKey", ps_string(draft_pick["PickKey"]))
            _set(pick, "PositionInRound", draft_pick.get("PositionInRound"))
            _set(pick, "OverallPick", draft_pick.get("OverallPick"))
            _set(pick, "PlayerID", draft_pick.get("PlayerID"))
            _set(pick, "PlayerName", draft_pick.get("PlayerName"))
            _set(pick, "PickStatus", draft_pick.get("Status"))
            _set(pick, "SleeperPickNo", draft_pick.get("SleeperPickNo"))


def expected_pick_key(pick: dict[str, Any]) -> str:
    return pick_key(ps_string(pick["DraftKey"]), int(pick["Round"]), int(pick["OriginalOwnerRosterID"]))
