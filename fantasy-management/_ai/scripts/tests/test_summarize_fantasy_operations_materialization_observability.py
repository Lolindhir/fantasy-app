from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def _load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[4]
    spec = importlib.util.spec_from_file_location(name, root / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


observability = _load_module(
    "summarize_fantasy_operations_materialization_observability",
    "fantasy-management/_ai/scripts/summarize_fantasy_operations_materialization_observability.py",
)


class FantasyOperationsMaterializationObservabilityTests(unittest.TestCase):
    def test_source_push_reports_queue_processing_and_end_to_end_latency(self) -> None:
        summary = observability.build_summary(
            event_name="push",
            trigger_reason="relevant_source_or_heartbeat_change",
            trigger_commit_sha="source123",
            trigger_commit_at="2026-08-19T09:09:19Z",
            materializer_started_at="2026-08-19T09:10:00Z",
            published_at="2026-08-19T09:11:40Z",
            published_commit_sha="published456",
            outcome="published",
        )

        self.assertIn("Source-triggered push | `true`", summary)
        self.assertIn("Trigger → materializer start | `41s`", summary)
        self.assertIn("Materializer start → published state | `100s`", summary)
        self.assertIn("Trigger → published state | `141s`", summary)
        self.assertIn("never determine Freshness Gate readiness", summary)

    def test_non_push_run_keeps_unavailable_trigger_latency_explicit(self) -> None:
        summary = observability.build_summary(
            event_name="schedule",
            trigger_reason="scheduled_0645_berlin_catch_up",
            trigger_commit_sha=None,
            trigger_commit_at=None,
            materializer_started_at="2026-08-19T04:45:00Z",
            published_at="2026-08-19T04:46:30Z",
            published_commit_sha="published456",
            outcome="published",
        )

        self.assertIn("Source-triggered push | `false`", summary)
        self.assertIn("Trigger → materializer start | `n/a`", summary)
        self.assertIn("Materializer start → published state | `90s`", summary)
        self.assertIn("Trigger → published state | `n/a`", summary)

    def test_no_change_run_does_not_claim_a_published_state(self) -> None:
        summary = observability.build_summary(
            event_name="workflow_dispatch",
            trigger_reason="manual_materialization",
            trigger_commit_sha=None,
            trigger_commit_at=None,
            materializer_started_at="2026-08-19T08:00:00Z",
            published_at=None,
            published_commit_sha=None,
            outcome="no_changes",
        )

        self.assertIn("Outcome | `no_changes`", summary)
        self.assertIn("Published state commit | `n/a`", summary)
        self.assertIn("Published at | `n/a`", summary)
        self.assertIn("Materializer start → published state | `n/a`", summary)


if __name__ == "__main__":
    unittest.main()
