#!/usr/bin/env python3
"""Read-only canonical League transaction shadow adapter and parity reporter."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SLEEPER = "Sleeper"
WEEK_FILE_RE = re.compile(r"week-(\d+)\.json$")


class ShadowContractError(ValueError):
    """Raised when canonical or legacy data violates the shadow contract."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _provider_mapping_value(
    mappings: object,
    field: str,
    *,
    context: str,
    provider: str = SLEEPER,
) -> str:
    if not isinstance(mappings, list):
        raise ShadowContractError(f"{context} ProviderMappings must be an array")
    values: list[str] = []
    for mapping in mappings:
        if not isinstance(mapping, dict) or str(mapping.get("Provider") or "") != provider:
            continue
        value = str(mapping.get(field) or "").strip()
        if value:
            values.append(value)
    unique = sorted(set(values))
    if len(unique) != 1:
        raise ShadowContractError(
            f"{context} requires exactly one {provider} {field}; found {unique}"
        )
    return unique[0]


def build_roster_provider_lookup(rosters: object) -> dict[str, int]:
    if not isinstance(rosters, list):
        raise ShadowContractError("Canonical rosters must be an array")
    result: dict[str, int] = {}
    provider_owners: dict[int, str] = {}
    for item in rosters:
        if not isinstance(item, dict):
            raise ShadowContractError("Canonical roster entries must be objects")
        canonical_id = str(item.get("CanonicalLeagueRosterID") or "").strip()
        if not canonical_id:
            raise ShadowContractError("Canonical roster is missing CanonicalLeagueRosterID")
        provider_raw = _provider_mapping_value(
            item.get("ProviderMappings"),
            "ProviderRosterID",
            context=f"roster {canonical_id}",
        )
        try:
            provider_id = int(provider_raw)
        except ValueError as exc:
            raise ShadowContractError(
                f"roster {canonical_id} has non-numeric Sleeper ProviderRosterID {provider_raw!r}"
            ) from exc
        if canonical_id in result:
            raise ShadowContractError(f"Duplicate CanonicalLeagueRosterID {canonical_id}")
        previous = provider_owners.get(provider_id)
        if previous is not None and previous != canonical_id:
            raise ShadowContractError(
                f"Sleeper ProviderRosterID {provider_id} maps to both {previous} and {canonical_id}"
            )
        result[canonical_id] = provider_id
        provider_owners[provider_id] = canonical_id
    return result


def _resolve_roster_id(canonical_id: object, lookup: dict[str, int], *, context: str) -> int:
    key = str(canonical_id or "").strip()
    if not key or key not in lookup:
        raise ShadowContractError(f"{context} references unknown CanonicalLeagueRosterID {key!r}")
    return lookup[key]


def _player_provider_id(player: object, *, context: str) -> str:
    if not isinstance(player, dict):
        raise ShadowContractError(f"{context} Player must be an object")
    return _provider_mapping_value(
        player.get("ProviderMappings"),
        "ProviderPlayerID",
        context=context,
    )


def _asset_map(entries: object, lookup: dict[str, int], *, label: str) -> dict[str, int]:
    if entries is None:
        return {}
    if not isinstance(entries, list):
        raise ShadowContractError(f"{label} must be an array")
    result: dict[str, int] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ShadowContractError(f"{label}[{index}] must be an object")
        player_id = _player_provider_id(entry.get("Player"), context=f"{label}[{index}]")
        roster_id = _resolve_roster_id(
            entry.get("CanonicalLeagueRosterID"),
            lookup,
            context=f"{label}[{index}]",
        )
        previous = result.get(player_id)
        if previous is not None and previous != roster_id:
            raise ShadowContractError(
                f"{label} contains conflicting roster mappings for Sleeper player {player_id}"
            )
        result[player_id] = roster_id
    return dict(sorted(result.items(), key=lambda pair: pair[0]))


