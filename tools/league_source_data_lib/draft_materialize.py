from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .core import canonical_league_season_id
from .materialize import CanonicalOutput, PlayerMappingResolver, _canonicalize_drafts
from .registry import LeagueDataset

DRAFT_DATASET_IDS = (
    "sleeper.league-drafts",
    "sleeper.draft-detail",
    "sleeper.draft-picks",
    "sleeper.draft-traded-picks",
)
DRAFT_SCOPE_DEPENDENCIES = (
    "canonical-members",
    "canonical-rosters",
    "nfl-player-provider-mappings",
    "raw-sleeper-league-drafts",
    "raw-sleeper-draft-detail",
    "raw-sleeper-draft-picks",
    "raw-sleeper-draft-traded-picks",
)


def _read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required draft materialization input is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _registry_guard(registry: Iterable[LeagueDataset]) -> None:
    by_id = {item.id: item for item in registry}
    missing = set(DRAFT_DATASET_IDS) - set(by_id)
    if missing:
        raise ValueError(
            f"League registry is missing required draft inputs: {sorted(missing)}"
        )
    if by_id["sleeper.league-drafts"].scope != "league-instance":
        raise ValueError("sleeper.league-drafts must be league-instance scoped")
    for dataset_id in DRAFT_DATASET_IDS[1:]:
        dataset = by_id[dataset_id]
        if dataset.scope != "draft":
            raise ValueError(f"{dataset_id} must be draft scoped")
        if dataset.discover_from != "sleeper.league-drafts":
            raise ValueError(
                f"{dataset_id} must discover drafts from sleeper.league-drafts"
            )


def _manifest(repo_root: Path, canonical_league_id: str) -> dict:
    path = repo_root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"League manifest must be an object: {path}")
    if str(raw.get("CanonicalLeagueID") or "") != canonical_league_id:
        raise ValueError(f"League manifest CanonicalLeagueID mismatch: {path}")
    if str(raw.get("Provider") or "") != "Sleeper":
        raise ValueError("Draft materialization currently supports Sleeper only")
    seasons = raw.get("Seasons")
    if not isinstance(seasons, list) or not seasons:
        raise ValueError(f"League manifest Seasons must be a non-empty array: {path}")
    return raw


def _season_entries(
    manifest: dict,
    canonical_league_id: str,
    seasons: set[int] | None,
) -> list[dict]:
    by_season: dict[int, dict] = {}
    for item in manifest["Seasons"]:
        if not isinstance(item, dict):
            raise ValueError("League manifest season entries must be objects")
        season = int(item["Season"])
        if season in by_season:
            raise ValueError(f"Duplicate season {season} in league manifest")
        expected_id = canonical_league_season_id(canonical_league_id, season)
        actual_id = str(item.get("CanonicalLeagueSeasonID") or "")
        if actual_id != expected_id:
            raise ValueError(
                f"CanonicalLeagueSeasonID mismatch for {canonical_league_id}/{season}: "
                f"{actual_id or '<missing>'} != {expected_id}"
            )
        by_season[season] = item

    selected = set(seasons or by_season.keys())
    unknown = selected - set(by_season)
    if unknown:
        raise ValueError(
            f"Unknown League season(s) for canonical league {canonical_league_id}: "
            f"{', '.join(str(value) for value in sorted(unknown))}"
        )
    return [by_season[season] for season in sorted(selected)]


def _sleeper_provider_league_id(season_entry: dict, season: int) -> str:
    mappings = season_entry.get("ProviderMappings")
    if not isinstance(mappings, list):
        raise ValueError(f"ProviderMappings must be an array for season {season}")
    sleeper = [
        item
        for item in mappings
        if isinstance(item, dict) and item.get("Provider") == "Sleeper"
    ]
    if len(sleeper) != 1:
        raise ValueError(f"Expected exactly one Sleeper mapping for season {season}")
    provider_league_id = str(sleeper[0].get("ProviderLeagueID") or "").strip()
    if not provider_league_id:
        raise ValueError(f"Sleeper ProviderLeagueID is required for season {season}")
    return provider_league_id


