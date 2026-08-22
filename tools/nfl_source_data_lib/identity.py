from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import IDENTITY_ID_KEYS, Dataset, clean, load_json, stable_internal_id
from .identity_model import (
    ALIAS_MIN_CORROBORATORS,
    ANCHOR_ID_KEYS,
    ATTACH_ID_KEYS,
    LINK_ID_KEYS,
    PRIMARY_SOURCE_PREFERENCE,
    IdentityCandidate,
    ids_from_ff,
    ids_from_players,
)
from .identity_sources import raw_identity_candidates


class UnionFind:
    def __init__(self) -> None:
        self.parent: list[int] = []
        self.rank: list[int] = []

    def add(self) -> int:
        idx = len(self.parent)
        self.parent.append(idx)
        self.rank.append(0)
        return idx

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def app_player_candidates(repo_root: Path) -> tuple[list[IdentityCandidate], list[dict[str, Any]]]:
    """Return current app identity candidates and the canonical audit population.

    `public/data/Players.json` is the current app player read model. The former
    `Players_Relevant.json` AI helper was intentionally retired and must not be a
    source-data dependency. The same current Players population therefore drives
    both app attachment candidates and coverage auditing.
    """

    players = load_json(repo_root / "public/data/Players.json", []) or []
    candidates: list[IdentityCandidate] = []
    for row in players:
        ids: dict[str, str] = {}
        if sleeper := clean(row.get("ID")):
            ids["Sleeper"] = sleeper
        if tank := clean(row.get("TankID")):
            ids["Tank01"] = tank
        if not ids:
            continue
        candidates.append(
            IdentityCandidate(
                ids=ids,
                name=clean(row.get("Name")) or clean(row.get("FullName")),
                first_name=clean(row.get("FirstName")),
                last_name=clean(row.get("LastName")),
                birth_date=clean(row.get("BirthDate")),
                position=clean(row.get("Position")),
                latest_team=clean(row.get("Team")) or clean(row.get("TeamID")),
                source="app.Players",
                priority=30,
            )
        )
    return candidates, players


def existing_identity_candidates(repo_root: Path) -> list[IdentityCandidate]:
    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    result: list[IdentityCandidate] = []
    for row in payload.get("Players", []):
        ids = {key: clean(value) for key, value in (row.get("IDs") or {}).items() if clean(value)}
        base = IdentityCandidate(
            ids=ids,
            name=clean(row.get("Name")),
            first_name=clean(row.get("FirstName")),
            last_name=clean(row.get("LastName")),
            birth_date=clean(row.get("BirthDate")),
            position=clean(row.get("Position")),
            latest_team=clean(row.get("LatestTeam")),
            source="canonical-existing",
            priority=0,
            existing_internal_id=clean(row.get("NFLPlayerID")),
        )
        result.append(base)
        for key, values in (row.get("IDAliases") or {}).items():
            for alias in values or []:
                alias_value = clean(alias)
                if not alias_value:
                    continue
                alias_ids = dict(ids)
                alias_ids[key] = alias_value
                result.append(
                    IdentityCandidate(
                        ids=alias_ids,
                        name=base.name,
                        first_name=base.first_name,
                        last_name=base.last_name,
                        birth_date=base.birth_date,
                        position=base.position,
                        latest_team=base.latest_team,
                        source="canonical-existing",
                        priority=0,
                        existing_internal_id=base.existing_internal_id,
                    )
                )
    return result


def _can_merge_on_anchor(left: IdentityCandidate, right: IdentityCandidate, shared_key: str) -> bool:
    if left.birth_date and right.birth_date and left.birth_date != right.birth_date:
        return False

    shared = {
        key
        for key in ANCHOR_ID_KEYS
        if left.ids.get(key) and left.ids.get(key) == right.ids.get(key)
    }
    conflicting = {
        key
        for key in ANCHOR_ID_KEYS
        if left.ids.get(key)
        and right.ids.get(key)
        and left.ids.get(key) != right.ids.get(key)
    }
    if not conflicting:
        return True
    if not left.birth_date or left.birth_date != right.birth_date:
        return False

    for conflict_key in conflicting:
        required = ALIAS_MIN_CORROBORATORS.get(conflict_key)
        if required is None:
            return False
        corroborators = len(shared - {conflict_key})
        if corroborators < required:
            return False
    return shared_key in shared


def _component_members(uf: UnionFind, candidates: list[IdentityCandidate]) -> dict[int, list[int]]:
    result: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(candidates)):
        result[uf.find(idx)].append(idx)
    return result


def _component_is_stable(indexes: list[int], candidates: list[IdentityCandidate]) -> bool:
    return any(
        candidates[idx].existing_internal_id
        or any(candidates[idx].ids.get(key) for key in ANCHOR_ID_KEYS)
        for idx in indexes
    )


