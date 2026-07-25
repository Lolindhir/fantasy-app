"""Process-review, publish-request, and ready-state validation."""
from __future__ import annotations

from pathlib import Path

from podcast_pipeline_schema import check_active_profiles, check_identity, load_optional_json, phase_requires, schema_path, validate_schema
from podcast_pipeline_types import GoldenProfiles, PipelineReport, WorkPackageData


def validate_process_review(
    data: WorkPackageData,
    repo_root: Path,
    profiles: GoldenProfiles,
    report: PipelineReport,
    require_ready: bool,
) -> None:
    work_status = data.work_status
    gates = work_status.get("gates") if isinstance(work_status.get("gates"), dict) else {}
    review_path = data.work_dir / "process-review/improvement-proposals.json"
    review = load_optional_json(review_path, report)
    if review is None:
        if phase_requires(work_status, "process_review_complete") or require_ready:
            report.error(review_path, "Process review is required.")
        return

    data.process_review = review
    validate_schema(review, schema_path(repo_root, "process_review"), report, review_path)
    check_identity(review, str(work_status.get("episode_id") or ""), str(work_status.get("source_id") or ""), review_path, report)
    check_active_profiles(review.get("evaluated_profiles"), profiles, review_path, report)
    selected_profiles = set(data.content_map_manifest.get("golden_profiles", [])) if data.content_map_manifest else set()
    if not selected_profiles.issubset(set(review.get("evaluated_profiles", []))):
        report.error(review_path, "Process review must evaluate every Golden Set profile selected by the Content Map.")
    for finding in review.get("findings", []):
        if not isinstance(finding, dict):
            continue
        for segment_id in finding.get("related_segments", []):
            if segment_id not in data.segments:
                report.error(review_path, f"finding references unknown segment_id: {segment_id!r}")
        for take_id in finding.get("related_takes", []):
            if take_id not in data.takes:
                report.error(review_path, f"finding references unknown take_id: {take_id!r}")
        if finding.get("severity") == "blocker" and (require_ready or gates.get("ready_for_publish")):
            report.error(review_path, f"blocking process-review finding remains: {finding.get('finding_id')}: {finding.get('description')}")


def validate_publish_request(data: WorkPackageData, repo_root: Path, report: PipelineReport, require_ready: bool) -> None:
    work_status = data.work_status
    gates = work_status.get("gates") if isinstance(work_status.get("gates"), dict) else {}
    publish_path = data.work_dir / "publish-request.json"
    request = load_optional_json(publish_path, report)
    if request is None:
        if require_ready or gates.get("ready_for_publish"):
            report.error(publish_path, "publish-request.json is required for ready_for_publish.")
        return

    data.publish_request = request
    episode_id = str(work_status.get("episode_id") or "")
    source_id = str(work_status.get("source_id") or "")
    validate_schema(request, schema_path(repo_root, "publish_request"), report, publish_path)
    check_identity(request, episode_id, source_id, publish_path, report)
    if request.get("year") != work_status.get("year"):
        report.error(publish_path, "year must match work-status.json.")
    expected_target = f"fantasy-management/sources/podcasts/{source_id}/episodes/{work_status.get('year')}/{episode_id}"
    if request.get("target_package_path") != expected_target:
        report.error(publish_path, f"target_package_path must equal {expected_target!r}.")
    if data.article_manifest and request.get("title") != data.article_manifest.get("title"):
        report.error(publish_path, "title must match article/manifest.json.")
    if data.article_manifest and request.get("language") != data.article_manifest.get("language"):
        report.error(publish_path, "language must match article/manifest.json.")


def validate_ready_state(data: WorkPackageData, report: PipelineReport, require_ready: bool) -> None:
    gates = data.work_status.get("gates") if isinstance(data.work_status.get("gates"), dict) else {}
    if not (require_ready or gates.get("ready_for_publish")):
        return
    if data.content_map_manifest and data.content_map_manifest.get("status") != "complete":
        report.error(data.work_dir / "content-map/manifest.json", "Content Map manifest must be complete before publication.")
    for segment_id, segment in data.segments.items():
        status = segment.get("status") if isinstance(segment.get("status"), dict) else {}
        for key in ("mapped", "takes_complete", "article_complete", "mention_audit_complete", "reconciled"):
            if status.get(key) is not True:
                report.error(data.work_dir, f"segment {segment_id!r} status.{key} must be true before publication.")
    if data.article_manifest and data.article_manifest.get("status") != "complete":
        report.error(data.work_dir / "article/manifest.json", "Article manifest must be complete before publication.")
    if data.process_review and data.process_review.get("review_status") != "complete":
        report.error(data.work_dir / "process-review/improvement-proposals.json", "Process review must be complete before publication.")
