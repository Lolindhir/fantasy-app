import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
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
            rank_min = max(1, index - 2)
            rank_max = index + 3
            player = {
                "player_id": 1000 + index,
                "player_name": f"Player {index}",
                "player_position_id": position,
                "player_team_id": "FA",
                "rank_ecr": index,
                "rank_min": str(rank_min),
                "rank_max": str(rank_max),
                "rank_ave": f"{index + 0.25:.2f}",
                "rank_std": "1.50",
                "tier": 1 + (index - 1) // 20,
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
        self.assertEqual(1, rows[0]["tier"])
        self.assertEqual(1, rows[0]["rank_min"])
        self.assertEqual(4, rows[0]["rank_max"])
        self.assertEqual(Decimal("1.25"), rows[0]["rank_ave"])
        self.assertEqual(Decimal("1.50"), rows[0]["rank_std"])

    def test_derives_position_rank_when_source_field_is_missing(self):
        rows = module.parse_players(
            module.extract_ecr_data(self.make_html(include_position_rank=False))
        )
        self.assertEqual("QB1", rows[0]["position_rank"])
        self.assertEqual("RB1", rows[1]["position_rank"])
        self.assertEqual("QB2", rows[4]["position_rank"])
        self.assertEqual("derived", rows[0]["position_rank_source"])

    def test_allows_missing_optional_consensus_fields(self):
        data = self.make_data()
        for field in module.CONSENSUS_FIELDS:
            data["players"][0][field] = None
        rows = module.parse_players(data)
        for field in module.CONSENSUS_FIELDS:
            self.assertEqual("", rows[0][field])
        coverage = module.consensus_field_coverage(rows)
        self.assertEqual(159, coverage["tier"])
        self.assertEqual(159, coverage["rank_std"])

    def test_rejects_inconsistent_rank_range(self):
        data = self.make_data()
        data["players"][0]["rank_min"] = "5"
        data["players"][0]["rank_max"] = "3"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "rank_min exceeds rank_max"):
            module.parse_players(data)

    def test_rejects_average_outside_rank_range(self):
        data = self.make_data()
        data["players"][0]["rank_ave"] = "9.00"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "rank_ave is outside"):
            module.parse_players(data)

    def test_rejects_negative_standard_deviation(self):
        data = self.make_data()
        data["players"][0]["rank_std"] = "-0.01"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "rank_std"):
            module.parse_players(data)

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
            self.assertEqual(module.CSV_FIELDS, list(csv_rows[0].keys()))
            self.assertEqual("QB1", csv_rows[0]["position_rank"])
            self.assertEqual("1", csv_rows[0]["tier"])
            self.assertEqual("1", csv_rows[0]["rank_min"])
            self.assertEqual("4", csv_rows[0]["rank_max"])
            self.assertEqual("1.25", csv_rows[0]["rank_ave"])
            self.assertEqual("1.50", csv_rows[0]["rank_std"])
            self.assertEqual("1001", csv_rows[0]["source_player_id"])

            metadata_data = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(module.SCHEMA_VERSION, metadata_data["schema_version"])
            self.assertEqual(160, metadata_data["snapshot"]["row_count"])
            self.assertEqual("raw-ecr-data.json", metadata_data["snapshot"]["raw_data_file"])
            self.assertEqual(160, metadata_data["snapshot"]["consensus_field_coverage"]["tier"])
            self.assertIn("rank_min", metadata_data["raw_schema"]["player_field_names"])
            self.assertEqual(160, metadata_data["raw_schema"]["player_count"])

            latest_data = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(module.SCHEMA_VERSION, latest_data["schema_version"])
            self.assertEqual("live_fetch", latest_data["freshness_status"])
            self.assertTrue(latest_data["raw_data_file"].endswith("raw-ecr-data.json"))

    def test_skip_unchanged_avoids_second_snapshot(self):
        html = self.make_html()
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            html_path = repo_root / "fantasypros.html"
            html_path.write_text(html, encoding="utf-8")

            first_result = module.main(
                [
                    "--from-file",
                    str(html_path),
                    "--repo-root",
                    str(repo_root),
                    "--fetched-at",
                    "2026-07-15T08:00:00Z",
                    "--skip-unchanged",
                ]
            )
            second_result = module.main(
                [
                    "--from-file",
                    str(html_path),
                    "--repo-root",
                    str(repo_root),
                    "--fetched-at",
                    "2026-07-16T08:00:00Z",
                    "--skip-unchanged",
                ]
            )

            self.assertEqual(0, first_result)
            self.assertEqual(0, second_result)
            snapshot_root = module.ranking_root(repo_root) / "snapshots"
            self.assertTrue((snapshot_root / "2026-07-15").is_dir())
            self.assertFalse((snapshot_root / "2026-07-16").exists())

    def test_schema_change_forces_snapshot_even_when_raw_payload_matches(self):
        data = self.make_data()
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            module.write_snapshot(
                repo_root=repo_root,
                rows=module.parse_players(data),
                ecr_data=data,
                fetched_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
                response_headers={},
            )
            latest = json.loads(
                (module.ranking_root(repo_root) / "latest.json").read_text(encoding="utf-8")
            )
            metadata_path = repo_root / latest["metadata_file"]
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["schema_version"] = module.SCHEMA_VERSION - 1
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            self.assertTrue(module.snapshot_needs_refresh(repo_root=repo_root, ecr_data=data))

    def test_changed_payload_publishes_new_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            first_data = self.make_data()
            module.write_snapshot(
                repo_root=repo_root,
                rows=module.parse_players(first_data),
                ecr_data=first_data,
                fetched_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
                response_headers={},
            )

            changed_data = self.make_data()
            changed_data["players"][0]["rank_std"] = "1.51"
            self.assertTrue(
                module.snapshot_needs_refresh(repo_root=repo_root, ecr_data=changed_data)
            )
            self.assertFalse(
                module.snapshot_needs_refresh(repo_root=repo_root, ecr_data=first_data)
            )


if __name__ == "__main__":
    unittest.main()
