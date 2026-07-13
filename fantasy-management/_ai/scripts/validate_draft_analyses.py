#!/usr/bin/env python3
"""Validate structured Fantasy Management draft analyses.

Default usage:

  python fantasy-management/_ai/scripts/validate_draft_analyses.py --all

Or validate one or more explicit JSON files:

  python fantasy-management/_ai/scripts/validate_draft_analyses.py \
    fantasy-management/analyses/2026/drafts/2026-07-13_2026-rookie-draft-postmortem.json

The validator checks JSON syntax, duplicate keys, the dedicated schema,
companion Markdown files and a small set of cross-field invariants. It does
not judge whether fantasy evaluations or grades are strategically correct.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains the same key more than once."""


@dataclass
class Issue:
    severity: str
    path: str
    message: str


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def error(self, path: Path | str, message: str) -> None:
        self.errors.append(Issue("error", str(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.warnings.append(Issue("warning", str(path), message))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"[{prefix}] {issue.path}: {issue.message}")

        if not self.errors and not self.warnings:
            print("OK: no draft analysis validation errors or warnings.")
        else:
            print(
                f"Summary: {len(self.errors)} error(s), "
                f"{len(self.warnings)} warning(s)."
            )


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


def load_json(path: Path, report: Report, root: Path) -> Any | None:
    label = rel(path, root)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=object_pairs_no_duplicates)
    except FileNotFoundError:
        report.error(label, "File does not exist.")
    except DuplicateKeyError as exc:
        report.error(label, str(exc))
    except json.JSONDecodeError as exc:
        report.error(label, f"Invalid JSON: {exc}")
    except UnicodeDecodeError as exc:
        report.error(label, f"File is not valid UTF-8: {exc}")
    return None


def format_json_path(path: Iterable[Any]) -> str:
    parts = list(path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


def validate_schema(
    data: Any,
    schema: dict[str, Any],
    path: Path,
    report: Report,
    root: Path,
) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        report.error(
            rel(path, root),
            f"Schema violation at {format_json_path(error.path)}: {error.message}",
        )


def ensure_unique(
    values: list[Any],
    label: str,
    path: Path,
    report: Report,
    root: Path,
) -> None:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        report.error(
            rel(path, root),
            f"Duplicate {label}: {sorted(duplicates, key=str)}",
        )


def validate_snapshot_sources(
    data: dict[str, Any],
    path: Path,
    report: Report,
    root: Path,
) -> None:
    sources = data.get("data_snapshot", {}).get("sources", [])
    sha_pattern = re.compile(r"^[0-9a-f]{40}$")

    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        blob_sha = source.get("blob_sha")
        if blob_sha is not None and not sha_pattern.fullmatch(str(blob_sha)):
            report.error(
                rel(path, root),
                f"data_snapshot.sources.{index}.blob_sha is not a 40-character lowercase Git SHA.",
            )
        source_path = str(source.get("path") or "").strip()
        if not source_path:
            report.error(
                rel(path, root),
                f"data_snapshot.sources.{index}.path is blank.",
            )


def validate_cross_fields(
    data: dict[str, Any],
    path: Path,
    report: Report,
    root: Path,
) -> None:
    label = rel(path, root)
    picks = data.get("picks", [])
    teams = data.get("teams", [])

    if isinstance(picks, list):
        pick_keys = [pick.get("pick_key") for pick in picks if isinstance(pick, dict)]
        overall_picks = [pick.get("overall_pick") for pick in picks if isinstance(pick, dict)]
        ensure_unique(pick_keys, "pick_key values", path, report, root)
        ensure_unique(overall_picks, "overall_pick values", path, report, root)

        expected = list(range(1, len(overall_picks) + 1))
        actual = sorted(value for value in overall_picks if isinstance(value, int))
        if actual != expected:
            report.warn(
                label,
                "overall_pick values are not a contiguous sequence from 1 through the number of picks.",
            )

    if isinstance(teams, list):
        team_ids = [team.get("team_id") for team in teams if isinstance(team, dict)]
        ensure_unique(team_ids, "team_id values", path, report, root)

    companion_markdown = path.with_suffix(".md")
    if not companion_markdown.is_file():
        report.error(
            label,
            f"Missing companion Markdown file: {rel(companion_markdown, root)}",
        )

    review_of = data.get("review_of")
    if isinstance(review_of, str) and review_of.strip():
        review_target = root / review_of
        if not review_target.is_file():
            report.error(label, f"review_of target does not exist: {review_of}")

    context_completeness = data.get("context_completeness")
    team_context_available = data.get("team_context_available")
    if context_completeness == "full" and team_context_available is False:
        report.warn(
            label,
            "context_completeness is full while team_context_available is false.",
        )

    validate_snapshot_sources(data, path, report, root)


def discover_analysis_files(root: Path) -> list[Path]:
    analyses_root = root / "fantasy-management" / "analyses"
    if not analyses_root.is_dir():
        return []
    return sorted(analyses_root.glob("**/drafts/*.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Draft-analysis JSON files to validate.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every JSON file under fantasy-management/analyses/**/drafts/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root_from_script()
    report = Report()

    schema_path = (
        root
        / "fantasy-management"
        / "_ai"
        / "schemas"
        / "draft-analysis.schema.json"
    )
    schema = load_json(schema_path, report, root)
    if schema is None:
        report.print_text()
        return 1

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema raises several schema-specific subclasses
        report.error(rel(schema_path, root), f"Invalid JSON Schema: {exc}")
        report.print_text()
        return 1

    paths: list[Path]
    if args.all:
        paths = discover_analysis_files(root)
    else:
        paths = [
            (root / value).resolve() if not Path(value).is_absolute() else Path(value)
            for value in args.paths
        ]

    if not paths:
        report.error(
            "draft analyses",
            "No analysis files selected. Pass --all or one or more JSON paths.",
        )
        report.print_text()
        return 1

    for path in paths:
        data = load_json(path, report, root)
        if not isinstance(data, dict):
            if data is not None:
                report.error(rel(path, root), "Top-level JSON value must be an object.")
            continue
        validate_schema(data, schema, path, report, root)
        validate_cross_fields(data, path, report, root)

    report.print_text()
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    sys.exit(main())
