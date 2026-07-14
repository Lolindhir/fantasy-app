#!/usr/bin/env python3
"""Validate cross-file entity coverage for podcast episode packages.

The complete technical mention register lives in mentions.json. episode.md is
checked only for substantive ranking, news and evaluation subjects.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MANDATORY_TYPES = {"ranking_subject", "substantive_take", "news_subject"}
FALSE_POSITIVE = "false_positive"
CATEGORIES = ["players", "teams", "positions", "nfl", "fantasy", "other"]


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

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"[{prefix}] {issue.package}: {issue.message}")
        if not self.errors and not self.warnings:
            print("OK: no mention coverage errors or warnings.")
        else:
            print(f"Summary: {len(self.errors)} error(s), {len(self.warnings)} warning(s).")

    def to_json(self) -> dict[str, Any]:
        return {
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "summary": {"errors": len(self.errors), "warnings": len(self.warnings)},
        }


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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
    except (DuplicateKeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.error(package, f"Invalid JSON in {path.as_posix()}: {exc}")
    return None


def validate_pretty_json(path: Path, data: Any, report: Report, package: str) -> None:
    expected = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        report.error(
            package,
            f"{path.name} is not canonical pretty JSON "
            "(UTF-8, two-space indentation, one property/item per line, trailing newline).",
        )


def format_json_path(path: Iterable[Any]) -> str:
    values = list(path)
    return ".".join(str(value) for value in values) if values else "<root>"


def validate_against_schema(
    data: Any,
    schema_path: Path,
    report: Report,
    package: str,
    label: str,
) -> None:
    schema = load_json(schema_path, report, package)
    if schema is None:
        return
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        report.error(package, "Python package 'jsonschema' is required.")
        return
    for error in sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda item: list(item.path),
    ):
        report.error(
            package,
            f"{label} schema violation at {format_json_path(error.path)}: {error.message}",
        )


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = text.replace("’", "'").replace("`", "'")
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def collect_takes(takes: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    player_ids: set[str] = set()
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        return by_id, player_ids
    for category in CATEGORIES:
        entries = categories.get(category)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            take_id = entry.get("id")
            if isinstance(take_id, str) and take_id:
                by_id[take_id] = entry
                if category == "players":
                    player_ids.add(take_id)
    return by_id, player_ids


def mention_names(mention: dict[str, Any]) -> list[str]:
    names: list[str] = []
    resolution = mention.get("entity_resolution")
    if (
        isinstance(resolution, dict)
        and resolution.get("status") == "confirmed"
        and isinstance(mention.get("entity"), str)
    ):
        names.append(mention["entity"])
    raw = mention.get("raw_entity_mentions")
    if isinstance(raw, list):
        names.extend(value for value in raw if isinstance(value, str))
    return names


def identities_for_mention(mention: dict[str, Any]) -> set[str]:
    return {normalize_text(value) for value in mention_names(mention) if normalize_text(value)}


def identities_for_take(take: dict[str, Any]) -> set[str]:
    return {
        normalize_text(take.get(key))
        for key in ("entity", "raw_entity_mention")
        if normalize_text(take.get(key))
    }


def valid_links(value: Any, takes: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item in takes]


def mandatory(mention_types: set[str]) -> bool:
    return bool(mention_types & MANDATORY_TYPES)


def mention_uncovered(mention: dict[str, Any], takes: dict[str, dict[str, Any]]) -> bool:
    types = set(mention.get("mention_types") or [])
    if FALSE_POSITIVE in types:
        return False
    coverage = mention.get("coverage")
    if not isinstance(coverage, dict):
        return True
    subjects = valid_links(coverage.get("subject_take_ids"), takes)
    if mandatory(types):
        return coverage.get("episode_md") is not True or not subjects
    if coverage.get("episode_md") is True:
        return False
    note = coverage.get("note")
    return not isinstance(note, str) or not note.strip()


def calculate_counts(
    mentions: list[dict[str, Any]],
    takes: dict[str, dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "total": len(mentions),
        "resolved": 0,
        "ambiguous": 0,
        "unresolved": 0,
        "ranking_subjects": 0,
        "substantive_subjects": 0,
        "context_only": 0,
        "with_take_links": 0,
        "uncovered": 0,
    }
    for mention in mentions:
        resolution = mention.get("entity_resolution")
        status = resolution.get("status") if isinstance(resolution, dict) else None
        if status == "confirmed":
            counts["resolved"] += 1
        elif status == "ambiguous":
            counts["ambiguous"] += 1
        elif status == "unresolved":
            counts["unresolved"] += 1

        types = set(mention.get("mention_types") or [])
        if "ranking_subject" in types:
            counts["ranking_subjects"] += 1
        if types & {"substantive_take", "news_subject"}:
            counts["substantive_subjects"] += 1
        if FALSE_POSITIVE not in types and not mandatory(types):
            counts["context_only"] += 1

        coverage = mention.get("coverage")
        if isinstance(coverage, dict):
            if valid_links(coverage.get("subject_take_ids"), takes) or valid_links(
                coverage.get("context_take_ids"), takes
            ):
                counts["with_take_links"] += 1
        if mention_uncovered(mention, takes):
            counts["uncovered"] += 1
    return counts


def validate_package(
    package_dir: Path,
    root: Path,
    index_schema_path: Path,
    mentions_schema_path: Path,
    report: Report,
    warnings_for_legacy: bool,
) -> None:
    package_label = rel(package_dir, root)
    index_path = package_dir / "index.json"
    takes_path = package_dir / "takes.json"
    mentions_path = package_dir / "mentions.json"
    episode_path = package_dir / "episode.md"

    index = load_json(index_path, report, package_label)
    takes = load_json(takes_path, report, package_label)
    if not isinstance(index, dict) or not isinstance(takes, dict):
        return

    validate_against_schema(index, index_schema_path, report, package_label, "index.json")

    try:
        version = int(index.get("package_schema_version", 1))
    except (TypeError, ValueError):
        report.error(package_label, "Invalid package_schema_version.")
        return

    if version < 2 and not mentions_path.exists():
        if warnings_for_legacy:
            report.warn(package_label, "Legacy package has no schema-v2 mention audit.")
        return
    if not mentions_path.exists():
        report.error(package_label, "Schema-version-2 package is missing mentions.json.")
        return

    mentions_data = load_json(mentions_path, report, package_label)
    if not isinstance(mentions_data, dict):
        return

    validate_against_schema(
        mentions_data,
        mentions_schema_path,
        report,
        package_label,
        "mentions.json",
    )

    if version >= 2:
        for path, data in (
            (index_path, index),
            (takes_path, takes),
            (mentions_path, mentions_data),
        ):
            validate_pretty_json(path, data, report, package_label)

    for key in ("episode_id", "source_id", "source_name"):
        if mentions_data.get(key) != index.get(key):
            report.error(package_label, f"mentions.json {key} does not match index.json.")
        if mentions_data.get(key) != takes.get(key):
            report.error(package_label, f"mentions.json {key} does not match takes.json.")

    files = index.get("files")
    if not isinstance(files, dict) or files.get("mentions") != "mentions.json":
        report.error(package_label, "index.json must declare files.mentions='mentions.json'.")

    if not episode_path.exists():
        report.error(package_label, "Missing episode.md.")
        return
    episode_text = normalize_text(episode_path.read_text(encoding="utf-8"))

    raw_mentions = mentions_data.get("mentions")
    if not isinstance(raw_mentions, list):
        report.error(package_label, "mentions.json mentions must be an array.")
        return
    mentions = [entry for entry in raw_mentions if isinstance(entry, dict)]

    take_by_id, player_take_ids = collect_takes(takes)
    covered_player_ids: set[str] = set()
    seen_ids: set[str] = set()

    for position, mention in enumerate(mentions):
        mention_id = mention.get("id")
        if not isinstance(mention_id, str) or not mention_id:
            report.error(package_label, f"mentions[{position}] is missing id.")
            mention_id = f"mentions[{position}]"
        elif mention_id in seen_ids:
            report.error(package_label, f"Duplicate mention id: {mention_id}")
        seen_ids.add(str(mention_id))

        types = set(mention.get("mention_types") or [])
        if FALSE_POSITIVE in types and len(types) > 1:
            report.error(package_label, f"{mention_id} combines false_positive with normal types.")

        coverage = mention.get("coverage")
        if not isinstance(coverage, dict):
            report.error(package_label, f"{mention_id} is missing coverage.")
            continue

        for label in ("subject_take_ids", "context_take_ids"):
            value = coverage.get(label)
            if not isinstance(value, list):
                report.error(package_label, f"{mention_id} {label} must be an array.")
                continue
            for take_id in value:
                if take_id not in take_by_id:
                    report.error(package_label, f"{mention_id} references unknown take {take_id}.")

        subject_ids = valid_links(coverage.get("subject_take_ids"), take_by_id)
        context_ids = valid_links(coverage.get("context_take_ids"), take_by_id)

        if FALSE_POSITIVE in types:
            if subject_ids or context_ids:
                report.error(package_label, f"{mention_id} false positive must not link to takes.")
            continue

        if mandatory(types):
            if not subject_ids:
                report.error(package_label, f"{mention_id} requires a valid subject take.")
            if coverage.get("episode_md") is not True:
                report.error(package_label, f"{mention_id} requires reader-facing coverage.")
            if not any(
                normalize_text(name) and normalize_text(name) in episode_text
                for name in mention_names(mention)
            ):
                report.error(package_label, f"{mention_id} subject name is absent from episode.md.")

        elif coverage.get("episode_md") is False:
            note = coverage.get("note")
            if not isinstance(note, str) or not note.strip():
                report.error(package_label, f"{mention_id} audit-only omission needs coverage.note.")

        if mention.get("entity_type") == "player":
            for take_id in subject_ids:
                if take_id not in player_take_ids:
                    report.error(package_label, f"{mention_id} links a non-player subject take.")
                    continue
                if not (identities_for_mention(mention) & identities_for_take(take_by_id[take_id])):
                    report.error(package_label, f"{mention_id} does not match subject take {take_id}.")
                    continue
                covered_player_ids.add(take_id)

    for take_id in sorted(player_take_ids - covered_player_ids):
        report.error(package_label, f"Player take {take_id} has no matching subject mention.")

    calculated = calculate_counts(mentions, take_by_id)
    declared = index.get("mention_counts")
    if not isinstance(declared, dict):
        report.error(package_label, "index.json is missing mention_counts.")
    else:
        for key, value in calculated.items():
            if declared.get(key) != value:
                report.error(
                    package_label,
                    f"mention_counts.{key}={declared.get(key)!r}, calculated={value}.",
                )

    audit = index.get("coverage_audit")
    if not isinstance(audit, dict):
        report.error(package_label, "index.json is missing coverage_audit.")
    else:
        if version >= 2 and audit.get("status") != "completed":
            report.error(package_label, "coverage_audit.status must be 'completed'.")
        if audit.get("method") != "second_pass_entity_mention_sweep":
            report.error(package_label, "coverage_audit.method is invalid.")
        if audit.get("uncovered_mentions") != calculated["uncovered"]:
            report.error(package_label, "coverage_audit.uncovered_mentions is inconsistent.")

    if version >= 2 and calculated["uncovered"] != 0:
        report.error(package_label, f"Package has {calculated['uncovered']} uncovered mention(s).")


def discover_episode_packages(root: Path) -> list[Path]:
    return [
        path.parent
        for path in sorted(
            (root / "fantasy-management/sources/podcasts").glob("*/episodes/*/*/index.json")
        )
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate podcast entity mention coverage.")
    parser.add_argument("packages", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--index-schema", default=None)
    parser.add_argument("--mentions-schema", default=None)
    parser.add_argument("--no-legacy-warnings", action="store_true")
    parser.add_argument("--warnings-as-errors", action="store_true")
    parser.add_argument("--json-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    index_schema = (
        Path(args.index_schema).resolve()
        if args.index_schema
        else root / "fantasy-management/_ai/schemas/episode-index.schema.json"
    )
    mentions_schema = (
        Path(args.mentions_schema).resolve()
        if args.mentions_schema
        else root / "fantasy-management/_ai/schemas/episode-mentions.schema.json"
    )
    packages = discover_episode_packages(root) if args.all else [Path(item).resolve() for item in args.packages]
    if not packages:
        print("No episode packages selected.", file=sys.stderr)
        return 2
    report = Report()
    for package in packages:
        if not package.exists():
            report.error(package, "Package directory does not exist.")
            continue
        validate_package(
            package,
            root,
            index_schema,
            mentions_schema,
            report,
            not args.no_legacy_warnings,
        )
    if args.json_report:
        print(json.dumps(report.to_json(), indent=2, ensure_ascii=False))
    else:
        report.print_text()
    return 1 if report.errors or (args.warnings_as_errors and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
