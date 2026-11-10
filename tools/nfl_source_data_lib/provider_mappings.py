from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import CANONICAL_SCHEMA_VERSION, load_json, normalize_legacy_canonical_player_fields
from .identity_adjudications import (
    apply_identity_adjudications,
    load_identity_adjudication_claims,
)
from .identity_model import ANCHOR_ID_KEYS
from .provisional_reconciliation import _without_season
from data_roots import DATA_SOURCE_ROOT

PLACEHOLDER_GSIS_UPGRADE_REASON = "placeholder_gsis_upgrade_transfers_current_claim"
CURRENT_ADJUDICATION_REASON = "current_identity_adjudication_transfers_current_claim"
CURRENT_ADJUDICATION_SOURCE_PREFIX = "manual.current-identity-adjudication:"


def _transfer_reason(claim: dict[str, Any]) -> str:
    if any(
        str(source).startswith(CURRENT_ADJUDICATION_SOURCE_PREFIX)
        for source in claim.get("Sources") or []
    ):
        return CURRENT_ADJUDICATION_REASON
    return PLACEHOLDER_GSIS_UPGRADE_REASON


def _transfer_reconciliation_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(item.get("Provider") or ""),
        str(item.get("ExternalID") or ""),
        int(item.get("ObservedSeason") or 0),
        str(item.get("CanonicalPlayerID") or ""),
        tuple(sorted(str(value) for value in item.get("RetiredCanonicalPlayerIDs") or [])),
        str(item.get("Reason") or ""),
    )


def _retire_transferred_claims(
    provider_claims: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    observation_season: int,
) -> list[dict[str, Any]]:
    reconciliations: list[dict[str, Any]] = []
    for claim in provider_claims:
        provider = str(claim["Provider"])
        external_id = str(claim["ExternalID"])
        new_owner = str(claim["CanonicalPlayerID"])
        for previous_owner in claim.get("TransferredFromCanonicalPlayerIDs") or []:
            previous_owner = str(previous_owner)
            retired_sources: set[str] = set()
            changed = False
            rebuilt: list[dict[str, Any]] = []
            for item in mappings:
                if (
                    str(item.get("Provider")) == provider
                    and str(item.get("ExternalID")) == external_id
                    and str(item.get("CanonicalPlayerID")) == previous_owner
                ):
                    rest = _without_season(item, observation_season)
                    if rest != [item]:
                        changed = True
                        retired_sources.update(str(v) for v in item.get("Sources") or [])
                    rebuilt.extend(rest)
                else:
                    rebuilt.append(item)
            mappings[:] = rebuilt
            rebuilt_conflicts: list[dict[str, Any]] = []
            for conflict in conflicts:
                owners = {str(v) for v in conflict.get("CanonicalPlayerIDs") or []}
                if (
                    str(conflict.get("Provider")) == provider
                    and str(conflict.get("ExternalID")) == external_id
                    and previous_owner in owners
                ):
                    rest = _without_season(conflict, observation_season)
                    if rest != [conflict]:
                        changed = True
                    rebuilt_conflicts.extend(rest)
                else:
                    rebuilt_conflicts.append(conflict)
            conflicts[:] = rebuilt_conflicts
            if changed:
                reconciliations.append(
                    {
                        "Provider": provider,
                        "ExternalID": external_id,
                        "ObservedSeason": observation_season,
                        "CanonicalPlayerID": new_owner,
                        "RetiredCanonicalPlayerIDs": [previous_owner],
                        "RetiredSourcesByCanonicalPlayerID": {
                            previous_owner: sorted(retired_sources)
                        },
                        "Sources": sorted(claim.get("Sources") or []),
                        "Status": "reconciled",
                        "Reason": _transfer_reason(claim),
                    }
                )
    return reconciliations


