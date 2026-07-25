"""Authored take validation and Content Map reconciliation."""
from __future__ import annotations

from pathlib import Path

from podcast_pipeline_schema import check_active_profiles, check_identity, load_optional_json, phase_requires, schema_path, validate_schema
from podcast_pipeline_types import GoldenProfiles, PipelineReport, WorkPackageData


def validate_takes(
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
    take_dir = work_dir / "takes/items"
    if take_dir.exists():
        for path in sorted(take_dir.glob("*.json")):
            take = load_optional_json(path, report)
            if take is None:
                continue
            validate_schema(take, schema_path(repo_root, "take_item"), report, path)
            check_identity(take, episode_id, source_id, path, report)
            take_id = str(take.get("id") or "")
            if take_id in data.takes:
                report.error(path, f"duplicate take id: {take_id!r}")
            data.takes[take_id] = take
            if path.name != f"{take_id}.json":
                report.error(path, "take filename must equal '<take_id>.json'.")
            check_active_profiles(take.get("golden_profiles"), profiles, path, report)
            for segment_id in take.get("segment_ids", []):
                if segment_id not in data.segments:
                    report.error(path, f"take references unknown segment_id: {segment_id!r}")
            claim_ids = take.get("claim_ids") if isinstance(take.get("claim_ids"), list) else []
            known_claims = {
                str(claim.get("claim_id"))
                for segment_id in take.get("segment_ids", [])
                for claim in data.segments.get(segment_id, {}).get("substantive_claims", [])
                if isinstance(claim, dict) and claim.get("claim_id")
            }
            for claim_id in claim_ids:
                if claim_id not in known_claims:
                    report.error(path, f"take references claim outside its segments: {claim_id!r}")
            if take.get("source_depth") in {"deep", "structural"} and not take.get("reasoning"):
                report.error(path, "deep or structural take must preserve a non-empty reasoning chain.")
    if (phase_requires(work_status, "takes_complete") or require_ready) and not data.takes:
        report.error(take_dir, "At least one authored take is required when takes_complete is true.")

    if not data.segments:
        return
    planned_take_ids: set[str] = set()
    for segment_id, segment in data.segments.items():
        planned = segment.get("planned_outputs") if isinstance(segment.get("planned_outputs"), dict) else {}
        segment_take_ids = set(planned.get("take_ids", []))
        planned_take_ids.update(segment_take_ids)
        status = segment.get("status") if isinstance(segment.get("status"), dict) else {}
        if not (status.get("takes_complete") or phase_requires(work_status, "takes_complete") or require_ready):
            continue
        for take_id in sorted(segment_take_ids - data.takes.keys()):
            report.error(work_dir, f"segment {segment_id!r} planned take is missing: {take_id!r}")
        covered_dimensions: set[str] = set()
        covered_claims: set[str] = set()
        for take_id in segment_take_ids:
            take = data.takes.get(take_id)
            if not take:
                continue
            if segment_id not in take.get("segment_ids", []):
                report.error(take_dir / f"{take_id}.json", f"planned take does not reference segment {segment_id!r}.")
            covered_dimensions.update(take.get("preserved_dimensions", []))
            covered_claims.update(take.get("claim_ids", []))
        for dimension in sorted(set(segment.get("expected_dimensions", [])) - covered_dimensions):
            report.error(work_dir, f"segment {segment_id!r} expected dimension is not preserved by its takes: {dimension!r}")
        segment_claim_ids = {
            str(claim.get("claim_id"))
            for claim in segment.get("substantive_claims", [])
            if isinstance(claim, dict) and claim.get("claim_id")
        }
        for claim_id in sorted(segment_claim_ids - covered_claims):
            report.error(work_dir, f"segment {segment_id!r} substantive claim is not linked from a take: {claim_id!r}")
    if phase_requires(work_status, "takes_complete") or require_ready:
        for take_id in sorted(data.takes.keys() - planned_take_ids):
            report.error(take_dir / f"{take_id}.json", "take is not planned by any Content Map segment.")