def _created_date(created_at: int) -> str | None:
    if created_at == 0:
        return None
    return datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _canonical_draft_pick_base(
    pick: object,
    lookup: dict[str, int],
    *,
    index: int,
) -> dict[str, Any]:
    if not isinstance(pick, dict):
        raise ShadowContractError(f"DraftPicks[{index}] must be an object")
    try:
        round_no = int(pick.get("Round"))
    except (TypeError, ValueError) as exc:
        raise ShadowContractError(f"DraftPicks[{index}] has invalid Round") from exc
    season = str(pick.get("Season") or "").strip()
    if not season:
        raise ShadowContractError(f"DraftPicks[{index}] is missing Season")
    return {
        "DraftType": None,
        "DraftInstance": None,
        "DraftCode": None,
        "DraftSource": SLEEPER,
        "DraftKey": None,
        "Season": season,
        "Round": round_no,
        "OriginalOwnerRosterID": _resolve_roster_id(
            pick.get("OriginalCanonicalLeagueRosterID"), lookup, context=f"DraftPicks[{index}].Original"
        ),
        "PreviousOwnerRosterID": _resolve_roster_id(
            pick.get("PreviousOwnerCanonicalLeagueRosterID"), lookup, context=f"DraftPicks[{index}].Previous"
        ),
        "NewOwnerRosterID": _resolve_roster_id(
            pick.get("OwnerCanonicalLeagueRosterID"), lookup, context=f"DraftPicks[{index}].Owner"
        ),
        "SleeperDraftID": None,
    }


def _draft_pick_sort_key(pick: dict[str, Any]) -> tuple[Any, ...]:
    season = pick.get("Season")
    try:
        season_key: Any = int(season)
    except (TypeError, ValueError):
        season_key = str(season or "")
    return (
        season_key,
        int(pick.get("Round") or 0),
        int(pick.get("OriginalOwnerRosterID") or 0),
        int(pick.get("PreviousOwnerRosterID") or 0),
        int(pick.get("NewOwnerRosterID") or 0),
    )


def convert_canonical_transaction(
    transaction: object,
    roster_lookup: dict[str, int],
    *,
    season: int | str,
) -> dict[str, Any]:
    if not isinstance(transaction, dict):
        raise ShadowContractError("Canonical transaction entry must be an object")
    transaction_id = _provider_mapping_value(
        transaction.get("ProviderMappings"),
        "ProviderTransactionID",
        context="canonical transaction",
    )
    try:
        created_at = int(transaction.get("CreatedAt") or 0)
        week = int(transaction.get("Week") or 0)
    except (TypeError, ValueError) as exc:
        raise ShadowContractError(f"transaction {transaction_id} has invalid CreatedAt or Week") from exc

    roster_ids_raw = transaction.get("CanonicalLeagueRosterIDs") or []
    if not isinstance(roster_ids_raw, list):
        raise ShadowContractError(f"transaction {transaction_id} CanonicalLeagueRosterIDs must be an array")
    roster_ids = sorted(
        {
            _resolve_roster_id(value, roster_lookup, context=f"transaction {transaction_id} roster")
            for value in roster_ids_raw
        }
    )
    draft_picks = [
        _canonical_draft_pick_base(pick, roster_lookup, index=index)
        for index, pick in enumerate(transaction.get("DraftPicks") or [])
    ]
    draft_picks.sort(key=_draft_pick_sort_key)
    metadata = transaction.get("Metadata") or {}
    if not isinstance(metadata, dict):
        raise ShadowContractError(f"transaction {transaction_id} Metadata must be an object")

    return {
        "Source": SLEEPER,
        "TransactionID": transaction_id,
        "Type": str(transaction.get("Type") or "unknown"),
        "Status": str(transaction.get("Status") or "unknown"),
        "Season": str(season),
        "Week": week,
        "CreatedAt": created_at,
        "CreatedDate": _created_date(created_at),
        "RosterIDs": roster_ids,
        "Adds": _asset_map(transaction.get("Adds"), roster_lookup, label=f"transaction {transaction_id} Adds"),
        "Drops": _asset_map(transaction.get("Drops"), roster_lookup, label=f"transaction {transaction_id} Drops"),
        "DraftPicks": draft_picks,
        "Notes": metadata.get("notes"),
    }


def _normalized_asset_map(value: object, *, context: str) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ShadowContractError(f"{context} must be an object")
    result: dict[str, int] = {}
    for key, raw in value.items():
        try:
            result[str(key)] = int(raw)
        except (TypeError, ValueError) as exc:
            raise ShadowContractError(f"{context} has invalid roster id for player {key!r}") from exc
    return dict(sorted(result.items(), key=lambda pair: pair[0]))


