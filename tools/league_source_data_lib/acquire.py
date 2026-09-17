from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .core import SleeperLeagueInstance, write_json_if_changed
from .registry import LeagueDataset
from .week_structure import resolve_nfl_regular_season_week_ceiling

API_ROOT = "https://api.sleeper.app"
SLEEPER_FETCH_MAX_ATTEMPTS = 3
SLEEPER_FETCH_BACKOFF_SECONDS = (1.0, 3.0)
SLEEPER_RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PlannedRawWrite:
    dataset_id: str
    provider_league_id: str
    season: int
    raw_path: Path
    metadata_path: Path
    payload: object
    source_url: str
    partition: dict


def _log_fetch_retry(source_url: str, attempt: int, error: BaseException, delay: float) -> None:
    print(
        f"Sleeper source fetch transient failure; retrying in {delay:g}s "
        f"after attempt {attempt}/{SLEEPER_FETCH_MAX_ATTEMPTS}: {source_url}: {error}",
        file=sys.stderr,
    )


def fetch_sleeper_json(source_url: str) -> object:
    request = urllib.request.Request(source_url, headers={"User-Agent": "fantasy-app-source-data/1"})
    for attempt in range(1, SLEEPER_FETCH_MAX_ATTEMPTS + 1):
        retry_error: BaseException | None = None
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    error = RuntimeError(f"Sleeper source fetch failed: HTTP {response.status} {source_url}")
                    if response.status not in SLEEPER_RETRYABLE_HTTP_STATUS_CODES or attempt >= SLEEPER_FETCH_MAX_ATTEMPTS:
                        raise error
                    retry_error = error
                else:
                    return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in SLEEPER_RETRYABLE_HTTP_STATUS_CODES or attempt >= SLEEPER_FETCH_MAX_ATTEMPTS:
                raise
            retry_error = error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt >= SLEEPER_FETCH_MAX_ATTEMPTS:
                raise
            retry_error = error

        if retry_error is None:
            raise RuntimeError(f"Sleeper source fetch failed without a retryable error: {source_url}")
        delay = SLEEPER_FETCH_BACKOFF_SECONDS[attempt - 1]
        _log_fetch_retry(source_url, attempt, retry_error, delay)
        time.sleep(delay)

    raise RuntimeError(f"Sleeper source fetch exhausted unexpectedly: {source_url}")


def _validate_payload(dataset: LeagueDataset, payload: object, source_url: str) -> None:
    if dataset.response_type == "object" and not isinstance(payload, dict):
        raise ValueError(f"{dataset.id} must return an object: {source_url}")
    if dataset.response_type == "array" and not isinstance(payload, list):
        raise ValueError(f"{dataset.id} must return an array: {source_url}")
    if dataset.availability_policy == "required" and dataset.response_type == "array" and not payload:
        raise ValueError(f"{dataset.id} unexpectedly returned an empty required array: {source_url}")


def _format(template: str, provider_league_id: str, week: int | None = None, draft_id: str | None = None) -> str:
    values = {
        "providerLeagueID": provider_league_id,
        "week": week,
        "draftID": draft_id,
    }
    return template.format(**values)


