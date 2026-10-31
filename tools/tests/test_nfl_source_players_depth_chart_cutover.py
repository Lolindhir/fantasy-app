"""#347 H4: Players.json depth chart fields come from the canonical Sleeper platform snapshot."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data-source" / "nfl" / "platform" / "sleeper" / "players.json"
MODEL = ROOT / "tools" / "derived_data_lib" / "players_read_model.py"


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

    def test_read_model_reads_depth_chart_from_canonical_snapshot(self) -> None:
        source = MODEL.read_text(encoding="utf-8")
        self.assertIn('record.get("DepthChartPosition")', source)
        self.assertIn('record.get("DepthChartOrder")', source)
        self.assertNotIn("depth_chart_position", source)
        self.assertNotIn("depth_chart_order", source)

    def test_read_model_fails_closed_without_snapshot(self) -> None:
        source = MODEL.read_text(encoding="utf-8")
        self.assertIn("Canonical Sleeper players snapshot is required for depth charts", source)


if __name__ == "__main__":
    unittest.main()