def _legacy_draft_pick_projection(pick: object, *, index: int) -> dict[str, Any]:
    if not isinstance(pick, dict):
        raise ShadowContractError(f"legacy DraftPicks[{index}] must be an object")
    return {
        "DraftSource": str(pick.get("DraftSource") or ""),
        "Season": str(pick.get("Season") or ""),
        "Round": int(pick.get("Round") or 0),
        "OriginalOwnerRosterID": int(pick.get("OriginalOwnerRosterID") or 0),
        "PreviousOwnerRosterID": int(pick.get("PreviousOwnerRosterID") or 0),
        "NewOwnerRosterID": int(pick.get("NewOwnerRosterID") or 0),
    }


def _canonical_draft_pick_projection(pick: dict[str, Any]) -> dict[str, Any]:
    return {
        "DraftSource": str(pick.get("DraftSource") or ""),
        "Season": str(pick.get("Season") or ""),
        "Round": int(pick.get("Round") or 0),
        "OriginalOwnerRosterID": int(pick.get("OriginalOwnerRosterID") or 0),
        "PreviousOwnerRosterID": int(pick.get("PreviousOwnerRosterID") or 0),
        "NewOwnerRosterID": int(pick.get("NewOwnerRosterID") or 0),
    }


def parity_projection(transaction: dict[str, Any], *, legacy: bool) -> dict[str, Any]:
    draft_picks_raw = transaction.get("DraftPicks") or []
    if not isinstance(draft_picks_raw, list):
        raise ShadowContractError("DraftPicks must be an array")
    if legacy:
        picks = [
            _legacy_draft_pick_projection(pick, index=index)
            for index, pick in enumerate(draft_picks_raw)
        ]
    else:
        picks = [_canonical_draft_pick_projection(pick) for pick in draft_picks_raw]
    picks.sort(key=_draft_pick_sort_key)
    roster_ids = sorted(int(value) for value in (transaction.get("RosterIDs") or []))
    return {
        "Source": str(transaction.get("Source") or ""),
        "TransactionID": str(transaction.get("TransactionID") or ""),
        "Type": str(transaction.get("Type") or ""),
        "Status": str(transaction.get("Status") or ""),
        "Season": str(transaction.get("Season") or ""),
        "Week": int(transaction.get("Week") or 0),
        "CreatedAt": int(transaction.get("CreatedAt") or 0),
        "CreatedDate": transaction.get("CreatedDate"),
        "RosterIDs": roster_ids,
        "Adds": _normalized_asset_map(transaction.get("Adds"), context="Adds"),
        "Drops": _normalized_asset_map(transaction.get("Drops"), context="Drops"),
        "DraftPicks": picks,
        "Notes": transaction.get("Notes"),
    }


def load_canonical_transactions(season_dir: Path, roster_lookup: dict[str, int], *, season: int) -> list[dict[str, Any]]:
    transaction_dir = season_dir / "transactions"
    if not transaction_dir.is_dir():
        raise FileNotFoundError(f"Canonical transaction directory missing: {transaction_dir}")
    files: list[tuple[int, Path]] = []
    for path in transaction_dir.glob("week-*.json"):
        match = WEEK_FILE_RE.search(path.name)
        if match:
            files.append((int(match.group(1)), path))
    if not files:
        raise FileNotFoundError(f"No canonical transaction partitions found in {transaction_dir}")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, path in sorted(files):
        payload = load_json(path)
        if not isinstance(payload, list):
            raise ShadowContractError(f"Canonical transaction partition must be an array: {path}")
        for item in payload:
            converted = convert_canonical_transaction(item, roster_lookup, season=season)
            transaction_id = converted["TransactionID"]
            if transaction_id in seen:
                raise ShadowContractError(f"Duplicate canonical ProviderTransactionID {transaction_id}")
            seen.add(transaction_id)
            result.append(converted)
    result.sort(key=lambda item: (-int(item["CreatedAt"]), item["TransactionID"]))
    return result


def manual_binding_ids(manual_transactions: object, *, season: int) -> set[str]:
    if manual_transactions is None:
        return set()
    if not isinstance(manual_transactions, list):
        raise ShadowContractError("Manual transactions must be an array")
    result: set[str] = set()
    for item in manual_transactions:
        if not isinstance(item, dict) or str(item.get("Season") or "") != str(season):
            continue
        raw = item.get("SleeperTransactionID")
        value = str(raw or "").strip()
        if value:
            result.add(value)
    return result


