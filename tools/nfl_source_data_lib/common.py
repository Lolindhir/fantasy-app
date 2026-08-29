from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = 1
CANONICAL_SCHEMA_VERSION = 2
REGISTRY_SCHEMA_VERSION = 3
SUPPORTED_REGISTRY_SCHEMA_VERSIONS = {1, 2, REGISTRY_SCHEMA_VERSION}

CANONICAL_PLAYER_ID_FIELD = "CanonicalPlayerID"
LEGACY_CANONICAL_PLAYER_ID_FIELD = "NFLPlayerID"
CANONICAL_PLAYER_IDS_FIELD = "CanonicalPlayerIDs"
LEGACY_CANONICAL_PLAYER_IDS_FIELD = "NFLPlayerIDs"
SOURCES_BY_CANONICAL_PLAYER_ID_FIELD = "SourcesByCanonicalPlayerID"
LEGACY_SOURCES_BY_CANONICAL_PLAYER_ID_FIELD = "SourcesByNFLPlayerID"

LIFECYCLE_CLASSES = {
    "dynamic",
    "seasonal-finalizable",
    "immutable-history",
    "snapshot",
}
PARTITION_KEYS = {"none", "season", "season-week", "snapshot-time"}
FINALIZATION_POLICIES = {
    "never",
    "freeze-prior-seasons",
    "freeze-existing-partitions",
    "append-only-snapshots",
}
REPAIR_POLICIES = {"normal", "explicit-force"}
REFRESH_POLICIES = {"periodic", "discover-new-partitions", "current-season", "snapshot"}
RETENTION_POLICIES = {"latest-with-git-history", "permanent-by-season", "permanent-snapshots"}
SOURCE_MODES = {"fixed", "season-partitioned"}
SOURCE_FORMATS = {"csv", "json"}
AVAILABILITY_POLICIES = {"required", "current-season-may-be-unavailable"}

IDENTITY_ID_KEYS = (
    "GSIS", "Sleeper", "Tank01", "ESPN", "PFR", "PFF", "OTC", "NFL", "NFLCom", "ESB",
    "FantasyPros", "MFL", "Sportradar", "Yahoo", "Fleaflicker", "CBS", "CFBRef",
    "Rotowire", "KTC", "FantasyData",
)

_LEGACY_CANONICAL_KEY_RENAMES = {
    LEGACY_CANONICAL_PLAYER_ID_FIELD: CANONICAL_PLAYER_ID_FIELD,
    LEGACY_CANONICAL_PLAYER_IDS_FIELD: CANONICAL_PLAYER_IDS_FIELD,
    LEGACY_SOURCES_BY_CANONICAL_PLAYER_ID_FIELD: SOURCES_BY_CANONICAL_PLAYER_ID_FIELD,
    "__NFLPlayerID": "__CanonicalPlayerID",
    "ExistingNFLPlayerIDIsStable": "ExistingCanonicalPlayerIDIsStable",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE", "NAN"}:
        return None
    return text


def normalize_legacy_canonical_player_fields(value: Any) -> Any:
    """Normalize the pre-migration canonical player field names without changing ID values."""
    if isinstance(value, list):
        return [normalize_legacy_canonical_player_fields(item) for item in value]
    if not isinstance(value, dict):
        return value

    normalized: dict[str, Any] = {}
    for key, item in value.items():
        target_key = _LEGACY_CANONICAL_KEY_RENAMES.get(key, key)
        normalized_item = normalize_legacy_canonical_player_fields(item)
        if target_key in normalized and normalized[target_key] != normalized_item:
            raise ValueError(
                f"Conflicting legacy/current canonical player fields for '{target_key}'"
            )
        normalized[target_key] = normalized_item

    if normalized.get("InternalKey") == LEGACY_CANONICAL_PLAYER_ID_FIELD:
        normalized["InternalKey"] = CANONICAL_PLAYER_ID_FIELD
    return normalized


def canonical_player_id(value: dict[str, Any]) -> str | None:
    normalized = normalize_legacy_canonical_player_fields(value)
    return clean(normalized.get(CANONICAL_PLAYER_ID_FIELD))


def as_int(value: Any) -> int | None:
    text = clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    text = clean(value)
    if text is None:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_internal_id(seed: str) -> str:
    return "NFLP-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    # utf-8-sig accepts normal UTF-8 and transparently strips a legacy BOM.
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_if_changed(path: Path, payload: Any) -> bool:
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == rendered:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return True


def iter_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def inspect_csv(path: Path, required_columns: Iterable[str], minimum_rows: int) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"CSV is empty: {path}") from exc
        missing = sorted(set(required_columns) - set(header))
        if missing:
            raise ValueError(f"CSV {path} is missing required columns: {', '.join(missing)}")
        row_count = sum(1 for _ in reader)
    if row_count < minimum_rows:
        raise ValueError(f"CSV {path} has implausibly few rows ({row_count}); expected at least {minimum_rows}.")
    return header, row_count


