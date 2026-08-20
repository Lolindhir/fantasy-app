from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import Dataset, clean, iter_csv
from .identity_v2 import (
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


def raw_identity_candidates(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[list[IdentityCandidate], list[dict[str, str]], list[IdentityCandidate | None], list[dict[str, Any]]]:
    del repo_root
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
    ff_rows: list[dict[str, str]] = []
    ff_candidates: list[IdentityCandidate | None] = []
    source_conflicts: list[dict[str, Any]] = []

    for row in iter_csv(datasets["nflverse.ff-player-ids"].raw_path):
        ff_rows.append(row)
        raw_ids = ids_from_ff(row)
        ids = dict(raw_ids)
        birth_date = clean(row.get("birthdate"))
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
                # The row has at least one exact-birthdate anchor identifying the
                # person. Remove only anchor mappings contradicted by nflverse and
                # keep the remaining row mappings attached to the corroborated person.
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
                # No authoritative anchor corroborates this row's birth date. Do
                # not let provider-only IDs bootstrap a person from a row that is
                # already contradicted by the canonical NFL identity source.
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
                    "Position": clean(row.get("position")),
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
                name=clean(row.get("name")),
                first_name=None,
                last_name=None,
                birth_date=birth_date,
                position=clean(row.get("position")),
                latest_team=clean(row.get("team")),
                source="nflverse.ff-player-ids",
                priority=20,
            )
            candidates.append(candidate)
        ff_candidates.append(candidate)

    return candidates, ff_rows, ff_candidates, source_conflicts
