import csv
import io
import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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
        offense_rows=120,
    ):
        config = module.FORMAT_CONFIGS[config_key]
        players = []
        positions = ["QB", "RB", "WR", "TE"]
        for index in range(1, offense_rows + 1):
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

    def write_runtime_contracts(self, root: Path) -> Path:
        schedule_path = root / "source-data" / "nfl" / "schedules" / "2026.json"
        schedule_path.parent.mkdir(parents=True, exist_ok=True)
        schedule_path.write_text(
            json.dumps({
                "SchemaVersion": 2,
                "Season": 2026,
                "SourceDataset": "nflverse.schedules",
                "Finalized": False,
                "Games": [
                    {"GameID": "w1", "GameType": "REG", "Week": 1, "GameDay": "2026-09-09"},
                    {"GameID": "w2", "GameType": "REG", "Week": 2, "GameDay": "2026-09-17"},
                    {"GameID": "w18", "GameType": "REG", "Week": 18, "GameDay": "2027-01-10"},
                ],
            }),
            encoding="utf-8",
        )
        policy_path = (
            root
            / "fantasy-management"
            / "sources"
            / "external-rankings"
            / "adp"
            / "fantasy-football-calculator"
            / "quality-policy.json"
        )
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        phases = {
            "pre_regular_season": {
                "active": True,
                "expected_minimum_rows": 80,
                "minimum_usable_rows": 50,
            },
            "regular_season": {
                "active": True,
                "expected_minimum_rows": 50,
                "minimum_usable_rows": 50,
            },
            "post_regular_season": {
                "active": False,
                "expected_minimum_rows": 0,
                "minimum_usable_rows": 0,
            },
        }
        policy_path.write_text(
            json.dumps({
                "schema_version": 1,
                "source_id": "fantasy-football-calculator",
                "season_context_id": "nfl-regular-season-context",
                "purpose": "test",
                "datasets": {
                    "redraft-ppr-8-team": {"phases": phases},
                    "redraft-2qb-10-team": {"phases": phases},
                },
            }),
            encoding="utf-8",
        )
        return policy_path

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

    def test_accepts_offense_population_at_contract_minimum(self):
        _, _, _, _, rows, diagnostics = self.prepare(offense_rows=50)
        self.assertEqual(50, len(rows))
        self.assertEqual(50, diagnostics["normalized_player_count"])

    def test_accepts_current_in_season_sized_offense_population(self):
        _, _, _, _, rows, diagnostics = self.prepare(offense_rows=72)
        self.assertEqual(72, len(rows))
        self.assertEqual(72, diagnostics["normalized_player_count"])

    def test_parser_keeps_coverage_separate_from_structural_validation(self):
        config = module.FORMAT_CONFIGS["ppr-8-team"]
        payload = self.make_payload(offense_rows=43)
        sample = module.validate_payload(
            payload,
            config,
            season=2026,
            fetched_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
        )
        rows, diagnostics = module.parse_players(payload, config, sample)
        self.assertEqual(43, len(rows))
        self.assertEqual(43, diagnostics["normalized_player_count"])

    def test_dry_run_preserves_healthy_formats_when_kicker_coverage_is_too_small(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ppr_path = root / "ppr.json"
            two_qb_path = root / "2qb.json"
            ppr_path.write_text(
                json.dumps(self.make_payload("ppr-8-team")),
                encoding="utf-8",
            )
            two_qb_path.write_text(
                json.dumps(self.make_payload("2qb-10-team")),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = module.main([
                    "--season",
                    "2026",
                    "--fetched-at",
                    "2026-07-18T08:00:00Z",
                    "--input",
                    f"ppr-8-team={ppr_path}",
                    "--input",
                    f"2qb-10-team={two_qb_path}",
                    "--dry-run",
                ])
            self.assertEqual(0, result)
            self.assertIn("redraft-ppr-8-team rows=120", output.getvalue())
            self.assertIn("redraft-2qb-10-team rows=120", output.getvalue())
            self.assertIn("skipped-preserving-last-good", output.getvalue())

    def test_regular_season_insufficient_ppr_preserves_last_good_and_publishes_2qb(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy_path = self.write_runtime_contracts(root)

            config, payload, _, sample, rows, diagnostics = self.prepare(offense_rows=58)
            module.write_format(
                repo_root=root,
                rows=rows,
                payload=payload,
                config=config,
                sample=sample,
                diagnostics=diagnostics,
                fetched_at=datetime(2026, 9, 20, 3, 49, tzinfo=timezone.utc),
                source_url=module.build_source_url(config, 2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )

            ppr_path = root / "ppr.json"
            two_qb_path = root / "2qb.json"
            ppr_payload = self.make_payload(
                "ppr-8-team",
                offense_rows=43,
                end_date="2026-09-20",
                total_drafts=100,
            )
            ppr_payload["meta"]["start_date"] = "2026-09-13"
            two_qb_payload = self.make_payload(
                "2qb-10-team",
                offense_rows=120,
                end_date="2026-09-20",
                total_drafts=1000,
            )
            two_qb_payload["meta"]["start_date"] = "2026-08-21"
            ppr_path.write_text(json.dumps(ppr_payload), encoding="utf-8")
            two_qb_path.write_text(json.dumps(two_qb_payload), encoding="utf-8")

            result = module.main([
                "--repo-root",
                str(root),
                "--quality-policy",
                str(policy_path),
                "--season",
                "2026",
                "--fetched-at",
                "2026-09-21T04:14:44Z",
                "--input",
                f"ppr-8-team={ppr_path}",
                "--input",
                f"2qb-10-team={two_qb_path}",
                "--skip-unchanged",
            ])
            self.assertEqual(0, result)

            ppr_root = module.ranking_root(root, module.FORMAT_CONFIGS["ppr-8-team"])
            ppr_latest = json.loads((ppr_root / "latest.json").read_text(encoding="utf-8"))
            ppr_status = json.loads(
                (ppr_root / "observation-status.json").read_text(encoding="utf-8")
            )
            ppr_raw = json.loads((ppr_root / "raw-latest.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-09-20", ppr_latest["snapshot_date"])
            self.assertFalse((ppr_root / "snapshots" / "2026-09-21").exists())
            self.assertEqual(45, len(ppr_raw["players"]))
            self.assertEqual("insufficient_coverage", ppr_status["status"])
            self.assertFalse(ppr_status["usable"])
            self.assertFalse(ppr_status["published"])
            self.assertEqual(43, ppr_status["coverage"]["observed_rows"])
            self.assertEqual(
                ppr_latest["ranking_file"],
                ppr_status["last_good"]["ranking_file"],
            )

            two_qb_root = module.ranking_root(root, module.FORMAT_CONFIGS["2qb-10-team"])
            two_qb_latest = json.loads(
                (two_qb_root / "latest.json").read_text(encoding="utf-8")
            )
            two_qb_status = json.loads(
                (two_qb_root / "observation-status.json").read_text(encoding="utf-8")
            )
            self.assertEqual("2026-09-21", two_qb_latest["snapshot_date"])
            self.assertTrue(two_qb_status["usable"])
            self.assertTrue(two_qb_status["published"])

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
