from __future__ import annotations

from collections import defaultdict
from typing import Any

from .common import normalize_legacy_canonical_player_fields


_RECONCILIATION_REASON = "corroborated_historical_claim_replaces_provisional_app_mapping"


def _is_provisional_app_source(source: object) -> bool:
    value = str(source or "")
    return value == "app.Players" or value.startswith("app.Players.git.")


def _is_provisional_app_mapping(item: dict[str, Any]) -> bool:
    sources = list(item.get("Sources") or [])
    return bool(sources) and all(_is_provisional_app_source(source) for source in sources)


def _has_external_historical_source(sources: set[str]) -> bool:
    return any(source and not source.startswith("app.") for source in sources)


def _interval(item: dict[str, Any], default_season: int) -> tuple[int, int]:
    first = int(item.get("FirstObservedSeason") or default_season)
    last = int(item.get("LastObservedSeason") or first)
    return first, last


def _without_season(item: dict[str, Any], season: int) -> list[dict[str, Any]]:
    first, last = _interval(item, season)
    if season < first or season > last:
        return [item]
    if first == last == season:
        return []
    if season == first:
        updated = dict(item)
        updated["FirstObservedSeason"] = season + 1
        return [updated]
    if season == last:
        updated = dict(item)
        updated["LastObservedSeason"] = season - 1
        return [updated]

    before = dict(item)
    before["LastObservedSeason"] = season - 1
    after = dict(item)
    after["FirstObservedSeason"] = season + 1
    return [before, after]


def _reconciliation_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(item.get("Provider") or ""),
        str(item.get("ExternalID") or ""),
        int(item.get("ObservedSeason") or 0),
        str(item.get("CanonicalPlayerID") or ""),
        tuple(sorted(str(value) for value in item.get("RetiredCanonicalPlayerIDs") or [])),
        str(item.get("Reason") or ""),
    )


def _prior_retired_owners(
    reconciliations: list[dict[str, Any]],
    *,
    provider: str,
    external_id: str,
    season: int,
    internal_id: str,
) -> set[str]:
    owners: set[str] = set()
    for item in reconciliations:
        if str(item.get("Reason") or "") != _RECONCILIATION_REASON:
            continue
        if str(item.get("Provider") or "") != provider:
            continue
        if str(item.get("ExternalID") or "") != external_id:
            continue
        if int(item.get("ObservedSeason") or 0) != season:
            continue
        if str(item.get("CanonicalPlayerID") or "") != internal_id:
            continue
        owners.update(
            str(value)
            for value in item.get("RetiredCanonicalPlayerIDs") or []
            if str(value)
        )
    return owners


