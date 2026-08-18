from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "resolve_fantasy_operations_materialization_trigger.py"
SPEC = importlib.util.spec_from_file_location("resolve_fantasy_operations_materialization_trigger", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

BERLIN = ZoneInfo("Europe/Berlin")


class MaterializationTriggerTests(unittest.TestCase):
    def test_correct_dst_schedule_runs_and_companion_skips(self) -> None:
        summer = datetime(2026, 8, 17, 6, 45, tzinfo=BERLIN)
        winter = datetime(2026, 12, 17, 6, 45, tzinfo=BERLIN)

        self.assertTrue(
            MODULE.decide(
                event_name="schedule",
                schedule_expression="45 4 * * *",
                now=summer,
            ).run
        )
        self.assertFalse(
            MODULE.decide(
                event_name="schedule",
                schedule_expression="45 5 * * *",
                now=summer,
            ).run
        )
        self.assertTrue(
            MODULE.decide(
                event_name="schedule",
                schedule_expression="45 5 * * *",
                now=winter,
            ).run
        )

    def test_external_source_only_push_is_batched_during_morning_window(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-rankings/market-value/fantasycalc/latest.json",
                "fantasy-management/sources/external-rankings/market-value/fantasycalc/snapshots/2026-08-17.json",
            ],
            now=datetime(2026, 8, 17, 5, 32, tzinfo=BERLIN),
        )
        self.assertFalse(decision.run)
        self.assertEqual(decision.reason, "batched_external_source_change_before_0645")

    def test_refresh_heartbeat_is_batched_with_external_source_during_morning_window(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/refresh-status/fantasycalc.json",
            ],
            now=datetime(2026, 8, 17, 5, 32, tzinfo=BERLIN),
        )
        self.assertFalse(decision.run)
        self.assertEqual(decision.reason, "batched_external_source_change_before_0645")

    def test_external_source_only_push_runs_immediately_after_batch_window(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-signals/roster-activity/sleeper/latest.json"
            ],
            now=datetime(2026, 8, 17, 6, 46, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "external_source_change_outside_morning_batch_window")

    def test_external_source_only_push_runs_immediately_before_batch_window(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-rankings/expert-consensus/fantasypros/latest.json"
            ],
            now=datetime(2026, 8, 17, 4, 59, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)

    def test_league_or_mixed_change_always_runs_immediately(self) -> None:
        league = MODULE.decide(
            event_name="push",
            changed_files=["public/data/League.json"],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        mixed = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-rankings/expert-consensus/fantasypros/latest.json",
                "public/data/Timestamps.json",
            ],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        self.assertTrue(league.run)
        self.assertTrue(mixed.run)
        self.assertEqual(mixed.reason, "immediate_non_external_input_change")

    def test_manual_materializer_dispatch_always_runs(self) -> None:
        decision = MODULE.decide(
            event_name="workflow_dispatch",
            changed_files=[],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "manual_materialization")

    def test_missing_push_diff_fails_open_to_materialization(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "push_without_changed_file_context")


if __name__ == "__main__":
    unittest.main()
