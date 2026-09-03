from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

VALID_SCOPES = {"league-instance", "week", "draft"}
VALID_RESPONSE_TYPES = {"object", "array"}
VALID_AVAILABILITY = {"required", "required-empty-allowed"}
VALID_LIFECYCLE = {"seasonal-finalizable"}
VALID_WEEK_END_SOURCES = {"nfl-regular-season-schedule"}


@dataclass(frozen=True)
class LeagueDataset:
    id: str
    scope: str
    endpoint: str
    raw_path: str
    metadata_path: str
    response_type: str
    availability_policy: str
    refresh_policy: str
    retention_policy: str
    lifecycle: dict
    week_start: int | None = None
    week_end_source: str | None = None
    discover_from: str | None = None
    id_field: str | None = None


def load_league_registry(repo_root: Path) -> list[LeagueDataset]:
    path = repo_root / "source-data/league-registry.json"
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if raw.get("schemaVersion") != 1:
        raise ValueError("source-data/league-registry.json must use schemaVersion 1")
    if raw.get("provider") != "Sleeper":
        raise ValueError("League registry currently supports provider Sleeper only")
    items = raw.get("datasets")
    if not isinstance(items, list) or not items:
        raise ValueError("League registry datasets must be a non-empty array")

    result: list[LeagueDataset] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("League registry dataset entries must be objects")
        dataset_id = str(item.get("id") or "").strip()
        if not dataset_id or dataset_id in seen:
            raise ValueError(f"Missing or duplicate league dataset id: {dataset_id!r}")
        seen.add(dataset_id)
        scope = str(item.get("scope") or "")
        response_type = str(item.get("responseType") or "")
        availability = str(item.get("availabilityPolicy") or "")
        lifecycle = item.get("lifecycle")
        if scope not in VALID_SCOPES:
            raise ValueError(f"Invalid scope for {dataset_id}: {scope}")
        if response_type not in VALID_RESPONSE_TYPES:
            raise ValueError(f"Invalid responseType for {dataset_id}: {response_type}")
        if availability not in VALID_AVAILABILITY:
            raise ValueError(f"Invalid availabilityPolicy for {dataset_id}: {availability}")
        if not isinstance(lifecycle, dict) or lifecycle.get("class") not in VALID_LIFECYCLE:
            raise ValueError(f"Invalid lifecycle for {dataset_id}")

        endpoint = str(item.get("endpoint") or "")
        raw_path = str(item.get("rawPath") or "")
        metadata_path = str(item.get("metadataPath") or "")
        for field_name, template in (
            ("endpoint", endpoint),
            ("rawPath", raw_path),
            ("metadataPath", metadata_path),
        ):
            if not template:
                raise ValueError(f"Missing {field_name} for {dataset_id}")

        week_start = None
        week_end_source = None
        discover_from = id_field = None
        required_tokens = {"{providerLeagueID}"}
        if scope == "week":
            week_range = item.get("weekRange")
            if not isinstance(week_range, dict):
                raise ValueError(f"weekRange is required for {dataset_id}")
            week_start = int(week_range.get("start", 0))
            week_end_source = str(week_range.get("endSource") or "")
            if week_start < 1:
                raise ValueError(f"Invalid weekRange start for {dataset_id}: {week_start}")
            if week_end_source not in VALID_WEEK_END_SOURCES:
                raise ValueError(
                    f"Invalid weekRange endSource for {dataset_id}: {week_end_source!r}"
                )
            if "end" in week_range:
                raise ValueError(
                    f"Fixed weekRange end is prohibited for {dataset_id}; use endSource"
                )
            required_tokens.add("{week}")
        elif scope == "draft":
            discover_from = str(item.get("discoverFrom") or "")
            id_field = str(item.get("idField") or "")
            if not discover_from or not id_field:
                raise ValueError(f"discoverFrom and idField are required for {dataset_id}")
            required_tokens.add("{draftID}")

        for token in required_tokens:
            if token not in endpoint and token not in raw_path and token not in metadata_path:
                raise ValueError(f"Required token {token} is absent for {dataset_id}")
        if "{providerLeagueID}" not in raw_path or "{providerLeagueID}" not in metadata_path:
            raise ValueError(f"Provider league paths must be partitioned by providerLeagueID for {dataset_id}")
        if scope == "week" and ("{week}" not in raw_path or "{week}" not in metadata_path):
            raise ValueError(f"Week dataset paths must include {{week}} for {dataset_id}")
        if scope == "draft" and ("{draftID}" not in raw_path or "{draftID}" not in metadata_path):
            raise ValueError(f"Draft dataset paths must include {{draftID}} for {dataset_id}")

        result.append(
            LeagueDataset(
                id=dataset_id,
                scope=scope,
                endpoint=endpoint,
                raw_path=raw_path,
                metadata_path=metadata_path,
                response_type=response_type,
                availability_policy=availability,
                refresh_policy=str(item.get("refreshPolicy") or ""),
                retention_policy=str(item.get("retentionPolicy") or ""),
                lifecycle=dict(lifecycle),
                week_start=week_start,
                week_end_source=week_end_source,
                discover_from=discover_from,
                id_field=id_field,
            )
        )

    ids = {item.id for item in result}
    for dataset in result:
        if dataset.scope == "draft" and dataset.discover_from not in ids:
            raise ValueError(
                f"Draft dataset {dataset.id} references unknown discoverFrom {dataset.discover_from}"
            )
    return result
