import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_sleeper_trending.py"
spec = importlib.util.spec_from_file_location("sleeper_trending_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class SleeperTrendingTests(unittest.TestCase):
    def test_build_source_url_uses_documented_parameters(self):
        url = module.build_source_url("add", lookback_hours=24, limit=100)
        parsed = urlparse(url)
        self.assertTrue(parsed.path.endswith("/players/nfl/trending/add"))
        self.assertEqual(
            {"lookback_hours": ["24"], "limit": ["100"]},
            parse_qs(parsed.query),
        )

    def test_validate_payload_assigns_rank_and_rejects_duplicates(self):
        rows = module.validate_activity_payload(
            [
                {"player_id": "11", "count": 50},
                {"player_id": "22", "count": 10},
            ],
            activity_type="add",
            limit=100,
        )
        self.assertEqual(
            [
                {"player_id": "11", "count": 50, "rank": 1},
                {"player_id": "22", "count": 10, "rank": 2},
            ],
            rows,
        )
        with self.assertRaisesRegex(module.SleeperTrendingFetchError, "Duplicate"):
            module.validate_activity_payload(
                [
                    {"player_id": "11", "count": 50},
                    {"player_id": "11", "count": 10},
                ],
                activity_type="add",
                limit=100,
            )

    def test_rejects_negative_or_non_integer_counts(self):
        with self.assertRaisesRegex(module.SleeperTrendingFetchError, "negative"):
            module.validate_activity_payload(
                [{"player_id": "11", "count": -1}],
                activity_type="drop",
                limit=100,
            )
        with self.assertRaisesRegex(module.SleeperTrendingFetchError, "not an integer"):
            module.validate_activity_payload(
                [{"player_id": "11", "count": "5"}],
                activity_type="drop",
                limit=100,
            )

    def test_normalized_union_uses_null_for_not_listed(self):
        players = module.normalize_players(
            {
                "add": [
                    {"player_id": "11", "count": 50, "rank": 1},
                    {"player_id": "22", "count": 10, "rank": 2},
                ],
                "drop": [
                    {"player_id": "22", "count": 7, "rank": 1},
                    {"player_id": "33", "count": 4, "rank": 2},
                ],
            }
        )
        self.assertEqual(
            ["11", "22", "33"], [p["sleeper_player_id"] for p in players]
        )
        self.assertEqual(
            {"status": "not_listed", "rank": None, "count": None},
            players[0]["drop"],
        )
        self.assertEqual("listed", players[1]["add"]["status"])
        self.assertEqual("listed", players[1]["drop"]["status"])

    def test_first_write_is_silent_baseline_and_second_is_comparable(self):
        first = {
            "add": [
                {"player_id": "11", "count": 50, "rank": 1},
                {"player_id": "22", "count": 10, "rank": 2},
            ],
            "drop": [{"player_id": "33", "count": 4, "rank": 1}],
        }
        second = {
            "add": [
                {"player_id": "22", "count": 15, "rank": 1},
                {"player_id": "44", "count": 9, "rank": 2},
            ],
            "drop": [{"player_id": "33", "count": 6, "rank": 1}],
        }

        def make_fetcher(payload):
            def fetcher(activity_type, **kwargs):
                return payload[activity_type], {}, f"https://example.test/{activity_type}"

            return fetcher

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "source"
            paths, latest = module.run_refresh(
                repo_root=Path(directory),
                output_root=output_root,
                fetched_at=datetime(2026, 8, 6, 8, 0, tzinfo=timezone.utc),
                fetcher=make_fetcher(first),
            )
            self.assertEqual(2, len(paths))
            self.assertTrue(latest["comparison"]["baseline"])
            self.assertFalse(latest["comparison"]["material_event_eligible"])

            _, latest2 = module.run_refresh(
                repo_root=Path(directory),
                output_root=output_root,
                fetched_at=datetime(2026, 8, 7, 8, 0, tzinfo=timezone.utc),
                fetcher=make_fetcher(second),
            )
            comparison = latest2["comparison"]
            self.assertFalse(comparison["baseline"])
            self.assertTrue(comparison["comparable"])
            self.assertEqual(
                ["44"], comparison["activity"]["add"]["entered_top_n"]
            )
            self.assertEqual(["11"], comparison["activity"]["add"]["left_top_n"])
            self.assertEqual(
                1, comparison["activity"]["add"]["rank_changed"][0]["rank_delta"]
            )
            self.assertEqual(
                5,
                comparison["activity"]["add"]["count_changed"][0]["count_delta"],
            )
            stored = json.loads(
                (output_root / "latest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(module.ATTRIBUTION, stored["attribution"])

    def test_configuration_change_creates_new_baseline(self):
        previous = {
            "schema_version": module.SCHEMA_VERSION,
            "provider": module.SOURCE_ID,
            "generated_at": "2026-08-06T08:00:00+00:00",
            "lookback_hours": 24,
            "limit": 25,
            "players": [],
        }
        comparison = module.build_comparison(
            previous,
            {
                "add": [{"player_id": "11", "count": 1, "rank": 1}],
                "drop": [{"player_id": "22", "count": 1, "rank": 1}],
            },
            lookback_hours=24,
            limit=100,
        )
        self.assertTrue(comparison["baseline"])
        self.assertEqual(
            "previous_snapshot_configuration_mismatch", comparison["reason"]
        )


if __name__ == "__main__":
    unittest.main()
