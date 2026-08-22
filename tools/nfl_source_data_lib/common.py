from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = 1
IDENTITY_ID_KEYS = (
    "GSIS", "Sleeper", "Tank01", "ESPN", "PFR", "PFF", "OTC", "NFL", "NFLCom", "ESB",
    "FantasyPros", "MFL", "Sportradar", "Yahoo", "Fleaflicker", "CBS", "CFBRef",
    "Rotowire", "KTC", "FantasyData",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE", "NAN"}:
        return None
    return text


def as_int(value: Any) -> int | None:
    text = clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
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


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Lolindhir-fantasy-app-nfl-source-data/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


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

    @staticmethod
    def from_dict(source_root: Path, value: dict[str, Any]) -> "Dataset":
        return Dataset(
            id=value["id"], provider=value["provider"], upstream=value["upstream"],
            source_url=value["sourceUrl"], raw_path=source_root / value["rawPath"],
            metadata_path=source_root / value["metadataPath"],
            required_columns=tuple(value["requiredColumns"]), minimum_rows=int(value["minimumRows"]),
            kind=value["kind"], refresh_policy=value["refreshPolicy"],
            retention_policy=value["retentionPolicy"], license=value["license"], attribution=value["attribution"],
        )


def load_registry(repo_root: Path) -> list[Dataset]:
    source_root = repo_root / "source-data"
    registry = load_json(source_root / "registry.json")
    if not registry or registry.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("source-data/registry.json is missing or has an unsupported schemaVersion")
    return [Dataset.from_dict(source_root, value) for value in registry["datasets"]]


def sync_dataset(dataset: Dataset, *, force: bool = False, offline: bool = False) -> dict[str, Any]:
    if offline:
        if not dataset.raw_path.exists():
            raise FileNotFoundError(f"Offline mode requires existing raw data: {dataset.raw_path}")
        header, row_count = inspect_csv(dataset.raw_path, dataset.required_columns, dataset.minimum_rows)
        return {"dataset": dataset.id, "status": "offline-existing", "rowCount": row_count,
                "contentHash": sha256_file(dataset.raw_path), "columns": header,
                "metadata": load_json(dataset.metadata_path, {}) or {}}

    dataset.raw_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nfl-source-") as temp_dir:
        candidate = Path(temp_dir) / "candidate.csv"
        download(dataset.source_url, candidate)
        header, row_count = inspect_csv(candidate, dataset.required_columns, dataset.minimum_rows)
        candidate_hash = sha256_file(candidate)
        old_hash = sha256_file(dataset.raw_path) if dataset.raw_path.exists() else None
        changed = force or old_hash != candidate_hash
        if changed:
            shutil.copyfile(candidate, dataset.raw_path)

        metadata = {
            "schemaVersion": SCHEMA_VERSION, "dataset": dataset.id, "provider": dataset.provider,
            "upstream": dataset.upstream, "sourceUrl": dataset.source_url, "sourceFormat": "csv",
            "retrievedAtUtc": utc_now(), "contentHashSha256": candidate_hash, "rowCount": row_count,
            "columns": header, "kind": dataset.kind, "refreshPolicy": dataset.refresh_policy,
            "retentionPolicy": dataset.retention_policy, "license": dataset.license,
            "attribution": dataset.attribution,
        }
        if changed or not dataset.metadata_path.exists():
            write_json_if_changed(dataset.metadata_path, metadata)
        else:
            metadata = load_json(dataset.metadata_path, metadata)
        return {"dataset": dataset.id, "status": "updated" if changed else "unchanged",
                "rowCount": row_count, "contentHash": candidate_hash, "columns": header, "metadata": metadata}