def _by_transaction_id(transactions: object, *, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(transactions, list):
        raise ShadowContractError(f"{label} transactions must be an array")
    result: dict[str, dict[str, Any]] = {}
    for item in transactions:
        if not isinstance(item, dict):
            raise ShadowContractError(f"{label} transaction entries must be objects")
        transaction_id = str(item.get("TransactionID") or "").strip()
        if not transaction_id:
            raise ShadowContractError(f"{label} transaction is missing TransactionID")
        if transaction_id in result:
            raise ShadowContractError(f"Duplicate {label} TransactionID {transaction_id}")
        result[transaction_id] = item
    return result


def _field_differences(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return sorted(key for key in left if left.get(key) != right.get(key))


def build_shadow_report(
    canonical_transactions: list[dict[str, Any]],
    legacy_transactions: list[dict[str, Any]],
    *,
    canonical_league_id: str,
    season: int,
    manual_bound_ids: set[str] | None = None,
) -> dict[str, Any]:
    manual_bound_ids = set(manual_bound_ids or set())
    canonical_by_id = _by_transaction_id(canonical_transactions, label="canonical-adapted")
    legacy_by_id = _by_transaction_id(legacy_transactions, label="legacy")
    canonical_ids = set(canonical_by_id)
    legacy_ids = set(legacy_by_id)
    intersection = canonical_ids & legacy_ids

    manual_bound = sorted(intersection & manual_bound_ids)
    strict_ids = sorted(intersection - manual_bound_ids)
    canonical_only = sorted(canonical_ids - legacy_ids)
    legacy_only_ids = sorted(legacy_ids - canonical_ids)
    manual_only: list[str] = []
    unexpected_legacy_only: list[str] = []
    for transaction_id in legacy_only_ids:
        source = str(legacy_by_id[transaction_id].get("Source") or "")
        if source == "Manual" or transaction_id.startswith("Manual_"):
            manual_only.append(transaction_id)
        else:
            unexpected_legacy_only.append(transaction_id)

    field_differences: list[dict[str, Any]] = []
    for transaction_id in strict_ids:
        canonical_projection = parity_projection(canonical_by_id[transaction_id], legacy=False)
        legacy_projection = parity_projection(legacy_by_id[transaction_id], legacy=True)
        differences = _field_differences(canonical_projection, legacy_projection)
        if differences:
            field_differences.append({"TransactionID": transaction_id, "Fields": differences})

    manual_overlay_differences: list[dict[str, Any]] = []
    for transaction_id in manual_bound:
        canonical_projection = parity_projection(canonical_by_id[transaction_id], legacy=False)
        legacy_projection = parity_projection(legacy_by_id[transaction_id], legacy=True)
        differences = _field_differences(canonical_projection, legacy_projection)
        if differences:
            manual_overlay_differences.append({"TransactionID": transaction_id, "Fields": differences})

    strict_parity = not canonical_only and not unexpected_legacy_only and not field_differences
    return {
        "schemaVersion": 1,
        "CanonicalLeagueID": canonical_league_id,
        "Season": season,
        "StrictParity": strict_parity,
        "Counts": {
            "CanonicalAdapted": len(canonical_transactions),
            "Legacy": len(legacy_transactions),
            "StrictCompared": len(strict_ids),
            "ManualBound": len(manual_bound),
            "ManualOnly": len(manual_only),
        },
        "Classifications": {
            "CanonicalOnly": canonical_only,
            "UnexpectedLegacyOnly": unexpected_legacy_only,
            "ManualOnly": manual_only,
            "ManualBound": manual_bound,
            "FieldDifferences": field_differences,
            "ManualOverlayDifferences": manual_overlay_differences,
        },
    }


def build_repo_shadow_report(repo_root: Path, *, canonical_league_id: str, season: int) -> dict[str, Any]:
    season_dir = repo_root / "source-data" / "leagues" / canonical_league_id / "seasons" / str(season)
    rosters = load_json(season_dir / "rosters.json")
    lookup = build_roster_provider_lookup(rosters)
    canonical_transactions = load_canonical_transactions(season_dir, lookup, season=season)
    legacy_transactions = load_json(repo_root / "public" / "data" / "Transactions.json")
    manual_path = repo_root / "public" / "data" / "Transactions_Manual.json"
    manual = load_json(manual_path) if manual_path.exists() else []
    return build_shadow_report(
        canonical_transactions,
        legacy_transactions,
        canonical_league_id=canonical_league_id,
        season=season,
        manual_bound_ids=manual_binding_ids(manual, season=season),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--canonical-league-id", required=True)
    parser.add_argument("--season", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_repo_shadow_report(
        args.repo_root.resolve(),
        canonical_league_id=args.canonical_league_id,
        season=args.season,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["StrictParity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
