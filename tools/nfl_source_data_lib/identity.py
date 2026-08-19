from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import IDENTITY_ID_KEYS, Dataset, clean, iter_csv, load_json, stable_internal_id

ANCHOR_ID_KEYS = ("GSIS", "ESPN", "PFR", "PFF")
LINK_ID_KEYS = {"GSIS", "Sleeper", "ESPN", "PFR", "PFF", "Tank01"}
WEAK_ID_KEYS = set(IDENTITY_ID_KEYS) - LINK_ID_KEYS
ALIAS_MIN_CORROBORATORS = {"ESPN": 1, "PFR": 2}
ALIASABLE_LINK_ID_KEYS = set(ALIAS_MIN_CORROBORATORS)
PRIMARY_SOURCE_PREFERENCE = (
    "canonical-existing",
    "nflverse.ff-player-ids",
    "nflverse.players",
    "app.Players",
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
) -> tuple[list[IdentityCandidate], list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]]]:
    del repo_root
    candidates: list[IdentityCandidate] = []
    player_rows = list(iter_csv(datasets["nflverse.players"].raw_path))
    for row in player_rows:
        ids = ids_from_players(row)
        if ids:
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
    ff_identity_ids: list[dict[str, str]] = []
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

        ff_identity_ids.append(ids)
        if ids:
            candidates.append(
                IdentityCandidate(
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
            )
    return candidates, ff_rows, ff_identity_ids, source_conflicts


def existing_identity_candidates(repo_root: Path) -> list[IdentityCandidate]:
    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    result: list[IdentityCandidate] = []
    for row in payload.get("Players", []):
        ids = {key: clean(value) for key, value in (row.get("IDs") or {}).items() if clean(value)}
        if not ids:
            continue
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


def _shared_strong_tokens(
    left: IdentityCandidate,
    right: IdentityCandidate,
    conflict_key: str,
) -> set[tuple[str, str]]:
    shared: set[tuple[str, str]] = set()
    for key in ANCHOR_ID_KEYS:
        if key == conflict_key:
            continue
        left_value = left.ids.get(key)
        right_value = right.ids.get(key)
        if left_value and left_value == right_value:
            shared.add((key, left_value))
    return shared


def _verified_link_alias(key: str, members: list[IdentityCandidate]) -> bool:
    required_corroborators = ALIAS_MIN_CORROBORATORS.get(key)
    if required_corroborators is None:
        return False
    relevant = [member for member in members if member.ids.get(key)]
    values = {member.ids[key] for member in relevant}
    if len(values) < 2:
        return False
    birth_dates = {member.birth_date for member in relevant}
    if None in birth_dates or len(birth_dates) != 1:
        return False

    grouped: dict[str, list[IdentityCandidate]] = defaultdict(list)
    for member in relevant:
        grouped[member.ids[key]].append(member)
    for value, group in grouped.items():
        corroborated = False
        for member in group:
            for other_value, other_group in grouped.items():
                if other_value == value:
                    continue
                if any(
                    len(_shared_strong_tokens(member, other, key)) >= required_corroborators
                    for other in other_group
                ):
                    corroborated = True
                    break
            if corroborated:
                break
        if not corroborated:
            return False
    return True


def _select_primary_provider_id(key: str, values: set[str], members: list[IdentityCandidate]) -> str:
    for source in PRIMARY_SOURCE_PREFERENCE:
        candidates = sorted(
            {
                member.ids[key]
                for member in members
                if member.source == source and member.ids.get(key) in values
            }
        )
        if candidates:
            return candidates[0]
    return sorted(values)[0]


def build_identities(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    raw_candidates, ff_rows, ff_identity_ids, source_conflicts = raw_identity_candidates(repo_root, datasets)
    app_candidates, _ = app_player_candidates(repo_root)
    candidates = existing_identity_candidates(repo_root) + raw_candidates + app_candidates
    uf = UnionFind()
    id_owner: dict[tuple[str, str], int] = {}
    indexes: list[int] = []
    for candidate in candidates:
        idx = uf.add()
        indexes.append(idx)
        for key, value in candidate.ids.items():
            if key not in LINK_ID_KEYS:
                continue
            token = (key, value)
            if token in id_owner:
                uf.union(idx, id_owner[token])
            else:
                id_owner[token] = idx

    components: dict[int, list[IdentityCandidate]] = defaultdict(list)
    for idx, candidate in zip(indexes, candidates):
        components[uf.find(idx)].append(candidate)

    canonical: list[dict[str, Any]] = []
    for members in components.values():
        external_values: dict[str, set[str]] = defaultdict(set)
        existing_ids: set[str] = set()
        sources: set[str] = set()
        for member in members:
            sources.add(member.source)
            if member.existing_internal_id:
                existing_ids.add(member.existing_internal_id)
            for key, value in member.ids.items():
                external_values[key].add(value)

        conflicts: dict[str, list[str]] = {}
        ids: dict[str, str] = {}
        aliases: dict[str, list[str]] = {}
        for key, values in external_values.items():
            if len(values) == 1:
                ids[key] = next(iter(values))
                continue
            if key in WEAK_ID_KEYS or _verified_link_alias(key, members):
                primary = _select_primary_provider_id(key, values, members)
                ids[key] = primary
                aliases[key] = sorted(values - {primary})
                continue
            conflicts[key] = sorted(values)

        if conflicts:
            member_summary = [
                {
                    "Source": member.source,
                    "Name": member.name,
                    "BirthDate": member.birth_date,
                    "IDs": member.ids,
                }
                for member in members[:8]
            ]
            raise ValueError(
                f"Identity component has conflicting IDs for the same link provider: {conflicts}; "
                f"members={member_summary}"
            )
        if len(existing_ids) > 1:
            raise ValueError(f"Identity component merges multiple existing NFLPlayerIDs: {sorted(existing_ids)}")

        if existing_ids:
            internal_id = next(iter(existing_ids))
        else:
            seed = next(
                (
                    f"{key}:{ids[key]}"
                    for key in ("GSIS", "Sleeper", "PFR", "ESPN", "Tank01")
                    if ids.get(key)
                ),
                None,
            )
            internal_id = stable_internal_id(
                seed or "|".join(f"{key}:{ids[key]}" for key in sorted(ids))
            )

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

    duplicate_internal = [
        key for key, rows in _group(canonical, "NFLPlayerID").items() if len(rows) > 1
    ]
    if duplicate_internal:
        raise ValueError(f"Duplicate NFLPlayerID values generated: {duplicate_internal[:10]}")
    canonical.sort(key=lambda item: ((item.get("Name") or "").lower(), item["NFLPlayerID"]))

    lookup = identity_lookup(canonical)
    resolved_ff_rows: list[dict[str, str]] = []
    for row, ids in zip(ff_rows, ff_identity_ids):
        internal_id = next(
            (lookup[(key, value)] for key, value in ids.items() if (key, value) in lookup),
            None,
        )
        resolved = dict(row)
        resolved["__NFLPlayerID"] = internal_id or ""
        resolved_ff_rows.append(resolved)
    return canonical, resolved_ff_rows, source_conflicts


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
