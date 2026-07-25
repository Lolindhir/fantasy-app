"""Raw-source and Content Map validation for podcast work packages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from podcast_pipeline_schema import (
    check_active_profiles,
    check_identity,
    contiguous_orders,
    load_optional_json,
    phase_requires,
    schema_path,
    validate_schema,
)
from podcast_pipeline_types import GoldenProfiles, PipelineDataError, PipelineReport, WorkPackageData, safe_relative_path


def validate_raw(work_status: dict[str, Any], work_dir: Path, report: PipelineReport, require_ready: bool) -> None:
    raw_dir = work_dir / "raw"
    if not (phase_requires(work_status, "raw_complete") or require_ready):
        return
    if not raw_dir.is_dir():
        report.error(raw_dir, "raw directory is required when raw_complete is true.")
        return
    if not (raw_dir / "manifest.md").is_file():
        report.error(raw_dir / "manifest.md", "raw/manifest.md is required.")
    raw_parts = [path for path in raw_dir.iterdir() if path.is_file() and path.name != "manifest.md"]
    if not raw_parts:
        report.error(raw_dir, "At least one raw source part is required.")


def validate_content_map(
    data: WorkPackageData,
    repo_root: Path,
    profiles: GoldenProfiles,
    report: PipelineReport,
    require_ready: bool,
) -> None:
    work_dir = data.work_dir
    work_status = data.work_status
    episode_id = str(work_status.get("episode_id") or "")
    source_id = str(work_status.get("source_id") or "")
    manifest_path = work_dir / "content-map/manifest.json"
    manifest = load_optional_json(manifest_path, report)
    if manifest is None:
        if phase_requires(work_status, "content_map_complete") or require_ready:
            report.error(manifest_path, "Content Map manifest is required.")
        return

    data.content_map_manifest = manifest
    validate_schema(manifest, schema_path(repo_root, "content_map_manifest"), report, manifest_path)
    check_identity(manifest, episode_id, source_id, manifest_path, report)
    check_active_profiles(manifest.get("golden_profiles"), profiles, manifest_path, report)
    descriptors = manifest.get("segments") if isinstance(manifest.get("segments"), list) else []
    if manifest.get("segment_count") != len(descriptors):
        report.error(manifest_path, f"segment_count={manifest.get('segment_count')!r} does not match {len(descriptors)} descriptors.")
    contiguous_orders(descriptors, manifest_path, report, "Content Map segment")

    seen_segment_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_claim_ids: set[str] = set()
    seen_mention_segment_ids: set[str] = set()
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        segment_id = str(descriptor.get("segment_id") or "")
        if segment_id in seen_segment_ids:
            report.error(manifest_path, f"duplicate segment_id: {segment_id!r}")
        seen_segment_ids.add(segment_id)
        raw_path = descriptor.get("path")
        if raw_path in seen_paths:
            report.error(manifest_path, f"duplicate segment path: {raw_path!r}")
        seen_paths.add(str(raw_path))
        try:
            path = safe_relative_path(work_dir, raw_path, "content-map")
        except PipelineDataError as exc:
            report.error(manifest_path, str(exc))
            continue
        segment = load_optional_json(path, report)
        if segment is None:
            report.error(path, "Content Map segment file is missing.")
            continue
        validate_schema(segment, schema_path(repo_root, "content_map_segment"), report, path)
        check_identity(segment, episode_id, source_id, path, report)
        if segment.get("segment_id") != segment_id:
            report.error(path, "segment_id does not match manifest descriptor.")
        if segment.get("order") != descriptor.get("order"):
            report.error(path, "order does not match manifest descriptor.")
        if descriptor.get("segment_type") and segment.get("segment_type") != descriptor.get("segment_type"):
            report.error(path, "segment_type does not match manifest descriptor.")
        if descriptor.get("source_depth") and segment.get("source_depth") != descriptor.get("source_depth"):
            report.error(path, "source_depth does not match manifest descriptor.")
        check_active_profiles(segment.get("golden_profiles"), profiles, path, report)
        if not set(segment.get("golden_profiles", [])).issubset(set(manifest.get("golden_profiles", []))):
            report.error(path, "segment Golden Set profiles must be declared in the Content Map manifest.")

        source_range = segment.get("source_range") if isinstance(segment.get("source_range"), dict) else {}
        for raw_part in source_range.get("raw_parts", []):
            try:
                raw_part_path = safe_relative_path(work_dir, raw_part, "raw")
            except PipelineDataError as exc:
                report.error(path, str(exc))
                continue
            if not raw_part_path.is_file():
                report.error(path, f"referenced raw part does not exist: {raw_part}")

        depth = segment.get("source_depth")
        claims = segment.get("substantive_claims") if isinstance(segment.get("substantive_claims"), list) else []
        obligations = segment.get("reasoning_obligations") if isinstance(segment.get("reasoning_obligations"), list) else []
        dimensions = segment.get("expected_dimensions") if isinstance(segment.get("expected_dimensions"), list) else []
        planned = segment.get("planned_outputs") if isinstance(segment.get("planned_outputs"), dict) else {}
        if depth in {"substantive", "deep", "structural"} and not planned.get("take_ids"):
            report.error(path, f"{depth} segment must plan at least one reusable take.")
        if depth in {"deep", "structural"}:
            if not claims:
                report.error(path, f"{depth} segment must preserve at least one substantive claim.")
            if not obligations:
                report.error(path, f"{depth} segment must define reasoning obligations.")
            if not dimensions:
                report.error(path, f"{depth} segment must define expected dimensions.")
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            claim_id = str(claim.get("claim_id") or "")
            if claim_id in seen_claim_ids:
                report.error(path, f"claim_id must be unique across the episode: {claim_id!r}")
            seen_claim_ids.add(claim_id)
        mention_segment_id = str(planned.get("mention_segment_id") or "")
        if mention_segment_id:
            if mention_segment_id in seen_mention_segment_ids:
                report.error(path, f"mention_segment_id must be unique: {mention_segment_id!r}")
            seen_mention_segment_ids.add(mention_segment_id)
        for value in sorted(set(dimensions) - profiles.all_dimensions):
            report.warn(path, f"expected dimension is not yet defined by an active Golden Set profile: {value!r}")
        data.segments[segment_id] = segment
