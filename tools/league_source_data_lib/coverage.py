from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def _read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sleeper_player_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for mapping in value:
        if not isinstance(mapping, dict) or mapping.get("Provider") != "Sleeper":
            continue
        external = str(mapping.get("ProviderPlayerID") or "").strip()
        if external:
            result.append(external)
    return sorted(set(result))


def _iter_player_references(value: object) -> Iterable[tuple[str | None, list[str]]]:
    if isinstance(value, dict):
        if "CanonicalPlayerID" in value:
            sleeper_ids = _sleeper_player_ids(value.get("ProviderMappings"))
            if sleeper_ids:
                canonical = str(value.get("CanonicalPlayerID") or "").strip() or None
                yield canonical, sleeper_ids
        for child in value.values():
            yield from _iter_player_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_player_references(child)


def _empty_counts() -> dict[str, Any]:
    return {
        "ReferenceCount": 0,
        "ResolvedReferenceCount": 0,
        "UnresolvedReferenceCount": 0,
        "UniqueSleeperPlayerIDCount": 0,
        "UnresolvedUniqueSleeperPlayerIDCount": 0,
        "UnresolvedSleeperPlayerIDs": [],
    }


def _coverage_for_paths(paths: Iterable[Path]) -> dict[str, Any]:
    result = _empty_counts()
    all_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for canonical_player_id, sleeper_ids in _iter_player_references(_read_json(path)):
            result["ReferenceCount"] += 1
            all_ids.update(sleeper_ids)
            if canonical_player_id:
                result["ResolvedReferenceCount"] += 1
            else:
                result["UnresolvedReferenceCount"] += 1
                unresolved_ids.update(sleeper_ids)
    result["UniqueSleeperPlayerIDCount"] = len(all_ids)
    result["UnresolvedUniqueSleeperPlayerIDCount"] = len(unresolved_ids)
    result["UnresolvedSleeperPlayerIDs"] = sorted(unresolved_ids)
    return result


def build_season_player_reference_coverage(season_root: Path) -> dict[str, Any]:
    domains = {
        "Rosters": [season_root / "rosters.json"],
        "Drafts": [season_root / "drafts.json"],
        "Matchups": sorted((season_root / "matchups").glob("*.json")),
        "Transactions": sorted((season_root / "transactions").glob("*.json")),
    }
    by_domain = {
        domain: _coverage_for_paths(paths)
        for domain, paths in domains.items()
    }

    all_paths = [path for paths in domains.values() for path in paths]
    total = _coverage_for_paths(all_paths)
    total["ByDomain"] = by_domain
    total["Ready"] = total["UnresolvedReferenceCount"] == 0
    return total
