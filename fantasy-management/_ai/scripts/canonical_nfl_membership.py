#!/usr/bin/env python3
"""Canonical NFL roster membership evidence for Fantasy Operations population.

Membership is resolved only from persisted canonical NFL roster facts
(``source-data/nfl/rosters`` and ``source-data/nfl/weekly-rosters``) by
CanonicalPlayerID. Provider team fields (Sleeper Team, Tank01 TeamAbbr/IsFreeAgent)
and name matching never create membership.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fantasy_operations_inputs as ops  # noqa: E402


class CanonicalNflMembershipError(RuntimeError):
    """Raised when canonical NFL roster membership cannot be resolved safely."""


def roster_records(document: Any, *, source_name: str) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise CanonicalNflMembershipError(f"{source_name} must be a JSON object")
    records = document.get("Records")
    if not isinstance(records, list):
        raise CanonicalNflMembershipError(f"{source_name} must contain Records[]")
    if any(not isinstance(row, dict) for row in records):
        raise CanonicalNflMembershipError(f"{source_name} Records must contain objects")
    return records


def _canonical_id(identity: dict[str, Any]) -> str | None:
    return ops.optional_text(identity.get("CanonicalPlayerID"))


def build_roster_membership_index(
    document: Any,
    identity_by_sleeper: dict[str, dict[str, Any]],
    *,
    source_name: str,
) -> dict[str, Any]:
    sleeper_ids: set[str] = set()
    canonical_ids: set[str] = set()
    current_sleeper_mapping_mismatch_count = 0
    unresolved_record_count = 0
    records = roster_records(document, source_name=source_name)

    for row in records:
        canonical_id = ops.optional_text(row.get("CanonicalPlayerID"))
        source_ids = row.get("SourceIDs") if isinstance(row.get("SourceIDs"), dict) else {}
        sleeper_id = ops.optional_text(source_ids.get("Sleeper"))

        # Canonical roster history is sticky. A SourceIDs.Sleeper value on the
        # roster row is evidence captured with that canonical row; a later/current
        # Sleeper mapping must not reinterpret CanonicalPlayerID.
        if canonical_id:
            canonical_ids.add(canonical_id)
            if sleeper_id:
                identity = identity_by_sleeper.get(sleeper_id)
                identity_canonical_id = _canonical_id(identity) if identity else None
                if identity_canonical_id == canonical_id:
                    sleeper_ids.add(sleeper_id)
                elif identity_canonical_id and identity_canonical_id != canonical_id:
                    current_sleeper_mapping_mismatch_count += 1
            continue

        # Do not manufacture canonical NFL-membership evidence for unresolved
        # canonical rows from a current provider mapping alone.
        unresolved_record_count += 1

    return {
        "sleeper_ids": sleeper_ids,
        "canonical_ids": canonical_ids,
        "record_count": len(records),
        "current_sleeper_mapping_mismatch_count": current_sleeper_mapping_mismatch_count,
        "unresolved_record_count": unresolved_record_count,
    }


def in_roster_membership(
    player_id: str,
    identity: dict[str, Any],
    membership: dict[str, Any],
) -> bool:
    canonical_id = _canonical_id(identity)
    return (
        player_id in membership["sleeper_ids"]
        or bool(canonical_id and canonical_id in membership["canonical_ids"])
    )


def list_weekly_roster_partitions(root: Path, season: int) -> list[tuple[int, Path]]:
    directory = root / "source-data" / "nfl" / "weekly-rosters" / str(season)
    if not directory.is_dir():
        raise CanonicalNflMembershipError(
            f"Canonical weekly-roster directory is missing for season {season}: {directory}"
        )
    partitions: list[tuple[int, Path]] = []
    for path in directory.glob("*.json"):
        try:
            week = int(path.stem)
        except ValueError:
            continue
        partitions.append((week, path))
    if not partitions:
        raise CanonicalNflMembershipError(
            f"No canonical weekly-roster partitions found for season {season}"
        )
    partitions.sort(key=lambda item: item[0])
    return partitions


def resolve_latest_weekly_roster_path(root: Path, season: int) -> tuple[int, Path]:
    return list_weekly_roster_partitions(root, season)[-1]


def build_weekly_history_membership(
    root: Path,
    season: int,
    identity_by_sleeper: dict[str, dict[str, Any]],
    *,
    include_documents: bool = False,
) -> dict[str, Any]:
    partitions = list_weekly_roster_partitions(root, season)
    sleeper_ids: set[str] = set()
    canonical_ids: set[str] = set()
    documents: list[tuple[int, Any]] = []
    record_count = mismatch_count = unresolved_count = 0
    for week, path in partitions:
        document = ops.load_json(path)
        membership = build_roster_membership_index(
            document,
            identity_by_sleeper,
            source_name=str(path.relative_to(root)),
        )
        sleeper_ids.update(membership["sleeper_ids"])
        canonical_ids.update(membership["canonical_ids"])
        record_count += int(membership["record_count"])
        mismatch_count += int(membership["current_sleeper_mapping_mismatch_count"])
        unresolved_count += int(membership["unresolved_record_count"])
        if include_documents:
            documents.append((week, document))

    result: dict[str, Any] = {
        "sleeper_ids": sleeper_ids,
        "canonical_ids": canonical_ids,
        "weeks": [week for week, _ in partitions],
        "partition_count": len(partitions),
        "record_count": record_count,
        "current_sleeper_mapping_mismatch_count": mismatch_count,
        "unresolved_record_count": unresolved_count,
        "paths": [path for _, path in partitions],
    }
    if include_documents:
        result["documents"] = documents
    return result


def load_current_season_membership(
    root: Path,
    season: int,
    identity_by_sleeper: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve latest-week membership and current-season history.

    * ``latest_weekly``: membership in the latest materialized weekly roster.
    * ``current_history``: season roster or any current-season weekly roster.
    """

    season_roster_path = root / "source-data" / "nfl" / "rosters" / f"{season}.json"
    if not season_roster_path.is_file():
        raise CanonicalNflMembershipError(
            f"Canonical season roster is missing for {season}: {season_roster_path}"
        )
    season_membership = build_roster_membership_index(
        ops.load_json(season_roster_path),
        identity_by_sleeper,
        source_name=str(season_roster_path.relative_to(root)),
    )
    weekly_history = build_weekly_history_membership(root, season, identity_by_sleeper)
    latest_week = weekly_history["weeks"][-1]
    latest_path = weekly_history["paths"][-1]
    latest_weekly = build_roster_membership_index(
        ops.load_json(latest_path),
        identity_by_sleeper,
        source_name=str(latest_path.relative_to(root)),
    )
    return {
        "season": season,
        "latest_week": latest_week,
        "season_roster_path": season_roster_path,
        "latest_weekly_path": latest_path,
        "weekly_paths": weekly_history["paths"],
        "season_roster": season_membership,
        "weekly_history": weekly_history,
        "latest_weekly": latest_weekly,
    }


def membership_flags(
    player_id: str,
    identity: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, bool]:
    latest = in_roster_membership(player_id, identity, evidence["latest_weekly"])
    history = (
        in_roster_membership(player_id, identity, evidence["season_roster"])
        or in_roster_membership(player_id, identity, evidence["weekly_history"])
    )
    return {"latest_weekly_member": latest, "current_season_history_member": history}
