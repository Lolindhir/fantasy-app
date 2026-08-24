from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .canonical_identity import identity_lookup
from .common import clean, load_json, normalize_legacy_canonical_player_fields

_SEASON_FILE = re.compile(r"Players_(\d{4})\.json$")
_MIN_HISTORICAL_CORROBORATORS = 2


def _snapshot_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("Players", "players"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def build_historical_app_mapping_claims(
    repo_root: Path,
    canonical: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    lookup = identity_lookup(canonical)
    claims: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    stats = {
        "snapshotSeasonCount": 0,
        "snapshotPlayerCount": 0,
        "resolvedPlayerCount": 0,
        "unresolvedPlayerCount": 0,
        "insufficientCorroborationCount": 0,
        "conflictingPlayerCount": 0,
    }

    archive_root = repo_root / "public/data/past_seasons"
    for path in sorted(archive_root.glob("Players_*.json")):
        match = _SEASON_FILE.search(path.name)
        if not match:
            continue
        season = int(match.group(1))
        rows = _snapshot_rows(load_json(path, []) or [])
        stats["snapshotSeasonCount"] += 1
        stats["snapshotPlayerCount"] += len(rows)

        for row in rows:
            snapshot_ids = {
                "Sleeper": clean(row.get("ID")),
                "Tank01": clean(row.get("TankID")),
                "ESPN": clean(row.get("ESPNID")),
            }
            snapshot_ids = {key: value for key, value in snapshot_ids.items() if value}
            token_results: dict[str, str] = {}
            for provider, external_id in snapshot_ids.items():
                internal_id = lookup.get((provider, external_id))
                if internal_id:
                    token_results[provider] = internal_id

            resolved_ids = sorted(set(token_results.values()))
            if len(resolved_ids) > 1:
                stats["conflictingPlayerCount"] += 1
                conflicts.append(
                    {
                        "Reason": "historical_app_snapshot_provider_disagreement",
                        "Season": season,
                        "Name": clean(row.get("Name")) or clean(row.get("FullName")),
                        "Position": clean(row.get("Position")),
                        "SleeperID": snapshot_ids.get("Sleeper"),
                        "Tank01ID": snapshot_ids.get("Tank01"),
                        "ESPNID": snapshot_ids.get("ESPN"),
                        "ResolvedByProvider": dict(sorted(token_results.items())),
                    }
                )
                continue

            # Historical app snapshots do not contain an exact birth date. A
            # single provider ID is therefore not enough to backfill identity:
            # that ID may have been corrected or reused later. Require at least
            # two independently resolved provider IDs to agree before using the
            # archived row as season-specific evidence.
            if len(token_results) < _MIN_HISTORICAL_CORROBORATORS or not resolved_ids:
                stats["unresolvedPlayerCount"] += 1
                stats["insufficientCorroborationCount"] += 1
                continue

            stats["resolvedPlayerCount"] += 1
            internal_id = resolved_ids[0]
            for provider, external_id in sorted(snapshot_ids.items()):
                claims.append(
                    {
                        "Provider": provider,
                        "ExternalID": external_id,
                        "CanonicalPlayerID": internal_id,
                        "ObservedSeason": season,
                        "Sources": [f"app.PastPlayers.{season}"],
                    }
                )

    return claims, conflicts, stats


def extend_provider_mapping_payload(
    payload: dict[str, Any],
    claims: list[dict[str, Any]],
    resolution_conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = normalize_legacy_canonical_player_fields(payload)
    mappings = [dict(item) for item in payload.get("Mappings", [])]
    conflicts = [dict(item) for item in payload.get("Conflicts", [])]

    def interval(item: dict[str, Any], default_season: int) -> tuple[int, int]:
        first = int(item.get("FirstObservedSeason") or default_season)
        last = int(item.get("LastObservedSeason") or first)
        return first, last

    for claim in sorted(
        claims,
        key=lambda item: (
            int(item["ObservedSeason"]),
            item["Provider"],
            item["ExternalID"],
            item["CanonicalPlayerID"],
        ),
    ):
        provider = claim["Provider"]
        external_id = claim["ExternalID"]
        internal_id = claim["CanonicalPlayerID"]
        season = int(claim["ObservedSeason"])
        sources = set(claim.get("Sources") or [])

        active_conflict = False
        for conflict in conflicts:
            if conflict.get("Provider") != provider or str(conflict.get("ExternalID")) != str(external_id):
                continue
            first, last = interval(conflict, season)
            if first <= season <= last:
                active_conflict = True
                break
        if active_conflict:
            continue

        exact = next(
            (
                item
                for item in mappings
                if item.get("Provider") == provider
                and str(item.get("ExternalID")) == str(external_id)
                and item.get("CanonicalPlayerID") == internal_id
            ),
            None,
        )
        if exact is not None:
            first, last = interval(exact, season)
            exact["FirstObservedSeason"] = min(first, season)
            exact["LastObservedSeason"] = max(last, season)
            exact["Sources"] = sorted(set(exact.get("Sources") or []) | sources)
            continue

        overlaps = []
        for item in mappings:
            if item.get("Provider") != provider or str(item.get("ExternalID")) != str(external_id):
                continue
            first, last = interval(item, season)
            if first <= season <= last:
                overlaps.append(item)
        if overlaps:
            owners = sorted({internal_id, *(str(item.get("CanonicalPlayerID")) for item in overlaps)})
            conflicts.append(
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerIDs": owners,
                    "FirstObservedSeason": season,
                    "LastObservedSeason": season,
                    "Status": "ambiguous",
                    "Reason": "historical_mapping_overlap",
                    "SourcesByCanonicalPlayerID": {internal_id: sorted(sources)},
                }
            )
            continue

        mappings.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerID": internal_id,
                "FirstObservedSeason": season,
                "LastObservedSeason": season,
                "Sources": sorted(sources),
            }
        )

    # Provider disagreements in one archived app snapshot are evidence conflicts,
    # not safe provider mappings. Keep them separately without inventing a winner.
    history_resolution_conflicts = [dict(item) for item in payload.get("HistoricalResolutionConflicts", [])]
    known = {
        (
            item.get("Reason"),
            item.get("Season"),
            item.get("SleeperID"),
            item.get("Tank01ID"),
            item.get("ESPNID"),
        )
        for item in history_resolution_conflicts
    }
    for conflict in resolution_conflicts:
        key = (
            conflict.get("Reason"),
            conflict.get("Season"),
            conflict.get("SleeperID"),
            conflict.get("Tank01ID"),
            conflict.get("ESPNID"),
        )
        if key not in known:
            history_resolution_conflicts.append(conflict)
            known.add(key)

    mappings.sort(
        key=lambda item: (
            item["Provider"],
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            item["CanonicalPlayerID"],
        )
    )
    conflicts.sort(
        key=lambda item: (
            item["Provider"],
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            tuple(item["CanonicalPlayerIDs"]),
        )
    )
    history_resolution_conflicts.sort(
        key=lambda item: (
            int(item.get("Season") or 0),
            str(item.get("SleeperID") or ""),
            str(item.get("Tank01ID") or ""),
            str(item.get("ESPNID") or ""),
        )
    )
    return {
        **payload,
        "Mappings": mappings,
        "Conflicts": conflicts,
        "HistoricalResolutionConflicts": history_resolution_conflicts,
    }
