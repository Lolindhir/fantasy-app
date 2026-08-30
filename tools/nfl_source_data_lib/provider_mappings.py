from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import CANONICAL_SCHEMA_VERSION, load_json, normalize_legacy_canonical_player_fields
from .identity_model import ANCHOR_ID_KEYS


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

    path = repo_root / "source-data/nfl/identities/provider-mappings.json"
    existing = normalize_legacy_canonical_player_fields(load_json(path, {}) or {})
    mappings = [dict(item) for item in existing.get("Mappings", [])]
    conflicts = [dict(item) for item in existing.get("Conflicts", [])]

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

        token = (provider, external_id)
        overlapping = [
            item
            for item in mappings_by_token.get(token, [])
            if int(item.get("FirstObservedSeason") or observation_season) <= observation_season
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
    return {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "TemporalResolution": "season",
        "Mappings": mappings,
        "Conflicts": conflicts,
    }
