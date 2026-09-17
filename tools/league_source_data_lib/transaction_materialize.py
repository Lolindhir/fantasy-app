from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .core import canonical_league_season_id
from .materialize import CanonicalOutput, PlayerMappingResolver, _canonicalize_transactions
from .registry import LeagueDataset
from .week_structure import resolve_nfl_regular_season_week_ceiling

TRANSACTION_DATASET_ID = "sleeper.transactions"
TRANSACTION_SCOPE_DEPENDENCIES = (
    "canonical-members",
    "canonical-rosters",
    "nfl-player-provider-mappings",
    "raw-sleeper-transactions",
)


def _read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(f"Required transaction materialization input is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _transaction_dataset(registry: Iterable[LeagueDataset]) -> LeagueDataset:
    matches = [item for item in registry if item.id == TRANSACTION_DATASET_ID]
    if len(matches) != 1:
        raise ValueError(
            f"League registry must contain exactly one {TRANSACTION_DATASET_ID} dataset"
        )
    dataset = matches[0]
    if dataset.scope != "week":
        raise ValueError(f"{TRANSACTION_DATASET_ID} must be week-scoped")
    if dataset.week_start is None or dataset.week_end_source != "nfl-regular-season-schedule":
        raise ValueError(
            f"{TRANSACTION_DATASET_ID} must use the canonical NFL regular-season week boundary"
        )
    return dataset


def _manifest(repo_root: Path, canonical_league_id: str) -> dict:
    path = repo_root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"League manifest must be an object: {path}")
    if str(raw.get("CanonicalLeagueID") or "") != canonical_league_id:
        raise ValueError(f"League manifest CanonicalLeagueID mismatch: {path}")
    if str(raw.get("Provider") or "") != "Sleeper":
        raise ValueError("Transaction materialization currently supports Sleeper only")
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


def plan_transaction_materialization(
    repo_root: Path,
    canonical_league_id: str,
    registry: Iterable[LeagueDataset],
    resolver: PlayerMappingResolver,
    *,
    seasons: set[int] | None = None,
    weeks: set[int] | None = None,
) -> list[CanonicalOutput]:
    dataset = _transaction_dataset(registry)
    if weeks and any(week < 1 for week in weeks):
        raise ValueError("Transaction materialization weeks must be positive integers")

    manifest = _manifest(repo_root, canonical_league_id)
    outputs: list[CanonicalOutput] = []
    seen_paths: set[Path] = set()

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

        week_ceiling = resolve_nfl_regular_season_week_ceiling(repo_root, season)
        assert dataset.week_start is not None
        target_weeks = sorted(weeks) if weeks else list(
            range(dataset.week_start, week_ceiling + 1)
        )
        invalid_weeks = [
            week
            for week in target_weeks
            if week < dataset.week_start or week > week_ceiling
        ]
        if invalid_weeks:
            raise ValueError(
                f"Requested transaction week(s) {invalid_weeks} are outside "
                f"{dataset.week_start}-{week_ceiling} for season {season}"
            )

        raw_root = (
            repo_root
            / "source-data"
            / "providers"
            / "sleeper"
            / "leagues"
            / provider_league_id
            / "transactions"
        )
        for week in target_weeks:
            raw_transactions = _read_json(raw_root / f"week-{week}.json")
            output = CanonicalOutput(
                season_root / "transactions" / f"week-{week}.json",
                _canonicalize_transactions(
                    raw_transactions,
                    season_id,
                    member_by_provider,
                    roster_by_provider,
                    resolver,
                    season,
                    week,
                ),
            )
            if output.path in seen_paths:
                raise ValueError(
                    f"Canonical League transaction output path collision: {output.path}"
                )
            seen_paths.add(output.path)
            outputs.append(output)

    return sorted(outputs, key=lambda output: str(output.path))
