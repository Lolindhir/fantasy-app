"""Reader-facing article validation for podcast work packages."""
from __future__ import annotations

from pathlib import Path

from podcast_pipeline_schema import check_identity, contiguous_orders, load_optional_json, phase_requires, schema_path, validate_schema
from podcast_pipeline_types import PipelineDataError, PipelineReport, WorkPackageData, safe_relative_path


def validate_article(data: WorkPackageData, repo_root: Path, report: PipelineReport, require_ready: bool) -> None:
    work_dir = data.work_dir
    work_status = data.work_status
    episode_id = str(work_status.get("episode_id") or "")
    source_id = str(work_status.get("source_id") or "")
    manifest_path = work_dir / "article/manifest.json"
    manifest = load_optional_json(manifest_path, report)
    if manifest is None:
        if phase_requires(work_status, "article_complete") or require_ready:
            report.error(manifest_path, "Article manifest is required.")
        return

    data.article_manifest = manifest
    validate_schema(manifest, schema_path(repo_root, "article_manifest"), report, manifest_path)
    check_identity(manifest, episode_id, source_id, manifest_path, report)
    descriptors = manifest.get("sections") if isinstance(manifest.get("sections"), list) else []
    if manifest.get("section_count") != len(descriptors):
        report.error(manifest_path, f"section_count={manifest.get('section_count')!r} does not match {len(descriptors)} descriptors.")
    contiguous_orders(descriptors, manifest_path, report, "article section")

    seen_section_ids: set[str] = set()
    seen_paths: set[str] = set()
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        section_id = str(descriptor.get("section_id") or "")
        if section_id in seen_section_ids:
            report.error(manifest_path, f"duplicate section_id: {section_id!r}")
        seen_section_ids.add(section_id)
        raw_path = descriptor.get("path")
        if raw_path in seen_paths:
            report.error(manifest_path, f"duplicate article section path: {raw_path!r}")
        seen_paths.add(str(raw_path))
        try:
            path = safe_relative_path(work_dir, raw_path, "article")
        except PipelineDataError as exc:
            report.error(manifest_path, str(exc))
            continue
        if not path.is_file():
            report.error(path, "Article section file is missing.")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            report.error(path, f"Article section must be UTF-8: {exc}")
            continue
        if not text.strip():
            report.error(path, "Article section must not be empty.")
        data.article_sections[section_id] = text
        for segment_id in descriptor.get("segment_ids", []):
            if segment_id not in data.segments:
                report.error(path, f"article section references unknown segment_id: {segment_id!r}")
        for take_id in descriptor.get("take_ids", []):
            if take_id not in data.takes:
                report.error(path, f"article section references unknown take_id: {take_id!r}")

    if not data.segments or not (phase_requires(work_status, "article_complete") or require_ready):
        return
    section_by_id = {
        str(item.get("section_id")): item
        for item in descriptors
        if isinstance(item, dict) and item.get("section_id")
    }
    for segment_id, segment in data.segments.items():
        planned = segment.get("planned_outputs") if isinstance(segment.get("planned_outputs"), dict) else {}
        planned_section_ids = set(planned.get("article_section_ids", []))
        if not planned_section_ids:
            report.error(manifest_path, f"segment {segment_id!r} has no planned article section.")
        for section_id in sorted(planned_section_ids):
            descriptor = section_by_id.get(section_id)
            if not descriptor:
                report.error(manifest_path, f"segment {segment_id!r} planned article section is missing: {section_id!r}")
            elif segment_id not in descriptor.get("segment_ids", []):
                report.error(manifest_path, f"article section {section_id!r} does not link back to segment {segment_id!r}.")
