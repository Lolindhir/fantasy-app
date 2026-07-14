#!/usr/bin/env python3
"""Validate cross-file entity mention coverage for podcast episode packages.

The validator checks technical completeness and consistency. It does not decide
whether a podcast statement is factually correct or strategically sound.

Schema-version-2 packages require mentions.json and a completed independent
second-pass coverage audit. The complete technical mention register lives in
mentions.json. episode.md is validated for substantive reader-facing subjects,
not as a duplicate metadata register.
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

MANDATORY_TAKE_TYPES = {
    "ranking_subject",
    "substantive_take",
    "news_subject",
}
FALSE_POSITIVE_TYPE = "false_positive"


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
    except DuplicateKeyError as exc:
        report.error(package, f"Duplicate key in {path.as_posix()}: {exc}")
    except json.JSONDecodeError as exc:
        report.error(package, f"Invalid JSON in {path.as_posix()}: {exc}")
    except UnicodeDecodeError as exc:
        report.error(package, f"File is not valid UTF-8: {path.as_posix()}: {exc}")
    return None


def format_json_path(path: Iterable[Any]) -> str:
    parts = list(path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


def validate_against_schema(
    data: Any,
    schema_path: Path,
    report: Report,
    package: Path | str,
    schema_label: str,
) -> None:
    schema = load_json(schema_path, report, package)
    if schema is None:
        return

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        report.error(
            package,
            "Python package 'jsonschema' is required for coverage schema validation.",
        )
        return

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    for error in errors:
        report.error(
            package,
            f"{schema_label} schema violation at "
            f"{format_json_path(error.path)}: {error.message}",
        )


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = text.replace("’", "'").replace("`", "'")
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_false_positive(mention_types: set[str]) -> bool:
    return FALSE_POSITIVE_TYPE in mention_types


def is_mandatory_subject(mention_types: set[str]) -> bool:
    return bool(mention_types & MANDATORY_TAKE_TYPES)


def mention_search_names(mention: dict[str, Any]) -> list[str]:
    resolution = mention.get("entity_resolution")
    status = resolution.get("status") if isinstance(resolution, dict) else None
    entity = mention.get("entity")
    raw_mentions = mention.get("raw_entity_mentions")

    names: list[str] = []
    if status == "confirmed" and isinstance(entity, str) and entity.strip():
        names.append(entity)
    if isinstance(raw_mentions, list):
        names.extend(
            raw
            for raw in raw_mentions
            if isinstance(raw, str) and raw.strip()
        )
    return names


def identity_values_from_mention(mention: dict[str, Any]) -> set[str]:
    return {
        normalize_text(value)
        for value in mention_search_names(mention)
        if normalize_text(value)
    }


def identity_values_from_take(take: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ["entity", "raw_entity_mention"]:
        normalized = normalize_text(take.get(key))
        if normalized:
            values.add(normalized)
    return values


def mention_matches_player_take(mention: dict[str, Any], take: dict[str, Any]) -> bool:
    return bool(identity_values_from_mention(mention) & identity_values_from_take(take))


def collect_takes(takes: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    take_by_id: dict[str, dict[str, Any]] = {}
    player_take_ids: set[str] = set()
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        return take_by_id, player_take_ids

    for category, entries in categories.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            take_id = entry.get("id")
            if not isinstance(take_id, str) or not take_id:
                continue
            take_by_id[take_id] = entry
            if category == "players":
                player_take_ids.add(take_id)

    return take_by_id, player_take_ids


def valid_links(raw_links: Any, take_by_id: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(raw_links, list):
        return []
    return [take_id for take_id in raw_links if take_id in take_by_id]


def mention_is_uncovered(
    mention: dict[str, Any],
    take_by_id: dict[str, dict[str, Any]],
) -> bool:
    raw_types = mention.get("mention_types")
    mention_types = set(raw_types) if isinstance(raw_types, list) else set()
    if is_false_positive(mention_types):
        return False

    coverage = mention.get("coverage")
    if not isinstance(coverage, dict):
        return True

    subject_ids = valid_links(coverage.get("subject_take_ids"), take_by_id)
    mandatory = is_mandatory_subject(mention_types)

    if mandatory:
        return coverage.get("episode_md") is not True or not subject_ids

    if coverage.get("episode_md") is True:
        return False

    note = coverage.get("note")
    return not isinstance(note, str) or not note.strip()


def calculate_mention_counts(
    mentions: list[dict[str, Any]],
    take_by_id: dict[str, dict[str, Any]],
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

        raw_types = mention.get("mention_types")
        mention_types = set(raw_types) if isinstance(raw_types, list) else set()
        if "ranking_subject" in mention_types:
            counts["ranking_subjects"] += 1
        if mention_types & {"substantive_take", "news_subject"}:
            counts["substantive_subjects"] += 1

        false_positive = is_false_positive(mention_types)
        if not false_positive and not is_mandatory_subject(mention_types):
            counts["context_only"] += 1

        coverage = mention.get("coverage")
        if isinstance(coverage, dict):
            subject_ids = valid_links(coverage.get("subject_take_ids"), take_by_id)
            context_ids = valid_links(coverage.get("context_take_ids"), take_by_id)
            if subject_ids or context_ids:
                counts["with_take_links"] += 1

        if mention_is_uncovered(mention, take_by_id):
            counts["uncovered"] += 1

    return counts


def validate_link_ids(
    mention_id: str,
    link_label: str,
    raw_links: Any,
    take_by_id: dict[str, dict[str, Any]],
    report: Report,
    package_label: str,
) -> list[str]:
    if not isinstance(raw_links, list):
        report.error(package_label, f"Mention {mention_id} {link_label} must be an array.")
        return []

    valid: list[str] = []
    for take_id in raw_links:
        if take_id not in take_by_id:
            report.error(
                package_label,
                f"Mention {mention_id} references unknown {link_label} take id: {take_id}",
            )
            continue
        valid.append(take_id)
    return valid


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
    episode_path = package_dir / "episode.md"
    mentions_path = package_dir / "mentions.json"

    index = load_json(index_path, report, package_label)
    takes = load_json(takes_path, report, package_label)
    if not isinstance(index, dict) or not isinstance(takes, dict):
        return

    validate_against_schema(
        index,
        index_schema_path,
        report,
        package_label,
        "index.json",
    )

    raw_version = index.get("package_schema_version", 1)
    try:
        package_version = int(raw_version)
    except (TypeError, ValueError):
        report.error(package_label, f"Invalid package_schema_version: {raw_version!r}")
        return

    if package_version < 2 and not mentions_path.exists():
        if warnings_for_legacy:
            report.warn(
                package_label,
                "Legacy package schema without mentions.json; full entity coverage is not audited.",
            )
        return

    if package_version >= 2 and not mentions_path.exists():
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

    for key in ["episode_id", "source_id", "source_name"]:
        if mentions_data.get(key) != index.get(key):
            report.error(
                package_label,
                f"mentions.json {key}={mentions_data.get(key)!r} does not match "
                f"index.json {key}={index.get(key)!r}.",
            )
        if mentions_data.get(key) != takes.get(key):
            report.error(
                package_label,
                f"mentions.json {key}={mentions_data.get(key)!r} does not match "
                f"takes.json {key}={takes.get(key)!r}.",
            )

    files = index.get("files")
    if package_version >= 2:
        if not isinstance(files, dict) or files.get("mentions") != "mentions.json":
            report.error(
                package_label,
                "Schema-version-2 index.json must declare files.mentions='mentions.json'.",
            )

    if not episode_path.exists():
        report.error(package_label, "Missing episode.md for mention coverage validation.")
        return

    try:
        episode_text = episode_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        report.error(package_label, f"episode.md is not valid UTF-8: {exc}")
        return
    normalized_episode = normalize_text(episode_text)

    mentions = mentions_data.get("mentions")
    if not isinstance(mentions, list):
        report.error(package_label, "mentions.json mentions must be an array.")
        return

    take_by_id, player_take_ids = collect_takes(takes)
    covered_player_take_ids: set[str] = set()
    seen_mention_ids: set[str] = set()

    for position, mention in enumerate(mentions):
        if not isinstance(mention, dict):
            report.error(package_label, f"mentions[{position}] must be an object.")
            continue

        mention_id = mention.get("id")
        if not isinstance(mention_id, str) or not mention_id:
            report.error(package_label, f"mentions[{position}] is missing id.")
            mention_id = f"mentions[{position}]"
        elif mention_id in seen_mention_ids:
            report.error(package_label, f"Duplicate mention id: {mention_id}")
        else:
            seen_mention_ids.add(mention_id)

        raw_types = mention.get("mention_types")
        mention_types = set(raw_types) if isinstance(raw_types, list) else set()
        false_positive = is_false_positive(mention_types)
        mandatory = is_mandatory_subject(mention_types)

        if false_positive and len(mention_types) > 1:
            report.error(
                package_label,
                f"Mention {mention_id} combines false_positive with normal mention types.",
            )

        coverage = mention.get("coverage")
        if not isinstance(coverage, dict):
            report.error(package_label, f"Mention {mention_id} is missing coverage object.")
            continue

        valid_subject_ids = validate_link_ids(
            mention_id,
            "subject_take_ids",
            coverage.get("subject_take_ids"),
            take_by_id,
            report,
            package_label,
        )
        valid_context_ids = validate_link_ids(
            mention_id,
            "context_take_ids",
            coverage.get("context_take_ids"),
            take_by_id,
            report,
            package_label,
        )

        if mandatory and not valid_subject_ids:
            report.error(
                package_label,
                f"Mention {mention_id} requires a standalone take but has no valid subject take link.",
            )

        if mention.get("entity_type") == "player":
            for take_id in valid_subject_ids:
                take = take_by_id[take_id]
                if take_id not in player_take_ids:
                    report.error(
                        package_label,
                        f"Player mention {mention_id} links non-player take {take_id} as a subject take.",
                    )
                    continue
                if not mention_matches_player_take(mention, take):
                    report.error(
                        package_label,
                        f"Player mention {mention_id} subject take {take_id} does not match the mention identity.",
                    )
                    continue
                covered_player_take_ids.add(take_id)

        if false_positive:
            if coverage.get("episode_md") is True:
                report.warn(
                    package_label,
                    f"False-positive mention {mention_id} is marked as included in episode.md.",
                )
            if valid_subject_ids or valid_context_ids:
                report.error(
                    package_label,
                    f"False-positive mention {mention_id} must not link to takes.",
                )
            continue

        if mandatory:
            if coverage.get("episode_md") is not True:
                report.error(
                    package_label,
                    f"Required subject {mention_id} is not covered in episode.md.",
                )
            else:
                search_names = [
                    normalize_text(name)
                    for name in mention_search_names(mention)
                    if normalize_text(name)
                ]
                if search_names and not any(name in normalized_episode for name in search_names):
                    report.error(
                        package_label,
                        f"Required subject {mention_id} is marked episode_md=true, but neither its "
                        "canonical nor raw name appears in episode.md.",
                    )
        elif coverage.get("episode_md") is False:
            note = coverage.get("note")
            if not isinstance(note, str) or not note.strip():
                report.error(
                    package_label,
                    f"Audit-only context mention {mention_id} must explain the reader-facing omission in coverage.note.",
                )

    for player_take_id in sorted(player_take_ids - covered_player_take_ids):
        report.error(
            package_label,
            f"Player take {player_take_id} is not covered as a matching subject take in mentions.json.",
        )

    calculated_counts = calculate_mention_counts(
        [mention for mention in mentions if isinstance(mention, dict)],
        take_by_id,
    )
    declared_counts = index.get("mention_counts")
    if package_version >= 2 and not isinstance(declared_counts, dict):
        report.error(package_label, "Schema-version-2 index.json is missing mention_counts.")
    elif isinstance(declared_counts, dict):
        for key, actual_value in calculated_counts.items():
            if declared_counts.get(key) != actual_value:
                report.error(
                    package_label,
                    f"mention_counts.{key}={declared_counts.get(key)!r} does not match "
                    f"calculated value {actual_value}.",
                )

    coverage_audit = index.get("coverage_audit")
    if package_version >= 2 and not isinstance(coverage_audit, dict):
        report.error(package_label, "Schema-version-2 index.json is missing coverage_audit.")
    elif isinstance(coverage_audit, dict):
        if package_version >= 2 and coverage_audit.get("status") != "completed":
            report.error(
                package_label,
                "Schema-version-2 coverage_audit.status must be 'completed' before the package is complete.",
            )
        if package_version >= 2 and coverage_audit.get("method") != "second_pass_entity_mention_sweep":
            report.error(
                package_label,
                "Schema-version-2 coverage_audit.method must be 'second_pass_entity_mention_sweep'.",
            )
        if coverage_audit.get("uncovered_mentions") != calculated_counts["uncovered"]:
            report.error(
                package_label,
                "coverage_audit.uncovered_mentions does not match calculated uncovered count.",
            )

    if package_version >= 2 and calculated_counts["uncovered"] != 0:
        report.error(
            package_label,
            f"Schema-version-2 package has {calculated_counts['uncovered']} uncovered mention(s).",
        )


def discover_episode_packages(root: Path) -> list[Path]:
    index_paths = sorted(
        (root / "fantasy-management/sources/podcasts").glob("*/episodes/*/*/index.json")
    )
    return [path.parent for path in index_paths]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate podcast entity mention coverage across episode files."
    )
    parser.add_argument("packages", nargs="*", help="Episode package directories to validate.")
    parser.add_argument("--all", action="store_true", help="Validate all podcast episode packages.")
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to script location.")
    parser.add_argument("--index-schema", default=None, help="Override episode index schema path.")
    parser.add_argument("--mentions-schema", default=None, help="Override episode mentions schema path.")
    parser.add_argument(
        "--no-legacy-warnings",
        action="store_true",
        help="Do not warn for legacy packages without mentions.json.",
    )
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit non-zero when warnings are present.",
    )
    parser.add_argument("--json-report", action="store_true", help="Print machine-readable JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    index_schema_path = (
        Path(args.index_schema).resolve()
        if args.index_schema
        else root / "fantasy-management/_ai/schemas/episode-index.schema.json"
    )
    mentions_schema_path = (
        Path(args.mentions_schema).resolve()
        if args.mentions_schema
        else root / "fantasy-management/_ai/schemas/episode-mentions.schema.json"
    )
    report = Report()

    if args.all:
        package_dirs = discover_episode_packages(root)
    else:
        package_dirs = [Path(package).resolve() for package in args.packages]

    if not package_dirs:
        print("No episode packages selected. Pass package paths or use --all.", file=sys.stderr)
        return 2

    for package_dir in package_dirs:
        if not package_dir.exists():
            report.error(package_dir, "Episode package directory does not exist.")
            continue
        validate_package(
            package_dir=package_dir,
            root=root,
            index_schema_path=index_schema_path,
            mentions_schema_path=mentions_schema_path,
            report=report,
            warnings_for_legacy=not args.no_legacy_warnings,
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
