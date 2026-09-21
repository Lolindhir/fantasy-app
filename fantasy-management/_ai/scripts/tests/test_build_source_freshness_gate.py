from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


def _load_module(name: str, relative_path: str):
    root = Path(__file__).resolve().parents[4]
    spec = importlib.util.spec_from_file_location(name, root / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


freshness = _load_module(
    "build_source_freshness_gate",
    "fantasy-management/_ai/scripts/build_source_freshness_gate.py",
)
heartbeat_writer = _load_module(
    "write_source_refresh_heartbeat",
    "fantasy-management/_ai/scripts/write_source_refresh_heartbeat.py",
)


class SourceFreshnessGateTests(unittest.TestCase):
    NOW = datetime(2026, 8, 18, 4, 45, tzinfo=timezone.utc)  # 06:45 Europe/Berlin (CEST)

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "public/data").mkdir(parents=True)
        (self.root / "fantasy-management/sources/refresh-status").mkdir(parents=True)
        self.config = {
            "schema_version": 2,
            "timezone": "Europe/Berlin",
            "morning_cycle": {
                "refresh_window_start": "05:00",
                "catch_up_time": "06:45",
                "monitoring_time": "07:00",
            },
            "sources": [
                {
                    "id": "league",
                    "label": "League",
                    "kind": "timestamp",
                    "path": "public/data/Timestamps.json",
                    "timestamp_field": "League",
                    "max_age_minutes": 30,
                    "block_monitoring_if_unfresh": True,
                    "required_for_no_event_conclusion": True,
                    "affected_signal_families": ["ownership"],
                },
                {
                    "id": "fantasycalc",
                    "label": "FantasyCalc",
                    "kind": "heartbeat",
                    "path": "fantasy-management/sources/refresh-status/fantasycalc.json",
                    "required_after_local_time": "05:00",
                    "max_age_minutes": 1440,
                    "block_monitoring_if_unfresh": False,
                    "required_for_no_event_conclusion": True,
                    "affected_signal_families": ["dynasty_market"],
                },
            ],
        }

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_schedule(self) -> None:
        path = self.root / "source-data/nfl/schedules/2026.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "Season": 2026,
                    "SourceDataset": "nflverse.schedules",
                    "Finalized": False,
                    "Games": [
                        {"GameID": "2026_01_A_B", "GameType": "REG", "Week": 1, "GameDay": "2026-09-09"},
                        {"GameID": "2026_18_A_B", "GameType": "REG", "Week": 18, "GameDay": "2027-01-10"},
                        {"GameID": "2026_19_A_B", "GameType": "WC", "Week": 19, "GameDay": "2027-01-16"},
                        {"GameID": "2026_22_A_B", "GameType": "SB", "Week": 22, "GameDay": "2027-02-14"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _enable_consumer_activity(self) -> None:
        self.config["domain_context"] = {
            "resolver": "canonical_nfl_schedule",
            "source_root": "source-data/nfl/schedules",
        }
        self.config["consumer_activity"] = {
            "modules": [
                {
                    "id": "free-agent-daily-monitoring",
                    "default_relevance": "required",
                    "phase_policy": {
                        "pre_regular_season": "required",
                        "regular_season": "required",
                        "postseason": "inactive",
                        "post_regular_season": "inactive",
                    },
                },
                {
                    "id": "kicker-daily-monitoring",
                    "default_relevance": "secondary",
                    "phase_policy": {
                        "pre_regular_season": "secondary",
                        "regular_season": "required",
                        "postseason": "inactive",
                        "post_regular_season": "inactive",
                    },
                },
            ]
        }

    def _write_timestamps(self, league: str) -> None:
        (self.root / "public/data/Timestamps.json").write_text(
            json.dumps({"League": league}), encoding="utf-8"
        )

    def _write_heartbeat(
        self,
        *,
        checked_at: str,
        status: str = "success",
        content_changed: bool = False,
        source_id: str = "fantasycalc",
    ) -> None:
        path = self.root / "fantasy-management/sources/refresh-status/fantasycalc.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_id": source_id,
                    "workflow": "FantasyCalc",
                    "status": status,
                    "checked_at": checked_at,
                    "berlin_date": "2026-08-18",
                    "trigger": "schedule",
                    "content_changed": content_changed,
                    "content_paths": ["fantasy-management/sources/external-rankings/market-value/fantasycalc"],
                }
            ),
            encoding="utf-8",
        )

    def test_all_fresh_sources_allow_normal_monitoring(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-18T03:32:00Z", content_changed=False)

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)

        self.assertEqual(2, report["schema_version"])
        self.assertEqual("ok", report["overall_status"])
        self.assertEqual("proceed", report["monitoring"]["decision"])
        self.assertTrue(report["monitoring"]["allowed"])
        self.assertTrue(report["monitoring"]["no_event_conclusion_allowed"])
        self.assertEqual(2, report["population"]["fresh_count"])
        self.assertEqual("06:45", report["morning_cycle"]["catch_up_time"])
        self.assertNotIn("consolidation_time", report["morning_cycle"])

    def test_successful_unchanged_refresh_is_still_fresh(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-18T03:32:00Z", content_changed=False)

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)
        source = next(item for item in report["sources"] if item["id"] == "fantasycalc")

        self.assertEqual("fresh", source["status"])
        self.assertFalse(source["content_changed"])

    def test_missing_external_heartbeat_degrades_and_disallows_zero_event_conclusion(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)

        self.assertEqual("degraded", report["overall_status"])
        self.assertEqual("proceed_degraded", report["monitoring"]["decision"])
        self.assertTrue(report["monitoring"]["allowed"])
        self.assertFalse(report["monitoring"]["no_event_conclusion_allowed"])
        self.assertEqual(["fantasycalc"], report["monitoring"]["unfresh_source_ids"])
        self.assertEqual(["dynasty_market"], report["monitoring"]["affected_signal_families"])

    def test_previous_day_heartbeat_is_stale_even_if_under_generic_age_limit(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-17T05:30:00Z")

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)
        source = next(item for item in report["sources"] if item["id"] == "fantasycalc")

        self.assertEqual("stale", source["status"])
        self.assertEqual("heartbeat_not_from_current_berlin_date", source["reason"])

    def test_same_day_heartbeat_before_morning_window_is_stale(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-18T02:30:00Z")  # 04:30 Berlin

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)
        source = next(item for item in report["sources"] if item["id"] == "fantasycalc")

        self.assertEqual("stale", source["status"])
        self.assertEqual("heartbeat_before_required_morning_window", source["reason"])

    def test_stale_blocking_league_source_blocks_monitoring(self) -> None:
        self._write_timestamps("2026-08-18T03:30:00Z")
        self._write_heartbeat(checked_at="2026-08-18T03:32:00Z")

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)

        self.assertEqual("blocked", report["overall_status"])
        self.assertEqual("block", report["monitoring"]["decision"])
        self.assertFalse(report["monitoring"]["allowed"])
        self.assertFalse(report["monitoring"]["no_event_conclusion_allowed"])
        self.assertEqual(["league"], report["monitoring"]["blocking_source_ids"])

    def test_non_success_heartbeat_is_reported_as_failed(self) -> None:
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-18T03:32:00Z", status="failed")

        report = freshness.evaluate_gate(root=self.root, config=self.config, now=self.NOW)
        source = next(item for item in report["sources"] if item["id"] == "fantasycalc")

        self.assertEqual("failed", source["status"])
        self.assertEqual("latest_heartbeat_not_successful", source["reason"])

    def test_regular_season_secondary_source_does_not_block_no_event_conclusion(self) -> None:
        self._write_schedule()
        self._write_timestamps("2026-09-21T04:35:00Z")
        self.config["domain_context"] = {
            "resolver": "canonical_nfl_schedule",
            "source_root": "source-data/nfl/schedules",
        }
        self.config["sources"][1]["phase_policy"] = {
            "regular_season": {
                "active": True,
                "required_for_no_event_conclusion": False,
            }
        }
        report = freshness.evaluate_gate(
            root=self.root,
            config=self.config,
            now=datetime(2026, 9, 21, 4, 45, tzinfo=timezone.utc),
        )
        self.assertEqual("regular_season", report["domain_context"]["phase"])
        self.assertEqual("degraded", report["overall_status"])
        self.assertEqual("proceed_degraded", report["monitoring"]["decision"])
        self.assertTrue(report["monitoring"]["no_event_conclusion_allowed"])
        self.assertEqual(["fantasycalc"], report["monitoring"]["unfresh_source_ids"])
        source = next(item for item in report["sources"] if item["id"] == "fantasycalc")
        self.assertFalse(source["required_for_no_event_conclusion"])

    def test_postseason_inactive_source_is_removed_from_expected_population(self) -> None:
        self._write_schedule()
        self._write_timestamps("2027-01-20T04:35:00Z")
        self.config["domain_context"] = {
            "resolver": "canonical_nfl_schedule",
            "source_root": "source-data/nfl/schedules",
        }
        self.config["sources"][1]["phase_policy"] = {
            "postseason": {
                "active": False,
                "required_for_no_event_conclusion": False,
            }
        }
        report = freshness.evaluate_gate(
            root=self.root,
            config=self.config,
            now=datetime(2027, 1, 20, 4, 45, tzinfo=timezone.utc),
        )
        self.assertEqual("postseason", report["domain_context"]["phase"])
        self.assertEqual(1, report["population"]["source_count"])
        self.assertEqual("ok", report["overall_status"])
        self.assertEqual(["league"], [item["id"] for item in report["sources"]])

    def test_regular_season_consumer_modules_are_active_ready(self) -> None:
        self._write_schedule()
        self._enable_consumer_activity()
        self._write_timestamps("2026-09-21T04:35:00Z")
        self._write_heartbeat(checked_at="2026-09-21T03:32:00Z")

        report = freshness.evaluate_gate(
            root=self.root,
            config=self.config,
            now=datetime(2026, 9, 21, 4, 45, tzinfo=timezone.utc),
        )

        activity = report["consumer_activity"]
        self.assertEqual("regular_season", activity["phase"])
        self.assertEqual(
            ["free-agent-daily-monitoring", "kicker-daily-monitoring"],
            activity["required_module_ids"],
        )
        self.assertEqual([], activity["inactive_module_ids"])
        self.assertTrue(
            all(item["runtime_status"] == "active_ready" for item in activity["modules"])
        )
        self.assertTrue(
            all(item["execution_allowed"] for item in activity["modules"])
        )

    def test_pre_regular_kicker_monitoring_is_secondary(self) -> None:
        self._write_schedule()
        self._enable_consumer_activity()
        self._write_timestamps("2026-08-18T04:35:00Z")
        self._write_heartbeat(checked_at="2026-08-18T03:32:00Z")

        report = freshness.evaluate_gate(
            root=self.root,
            config=self.config,
            now=self.NOW,
        )

        activity = report["consumer_activity"]
        self.assertEqual("pre_regular_season", activity["phase"])
        self.assertEqual(
            ["free-agent-daily-monitoring"],
            activity["required_module_ids"],
        )
        self.assertEqual(
            ["kicker-daily-monitoring"],
            activity["secondary_module_ids"],
        )
        kicker = next(
            item for item in activity["modules"] if item["id"] == "kicker-daily-monitoring"
        )
        self.assertEqual("active_ready", kicker["runtime_status"])
        self.assertTrue(kicker["execution_allowed"])

    def test_postseason_monitoring_modules_short_circuit_as_inactive_by_policy(self) -> None:
        self._write_schedule()
        self._enable_consumer_activity()
        self._write_timestamps("2027-01-20T04:35:00Z")

        report = freshness.evaluate_gate(
            root=self.root,
            config=self.config,
            now=datetime(2027, 1, 20, 4, 45, tzinfo=timezone.utc),
        )

        activity = report["consumer_activity"]
        self.assertEqual("postseason", activity["phase"])
        self.assertEqual(
            ["free-agent-daily-monitoring", "kicker-daily-monitoring"],
            activity["inactive_module_ids"],
        )
        for item in activity["modules"]:
            self.assertEqual("inactive_by_policy", item["runtime_status"])
            self.assertFalse(item["execution_allowed"])
            self.assertIsNone(item["no_event_conclusion_allowed"])

    def test_heartbeat_writer_records_success_without_equating_unchanged_with_failure(self) -> None:
        heartbeat = heartbeat_writer.build_heartbeat(
            source_id="fantasycalc",
            workflow="FM • Ranking • FantasyCalc Market",
            trigger="schedule",
            content_paths=["some/source/path"],
            content_changed=False,
            checked_at=datetime(2026, 8, 18, 3, 32, tzinfo=timezone.utc),
        )

        self.assertEqual("success", heartbeat["status"])
        self.assertFalse(heartbeat["content_changed"])
        self.assertEqual("2026-08-18", heartbeat["berlin_date"])


if __name__ == "__main__":
    unittest.main()
