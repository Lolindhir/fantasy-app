"""Schema and Golden Set helpers for the podcast extraction pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from podcast_pipeline_types import (
    GoldenProfiles,
    PipelineDataError,
    PipelineReport,
    SCHEMA_FILES,
    load_json,
    safe_relative_path,
)


def format_json_path(path: Iterable[Any]) -> str:
    values = list(path)
    return ".".join(str(value) for value in values) if values else "<root>"


def schema_path(repo_root: Path, key: str) -> Path:
    return repo_root / "fantasy-management/_ai/schemas" / SCHEMA_FILES[key]


def validate_schema(data: Any, schema_file: Path, report: PipelineReport, label_path: Path | str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        report.error(label_path, "Python package 'jsonschema' is required for schema validation.")
        return
    try:
        schema = load_json(schema_file)
    except PipelineDataError as exc:
        report.error(label_path, str(exc))
        return
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # pragma: no cover
        report.error(schema_file, f"invalid JSON schema: {exc}")
        return
    for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path)):
        report.error(label_path, f"schema violation at {format_json_path(error.path)}: {error.message}")


def load_optional_json(path: Path, report: PipelineReport) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = load_json(path)
    except PipelineDataError as exc:
        report.error(path, str(exc))
        return None
    if not isinstance(data, dict):
        report.error(path, "JSON root must be an object.")
        return None
    return data


def check_identity(data: dict[str, Any], episode_id: str, source_id: str, path: Path, report: PipelineReport) -> None:
    if data.get("episode_id") != episode_id:
        report.error(path, f"episode_id must equal {episode_id!r}.")
    if data.get("source_id") != source_id:
        report.error(path, f"source_id must equal {source_id!r}.")


def check_active_profiles(values: Any, profiles: GoldenProfiles, path: Path, report: PipelineReport) -> None:
    if not isinstance(values, list):
        return
    for value in values:
        if value not in profiles.active_ids:
            report.error(path, f"Golden Set profile is not active: {value!r}.")


def contiguous_orders(items: list[dict[str, Any]], path: Path, report: PipelineReport, label: str) -> None:
    orders = [item.get("order") for item in items if isinstance(item, dict)]
    if len(orders) != len(set(orders)):
        report.error(path, f"{label} order values must be unique.")
    expected = list(range(1, len(items) + 1))
    if sorted(value for value in orders if isinstance(value, int)) != expected:
        report.error(path, f"{label} order values must be contiguous from 1.")


def phase_requires(work_status: dict[str, Any], gate: str) -> bool:
    gates = work_status.get("gates")
    return bool(isinstance(gates, dict) and gates.get(gate))


def load_golden_profiles(repo_root: Path, report: PipelineReport) -> GoldenProfiles:
    base = repo_root / "fantasy-management/_ai/golden-set"
    list_path = base / "profile-list.json"
    profile_list = load_optional_json(list_path, report)
    if profile_list is None:
        report.error(list_path, "Active Golden Set profile list is required.")
        return GoldenProfiles(frozenset(), {})
    validate_schema(profile_list, schema_path(repo_root, "golden_profile_list"), report, list_path)
    descriptors = profile_list.get("profiles") if isinstance(profile_list.get("profiles"), list) else []
    if profile_list.get("profile_count") != len(descriptors):
        report.error(list_path, f"profile_count={profile_list.get('profile_count')!r} does not match {len(descriptors)} descriptors.")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    active: set[str] = set()
    dimensions: dict[str, frozenset[str]] = {}
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        profile_id = str(descriptor.get("profile_id") or "")
        raw_path = descriptor.get("path")
        if profile_id in seen_ids:
            report.error(list_path, f"duplicate profile_id: {profile_id!r}")
        seen_ids.add(profile_id)
        if raw_path in seen_paths:
            report.error(list_path, f"duplicate profile path: {raw_path!r}")
        seen_paths.add(str(raw_path))
        try:
            path = safe_relative_path(base, raw_path, "profiles")
        except PipelineDataError as exc:
            report.error(list_path, str(exc))
            continue
        profile = load_optional_json(path, report)
        if profile is None:
            report.error(path, "Registered Golden Set profile file is missing.")
            continue
        validate_schema(profile, schema_path(repo_root, "golden_profile"), report, path)
        if profile.get("profile_id") != profile_id:
            report.error(path, f"profile_id does not match profile-list descriptor {profile_id!r}.")
        if profile.get("version") != descriptor.get("version"):
            report.error(path, "profile version does not match profile-list descriptor.")
        dimensions[profile_id] = frozenset(
            str(item.get("id"))
            for item in profile.get("dimensions", [])
            if isinstance(item, dict) and item.get("id")
        )
        if descriptor.get("status") == "active":
            active.add(profile_id)
    return GoldenProfiles(frozenset(active), dimensions)
