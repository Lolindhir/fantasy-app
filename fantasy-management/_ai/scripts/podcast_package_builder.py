"""Deterministic publication builder for podcast extraction work packages."""
from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path
from typing import Any

from episode_coverage_validation import validate_package as validate_coverage_package
from episode_coverage_validation_common import Report as CoverageReport, calculate_counts, collect_takes
from episode_package_validation import validate_episode_package
from episode_package_validation_common import RegistryIndex, Report as PackageReport, rel
from podcast_pipeline_types import BuildResult, CATEGORIES, PipelineDataError, WorkPackageData, write_json
from podcast_work_validation import validate_work_package


def generated_episode_markdown(data: WorkPackageData) -> str:
    assert data.article_manifest is not None
    ordered = sorted(data.article_manifest["sections"], key=lambda item: item["order"])
    chunks = [data.article_sections[descriptor["section_id"]].strip() for descriptor in ordered]
    return "\n\n".join(chunks).rstrip() + "\n"


def _entry_point_take(take: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(take)
    evidence = result.get("evidence")
    if isinstance(evidence, list):
        result["evidence_points"] = evidence
        result["evidence"] = evidence[0] if evidence else {"timestamp_start": "unknown"}
    return result


def generated_takes(data: WorkPackageData) -> dict[str, Any]:
    assert data.publish_request is not None
    categories: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}
    for take in data.takes.values():
        categories[str(take["category"])].append(_entry_point_take(take))
    for category in CATEGORIES:
        categories[category].sort(key=lambda item: str(item.get("id")))
    return {
        "episode_id": data.publish_request["episode_id"],
        "source_id": data.publish_request["source_id"],
        "source_name": data.publish_request["source_name"],
        "take_categories": categories,
    }


def generated_mentions(data: WorkPackageData) -> dict[str, Any]:
    assert data.publish_request is not None
    mentions: list[dict[str, Any]] = []
    for segment in sorted(data.segments.values(), key=lambda item: item["order"]):
        mention_id = segment["planned_outputs"]["mention_segment_id"]
        mentions.extend(data.mention_segments[mention_id].get("mentions", []))
    return {
        "episode_id": data.publish_request["episode_id"],
        "source_id": data.publish_request["source_id"],
        "source_name": data.publish_request["source_name"],
        "mentions": mentions,
    }


def generated_index(data: WorkPackageData, takes: dict[str, Any], mentions: dict[str, Any]) -> dict[str, Any]:
    assert data.publish_request is not None
    request = data.publish_request
    take_by_id, _ = collect_takes(takes)
    counts = calculate_counts(mentions["mentions"], take_by_id)
    return {
        "package_schema_version": request["package_schema_version"],
        "episode_id": request["episode_id"],
        "source_id": request["source_id"],
        "source_name": request["source_name"],
        "episode_number": request.get("episode_number"),
        "title": request["title"],
        "published_date": request.get("published_date"),
        "processed_date": request.get("processed_date"),
        "language": request["language"],
        "status": "active_source_package",
        "package_path": request["target_package_path"].rstrip("/") + "/",
        "files": {
            "raw_manifest": "raw/manifest.md",
            "episode_summary": "episode.md",
            "takes": "takes.json",
            "mentions": "mentions.json",
        },
        "raw_status": "split_raw_referenced",
        "take_counts": {category: len(takes["take_categories"][category]) for category in CATEGORIES},
        "mention_counts": counts,
        "coverage_audit": {
            "status": "completed" if counts["uncovered"] == 0 else "needs_review",
            "method": "independent_second_pass_by_content_map_segment",
            "uncovered_mentions": counts["uncovered"],
            "notes": ["Generated from authored mention segments after Content Map reconciliation."],
        },
        "knowledge_derivation_status": "not_started",
        "notes": ["Generated deterministically from the podcast work package."],
    }


def _validate_generated_package(temp_dir: Path, repo_root: Path, final_index: dict[str, Any]) -> None:
    validation_dir = Path(tempfile.mkdtemp(prefix="podcast-validate-", dir=repo_root))
    try:
        shutil.copytree(temp_dir, validation_dir, dirs_exist_ok=True)
        staged_index = copy.deepcopy(final_index)
        staged_index["package_path"] = rel(validation_dir, repo_root).rstrip("/") + "/"
        write_json(validation_dir / "index.json", staged_index)

        package_report = PackageReport()
        validate_episode_package(
            validation_dir,
            repo_root,
            repo_root / "fantasy-management/_ai/schemas/episode-takes.schema.json",
            RegistryIndex(),
            package_report,
            False,
            True,
        )
        coverage_report = CoverageReport()
        validate_coverage_package(
            validation_dir,
            repo_root,
            repo_root / "fantasy-management/_ai/schemas/episode-index.schema.json",
            repo_root / "fantasy-management/_ai/schemas/episode-mentions.schema.json",
            coverage_report,
            True,
        )
        errors = [f"{issue.package}: {issue.message}" for issue in package_report.errors + coverage_report.errors]
        if errors:
            raise PipelineDataError("generated package failed existing validators: " + "; ".join(errors))
    finally:
        if validation_dir.exists():
            shutil.rmtree(validation_dir)


def build_published_package(
    work_dir: Path,
    repo_root: Path,
    output_dir: Path | None = None,
    *,
    replace_existing: bool = False,
) -> BuildResult:
    report, data = validate_work_package(work_dir, repo_root, require_ready=True)
    if report.errors or data is None:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in report.errors)
        raise PipelineDataError(f"work package is not publishable: {details}")
    assert data.publish_request is not None
    output_dir = (output_dir or repo_root / data.publish_request["target_package_path"]).resolve()
    if output_dir.exists() and not replace_existing:
        raise PipelineDataError(f"output directory already exists: {output_dir.as_posix()}")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.build-", dir=output_dir.parent))
    try:
        for name in ("raw", "content-map", "takes", "mentions", "article", "process-review"):
            source = work_dir / name
            if source.exists():
                shutil.copytree(source, temp_dir / name)
        episode_md = generated_episode_markdown(data)
        takes = generated_takes(data)
        mentions = generated_mentions(data)
        index = generated_index(data, takes, mentions)
        (temp_dir / "episode.md").write_text(episode_md, encoding="utf-8")
        write_json(temp_dir / "takes.json", takes)
        write_json(temp_dir / "mentions.json", mentions)
        write_json(temp_dir / "index.json", index)
        if index["coverage_audit"]["uncovered_mentions"] != 0:
            raise PipelineDataError("generated package has uncovered required mentions")
        _validate_generated_package(temp_dir, repo_root, index)

        backup_dir: Path | None = None
        if output_dir.exists():
            backup_dir = output_dir.with_name(f".{output_dir.name}.previous")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            output_dir.rename(backup_dir)
        try:
            temp_dir.rename(output_dir)
        except Exception:
            if backup_dir and backup_dir.exists() and not output_dir.exists():
                backup_dir.rename(output_dir)
            raise
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir)
        return BuildResult(
            output_dir=output_dir,
            take_count=sum(len(values) for values in takes["take_categories"].values()),
            mention_count=len(mentions["mentions"]),
            section_count=len(data.article_sections),
        )
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
