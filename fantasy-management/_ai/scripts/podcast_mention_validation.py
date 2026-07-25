"""Independent mention-audit validation for podcast work packages."""
from __future__ import annotations

from pathlib import Path

from podcast_pipeline_schema import check_identity, load_optional_json, phase_requires, schema_path, validate_schema
from podcast_pipeline_types import PipelineReport, WorkPackageData


def validate_mentions(data: WorkPackageData, repo_root: Path, report: PipelineReport, require_ready: bool) -> None:
    work_dir = data.work_dir
    work_status = data.work_status
    episode_id = str(work_status.get("episode_id") or "")
    source_id = str(work_status.get("source_id") or "")
    mention_dir = work_dir / "mentions/segments"
    if mention_dir.exists():
        for path in sorted(mention_dir.glob("*.json")):
            mention_segment = load_optional_json(path, report)
            if mention_segment is None:
                continue
            validate_schema(mention_segment, schema_path(repo_root, "mention_segment"), report, path)
            check_identity(mention_segment, episode_id, source_id, path, report)
            segment_id = str(mention_segment.get("segment_id") or "")
            if segment_id in data.mention_segments:
                report.error(path, f"duplicate mention segment_id: {segment_id!r}")
            data.mention_segments[segment_id] = mention_segment
            if segment_id not in data.segments:
                report.error(path, f"mention segment references unknown Content Map segment: {segment_id!r}")
            if path.name != f"{segment_id}.json":
                report.error(path, "mention segment filename must equal '<segment_id>.json'.")

    if data.segments and (phase_requires(work_status, "mention_audit_complete") or require_ready):
        for segment_id, segment in data.segments.items():
            planned = segment.get("planned_outputs") if isinstance(segment.get("planned_outputs"), dict) else {}
            mention_segment_id = str(planned.get("mention_segment_id") or "")
            mention_segment = data.mention_segments.get(mention_segment_id)
            if not mention_segment:
                report.error(mention_dir, f"segment {segment_id!r} mention audit is missing: {mention_segment_id!r}")
            elif mention_segment.get("status") != "complete":
                report.error(mention_dir / f"{mention_segment_id}.json", "mention segment must be complete.")

    seen_mention_ids: set[str] = set()
    section_ids = set(data.article_sections)
    for segment_id, mention_segment in data.mention_segments.items():
        path = mention_dir / f"{segment_id}.json"
        for mention in mention_segment.get("mentions", []):
            if not isinstance(mention, dict):
                continue
            mention_id = str(mention.get("id") or "")
            if mention_id in seen_mention_ids:
                report.error(path, f"mention id must be unique across the episode: {mention_id!r}")
            seen_mention_ids.add(mention_id)
            coverage = mention.get("coverage") if isinstance(mention.get("coverage"), dict) else {}
            for take_id in coverage.get("subject_take_ids", []) + coverage.get("context_take_ids", []):
                if take_id not in data.takes:
                    report.error(path, f"mention references unknown take_id: {take_id!r}")
            if coverage.get("episode_md"):
                article_section = coverage.get("episode_md_section")
                if article_section not in section_ids:
                    report.error(path, f"mention episode_md_section must reference an article section ID: {article_section!r}")
