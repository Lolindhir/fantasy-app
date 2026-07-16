import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasypros_redraft_ppr_superflex.py"
spec = importlib.util.spec_from_file_location("fantasypros_redraft_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyProsRedraftFetcherTests(unittest.TestCase):
    def make_data(self, count=160):
        positions = ["QB", "RB", "WR", "TE"]
        counters = {position: 0 for position in positions}
        players = []
        for index in range(1, count + 1):
            position = positions[(index - 1) % len(positions)]
            counters[position] += 1
            players.append(
                {
                    "player_id": 1000 + index,
                    "player_name": f"Player {index}",
                    "player_position_id": position,
                    "player_team_id": "FA",
                    "rank_ecr": index,
                    "rank_min": str(max(1, index - 2)),
                    "rank_max": str(index + 3),
                    "rank_ave": f"{index + 0.25:.2f}",
                    "rank_std": "1.50",
                    "tier": 1 + (index - 1) // 20,
                    "pos_rank": f"{position}{counters[position]}",
                }
            )
        return {
            "sport": "NFL",
            "type": "Draft",
            "ranking_type_name": "draft",
            "year": "2026",
            "week": "0",
            "position_id": "OP",
            "scoring": "PPR",
            "count": count,
            "total_experts": 12,
            "last_updated": "7/15",
            "players": players,
        }

    def make_html(self):
        return f"<html><script>var ecrData = {json.dumps(self.make_data())};</script></html>"

    def test_uses_public_ppr_superflex_redraft_source(self):
        self.assertEqual(
            "https://www.fantasypros.com/nfl/rankings/ppr-superflex-cheatsheets.php",
            module.SOURCE_URL,
        )
        self.assertEqual("redraft-ppr-superflex", module.RANKING_ID)

    def test_rejects_wrong_ranking_identity(self):
        data = self.make_data()
        data["type"] = "Dynasty"
        data["ranking_type_name"] = "dynasty"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "ranking type"):
            module.validate_source_identity(data)

        data = self.make_data()
        data["scoring"] = "HALF"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "scoring"):
            module.validate_source_identity(data)

        data = self.make_data()
        data["position_id"] = "RB"
        with self.assertRaisesRegex(module.FantasyProsFetchError, "position_id"):
            module.validate_source_identity(data)

    def test_reuses_shared_parser_and_writes_redraft_metadata(self):
        data = module.extract_ecr_data(self.make_html())
        module.validate_source_identity(data)
        rows = module.parse_players(data)
        self.assertEqual(160, len(rows))

        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            ranking, raw_data, metadata, latest = module.write_snapshot(
                repo_root=repo_root,
                rows=rows,
                ecr_data=data,
                fetched_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
                response_headers={"etag": "test"},
            )

            with ranking.open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(module.CSV_FIELDS, list(csv_rows[0].keys()))
            self.assertEqual(data, json.loads(raw_data.read_text(encoding="utf-8")))

            metadata_data = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual("redraft-ppr-superflex", metadata_data["ranking_id"])
            self.assertEqual("Redraft PPR Superflex ECR", metadata_data["ranking_name"])
            self.assertFalse(metadata_data["format"]["dynasty"])
            self.assertEqual("single_season", metadata_data["format"]["season_scope"])
            self.assertEqual(
                "current_season_lineup_value",
                metadata_data["analysis_usage"]["primary_use"],
            )
            self.assertEqual(
                module.ANALYSIS_METADATA_FILE,
                metadata_data["analysis_usage"]["comparison_contract"],
            )
            self.assertEqual("Draft", metadata_data["source_published_context"]["type"])

            latest_data = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(module.DIRECT_FETCHER, latest_data["direct_fetcher"])
            self.assertEqual(
                module.ANALYSIS_METADATA_FILE, latest_data["analysis_metadata_file"]
            )

    def test_skip_unchanged_avoids_second_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            html_path = repo_root / "redraft.html"
            html_path.write_text(self.make_html(), encoding="utf-8")

            first = module.main(
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
            second = module.main(
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

            self.assertEqual(0, first)
            self.assertEqual(0, second)
            snapshot_root = module.ranking_root(repo_root) / "snapshots"
            self.assertTrue((snapshot_root / "2026-07-15").is_dir())
            self.assertFalse((snapshot_root / "2026-07-16").exists())


if __name__ == "__main__":
    unittest.main()
