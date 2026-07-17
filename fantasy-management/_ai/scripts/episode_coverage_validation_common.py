"""Shared helpers for podcast mention coverage validation."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from podcast_package_io import CATEGORIES, PackageDataError, load_json_file

MANDATORY_TYPES = {"ranking_subject", "substantive_take", "news_subject"}
FALSE_POSITIVE = "false_positive"

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
        report.error(package, "Python package 'jsonschema' is required.")
        return
    for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path)):
        report.error(package, f"{label} schema violation at {format_json_path(error.path)}: {error.message}")


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = text.replace("’", "'").replace("`", "'")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def collect_takes(takes: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    player_ids: set[str] = set()
    categories = takes.get("take_categories")
    if not isinstance(categories, dict):
        return by_id, player_ids
    for category in CATEGORIES:
        for entry in categories.get(category, []):
            if not isinstance(entry, dict):
                continue
            take_id = entry.get("id")
            if isinstance(take_id, str) and take_id:
                by_id[take_id] = entry
                if category == "players":
                    player_ids.add(take_id)
    return by_id, player_ids


def mention_names(mention: dict[str, Any]) -> list[str]:
    result: list[str] = []
    resolution = mention.get("entity_resolution")
    if isinstance(resolution, dict) and resolution.get("status") == "confirmed" and isinstance(mention.get("entity"), str):
        result.append(mention["entity"])
    raw = mention.get("raw_entity_mentions")
    if isinstance(raw, list):
        result.extend(value for value in raw if isinstance(value, str))
    return result


def identities_for_mention(mention: dict[str, Any]) -> set[str]:
    return {normalize_text(value) for value in mention_names(mention) if normalize_text(value)}


def identities_for_take(take: dict[str, Any]) -> set[str]:
    return {normalize_text(take.get(key)) for key in ("entity", "raw_entity_mention") if normalize_text(take.get(key))}


def valid_links(value: Any, takes: dict[str, dict[str, Any]]) -> list[str]:
    return [item for item in value if isinstance(item, str) and item in takes] if isinstance(value, list) else []


def mandatory(types: set[str]) -> bool:
    return bool(types & MANDATORY_TYPES)


def mention_uncovered(mention: dict[str, Any], takes: dict[str, dict[str, Any]]) -> bool:
    types = set(mention.get("mention_types") or [])
    if FALSE_POSITIVE in types:
        return False
    coverage = mention.get("coverage")
    if not isinstance(coverage, dict):
        return True
    if mandatory(types):
        return coverage.get("episode_md") is not True or not valid_links(coverage.get("subject_take_ids"), takes)
    if coverage.get("episode_md") is True:
        return False
    note = coverage.get("note")
    return not isinstance(note, str) or not note.strip()


def calculate_counts(mentions: list[dict[str, Any]], takes: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(mentions), "resolved": 0, "ambiguous": 0, "unresolved": 0, "ranking_subjects": 0, "substantive_subjects": 0, "context_only": 0, "with_take_links": 0, "uncovered": 0}
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
        if isinstance(coverage, dict) and (valid_links(coverage.get("subject_take_ids"), takes) or valid_links(coverage.get("context_take_ids"), takes)):
            counts["with_take_links"] += 1
        if mention_uncovered(mention, takes):
            counts["uncovered"] += 1
    return counts
