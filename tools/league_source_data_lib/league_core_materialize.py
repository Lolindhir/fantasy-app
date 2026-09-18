from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .core import canonical_league_season_id
from .materialize import (
    SCHEMA_VERSION,
    CanonicalOutput,
    PlayerMappingResolver,
    _canonical_trade_deadline_week,
    _canonicalize_bracket,
    _members_and_rosters,
)
from .registry import LeagueDataset

LEAGUE_CORE_DATASET_IDS = (
    "sleeper.league",
    "sleeper.league-members",
    "sleeper.league-rosters",
    "sleeper.winners-bracket",
    "sleeper.losers-bracket",
)
LEAGUE_CORE_SCOPE_DEPENDENCIES = (
    "raw-sleeper-league",
    "raw-sleeper-league-members",
    "raw-sleeper-league-rosters",
    "raw-sleeper-winners-bracket",
    "raw-sleeper-losers-bracket",
    "nfl-player-provider-mappings",
    "canonical-week-structure",
)


def _read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required League Core materialization input is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _registry_guard(registry: Iterable[LeagueDataset]) -> None:
    by_id = {item.id: item for item in registry}
    missing = set(LEAGUE_CORE_DATASET_IDS) - set(by_id)
    if missing:
        raise ValueError(
            f"League registry is missing required League Core inputs: {sorted(missing)}"
        )
    invalid = [
        dataset_id
        for dataset_id in LEAGUE_CORE_DATASET_IDS
        if by_id[dataset_id].scope != "league-instance"
    ]
    if invalid:
        raise ValueError(
            f"League Core datasets must be league-instance scoped: {sorted(invalid)}"
        )


def _manifest(repo_root: Path, canonical_league_id: str) -> dict:
    path = repo_root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"League manifest must be an object: {path}")
    if str(raw.get("CanonicalLeagueID") or "") != canonical_league_id:
        raise ValueError(f"League manifest CanonicalLeagueID mismatch: {path}")
    if str(raw.get("Provider") or "") != "Sleeper":
        raise ValueError("League Core materialization currently supports Sleeper only")
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


def _sleeper_provider_mapping(season_entry: dict, season: int) -> dict:
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
    return sleeper[0]


def resolve_current_league_core_season(
    repo_root: Path,
    canonical_league_id: str,
    current_provider_league_id: str,
) -> int:
    manifest = _manifest(repo_root, canonical_league_id)
    manifest_current_provider_id = str(manifest.get("CurrentProviderLeagueID") or "").strip()
    if manifest_current_provider_id != current_provider_league_id:
        raise ValueError(
            "Current League Core scope requires the League manifest to be attached to the "
            f"bootstrap current ProviderLeagueID: {manifest_current_provider_id or '<missing>'} "
            f"!= {current_provider_league_id}"
        )

    matches: list[int] = []
    for entry in manifest["Seasons"]:
        season = int(entry["Season"])
        mapping = _sleeper_provider_mapping(entry, season)
        if str(mapping.get("ProviderLeagueID") or "").strip() == current_provider_league_id:
            matches.append(season)
    if len(matches) != 1:
        raise ValueError(
            "Current ProviderLeagueID must map to exactly one canonical season for League Core scope: "
            f"{current_provider_league_id} -> {matches}"
        )
    return matches[0]


def _existing_week_structure(
    season_root: Path,
    canonical_league_id: str,
    season_id: str,
    season: int,
    provider_league_id: str,
) -> dict:
    path = season_root / "league.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Existing canonical league baseline must be an object: {path}")
    if str(raw.get("CanonicalLeagueID") or "") != canonical_league_id:
        raise ValueError(f"Existing canonical league baseline CanonicalLeagueID mismatch: {path}")
    if str(raw.get("CanonicalLeagueSeasonID") or "") != season_id:
        raise ValueError(f"Existing canonical league baseline season identity mismatch: {path}")
    if int(raw.get("Season")) != season:
        raise ValueError(f"Existing canonical league baseline season mismatch: {path}")

    mappings = raw.get("ProviderMappings")
    if not isinstance(mappings, list):
        raise ValueError(f"Existing canonical league baseline ProviderMappings must be an array: {path}")
    provider_ids = {
        str(item.get("ProviderLeagueID") or "").strip()
        for item in mappings
        if isinstance(item, dict)
        and item.get("Provider") == "Sleeper"
        and str(item.get("ProviderLeagueID") or "").strip()
    }
    if provider_ids != {provider_league_id}:
        raise ValueError(
            "Existing canonical league baseline provider identity mismatch: "
            f"{sorted(provider_ids)} != {[provider_league_id]}"
        )

    week_structure = raw.get("WeekStructure")
    if not isinstance(week_structure, dict) or not week_structure:
        raise ValueError(
            "League Core scope requires an existing accepted canonical WeekStructure; "
            "run full League Source materialization first"
        )
    return week_structure


