#!/usr/bin/env python3
"""Validate Fantasy Management podcast episode packages.

This validator intentionally checks technical quality and consistency only.
It does not decide whether a podcast take is factually or strategically correct.

Default usage:

  python fantasy-management/_ai/scripts/validate_episode_package.py \
    fantasy-management/sources/podcasts/stoned-lack/episodes/2026/sl_0569

Validate every local podcast package:

  python fantasy-management/_ai/scripts/validate_episode_package.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

CATEGORIES = ["players", "teams", "positions", "nfl", "fantasy", "other"]
FORBIDDEN_PACKAGE_FILES = {"entity_resolution.json"}
EPISODE_MD_FORBIDDEN_TOKENS = [
    "global_index_update",
    "package_path",
    "raw_manifest",
    "entity_resolution.json",
    "Mighty Giants recommendation",
]
REGISTRY_METHODS = {"registry"}
CONFIRMED_METHODS = {
    "registry",
    "external_verification",
    "context_inference",
    "manual_confirmation",
}


class DuplicateKeyError(ValueError):
    pass


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

    def has_errors(self) -> bool:
        return bool(self.errors)

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"[{prefix}] {issue.package}: {issue.message}")

        if not self.errors and not self.warnings:
            print("OK: no validation errors or warnings.")
        else:
            print(
                f"Summary: {len(self.errors)} error(s), "
                f"{len(self.warnings)} warning(s)."
            )

    def to_json(self) -> dict[str, Any]:
        return {
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
        }


@dataclass
class RegistryIndex:
    canonical_names: set[str] = field(default_factory=set)
    alias_by_source: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    def has_alias_mapping(self, alias: str, source_id: str, canonical: str | None) -> bool:
        canonicals = self.alias_by_source.get((normalize(alias), source_id), set())
        return canonical in canonicals if canonical else bool(canonicals)

    def has_canonical(self, canonical: str | None) -> bool:
        return bool(canonical and canonical in self.canonical_names)


# ---------- Generic helpers ----------


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


def object_pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, report: Report, package: Path | str) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=object_pairs_no_duplicates)
    except FileNotFoundError:
        report.error(package, f"Missing JSON file: {path.as_posix()}")
    except DuplicateKeyError as exc:
        report.error(package, f"Duplicate key in {path.as_posix()}: {exc}")
    except json.JSONDecodeError as exc:
        report.error(package, f"Invalid JSON in {path.as_posix()}: {exc}")
    except UnicodeDecodeError as exc:
        report.error(package, f"File is not valid UTF-8: {path.as_posix()}: {exc}")
    return None


def ensure_file(path: Path, report: Report, package: Path | str) -> bool:
    if not path.is_file():
        report.error(package, f"Missing required file: {path.as_posix()}")
        return False
    return True


def ensure_dir(path: Path, report: Report, package: Path | str) -> bool:
    if not path.is_dir():
        report.error(package, f"Missing required directory: {path.as_posix()}")
        return False
    return True


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def format_json_path(path: Iterable[Any]) -> str:
    parts = list(path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


# ---------- Dynamic schema validation ----------


def validate_against_schema(
    data: Any,
    schema_path: Path,
    report: Report,
    package: Path | str,
) -> None:
    schema = load_json(schema_path, report, package)
    if schema is None:
        return

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        report.error(
            package,
            "Python package 'jsonschema' is required for schema validation. "
            "Install it or run with --skip-schema.",
        )
        return

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    for error in errors:
        report.error(
            package,
            f"Schema violation at {format_json_path(error.path)}: {error.message}",
        )


# ---------- Registry validation ----------


def load_and_validate_registry(
    root: Path,
    report: Report,
    skip_registry: bool,
) -> RegistryIndex:
    registry_index = RegistryIndex()
    if skip_registry:
        return registry_index

    registry_path = root / "fantasy-management/_ai/entity-resolution/player_identity_registry.json"
    if not registry_path.exists():
        report.warn("registry", f"Registry not found: {rel(registry_path, root)}")
        return registry_index

    registry = load_json(registry_path, report, "registry")
    if not isinstance(registry, dict):
        report.error("registry", "Registry root must be a JSON object.")
        return registry_index

    seen_alias_source: set[tuple[str, str]] = set()
    entries = registry.get("entries")
    if not isinstance(entries, list):
        report.error("registry", "Registry must contain an entries array.")
        return registry_index

    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            report.error("registry", f"entries[{entry_index}] must be an object.")
            continue

        canonical = entry.get("canonical_name")
        if is_blank(canonical):
            report.error("registry", f"entries[{entry_index}] missing canonical_name.")
            continue
        canonical = str(canonical)
        registry_index.canonical_names.add(canonical)

        aliases = entry.get("aliases")
        if not isinstance(aliases, list):
            report.error("registry", f"{canonical}: aliases must be an array.")
            continue

        for alias_index, alias_entry in enumerate(aliases):
            if not isinstance(alias_entry, dict):
                report.error("registry", f"{canonical}.aliases[{alias_index}] must be an object.")
                continue

            alias = alias_entry.get("alias")
            if is_blank(alias):
                report.error("registry", f"{canonical}.aliases[{alias_index}] missing alias.")
                continue

            source_ids = alias_entry.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                report.error("registry", f"{canonical}/{alias}: source_ids must be a non-empty array.")
                continue

            for source_id in source_ids:
                key = (normalize(alias), str(source_id))
                if key in seen_alias_source:
                    report.error(
                        "registry",
                        f"Duplicate alias/source mapping: alias={alias!r}, source_id={source_id!r}.",
                    )
                seen_alias_source.add(key)
                registry_index.alias_by_source.setdefault(key, set()).add(canonical)

            evidence_paths = alias_entry.get("evidence_paths", [])
            if not isinstance(evidence_paths, list):
                report.error("registry", f"{canonical}/{alias}: evidence_paths must be an array.")
                continue

            for evidence in evidence_paths:
                evidence_path = root / str(evidence)
                if not evidence_path.exists():
                    report.error(
                        "registry",
                        f"Evidence path does not exist for {canonical}/{alias}: {evidence}",
                    )

    return registry_index


# ---------- Episode package checks ----------


def validate_episode_package(
    package_dir: Path,
    root: Path,
    schema_path: Path,
    registry: RegistryIndex,
    report: Report,
    skip_schema: bool,
    skip_registry: bool,
) -> None:
    package_label = rel(package_dir, root)

    index_path = package_dir / "index.json"
    takes_path = package_dir / "takes.json"
    episode_path = package_dir / "episode.md"
    raw_dir = package_dir / "raw"

    ensure_file(index_path, report, package_label)
    ensure_file(takes_path, report, package_label)
    ensure_file(episode_path, report, package_label)
    ensure_dir(raw_dir, report, package_label)

    for forbidden_file in FORBIDDEN_PACKAGE_FILES:
        forbidden_path = package_dir / forbidden_file
        if forbidden_path.exists():
            report.error(package_label, f"Forbidden companion file exists: {forbidden_file}")

    index = load_json(index_path, report, package_label)
    takes = load_json(takes_path, report, package_label)
    if not isinstance(index, dict) or not isinstance(takes, dict):
        return

    if not skip_schema:
        validate_against_schema(takes, schema_path, report, package_label)

    validate_index_consistency(package_dir, root, index, takes, report, package_label)
    validate_raw_manifest(package_dir, index, report, package_label)
    validate_episode_markdown(episode_path, report, package_label)
    validate_takes(takes, index, registry, report, package_label, skip_registry)



def validate_index_consistency(
    package_dir: Path,
    root: Path,
    index: dict[str, Any],
    takes: dict[str, Any],
    report: Report,
    package_label: str,
) -> None:
    for key in ["episode_id", "source_id", "source_name"]:
        if index.get(key) != takes.get(key):
            report.error(
                package_label,
                f"index.json {key}={index.get(key)!r} does not match takes.json {key}={takes.get(key)!r}.",
            )

    actual_package_path = rel(package_dir, root).rstrip("/") + "/"
    declared_package_path = str(index.get("package_path", "")).strip().lstrip("./")
    if declared_package_path and declared_package_path != actual_package_path:
        report.error(
            package_label,
            f"index.json package_path={declared_package_path!r} does not match actual path {actual_package_path!r}.",
        )

    files = index.get("files")
    if not isinstance(files, dict):
        report.error(package_label, "index.json files must be an object.")
        return

    expected_files = {
        "takes": "takes.json",
        "episode_summary": "episode.md",
    }
    for file_key, expected_path in expected_files.items():
        declared = files.get(file_key)
        if declared != expected_path:
            report.error(
                package_label,
                f"index.json files.{file_key} should be {expected_path!r}, got {declared!r}.",
            )

    for file_key, declared in files.items():
        if not isinstance(declared, str):
            report.error(package_label, f"index.json files.{file_key} must be a string path.")
            continue
        if declared.endswith("entity_resolution.json"):
            report.error(package_label, "index.json still references entity_resolution.json.")
        if not (package_dir / declared).exists():
            report.error(package_label, f"index.json files.{file_key} path does not exist: {declared}")

    counts = index.get("take_counts")
    categories = takes.get("take_categories")
    if not isinstance(counts, dict):
        report.error(package_label, "index.json take_counts must be an object.")
        return
    if not isinstance(categories, dict):
        report.error(package_label, "takes.json take_categories must be an object.")
        return

    for category in CATEGORIES:
        actual_count = len(as_list(categories.get(category)))
        declared_count = counts.get(category)
        if declared_count != actual_count:
            report.error(
                package_label,
                f"take_counts.{category}={declared_count!r} does not match actual count {actual_count}.",
            )



def validate_raw_manifest(
    package_dir: Path,
    index: dict[str, Any],
    report: Report,
    package_label: str,
) -> None:
    raw_status = index.get("raw_status")
    files = index.get("files") if isinstance(index.get("files"), dict) else {}
    raw_manifest_value = files.get("raw_manifest")

    if raw_status == "split_raw_referenced" and raw_manifest_value != "raw/manifest.md":
        report.error(
            package_label,
            "raw_status is split_raw_referenced but files.raw_manifest is not raw/manifest.md.",
        )

    manifest_path = package_dir / "raw" / "manifest.md"
    if raw_status == "split_raw_referenced" or raw_manifest_value:
        if not manifest_path.exists():
            report.error(package_label, "Missing raw/manifest.md for split raw transcript.")
            return

    if not manifest_path.exists():
        return

    manifest_text = manifest_path.read_text(encoding="utf-8")
    mentioned_parts = set(re.findall(r"`([^`]*part\d{2}[^`]*\.md)`", manifest_text))
    raw_parts = {path.name for path in (package_dir / "raw").glob("part*.md")}

    if raw_parts and not mentioned_parts:
        report.warn(package_label, "raw/manifest.md does not list any raw part files in backticks.")

    for mentioned in mentioned_parts:
        if not (package_dir / "raw" / mentioned).exists():
            report.error(package_label, f"raw/manifest.md references missing raw part: {mentioned}")

    unmentioned = raw_parts - mentioned_parts
    for part_name in sorted(unmentioned):
        report.warn(package_label, f"Raw part exists but is not listed in raw/manifest.md: {part_name}")

    part_numbers = sorted(
        int(match.group(1))
        for part_name in raw_parts
        if (match := re.search(r"part(\d{2})", part_name))
    )
    if part_numbers:
        expected = list(range(part_numbers[0], part_numbers[-1] + 1))
        if part_numbers != expected:
            report.error(package_label, f"Raw part numbering is not contiguous: {part_numbers}")



def validate_episode_markdown(episode_path: Path, report: Report, package_label: str) -> None:
    if not episode_path.exists():
        return
    text = episode_path.read_text(encoding="utf-8")
    if not text.strip():
        report.error(package_label, "episode.md is empty.")
        return
    if not text.lstrip().startswith("# "):
        report.warn(package_label, "episode.md should start with a level-1 Markdown heading.")
    for token in EPISODE_MD_FORBIDDEN_TOKENS:
        if token in text:
            report.error(package_label, f"episode.md contains forbidden internal token: {token}")



def validate_takes(
    takes: dict[str, Any],
    index: dict[str, Any],
    registry: RegistryIndex,
    report: Report,
    package_label: str,
    skip_registry: bool,
) -> None:
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        return

    episode_id = takes.get("episode_id")
    source_id = takes.get("source_id")
    seen_ids: set[str] = set()

    for category in CATEGORIES:
        take_list = categories.get(category)
        if not isinstance(take_list, list):
            report.error(package_label, f"take_categories.{category} must be an array.")
            continue

        if category in {"players", "teams", "positions", "fantasy"} and not take_list:
            report.warn(package_label, f"take_categories.{category} is empty; confirm this is intentional.")

        for take_index, take in enumerate(take_list):
            if not isinstance(take, dict):
                report.error(package_label, f"take_categories.{category}[{take_index}] must be an object.")
                continue

            take_id = take.get("id")
            if is_blank(take_id):
                report.error(package_label, f"take_categories.{category}[{take_index}] is missing id.")
            elif take_id in seen_ids:
                report.error(package_label, f"Duplicate take id: {take_id}")
            else:
                seen_ids.add(str(take_id))
                if episode_id and not str(take_id).startswith(str(episode_id)):
                    report.warn(package_label, f"Take id does not start with episode_id: {take_id}")

            if take.get("category") != category:
                report.error(
                    package_label,
                    f"Take {take_id or take_index} is in {category} bucket but category={take.get('category')!r}.",
                )

            if is_blank(take.get("podcast_take")):
                report.warn(package_label, f"Take {take_id or take_index} has empty podcast_take.")

            evidence = take.get("evidence")
            if not isinstance(evidence, dict) or not evidence.get("timestamp_start"):
                report.warn(package_label, f"Take {take_id or take_index} has no timestamp_start evidence.")

            if category == "players":
                validate_player_take(take, source_id, registry, report, package_label, skip_registry)



def validate_player_take(
    take: dict[str, Any],
    source_id: Any,
    registry: RegistryIndex,
    report: Report,
    package_label: str,
    skip_registry: bool,
) -> None:
    take_id = take.get("id", "<unknown>")
    raw = take.get("raw_entity_mention")
    entity = take.get("entity")
    resolution = take.get("entity_resolution")

    if is_blank(raw):
        report.error(package_label, f"Player take {take_id} missing raw_entity_mention.")
    elif isinstance(raw, str) and len(raw.split()) == 1 and raw != entity:
        report.warn(package_label, f"Player take {take_id} has single-token raw_entity_mention: {raw!r}.")

    if not isinstance(resolution, dict):
        report.error(package_label, f"Player take {take_id} missing entity_resolution object.")
        return

    status = resolution.get("status")
    method = resolution.get("method")
    confidence = resolution.get("confidence")

    if status == "confirmed" and is_blank(entity):
        report.error(package_label, f"Player take {take_id} is confirmed but entity is empty/null.")
    if status in {"ambiguous", "unresolved"} and not is_blank(entity):
        report.error(package_label, f"Player take {take_id} is {status} but entity is not null.")
    if status == "unresolved" and method != "none":
        report.error(package_label, f"Player take {take_id} is unresolved but method is not 'none'.")
    if status == "confirmed" and method not in CONFIRMED_METHODS:
        report.error(package_label, f"Player take {take_id} is confirmed with invalid method {method!r}.")
    if confidence == "high" and status != "confirmed":
        report.warn(package_label, f"Player take {take_id} has high confidence but status={status!r}.")

    if isinstance(entity, str) and len(entity.split()) == 1 and status == "confirmed":
        report.warn(package_label, f"Player take {take_id} has single-token confirmed entity: {entity!r}.")

    if raw != entity and method not in {"registry", "external_verification", "manual_confirmation"}:
        report.warn(
            package_label,
            f"Player take {take_id} maps raw_entity_mention to a different entity using method={method!r}.",
        )

    if skip_registry or method not in REGISTRY_METHODS:
        return

    source_id_str = str(source_id or "")
    entity_str = str(entity) if entity is not None else None
    raw_str = str(raw or "")

    if registry.has_alias_mapping(raw_str, source_id_str, entity_str):
        return
    if raw_str == entity_str and registry.has_canonical(entity_str):
        return

    report.warn(
        package_label,
        f"Player take {take_id} uses registry method, but no matching registry alias/canonical mapping was found for raw={raw_str!r}, entity={entity_str!r}, source_id={source_id_str!r}.",
    )


# ---------- Package discovery and CLI ----------


def discover_episode_packages(root: Path) -> list[Path]:
    index_paths = sorted(
        (root / "fantasy-management/sources/podcasts").glob("*/episodes/*/*/index.json")
    )
    return [path.parent for path in index_paths]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Fantasy Management podcast episode packages.")
    parser.add_argument("packages", nargs="*", help="Episode package directories to validate.")
    parser.add_argument("--all", action="store_true", help="Validate all podcast episode packages.")
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to script location.")
    parser.add_argument("--schema", default=None, help="Override episode takes schema path.")
    parser.add_argument("--skip-schema", action="store_true", help="Skip JSON Schema validation.")
    parser.add_argument("--skip-registry", action="store_true", help="Skip central player identity registry checks.")
    parser.add_argument("--warnings-as-errors", action="store_true", help="Exit non-zero when warnings are present.")
    parser.add_argument("--json-report", action="store_true", help="Print machine-readable JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    schema_path = Path(args.schema).resolve() if args.schema else root / "fantasy-management/_ai/schemas/episode-takes.schema.json"
    report = Report()

    if args.all:
        package_dirs = discover_episode_packages(root)
    else:
        package_dirs = [Path(package).resolve() for package in args.packages]

    if not package_dirs:
        print("No episode packages selected. Pass one or more package paths, or use --all.", file=sys.stderr)
        return 2

    registry = load_and_validate_registry(root, report, args.skip_registry)

    for package_dir in package_dirs:
        if not package_dir.is_absolute():
            package_dir = (Path.cwd() / package_dir).resolve()
        if not package_dir.exists():
            report.error(package_dir, "Episode package directory does not exist.")
            continue
        validate_episode_package(
            package_dir=package_dir,
            root=root,
            schema_path=schema_path,
            registry=registry,
            report=report,
            skip_schema=args.skip_schema,
            skip_registry=args.skip_registry,
        )

    if args.json_report:
        print(json.dumps(report.to_json(), indent=2, ensure_ascii=False))
    else:
        report.print_text()

    if report.errors or (args.warnings_as_errors and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