def inspect_json(path: Path, required_fields: Iterable[str], minimum_rows: int) -> tuple[list[str], int]:
    payload = load_json(path)
    if isinstance(payload, dict):
        records = [value for value in payload.values() if isinstance(value, dict)]
    elif isinstance(payload, list):
        records = [value for value in payload if isinstance(value, dict)]
    else:
        raise ValueError(f"JSON dataset must be an object-of-records or array-of-records: {path}")
    row_count = len(records)
    if row_count < minimum_rows:
        raise ValueError(f"JSON {path} has implausibly few records ({row_count}); expected at least {minimum_rows}.")
    available_fields = sorted({key for record in records for key in record})
    missing = sorted(set(required_fields) - set(available_fields))
    if missing:
        raise ValueError(f"JSON {path} is missing required record fields: {', '.join(missing)}")
    return available_fields, row_count


def inspect_source_file(
    path: Path,
    source_format: str,
    required_fields: Iterable[str],
    minimum_rows: int,
) -> tuple[list[str], int]:
    if source_format == "csv":
        return inspect_csv(path, required_fields, minimum_rows)
    if source_format == "json":
        return inspect_json(path, required_fields, minimum_rows)
    raise ValueError(f"Unsupported source format: {source_format}")


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Lolindhir-fantasy-app-nfl-source-data/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def _validate_lifecycle(value: dict[str, Any], dataset_id: str) -> dict[str, str]:
    lifecycle = value.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise ValueError(f"Dataset {dataset_id} requires lifecycle metadata in registry schema v2+")

    lifecycle_class = str(lifecycle.get("class") or "").strip()
    partition_key = str(lifecycle.get("partitionKey") or "").strip()
    finalization = str(lifecycle.get("finalization") or "").strip()
    repair = str(lifecycle.get("repairPolicy") or "").strip()

    if lifecycle_class not in LIFECYCLE_CLASSES:
        raise ValueError(f"Dataset {dataset_id} has unsupported lifecycle class: {lifecycle_class}")
    if partition_key not in PARTITION_KEYS:
        raise ValueError(f"Dataset {dataset_id} has unsupported partitionKey: {partition_key}")
    if finalization not in FINALIZATION_POLICIES:
        raise ValueError(f"Dataset {dataset_id} has unsupported finalization policy: {finalization}")
    if repair not in REPAIR_POLICIES:
        raise ValueError(f"Dataset {dataset_id} has unsupported repairPolicy: {repair}")

    if lifecycle_class == "dynamic":
        expected = ("none", "never", "normal")
        if (partition_key, finalization, repair) != expected:
            raise ValueError(
                f"Dynamic dataset {dataset_id} must use partitionKey=none, "
                "finalization=never and repairPolicy=normal"
            )
    elif lifecycle_class == "immutable-history":
        if partition_key != "season" or finalization != "freeze-prior-seasons" or repair != "explicit-force":
            raise ValueError(
                f"Immutable-history dataset {dataset_id} must use partitionKey=season, "
                "finalization=freeze-prior-seasons and repairPolicy=explicit-force"
            )
    elif lifecycle_class == "seasonal-finalizable":
        if partition_key not in {"season", "season-week"} or finalization != "freeze-prior-seasons" or repair != "explicit-force":
            raise ValueError(
                f"Seasonal-finalizable dataset {dataset_id} must use partitionKey=season or season-week, "
                "finalization=freeze-prior-seasons and repairPolicy=explicit-force"
            )
    elif lifecycle_class == "snapshot":
        if partition_key != "snapshot-time" or finalization != "append-only-snapshots" or repair != "explicit-force":
            raise ValueError(
                f"Snapshot dataset {dataset_id} must use partitionKey=snapshot-time, "
                "finalization=append-only-snapshots and repairPolicy=explicit-force"
            )

    return {
        "class": lifecycle_class,
        "partitionKey": partition_key,
        "finalization": finalization,
        "repairPolicy": repair,
    }


