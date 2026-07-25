"""Orchestrate validation for incremental podcast extraction work packages."""
from __future__ import annotations

from pathlib import Path

from podcast_pipeline_types import READY_GATES, PipelineReport, WorkPackageData
from podcast_pipeline_schema import load_golden_profiles, load_optional_json, schema_path, validate_schema
from podcast_article_validation import validate_article
from podcast_content_map_validation import validate_content_map, validate_raw
from podcast_mention_validation import validate_mentions
from podcast_publish_validation import validate_process_review, validate_publish_request, validate_ready_state
from podcast_take_validation import validate_takes


def validate_work_package(
    work_dir: Path,
    repo_root: Path,
    report: PipelineReport | None = None,
    *,
    require_ready: bool = False,
) -> tuple[PipelineReport, WorkPackageData | None]:
    report = report or PipelineReport()
    work_dir = work_dir.resolve()
    status_path = work_dir / "work-status.json"
    work_status = load_optional_json(status_path, report)
    if work_status is None:
        report.error(status_path, "work-status.json is required.")
        return report, None
    validate_schema(work_status, schema_path(repo_root, "work_status"), report, status_path)

    gates = work_status.get("gates") if isinstance(work_status.get("gates"), dict) else {}
    if gates.get("ready_for_publish") and not all(gates.get(key) for key in READY_GATES[:-1]):
        report.error(status_path, "ready_for_publish gate requires every previous gate to be true.")
    if work_status.get("phase") in {"ready_for_publish", "published"} and not all(gates.get(key) for key in READY_GATES):
        report.error(status_path, f"phase {work_status.get('phase')!r} requires all gates to be true.")
    if require_ready and work_status.get("phase") != "ready_for_publish":
        report.error(status_path, "Builder requires phase='ready_for_publish'.")
    for blocker in work_status.get("blockers", []):
        if isinstance(blocker, dict) and blocker.get("blocking") and (require_ready or gates.get("ready_for_publish")):
            report.error(status_path, f"blocking work item remains: {blocker.get('id')}: {blocker.get('description')}")

    data = WorkPackageData(work_dir=work_dir, work_status=work_status)
    profiles = load_golden_profiles(repo_root, report)
    validate_raw(work_status, work_dir, report, require_ready)
    validate_content_map(data, repo_root, profiles, report, require_ready)
    validate_takes(data, repo_root, profiles, report, require_ready)
    validate_article(data, repo_root, report, require_ready)
    validate_mentions(data, repo_root, report, require_ready)
    validate_process_review(data, repo_root, profiles, report, require_ready)
    validate_publish_request(data, repo_root, report, require_ready)
    validate_ready_state(data, report, require_ready)
    return report, data