def reconcile_provisional_app_mappings(
    payload: dict[str, Any],
    historical_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Replace only season-local provisional app mappings with corroborated history.

    ``app.Players`` and its contemporaneous git snapshots can bootstrap a person
    when no durable provider bridge exists yet. They are deliberately weaker than
    the external historical-crosswalk claims, which are emitted only after at
    least two independent non-Sleeper provider IDs resolve to one canonical person.

    This function never resolves a collision involving any non-provisional mapping
    owner. It also preserves an explicit reconciliation record so the stronger
    evidence does not silently erase the earlier provisional observation. On a
    later full replay, that persisted record may suppress only the exact same
    token/season conflict against the same retired provisional owner set.
    """

    payload = normalize_legacy_canonical_player_fields(payload)
    mappings = [dict(item) for item in payload.get("Mappings", [])]
    conflicts = [dict(item) for item in payload.get("Conflicts", [])]
    reconciliations = [
        dict(item) for item in payload.get("HistoricalMappingReconciliations", [])
    ]
    known_reconciliations = {_reconciliation_key(item) for item in reconciliations}

    mappings_by_token: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    conflicts_by_token: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in mappings:
        mappings_by_token[(str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))].append(item)
    for item in conflicts:
        conflicts_by_token[(str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))].append(item)

    for claim in sorted(
        historical_claims,
        key=lambda item: (
            int(item["ObservedSeason"]),
            str(item["Provider"]),
            str(item["ExternalID"]),
            str(item["CanonicalPlayerID"]),
        ),
    ):
        sources = {str(source) for source in claim.get("Sources") or [] if str(source)}
        if not _has_external_historical_source(sources):
            continue

        provider = str(claim["Provider"])
        external_id = str(claim["ExternalID"])
        internal_id = str(claim["CanonicalPlayerID"])
        season = int(claim["ObservedSeason"])
        token = (provider, external_id)
        token_mappings = mappings_by_token[token]
        token_conflicts = conflicts_by_token[token]
        prior_retired_owners = _prior_retired_owners(
            reconciliations,
            provider=provider,
            external_id=external_id,
            season=season,
            internal_id=internal_id,
        )

        active_other_mappings = [
            item
            for item in token_mappings
            if str(item.get("CanonicalPlayerID") or "") != internal_id
            and _interval(item, season)[0] <= season <= _interval(item, season)[1]
        ]
        if active_other_mappings and not all(
            _is_provisional_app_mapping(item) for item in active_other_mappings
        ):
            continue

        retired_owners = {
            str(item.get("CanonicalPlayerID") or "")
            for item in active_other_mappings
            if str(item.get("CanonicalPlayerID") or "")
        }
        if not retired_owners:
            retired_owners = set(prior_retired_owners)
        if not retired_owners:
            continue

        allowed_conflict_owners = {internal_id, *retired_owners}
        active_conflicts = [
            item
            for item in token_conflicts
            if _interval(item, season)[0] <= season <= _interval(item, season)[1]
        ]
        blocking_conflict = False
        for conflict in active_conflicts:
            owners = {
                str(value)
                for value in conflict.get("CanonicalPlayerIDs") or []
                if str(value)
            }
            if not owners or not owners.issubset(allowed_conflict_owners):
                blocking_conflict = True
                break
        if blocking_conflict:
            continue

        retired_sources: dict[str, set[str]] = defaultdict(set)
        rebuilt_mappings: list[dict[str, Any]] = []
        for item in token_mappings:
            owner = str(item.get("CanonicalPlayerID") or "")
            first, last = _interval(item, season)
            if (
                owner in retired_owners
                and first <= season <= last
                and _is_provisional_app_mapping(item)
            ):
                retired_sources[owner].update(str(value) for value in item.get("Sources") or [])
                rebuilt_mappings.extend(_without_season(item, season))
            else:
                rebuilt_mappings.append(item)
        token_mappings[:] = rebuilt_mappings

        winning_conflict_sources: set[str] = set()
        rebuilt_conflicts: list[dict[str, Any]] = []
        for conflict in token_conflicts:
            first, last = _interval(conflict, season)
            owners = {
                str(value)
                for value in conflict.get("CanonicalPlayerIDs") or []
                if str(value)
            }
            if (
                first <= season <= last
                and owners
                and owners.issubset(allowed_conflict_owners)
                and owners.intersection(retired_owners)
            ):
                sources_by_owner = conflict.get("SourcesByCanonicalPlayerID") or {}
                winning_conflict_sources.update(
                    str(value)
                    for value in sources_by_owner.get(internal_id, []) or []
                    if str(value)
                )
                rebuilt_conflicts.extend(_without_season(conflict, season))
            else:
                rebuilt_conflicts.append(conflict)
        token_conflicts[:] = rebuilt_conflicts

        # The provisional mapping's source rows are still valid observations of
        # this provider token; only their provisional canonical owner was wrong.
        # Current-claim provenance attached to a conflict that is safely retired
        # is also valid evidence for the winning durable owner and must survive
        # removal of that conflict. Otherwise the next full identity replay adds
        # the same current source one pass later and violates semantic no-op.
        winning_sources = set(sources)
        winning_sources.update(winning_conflict_sources)
        for values in retired_sources.values():
            winning_sources.update(values)

        touching = [
            item
            for item in token_mappings
            if str(item.get("CanonicalPlayerID") or "") == internal_id
            and _interval(item, season)[0] - 1 <= season <= _interval(item, season)[1] + 1
        ]
        if touching:
            primary = touching[0]
            first_values = [_interval(item, season)[0] for item in touching]
            last_values = [_interval(item, season)[1] for item in touching]
            primary["FirstObservedSeason"] = min([season, *first_values])
            primary["LastObservedSeason"] = max([season, *last_values])
            merged_sources = set(winning_sources)
            for item in touching:
                merged_sources.update(str(value) for value in item.get("Sources") or [])
            primary["Sources"] = sorted(merged_sources)
            for item in touching[1:]:
                token_mappings.remove(item)
        else:
            token_mappings.append(
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerID": internal_id,
                    "FirstObservedSeason": season,
                    "LastObservedSeason": season,
                    "Sources": sorted(winning_sources),
                }
            )

        if active_other_mappings:
            reconciliation = {
                "Provider": provider,
                "ExternalID": external_id,
                "ObservedSeason": season,
                "CanonicalPlayerID": internal_id,
                "RetiredCanonicalPlayerIDs": sorted(retired_owners),
                "RetiredSourcesByCanonicalPlayerID": {
                    owner: sorted(values) for owner, values in sorted(retired_sources.items())
                },
                "Sources": sorted(sources),
                "Status": "reconciled",
                "Reason": _RECONCILIATION_REASON,
            }
            key = _reconciliation_key(reconciliation)
            if key not in known_reconciliations:
                reconciliations.append(reconciliation)
                known_reconciliations.add(key)

    mappings = [item for bucket in mappings_by_token.values() for item in bucket]
    conflicts = [item for bucket in conflicts_by_token.values() for item in bucket]
    mappings.sort(
        key=lambda item: (
            str(item["Provider"]),
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            str(item["CanonicalPlayerID"]),
        )
    )
    conflicts.sort(
        key=lambda item: (
            str(item["Provider"]),
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            tuple(str(value) for value in item.get("CanonicalPlayerIDs") or []),
        )
    )
    reconciliations.sort(key=_reconciliation_key)
    return {
        **payload,
        "Mappings": mappings,
        "Conflicts": conflicts,
        "HistoricalMappingReconciliations": reconciliations,
    }