def _canonical_provider_lookup(
    raw: object,
    *,
    canonical_field: str,
    provider_field: str,
    label: str,
) -> dict[str, str]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    result: dict[str, str] = {}
    canonical_claims: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        canonical_id = str(item.get(canonical_field) or "").strip()
        if not canonical_id:
            raise ValueError(f"{label}[{index}] is missing {canonical_field}")
        if canonical_id in canonical_claims:
            raise ValueError(f"Duplicate {canonical_field} in {label}: {canonical_id}")
        canonical_claims.add(canonical_id)
        mappings = item.get("ProviderMappings")
        if not isinstance(mappings, list):
            raise ValueError(f"{label}[{index}] ProviderMappings must be an array")
        values = {
            str(mapping.get(provider_field) or "").strip()
            for mapping in mappings
            if isinstance(mapping, dict)
            and mapping.get("Provider") == "Sleeper"
            and str(mapping.get(provider_field) or "").strip()
        }
        if len(values) != 1:
            raise ValueError(
                f"{label}[{index}] requires exactly one Sleeper {provider_field}; "
                f"found {sorted(values)}"
            )
        provider_id = next(iter(values))
        previous = result.get(provider_id)
        if previous is not None and previous != canonical_id:
            raise ValueError(
                f"Sleeper {provider_field} {provider_id} maps to both "
                f"{previous} and {canonical_id}"
            )
        result[provider_id] = canonical_id
    return result


def resolve_current_draft_season(
    repo_root: Path,
    canonical_league_id: str,
    current_provider_league_id: str,
) -> int:
    manifest = _manifest(repo_root, canonical_league_id)
    manifest_current_provider_id = str(manifest.get("CurrentProviderLeagueID") or "").strip()
    if manifest_current_provider_id != current_provider_league_id:
        raise ValueError(
            "Current draft scope requires the League manifest to be attached to the "
            f"bootstrap current ProviderLeagueID: {manifest_current_provider_id or '<missing>'} "
            f"!= {current_provider_league_id}"
        )
    matches: list[int] = []
    for entry in manifest["Seasons"]:
        season = int(entry["Season"])
        if _sleeper_provider_league_id(entry, season) == current_provider_league_id:
            matches.append(season)
    if len(matches) != 1:
        raise ValueError(
            "Current ProviderLeagueID must map to exactly one canonical season for draft scope: "
            f"{current_provider_league_id} -> {matches}"
        )
    return matches[0]


def plan_draft_materialization(
    repo_root: Path,
    canonical_league_id: str,
    registry: Iterable[LeagueDataset],
    resolver: PlayerMappingResolver,
    *,
    seasons: set[int] | None = None,
) -> list[CanonicalOutput]:
    _registry_guard(registry)
    manifest = _manifest(repo_root, canonical_league_id)
    outputs: list[CanonicalOutput] = []

    for season_entry in _season_entries(manifest, canonical_league_id, seasons):
        season = int(season_entry["Season"])
        season_id = str(season_entry["CanonicalLeagueSeasonID"])
        provider_league_id = _sleeper_provider_league_id(season_entry, season)
        season_root = (
            repo_root
            / "source-data"
            / "leagues"
            / canonical_league_id
            / "seasons"
            / str(season)
        )
        member_by_provider = _canonical_provider_lookup(
            _read_json(season_root / "members.json"),
            canonical_field="CanonicalLeagueMemberID",
            provider_field="ProviderUserID",
            label=f"canonical members {canonical_league_id}/{season}",
        )
        roster_by_provider = _canonical_provider_lookup(
            _read_json(season_root / "rosters.json"),
            canonical_field="CanonicalLeagueRosterID",
            provider_field="ProviderRosterID",
            label=f"canonical rosters {canonical_league_id}/{season}",
        )
        raw_base = (
            repo_root
            / "source-data"
            / "providers"
            / "sleeper"
            / "leagues"
            / provider_league_id
        )
        draft_index_raw = _read_json(raw_base / "drafts" / "index.json")
        drafts = _canonicalize_drafts(
            raw_base,
            draft_index_raw,
            season_id,
            member_by_provider,
            roster_by_provider,
            resolver,
            season,
        )
        outputs.append(CanonicalOutput(season_root / "drafts.json", drafts))

    return sorted(outputs, key=lambda output: str(output.path))
