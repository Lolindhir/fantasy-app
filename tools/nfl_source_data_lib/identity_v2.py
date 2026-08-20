from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import IDENTITY_ID_KEYS, Dataset, clean, iter_csv, load_json, stable_internal_id

ANCHOR_ID_KEYS = ("GSIS", "ESPN", "PFR", "PFF")
LINK_ID_KEYS = {"GSIS", "Sleeper", "ESPN", "PFR", "PFF", "Tank01"}
ATTACH_ID_KEYS = {"Sleeper", "Tank01"}
WEAK_ID_KEYS = set(IDENTITY_ID_KEYS) - LINK_ID_KEYS
PRIMARY_SOURCE_PREFERENCE = (
    "nflverse.ff-player-ids",
    "nflverse.players",
    "app.Players",
    "canonical-existing",
)


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


@dataclass
class IdentityCandidate:
    ids: dict[str, str]
    name: str | None
    first_name: str | None
    last_name: str | None
    birth_date: str | None
    position: str | None
    latest_team: str | None
    source: str
    priority: int
    existing_internal_id: str | None = None


def ids_from_players(row: dict[str, str]) -> dict[str, str]:
    mapping = {
        "GSIS": "gsis_id",
        "ESPN": "espn_id",
        "PFR": "pfr_id",
        "PFF": "pff_id",
        "OTC": "otc_id",
        "NFL": "nfl_id",
        "ESB": "esb_id",
    }
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}


def ids_from_ff(row: dict[str, str]) -> dict[str, str]:
    mapping = {
        "GSIS": "gsis_id",
        "Sleeper": "sleeper_id",
        "ESPN": "espn_id",
        "PFR": "pfr_id",
        "PFF": "pff_id",
        "NFLCom": "nfl_id",
        "FantasyPros": "fantasypros_id",
        "MFL": "mfl_id",
        "Sportradar": "sportradar_id",
        "Yahoo": "yahoo_id",
        "Fleaflicker": "fleaflicker_id",
        "CBS": "cbs_id",
        "CFBRef": "cfbref_id",
        "Rotowire": "rotowire_id",
        "KTC": "ktc_id",
        "FantasyData": "fantasy_data_id",
    }
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}