def plan_league_core_materialization(
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
    seen_paths: set[Path] = set()

    for season_entry in _season_entries(manifest, canonical_league_id, seasons):
        season = int(season_entry["Season"])
        season_id = str(season_entry["CanonicalLeagueSeasonID"])
        provider_mapping = _sleeper_provider_mapping(season_entry, season)
        provider_league_id = str(provider_mapping["ProviderLeagueID"])
        raw_base = (
            repo_root
            / "source-data"
            / "providers"
            / "sleeper"
            / "leagues"
            / provider_league_id
        )
        season_root = (
            repo_root
            / "source-data"
            / "leagues"
            / canonical_league_id
            / "seasons"
            / str(season)
        )

        league_raw = _read_json(raw_base / "league.json")
        members_raw = _read_json(raw_base / "members.json")
        rosters_raw = _read_json(raw_base / "rosters.json")
        winners_raw = _read_json(raw_base / "winners-bracket.json")
        losers_raw = _read_json(raw_base / "losers-bracket.json")
        if not isinstance(league_raw, dict):
            raise ValueError(f"Sleeper league raw must be an object for {provider_league_id}")
        if str(league_raw.get("league_id") or "") != provider_league_id:
            raise ValueError(f"Sleeper league raw id mismatch for {provider_league_id}")
        if int(league_raw.get("season")) != season:
            raise ValueError(f"Sleeper league raw season mismatch for {provider_league_id}")

        members, rosters, _, roster_by_provider = _members_and_rosters(
            canonical_league_id,
            season_id,
            members_raw,
            rosters_raw,
            resolver,
            season,
        )
        winners = _canonicalize_bracket(winners_raw, roster_by_provider, "winners")
        losers = _canonicalize_bracket(losers_raw, roster_by_provider, "losers")
        week_structure = _existing_week_structure(
            season_root,
            canonical_league_id,
            season_id,
            season,
            provider_league_id,
        )
        league_settings = league_raw.get("settings") or {}
        league = {
            "schemaVersion": SCHEMA_VERSION,
            "CanonicalLeagueID": canonical_league_id,
            "CanonicalLeagueSeasonID": season_id,
            "PreviousCanonicalLeagueSeasonID": season_entry.get("PreviousCanonicalLeagueSeasonID"),
            "Season": season,
            "Name": league_raw.get("name"),
            "Status": league_raw.get("status"),
            "SeasonType": league_raw.get("season_type"),
            "Avatar": league_raw.get("avatar"),
            "Settings": league_settings,
            "TradeDeadlineWeek": _canonical_trade_deadline_week(league_settings),
            "ScoringSettings": league_raw.get("scoring_settings") or {},
            "RosterPositions": league_raw.get("roster_positions") or [],
            "WeekStructure": week_structure,
            "ProviderMappings": season_entry.get("ProviderMappings") or [],
            "ProviderLineageEvidence": {
                "PreviousProviderLeagueID": provider_mapping.get("PreviousProviderLeagueID")
            },
        }

        season_outputs = [
            CanonicalOutput(season_root / "league.json", league),
            CanonicalOutput(season_root / "members.json", members),
            CanonicalOutput(season_root / "rosters.json", rosters),
            CanonicalOutput(season_root / "winners-bracket.json", winners),
            CanonicalOutput(season_root / "losers-bracket.json", losers),
        ]
        for output in season_outputs:
            if output.path in seen_paths:
                raise ValueError(f"Canonical League Core output path collision: {output.path}")
            seen_paths.add(output.path)
            outputs.append(output)

    return sorted(outputs, key=lambda output: str(output.path))