def _metadata(plan: PlannedRawWrite) -> dict:
    content = json.dumps(
        plan.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    result = {
        "schemaVersion": 1,
        "Provider": "Sleeper",
        "Dataset": plan.dataset_id,
        "ProviderLeagueID": plan.provider_league_id,
        "Season": plan.season,
        "SourceUrl": plan.source_url,
        "ContentSha256": hashlib.sha256(content).hexdigest(),
    }
    result.update(plan.partition)
    return result


def _existing_payload(repo_root: Path, raw_relative_path: str) -> object | None:
    path = repo_root / "source-data" / raw_relative_path
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _plan_one(
    repo_root: Path,
    dataset: LeagueDataset,
    instance: SleeperLeagueInstance,
    fetcher: Callable[[str], object],
    current_season: int,
    force: bool,
    offline: bool,
    *,
    week: int | None = None,
    draft_id: str | None = None,
    seeded_payload: object | None = None,
) -> PlannedRawWrite:
    raw_relative = _format(dataset.raw_path, instance.provider_league_id, week, draft_id)
    metadata_relative = _format(dataset.metadata_path, instance.provider_league_id, week, draft_id)
    endpoint = _format(dataset.endpoint, instance.provider_league_id, week, draft_id)
    source_url = f"{API_ROOT}{endpoint}"

    existing = _existing_payload(repo_root, raw_relative)
    if offline:
        if existing is None and seeded_payload is None:
            raise FileNotFoundError(f"Offline raw dataset missing: {repo_root / 'source-data' / raw_relative}")
        payload = seeded_payload if seeded_payload is not None else existing
    elif instance.season < current_season and existing is not None and not force:
        payload = existing
    elif seeded_payload is not None:
        payload = seeded_payload
    else:
        payload = fetcher(source_url)
    _validate_payload(dataset, payload, source_url)
    partition: dict = {}
    if week is not None:
        partition["Week"] = week
    if draft_id is not None:
        partition["DraftID"] = draft_id
    return PlannedRawWrite(
        dataset_id=dataset.id,
        provider_league_id=instance.provider_league_id,
        season=instance.season,
        raw_path=repo_root / "source-data" / raw_relative,
        metadata_path=repo_root / "source-data" / metadata_relative,
        payload=payload,
        source_url=source_url,
        partition=partition,
    )


def _selected_datasets(
    datasets: list[LeagueDataset],
    dataset_ids: set[str] | None,
) -> list[LeagueDataset]:
    if not dataset_ids:
        return list(datasets)
    known = {item.id for item in datasets}
    unknown = dataset_ids - known
    if unknown:
        raise ValueError(f"Unknown League dataset id(s): {', '.join(sorted(unknown))}")

    selected_ids = set(dataset_ids)
    by_id = {item.id: item for item in datasets}
    for dataset_id in tuple(selected_ids):
        dataset = by_id[dataset_id]
        if dataset.scope == "draft":
            if not dataset.discover_from:
                raise ValueError(f"Draft dataset {dataset.id} has no discovery dataset")
            selected_ids.add(dataset.discover_from)
    return [item for item in datasets if item.id in selected_ids]


def _selected_seasons(
    lineage: list[SleeperLeagueInstance],
    seasons: set[int] | None,
) -> set[int]:
    known = {item.season for item in lineage}
    if not seasons:
        return known
    unknown = seasons - known
    if unknown:
        raise ValueError(f"Unknown League season(s) for provider lineage: {', '.join(str(v) for v in sorted(unknown))}")
    return set(seasons)


def plan_raw_acquisition(
    repo_root: Path,
    lineage: list[SleeperLeagueInstance],
    datasets: list[LeagueDataset],
    fetcher: Callable[[str], object],
    *,
    force: bool = False,
    offline: bool = False,
    dataset_ids: set[str] | None = None,
    seasons: set[int] | None = None,
    weeks: set[int] | None = None,
) -> list[PlannedRawWrite]:
    if not lineage:
        raise ValueError("Cannot acquire league datasets without provider lineage")
    if weeks and any(week < 1 for week in weeks):
        raise ValueError("League acquisition weeks must be positive integers")

    current_season = lineage[0].season
    selected_datasets = _selected_datasets(datasets, dataset_ids)
    selected_seasons = _selected_seasons(lineage, seasons)

    league_datasets = [item for item in selected_datasets if item.scope == "league-instance"]
    week_datasets = [item for item in selected_datasets if item.scope == "week"]
    draft_datasets = [item for item in selected_datasets if item.scope == "draft"]
    if weeks and not week_datasets:
        raise ValueError("--week targeting requires at least one selected week-scoped dataset")

    league_drafts = next((item for item in league_datasets if item.id == "sleeper.league-drafts"), None)
    if draft_datasets and league_drafts is None:
        raise ValueError("Draft datasets require sleeper.league-drafts discovery dataset")

    plans: list[PlannedRawWrite] = []
    week_ceilings: dict[int, int] = {}
    for instance in lineage:
        if instance.season not in selected_seasons:
            continue

        by_id: dict[str, PlannedRawWrite] = {}
        for dataset in league_datasets:
            seeded = instance.payload if dataset.id == "sleeper.league" else None
            plan = _plan_one(
                repo_root,
                dataset,
                instance,
                fetcher,
                current_season,
                force,
                offline,
                seeded_payload=seeded,
            )
            plans.append(plan)
            by_id[dataset.id] = plan

        if week_datasets:
            week_ceiling = week_ceilings.setdefault(
                instance.season,
                resolve_nfl_regular_season_week_ceiling(repo_root, instance.season),
            )
            for dataset in week_datasets:
                assert dataset.week_start is not None
                if dataset.week_end_source != "nfl-regular-season-schedule":
                    raise ValueError(
                        f"Unsupported week end source for {dataset.id}: {dataset.week_end_source!r}"
                    )
                if dataset.week_start > week_ceiling:
                    raise ValueError(
                        f"Week start {dataset.week_start} exceeds NFL schedule ceiling "
                        f"{week_ceiling} for {dataset.id} season {instance.season}"
                    )

                target_weeks = sorted(weeks) if weeks else list(range(dataset.week_start, week_ceiling + 1))
                invalid_weeks = [
                    week for week in target_weeks if week < dataset.week_start or week > week_ceiling
                ]
                if invalid_weeks:
                    raise ValueError(
                        f"Requested week(s) {invalid_weeks} are outside {dataset.id} "
                        f"range {dataset.week_start}-{week_ceiling} for season {instance.season}"
                    )
                for week in target_weeks:
                    plans.append(
                        _plan_one(
                            repo_root,
                            dataset,
                            instance,
                            fetcher,
                            current_season,
                            force,
                            offline,
                            week=week,
                        )
                    )

        if draft_datasets:
            draft_index = by_id["sleeper.league-drafts"].payload
            if not isinstance(draft_index, list):
                raise ValueError("sleeper.league-drafts must be an array before draft discovery")
            draft_ids: list[str] = []
            seen: set[str] = set()
            for draft in draft_index:
                if not isinstance(draft, dict):
                    raise ValueError(
                        f"Sleeper league draft index contains non-object for {instance.provider_league_id}"
                    )
                draft_id = str(draft.get("draft_id") or "").strip()
                if not draft_id or not draft_id.isdigit():
                    raise ValueError(
                        f"Sleeper league draft index contains invalid draft_id for {instance.provider_league_id}: {draft_id!r}"
                    )
                if draft_id in seen:
                    raise ValueError(
                        f"Duplicate Sleeper draft_id {draft_id} for league {instance.provider_league_id}"
                    )
                seen.add(draft_id)
                draft_ids.append(draft_id)
            for draft_id in sorted(draft_ids):
                for dataset in draft_datasets:
                    plans.append(
                        _plan_one(
                            repo_root,
                            dataset,
                            instance,
                            fetcher,
                            current_season,
                            force,
                            offline,
                            draft_id=draft_id,
                        )
                    )

    seen_paths: dict[Path, str] = {}
    for plan in plans:
        for path in (plan.raw_path, plan.metadata_path):
            owner = seen_paths.get(path)
            if owner is not None and owner != plan.dataset_id:
                raise ValueError(f"League dataset path collision: {path} ({owner}, {plan.dataset_id})")
            seen_paths[path] = plan.dataset_id
    return plans


def persist_raw_plans(plans: list[PlannedRawWrite]) -> dict:
    raw_changed = 0
    metadata_changed = 0
    for plan in plans:
        raw_changed += int(write_json_if_changed(plan.raw_path, plan.payload))
        metadata_changed += int(write_json_if_changed(plan.metadata_path, _metadata(plan)))
    return {
        "DatasetPartitions": len(plans),
        "RawFilesChanged": raw_changed,
        "MetadataFilesChanged": metadata_changed,
    }
