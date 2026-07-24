#!/usr/bin/env python3
"""Load inline or split Fantasy Management podcast package data.

The public entry points remain ``takes.json`` and ``mentions.json``.  Small
packages may keep their payload inline.  Large packages may use those files as
small manifests whose ordered parts live below ``takes/`` or ``mentions/``.
The loaders return the same aggregate shape to validators and future readers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

CATEGORIES = ["players", "teams", "positions", "nfl", "fantasy", "other"]


class DuplicateKeyError(ValueError):
    """Raised when JSON contains a duplicate object key."""


class PackageDataError(ValueError):
    """Raised when a package manifest or part set is invalid."""


def object_pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_file(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=object_pairs_no_duplicates)
    except FileNotFoundError as exc:
        raise PackageDataError(f"missing JSON file: {path.as_posix()}") from exc
    except (DuplicateKeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PackageDataError(f"invalid JSON in {path.as_posix()}: {exc}") from exc


def canonical_json_text(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def is_canonical_pretty_json(path: Path, data: Any) -> bool:
    return path.read_text(encoding="utf-8") == canonical_json_text(data)


def _identity(data: dict[str, Any]) -> tuple[Any, Any, Any]:
    return data.get("episode_id"), data.get("source_id"), data.get("source_name")


def _safe_part_path(package_dir: Path, raw_path: Any, expected_dir: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise PackageDataError("part path must be a non-empty string")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PackageDataError(f"part path must stay inside the package: {raw_path!r}")
    if not relative.parts or relative.parts[0] != expected_dir:
        raise PackageDataError(
            f"part path must live below {expected_dir}/: {raw_path!r}"
        )
    return package_dir / relative


@dataclass(frozen=True)
class LoadedDocumentSet:
    mode: str
    manifest_path: Path
    manifest: dict[str, Any]
    part_documents: tuple[tuple[Path, dict[str, Any]], ...]
    aggregate: dict[str, Any]

    @property
    def json_documents(self) -> tuple[tuple[Path, dict[str, Any]], ...]:
        return ((self.manifest_path, self.manifest),) + self.part_documents


def load_takes(package_dir: Path) -> LoadedDocumentSet:
    manifest_path = package_dir / "takes.json"
    raw = load_json_file(manifest_path)
    if not isinstance(raw, dict):
        raise PackageDataError("takes.json root must be an object")

    if isinstance(raw.get("take_categories"), dict):
        return LoadedDocumentSet(
            mode="inline",
            manifest_path=manifest_path,
            manifest=raw,
            part_documents=(),
            aggregate=raw,
        )

    if raw.get("storage_mode") != "split":
        raise PackageDataError(
            "takes.json must contain take_categories or storage_mode='split'"
        )

    parts = raw.get("parts")
    if not isinstance(parts, list) or not parts:
        raise PackageDataError("split takes.json must contain a non-empty parts array")

    identity = _identity(raw)
    seen_paths: set[str] = set()
    seen_categories: set[str] = set()
    categories: dict[str, list[Any]] = {category: [] for category in CATEGORIES}
    documents: list[tuple[Path, dict[str, Any]]] = []

    for position, descriptor in enumerate(parts):
        if not isinstance(descriptor, dict):
            raise PackageDataError(f"takes.json parts[{position}] must be an object")
        raw_path = descriptor.get("path")
        if raw_path in seen_paths:
            raise PackageDataError(f"duplicate takes part path: {raw_path!r}")
        seen_paths.add(str(raw_path))
        path = _safe_part_path(package_dir, raw_path, "takes")
        document = load_json_file(path)
        if not isinstance(document, dict):
            raise PackageDataError(f"takes part root must be an object: {raw_path}")
        if _identity(document) != identity:
            raise PackageDataError(f"takes part identity mismatch: {raw_path}")

        category = descriptor.get("category")
        if category not in CATEGORIES:
            raise PackageDataError(
                f"takes.json parts[{position}].category is invalid: {category!r}"
            )
        seen_categories.add(str(category))
        if document.get("category") != category:
            raise PackageDataError(f"takes part category mismatch: {raw_path}")

        entries = document.get("takes")
        if not isinstance(entries, list):
            raise PackageDataError(f"takes part must contain a takes array: {raw_path}")
        declared = descriptor.get("count")
        if declared != len(entries):
            raise PackageDataError(
                f"takes part count mismatch for {raw_path}: declared {declared!r}, actual {len(entries)}"
            )
        categories[str(category)].extend(entries)
        documents.append((path, document))

    missing_categories = [category for category in CATEGORIES if category not in seen_categories]
    if missing_categories:
        raise PackageDataError(f"split takes.json is missing category part(s): {', '.join(missing_categories)}")

    declared_counts = raw.get("take_counts")
    if not isinstance(declared_counts, dict):
        raise PackageDataError("split takes.json must contain take_counts")
    for category in CATEGORIES:
        actual = len(categories[category])
        declared = declared_counts.get(category)
        if declared != actual:
            raise PackageDataError(
                f"takes.json take_counts.{category}={declared!r} does not match {actual}"
            )

    aggregate = {
        "episode_id": raw.get("episode_id"),
        "source_id": raw.get("source_id"),
        "source_name": raw.get("source_name"),
        "take_categories": categories,
    }
    return LoadedDocumentSet(
        mode="split",
        manifest_path=manifest_path,
        manifest=raw,
        part_documents=tuple(documents),
        aggregate=aggregate,
    )


def load_mentions(package_dir: Path) -> LoadedDocumentSet:
    manifest_path = package_dir / "mentions.json"
    raw = load_json_file(manifest_path)
    if not isinstance(raw, dict):
        raise PackageDataError("mentions.json root must be an object")

    if isinstance(raw.get("mentions"), list):
        return LoadedDocumentSet(
            mode="inline",
            manifest_path=manifest_path,
            manifest=raw,
            part_documents=(),
            aggregate=raw,
        )

    if raw.get("storage_mode") != "split":
        raise PackageDataError(
            "mentions.json must contain mentions or storage_mode='split'"
        )

    parts = raw.get("parts")
    if not isinstance(parts, list) or not parts:
        raise PackageDataError("split mentions.json must contain a non-empty parts array")

    identity = _identity(raw)
    seen_paths: set[str] = set()
    all_mentions: list[Any] = []
    documents: list[tuple[Path, dict[str, Any]]] = []

    for position, descriptor in enumerate(parts, start=1):
        if not isinstance(descriptor, dict):
            raise PackageDataError(f"mentions.json parts[{position - 1}] must be an object")
        raw_path = descriptor.get("path")
        if raw_path in seen_paths:
            raise PackageDataError(f"duplicate mentions part path: {raw_path!r}")
        seen_paths.add(str(raw_path))
        path = _safe_part_path(package_dir, raw_path, "mentions")
        document = load_json_file(path)
        if not isinstance(document, dict):
            raise PackageDataError(f"mentions part root must be an object: {raw_path}")
        if _identity(document) != identity:
            raise PackageDataError(f"mentions part identity mismatch: {raw_path}")
        if document.get("part_number") != position:
            raise PackageDataError(
                f"mentions part numbering must be contiguous from 1: {raw_path}"
            )
        entries = document.get("mentions")
        if not isinstance(entries, list):
            raise PackageDataError(f"mentions part must contain a mentions array: {raw_path}")
        declared = descriptor.get("count")
        if declared != len(entries):
            raise PackageDataError(
                f"mentions part count mismatch for {raw_path}: declared {declared!r}, actual {len(entries)}"
            )
        all_mentions.extend(entries)
        documents.append((path, document))

    declared_total = raw.get("mention_count")
    if declared_total != len(all_mentions):
        raise PackageDataError(
            f"mentions.json mention_count={declared_total!r} does not match {len(all_mentions)}"
        )

    aggregate = {
        "episode_id": raw.get("episode_id"),
        "source_id": raw.get("source_id"),
        "source_name": raw.get("source_name"),
        "mentions": all_mentions,
    }
    return LoadedDocumentSet(
        mode="split",
        manifest_path=manifest_path,
        manifest=raw,
        part_documents=tuple(documents),
        aggregate=aggregate,
    )


def flatten_take_ids(takes: dict[str, Any]) -> Iterable[str]:
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        return ()
    return (
        str(entry.get("id"))
        for category in CATEGORIES
        for entry in categories.get(category, [])
        if isinstance(entry, dict) and entry.get("id")
    )
