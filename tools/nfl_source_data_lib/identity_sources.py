from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import Dataset, clean, iter_csv, load_json
from .identity_model import (
    ANCHOR_ID_KEYS,
    IdentityCandidate,
    ids_from_ff,
    ids_from_players,
)


def _player_birthdate_anchors(player_rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    anchors: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in player_rows:
        birth_date = clean(row.get("birth_date"))
        if not birth_date:
            continue
        for key, value in ids_from_players(row).items():
            if key in ANCHOR_ID_KEYS:
                anchors[(key, value)].add(birth_date)
    return anchors


def _existing_mfl_replay_index(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Index canonical MFL evidence only for deterministic replay.

    MFL remains a weak provider ID and never becomes a general merge edge. The
    index is used solely to reconnect an unchanged, fully quarantined MFL-only row
    to the canonical identity created for that same row on a previous
    materialization. Exact birth-date evidence is required before replay.
    """

    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    by_mfl: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("Players", []) or []:
        values: set[str] = set()
        if value := clean((row.get("IDs") or {}).get("MFL")):
            values.add(value)
        for alias in (row.get("IDAliases") or {}).get("MFL", []) or []:
            if value := clean(alias):
                values.add(value)
        for value in values:
            by_mfl[value].append(row)
    return by_mfl


def _replay_existing_mfl_identity(
    by_mfl: dict[str, list[dict[str, Any]]],
    mfl_id: str | None,
    birth_date: str | None,
    position: str | None,
) -> str | None:
    if not mfl_id or not birth_date:
        return None
    matches: list[str] = []
    for row in by_mfl.get(mfl_id, []):
        if clean(row.get("BirthDate")) != birth_date:
            continue
        existing_position = clean(row.get("Position"))
        if position and existing_position and existing_position != position:
            continue
        if internal_id := clean(row.get("NFLPlayerID")):
            matches.append(internal_id)
    unique = sorted(set(matches))
    return unique[0] if len(unique) == 1 else None


def raw_identity_candidates(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[list[IdentityCandidate], list[dict[str, str]], list[IdentityCandidate | None], list[dict[str, Any]]]:
    candidates: list[IdentityCandidate] = []
    player_rows = list(iter_csv(datasets["nflverse.players"].raw_path))
    for row in player_rows:
        ids = ids_from_players(row)
        if not ids:
            continue
        candidates.append(
            IdentityCandidate(
                ids=ids,
                name=clean(row.get("display_name")),
                first_name=clean(row.get("first_name")) or clean(row.get("common_first_name")),
                last_name=clean(row.get("last_name")),
                birth_date=clean(row.get("birth_date")),
                position=clean(row.get("position")),
                latest_team=clean(row.get("latest_team")),
                source="nflverse.players",
                priority=10,
            )
        )

    anchors = _player_birthdate_anchors(player_rows)
    existing_by_mfl = _existing_mfl_replay_index(repo_root)
    ff_rows: list[dict[str, str]] = []
    ff_candidates: list[IdentityCandidate | None] = []
    source_conflicts: list[dict[str, Any]] = []

    for row in iter_csv(datasets["nflverse.ff-player-ids"].raw_path):
        ff_rows.append(row)
        raw_ids = ids_from_ff(row)
        ids = dict(raw_ids)
        birth_date = clean(row.get("birthdate"))
        position = clean(row.get("position"))
        conflicting_anchors: list[dict[str, Any]] = []
        matching_anchors: list[dict[str, Any]] = []

        if birth_date:
            for key in ANCHOR_ID_KEYS:
                value = raw_ids.get(key)
                if not value:
                    continue
                expected_birth_dates = sorted(anchors.get((key, value), set()))
                if not expected_birth_dates:
                    continue
                detail = {
                    "Provider": key,
                    "ID": value,
                    "NFLVerseBirthDates": expected_birth_dates,
                }
                if birth_date in expected_birth_dates:
                    matching_anchors.append(detail)
                else:
                    conflicting_anchors.append(detail)

        if conflicting_anchors:
            conflicting_keys = {item["Provider"] for item in conflicting_anchors}
            if matching_anchors:
                # One exact-birthdate anchor still identifies the person. Keep
                # unrelated provider mappings and suppress only contradicted anchors.
                suppressed = {
                    key: value
                    for key, value in raw_ids.items()
                    if key in conflicting_keys
                }
                ids = {
                    key: value
                    for key, value in raw_ids.items()
                    if key not in conflicting_keys
                }
                quarantine_scope = "mapping"
            else:
                # No authoritative NFL anchor corroborates this row's birth date.
                # Do not let provider-only IDs bootstrap a person from contradicted evidence.
                suppressed = {key: value for key, value in raw_ids.items() if key != "MFL"}
                ids = {"MFL": raw_ids["MFL"]} if raw_ids.get("MFL") else {}
                quarantine_scope = "row"

            source_conflicts.append(
                {
                    "Source": "nflverse.ff-player-ids",
                    "Reason": "birthdate_conflict_with_nflverse_players",
                    "QuarantineScope": quarantine_scope,
                    "MFLID": raw_ids.get("MFL"),
                    "Name": clean(row.get("name")),
                    "BirthDate": birth_date,
                    "Position": position,
                    "DraftYear": clean(row.get("draft_year")),
                    "ConflictingAnchors": conflicting_anchors,
                    "MatchingAnchors": matching_anchors,
                    "SuppressedIDs": suppressed,
                }
            )

        candidate = None
        if ids:
            existing_internal_id = None
            if set(ids) == {"MFL"}:
                existing_internal_id = _replay_existing_mfl_identity(
                    existing_by_mfl,
                    ids.get("MFL"),
                    birth_date,
                    position,
                )
            candidate = IdentityCandidate(
                ids=ids,
                name=clean(row.get("name")),
                first_name=None,
                last_name=None,
                birth_date=birth_date,
                position=position,
                latest_team=clean(row.get("team")),
                source="nflverse.ff-player-ids",
                priority=20,
                existing_internal_id=existing_internal_id,
            )
            candidates.append(candidate)
        ff_candidates.append(candidate)

    return candidates, ff_rows, ff_candidates, source_conflicts