def _component_compatible(candidate: IdentityCandidate, indexes: list[int], candidates: list[IdentityCandidate]) -> bool:
    for idx in indexes:
        other = candidates[idx]
        if candidate.birth_date and other.birth_date and candidate.birth_date != other.birth_date:
            return False
    return True


def _build_components(candidates: list[IdentityCandidate]) -> UnionFind:
    uf = UnionFind()
    for _ in candidates:
        uf.add()

    existing_owner: dict[str, int] = {}
    anchor_owners: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, candidate in enumerate(candidates):
        if candidate.existing_internal_id:
            previous = existing_owner.get(candidate.existing_internal_id)
            if previous is None:
                existing_owner[candidate.existing_internal_id] = idx
            else:
                uf.union(previous, idx)
        for key in ANCHOR_ID_KEYS:
            if value := candidate.ids.get(key):
                anchor_owners[(key, value)].append(idx)

    for (key, _), owners in anchor_owners.items():
        for left_offset, left in enumerate(owners):
            for right in owners[left_offset + 1 :]:
                if _can_merge_on_anchor(candidates[left], candidates[right], key):
                    uf.union(left, right)

    # Provider attachment IDs such as Sleeper and Tank01 may connect a current
    # provider-only row to one stable component, but never merge stable components
    # with each other. If the same attachment token points at multiple possible
    # current people it remains ambiguous and is quarantined later.
    components = _component_members(uf, candidates)
    app_token_roots: dict[tuple[str, str], set[int]] = defaultdict(set)
    for idx, candidate in enumerate(candidates):
        if candidate.source not in {"app.Players", "canonical-existing"}:
            continue
        root = uf.find(idx)
        for key in ATTACH_ID_KEYS:
            if value := candidate.ids.get(key):
                app_token_roots[(key, value)].add(root)

    proposals: dict[int, list[int]] = defaultdict(list)
    for idx, candidate in enumerate(candidates):
        if candidate.source in {"app.Players", "canonical-existing"}:
            continue
        if _component_is_stable(components.get(uf.find(idx), []), candidates):
            continue
        targets: set[int] = set()
        for key in ATTACH_ID_KEYS:
            if value := candidate.ids.get(key):
                targets.update(app_token_roots.get((key, value), set()))
        if len(targets) == 1:
            proposals[next(iter(targets))].append(idx)

    for target, proposed_indexes in proposals.items():
        if len(proposed_indexes) != 1:
            continue
        idx = proposed_indexes[0]
        target_indexes = components.get(target, [])
        if _component_compatible(candidates[idx], target_indexes, candidates):
            uf.union(idx, target)
    return uf


def _select_primary_provider_id(key: str, values: set[str], members: list[IdentityCandidate]) -> str:
    for source in PRIMARY_SOURCE_PREFERENCE:
        selected = sorted(
            member.ids[key]
            for member in members
            if member.source == source and member.ids.get(key) in values
        )
        if selected:
            return selected[0]
    return sorted(values)[0]


def _seed_for_component(members: list[IdentityCandidate]) -> str:
    id_tokens = sorted(
        {
            f"{key}:{value}"
            for member in members
            if member.source != "canonical-existing"
            for key, value in member.ids.items()
            if value
        }
    )
    if not id_tokens:
        id_tokens = sorted(
            {
                f"{key}:{value}"
                for member in members
                for key, value in member.ids.items()
                if value
            }
        )
    birth_dates = sorted({member.birth_date for member in members if member.birth_date})
    names = sorted({member.name.strip().lower() for member in members if member.name and member.name.strip()})
    positions = sorted({member.position for member in members if member.position})
    seed_parts = ["component", *id_tokens]
    if birth_dates:
        seed_parts.append("birth=" + ",".join(birth_dates))
    if positions:
        seed_parts.append("position=" + ",".join(positions))
    if names:
        seed_parts.append("names=" + ",".join(names))
    return "|".join(seed_parts)


