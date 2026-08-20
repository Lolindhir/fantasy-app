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


if __name__ == "__main__":
    unittest.main()
