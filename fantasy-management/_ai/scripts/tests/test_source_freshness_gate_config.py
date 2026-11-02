from __future__ import annotations

import json
import unittest
from pathlib import Path


class SourceFreshnessGateConfigTests(unittest.TestCase):
    def test_production_gate_uses_success_heartbeats_for_monitored_morning_sources(self) -> None:
        root = Path(__file__).resolve().parents[4]
        config = json.loads(
            (root / "fantasy-management/automation/source-freshness-gate.json").read_text(encoding="utf-8")
        )
        sources = {source["id"]: source for source in config["sources"]}

        self.assertEqual(
            {
                "fantasypros",
                "fantasycalc",
                "fantasy-football-calculator",
                "fftoday",
                "cbs-sports",
                "sleeper-trending",
            },
            set(sources),
        )
        # League and Players are app-owned read-only inputs, not Fantasy Operations freshness sources.
        self.assertNotIn("league", sources)
        self.assertNotIn("players", sources)
        self.assertTrue(all(source["kind"] == "heartbeat" for source in sources.values()))
        self.assertTrue(all(not source["block_monitoring_if_unfresh"] for source in sources.values()))
        self.assertTrue(all(source["required_for_no_event_conclusion"] for source in sources.values()))


    def test_active_entity_observation_uses_shared_readiness_not_app_timestamps(self) -> None:
        root = Path(__file__).resolve().parents[4]
        job = json.loads(
            (root / "fantasy-management/automation/jobs/entity-observation.json").read_text(encoding="utf-8")
        )
        paths = [item["path"] for item in job["dependencies"]]
        self.assertEqual(1, paths.count("fantasy-management/generated/operations/source-freshness.json"))
        self.assertNotIn("public/data/Timestamps.json", paths)
        condition = next(item["condition"] for item in job["dependencies"]
                         if item["path"] == "fantasy-management/generated/operations/source-freshness.json")
        for contract in ("decision=block", "proceed_degraded", "no_event_conclusion_allowed=false"):
            self.assertIn(contract, condition)
        self.assertTrue(job["enabled"])
        self.assertEqual("entity-observation", job["id"])
        self.assertEqual([], job["execution"]["write_scope"])
        self.assertEqual("notification_only", job["output"]["mode"])
        self.assertEqual("material_changes_only", job["notification"]["mode"])

    def test_weekly_review_stays_disabled_with_independent_postfinality_gate_unresolved(self) -> None:
        root = Path(__file__).resolve().parents[4]
        job = json.loads(
            (root / "fantasy-management/automation/jobs/weekly-league-review.json").read_text(encoding="utf-8")
        )
        self.assertFalse(job["enabled"])
        self.assertEqual("canonical_lifecycle", job["trigger"]["source_type"])
        self.assertEqual(60, job["trigger"]["minimum_data_age_minutes"])
        # The weekly league post-finality data proof is not a provider freshness heartbeat.
        # Keep this conservative legacy dependency until an independent replacement exists.
        self.assertIn("public/data/Timestamps.json", {item["path"] for item in job["dependencies"]})
        self.assertTrue(job["trigger"]["retry_when_not_ready"])


if __name__ == "__main__":
    unittest.main()