def build_identities(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, str]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    raw_candidates, ff_rows, ff_candidates, source_conflicts = raw_identity_candidates(repo_root, datasets)
    app_candidates, _ = app_player_candidates(repo_root)
    candidates = existing_identity_candidates(repo_root) + raw_candidates + app_candidates
    candidate_index = {id(candidate): idx for idx, candidate in enumerate(candidates)}
    uf = _build_components(candidates)
    components = _component_members(uf, candidates)

    root_internal: dict[int, str] = {}
    for root, indexes in components.items():
        members = [candidates[idx] for idx in indexes]
        existing_ids = {member.existing_internal_id for member in members if member.existing_internal_id}
        if len(existing_ids) > 1:
            raise ValueError(f"Identity component merges multiple existing NFLPlayerIDs: {sorted(existing_ids)}")
        root_internal[root] = next(iter(existing_ids)) if existing_ids else stable_internal_id(_seed_for_component(members))

    current_claim_owners: dict[tuple[str, str], set[str]] = defaultdict(set)
    current_claim_sources: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for idx, candidate in enumerate(candidates):
        if candidate.source == "canonical-existing":
            continue
        internal_id = root_internal[uf.find(idx)]
        for key, value in candidate.ids.items():
            token = (key, value)
            current_claim_owners[token].add(internal_id)
            current_claim_sources[(key, value, internal_id)].add(candidate.source)

    lookup_conflicts: list[dict[str, Any]] = []
    mapping_conflicts: list[dict[str, Any]] = []
    ambiguous_lookup_tokens: set[tuple[str, str]] = set()
    for (key, value), owners in sorted(current_claim_owners.items()):
        if len(owners) <= 1:
            continue
        detail = {
            "Provider": key,
            "ExternalID": value,
            "NFLPlayerIDs": sorted(owners),
            "SourcesByNFLPlayerID": {
                internal_id: sorted(current_claim_sources[(key, value, internal_id)])
                for internal_id in sorted(owners)
            },
        }
        mapping_conflicts.append(detail)
        if key in LINK_ID_KEYS:
            ambiguous_lookup_tokens.add((key, value))
            lookup_conflicts.append(
                {
                    "Source": "identity-resolution",
                    "Reason": "provider_id_maps_to_multiple_people",
                    **detail,
                }
            )
    source_conflicts.extend(lookup_conflicts)

    canonical: list[dict[str, Any]] = []
    for root, indexes in components.items():
        members = [candidates[idx] for idx in indexes]
        internal_id = root_internal[root]
        sources = {member.source for member in members if member.source != "canonical-existing"}
        values_by_key: dict[str, set[str]] = defaultdict(set)
        for member in members:
            for key, value in member.ids.items():
                if member.source == "canonical-existing" and key in ATTACH_ID_KEYS:
                    if internal_id not in current_claim_owners.get((key, value), set()):
                        continue
                if key in LINK_ID_KEYS and (key, value) in ambiguous_lookup_tokens:
                    continue
                values_by_key[key].add(value)

        ids: dict[str, str] = {}
        aliases: dict[str, list[str]] = {}
        for key, values in values_by_key.items():
            if not values:
                continue
            primary = _select_primary_provider_id(key, values, members)
            ids[key] = primary
            remaining = sorted(values - {primary})
            if remaining:
                aliases[key] = remaining

        ranked = sorted(members, key=lambda item: item.priority)

        def first(field: str) -> str | None:
            return next((getattr(item, field) for item in ranked if getattr(item, field)), None)

        canonical.append(
            {
                "NFLPlayerID": internal_id,
                "Name": first("name"),
                "FirstName": first("first_name"),
                "LastName": first("last_name"),
                "BirthDate": first("birth_date"),
                "Position": first("position"),
                "LatestTeam": first("latest_team"),
                "IDs": {key: ids[key] for key in IDENTITY_ID_KEYS if key in ids},
                "IDAliases": {key: aliases[key] for key in IDENTITY_ID_KEYS if aliases.get(key)},
                "Sources": sorted(sources),
            }
        )

    duplicate_internal = [key for key, rows in _group(canonical, "NFLPlayerID").items() if len(rows) > 1]
    if duplicate_internal:
        raise ValueError(f"Duplicate NFLPlayerID values generated: {duplicate_internal[:10]}")
    canonical.sort(key=lambda item: ((item.get("Name") or "").lower(), item["NFLPlayerID"]))

    provider_claims: list[dict[str, Any]] = []
    for (key, value), owners in sorted(current_claim_owners.items()):
        if len(owners) != 1:
            continue
        internal_id = next(iter(owners))
        provider_claims.append(
            {
                "Provider": key,
                "ExternalID": value,
                "NFLPlayerID": internal_id,
                "Sources": sorted(current_claim_sources[(key, value, internal_id)]),
            }
        )

    resolved_ff_rows: list[dict[str, str]] = []
    for row, candidate in zip(ff_rows, ff_candidates):
        resolved = dict(row)
        internal_id = None
        if candidate is not None:
            idx = candidate_index[id(candidate)]
            internal_id = root_internal[uf.find(idx)]
        resolved["__NFLPlayerID"] = internal_id or ""
        resolved_ff_rows.append(resolved)

    identity_lookup(canonical)
    return canonical, resolved_ff_rows, source_conflicts, provider_claims, mapping_conflicts


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def identity_lookup(canonical: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for row in canonical:
        mappings = [
            (key, value)
            for key, value in (row.get("IDs") or {}).items()
            if key in LINK_ID_KEYS
        ]
        for key, values in (row.get("IDAliases") or {}).items():
            if key in LINK_ID_KEYS:
                mappings.extend((key, value) for value in values or [])
        for key, value in mappings:
            token = (key, value)
            previous = lookup.get(token)
            if previous and previous != row["NFLPlayerID"]:
                raise ValueError(f"Link ID {key}:{value} maps to multiple canonical players")
            lookup[token] = row["NFLPlayerID"]
    return lookup