def app_player_candidates(repo_root: Path) -> tuple[list[IdentityCandidate], list[dict[str, Any]]]:
    players = load_json(repo_root / "public/data/Players.json", []) or []
    relevant = load_json(repo_root / "public/data/Players_Relevant.json", []) or []
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
    return candidates, relevant


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
                detail = {"Provider": key, "ID": value, "NFLVerseBirthDates": expected_birth_dates}
                if birth_date in expected_birth_dates:
                    matching_anchors.append(detail)
                else:
                    conflicting_anchors.append(detail)

        if conflicting_anchors:
            suppressed = {key: value for key, value in raw_ids.items() if key != "MFL"}
            ids = {"MFL": raw_ids["MFL"]} if raw_ids.get("MFL") else {}
            source_conflicts.append(
                {
                    "Source": "nflverse.ff-player-ids",
                    "Reason": "birthdate_conflict_with_nflverse_players",
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


def _shared_anchor_count(left: IdentityCandidate, right: IdentityCandidate, exclude_key: str | None = None) -> int:
    return sum(
        1
        for key in ANCHOR_ID_KEYS
        if key != exclude_key and left.ids.get(key) and left.ids.get(key) == right.ids.get(key)
    )


def _conflicting_anchor_count(left: IdentityCandidate, right: IdentityCandidate, exclude_key: str | None = None) -> int:
    return sum(
        1
        for key in ANCHOR_ID_KEYS
        if key != exclude_key
        and left.ids.get(key)
        and right.ids.get(key)
        and left.ids.get(key) != right.ids.get(key)
    )


def _can_merge_on_anchor(left: IdentityCandidate, right: IdentityCandidate, shared_key: str) -> bool:
    if left.birth_date and right.birth_date and left.birth_date != right.birth_date:
        return False
    conflicts = _conflicting_anchor_count(left, right, shared_key)
    if conflicts == 0:
        return True
    same_birth_date = bool(left.birth_date and left.birth_date == right.birth_date)
    return same_birth_date and _shared_anchor_count(left, right, shared_key) >= 1


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
            if previous is not None:
                uf.union(idx, previous)
            else:
                existing_owner[candidate.existing_internal_id] = idx
        for key in ANCHOR_ID_KEYS:
            value = candidate.ids.get(key)
            if not value:
                continue
            token = (key, value)
            for previous in anchor_owners[token]:
                if _can_merge_on_anchor(candidate, candidates[previous], key):
                    uf.union(idx, previous)
            anchor_owners[token].append(idx)

    for _ in range(3):
        components = _component_members(uf, candidates)
        stable_roots = {root for root, indexes in components.items() if _component_is_stable(indexes, candidates)}
        token_roots: dict[tuple[str, str], set[int]] = defaultdict(set)
        for idx, candidate in enumerate(candidates):
            root = uf.find(idx)
            if root not in stable_roots:
                continue
            for key in ATTACH_ID_KEYS:
                if value := candidate.ids.get(key):
                    token_roots[(key, value)].add(root)

        changed = False
        for idx, candidate in enumerate(candidates):
            root = uf.find(idx)
            if root in stable_roots:
                continue
            targets: set[int] = set()
            for key in ATTACH_ID_KEYS:
                if value := candidate.ids.get(key):
                    targets.update(token_roots.get((key, value), set()))
            if len(targets) != 1:
                continue
            target = next(iter(targets))
            target_indexes = components.get(target, [])
            if not _component_compatible(candidate, target_indexes, candidates):
                continue
            uf.union(idx, target)
            changed = True
        if not changed:
            break
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
    for key in ("GSIS", "PFR", "ESPN", "PFF"):
        values = sorted({member.ids[key] for member in members if member.ids.get(key)})
        if values:
            return f"{key}:{values[0]}"
    for key in ("Sleeper", "Tank01"):
        values = sorted(
            {
                member.ids[key]
                for member in members
                if member.source != "canonical-existing" and member.ids.get(key)
            }
        )
        if values:
            return f"{key}:{values[0]}"
    all_tokens = sorted(
        f"{key}:{value}"
        for member in members
        for key, value in member.ids.items()
        if value
    )
    if not all_tokens:
        descriptive = next((member.name for member in members if member.name), "unknown")
        return f"descriptive:{descriptive}"
    return "|".join(all_tokens)


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
        sources = {member.source for member in members}
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


def build_provider_mapping_payload(
    repo_root: Path,
    provider_claims: list[dict[str, Any]],
    mapping_conflicts: list[dict[str, Any]],
    observation_season: int,
) -> dict[str, Any]:
    path = repo_root / "source-data/nfl/identities/provider-mappings.json"
    existing = load_json(path, {}) or {}
    mappings = [dict(item) for item in existing.get("Mappings", [])]
    conflicts = [dict(item) for item in existing.get("Conflicts", [])]

    def mapping_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("Provider") or ""),
            str(item.get("ExternalID") or ""),
            str(item.get("NFLPlayerID") or ""),
        )

    for claim in provider_claims:
        provider = claim["Provider"]
        external_id = claim["ExternalID"]
        internal_id = claim["NFLPlayerID"]
        exact = next(
            (item for item in mappings if mapping_key(item) == (provider, external_id, internal_id)),
            None,
        )
        if exact is not None:
            first = int(exact.get("FirstObservedSeason") or observation_season)
            last = int(exact.get("LastObservedSeason") or observation_season)
            exact["FirstObservedSeason"] = min(first, observation_season)
            exact["LastObservedSeason"] = max(last, observation_season)
            exact["Sources"] = sorted(set(exact.get("Sources") or []) | set(claim.get("Sources") or []))
            continue

        previous_for_token = [
            item
            for item in mappings
            if item.get("Provider") == provider and item.get("ExternalID") == external_id
        ]
        overlapping = [
            item
            for item in previous_for_token
            if int(item.get("LastObservedSeason") or observation_season) >= observation_season
        ]
        if overlapping:
            owners = sorted({internal_id, *(str(item.get("NFLPlayerID")) for item in overlapping)})
            mapping_conflicts.append(
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "NFLPlayerIDs": owners,
                    "SourcesByNFLPlayerID": {internal_id: sorted(claim.get("Sources") or [])},
                }
            )
            continue

        mappings.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "NFLPlayerID": internal_id,
                "FirstObservedSeason": observation_season,
                "LastObservedSeason": observation_season,
                "Sources": sorted(claim.get("Sources") or []),
            }
        )

    for conflict in mapping_conflicts:
        provider = str(conflict.get("Provider") or "")
        external_id = str(conflict.get("ExternalID") or "")
        owners = sorted(str(value) for value in conflict.get("NFLPlayerIDs") or [])
        same = next(
            (
                item
                for item in conflicts
                if item.get("Provider") == provider
                and item.get("ExternalID") == external_id
                and sorted(str(value) for value in item.get("NFLPlayerIDs") or []) == owners
            ),
            None,
        )
        if same is None:
            same = {
                "Provider": provider,
                "ExternalID": external_id,
                "NFLPlayerIDs": owners,
                "FirstObservedSeason": observation_season,
                "LastObservedSeason": observation_season,
                "Status": "ambiguous",
            }
            conflicts.append(same)
        else:
            same["FirstObservedSeason"] = min(
                int(same.get("FirstObservedSeason") or observation_season), observation_season
            )
            same["LastObservedSeason"] = max(
                int(same.get("LastObservedSeason") or observation_season), observation_season
            )
        sources_by_player = conflict.get("SourcesByNFLPlayerID") or {}
        if sources_by_player:
            merged = {
                key: set(values or [])
                for key, values in (same.get("SourcesByNFLPlayerID") or {}).items()
            }
            for internal_id, values in sources_by_player.items():
                merged.setdefault(internal_id, set()).update(values or [])
            same["SourcesByNFLPlayerID"] = {
                key: sorted(values) for key, values in sorted(merged.items())
            }

    mappings.sort(
        key=lambda item: (
            item["Provider"],
            item["ExternalID"],
            item["FirstObservedSeason"],
            item["NFLPlayerID"],
        )
    )
    conflicts.sort(
        key=lambda item: (
            item["Provider"],
            item["ExternalID"],
            item["FirstObservedSeason"],
            tuple(item["NFLPlayerIDs"]),
        )
    )
    return {
        "SchemaVersion": 1,
        "TemporalResolution": "season",
        "Mappings": mappings,
        "Conflicts": conflicts,
    }
