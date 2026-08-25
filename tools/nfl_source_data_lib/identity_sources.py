from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import Dataset, canonical_player_id, clean, iter_csv, load_json
from .identity_model import (
    ANCHOR_ID_KEYS,
    ATTACH_ID_KEYS,
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


def _is_weak_only(ids: dict[str, str]) -> bool:
    if not ids:
        return False
    strong_or_attach = set(ANCHOR_ID_KEYS) | set(ATTACH_ID_KEYS)
    return not any(key in strong_or_attach for key in ids)


def _replay_signature(
    ids: dict[str, str],
    birth_date: str | None,
    position: str | None,
    name: str | None,
) -> tuple[tuple[tuple[str, str], ...], str, str, str] | None:
    """Return exact canonical-visible evidence for weak-only replay.

    This signature is never used to merge two current candidates. It only lets an
    unchanged weak-only current candidate reconnect to one canonical identity that
    this pipeline already materialized previously. Provider names remain
    non-authoritative: name participates only as an exact replay discriminator.
    """

    if not _is_weak_only(ids):
        return None
    return (
        tuple(sorted((key, value) for key, value in ids.items())),
        clean(birth_date) or "",
        clean(position) or "",
        (clean(name) or "").casefold(),
    )


def _existing_weak_replay_index(
    repo_root: Path,
) -> dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]]:
    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    index: dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]] = defaultdict(set)
    for row in payload.get("Players", []) or []:
        ids = {
            key: value
            for key, raw_value in (row.get("IDs") or {}).items()
            if (value := clean(raw_value))
        }
        signature = _replay_signature(
            ids,
            clean(row.get("BirthDate")),
            clean(row.get("Position")),
            clean(row.get("Name")),
        )
        internal_id = canonical_player_id(row)
        if signature is not None and internal_id:
            index[signature].add(internal_id)
    return index


def _replay_existing_weak_identity(
    replay_index: dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]],
    ids: dict[str, str],
    birth_date: str | None,
    position: str | None,
    name: str | None,
) -> str | None:
    signature = _replay_signature(ids, birth_date, position, name)
    if signature is None:
        return None
    owners = sorted(replay_index.get(signature, set()))
    return owners[0] if len(owners) == 1 else None


def raw_identity_candidates(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[list[IdentityCandidate], list[dict[str, str]], list[IdentityCandidate | None], list[dict[str, Any]]]:
    existing_replay_index = _existing_weak_replay_index(repo_root)
    candidates: list[IdentityCandidate] = []
    player_rows = list(iter_csv(datasets["nflverse.players"].raw_path))
    for row in player_rows:
        ids = ids_from_players(row)
        if not ids:
            continue
        name = clean(row.get("display_name"))
        birth_date = clean(row.get("birth_date"))
        position = clean(row.get("position"))
        candidates.append(
            IdentityCandidate(
                ids=ids,
                name=name,
                first_name=clean(row.get("first_name")) or clean(row.get("common_first_name")),
                last_name=clean(row.get("last_name")),
                birth_date=birth_date,
                position=position,
                latest_team=clean(row.get("latest_team")),
                source="nflverse.players",
                priority=10,
                existing_internal_id=_replay_existing_weak_identity(
                    existing_replay_index,
                    ids,
                    birth_date,
                    position,
                    name,
                ),
            )
        )

    anchors = _player_birthdate_anchors(player_rows)
    ff_rows: list[dict[str, str]] = []
    ff_candidates: list[IdentityCandidate | None] = []
    source_conflicts: list[dict[str, Any]] = []

    for row in iter_csv(datasets["nflverse.ff-player-ids"].raw_path):
        ff_rows.append(row)
        raw_ids = ids_from_ff(row)
        ids = dict(raw_ids)
        name = clean(row.get("name"))
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
                    "Name": name,
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
            candidate = IdentityCandidate(
                ids=ids,
                name=name,
                first_name=None,
                last_name=None,
                birth_date=birth_date,
                position=position,
                latest_team=clean(row.get("team")),
                source="nflverse.ff-player-ids",
                priority=20,
                existing_internal_id=_replay_existing_weak_identity(
                    existing_replay_index,
                    ids,
                    birth_date,
                    position,
                    name,
                ),
            )
            candidates.append(candidate)
        ff_candidates.append(candidate)

    return candidates, ff_rows, ff_candidates, source_conflicts
