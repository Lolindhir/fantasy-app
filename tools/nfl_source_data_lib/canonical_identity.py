from __future__ import annotations

from typing import Any

from .common import (
    CANONICAL_PLAYER_ID_FIELD,
    CANONICAL_PLAYER_IDS_FIELD,
    clean,
    normalize_legacy_canonical_player_fields,
)
from .historical_identity import PLAYER_STATS_VERIFIED_PROVIDER_ALIASES
from .identity_model import LINK_ID_KEYS


def identity_lookup(canonical: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    """Build reverse provider-ID lookup from the current canonical identity schema."""
    lookup: dict[tuple[str, str], str] = {}
    for raw_row in canonical:
        row = normalize_legacy_canonical_player_fields(raw_row)
        canonical_player_id = clean(row.get(CANONICAL_PLAYER_ID_FIELD))
        if not canonical_player_id:
            raise ValueError("Canonical identity row is missing CanonicalPlayerID")

        mappings = [
            (key, value)
            for key, value in (row.get("IDs") or {}).items()
            if key in LINK_ID_KEYS
        ]
        for key, values in (row.get("IDAliases") or {}).items():
            if key in LINK_ID_KEYS:
                mappings.extend((key, value) for value in values or [])

        for key, value in mappings:
            token = (key, str(value))
            previous = lookup.get(token)
            if previous and previous != canonical_player_id:
                raise ValueError(f"Link ID {key}:{value} maps to multiple canonical players")
            lookup[token] = canonical_player_id

    # A tiny set of legacy nflverse player-stat tokens are synthetic rather than
    # ordinary GSIS IDs. Resolve them only through an independently verified
    # provider bridge to an already-canonical person. The synthetic token is not
    # promoted into the person's active canonical IDs/aliases.
    for legacy_source_id, alias in sorted(PLAYER_STATS_VERIFIED_PROVIDER_ALIASES.items()):
        target_provider = alias["TargetProvider"]
        target_id = alias["TargetID"]
        target = lookup.get((target_provider, target_id))
        if not target:
            raise ValueError(
                "Verified historical player-stat alias target is unresolved: "
                f"{legacy_source_id} -> {target_provider}:{target_id}"
            )
        token = ("GSIS", legacy_source_id)
        previous = lookup.get(token)
        if previous and previous != target:
            raise ValueError(
                f"Verified historical player-stat alias {legacy_source_id} conflicts with canonical GSIS ownership"
            )
        lookup[token] = target
    return lookup


def provider_mapping_lookup(
    payload: dict[str, Any],
    provider: str,
    external_id: str,
    season: int,
) -> str | None:
    """Resolve a season-aware external provider ID to one CanonicalPlayerID."""
    normalized = normalize_legacy_canonical_player_fields(payload)
    provider = str(provider)
    external_id = str(external_id)
    season = int(season)

    for conflict in normalized.get("Conflicts", []) or []:
        if conflict.get("Provider") != provider or str(conflict.get("ExternalID")) != external_id:
            continue
        first = int(conflict.get("FirstObservedSeason") or season)
        last = int(conflict.get("LastObservedSeason") or first)
        if first <= season <= last:
            return None

    matches: list[str] = []
    for mapping in normalized.get("Mappings", []) or []:
        if mapping.get("Provider") != provider or str(mapping.get("ExternalID")) != external_id:
            continue
        first = int(mapping.get("FirstObservedSeason") or season)
        last = int(mapping.get("LastObservedSeason") or first)
        if first <= season <= last:
            value = clean(mapping.get(CANONICAL_PLAYER_ID_FIELD))
            if value:
                matches.append(value)
    unique = sorted(set(matches))
    return unique[0] if len(unique) == 1 else None


def conflict_canonical_player_ids(conflict: dict[str, Any]) -> list[str]:
    normalized = normalize_legacy_canonical_player_fields(conflict)
    return sorted(str(value) for value in normalized.get(CANONICAL_PLAYER_IDS_FIELD) or [])
