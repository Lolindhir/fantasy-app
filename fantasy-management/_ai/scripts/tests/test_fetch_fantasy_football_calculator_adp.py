import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_fantasy_football_calculator_adp.py"
spec = importlib.util.spec_from_file_location("ffc_adp_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyFootballCalculatorAdpTests(unittest.TestCase):
    def make_payload(
        self,
        config_key="ppr-8-team",
        *,
        change_adp=False,
        raw_note="a",
        end_date="2026-07-18",
        total_drafts=300,
    ):
        config = module.FORMAT_CONFIGS[config_key]
        players = []
        positions = ["QB", "RB", "WR", "TE"]
        for index in range(1, 121):
            adp = index + 0.25 + (0.1 if change_adp and index == 1 else 0)
            players.append(
                {
                    "player_id": 1000 + index,
                    "name": f"Player {index}",
                    "position": positions[(index - 1) % len(positions)],
                    "team": "FA",
                    "adp": adp,
                    "adp_formatted": f"{1 + (index - 1) // config['source_team_count']}.{1 + (index - 1) % config['source_team_count']:02d}",
                    "times_drafted": 400 - index,
                    "high": max(1, index - 2),
                    "low": index + 3,
                    "stdev": 1.5,
                    "bye": index % 15,
                }
            )
        players.extend(
            [
                {
                    "player_id": 9001,
                    "name": "Example Defense",
                    "position": "DEF",
                    "team": "BUF",
                    "adp": 121.0,
                    "adp_formatted": "13.01",
                    "times_drafted": 25,
                    "high": 110,
                    "low": 130,
                    "stdev": 4.0,
                    "bye": 7,
                },
                {
                    "player_id": 9002,
                    "name": "Example Kicker",
                    "position": "PK",
                    "team": "DAL",
                    "adp": 122.0,
                    "adp_formatted": "13.02",
                    "times_drafted": 20,
                    "high": 111,
                    "low": 131,
                    "stdev": 4.5,
                    "bye": 14,
                },
            ]
        )
        return {
            "status": "Success",
            "meta": {
                "type": "PPR" if config_key == "ppr-8-team" else "2-QB",
                "teams": config["source_team_count"],
                "rounds": 15,
                "total_drafts": total_drafts,
                "start_date": "2026-07-01",
                "end_date": end_date,
                "year": 2026,
            },
            "players": players,
            "raw_note": raw_note,
        }

    def prepare(self, config_key="ppr-8-team", **kwargs):
        config = module.FORMAT_CONFIGS[config_key]
        payload = self.make_payload(config_key, **kwargs)
        fetched_at = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)
        sample = module.validate_payload(
            payload,
            config,
            season=2026,
            fetched_at=fetched_at,
        )
        rows, diagnostics = module.parse_players(payload, config, sample)
        return config, payload, fetched_at, sample, rows, diagnostics

    def test_request_parameters_match_agreed_formats(self):
        ppr = module.FORMAT_CONFIGS["ppr-8-team"]
        two_qb = module.FORMAT_CONFIGS["2qb-10-team"]
        self.assertEqual(
            {"teams": "8", "year": "2026", "position": "all"},
            module.request_parameters(ppr, 2026),
        )
        self.assertEqual(
            {"teams": "10", "year": "2026", "position": "all"},
            module.request_parameters(two_qb, 2026),
        )
        ppr_query = parse_qs(urlparse(module.build_source_url(ppr, 2026)).query)
        self.assertEqual(["8"], ppr_query["teams"])
        self.assertTrue(module.build_source_url(two_qb, 2026).split("?", 1)[0].endswith("/2qb"))

    def test_normalizes_offense_and_retains_exclusion_diagnostics(self):
        _, _, _, sample, rows, diagnostics = self.prepare()
        self.assertEqual(120, len(rows))
        self.assertEqual(list(range(1, 121)), [row["Rank"] for row in rows])
        self.assertEqual("1001", rows[0]["source_player_id"])
        self.assertEqual(1, rows[0]["source_rank"])
        self.assertEqual(300, rows[0]["sample_total_drafts"])
        self.assertEqual("high_sample", sample["quality"])
        self.assertEqual({"DEF": 1, "PK": 1}, diagnostics["excluded_position_counts"])
        self.assertEqual(122, diagnostics["source_player_count"])
        self.assertEqual(120, diagnostics["normalized_player_count"])

    def test_accepts_2qb_source_identity(self):
        config, _, _, sample, rows, _ = self.prepare("2qb-10-team")
        self.assertTrue(config["two_qb"])
        self.assertEqual(10, sample["teams"])
        self.assertEqual(120, len(rows))

    def test_rejects_wrong_team_count_and_stale_sample(self):
        config = module.FORMAT_CONFIGS["ppr-8-team"]
        payload = self.make_payload()
        payload["meta"]["teams"] = 10
        with self.assertRaisesRegex(module.FantasyFootballCalculatorFetchError, "team count"):
            module.validate_payload(
                payload,
                config,
                season=2026,
                fetched_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
            )

        stale = self.make_payload(end_date="2026-05-01")
        stale["meta"]["start_date"] = "2026-04-01"
        with self.assertRaisesRegex(module.FantasyFootballCalculatorFetchError, "stale"):
            module.validate_payload(
                stale,
                config,
                season=2026,
                fetched_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
            )

    def test_rejects_adp_outside_high_low(self):
        config = module.FORMAT_CONFIGS["ppr-8-team"]
        payload = self.make_payload()
        payload["players"][0]["adp"] = 50
        sample = module.validate_payload(
            payload,
            config,
            season=2026,
            fetched_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
        )
        with self.assertRaisesRegex(module.FantasyFootballCalculatorFetchError, "outside high/low"):
            module.parse_players(payload, config, sample)

    def test_latest_raw_only_and_unchanged_ranking_is_not_archived_again(self):
        config, payload, fetched_at, sample, rows, diagnostics = self.prepare(raw_note="first")
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=rows,
                payload=payload,
                config=config,
                sample=sample,
                diagnostics=diagnostics,
                fetched_at=fetched_at,
                source_url=module.build_source_url(config, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            self.assertTrue(created)
            self.assertEqual(4, len(paths))

            config2, payload2, fetched_at2, sample2, rows2, diagnostics2 = self.prepare(
                raw_note="second"
            )
            fetched_at2 = datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=rows2,
                payload=payload2,
                config=config2,
                sample=sample2,
                diagnostics=diagnostics2,
                fetched_at=fetched_at2,
                source_url=module.build_source_url(config2, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            self.assertFalse(created)
            self.assertEqual(2, len(paths))
            root = module.ranking_root(repo_root, config)
            self.assertTrue((root / "snapshots" / "2026-07-18" / "ranking.csv").is_file())
            self.assertFalse((root / "snapshots" / "2026-07-19").exists())
            raw = json.loads((root / "raw-latest.json").read_text(encoding="utf-8"))
            self.assertEqual("second", raw["raw_note"])
            latest = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-07-18", latest["snapshot_date"])
            self.assertEqual("2026-07-19T08:00:00+00:00", latest["raw_fetched_at"])

    def test_changed_adp_creates_new_snapshot_and_csv(self):
        config, payload, fetched_at, sample, rows, diagnostics = self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            module.write_format(
                repo_root=repo_root,
                rows=rows,
                payload=payload,
                config=config,
                sample=sample,
                diagnostics=diagnostics,
                fetched_at=fetched_at,
                source_url=module.build_source_url(config, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            config2, payload2, _, sample2, rows2, diagnostics2 = self.prepare(change_adp=True)
            paths, created = module.write_format(
                repo_root=repo_root,
                rows=rows2,
                payload=payload2,
                config=config2,
                sample=sample2,
                diagnostics=diagnostics2,
                fetched_at=datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc),
                source_url=module.build_source_url(config2, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            self.assertTrue(created)
            self.assertEqual(4, len(paths))
            ranking_path = (
                module.ranking_root(repo_root, config)
                / "snapshots"
                / "2026-07-19"
                / "ranking.csv"
            )
            with ranking_path.open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(module.CSV_FIELDS, list(csv_rows[0].keys()))
            self.assertEqual("1.35", csv_rows[0]["adp"])
            metadata = json.loads(
                (ranking_path.parent / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(module.SCHEMA_VERSION, metadata["schema_version"])
            self.assertEqual("adp", metadata["ranking_kind"])
            self.assertEqual("latest_only", metadata["raw_retention"]["policy"])
            self.assertFalse(metadata["raw_retention"]["historical_raw_snapshots"])


if __name__ == "__main__":
    unittest.main()