def _validate_refresh_retention(value: dict[str, Any], dataset_id: str, lifecycle_class: str) -> None:
    refresh = str(value.get("refreshPolicy") or "").strip()
    retention = str(value.get("retentionPolicy") or "").strip()
    if refresh not in REFRESH_POLICIES:
        raise ValueError(f"Dataset {dataset_id} has unsupported refreshPolicy: {refresh}")
    if retention not in RETENTION_POLICIES:
        raise ValueError(f"Dataset {dataset_id} has unsupported retentionPolicy: {retention}")
    expected = {
        "dynamic": ("periodic", "latest-with-git-history"),
        "immutable-history": ("discover-new-partitions", "permanent-by-season"),
        "seasonal-finalizable": ("current-season", "permanent-by-season"),
        "snapshot": ("snapshot", "permanent-snapshots"),
    }[lifecycle_class]
    if (refresh, retention) != expected:
        raise ValueError(
            f"Dataset {dataset_id} lifecycle {lifecycle_class} requires "
            f"refreshPolicy={expected[0]} and retentionPolicy={expected[1]}"
        )


def _validate_source_contract(value: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    source_mode = str(value.get("sourceMode") or "fixed").strip()
    source_format = str(value.get("sourceFormat") or "csv").strip()
    availability_policy = str(value.get("availabilityPolicy") or "required").strip()
    materialize = value.get("materialize", True)

    if source_mode not in SOURCE_MODES:
        raise ValueError(f"Dataset {dataset_id} has unsupported sourceMode: {source_mode}")
    if source_format not in SOURCE_FORMATS:
        raise ValueError(f"Dataset {dataset_id} has unsupported sourceFormat: {source_format}")
    if availability_policy not in AVAILABILITY_POLICIES:
        raise ValueError(
            f"Dataset {dataset_id} has unsupported availabilityPolicy: {availability_policy}"
        )
    if not isinstance(materialize, bool):
        raise ValueError(f"Dataset {dataset_id} materialize must be boolean")

    source_url = str(value.get("sourceUrl") or "").strip()
    raw_path = str(value.get("rawPath") or "").strip()
    metadata_path = str(value.get("metadataPath") or "").strip()
    if not source_url or not raw_path or not metadata_path:
        raise ValueError(f"Dataset {dataset_id} requires sourceUrl, rawPath and metadataPath")

    has_season_tokens = tuple("{season}" in item for item in (source_url, raw_path, metadata_path))
    if source_mode == "season-partitioned" and not all(has_season_tokens):
        raise ValueError(
            f"Season-partitioned dataset {dataset_id} requires {{season}} in sourceUrl, rawPath and metadataPath"
        )
    if source_mode == "fixed" and any(has_season_tokens):
        raise ValueError(f"Fixed dataset {dataset_id} must not contain {{season}} path/url templates")

    return {
        "sourceMode": source_mode,
        "sourceFormat": source_format,
        "availabilityPolicy": availability_policy,
        "materialize": materialize,
    }


@dataclass(frozen=True)
class Dataset:
    id: str
    provider: str
    upstream: str
    source_url: str
    raw_path: Path
    metadata_path: Path
    required_columns: tuple[str, ...]
    minimum_rows: int
    kind: str
    refresh_policy: str
    retention_policy: str
    license: str
    attribution: str
    lifecycle_class: str = "dynamic"
    partition_key: str = "none"
    finalization_policy: str = "never"
    repair_policy: str = "normal"
    source_mode: str = "fixed"
    source_format: str = "csv"
    availability_policy: str = "required"
    materialize: bool = True

    @property
    def is_season_partitioned(self) -> bool:
        return self.source_mode == "season-partitioned"

    def _resolve_template(self, value: str, season: int | None) -> str:
        if not self.is_season_partitioned:
            return value
        if season is None:
            raise ValueError(f"Dataset {self.id} requires an explicit season partition")
        return value.format(season=season)

    def source_url_for(self, season: int | None = None) -> str:
        return self._resolve_template(self.source_url, season)

    def raw_path_for(self, season: int | None = None) -> Path:
        return Path(self._resolve_template(str(self.raw_path), season))

    def metadata_path_for(self, season: int | None = None) -> Path:
        return Path(self._resolve_template(str(self.metadata_path), season))

    @staticmethod
    def from_dict(source_root: Path, value: dict[str, Any], *, registry_schema_version: int) -> "Dataset":
        if registry_schema_version >= 2:
            lifecycle = _validate_lifecycle(value, value["id"])
            _validate_refresh_retention(value, value["id"], lifecycle["class"])
        else:
            # Compatibility for existing test fixtures written against registry v1.
            lifecycle = {
                "class": "dynamic",
                "partitionKey": "none",
                "finalization": "never",
                "repairPolicy": "normal",
            }
        if registry_schema_version >= REGISTRY_SCHEMA_VERSION:
            source_contract = _validate_source_contract(value, value["id"])
        else:
            source_contract = {
                "sourceMode": "fixed",
                "sourceFormat": str(value.get("sourceFormat") or "csv"),
                "availabilityPolicy": "required",
                "materialize": True,
            }
        return Dataset(
            id=value["id"], provider=value["provider"], upstream=value["upstream"],
            source_url=value["sourceUrl"], raw_path=source_root / value["rawPath"],
            metadata_path=source_root / value["metadataPath"],
            required_columns=tuple(value["requiredColumns"]), minimum_rows=int(value["minimumRows"]),
            kind=value["kind"], refresh_policy=value["refreshPolicy"],
            retention_policy=value["retentionPolicy"], license=value["license"], attribution=value["attribution"],
            lifecycle_class=lifecycle["class"], partition_key=lifecycle["partitionKey"],
            finalization_policy=lifecycle["finalization"], repair_policy=lifecycle["repairPolicy"],
            source_mode=source_contract["sourceMode"], source_format=source_contract["sourceFormat"],
            availability_policy=source_contract["availabilityPolicy"], materialize=source_contract["materialize"],
        )


def load_registry_manifest(repo_root: Path) -> dict[str, Any]:
    source_root = repo_root / "source-data"
    registry = load_json(source_root / "registry.json")
    if not isinstance(registry, dict):
        raise ValueError("source-data/registry.json is missing or invalid")
    version = as_int(registry.get("schemaVersion"))
    if version not in SUPPORTED_REGISTRY_SCHEMA_VERSIONS:
        raise ValueError("source-data/registry.json has an unsupported schemaVersion")
    datasets = registry.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("source-data/registry.json must contain at least one active dataset")

    seen: set[str] = set()
    for value in datasets:
        dataset_id = clean(value.get("id")) if isinstance(value, dict) else None
        if not dataset_id:
            raise ValueError("Every active registry dataset requires a non-empty id")
        if dataset_id in seen:
            raise ValueError(f"Duplicate registry dataset id: {dataset_id}")
        seen.add(dataset_id)
        Dataset.from_dict(source_root, value, registry_schema_version=version)

    planned = registry.get("plannedDatasets", [])
    if planned is None:
        planned = []
    if not isinstance(planned, list):
        raise ValueError("plannedDatasets must be a list")
    for value in planned:
        dataset_id = clean(value.get("id")) if isinstance(value, dict) else None
        if not dataset_id:
            raise ValueError("Every planned registry dataset requires a non-empty id")
        if dataset_id in seen:
            raise ValueError(f"Duplicate active/planned registry dataset id: {dataset_id}")
        seen.add(dataset_id)
        if version >= 2:
            lifecycle = _validate_lifecycle(value, dataset_id)
            _validate_refresh_retention(value, dataset_id, lifecycle["class"])
    return registry


def load_registry(repo_root: Path) -> list[Dataset]:
    source_root = repo_root / "source-data"
    registry = load_registry_manifest(repo_root)
    version = int(registry["schemaVersion"])
    return [
        Dataset.from_dict(source_root, value, registry_schema_version=version)
        for value in registry["datasets"]
    ]


def planned_dataset_ids(repo_root: Path) -> list[str]:
    registry = load_registry_manifest(repo_root)
    return [value["id"] for value in registry.get("plannedDatasets", [])]


def current_source_season(repo_root: Path) -> int:
    league = load_json(repo_root / "public/data/League.json", {}) or {}
    season = as_int(league.get("Season"))
    if season is not None:
        return season
    metadata = load_json(repo_root / "public/data/Metadata.json", {}) or {}
    season = as_int(metadata.get("LeagueYear"))
    if season is not None:
        return season
    return datetime.now(timezone.utc).year


def _availability_metadata(dataset: Dataset, season: int | None, status: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "registrySchemaVersion": REGISTRY_SCHEMA_VERSION,
        "dataset": dataset.id,
        "provider": dataset.provider,
        "upstream": dataset.upstream,
        "sourceUrl": dataset.source_url_for(season),
        "sourceFormat": dataset.source_format,
        "sourceMode": dataset.source_mode,
        "availabilityStatus": status,
        "kind": dataset.kind,
        "refreshPolicy": dataset.refresh_policy,
        "retentionPolicy": dataset.retention_policy,
        "lifecycle": {
            "class": dataset.lifecycle_class,
            "partitionKey": dataset.partition_key,
            "finalization": dataset.finalization_policy,
            "repairPolicy": dataset.repair_policy,
        },
        "license": dataset.license,
        "attribution": dataset.attribution,
    }
    if season is not None:
        payload["partition"] = {"season": season}
    return payload


def sync_dataset(
    dataset: Dataset,
    *,
    force: bool = False,
    offline: bool = False,
    season: int | None = None,
    current_season: int | None = None,
) -> dict[str, Any]:
    raw_path = dataset.raw_path_for(season)
    metadata_path = dataset.metadata_path_for(season)
    source_url = dataset.source_url_for(season)

    if dataset.is_season_partitioned and current_season is None:
        raise ValueError(f"Dataset {dataset.id} requires current_season for partition lifecycle checks")

    if (
        dataset.is_season_partitioned
        and season is not None
        and current_season is not None
        and season < current_season
        and raw_path.exists()
        and not force
    ):
        columns, row_count = inspect_source_file(
            raw_path, dataset.source_format, dataset.required_columns, dataset.minimum_rows
        )
        return {
            "dataset": dataset.id,
            "status": "frozen-existing",
            "season": season,
            "rowCount": row_count,
            "contentHash": sha256_file(raw_path),
            "columns": columns,
            "metadata": load_json(metadata_path, {}) or {},
        }

    if offline:
        if not raw_path.exists():
            metadata = load_json(metadata_path, {}) or {}
            if metadata.get("availabilityStatus") == "not-yet-available":
                return {
                    "dataset": dataset.id,
                    "status": "not-yet-available",
                    "season": season,
                    "rowCount": None,
                    "contentHash": None,
                    "columns": [],
                    "metadata": metadata,
                }
            raise FileNotFoundError(f"Offline mode requires existing raw data: {raw_path}")
        columns, row_count = inspect_source_file(
            raw_path, dataset.source_format, dataset.required_columns, dataset.minimum_rows
        )
        return {
            "dataset": dataset.id,
            "status": "offline-existing",
            "season": season,
            "rowCount": row_count,
            "contentHash": sha256_file(raw_path),
            "columns": columns,
            "metadata": load_json(metadata_path, {}) or {},
        }

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nfl-source-") as temp_dir:
        candidate = Path(temp_dir) / f"candidate.{dataset.source_format}"
        try:
            download(source_url, candidate)
        except urllib.error.HTTPError as exc:
            can_be_not_yet_available = (
                exc.code == 404
                and dataset.availability_policy == "current-season-may-be-unavailable"
                and dataset.is_season_partitioned
                and season == current_season
                and not raw_path.exists()
            )
            if not can_be_not_yet_available:
                raise
            metadata = _availability_metadata(dataset, season, "not-yet-available")
            write_json_if_changed(metadata_path, metadata)
            return {
                "dataset": dataset.id,
                "status": "not-yet-available",
                "season": season,
                "rowCount": None,
                "contentHash": None,
                "columns": [],
                "metadata": metadata,
            }

        columns, row_count = inspect_source_file(
            candidate, dataset.source_format, dataset.required_columns, dataset.minimum_rows
        )
        candidate_hash = sha256_file(candidate)
        old_hash = sha256_file(raw_path) if raw_path.exists() else None
        changed = force or old_hash != candidate_hash
        if changed:
            shutil.copyfile(candidate, raw_path)

        metadata = _availability_metadata(dataset, season, "available")
        metadata.update({
            "retrievedAtUtc": utc_now(),
            "contentHashSha256": candidate_hash,
            "rowCount": row_count,
            "columns": columns,
        })
        if changed or not metadata_path.exists():
            write_json_if_changed(metadata_path, metadata)
        else:
            metadata = load_json(metadata_path, metadata)
        return {
            "dataset": dataset.id,
            "status": "updated" if changed else "unchanged",
            "season": season,
            "rowCount": row_count,
            "contentHash": candidate_hash,
            "columns": columns,
            "metadata": metadata,
        }
