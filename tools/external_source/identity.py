"""Identity index per external dataset (contract: external-source-data.yaml, ADR-060).

Maps (Season, ProviderPlayerID) of the normalized provider snapshots to a CanonicalPlayerID through
data-source/nfl/identities/provider-mappings.json with season validity. Fail-closed and without any
name fallback: an unknown ID is unresolved, a contradicting mapping is ambiguous and carries no ID.
The index is a regenerable product; it is written only when its content differs.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from data_roots import data_source_dir
from nfl_season_context import resolve_season_for_date

from .registry import dataset_dir
from .snapshot_discovery import discover_snapshots

IDENTITY_FILE_NAME = "identity.json"
SCHEMA_VERSION = 1
PROVIDER_MAPPINGS_RELATIVE = Path("nfl") / "identities" / "provider-mappings.json"
SNAPSHOTS_DIR = "snapshots"
RANKING_FILE = "ranking.csv"
ASSET_TYPE_COLUMN = "asset_type"
PLAYER_ASSET_TYPE = "player"


class MappingIndex:
    """Provider mappings indexed by (Provider, ExternalID) for season-valid lookups."""

    def __init__(self, mappings: Iterable[dict[str, Any]]) -> None:
        self._by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for mapping in mappings:
            self._by_key.setdefault((mapping["Provider"], str(mapping["ExternalID"])), []).append(mapping)

    @classmethod
    def load(cls, repo_root: Path) -> "MappingIndex":
        path = data_source_dir(repo_root) / PROVIDER_MAPPINGS_RELATIVE
        return cls(json.loads(path.read_text(encoding="utf-8"))["Mappings"])

    def candidates(self, provider_key: str, external_id: str, season: int) -> list[str]:
        found = {
            m["CanonicalPlayerID"]
            for m in self._by_key.get((provider_key, str(external_id)), [])
            if m["FirstObservedSeason"] <= season <= m["LastObservedSeason"]
        }
        return sorted(found)


def resolve_entry(provider_key: str | None, provider_player_id: str, asset_type: str, season: int, index: MappingIndex) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "Season": season,
        "ProviderPlayerID": provider_player_id,
        "AssetType": asset_type,
        "CanonicalPlayerID": None,
        "Status": None,
        "Method": None,
    }
    if asset_type != PLAYER_ASSET_TYPE:
        entry["Status"] = "not-a-player"
    elif provider_key is None:
        entry["Status"] = "no-provider-key"
    else:
        candidates = index.candidates(provider_key, provider_player_id, season)
        if len(candidates) == 1:
            entry.update(CanonicalPlayerID=candidates[0], Status="resolved", Method="provider-mapping")
        elif candidates:
            entry["Status"] = "ambiguous"
        else:
            entry["Status"] = "unresolved"
    return entry


def snapshot_rows(snapshot_dir: Path, id_column: str) -> list[tuple[str, str]]:
    """(ProviderPlayerID, AssetType) of every ranking row of one snapshot."""
    path = snapshot_dir / RANKING_FILE
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or id_column not in reader.fieldnames:
            raise ValueError(f"{path}: identity column {id_column!r} not found")
        has_asset_type = ASSET_TYPE_COLUMN in reader.fieldnames
        rows = []
        for row in reader:
            provider_id = (row.get(id_column) or "").strip()
            if not provider_id:
                continue
            asset_type = (row.get(ASSET_TYPE_COLUMN) or "").strip() if has_asset_type else PLAYER_ASSET_TYPE
            rows.append((provider_id, asset_type or PLAYER_ASSET_TYPE))
    return rows


def build_identity(repo_root: Path, dataset: dict[str, Any], index: MappingIndex) -> dict[str, Any] | None:
    """Return the identity index of one dataset, or None when it has no snapshot yet."""
    base = dataset_dir(repo_root, dataset) / SNAPSHOTS_DIR
    if not base.is_dir():
        return None
    provider_key = dataset["identity"]["providerKey"]
    column = dataset["identity"]["column"]
    entries: dict[tuple[int, str, str], dict[str, Any]] = {}
    for snapshot in discover_snapshots(base):
        season = resolve_season_for_date(repo_root, snapshot.day.isoformat())
        for provider_id, asset_type in snapshot_rows(snapshot.directory, column):
            key = (season, provider_id, asset_type)
            if key not in entries:
                entries[key] = resolve_entry(provider_key, provider_id, asset_type, season, index)
    if not entries:
        return None
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "DatasetID": dataset["id"],
        "ProviderKey": provider_key,
        "Entries": [entries[key] for key in sorted(entries)],
    }


def render(identity: dict[str, Any]) -> str:
    return json.dumps(identity, indent=2, ensure_ascii=False) + "\n"


def write_if_changed(repo_root: Path, dataset: dict[str, Any], identity: dict[str, Any]) -> bool:
    path = dataset_dir(repo_root, dataset) / IDENTITY_FILE_NAME
    content = render(identity)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True
