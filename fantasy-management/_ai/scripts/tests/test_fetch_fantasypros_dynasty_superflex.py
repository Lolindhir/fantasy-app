import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasypros_dynasty_superflex.py"
spec = importlib.util.spec_from_file_location("fantasypros_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyProsFetcherTests(unittest.TestCase):
    def make_html(self, count=160):
        players = []
        positions = ["QB", "RB", "WR", "TE"]
        for index in range(1, count + 1):
            players.append(
                {
                    "player_name": f"Player {index}",
                    "player_position_id": positions[(index - 1) % len(positions)],
                    "player_team_id": "FA",
                    "rank_ecr": index,
                }
            )
        payload = json.dumps({"players": players, "note": "brace } inside string"})
        return f"<html><script>var ecrData = {payload};</script></html>"

    def test_extract_and_parse(self):
        rows = module.parse_players(module.extract_ecr_data(self.make_html()))
        self.assertEqual(160, len(rows))
        self.assertEqual("Player 1", rows[0]["name"])
        self.assertEqual(160, rows[-1]["Rank"])

    def test_rejects_too_few_rows(self):
        with self.assertRaises(module.FantasyProsFetchError):
            module.parse_players(module.extract_ecr_data(self.make_html(20)))

    def test_writes_snapshot_and_latest_pointer(self):
        rows = module.parse_players(module.extract_ecr_data(self.make_html()))
        fetched_at = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            ranking, metadata, latest = module.write_snapshot(
                repo_root=repo_root,
                rows=rows,
                fetched_at=fetched_at,
                response_headers={"etag": "test"},
            )
            self.assertTrue(ranking.exists())
            self.assertEqual(160, json.loads(metadata.read_text())["snapshot"]["row_count"])
            self.assertEqual("live_fetch", json.loads(latest.read_text())["freshness_status"])


if __name__ == "__main__":
    unittest.main()
