from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

CANONICAL_LEAGUE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_PROVIDERS = {"Sleeper"}


@dataclass(frozen=True)
class LeagueBootstrap:
    canonical_league_id: str
    provider: str
    current_provider_league_id: str
    path: Path


@dataclass(frozen=True)
class SleeperLeagueInstance:
    provider_league_id: str
    season: int
    previous_provider_league_id: str | None
    payload: dict


def canonical_league_season_id(canonical_league_id: str, season: int) -> str:
    if not CANONICAL_LEAGUE_ID_PATTERN.fullmatch(canonical_league_id):
        raise ValueError(f"Invalid CanonicalLeagueID: {canonical_league_id}")
    if season < 2000 or season > 2200:
        raise ValueError(f"Implausible league season: {season}")
    return f"{canonical_league_id}-{season}"


def _read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalized_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def write_json_if_changed(path: Path, value: object) -> bool:
    content = _normalized_json_bytes(value)
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def load_bootstraps(repo_root: Path) -> list[LeagueBootstrap]:
    bootstrap_dir = repo_root / "source-data/leagues/_bootstrap"
    if not bootstrap_dir.exists():
        return []
    result: list[LeagueBootstrap] = []
    seen_ids: set[str] = set()
    for path in sorted(bootstrap_dir.glob("*.json")):
        raw = _read_json(path)
        if not isinstance(raw, dict):
            raise ValueError(f"Bootstrap must be a JSON object: {path}")
        expected = {"CanonicalLeagueID", "Provider", "CurrentProviderLeagueID"}
        missing = expected - set(raw)
        extra = set(raw) - expected
        if missing or extra:
            raise ValueError(
                f"Bootstrap {path} must contain exactly {sorted(expected)}; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        canonical_id = str(raw["CanonicalLeagueID"]).strip()
        provider = str(raw["Provider"]).strip()
        current_id = str(raw["CurrentProviderLeagueID"]).strip()
        if not CANONICAL_LEAGUE_ID_PATTERN.fullmatch(canonical_id):
            raise ValueError(f"Invalid CanonicalLeagueID in {path}: {canonical_id}")
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported league provider in {path}: {provider}")
        if not current_id.isdigit():
            raise ValueError(f"Invalid CurrentProviderLeagueID in {path}: {current_id}")
        if canonical_id in seen_ids:
            raise ValueError(f"Duplicate CanonicalLeagueID bootstrap: {canonical_id}")
        seen_ids.add(canonical_id)
        if path.stem != canonical_id:
            raise ValueError(
                f"Bootstrap filename must equal CanonicalLeagueID: {path.name} != {canonical_id}.json"
            )
        result.append(LeagueBootstrap(canonical_id, provider, current_id, path))
    return result


def _normalize_previous(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text in {"", "0", "null", "None"} else text


def parse_sleeper_league(payload: object, requested_id: str) -> SleeperLeagueInstance:
    if not isinstance(payload, dict):
        raise ValueError(f"Sleeper league {requested_id} response must be an object")
    actual_id = str(payload.get("league_id") or "").strip()
    if actual_id != requested_id:
        raise ValueError(
            f"Sleeper league id mismatch: requested {requested_id}, response has {actual_id or '<missing>'}"
        )
    season_raw = payload.get("season")
    try:
        season = int(str(season_raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Sleeper league {requested_id} has invalid season: {season_raw!r}") from exc
    if season < 2000 or season > 2200:
        raise ValueError(f"Sleeper league {requested_id} has implausible season: {season}")
    previous = _normalize_previous(payload.get("previous_league_id"))
    if previous is not None and not previous.isdigit():
        raise ValueError(
            f"Sleeper league {requested_id} has invalid previous_league_id: {previous}"
        )
    return SleeperLeagueInstance(actual_id, season, previous, dict(payload))


def fetch_sleeper_league(provider_league_id: str) -> dict:
    url = f"https://api.sleeper.app/v1/league/{provider_league_id}"
    request = urllib.request.Request(url, headers={"User-Agent": "fantasy-app-source-data/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Sleeper league fetch failed for {provider_league_id}: HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if payload is None:
        raise RuntimeError(f"Sleeper league not found: {provider_league_id}")
    return payload


def persisted_sleeper_fetcher(repo_root: Path) -> Callable[[str], dict]:
    def fetch(provider_league_id: str) -> dict:
        path = (
            repo_root
            / "source-data/providers/sleeper/leagues"
            / provider_league_id
            / "league.json"
        )
        if not path.exists():
            raise FileNotFoundError(
                f"Offline Sleeper league raw data missing for {provider_league_id}: {path}"
            )
        value = _read_json(path)
        if not isinstance(value, dict):
            raise ValueError(f"Persisted Sleeper league raw data must be an object: {path}")
        return value

    return fetch


def discover_sleeper_lineage(
    current_provider_league_id: str,
    fetcher: Callable[[str], dict],
) -> list[SleeperLeagueInstance]:
    result: list[SleeperLeagueInstance] = []
    seen: set[str] = set()
    next_id: str | None = current_provider_league_id
    previous_child: SleeperLeagueInstance | None = None
    while next_id is not None:
        if next_id in seen:
            raise ValueError(f"Sleeper league lineage cycle detected at {next_id}")
        seen.add(next_id)
        instance = parse_sleeper_league(fetcher(next_id), next_id)
        if previous_child is not None and instance.season >= previous_child.season:
            raise ValueError(
                "Sleeper league lineage seasons must decrease when following previous_league_id: "
                f"{previous_child.provider_league_id}({previous_child.season}) -> "
                f"{instance.provider_league_id}({instance.season})"
            )
        result.append(instance)
        previous_child = instance
        next_id = instance.previous_provider_league_id
    return result


def _load_existing_manifests(repo_root: Path) -> dict[str, dict]:
    league_root = repo_root / "source-data/leagues"
    result: dict[str, dict] = {}
    if not league_root.exists():
        return result
    for path in sorted(league_root.glob("*/manifest.json")):
        if path.parent.name == "_bootstrap":
            continue
        raw = _read_json(path)
        if not isinstance(raw, dict):
            raise ValueError(f"League manifest must be a JSON object: {path}")
        canonical_id = str(raw.get("CanonicalLeagueID") or "").strip()
        if not canonical_id:
            raise ValueError(f"League manifest lacks CanonicalLeagueID: {path}")
        if canonical_id in result:
            raise ValueError(f"Duplicate manifest for CanonicalLeagueID {canonical_id}")
        result[canonical_id] = raw
    return result


def _provider_index(manifests: dict[str, dict]) -> dict[tuple[str, str], tuple[str, int]]:
    index: dict[tuple[str, str], tuple[str, int]] = {}
    for canonical_id, manifest in manifests.items():
        seasons = manifest.get("Seasons", [])
        if not isinstance(seasons, list):
            raise ValueError(f"League manifest Seasons must be an array: {canonical_id}")
        seen_seasons: set[int] = set()
        for season_entry in seasons:
            if not isinstance(season_entry, dict):
                raise ValueError(f"Invalid season entry in league manifest {canonical_id}")
            season = int(season_entry["Season"])
            if season in seen_seasons:
                raise ValueError(f"Duplicate season {season} in league manifest {canonical_id}")
            seen_seasons.add(season)
            mappings = season_entry.get("ProviderMappings", [])
            if not isinstance(mappings, list):
                raise ValueError(f"ProviderMappings must be an array in {canonical_id}/{season}")
            for mapping in mappings:
                provider = str(mapping.get("Provider") or "").strip()
                provider_id = str(mapping.get("ProviderLeagueID") or "").strip()
                key = (provider, provider_id)
                existing = index.get(key)
                if existing is not None and existing != (canonical_id, season):
                    raise ValueError(
                        f"Provider league mapping conflict for {provider}/{provider_id}: "
                        f"{existing[0]}/{existing[1]} vs {canonical_id}/{season}"
                    )
                index[key] = (canonical_id, season)
    return index


def build_manifest(
    bootstrap: LeagueBootstrap,
    lineage: Iterable[SleeperLeagueInstance],
    existing_manifests: dict[str, dict],
) -> dict:
    instances = list(lineage)
    if not instances:
        raise ValueError(f"No provider lineage discovered for {bootstrap.canonical_league_id}")
    if instances[0].provider_league_id != bootstrap.current_provider_league_id:
        raise ValueError("Discovered lineage does not start at bootstrap CurrentProviderLeagueID")

    provider_index = _provider_index(existing_manifests)
    for instance in instances:
        mapped = provider_index.get((bootstrap.provider, instance.provider_league_id))
        if mapped is not None and mapped[0] != bootstrap.canonical_league_id:
            raise ValueError(
                f"Provider league {bootstrap.provider}/{instance.provider_league_id} is already mapped "
                f"to {mapped[0]}, cannot attach to {bootstrap.canonical_league_id}"
            )

    existing = existing_manifests.get(bootstrap.canonical_league_id)
    existing_by_season: dict[int, dict] = {}
    existing_provider_by_season: dict[int, str] = {}
    if existing is not None:
        if str(existing.get("Provider") or "") != bootstrap.provider:
            raise ValueError(
                f"Provider change for {bootstrap.canonical_league_id} requires an explicit migration contract"
            )
        for item in existing.get("Seasons", []):
            season = int(item["Season"])
            existing_by_season[season] = item
            sleeper = [
                mapping for mapping in item.get("ProviderMappings", [])
                if mapping.get("Provider") == bootstrap.provider
            ]
            if len(sleeper) != 1:
                raise ValueError(
                    f"Expected exactly one {bootstrap.provider} mapping in existing manifest "
                    f"{bootstrap.canonical_league_id}/{season}"
                )
            existing_provider_by_season[season] = str(sleeper[0]["ProviderLeagueID"])

        known_current_ids = set(existing_provider_by_season.values())
        if bootstrap.current_provider_league_id not in known_current_ids and existing_by_season:
            latest_season = max(existing_by_season)
            latest_provider_id = existing_provider_by_season[latest_season]
            new_current = instances[0]
            if new_current.season <= latest_season:
                raise ValueError(
                    f"New current provider league season {new_current.season} does not advance "
                    f"known season {latest_season} for {bootstrap.canonical_league_id}"
                )
            if new_current.previous_provider_league_id != latest_provider_id:
                raise ValueError(
                    f"New current provider league {new_current.provider_league_id} does not connect to "
                    f"known latest provider league {latest_provider_id}"
                )

    discovered_by_season: dict[int, SleeperLeagueInstance] = {}
    by_provider_id = {instance.provider_league_id: instance for instance in instances}
    for instance in instances:
        duplicate = discovered_by_season.get(instance.season)
        if duplicate is not None and duplicate.provider_league_id != instance.provider_league_id:
            raise ValueError(
                f"Multiple {bootstrap.provider} league ids discovered for season {instance.season}: "
                f"{duplicate.provider_league_id}, {instance.provider_league_id}"
            )
        discovered_by_season[instance.season] = instance
        existing_provider_id = existing_provider_by_season.get(instance.season)
        if existing_provider_id is not None and existing_provider_id != instance.provider_league_id:
            raise ValueError(
                f"Season {instance.season} is already mapped to {existing_provider_id}, "
                f"not {instance.provider_league_id}"
            )

    for season, provider_id in existing_provider_by_season.items():
        if provider_id not in by_provider_id:
            raise ValueError(
                f"Persisted provider league {provider_id} for season {season} is no longer present "
                f"in discovered lineage for {bootstrap.canonical_league_id}"
            )

    seasons: list[dict] = []
    for season in sorted(discovered_by_season):
        instance = discovered_by_season[season]
        previous_canonical = None
        if instance.previous_provider_league_id is not None:
            previous = by_provider_id.get(instance.previous_provider_league_id)
            if previous is None:
                raise ValueError(
                    f"Missing previous provider league {instance.previous_provider_league_id} "
                    f"inside discovered lineage"
                )
            previous_canonical = canonical_league_season_id(
                bootstrap.canonical_league_id, previous.season
            )
        seasons.append(
            {
                "CanonicalLeagueSeasonID": canonical_league_season_id(
                    bootstrap.canonical_league_id, season
                ),
                "Season": season,
                "PreviousCanonicalLeagueSeasonID": previous_canonical,
                "ProviderMappings": [
                    {
                        "Provider": bootstrap.provider,
                        "ProviderLeagueID": instance.provider_league_id,
                        "PreviousProviderLeagueID": instance.previous_provider_league_id,
                    }
                ],
            }
        )

    current = instances[0]
    return {
        "schemaVersion": 1,
        "CanonicalLeagueID": bootstrap.canonical_league_id,
        "Provider": bootstrap.provider,
        "CurrentCanonicalLeagueSeasonID": canonical_league_season_id(
            bootstrap.canonical_league_id, current.season
        ),
        "CurrentProviderLeagueID": current.provider_league_id,
        "Seasons": seasons,
    }


def _raw_metadata(instance: SleeperLeagueInstance) -> dict:
    payload_bytes = json.dumps(
        instance.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schemaVersion": 1,
        "Provider": "Sleeper",
        "Dataset": "sleeper.league",
        "ProviderLeagueID": instance.provider_league_id,
        "Season": instance.season,
        "SourceUrl": f"https://api.sleeper.app/v1/league/{instance.provider_league_id}",
        "ContentSha256": hashlib.sha256(payload_bytes).hexdigest(),
    }


def sync_bootstrap(
    repo_root: Path,
    bootstrap: LeagueBootstrap,
    fetcher: Callable[[str], dict],
) -> dict:
    lineage = discover_sleeper_lineage(bootstrap.current_provider_league_id, fetcher)
    manifests = _load_existing_manifests(repo_root)
    manifest = build_manifest(bootstrap, lineage, manifests)

    raw_outputs: list[tuple[Path, object]] = []
    for instance in lineage:
        base = (
            repo_root
            / "source-data/providers/sleeper/leagues"
            / instance.provider_league_id
        )
        raw_outputs.append((base / "league.json", instance.payload))
        raw_outputs.append((base / "league.metadata.json", _raw_metadata(instance)))

    raw_changed = sum(write_json_if_changed(path, value) for path, value in raw_outputs)
    manifest_path = repo_root / "source-data/leagues" / bootstrap.canonical_league_id / "manifest.json"
    manifest_changed = write_json_if_changed(manifest_path, manifest)
    return {
        "CanonicalLeagueID": bootstrap.canonical_league_id,
        "SeasonCount": len(lineage),
        "RawFilesChanged": raw_changed,
        "ManifestChanged": manifest_changed,
    }
