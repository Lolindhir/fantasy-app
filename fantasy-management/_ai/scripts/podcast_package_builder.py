"""Deterministic publication builder for podcast extraction work packages."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from podcast_pipeline_types import BuildResult, CATEGORIES, PipelineDataError, WorkPackageData, write_json
from podcast_work_validation import validate_work_package


def generated_episode_markdown(data: WorkPackageData) -> str:
    assert data.article_manifest is not None
    ordered = sorted(data.article_manifest["sections"], key=lambda item: item["order"])
    chunks = [data.article_sections[descriptor["section_id"]].strip() for descriptor in ordered]
    return "\n\n".join(chunks).rstrip() + "\n"


def generated_takes(data: WorkPackageData) -> dict[str, Any]:
    assert data.publish_request is not None
    categories: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}
    for take in data.takes.values():
        categories[str(take["category"])].append(take)
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


def mention_counts(mentions: list[dict[str, Any]]) -> dict[str, int]:
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
        status = (mention.get("entity_resolution") or {}).get("status")
        if status == "confirmed":
            counts["resolved"] += 1
        elif status == "ambiguous":
            counts["ambiguous"] += 1
        elif status == "unresolved":
            counts["unresolved"] += 1
        types = set(mention.get("mention_types", []))
        if "ranking_subject" in types:
            counts["ranking_subjects"] += 1
        if types & {"substantive_take", "news_subject"}:
            counts["substantive_subjects"] += 1
        if not types & {"ranking_subject", "substantive_take", "news_subject"}:
            counts["context_only"] += 1
        coverage = mention.get("coverage") or {}
        if coverage.get("subject_take_ids") or coverage.get("context_take_ids"):
            counts["with_take_links"] += 1
        if coverage.get("standalone_take_required") and not coverage.get("subject_take_ids"):
            counts["uncovered"] += 1
        elif coverage.get("episode_md") and not coverage.get("episode_md_section"):
            counts["uncovered"] += 1
    return counts


def generated_index(data: WorkPackageData, takes: dict[str, Any], mentions: dict[str, Any]) -> dict[str, Any]:
    assert data.publish_request is not None
    request = data.publish_request
    counts = mention_counts(mentions["mentions"])
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
        "package_path": request["target_package_path"],
        "files": {
            "raw_manifest": "raw/manifest.md",
            "episode_summary": "episode.md",
            "takes": "takes.json",
            "mentions": "mentions.json",
        },
        "raw_status": "complete",
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
