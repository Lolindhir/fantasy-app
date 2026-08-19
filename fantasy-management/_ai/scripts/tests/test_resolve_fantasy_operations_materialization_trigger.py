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
    def test_correct_dst_catch_up_schedule_runs_and_companion_skips(self) -> None:
        summer = datetime(2026, 8, 17, 6, 45, tzinfo=BERLIN)
        winter = datetime(2026, 12, 17, 6, 45, tzinfo=BERLIN)

        summer_decision = MODULE.decide(
            event_name="schedule",
            schedule_expression="45 4 * * *",
            now=summer,
        )
        self.assertTrue(summer_decision.run)
        self.assertEqual(summer_decision.reason, "scheduled_0645_berlin_catch_up")
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

    def test_relevant_source_push_runs_immediately_at_0530(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-rankings/market-value/fantasycalc/latest.json",
                "fantasy-management/sources/external-rankings/market-value/fantasycalc/snapshots/2026-08-17.json",
            ],
            now=datetime(2026, 8, 17, 5, 30, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "relevant_source_or_heartbeat_change")

    def test_relevant_heartbeat_push_runs_immediately_at_0630(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=["fantasy-management/sources/refresh-status/sleeper-trending.json"],
            now=datetime(2026, 8, 17, 6, 30, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "relevant_source_or_heartbeat_change")

    def test_relevant_source_push_runs_immediately_outside_former_morning_window(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/sources/external-signals/roster-activity/sleeper/latest.json"
            ],
            now=datetime(2026, 8, 17, 14, 15, tzinfo=BERLIN),
        )
        self.assertTrue(decision.run)
        self.assertEqual(decision.reason, "relevant_source_or_heartbeat_change")

    def test_league_players_and_timestamps_inputs_run_immediately(self) -> None:
        for path in (
            "public/data/League.json",
            "public/data/Players.json",
            "public/data/Timestamps.json",
        ):
            with self.subTest(path=path):
                decision = MODULE.decide(
                    event_name="push",
                    changed_files=[path],
                    now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
                )
                self.assertTrue(decision.run)
                self.assertEqual(decision.reason, "relevant_league_or_player_input_change")

    def test_generated_operations_only_push_does_not_retrigger_materializer(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=[
                "fantasy-management/generated/operations/source-freshness.json",
                "fantasy-management/generated/operations/player-signals.json",
            ],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        self.assertFalse(decision.run)
        self.assertEqual(decision.reason, "generated_operations_only_change")

    def test_irrelevant_push_does_not_materialize(self) -> None:
        decision = MODULE.decide(
            event_name="push",
            changed_files=["README.md"],
            now=datetime(2026, 8, 17, 5, 40, tzinfo=BERLIN),
        )
        self.assertFalse(decision.run)
        self.assertEqual(decision.reason, "irrelevant_push")

    def test_pull_request_context_never_requests_production_materialization(self) -> None:
        decision = MODULE.decide(
            event_name="pull_request",
            changed_files=["fantasy-management/sources/refresh-status/fantasycalc.json"],
            now=datetime(2026, 8, 17, 5, 32, tzinfo=BERLIN),
        )
        self.assertFalse(decision.run)
        self.assertEqual(decision.reason, "pull_request_validation_only")

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
