from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import clean, load_json
from .historical_identity import non_player_stat_identity


def build_player_stats_identity_coverage(
    repo_root: Path,
    *,
    current_season: int,
) -> dict[str, Any]:
    """Audit canonical player-stat identity coverage independently of League providers.

    Canonical NFL player stats are keyed by nflverse/GSIS evidence. Sleeper IDs and
    archived app Players.json snapshots are intentionally not part of this check.
    Explicit upstream non-player aggregate sentinels remain observable, but they do
    not count as unresolved people and must never receive a CanonicalPlayerID.
    """

    root = repo_root / "source-data/nfl/player-stats"
    by_season: dict[str, dict[str, Any]] = {}
    gsis_to_canonical: dict[str, set[str]] = defaultdict(set)
    canonical_to_seasons: dict[str, set[int]] = defaultdict(set)

    historical_record_count = 0
    historical_resolved_count = 0
    historical_unresolved_count = 0
    historical_missing_gsis_count = 0
    historical_non_player_count = 0
    historical_unresolved_gsis: set[str] = set()
    historical_non_player_ids: set[str] = set()
    current_record_count = 0
    current_resolved_count = 0
    current_unresolved_count = 0
    current_missing_gsis_count = 0
    current_non_player_count = 0
    current_unresolved_gsis: set[str] = set()
    current_non_player_ids: set[str] = set()
    invalid_non_player_assignments: list[dict[str, str]] = []

    if not root.exists():
        return {
            "HistoricalRecordCount": 0,
            "HistoricalResolvedRecordCount": 0,
            "HistoricalUnresolvedRecordCount": 0,
            "HistoricalMissingGSISRecordCount": 0,
            "HistoricalNonPlayerAggregateRecordCount": 0,
            "HistoricalNonPlayerSourceIDs": [],
            "HistoricalUnresolvedUniqueGSISCount": 0,
            "HistoricalUnresolvedGSISIDs": [],
            "CurrentRecordCount": 0,
            "CurrentResolvedRecordCount": 0,
            "CurrentUnresolvedRecordCount": 0,
            "CurrentMissingGSISRecordCount": 0,
            "CurrentNonPlayerAggregateRecordCount": 0,
            "CurrentNonPlayerSourceIDs": [],
            "CurrentUnresolvedUniqueGSISCount": 0,
            "CurrentUnresolvedGSISIDs": [],
            "InvalidNonPlayerCanonicalAssignmentCount": 0,
            "InvalidNonPlayerCanonicalAssignments": [],
            "GSISCanonicalConflictCount": 0,
            "GSISCanonicalConflicts": [],
            "MultiSeasonCanonicalPlayerCount": 0,
            "BySeason": {},
            "Ready": False,
        }

    for season_dir in sorted(
        (path for path in root.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: int(path.name),
    ):
        season = int(season_dir.name)
        historical = season < int(current_season)
        record_count = 0
        resolved_count = 0
        unresolved_count = 0
        missing_gsis_count = 0
        non_player_count = 0
        unresolved_gsis: set[str] = set()
        non_player_ids: set[str] = set()
        unique_gsis: set[str] = set()
        canonical_players: set[str] = set()

        for partition in sorted(season_dir.glob("*.json")):
            payload = load_json(partition, {}) or {}
            records = payload.get("Records", []) if isinstance(payload, dict) else []
            if not isinstance(records, list):
                raise ValueError(f"Canonical player-stats partition has non-list Records: {partition}")
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError(f"Canonical player-stats partition has non-object record: {partition}")
                record_count += 1
                source_ids = record.get("SourceIDs") or {}
                gsis = clean(source_ids.get("GSIS")) if isinstance(source_ids, dict) else None
                canonical_player_id = clean(record.get("CanonicalPlayerID"))
                non_player = non_player_stat_identity(gsis)

                if not gsis:
                    missing_gsis_count += 1
                else:
                    unique_gsis.add(gsis)

                if non_player is not None:
                    non_player_count += 1
                    if gsis:
                        non_player_ids.add(gsis)
                    if canonical_player_id:
                        invalid_non_player_assignments.append(
                            {
                                "Season": str(season),
                                "SourceID": gsis or "",
                                "CanonicalPlayerID": canonical_player_id,
                            }
                        )
                    continue

                if canonical_player_id:
                    resolved_count += 1
                    canonical_players.add(canonical_player_id)
                    canonical_to_seasons[canonical_player_id].add(season)
                    if gsis:
                        gsis_to_canonical[gsis].add(canonical_player_id)
                else:
                    unresolved_count += 1
                    if gsis:
                        unresolved_gsis.add(gsis)

        by_season[str(season)] = {
            "Historical": historical,
            "RecordCount": record_count,
            "ResolvedRecordCount": resolved_count,
            "UnresolvedRecordCount": unresolved_count,
            "MissingGSISRecordCount": missing_gsis_count,
            "NonPlayerAggregateRecordCount": non_player_count,
            "NonPlayerSourceIDs": sorted(non_player_ids),
            "UniqueGSISCount": len(unique_gsis),
            "ResolvedCanonicalPlayerCount": len(canonical_players),
            "UnresolvedUniqueGSISCount": len(unresolved_gsis),
            "UnresolvedGSISIDs": sorted(unresolved_gsis),
        }

        if historical:
            historical_record_count += record_count
            historical_resolved_count += resolved_count
            historical_unresolved_count += unresolved_count
            historical_missing_gsis_count += missing_gsis_count
            historical_non_player_count += non_player_count
            historical_unresolved_gsis.update(unresolved_gsis)
            historical_non_player_ids.update(non_player_ids)
        else:
            current_record_count += record_count
            current_resolved_count += resolved_count
            current_unresolved_count += unresolved_count
            current_missing_gsis_count += missing_gsis_count
            current_non_player_count += non_player_count
            current_unresolved_gsis.update(unresolved_gsis)
            current_non_player_ids.update(non_player_ids)

    conflicts = [
        {"GSIS": gsis, "CanonicalPlayerIDs": sorted(canonical_ids)}
        for gsis, canonical_ids in sorted(gsis_to_canonical.items())
        if len(canonical_ids) > 1
    ]
    multi_season_player_count = sum(1 for seasons in canonical_to_seasons.values() if len(seasons) > 1)

    return {
        "HistoricalRecordCount": historical_record_count,
        "HistoricalResolvedRecordCount": historical_resolved_count,
        "HistoricalUnresolvedRecordCount": historical_unresolved_count,
        "HistoricalMissingGSISRecordCount": historical_missing_gsis_count,
        "HistoricalNonPlayerAggregateRecordCount": historical_non_player_count,
        "HistoricalNonPlayerSourceIDs": sorted(historical_non_player_ids),
        "HistoricalUnresolvedUniqueGSISCount": len(historical_unresolved_gsis),
        "HistoricalUnresolvedGSISIDs": sorted(historical_unresolved_gsis),
        "CurrentRecordCount": current_record_count,
        "CurrentResolvedRecordCount": current_resolved_count,
        "CurrentUnresolvedRecordCount": current_unresolved_count,
        "CurrentMissingGSISRecordCount": current_missing_gsis_count,
        "CurrentNonPlayerAggregateRecordCount": current_non_player_count,
        "CurrentNonPlayerSourceIDs": sorted(current_non_player_ids),
        "CurrentUnresolvedUniqueGSISCount": len(current_unresolved_gsis),
        "CurrentUnresolvedGSISIDs": sorted(current_unresolved_gsis),
        "InvalidNonPlayerCanonicalAssignmentCount": len(invalid_non_player_assignments),
        "InvalidNonPlayerCanonicalAssignments": invalid_non_player_assignments,
        "GSISCanonicalConflictCount": len(conflicts),
        "GSISCanonicalConflicts": conflicts,
        "MultiSeasonCanonicalPlayerCount": multi_season_player_count,
        "BySeason": by_season,
        "Ready": (
            historical_unresolved_count == 0
            and historical_missing_gsis_count == 0
            and not invalid_non_player_assignments
            and not conflicts
        ),
    }