def build_provider_mapping_payload(
    repo_root: Path,
    provider_claims: list[dict[str, Any]],
    mapping_conflicts: list[dict[str, Any]],
    observation_season: int,
) -> dict[str, Any]:
    """Build season-aware provider mappings without quadratic list scans.

    Current canonical claims represent the active provider bridge for the current
    observation season. Persisted anchor mappings may still represent real older
    history, but a stale value from a previous latest snapshot must not block a
    corrected current mapping for the same canonical person.
    """

    path = repo_root / DATA_SOURCE_ROOT / "nfl/identities/provider-mappings.json"
    existing = normalize_legacy_canonical_player_fields(load_json(path, {}) or {})
    mappings = [dict(item) for item in existing.get("Mappings", [])]
    conflicts = [dict(item) for item in existing.get("Conflicts", [])]

    # Historical provenance is durable state, not a by-product of only the
    # historical replay stage. The current-claim rebuild runs before replay and
    # reconciliation on every full materialization, so it must carry these
    # records forward. Otherwise a second pass forgets which provisional owner
    # was already retired and recreates the same conflict indefinitely.
    persisted_history: dict[str, list[dict[str, Any]]] = {}
    for key in ("HistoricalResolutionConflicts", "HistoricalMappingReconciliations"):
        if key in existing:
            persisted_history[key] = [dict(item) for item in existing.get(key, [])]

    current_values_by_owner_provider: dict[tuple[str, str], set[str]] = defaultdict(set)
    for claim in provider_claims:
        current_values_by_owner_provider[
            (str(claim["CanonicalPlayerID"]), str(claim["Provider"]))
        ].add(str(claim["ExternalID"]))

    # Canonical identity stores the active provider bridge, while this mapping
    # payload also retains true historical validity. If an anchor provider has a
    # corrected current value for the same canonical person, retire the stale
    # latest-snapshot value from the current season. Preserve earlier seasons by
    # closing the old interval immediately before the current observation season.
    reconciled_mappings: list[dict[str, Any]] = []
    for item in mappings:
        provider = str(item.get("Provider") or "")
        external_id = str(item.get("ExternalID") or "")
        internal_id = str(item.get("CanonicalPlayerID") or "")
        current_values = current_values_by_owner_provider.get((internal_id, provider))
        if provider not in ANCHOR_ID_KEYS or not current_values or external_id in current_values:
            reconciled_mappings.append(item)
            continue

        first = int(item.get("FirstObservedSeason") or observation_season)
        last = int(item.get("LastObservedSeason") or first)
        if last < observation_season or first > observation_season:
            reconciled_mappings.append(item)
            continue
        if first < observation_season:
            item["LastObservedSeason"] = observation_season - 1
            reconciled_mappings.append(item)
            continue
        # first == observation_season: this value only came from an earlier
        # snapshot inside the same season and is no longer current evidence.
        # Git history retains that raw observation; season-resolution mappings
        # must not pretend it remained valid for the whole season.

    mappings = reconciled_mappings

    # Rule ``placeholderGsisUpgrade``: a current claim that moved from a
    # placeholder-GSIS record to the valid-GSIS record retires the previous
    # owner's current-season mapping and conflicts for that token, so the token
    # does not turn into an ambiguous two-owner claim. Earlier seasons stay.
    transfer_reconciliations = _retire_transferred_claims(
        provider_claims, mappings, conflicts, observation_season
    )
    if transfer_reconciliations:
        known = {
            _transfer_reconciliation_key(item)
            for item in persisted_history.get("HistoricalMappingReconciliations", [])
        }
        persisted_history["HistoricalMappingReconciliations"] = [
            *persisted_history.get("HistoricalMappingReconciliations", []),
            *(
                item
                for item in transfer_reconciliations
                if _transfer_reconciliation_key(item) not in known
            ),
        ]

    def mapping_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("Provider") or ""),
            str(item.get("ExternalID") or ""),
            str(item.get("CanonicalPlayerID") or ""),
        )

    mapping_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    mappings_by_token: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in mappings:
        key = mapping_key(item)
        mapping_by_key[key] = item
        mappings_by_token[(key[0], key[1])].append(item)

    for claim in provider_claims:
        provider = str(claim["Provider"])
        external_id = str(claim["ExternalID"])
        internal_id = str(claim["CanonicalPlayerID"])
        key = (provider, external_id, internal_id)
        token = (provider, external_id)
        # Historical evidence can add an exact mapping for an earlier season.
        # Its existence does not make the current-season claim safe: check other
        # owners before extending its interval or merging current provenance.
        overlapping = [
            item
            for item in mappings_by_token.get(token, [])
            if str(item.get("CanonicalPlayerID")) != internal_id
            and int(item.get("FirstObservedSeason") or observation_season) <= observation_season
            <= int(item.get("LastObservedSeason") or observation_season)
        ]
        if overlapping:
            owners = sorted({internal_id, *(str(item.get("CanonicalPlayerID")) for item in overlapping)})
            mapping_conflicts.append(
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerIDs": owners,
                    "SourcesByCanonicalPlayerID": {
                        internal_id: sorted(claim.get("Sources") or [])
                    },
                }
            )
            continue

        exact = mapping_by_key.get(key)
        if exact is not None:
            first = int(exact.get("FirstObservedSeason") or observation_season)
            last = int(exact.get("LastObservedSeason") or observation_season)
            exact["FirstObservedSeason"] = min(first, observation_season)
            exact["LastObservedSeason"] = max(last, observation_season)
            exact["Sources"] = sorted(
                set(exact.get("Sources") or []) | set(claim.get("Sources") or [])
            )
            continue

        item = {
            "Provider": provider,
            "ExternalID": external_id,
            "CanonicalPlayerID": internal_id,
            "FirstObservedSeason": observation_season,
            "LastObservedSeason": observation_season,
            "Sources": sorted(claim.get("Sources") or []),
        }
        mappings.append(item)
        mapping_by_key[key] = item
        mappings_by_token[token].append(item)

    def conflict_key(item: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
        return (
            str(item.get("Provider") or ""),
            str(item.get("ExternalID") or ""),
            tuple(sorted(str(value) for value in item.get("CanonicalPlayerIDs") or [])),
        )

    conflict_by_key = {conflict_key(item): item for item in conflicts}

    for conflict in mapping_conflicts:
        provider = str(conflict.get("Provider") or "")
        external_id = str(conflict.get("ExternalID") or "")
        owners = sorted(str(value) for value in conflict.get("CanonicalPlayerIDs") or [])
        key = (provider, external_id, tuple(owners))
        same = conflict_by_key.get(key)
        if same is None:
            same = {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerIDs": owners,
                "FirstObservedSeason": observation_season,
                "LastObservedSeason": observation_season,
                "Status": "ambiguous",
            }
            conflicts.append(same)
            conflict_by_key[key] = same
        else:
            same["FirstObservedSeason"] = min(
                int(same.get("FirstObservedSeason") or observation_season),
                observation_season,
            )
            same["LastObservedSeason"] = max(
                int(same.get("LastObservedSeason") or observation_season),
                observation_season,
            )

        sources_by_player = conflict.get("SourcesByCanonicalPlayerID") or {}
        if sources_by_player:
            merged = {
                key: set(values or [])
                for key, values in (same.get("SourcesByCanonicalPlayerID") or {}).items()
            }
            for internal_id, values in sources_by_player.items():
                merged.setdefault(internal_id, set()).update(values or [])
            same["SourcesByCanonicalPlayerID"] = {
                key: sorted(values) for key, values in sorted(merged.items())
            }

    mappings.sort(
        key=lambda item: (
            item["Provider"],
            item["ExternalID"],
            item["FirstObservedSeason"],
            item["CanonicalPlayerID"],
        )
    )
    conflicts.sort(
        key=lambda item: (
            item["Provider"],
            item["ExternalID"],
            item["FirstObservedSeason"],
            tuple(item["CanonicalPlayerIDs"]),
        )
    )

    payload = {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "TemporalResolution": "season",
        "Mappings": mappings,
        "Conflicts": conflicts,
        **persisted_history,
    }
    known_canonical_ids = {
        str(item.get("CanonicalPlayerID") or "")
        for item in mappings
        if str(item.get("CanonicalPlayerID") or "")
    }
    known_canonical_ids.update(
        str(claim.get("CanonicalPlayerID") or "")
        for claim in provider_claims
        if str(claim.get("CanonicalPlayerID") or "")
    )
    for conflict in conflicts:
        known_canonical_ids.update(
            str(value)
            for value in conflict.get("CanonicalPlayerIDs") or []
            if str(value)
        )

    adjudication_claims = load_identity_adjudication_claims(
        repo_root,
        known_canonical_ids,
    )
    return apply_identity_adjudications(payload, adjudication_claims)


def retire_merged_duplicate_mappings(
    payload: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Re-own the persisted mappings of a merged (retired) duplicate to its target.

    A ``confirmed-canonical-duplicate-merge`` retires the duplicate's
    CanonicalPlayerID, so no persisted mapping or active conflict may keep
    pointing at it. Its mappings (every season) move to the target and merge with
    an equal mapping of the target; tokens the decision declares as contaminated
    belong to another person and are dropped from the duplicate. Conflicts that
    only existed between the duplicate and the target disappear, other conflicts
    keep their remaining owners. Historical resolution records and reconciliations
    stay as evidence. Without a merge decision the payload is returned unchanged.
    """
    merges = [d for d in decisions if d.get("ResolutionKind") == "confirmed-canonical-duplicate-merge"]
    if not merges:
        return payload
    target_of: dict[str, str] = {}
    contaminated: dict[str, set[tuple[str, str]]] = {}
    for decision in merges:
        for duplicate_id in decision["DuplicateCanonicalPlayerIDs"]:
            target_of[str(duplicate_id)] = str(decision["TargetCanonicalPlayerID"])
            contaminated[str(duplicate_id)] = {
                (str(t["Provider"]), str(t["ExternalID"]))
                for t in decision.get("ContaminatedTokens") or []
            }

    mappings: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    for item in payload.get("Mappings", []):
        owner = str(item.get("CanonicalPlayerID") or "")
        if owner not in target_of:
            mappings.append(item)
            continue
        token = (str(item.get("Provider")), str(item.get("ExternalID")))
        if token not in contaminated[owner]:
            moved.append({**item, "CanonicalPlayerID": target_of[owner]})
    for item in moved:
        # Only a mapping of the target whose interval overlaps or touches the moved
        # one is the same validity span; unrelated spans of the target stay as they are.
        same = next(
            (
                other
                for other in mappings
                if (other.get("Provider"), other.get("ExternalID"), other.get("CanonicalPlayerID"))
                == (item["Provider"], item["ExternalID"], item["CanonicalPlayerID"])
                and int(other["FirstObservedSeason"]) <= int(item["LastObservedSeason"]) + 1
                and int(item["FirstObservedSeason"]) <= int(other["LastObservedSeason"]) + 1
            ),
            None,
        )
        if same is None:
            mappings.append(item)
            continue
        same["FirstObservedSeason"] = min(int(same["FirstObservedSeason"]), int(item["FirstObservedSeason"]))
        same["LastObservedSeason"] = max(int(same["LastObservedSeason"]), int(item["LastObservedSeason"]))
        same["Sources"] = sorted(set(same.get("Sources") or []) | set(item.get("Sources") or []))
    if moved:
        mappings.sort(
            key=lambda item: (
                item["Provider"], item["ExternalID"],
                item["FirstObservedSeason"], item["CanonicalPlayerID"],
            )
        )

    conflicts: list[dict[str, Any]] = []
    for conflict in payload.get("Conflicts", []):
        owners = [str(v) for v in conflict.get("CanonicalPlayerIDs") or []]
        if not any(owner in target_of for owner in owners):
            conflicts.append(conflict)
            continue
        token = (str(conflict.get("Provider")), str(conflict.get("ExternalID")))
        remaining: list[str] = []
        sources: dict[str, set[str]] = defaultdict(set)
        for owner in owners:
            if owner in target_of and token in contaminated[owner]:
                continue
            new_owner = target_of.get(owner, owner)
            if new_owner not in remaining:
                remaining.append(new_owner)
            sources[new_owner].update(
                str(v) for v in (conflict.get("SourcesByCanonicalPlayerID") or {}).get(owner, [])
            )
        if len(remaining) < 2:
            continue
        rebuilt = {**conflict, "CanonicalPlayerIDs": sorted(remaining)}
        if conflict.get("SourcesByCanonicalPlayerID"):
            rebuilt["SourcesByCanonicalPlayerID"] = {
                owner: sorted(values) for owner, values in sorted(sources.items()) if values
            }
        conflicts.append(rebuilt)
    return {**payload, "Mappings": mappings, "Conflicts": conflicts}
