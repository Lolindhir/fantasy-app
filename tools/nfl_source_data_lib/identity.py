from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import IDENTITY_ID_KEYS, Dataset, clean, iter_csv, load_json, stable_internal_id


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
    mapping = {"GSIS": "gsis_id", "ESPN": "espn_id", "PFR": "pfr_id", "PFF": "pff_id",
               "OTC": "otc_id", "NFL": "nfl_id", "ESB": "esb_id"}
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}


def ids_from_ff(row: dict[str, str]) -> dict[str, str]:
    mapping = {
        "GSIS": "gsis_id", "Sleeper": "sleeper_id", "ESPN": "espn_id", "PFR": "pfr_id",
        "PFF": "pff_id", "NFL": "nfl_id", "FantasyPros": "fantasypros_id", "MFL": "mfl_id",
        "Sportradar": "sportradar_id", "Yahoo": "yahoo_id", "Fleaflicker": "fleaflicker_id",
        "CBS": "cbs_id", "CFBRef": "cfbref_id", "Rotowire": "rotowire_id", "KTC": "ktc_id",
        "FantasyData": "fantasy_data_id",
    }
    return {key: value for key, field in mapping.items() if (value := clean(row.get(field)))}


def app_player_candidates(repo_root: Path) -> tuple[list[IdentityCandidate], list[dict[str, Any]]]:
    players = load_json(repo_root / "public/data/Players.json", []) or []
    relevant = load_json(repo_root / "public/data/Players_Relevant.json", []) or []
    candidates: list[IdentityCandidate] = []
    for row in players:
        ids = {}
        if sleeper := clean(row.get("ID")):
            ids["Sleeper"] = sleeper
        if tank := clean(row.get("TankID")):
            ids["Tank01"] = tank
        if not ids:
            continue
        candidates.append(IdentityCandidate(
            ids=ids, name=clean(row.get("Name")) or clean(row.get("FullName")),
            first_name=clean(row.get("FirstName")), last_name=clean(row.get("LastName")),
            birth_date=clean(row.get("BirthDate")), position=clean(row.get("Position")),
            latest_team=clean(row.get("Team")) or clean(row.get("TeamID")),
            source="app.Players", priority=30,
        ))
    return candidates, relevant


def raw_identity_candidates(repo_root: Path, datasets: dict[str, Dataset]) -> tuple[list[IdentityCandidate], list[dict[str, str]]]:
    del repo_root
    candidates: list[IdentityCandidate] = []
    ff_rows: list[dict[str, str]] = []
    for row in iter_csv(datasets["nflverse.players"].raw_path):
        ids = ids_from_players(row)
        if ids:
            candidates.append(IdentityCandidate(
                ids=ids, name=clean(row.get("display_name")),
                first_name=clean(row.get("first_name")) or clean(row.get("common_first_name")),
                last_name=clean(row.get("last_name")), birth_date=clean(row.get("birth_date")),
                position=clean(row.get("position")), latest_team=clean(row.get("latest_team")),
                source="nflverse.players", priority=10,
            ))
    for row in iter_csv(datasets["nflverse.ff-player-ids"].raw_path):
        ff_rows.append(row)
        ids = ids_from_ff(row)
        if ids:
            candidates.append(IdentityCandidate(
                ids=ids, name=clean(row.get("name")), first_name=None, last_name=None,
                birth_date=clean(row.get("birthdate")), position=clean(row.get("position")),
                latest_team=clean(row.get("team")), source="nflverse.ff-player-ids", priority=20,
            ))
    return candidates, ff_rows


def existing_identity_candidates(repo_root: Path) -> list[IdentityCandidate]:
    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    result = []
    for row in payload.get("Players", []):
        ids = {key: clean(value) for key, value in (row.get("IDs") or {}).items() if clean(value)}
        if ids:
            result.append(IdentityCandidate(
                ids=ids, name=clean(row.get("Name")), first_name=clean(row.get("FirstName")),
                last_name=clean(row.get("LastName")), birth_date=clean(row.get("BirthDate")),
                position=clean(row.get("Position")), latest_team=clean(row.get("LatestTeam")),
                source="canonical-existing", priority=0, existing_internal_id=clean(row.get("NFLPlayerID")),
            ))
    return result


def build_identities(repo_root: Path, datasets: dict[str, Dataset]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    raw_candidates, ff_rows = raw_identity_candidates(repo_root, datasets)
    app_candidates, _ = app_player_candidates(repo_root)
    candidates = existing_identity_candidates(repo_root) + raw_candidates + app_candidates
    uf, id_owner, indexes = UnionFind(), {}, []
    for candidate in candidates:
        idx = uf.add()
        indexes.append(idx)
        for key, value in candidate.ids.items():
            token = (key, value)
            if token in id_owner:
                uf.union(idx, id_owner[token])
            else:
                id_owner[token] = idx

    components: dict[int, list[IdentityCandidate]] = defaultdict(list)
    for idx, candidate in zip(indexes, candidates):
        components[uf.find(idx)].append(candidate)

    canonical = []
    for members in components.values():
        external_values: dict[str, set[str]] = defaultdict(set)
        existing_ids, sources = set(), set()
        for member in members:
            sources.add(member.source)
            if member.existing_internal_id:
                existing_ids.add(member.existing_internal_id)
            for key, value in member.ids.items():
                external_values[key].add(value)
        conflicts = {key: sorted(values) for key, values in external_values.items() if len(values) > 1}
        if conflicts:
            raise ValueError(f"Identity component has conflicting IDs for the same provider: {conflicts}")
        if len(existing_ids) > 1:
            raise ValueError(f"Identity component merges multiple existing NFLPlayerIDs: {sorted(existing_ids)}")
        ids = {key: next(iter(values)) for key, values in external_values.items()}
        if existing_ids:
            internal_id = next(iter(existing_ids))
        else:
            seed = next((f"{key}:{ids[key]}" for key in ("GSIS", "Sleeper", "PFR", "ESPN", "MFL", "Tank01") if ids.get(key)), None)
            internal_id = stable_internal_id(seed or "|".join(f"{key}:{ids[key]}" for key in sorted(ids)))
        ranked = sorted(members, key=lambda item: item.priority)
        def first(field: str) -> str | None:
            return next((getattr(item, field) for item in ranked if getattr(item, field)), None)
        canonical.append({
            "NFLPlayerID": internal_id, "Name": first("name"), "FirstName": first("first_name"),
            "LastName": first("last_name"), "BirthDate": first("birth_date"), "Position": first("position"),
            "LatestTeam": first("latest_team"), "IDs": {key: ids[key] for key in IDENTITY_ID_KEYS if key in ids},
            "Sources": sorted(sources),
        })
    duplicate_internal = [key for key, rows in _group(canonical, "NFLPlayerID").items() if len(rows) > 1]
    if duplicate_internal:
        raise ValueError(f"Duplicate NFLPlayerID values generated: {duplicate_internal[:10]}")
    canonical.sort(key=lambda item: ((item.get("Name") or "").lower(), item["NFLPlayerID"]))
    return canonical, ff_rows


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def identity_lookup(canonical: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    lookup = {}
    for row in canonical:
        for key, value in (row.get("IDs") or {}).items():
            token = (key, value)
            previous = lookup.get(token)
            if previous and previous != row["NFLPlayerID"]:
                raise ValueError(f"External ID {key}:{value} maps to multiple canonical players")
            lookup[token] = row["NFLPlayerID"]
    return lookup
