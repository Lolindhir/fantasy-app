from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .common import IDENTITY_ID_KEYS, clean
from .draft import build_ff_draft_evidence, classify_draft_status
from .identity import LINK_ID_KEYS, WEAK_ID_KEYS, app_player_candidates, identity_lookup


def build_audit(
    repo_root: Path,
    canonical: list[dict[str, Any]],
    ff_rows: list[dict[str, str]],
    drafted_internal_ids: set[str],
    draft_seasons: Iterable[int],
    identity_source_conflicts: list[dict[str, Any]] | None = None,
    provider_mapping_conflicts: list[dict[str, Any]] | None = None,
    historical_mapping_stats: dict[str, int] | None = None,
    historical_resolution_conflicts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    _, relevant_players = app_player_candidates(repo_root)
    lookup = identity_lookup(canonical)
    canonical_by_internal = {row["NFLPlayerID"]: row for row in canonical}
    ff_evidence = build_ff_draft_evidence(ff_rows, canonical)
    max_draft_season = max(draft_seasons, default=None)
    identity_counts, draft_counts = Counter(), Counter()
    by_position: dict[str, Counter[str]] = defaultdict(Counter)
    matched_by_provider = Counter()
    unmatched, unknown_draft = [], []

    for player in relevant_players:
        sleeper = clean(player.get("ID"))
        tank = clean(player.get("TankID"))
        internal_id = lookup.get(("Sleeper", sleeper)) if sleeper else None
        matched_provider = "Sleeper" if internal_id else None
        if internal_id is None and tank:
            internal_id = lookup.get(("Tank01", tank))
            if internal_id:
                matched_provider = "Tank01"
        position = clean(player.get("Position")) or "UNKNOWN"
        name = clean(player.get("Name")) or clean(player.get("FullName"))
        if internal_id:
            identity_counts["matched"] += 1
            matched_by_provider[matched_provider or "unknown"] += 1
            if canonical_by_internal[internal_id].get("IDs", {}).get("GSIS"):
                identity_counts["withGSIS"] += 1
            else:
                identity_counts["withoutGSIS"] += 1
        else:
            identity_counts["unmatched"] += 1
            unmatched.append({"SleeperID": sleeper, "Tank01ID": tank, "Name": name, "Position": position})
        status, draft_year = classify_draft_status(
            internal_id, ff_evidence, drafted_internal_ids, max_draft_season
        )
        draft_counts[status] += 1
        by_position[position][status] += 1
        if status == "unknown":
            unknown_draft.append(
                {
                    "SleeperID": sleeper,
                    "Tank01ID": tank,
                    "NFLPlayerID": internal_id,
                    "Name": name,
                    "Position": position,
                    "DraftYear": draft_year,
                }
            )

    alias_counts = Counter()
    provider_value_owners: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in canonical:
        internal_id = row["NFLPlayerID"]
        for key, value in (row.get("IDs") or {}).items():
            provider_value_owners[key][value].add(internal_id)
        for key, aliases in (row.get("IDAliases") or {}).items():
            alias_counts[key] += len(aliases or [])
            for value in aliases or []:
                provider_value_owners[key][value].add(internal_id)

    link_duplicates = {}
    weak_collisions = {}
    for key in IDENTITY_ID_KEYS:
        duplicates = sorted(
            value
            for value, owners in provider_value_owners.get(key, {}).items()
            if len(owners) > 1
        )
        if not duplicates:
            continue
        if key in LINK_ID_KEYS:
            link_duplicates[key] = duplicates
        elif key in WEAK_ID_KEYS:
            weak_collisions[key] = duplicates

    source_conflicts = identity_source_conflicts or []
    source_conflicts_by_reason = Counter(item.get("Reason") or "unknown" for item in source_conflicts)
    mapping_conflicts = provider_mapping_conflicts or []
    mapping_conflicts_by_provider = Counter(item.get("Provider") or "unknown" for item in mapping_conflicts)
    history_stats = dict(historical_mapping_stats or {})
    history_conflicts = historical_resolution_conflicts or []
    history_conflicts_by_reason = Counter(item.get("Reason") or "unknown" for item in history_conflicts)
    return {
        "schemaVersion": 1,
        "scope": "public/data/Players_Relevant.json",
        "canonicalIdentityCount": len(canonical),
        "relevantPlayerCount": len(relevant_players),
        "identityCoverage": dict(identity_counts),
        "identityCoverageByProvider": dict(sorted(matched_by_provider.items())),
        "draftStatusCoverage": dict(draft_counts),
        "draftStatusByPosition": {
            position: dict(counts) for position, counts in sorted(by_position.items())
        },
        "identityInvariantViolations": {
            "duplicateLinkProviderIDs": link_duplicates,
            "duplicateLinkProviderIDCount": sum(len(values) for values in link_duplicates.values()),
        },
        "identityWeakProviderCollisionCount": sum(len(values) for values in weak_collisions.values()),
        "identityWeakProviderCollisions": weak_collisions,
        "identityAliasCount": sum(alias_counts.values()),
        "identityAliasesByProvider": dict(sorted(alias_counts.items())),
        "identitySourceMappingConflictCount": len(source_conflicts),
        "identitySourceMappingConflictsByReason": dict(source_conflicts_by_reason),
        "identitySourceMappingConflicts": source_conflicts,
        "providerMappingConflictCount": len(mapping_conflicts),
        "providerMappingConflictsByProvider": dict(sorted(mapping_conflicts_by_provider.items())),
        "providerMappingConflicts": mapping_conflicts,
        "historicalAppMappingCoverage": history_stats,
        "historicalResolutionConflictCount": len(history_conflicts),
        "historicalResolutionConflictsByReason": dict(sorted(history_conflicts_by_reason.items())),
        "historicalResolutionConflicts": history_conflicts,
        "unmatchedRelevantPlayers": unmatched,
        "unknownDraftStatusRelevantPlayers": unknown_draft,
        "rules": {
            "drafted": "Player resolves to a canonical pick in nflverse.draft-picks.",
            "undrafted": "FF Player IDs has a concrete past/current draft year but no pick fields, and no canonical draft pick exists.",
            "unknown": "Identity or draft evidence is insufficient or contradictory; draft_year=0 is never treated as proof of UDFA.",
            "not_yet_drafted": "FF Player IDs points to a draft year later than the newest materialized draft season.",
            "linkProviderID": "Link-provider IDs support reverse lookup only while their mapping is unambiguous; they do not unconditionally merge distinct person components.",
            "weakProviderID": "Weak provider IDs are retained as attributes but never merge identities; cross-player collisions are audited instead.",
            "historicalProviderMapping": "Provider mappings are stored separately with season-level observation history. Archived app snapshots may backfill Sleeper, Tank01 and ESPN only when at least two independently resolved provider IDs agree on one canonical person.",
            "quarantinedProviderMapping": "A provider ID that currently claims multiple distinguishable people is suppressed from canonical reverse lookup and recorded as ambiguous instead of merging those people.",
            "historicalSnapshotConflict": "If resolved provider IDs from one archived player snapshot disagree, no historical mapping from that row is accepted. A single resolved historical provider ID is also insufficient because later ID reuse cannot be excluded.",
            "quarantinedIdentityMapping": "FF Player IDs mappings that contradict nflverse.players on exact birth date do not participate in provider-ID resolution; when another exact-birthdate anchor corroborates the row, only the contradictory anchor mapping is suppressed, otherwise the row remains fully quarantined.",
        },
    }
