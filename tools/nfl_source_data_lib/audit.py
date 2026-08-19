from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .common import IDENTITY_ID_KEYS, clean, utc_now
from .draft import build_ff_draft_evidence, classify_draft_status
from .identity import app_player_candidates, identity_lookup


def build_audit(
    repo_root: Path,
    canonical: list[dict[str, Any]],
    ff_rows: list[dict[str, str]],
    drafted_internal_ids: set[str],
    draft_seasons: Iterable[int],
    identity_source_conflicts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    _, relevant_players = app_player_candidates(repo_root)
    lookup = identity_lookup(canonical)
    canonical_by_internal = {row["NFLPlayerID"]: row for row in canonical}
    ff_evidence = build_ff_draft_evidence(ff_rows, canonical)
    max_draft_season = max(draft_seasons, default=None)
    identity_counts, draft_counts = Counter(), Counter()
    by_position: dict[str, Counter[str]] = defaultdict(Counter)
    unmatched, unknown_draft = [], []

    for player in relevant_players:
        sleeper = clean(player.get("ID"))
        internal_id = lookup.get(("Sleeper", sleeper)) if sleeper else None
        position = clean(player.get("Position")) or "UNKNOWN"
        name = clean(player.get("Name")) or clean(player.get("FullName"))
        if internal_id:
            identity_counts["matched"] += 1
            if canonical_by_internal[internal_id].get("IDs", {}).get("GSIS"):
                identity_counts["withGSIS"] += 1
            else:
                identity_counts["withoutGSIS"] += 1
        else:
            identity_counts["unmatched"] += 1
            unmatched.append({"SleeperID": sleeper, "Name": name, "Position": position})
        status, draft_year = classify_draft_status(internal_id, ff_evidence, drafted_internal_ids, max_draft_season)
        draft_counts[status] += 1
        by_position[position][status] += 1
        if status == "unknown":
            unknown_draft.append({"SleeperID": sleeper, "NFLPlayerID": internal_id, "Name": name,
                                  "Position": position, "DraftYear": draft_year})

    provider_duplicates = {}
    alias_counts = Counter()
    for row in canonical:
        for key, aliases in (row.get("IDAliases") or {}).items():
            alias_counts[key] += len(aliases or [])
    for key in IDENTITY_ID_KEYS:
        values = [row.get("IDs", {}).get(key) for row in canonical if row.get("IDs", {}).get(key)]
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            provider_duplicates[key] = duplicates
    source_conflicts = identity_source_conflicts or []
    source_conflicts_by_reason = Counter(item.get("Reason") or "unknown" for item in source_conflicts)
    return {
        "schemaVersion": 1, "generatedAtUtc": utc_now(), "scope": "public/data/Players_Relevant.json",
        "canonicalIdentityCount": len(canonical), "relevantPlayerCount": len(relevant_players),
        "identityCoverage": dict(identity_counts), "draftStatusCoverage": dict(draft_counts),
        "draftStatusByPosition": {position: dict(counts) for position, counts in sorted(by_position.items())},
        "identityInvariantViolations": {"duplicateProviderIDs": provider_duplicates,
                                        "duplicateProviderIDCount": sum(len(values) for values in provider_duplicates.values())},
        "identityAliasCount": sum(alias_counts.values()),
        "identityAliasesByProvider": dict(sorted(alias_counts.items())),
        "identitySourceMappingConflictCount": len(source_conflicts),
        "identitySourceMappingConflictsByReason": dict(source_conflicts_by_reason),
        "identitySourceMappingConflicts": source_conflicts,
        "unmatchedRelevantPlayers": unmatched, "unknownDraftStatusRelevantPlayers": unknown_draft,
        "rules": {
            "drafted": "Player resolves to a canonical pick in nflverse.draft-picks.",
            "undrafted": "FF Player IDs has a concrete past/current draft year but no pick fields, and no canonical draft pick exists.",
            "unknown": "Identity or draft evidence is insufficient or contradictory; draft_year=0 is never treated as proof of UDFA.",
            "not_yet_drafted": "FF Player IDs points to a draft year later than the newest materialized draft season.",
            "verifiedProviderAlias": "Multiple IDs from an alias-capable provider are retained only when exact birth date and at least two other strong provider IDs corroborate the same player.",
            "quarantinedIdentityMapping": "FF Player IDs mappings that contradict nflverse.players on exact birth date do not participate in provider-ID merges; the row remains isolated by MFL primary key and the suppressed mappings are recorded here.",
        },
    }
