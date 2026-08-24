from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .canonical_identity import identity_lookup
from .common import Dataset, as_float, as_int, clean, iter_csv


def _height_inches(value: Any) -> int | None:
    text = clean(value)
    if text is None:
        return None
    normalized = text.replace("’", "-").replace("'", "-").replace('"', "").strip()
    if "-" in normalized:
        left, right = normalized.split("-", 1)
        feet, inches = as_int(left), as_int(right)
        if feet is None or inches is None or feet < 0 or not 0 <= inches < 12:
            return None
        return feet * 12 + inches
    number = as_float(normalized)
    if number is None:
        return None
    # nflverse currently exposes feet-inches text, but tolerate an already-normalized
    # numeric inches representation without guessing from player names or positions.
    if number >= 48:
        return int(round(number))
    return None


def _draft_index(
    draft_payloads: dict[int, dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    index: dict[tuple[int, str], dict[str, Any]] = {}
    for season, payload in sorted(draft_payloads.items()):
        for pick in payload.get("Picks", []):
            internal_id = clean(pick.get("CanonicalPlayerID"))
            if not internal_id:
                continue
            candidate = {
                "Season": season,
                "Round": pick.get("Round"),
                "PositionInRound": pick.get("PositionInRound"),
                "OverallPick": pick.get("OverallPick"),
                "Team": pick.get("Team"),
            }
            # Draft identity is season-scoped. A real player can legitimately
            # appear in more than one NFL draft across different seasons, while
            # conflicting facts for the same person inside one draft season are
            # still an invariant violation.
            draft_key = (season, internal_id)
            previous = index.get(draft_key)
            if previous is not None and previous != candidate:
                raise ValueError(
                    f"Canonical player {internal_id} has multiple NFL draft facts in season {season}"
                )
            index[draft_key] = candidate
    return index


def _source_identity_key(row: dict[str, str]) -> tuple[int, str] | None:
    season = as_int(row.get("season"))
    pfr = clean(row.get("pfr_id"))
    if season is None or not pfr:
        return None
    return season, pfr


def _raw_row_signature(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, value or "") for key, value in row.items()))


def build_combine_files(
    dataset: Dataset,
    canonical: list[dict[str, Any]],
    draft_payloads: dict[int, dict[str, Any]],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    lookup = identity_lookup(canonical)
    draft_by_player = _draft_index(draft_payloads)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    conflicts: list[dict[str, Any]] = []
    seen_internal: set[tuple[int, str]] = set()

    rows = list(iter_csv(dataset.raw_path))
    pfr_claim_counts = Counter(
        key for row in rows if (key := _source_identity_key(row)) is not None
    )
    ambiguous_pfr_claims = {
        key for key, count in pfr_claim_counts.items() if count > 1
    }
    if ambiguous_pfr_claims:
        signatures_by_claim: dict[tuple[int, str], list[tuple[tuple[str, str], ...]]] = defaultdict(list)
        for row in rows:
            key = _source_identity_key(row)
            if key in ambiguous_pfr_claims:
                signatures_by_claim[key].append(_raw_row_signature(row))
        for (season, pfr), signatures in sorted(signatures_by_claim.items()):
            if len(set(signatures)) != len(signatures):
                raise ValueError(f"Duplicate identical combine row for PFR identity {season}/{pfr}")

    for row in rows:
        season = as_int(row.get("season"))
        if season is None:
            continue
        pfr = clean(row.get("pfr_id"))
        cfb = clean(row.get("cfb_id"))
        pfr_key = (season, pfr) if pfr else None
        ambiguous_source_claim = pfr_key in ambiguous_pfr_claims if pfr_key else False
        internal_id = None if ambiguous_source_claim else lookup.get(("PFR", pfr)) if pfr else None

        if internal_id:
            internal_key = (season, internal_id)
            if internal_key in seen_internal:
                raise ValueError(f"Duplicate combine canonical identity {season}/{internal_id}")
            seen_internal.add(internal_key)

        if ambiguous_source_claim:
            identity_resolution = {
                "Status": "ambiguous",
                "Provider": "PFR",
                "ExternalID": pfr,
                "Reason": "duplicate-source-claim",
            }
        elif internal_id:
            identity_resolution = {
                "Status": "resolved",
                "Provider": "PFR",
                "ExternalID": pfr,
            }
        elif pfr:
            identity_resolution = {
                "Status": "unresolved",
                "Provider": "PFR",
                "ExternalID": pfr,
                "Reason": "unmapped-provider-id",
            }
        else:
            identity_resolution = {
                "Status": "unresolved",
                "Reason": "missing-pfr-id",
            }

        source_draft = {
            "Year": as_int(row.get("draft_year")),
            "Team": clean(row.get("draft_team")),
            "Round": as_int(row.get("draft_round")),
            "OverallPick": as_int(row.get("draft_ovr")),
        }
        source_draft = {key: value for key, value in source_draft.items() if value is not None}

        canonical_draft = draft_by_player.get((season, internal_id)) if internal_id else None
        if canonical_draft and source_draft:
            comparable = (
                ("Year", "Season"),
                ("Round", "Round"),
                ("OverallPick", "OverallPick"),
            )
            differences = {
                source_key: {
                    "combine": source_draft.get(source_key),
                    "canonicalDraft": canonical_draft.get(canonical_key),
                }
                for source_key, canonical_key in comparable
                if source_draft.get(source_key) is not None
                and canonical_draft.get(canonical_key) is not None
                and source_draft.get(source_key) != canonical_draft.get(canonical_key)
            }
            if differences:
                conflicts.append({
                    "Season": season,
                    "CanonicalPlayerID": internal_id,
                    "PFR": pfr,
                    "PlayerName": clean(row.get("player_name")),
                    "Differences": differences,
                })

        measurements = {
            "HeightInches": _height_inches(row.get("ht")),
            "WeightPounds": as_int(row.get("wt")),
            "FortyYardDashSeconds": as_float(row.get("forty")),
            "BenchPressReps": as_int(row.get("bench")),
            "VerticalJumpInches": as_float(row.get("vertical")),
            "BroadJumpInches": as_float(row.get("broad_jump")),
            "ThreeConeSeconds": as_float(row.get("cone")),
            "ShuttleSeconds": as_float(row.get("shuttle")),
        }

        grouped[season].append({
            "CanonicalPlayerID": internal_id,
            "IdentityResolution": identity_resolution,
            "PlayerName": clean(row.get("player_name")),
            "Position": clean(row.get("pos")),
            "School": clean(row.get("school")),
            "Measurements": measurements,
            "Draft": canonical_draft,
            "SourceDraftEvidence": source_draft,
            "SourceIDs": {
                key: value
                for key, value in {"PFR": pfr, "CFBRef": cfb}.items()
                if value
            },
        })

    for records in grouped.values():
        records.sort(key=lambda item: (
            item.get("CanonicalPlayerID") or "~",
            item.get("SourceIDs", {}).get("PFR") or "~",
            item.get("PlayerName") or "~",
            item.get("Position") or "~",
            item.get("School") or "~",
        ))
    conflicts.sort(key=lambda item: (item["Season"], item.get("PFR") or "", item.get("PlayerName") or ""))
    return grouped, conflicts
