from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .common import Dataset, as_int, clean, iter_csv
from .identity import identity_lookup


def build_draft_files(dataset: Dataset, canonical: list[dict[str, Any]]) -> tuple[dict[int, list[dict[str, Any]]], set[str]]:
    lookup = identity_lookup(canonical)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    drafted_internal_ids: set[str] = set()
    for row in iter_csv(dataset.raw_path):
        season, round_no, overall_pick = as_int(row.get("season")), as_int(row.get("round")), as_int(row.get("pick"))
        if season is None or round_no is None or overall_pick is None:
            continue
        gsis = clean(row.get("gsis_id"))
        pfr = clean(row.get("pfr_player_id")) or clean(row.get("pfr_id"))
        internal_id = lookup.get(("GSIS", gsis)) if gsis else None
        if internal_id is None and pfr:
            internal_id = lookup.get(("PFR", pfr))
        if internal_id:
            drafted_internal_ids.add(internal_id)
        grouped[season].append({
            "Round": round_no, "PositionInRound": None, "OverallPick": overall_pick,
            "Team": clean(row.get("team")), "NFLPlayerID": internal_id,
            "PlayerName": clean(row.get("pfr_player_name")) or clean(row.get("player_name")),
            "Position": clean(row.get("position")),
            "SourceIDs": {key: value for key, value in {"GSIS": gsis, "PFR": pfr}.items() if value},
        })
    for season, picks in grouped.items():
        picks.sort(key=lambda item: item["OverallPick"])
        round_positions, seen_overall = Counter(), set()
        for pick in picks:
            if pick["OverallPick"] in seen_overall:
                raise ValueError(f"Duplicate overall pick {season}/{pick['OverallPick']}")
            seen_overall.add(pick["OverallPick"])
            round_positions[pick["Round"]] += 1
            pick["PositionInRound"] = round_positions[pick["Round"]]
    return grouped, drafted_internal_ids


def build_ff_draft_evidence(ff_rows: list[dict[str, str]], canonical: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup, evidence = identity_lookup(canonical), {}
    for row in ff_rows:
        internal_id = None
        for key, value in (("GSIS", clean(row.get("gsis_id"))), ("Sleeper", clean(row.get("sleeper_id"))), ("PFR", clean(row.get("pfr_id")))):
            if value and (key, value) in lookup:
                internal_id = lookup[(key, value)]
                break
        if not internal_id:
            continue
        candidate = {"DraftYear": as_int(row.get("draft_year")), "Round": as_int(row.get("draft_round")),
                     "PositionInRound": as_int(row.get("draft_pick")), "OverallPick": as_int(row.get("draft_ovr"))}
        current = evidence.get(internal_id)
        if current is None or _filled(candidate) > _filled(current):
            evidence[internal_id] = candidate
    return evidence


def _filled(value: dict[str, Any]) -> int:
    return sum(item is not None for item in value.values())


def classify_draft_status(internal_id: str | None, ff_evidence: dict[str, dict[str, Any]], drafted_internal_ids: set[str], max_draft_season: int | None) -> tuple[str, int | None]:
    if not internal_id:
        return "unknown", None
    if internal_id in drafted_internal_ids:
        return "drafted", ff_evidence.get(internal_id, {}).get("DraftYear")
    evidence = ff_evidence.get(internal_id)
    if not evidence:
        return "unknown", None
    draft_year = evidence.get("DraftYear")
    if any(evidence.get(key) is not None for key in ("Round", "PositionInRound", "OverallPick")):
        return "unknown", draft_year
    if draft_year is None or draft_year == 0:
        return "unknown", draft_year
    if max_draft_season is not None and draft_year > max_draft_season:
        return "not_yet_drafted", draft_year
    return "undrafted", draft_year
