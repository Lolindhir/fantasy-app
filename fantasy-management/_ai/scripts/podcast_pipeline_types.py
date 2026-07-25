"""Core types and filesystem helpers for the podcast extraction pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CATEGORIES = ("players", "teams", "positions", "nfl", "fantasy", "other")
READY_GATES = (
    "raw_complete",
    "content_map_complete",
    "takes_complete",
    "article_complete",
    "mention_audit_complete",
    "content_map_reconciled",
    "process_review_complete",
    "ready_for_publish",
)
SCHEMA_FILES = {
    "work_status": "podcast-work-status.schema.json",
    "content_map_manifest": "podcast-content-map-manifest.schema.json",
    "content_map_segment": "podcast-content-map-segment.schema.json",
    "take_item": "podcast-take-item.schema.json",
    "article_manifest": "podcast-article-manifest.schema.json",
    "mention_segment": "podcast-mention-segment.schema.json",
    "process_review": "podcast-process-review.schema.json",
    "publish_request": "podcast-publish-request.schema.json",
    "golden_profile": "podcast-golden-profile.schema.json",
    "golden_profile_list": "podcast-golden-profile-list.schema.json",
}


class PipelineDataError(ValueError):
    """Raised when a podcast work package cannot be loaded safely."""


class DuplicateKeyError(ValueError):
    """Raised when JSON contains duplicate object keys."""


def _object_pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_object_pairs_no_duplicates)
    except FileNotFoundError as exc:
        raise PipelineDataError(f"missing JSON file: {path.as_posix()}") from exc
    except (DuplicateKeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PipelineDataError(f"invalid JSON in {path.as_posix()}: {exc}") from exc


def canonical_json_text(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json_text(data), encoding="utf-8")


def safe_relative_path(root: Path, raw: Any, expected_prefix: str | None = None) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise PipelineDataError("path must be a non-empty string")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise PipelineDataError(f"path must stay inside the package: {raw!r}")
    if expected_prefix and (not relative.parts or relative.parts[0] != expected_prefix):
        raise PipelineDataError(f"path must live below {expected_prefix}/: {raw!r}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise PipelineDataError(f"path escapes package: {raw!r}") from exc
    return resolved


@dataclass
class Issue:
    severity: str
    path: str
    message: str


@dataclass
class PipelineReport:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def error(self, path: Path | str, message: str) -> None:
        self.errors.append(Issue("error", str(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.warnings.append(Issue("warning", str(path), message))

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            label = "ERROR" if issue.severity == "error" else "WARN"
            print(f"[{label}] {issue.path}: {issue.message}")
        if not self.errors and not self.warnings:
            print("OK: podcast work package is valid.")
        else:
            print(f"Summary: {len(self.errors)} error(s), {len(self.warnings)} warning(s).")

    def to_json(self) -> dict[str, Any]:
        return {
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "summary": {"errors": len(self.errors), "warnings": len(self.warnings)},
        }


@dataclass(frozen=True)
class GoldenProfiles:
    active_ids: frozenset[str]
    dimensions_by_profile: dict[str, frozenset[str]]

    @property
    def all_dimensions(self) -> frozenset[str]:
        result: set[str] = set()
        for values in self.dimensions_by_profile.values():
            result.update(values)
        return frozenset(result)


@dataclass
class WorkPackageData:
    work_dir: Path
    work_status: dict[str, Any]
    content_map_manifest: dict[str, Any] | None = None
    segments: dict[str, dict[str, Any]] = field(default_factory=dict)
    takes: dict[str, dict[str, Any]] = field(default_factory=dict)
    article_manifest: dict[str, Any] | None = None
    article_sections: dict[str, str] = field(default_factory=dict)
    mention_segments: dict[str, dict[str, Any]] = field(default_factory=dict)
    process_review: dict[str, Any] | None = None
    publish_request: dict[str, Any] | None = None


@dataclass(frozen=True)
class BuildResult:
    output_dir: Path
    take_count: int
    mention_count: int
    section_count: int


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]
