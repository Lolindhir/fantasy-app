"""Shared helpers for podcast episode package validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from podcast_package_io import PackageDataError, load_json_file

@dataclass
class Issue:
    severity: str
    package: str
    message: str


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def error(self, package: Path | str, message: str) -> None:
        self.errors.append(Issue("error", str(package), message))

    def warn(self, package: Path | str, message: str) -> None:
        self.warnings.append(Issue("warning", str(package), message))

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            print(f"[{'ERROR' if issue.severity == 'error' else 'WARN'}] {issue.package}: {issue.message}")
        if not self.errors and not self.warnings:
            print("OK: no validation errors or warnings.")
        else:
            print(f"Summary: {len(self.errors)} error(s), {len(self.warnings)} warning(s).")

    def to_json(self) -> dict[str, Any]:
        return {
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "summary": {"errors": len(self.errors), "warnings": len(self.warnings)},
        }


@dataclass
class RegistryIndex:
    canonical_names: set[str] = field(default_factory=set)
    alias_by_source: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    def has_alias_mapping(self, alias: str, source_id: str, canonical: str | None) -> bool:
        values = self.alias_by_source.get((normalize(alias), source_id), set())
        return canonical in values if canonical else bool(values)

    def has_canonical(self, canonical: str | None) -> bool:
        return bool(canonical and canonical in self.canonical_names)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize(value: Any) -> str:
    return str(value or "").strip().casefold()


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def format_json_path(path: Iterable[Any]) -> str:
    values = list(path)
    return ".".join(str(value) for value in values) if values else "<root>"


def validate_against_schema(data: Any, schema_path: Path, report: Report, package: str, label: str) -> None:
    try:
        schema = load_json_file(schema_path)
    except PackageDataError as exc:
        report.error(package, str(exc))
        return
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        report.error(package, "Python package 'jsonschema' is required for schema validation.")
        return
    for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path)):
        report.error(package, f"{label} schema violation at {format_json_path(error.path)}: {error.message}")


def load_and_validate_registry(root: Path, report: Report, skip_registry: bool) -> RegistryIndex:
    result = RegistryIndex()
    if skip_registry:
        return result
    path = root / "fantasy-management/_ai/entity-resolution/player_identity_registry.json"
    if not path.exists():
        report.warn("registry", f"Registry not found: {rel(path, root)}")
        return result
    try:
        registry = load_json_file(path)
    except PackageDataError as exc:
        report.error("registry", str(exc))
        return result
    entries = registry.get("entries") if isinstance(registry, dict) else None
    if not isinstance(entries, list):
        report.error("registry", "Registry must contain an entries array.")
        return result
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or is_blank(entry.get("canonical_name")):
            report.error("registry", f"entries[{index}] missing canonical_name.")
            continue
        canonical = str(entry["canonical_name"])
        result.canonical_names.add(canonical)
        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list):
            report.error("registry", f"{canonical}: aliases must be an array.")
            continue
        for alias_entry in aliases:
            if not isinstance(alias_entry, dict) or is_blank(alias_entry.get("alias")):
                report.error("registry", f"{canonical}: malformed alias entry.")
                continue
            alias = str(alias_entry["alias"])
            source_ids = alias_entry.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                report.error("registry", f"{canonical}/{alias}: source_ids must be non-empty.")
                continue
            for source_id in source_ids:
                key = (normalize(alias), str(source_id))
                if key in seen:
                    report.error("registry", f"Duplicate alias/source mapping: {alias!r}/{source_id!r}.")
                seen.add(key)
                result.alias_by_source.setdefault(key, set()).add(canonical)
            for evidence in alias_entry.get("evidence_paths", []):
                if not (root / str(evidence)).exists():
                    report.error("registry", f"Evidence path does not exist for {canonical}/{alias}: {evidence}")
    return result
