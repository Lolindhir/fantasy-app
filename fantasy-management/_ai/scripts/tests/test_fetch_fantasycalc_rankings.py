import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasycalc_rankings.py"
spec = importlib.util.spec_from_file_location("fantasycalc_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyCalcFetcherTests(unittest.TestCase):
    def make_payload(
        self,
        *,
        dynasty: bool,
        change_value: bool = False,
        raw_note: str = "a",
        duplicate_source_rank: bool = False,
    ):
        positions = ["QB", "RB", "WR", "TE"]
        payload = []
        rank = 1
        for index in range(1, 121):
            position = positions[(index - 1) % len(positions)]
            source_rank = rank
            if duplicate_source_rank and index == 11:
                source_rank = 10
            payload.append(
                {
                    "player": {
                        "id": 1000 + index,
                        "name": f"Player {index}",
                        "position": position,
                        "maybeTeam": "FA",
                        "sleeperId": str(5000 + index),
                        "mflId": str(6000 + index),
                        "espnId": str(7000 + index),
                        "maybeAge": 20 + index / 100,
                        "maybeYoe": index % 8,
                    },
                    "value": 9000 - index - (1 if change_value and index == 1 else 0),
                    "overallRank": source_rank,
                    "positionRank": 1 + (index - 1) // 4,
                    "trend30Day": index % 7 - 3,
                    "redraftValue": 5000 - index,
                    "combinedValue": 7000 - index,
                    "redraftDynastyValueDifference": -100,
                    "redraftDynastyValuePercDifference": -2,
                    "maybeTier": 1 + (index - 1) // 20,
                    "maybeAdp": index + 0.25,
                    "maybeTradeFrequency": 0.5,
                    "maybeRosterPercent": 99.0,
                    "starter": index <= 40,
                    "rawNote": raw_note,
                }
            )
            rank += 1
        if dynasty:
            for pick_index in range(1, 7):
                payload.append(
                    {
                        "player": {
                            "id": 9000 + pick_index,
                            "name": f"2027 Round {pick_index}",
                            "position": "PICK",
                            "sleeperId": f"FP_2027_{pick_index}",
                        },
                        "value": 4000 - pick_index,
                        "overallRank": rank,
                        "positionRank": pick_index,
                        "trend30Day": 0,
                        "starter": False,
                        "rawNote": raw_note,
                    }
                )
                rank += 1
        return payload

    def test_uses_eight_team_proxy_without_tep(self):
        config = module.FORMAT_CONFIGS["dynasty"]
        params = module.request_parameters(config)
        self.assertEqual(6, module.ACTUAL_LEAGUE_TEAMS)
        self.assertEqual("8", params["numTeams"])
        self.assertEqual("2", params["numQbs"])
        self.assertEqual("1", params["ppr"])
        self.assertNotIn("tep", params)
        query = parse_qs(urlparse(module.build_source_url(config)).query)
        self.assertEqual(["8"], query["numTeams"])

    def test_normalizes_dynasty_players_and_picks(self):
        rows = module.parse_assets(
            self.make_payload(dynasty=True), module.FORMAT_CONFIGS["dynasty"]
        )
        self.assertEqual(126, len(rows))
        self.assertEqual("player", rows[0]["asset_type"])
        self.assertEqual("draft_pick", rows[-1]["asset_type"])
        self.assertEqual("5001", rows[0]["sleeper_id"])
        self.assertEqual(1, rows[0]["Rank"])
        self.assertEqual(1, rows[0]["source_overall_rank"])

    def test_accepts_duplicate_source_ranks_and_assigns_unique_normalized_ranks(self):
        rows = module.parse_assets(
            self.make_payload(dynasty=True, duplicate_source_rank=True),
            module.FORMAT_CONFIGS["dynasty"],
        )
        tied = [row for row in rows if row["source_overall_rank"] == 10]
        self.assertEqual(2, len(tied))
        self.assertEqual([10, 11], [row["Rank"] for row in tied])
        self.assertGreaterEqual(tied[0]["value"], tied[1]["value"])
        self.assertEqual(len(rows), len({row["Rank"] for row in rows}))
        diagnostics = module.source_rank_diagnostics(rows)
        self.assertFalse(diagnostics["source_overall_rank_unique"])
        self.assertEqual(1, diagnostics["duplicate_source_rank_group_count"])
        self.assertEqual(2, diagnostics["duplicate_source_rank_row_count"])

    def test_rejects_picks_in_redraft(self):
        with self.assertRaisesRegex(module.FantasyCalcFetchError, "Redraft"):
            module.parse_assets(
                self.make_payload(dynasty=True), module.FORMAT_CONFIGS["redraft"]
            )

    def test_raw_is_latest_only_and_unchanged_ranking_is_not_archived_again(self):
        config = module.FORMAT_CONFIGS["dynasty"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            first_payload = self.make_payload(
                dynasty=True, raw_note="first", duplicate_source_rank=True
            )
            first_rows = module.parse_assets(first_payload, config)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=first_rows,
                payload=first_payload,
                config=config,
                fetched_at=datetime(2026, 7, 17, 6, 0, tzinfo=timezone.utc),
                source_url=module.build_source_url(config),
                response_headers={},
                skip_unchanged=True,
            )
            self.assertTrue(created)
            self.assertEqual(4, len(paths))

            second_payload = self.make_payload(
                dynasty=True, raw_note="second", duplicate_source_rank=True
            )
            second_rows = module.parse_assets(second_payload, config)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=second_rows,
                payload=second_payload,
                config=config,
                fetched_at=datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc),
                source_url=module.build_source_url(config),
                response_headers={},
                skip_unchanged=True,
            )
            self.assertFalse(created)
            self.assertEqual(2, len(paths))
            root = module.ranking_root(repo_root, config)
            self.assertTrue((root / "snapshots" / "2026-07-17" / "ranking.csv").is_file())
            self.assertFalse((root / "snapshots" / "2026-07-18").exists())
            raw = json.loads((root / "raw-latest.json").read_text(encoding="utf-8"))
            self.assertEqual("second", raw[0]["rawNote"])
            latest = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-07-17", latest["snapshot_date"])
            self.assertEqual("2026-07-18T06:00:00+00:00", latest["raw_fetched_at"])
            metadata = json.loads(
                (root / "snapshots" / "2026-07-17" / "metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(2, metadata["schema_version"])
            self.assertEqual(
                1,
                metadata["snapshot"]["rank_diagnostics"][
                    "duplicate_source_rank_group_count"
                ],
            )

    def test_changed_ranking_creates_new_normalized_snapshot(self):
        config = module.FORMAT_CONFIGS["redraft"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            first = self.make_payload(dynasty=False)
            module.write_format(
                repo_root=repo_root,
                rows=module.parse_assets(first, config),
                payload=first,
                config=config,
                fetched_at=datetime(2026, 7, 17, 6, 0, tzinfo=timezone.utc),
                source_url=module.build_source_url(config),
                response_headers={},
                skip_unchanged=True,
            )
            second = self.make_payload(dynasty=False, change_value=True)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=module.parse_assets(second, config),
                payload=second,
                config=config,
                fetched_at=datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc),
                source_url=module.build_source_url(config),
                response_headers={},
                skip_unchanged=True,
            )
            self.assertTrue(created)
            ranking_path = (
                module.ranking_root(repo_root, config)
                / "snapshots"
                / "2026-07-18"
                / "ranking.csv"
            )
            with ranking_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(module.CSV_FIELDS, list(rows[0]))
            self.assertEqual("8998", rows[0]["value"])
            self.assertEqual("1", rows[0]["source_overall_rank"])
            self.assertEqual(4, len(paths))


if __name__ == "__main__":
    unittest.main()
