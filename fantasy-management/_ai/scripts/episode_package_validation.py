"""Semantic validation for one podcast episode package."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from podcast_package_io import CATEGORIES, PackageDataError, load_json_file, load_takes
from episode_package_validation_common import (
    RegistryIndex, Report, is_blank, rel, validate_against_schema,
)

FORBIDDEN_PACKAGE_FILES = {"entity_resolution.json"}
EPISODE_MD_FORBIDDEN_TOKENS = [
    "global_index_update", "package_path", "raw_manifest",
    "entity_resolution.json", "Mighty Giants recommendation",
]
CONFIRMED_METHODS = {"registry", "external_verification", "context_inference", "manual_confirmation"}

def validate_raw(package_dir: Path, index: dict[str, Any], report: Report, label: str) -> None:
    files = index.get("files") if isinstance(index.get("files"), dict) else {}
    raw_status = index.get("raw_status")
    if raw_status == "split_raw_referenced":
        if files.get("raw_manifest") != "raw/manifest.md":
            report.error(label, "split raw must declare files.raw_manifest='raw/manifest.md'.")
        manifest = package_dir / "raw/manifest.md"
        if not manifest.exists():
            report.error(label, "Missing raw/manifest.md for split raw transcript.")
            return
        text = manifest.read_text(encoding="utf-8")
        mentioned = set(re.findall(r"`([^`]*part\d{2}[^`]*\.md)`", text))
        actual = {path.name for path in (package_dir / "raw").glob("part*.md")}
        for name in mentioned:
            if not (package_dir / "raw" / name).exists():
                report.error(label, f"raw/manifest.md references missing raw part: {name}")
        for name in sorted(actual - mentioned):
            report.warn(label, f"Raw part exists but is not listed in raw/manifest.md: {name}")
        numbers = sorted(int(match.group(1)) for name in actual if (match := re.search(r"part(\d{2})", name)))
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            report.error(label, f"Raw part numbering is not contiguous from 1: {numbers}")
    else:
        source = files.get("raw_source", "raw/source.md")
        if not isinstance(source, str) or not (package_dir / source).exists():
            report.error(label, f"Missing raw source: {source}")


def validate_episode_markdown(path: Path, report: Report, label: str) -> None:
    if not path.exists():
        report.error(label, "Missing required file: episode.md")
        return
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        report.error(label, "episode.md is empty.")
    elif not text.lstrip().startswith("# "):
        report.warn(label, "episode.md should start with a level-1 heading.")
    for token in EPISODE_MD_FORBIDDEN_TOKENS:
        if token in text:
            report.error(label, f"episode.md contains forbidden internal token: {token}")


def validate_player_take(take: dict[str, Any], source_id: str, registry: RegistryIndex, report: Report, label: str, skip_registry: bool) -> None:
    take_id = take.get("id", "<unknown>")
    raw = take.get("raw_entity_mention")
    entity = take.get("entity")
    resolution = take.get("entity_resolution")
    if is_blank(raw):
        report.error(label, f"Player take {take_id} missing raw_entity_mention.")
    if not isinstance(take.get("tags"), list):
        report.error(label, f"Player take {take_id} missing tags array.")
    if not isinstance(resolution, dict):
        report.error(label, f"Player take {take_id} missing entity_resolution object.")
        return
    status, method = resolution.get("status"), resolution.get("method")
    if status == "confirmed" and is_blank(entity):
        report.error(label, f"Player take {take_id} is confirmed but entity is empty/null.")
    if status in {"ambiguous", "unresolved"} and not is_blank(entity):
        report.error(label, f"Player take {take_id} is {status} but entity is not null.")
    if status == "unresolved" and method != "none":
        report.error(label, f"Player take {take_id} is unresolved but method is not 'none'.")
    if status == "confirmed" and method not in CONFIRMED_METHODS:
        report.error(label, f"Player take {take_id} is confirmed with invalid method {method!r}.")
    if skip_registry or method != "registry":
        return
    raw_str, entity_str = str(raw or ""), str(entity) if entity is not None else None
    if not registry.has_alias_mapping(raw_str, source_id, entity_str) and not (
        raw_str == entity_str and registry.has_canonical(entity_str)
    ):
        report.warn(label, f"Player take {take_id} uses registry method without matching registry entry.")


def validate_takes(takes: dict[str, Any], index: dict[str, Any], registry: RegistryIndex, report: Report, label: str, skip_registry: bool) -> None:
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        report.error(label, "Aggregated take_categories must be an object.")
        return
    seen: set[str] = set()
    episode_id = str(takes.get("episode_id") or "")
    source_id = str(takes.get("source_id") or "")
    counts = index.get("take_counts") if isinstance(index.get("take_counts"), dict) else {}
    for category in CATEGORIES:
        entries = categories.get(category)
        if not isinstance(entries, list):
            report.error(label, f"take_categories.{category} must be an array.")
            continue
        if counts.get(category) != len(entries):
            report.error(label, f"take_counts.{category}={counts.get(category)!r} does not match {len(entries)}.")
        for position, take in enumerate(entries):
            if not isinstance(take, dict):
                report.error(label, f"take_categories.{category}[{position}] must be an object.")
                continue
            take_id = take.get("id")
            if not isinstance(take_id, str) or not take_id:
                report.error(label, f"take_categories.{category}[{position}] is missing id.")
            elif take_id in seen:
                report.error(label, f"Duplicate take id: {take_id}")
            else:
                seen.add(take_id)
                if episode_id and not take_id.startswith(episode_id):
                    report.warn(label, f"Take id does not start with episode_id: {take_id}")
            if take.get("category") != category:
                report.error(label, f"Take {take_id or position} is in {category} but category={take.get('category')!r}.")
            if is_blank(take.get("podcast_take")):
                report.error(label, f"Take {take_id or position} has empty podcast_take.")
            evidence = take.get("evidence")
            if not isinstance(evidence, dict) or not evidence.get("timestamp_start"):
                report.warn(label, f"Take {take_id or position} has no timestamp_start evidence.")
            if take.get("type") == take.get("entity"):
                report.warn(label, f"Take {take_id or position} may have swapped type/entity fields.")
            if category == "players":
                validate_player_take(take, source_id, registry, report, label, skip_registry)


def validate_episode_package(package_dir: Path, root: Path, schema_path: Path, registry: RegistryIndex, report: Report, skip_schema: bool, skip_registry: bool) -> None:
    label = rel(package_dir, root)
    index_path = package_dir / "index.json"
    if not index_path.exists():
        report.error(label, "Missing required file: index.json")
        return
    try:
        index = load_json_file(index_path)
        loaded = load_takes(package_dir)
    except PackageDataError as exc:
        report.error(label, str(exc))
        return
    if not isinstance(index, dict):
        report.error(label, "index.json root must be an object.")
        return
    for forbidden in FORBIDDEN_PACKAGE_FILES:
        if (package_dir / forbidden).exists():
            report.error(label, f"Forbidden companion file exists: {forbidden}")
    if not skip_schema:
        validate_against_schema(loaded.manifest, schema_path, report, label, "takes.json")
        part_schema = root / "fantasy-management/_ai/schemas/episode-takes-part.schema.json"
        for path, document in loaded.part_documents:
            validate_against_schema(document, part_schema, report, label, path.relative_to(package_dir).as_posix())
    takes = loaded.aggregate
    for key in ("episode_id", "source_id", "source_name"):
        if index.get(key) != takes.get(key):
            report.error(label, f"index.json {key} does not match aggregated takes.")
    expected_path = rel(package_dir, root).rstrip("/") + "/"
    if str(index.get("package_path", "")).lstrip("./") != expected_path:
        report.error(label, f"index.json package_path does not match actual path {expected_path!r}.")
    files = index.get("files")
    if not isinstance(files, dict) or files.get("takes") != "takes.json" or files.get("episode_summary") != "episode.md":
        report.error(label, "index.json must declare files.takes='takes.json' and files.episode_summary='episode.md'.")
    else:
        for key, value in files.items():
            if isinstance(value, str) and not (package_dir / value).exists():
                report.error(label, f"index.json files.{key} path does not exist: {value}")
    validate_raw(package_dir, index, report, label)
    validate_episode_markdown(package_dir / "episode.md", report, label)
    validate_takes(takes, index, registry, report, label, skip_registry)
