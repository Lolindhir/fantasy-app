#!/usr/bin/env python3
"""Validate cross-file entity mention coverage for podcast episode packages.

The validator checks technical completeness and consistency. It does not decide
whether a podcast statement is factually correct or whether an evaluation is
strategically sound.

Schema-version-2 packages require mentions.json and a completed second-pass
coverage audit. Legacy packages remain valid but do not receive the same
coverage guarantee.
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
        if not false_positive and not (mention_types & MANDATORY_TAKE_TYPES):
            counts["context_only"] += 1

        coverage = mention.get("coverage")
        if not isinstance(coverage, dict):
            if not false_positive:
                counts["uncovered"] += 1
            continue

        take_ids = coverage.get("take_ids")
        take_ids = take_ids if isinstance(take_ids, list) else []
        valid_take_ids = [take_id for take_id in take_ids if take_id in take_by_id]
        if valid_take_ids:
            counts["with_take_links"] += 1

        standalone_required = coverage.get("standalone_take_required") is True
        episode_covered = coverage.get("episode_md") is True
        if not false_positive and (
            not episode_covered
            or (standalone_required and not valid_take_ids)
        ):
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
    referenced_take_ids: set[str] = set()
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

        if false_positive and len(mention_types) > 1:
            report.error(
                package_label,
                f"Mention {mention_id} combines false_positive with normal mention types.",
            )

        coverage = mention.get("coverage")
        if not isinstance(coverage, dict):
            report.error(package_label, f"Mention {mention_id} is missing coverage object.")
            continue

        take_ids = coverage.get("take_ids")
        take_ids = take_ids if isinstance(take_ids, list) else []
        valid_take_ids: list[str] = []
        for take_id in take_ids:
            if take_id not in take_by_id:
                report.error(
                    package_label,
                    f"Mention {mention_id} references unknown take id: {take_id}",
                )
                continue
            valid_take_ids.append(take_id)
            referenced_take_ids.add(take_id)

        standalone_required = coverage.get("standalone_take_required") is True
        if standalone_required and not valid_take_ids:
            report.error(
                package_label,
                f"Mention {mention_id} requires a standalone take but has no valid take link.",
            )

        if (
            mention.get("entity_type") == "player"
            and standalone_required
            and valid_take_ids
            and not any(take_id in player_take_ids for take_id in valid_take_ids)
        ):
            report.error(
                package_label,
                f"Player mention {mention_id} requires a player take, but links only to non-player takes.",
            )

        if false_positive:
            if coverage.get("episode_md") is True:
                report.warn(
                    package_label,
                    f"False-positive mention {mention_id} is marked as included in episode.md.",
                )
            if take_ids:
                report.error(
                    package_label,
                    f"False-positive mention {mention_id} must not link to takes.",
                )
            continue

        if coverage.get("episode_md") is not True:
            report.error(
                package_label,
                f"Mention {mention_id} is not covered by the complete episode.md mention register.",
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
                    f"Mention {mention_id} is marked episode_md=true, but neither its canonical "
                    "nor raw name appears in episode.md.",
                )

    for player_take_id in sorted(player_take_ids - referenced_take_ids):
        report.error(
            package_label,
            f"Player take {player_take_id} is not covered by any mentions.json entry.",
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
