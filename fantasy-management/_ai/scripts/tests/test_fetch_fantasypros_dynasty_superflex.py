import csv
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
    def make_data(self, count=160, *, include_position_rank=True):
        players = []
        positions = ["QB", "RB", "WR", "TE"]
        counters = {position: 0 for position in positions}
        for index in range(1, count + 1):
            position = positions[(index - 1) % len(positions)]
            counters[position] += 1
            player = {
                "player_id": 1000 + index,
                "player_name": f"Player {index}",
                "player_position_id": position,
                "player_team_id": "FA",
                "rank_ecr": index,
                "rank_min": max(1, index - 2),
                "rank_max": index + 3,
            }
            if include_position_rank:
                player["pos_rank"] = f"{position}{counters[position]}"
            players.append(player)
        return {
            "players": players,
            "note": "brace } inside string",
            "experts": [{"id": 1, "name": "Example Expert"}],
        }

    def make_html(self, count=160, *, include_position_rank=True):
        payload = json.dumps(self.make_data(count, include_position_rank=include_position_rank))
        return f"<html><script>var ecrData = {payload};</script></html>"

    def test_extract_and_parse_preserves_normalized_fields(self):
        rows = module.parse_players(module.extract_ecr_data(self.make_html()))
        self.assertEqual(160, len(rows))
        self.assertEqual("Player 1", rows[0]["name"])
        self.assertEqual(160, rows[-1]["Rank"])
        self.assertEqual("QB1", rows[0]["position_rank"])
        self.assertEqual("1001", rows[0]["source_player_id"])
        self.assertEqual("source", rows[0]["position_rank_source"])

    def test_derives_position_rank_when_source_field_is_missing(self):
        rows = module.parse_players(
            module.extract_ecr_data(self.make_html(include_position_rank=False))
        )
        self.assertEqual("QB1", rows[0]["position_rank"])
        self.assertEqual("RB1", rows[1]["position_rank"])
        self.assertEqual("QB2", rows[4]["position_rank"])
        self.assertEqual("derived", rows[0]["position_rank_source"])

    def test_rejects_too_few_rows(self):
        with self.assertRaises(module.FantasyProsFetchError):
            module.parse_players(module.extract_ecr_data(self.make_html(20)))

    def test_writes_csv_raw_payload_metadata_and_latest_pointer(self):
        data = module.extract_ecr_data(self.make_html())
        rows = module.parse_players(data)
        fetched_at = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            ranking, raw_data, metadata, latest = module.write_snapshot(
                repo_root=repo_root,
                rows=rows,
                ecr_data=data,
                fetched_at=fetched_at,
                response_headers={"etag": "test"},
            )

            self.assertTrue(ranking.exists())
            self.assertEqual(data, json.loads(raw_data.read_text(encoding="utf-8")))

            with ranking.open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual("QB1", csv_rows[0]["position_rank"])
            self.assertEqual("1001", csv_rows[0]["source_player_id"])

            metadata_data = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(160, metadata_data["snapshot"]["row_count"])
            self.assertEqual("raw-ecr-data.json", metadata_data["snapshot"]["raw_data_file"])
            self.assertIn("rank_min", metadata_data["raw_schema"]["player_field_names"])
            self.assertEqual(160, metadata_data["raw_schema"]["player_count"])

            latest_data = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual("live_fetch", latest_data["freshness_status"])
            self.assertTrue(latest_data["raw_data_file"].endswith("raw-ecr-data.json"))


if __name__ == "__main__":
    unittest.main()
