"""Synthetic podcast work-package fixtures for pipeline tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def create_ready_work_package(root: Path) -> Path:
    work = root / "fantasy-management/podcast-work/test-source/2026/test-0001"
    (work / "raw").mkdir(parents=True, exist_ok=True)
    (work / "raw/manifest.md").write_text("# Raw manifest\n\n- `part01.md`\n", encoding="utf-8")
    (work / "raw/part01.md").write_text("[00:00:01] Test Player is discussed in detail.\n", encoding="utf-8")

    write_json(work / "work-status.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "year": 2026,
        "phase": "ready_for_publish",
        "gates": {
            "raw_complete": True,
            "content_map_complete": True,
            "takes_complete": True,
            "article_complete": True,
            "mention_audit_complete": True,
            "content_map_reconciled": True,
            "process_review_complete": True,
            "ready_for_publish": True
        },
        "blockers": [],
        "phase_history": [{"phase": "ready_for_publish", "recorded_at": "2026-07-25T05:00:00Z"}],
        "notes": []
    })

    write_json(work / "content-map/manifest.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "status": "complete",
        "golden_profiles": ["player-evaluation", "ranking"],
        "segment_count": 1,
        "segments": [{
            "segment_id": "segment-001",
            "order": 1,
            "path": "content-map/segments/segment-001.json",
            "segment_type": "player_ranking",
            "source_depth": "deep"
        }],
        "notes": []
    })

    write_json(work / "content-map/segments/segment-001.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "segment_id": "segment-001",
        "order": 1,
        "title": "Test player analysis",
        "segment_type": "player_ranking",
        "source_depth": "deep",
        "source_range": {"raw_parts": ["raw/part01.md"], "timestamp_start": "00:00:01", "timestamp_end": "00:05:00"},
        "primary_subjects": [{"ref_id": "subject-player", "type": "player", "entity": "Test Player"}],
        "related_subjects": [],
        "substantive_claims": [{
            "claim_id": "claim-player-value",
            "claim": "Test Player has a strong long-term profile but carries role risk.",
            "subject_refs": ["subject-player"],
            "conditions": [],
            "uncertainties": ["Immediate workload is uncertain."]
        }],
        "reasoning_obligations": ["Preserve the college background and the role-risk argument."],
        "expected_dimensions": ["background_development", "positive_case", "negative_case", "role_opportunity"],
        "host_differences": [],
        "uncertainties": ["Immediate workload is uncertain."],
        "golden_profiles": ["player-evaluation", "ranking"],
        "planned_outputs": {
            "take_ids": ["take-test-player"],
            "take_types": ["player_evaluation"],
            "article_section_ids": ["section-player"],
            "mention_segment_id": "segment-001"
        },
        "status": {
            "mapped": True,
            "takes_complete": True,
            "article_complete": True,
            "mention_audit_complete": True,
            "reconciled": True
        },
        "notes": []
    })

    write_json(work / "takes/items/take-test-player.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "id": "take-test-player",
        "category": "players",
        "type": "player_evaluation",
        "source_depth": "deep",
        "segment_ids": ["segment-001"],
        "claim_ids": ["claim-player-value"],
        "primary_subject": {"type": "player", "entity": "Test Player", "raw_mentions": ["Test Player"]},
        "related_subjects": [],
        "raw_entity_mention": "Test Player",
        "entity": "Test Player",
        "team": "TST",
        "position": "RB",
        "entity_resolution": {"status": "confirmed", "method": "manual_confirmation", "confidence": "high"},
        "formats": ["dynasty"],
        "podcast_take": "Test Player has a strong long-term profile but carries role risk.",
        "background": ["The source describes a productive college history."],
        "reasoning": ["The source combines college production with an uncertain immediate workload."],
        "positive_case": ["Strong long-term talent case."],
        "negative_case": ["Immediate touches are not guaranteed."],
        "risks": ["Role uncertainty."],
        "conditions": [],
        "uncertainties": ["Immediate workload is uncertain."],
        "role_and_context": ["The player may begin in a committee."],
        "market_context": [],
        "time_horizon": ["Long-term dynasty value is stronger than immediate redraft value."],
        "format_distinctions": [{"format": "dynasty", "source_view": "Positive long-term profile."}],
        "host_views": [],
        "comparisons": [],
        "preserved_dimensions": ["background_development", "positive_case", "negative_case", "role_opportunity"],
        "golden_profiles": ["player-evaluation", "ranking"],
        "sentiment": "positive_with_risk",
        "conviction": "medium",
        "tags": ["rookie", "role-risk"],
        "evidence": [{"timestamp_start": "00:00:01", "timestamp_end": "00:05:00", "raw_part": "raw/part01.md"}],
        "notes": []
    })

    (work / "article/sections").mkdir(parents=True, exist_ok=True)
    (work / "article/sections/010-player.md").write_text(
        "# Test Episode\n\n## Test Player\n\nDer Podcast beschreibt ausführlich die College-Historie, den positiven Langzeit-Case und das unmittelbare Rollenrisiko.\n",
        encoding="utf-8"
    )
    write_json(work / "article/manifest.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "title": "Synthetic Test Episode",
        "language": "de",
        "output_path": "episode.md",
        "section_count": 1,
        "sections": [{
            "section_id": "section-player",
            "order": 1,
            "path": "article/sections/010-player.md",
            "segment_ids": ["segment-001"],
            "take_ids": ["take-test-player"],
            "heading_level": 1
        }],
        "status": "complete",
        "notes": []
    })

    write_json(work / "mentions/segments/segment-001.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "segment_id": "segment-001",
        "audit_pass": "independent_second_pass",
        "status": "complete",
        "mentions": [{
            "id": "mention-test-player",
            "entity_type": "player",
            "raw_entity_mentions": ["Test Player"],
            "entity": "Test Player",
            "entity_resolution": {"status": "confirmed", "method": "manual_confirmation", "confidence": "high"},
            "mention_types": ["ranking_subject", "substantive_take"],
            "occurrences": [{"timestamp_start": "00:00:01", "timestamp_end": "00:05:00", "section": "segment-001", "context_summary": "Detailed player discussion."}],
            "coverage": {
                "episode_md": True,
                "episode_md_section": "section-player",
                "standalone_take_required": True,
                "subject_take_ids": ["take-test-player"],
                "context_take_ids": [],
                "note": None
            }
        }],
        "notes": []
    })

    write_json(work / "process-review/improvement-proposals.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "review_status": "complete",
        "evaluated_profiles": ["player-evaluation", "ranking"],
        "findings": [],
        "improvement_proposals": [],
        "explicit_no_proposals": True,
        "summary": "No pipeline extensions were required for the synthetic package.",
        "notes": []
    })

    write_json(work / "publish-request.json", {
        "pipeline_schema_version": 1,
        "episode_id": "test-0001",
        "source_id": "test-source",
        "source_name": "Synthetic Source",
        "year": 2026,
        "episode_number": 1,
        "title": "Synthetic Test Episode",
        "published_date": "2026-07-24",
        "processed_date": "2026-07-25",
        "language": "de",
        "status": "ready_for_publish",
        "target_package_path": "fantasy-management/sources/podcasts/test-source/episodes/2026/test-0001",
        "package_schema_version": 2,
        "notes": []
    })
    return work
