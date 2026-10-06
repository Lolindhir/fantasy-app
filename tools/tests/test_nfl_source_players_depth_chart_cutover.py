"""#347 H4: Players.json depth chart fields come from the canonical Sleeper platform snapshot."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "source-data" / "nfl" / "platform" / "sleeper" / "players.json"
GENERATOR = ROOT / "public" / "requests" / "RequestPlayers.ps1"
MODULE = ROOT / "public" / "requests" / "utils" / "player" / "SleeperPlatformUtils.psm1"


class PlayersDepthChartCutoverTests(unittest.TestCase):
    def test_snapshot_carries_unique_ids_and_depth_fields(self) -> None:
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["SourceDataset"], "sleeper.players")
        self.assertEqual(snapshot["SchemaVersion"], 2)
        records = snapshot["Records"]
        self.assertTrue(records)
        ids = [r["SleeperPlayerID"] for r in records]
        self.assertEqual(len(ids), len(set(ids)))
        for record in records:
            self.assertIn("DepthChartPosition", record)
            self.assertIn("DepthChartOrder", record)

    def test_generator_reads_depth_chart_from_canonical_snapshot(self) -> None:
        source = GENERATOR.read_text(encoding="utf-8")
        self.assertIn("SleeperPlatformUtils.psm1", source)
        self.assertIn("Get-CanonicalSleeperDepthCharts", source)
        self.assertNotRegex(source, r"\$sleeperEntry\.depth_chart_(position|order)")
        self.assertRegex(source, r"SleeperDepthChartPosition\s*=\s*\$depthChart\.Position")
        self.assertRegex(source, r"SleeperDepthChartOrder\s*=\s*\$depthChart\.Order")

    def test_module_fails_closed(self) -> None:
        module = MODULE.read_text(encoding="utf-8")
        self.assertRegex(module, r"throw .*is required for depth charts")
        self.assertIn("lists SleeperPlayerID", module)
        self.assertIn("Unexpected canonical Sleeper players source", module)


if __name__ == "__main__":
    unittest.main()
