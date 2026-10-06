"""Canonical nflverse player profile projection (#347 F2).

Profile facts only (names, headshot, position group, career bounds, status). The projection is
keyed by the canonical identity that the identity layer already resolved from the GSIS ID; it never
creates, merges or re-links a player and therefore is not an identity owner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical_identity import identity_lookup
from .common import CANONICAL_SCHEMA_VERSION, Dataset, as_int, clean, iter_csv

PLAYER_PROFILES_DATASET_ID = "nflverse.players"
PLAYER_PROFILES_RELATIVE_PATH = "source-data/nfl/player-profiles/nflverse.json"

# Output field -> (raw nflverse column, coercion). Single contract-driven table; consumers decide what to read.
_PROFILE_FIELDS: tuple[tuple[str, str, Any], ...] = (
    ("DisplayName", "display_name", clean),
    ("ShortName", "short_name", clean),
    ("Headshot", "headshot", clean),
    ("Position", "position", clean),
    ("PositionGroup", "position_group", clean),
    ("RookieSeason", "rookie_season", as_int),
    ("LastSeason", "last_season", as_int),
    ("Status", "status", clean),
    ("LatestTeam", "latest_team", clean),
    ("BirthDate", "birth_date", clean),
)


def build_player_profiles(
    repo_root: Path,
    dataset: Dataset,
    canonical: list[dict[str, Any]],
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    """Project the persisted nflverse players CSV onto already resolved CanonicalPlayerIDs.

    Rows whose GSIS ID has no canonical identity are counted but not persisted; the projection must
    not become a second identity owner. Duplicate GSIS IDs or two source rows that resolve to one
    CanonicalPlayerID fail closed because a profile join would be ambiguous.
    """
    lookup = identity_lookup(canonical)
    records: list[dict[str, Any]] = []
    seen_gsis: set[str] = set()
    by_canonical: dict[str, str] = {}
    source_rows = 0
    unresolved = 0
    for row in iter_csv(dataset.raw_path):
        source_rows += 1
        gsis_id = clean(row.get("gsis_id"))
        if not gsis_id:
            unresolved += 1
            continue
        if gsis_id in seen_gsis:
            raise ValueError(f"Duplicate nflverse players gsis_id: {gsis_id}")
        seen_gsis.add(gsis_id)
        canonical_player_id = lookup.get(("GSIS", gsis_id))
        if canonical_player_id is None:
            unresolved += 1
            continue
        previous = by_canonical.get(canonical_player_id)
        if previous is not None:
            raise ValueError(
                f"nflverse players rows {previous} and {gsis_id} resolve to the same CanonicalPlayerID "
                f"{canonical_player_id}"
            )
        by_canonical[canonical_player_id] = gsis_id
        record: dict[str, Any] = {"CanonicalPlayerID": canonical_player_id, "GSISID": gsis_id}
        for output_name, raw_key, coerce in _PROFILE_FIELDS:
            record[output_name] = coerce(row.get(raw_key))
        records.append(record)
    records.sort(key=lambda item: item["CanonicalPlayerID"])
    payload = {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "SourceDataset": dataset.id,
        "Records": records,
    }
    audit = {
        "sourceRowCount": source_rows,
        "recordCount": len(records),
        "unresolvedIdentityCount": unresolved,
    }
    return [(repo_root / PLAYER_PROFILES_RELATIVE_PATH, payload)], audit, 0
