from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib import common as common_mod
from nfl_source_data_lib.phase1 import _build_schedule_odds, _build_schedules
from nfl_source_data_lib.schedule_odds_materialize import materialize_schedule_odds
from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.source_projection import (
    SCHEDULE_ODDS_COLUMNS,
    SCHEDULE_ODDS_PROJECTION_ID,
    SCHEDULE_ODDS_PROJECTION_VERSION,
    SCHEDULE_WITHOUT_ODDS_PROJECTION_ID,
    SCHEDULE_WITHOUT_ODDS_PROJECTION_VERSION,
    project_schedule_odds,
    project_schedule_without_odds,
)

ROOT = Path(__file__).resolve().parents[2]

UPSTREAM_FIELDS = [
    "game_id", "season", "game_type", "week", "gameday", "gametime", "away_team", "away_score",
    "home_team", "home_score", "away_moneyline", "home_moneyline", "spread_line",
    "away_spread_odds", "home_spread_odds", "total_line", "under_odds", "over_odds", "stadium",
]


def game(game_id: str = "2026_01_AAA_BBB", **overrides: str) -> dict[str, str]:
    row = {field: "" for field in UPSTREAM_FIELDS}
    row.update(
        {
            "game_id": game_id,
            "season": "2026",
            "game_type": "REG",
            "week": "1",
            "gameday": "2026-09-13",
            "gametime": "13:00",
            "away_team": "AAA",
            "home_team": "BBB",
            "away_moneyline": "150",
            "home_moneyline": "-180",
            "spread_line": "3.5",
            "away_spread_odds": "-110",
            "home_spread_odds": "-110",
            "total_line": "44.5",
            "under_odds": "-110",
            "over_odds": "-110",
            "stadium": "Test, Stadium",
        }
    )
    row.update(overrides)
    return row


def write_upstream(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UPSTREAM_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def dataset(root: Path, dataset_id: str, projection_id: str, required: tuple[str, ...]) -> common_mod.Dataset:
    folder = "schedules" if dataset_id == "nflverse.schedules" else "schedule-odds"
    return common_mod.Dataset(
        id=dataset_id,
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/games.csv",
        raw_path=root / f"providers/nflverse/{folder}/raw-latest.csv",
        metadata_path=root / f"providers/nflverse/{folder}/metadata.json",
        required_columns=required,
        minimum_rows=1,
        kind="test",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="fixed",
        source_format="csv",
        availability_policy="required",
        materialize=dataset_id == "nflverse.schedules",
        source_projection_id=projection_id,
        source_projection_version=1,
        upstream_format="csv",
    )


class ScheduleOddsProjectionTests(unittest.TestCase):
    def test_projections_split_the_columns_without_losing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "games.csv"
            write_upstream(upstream, [game(), game("2026_01_CCC_DDD", away_team="CCC", home_team="DDD")])
            schedule = root / "schedule.csv"
            odds = root / "odds.csv"
            schedule_stats = project_schedule_without_odds(upstream, schedule)
            odds_stats = project_schedule_odds(upstream, odds)

            with schedule.open(encoding="utf-8", newline="") as handle:
                schedule_rows = list(csv.DictReader(handle))
            with odds.open(encoding="utf-8", newline="") as handle:
                odds_reader = csv.DictReader(handle)
                odds_rows = list(odds_reader)
            self.assertEqual(2, schedule_stats["projectedRowCount"])
            self.assertEqual(2, odds_stats["projectedRowCount"])
            self.assertEqual(["game_id", *SCHEDULE_ODDS_COLUMNS], odds_reader.fieldnames)
            for column in SCHEDULE_ODDS_COLUMNS:
                self.assertNotIn(column, schedule_rows[0])
            self.assertEqual("Test, Stadium", schedule_rows[0]["stadium"])
            self.assertEqual("2026_01_CCC_DDD", schedule_rows[1]["game_id"])
            self.assertEqual("3.5", odds_rows[0]["spread_line"])
            self.assertEqual(
                {"game_id", *SCHEDULE_ODDS_COLUMNS},
                set(odds_rows[0]),
            )

    def test_projection_fails_closed_when_an_odds_column_disappears_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "games.csv"
            upstream.write_text("game_id,season,spread_line\nx,2026,1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                project_schedule_without_odds(upstream, root / "out.csv")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                project_schedule_odds(upstream, root / "out.csv")


class ScheduleOddsSyncTests(unittest.TestCase):
    def _sync(self, root: Path, rows: list[dict[str, str]]) -> tuple[dict, dict]:
        upstream = root / "upstream.csv"
        write_upstream(upstream, rows)

        def fake_download(_url: str, target: Path) -> None:
            shutil.copyfile(upstream, target)

        schedules = dataset(
            root, "nflverse.schedules", SCHEDULE_WITHOUT_ODDS_PROJECTION_ID, ("game_id", "season", "away_team")
        )
        odds = dataset(root, "nflverse.schedule-odds", SCHEDULE_ODDS_PROJECTION_ID, ("game_id", "spread_line"))
        with patch.object(common_mod, "download", side_effect=fake_download):
            return (
                common_mod.sync_dataset(schedules, current_season=2026),
                common_mod.sync_dataset(odds, current_season=2026),
            )

    def test_odds_only_change_does_not_rewrite_the_schedule_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schedule_raw = root / "providers/nflverse/schedules/raw-latest.csv"
            schedule_meta = root / "providers/nflverse/schedules/metadata.json"
            first_schedule, first_odds = self._sync(root, [game()])
            self.assertEqual("updated", first_schedule["status"])
            self.assertEqual("updated", first_odds["status"])
            schedule_bytes = schedule_raw.read_bytes()
            schedule_meta_bytes = schedule_meta.read_bytes()

            schedule_result, odds_result = self._sync(root, [game(spread_line="4.0", home_moneyline="-200")])
            self.assertEqual("unchanged", schedule_result["status"])
            self.assertEqual("updated", odds_result["status"])
            self.assertEqual(schedule_bytes, schedule_raw.read_bytes())
            self.assertEqual(schedule_meta_bytes, schedule_meta.read_bytes())

            odds_metadata = json.loads(
                (root / "providers/nflverse/schedule-odds/metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(SCHEDULE_ODDS_PROJECTION_ID, odds_metadata["sourceProjection"]["id"])
            self.assertNotIn("stadium", odds_metadata["columns"])

    def test_real_schedule_change_rewrites_the_schedule_but_not_the_odds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._sync(root, [game()])
            schedule_result, odds_result = self._sync(root, [game(gametime="16:25", home_score="21", away_score="17")])
            self.assertEqual("updated", schedule_result["status"])
            self.assertEqual("unchanged", odds_result["status"])
            with (root / "providers/nflverse/schedules/raw-latest.csv").open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual("16:25", row["gametime"])


class RegistrySplitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.datasets = {item.id: item for item in common_mod.load_registry(ROOT)}

    def test_schedule_and_odds_are_separate_raw_datasets_of_one_upstream(self) -> None:
        schedules = self.datasets["nflverse.schedules"]
        odds = self.datasets["nflverse.schedule-odds"]
        self.assertEqual(schedules.source_url, odds.source_url)
        self.assertNotEqual(schedules.raw_path, odds.raw_path)
        self.assertNotEqual(schedules.metadata_path, odds.metadata_path)
        self.assertEqual(
            (SCHEDULE_WITHOUT_ODDS_PROJECTION_ID, SCHEDULE_WITHOUT_ODDS_PROJECTION_VERSION),
            (schedules.source_projection_id, schedules.source_projection_version),
        )
        self.assertEqual(
            (SCHEDULE_ODDS_PROJECTION_ID, SCHEDULE_ODDS_PROJECTION_VERSION),
            (odds.source_projection_id, odds.source_projection_version),
        )

    def test_odds_are_materialized_separately_and_schedule_requires_no_odds_column(self) -> None:
        self.assertTrue(self.datasets["nflverse.schedule-odds"].materialize)
        self.assertTrue(self.datasets["nflverse.schedules"].materialize)
        for column in SCHEDULE_ODDS_COLUMNS:
            self.assertNotIn(column, self.datasets["nflverse.schedules"].required_columns)

    def test_only_separate_canonical_odds_builder_consumes_odds_columns(self) -> None:
        phase1 = (ROOT / "tools/nfl_source_data_lib/phase1.py").read_text(encoding="utf-8")
        scoped = (ROOT / "tools/nfl_source_data_lib/finality_materialize.py").read_text(encoding="utf-8")
        self.assertIn("def _build_schedule_odds(", phase1)
        self.assertIn('audit["scheduleOdds"]', phase1)
        self.assertNotIn("_build_schedule_odds", scoped)


class CanonicalScheduleOddsMaterializationTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        rows: list[dict[str, str]],
        season: int = 2026,
    ) -> tuple[common_mod.Dataset, dict[str, dict]]:
        source_root = root / DATA_SOURCE_ROOT
        odds = dataset(
            source_root, "nflverse.schedule-odds", SCHEDULE_ODDS_PROJECTION_ID, ("game_id", "spread_line")
        )
        odds.raw_path.parent.mkdir(parents=True, exist_ok=True)
        write_upstream(odds.raw_path, rows)
        schedule_index = {
            row["game_id"]: {"Season": season, "GameType": "REG", "Week": 1}
            for row in rows
        }
        return odds, schedule_index

    def test_committed_provider_odds_join_all_canonical_schedule_games(self) -> None:
        """Production-sized source evidence must cover exactly the same game identities."""
        datasets = {item.id: item for item in common_mod.load_registry(ROOT)}
        _, _, _, game_index = _build_schedules(
            ROOT, datasets["nflverse.schedules"], 2026, force=False
        )
        _, audit, _ = _build_schedule_odds(
            ROOT, datasets["nflverse.schedule-odds"], game_index, 2026, force=False
        )
        self.assertEqual(len(game_index), audit["gameCount"])
        self.assertGreater(audit["gameCount"], 7000)
        self.assertGreater(audit["gamesWithCompleteLines"], 7000)

    def test_source_only_lines_join_without_derived_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odds, index = self._fixture(root, [game()])
            result, audit, preserved = _build_schedule_odds(root, odds, index, 2026, force=False)
            self.assertEqual(0, preserved)
            self.assertEqual(1, audit["gamesWithCompleteLines"])
            self.assertEqual(0, audit["gamesWithoutCompleteLines"])
            path, payload = result[0]
            self.assertEqual(root / DATA_SOURCE_ROOT / "nfl/schedule-odds/2026.json", path)
            self.assertEqual("nflverse.schedule-odds", payload["SourceDataset"])
            self.assertFalse(payload["Finalized"])
            row = payload["Games"][0]
            self.assertEqual("2026_01_AAA_BBB", row["GameID"])
            self.assertEqual(3.5, row["SpreadLine"])
            self.assertEqual(44.5, row["TotalLine"])
            self.assertEqual(-180.0, row["HomeMoneyline"])
            self.assertNotIn("ImpliedAwayPoints", row)
            self.assertNotIn("ImpliedHomePoints", row)

    def test_missing_prices_and_incomplete_lines_are_null_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odds, index = self._fixture(root, [
                game("2026_01_AAA_BBB", total_line="", away_moneyline=""),
                game("2026_01_CCC_DDD", spread_line="", total_line="45.5",
                     away_team="CCC", home_team="DDD"),
            ])
            outputs, audit, _ = _build_schedule_odds(root, odds, index, 2026, force=False)
            records = {v["GameID"]: v for v in outputs[0][1]["Games"]}
            self.assertEqual(0, audit["gamesWithCompleteLines"])
            self.assertIsNone(records["2026_01_AAA_BBB"]["TotalLine"])
            self.assertIsNone(records["2026_01_AAA_BBB"]["AwayMoneyline"])
            self.assertIsNone(records["2026_01_CCC_DDD"]["SpreadLine"])
            self.assertEqual(45.5, records["2026_01_CCC_DDD"]["TotalLine"])

    def test_unknown_duplicate_and_missing_schedule_game_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odds, index = self._fixture(root, [game()])
            with self.assertRaisesRegex(ValueError, "requires nflverse.schedules"):
                _build_schedule_odds(root, odds, {}, 2026, force=False)
            index2 = {**index, "2026_01_CCC_DDD": {
                "Season": 2026, "GameType": "REG", "Week": 1
            }}
            with self.assertRaisesRegex(ValueError, "missing from odds source"):
                _build_schedule_odds(root, odds, index2, 2026, force=False)
            write_upstream(odds.raw_path, [game(), game()])
            with self.assertRaisesRegex(ValueError, "Duplicate NFL schedule odds"):
                _build_schedule_odds(root, odds, index, 2026, force=False)
            write_upstream(odds.raw_path, [game("2026_01_CCC_DDD")])
            with self.assertRaisesRegex(ValueError, "no canonical NFL schedule match"):
                _build_schedule_odds(root, odds, index, 2026, force=False)

    def test_invalid_numeric_lines_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odds, index = self._fixture(root, [game(spread_line="infinite")])
            with self.assertRaisesRegex(ValueError, "Invalid NFL odds number"):
                _build_schedule_odds(root, odds, index, 2026, force=False)
            write_upstream(odds.raw_path, [game(total_line="-1")])
            with self.assertRaisesRegex(ValueError, "Non-positive NFL odds total"):
                _build_schedule_odds(root, odds, index, 2026, force=False)
            write_upstream(odds.raw_path, [game(total_line="2", spread_line="10")])
            with self.assertRaisesRegex(ValueError, "Impossible NFL odds line"):
                _build_schedule_odds(root, odds, index, 2026, force=False)

    def test_deterministic_output_and_past_season_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odds, index = self._fixture(root, [game("2025_01_AAA_BBB")], season=2025)
            first, _, _ = _build_schedule_odds(root, odds, index, 2026, force=False)
            second, _, _ = _build_schedule_odds(root, odds, index, 2026, force=False)
            self.assertEqual(first, second)
            path, original = first[0]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(original) + "\n", encoding="utf-8")
            write_upstream(odds.raw_path, [game("2025_01_AAA_BBB", spread_line="7.5")])
            frozen, _, preserved = _build_schedule_odds(root, odds, index, 2026, force=False)
            self.assertEqual(1, preserved)
            self.assertEqual(original, frozen[0][1])


class ScopedOddsMaterializationTests(unittest.TestCase):
    def _fixture(self, root: Path, rows: list[dict[str, str]]) -> dict[str, common_mod.Dataset]:
        source_root = root / DATA_SOURCE_ROOT
        datasets = {
            "nflverse.schedules": dataset(
                source_root, "nflverse.schedules",
                SCHEDULE_WITHOUT_ODDS_PROJECTION_ID, ("game_id", "season", "away_team"),
            ),
            "nflverse.schedule-odds": dataset(
                source_root, "nflverse.schedule-odds",
                SCHEDULE_ODDS_PROJECTION_ID, ("game_id", "spread_line"),
            ),
        }
        for item in datasets.values():
            item.raw_path.parent.mkdir(parents=True, exist_ok=True)
            write_upstream(item.raw_path, rows)
        schedules, _, _, _ = _build_schedules(
            root, datasets["nflverse.schedules"], 2026, force=False
        )
        for path, payload in schedules:
            self.assertTrue(common_mod.write_json_if_changed(path, payload))
        return datasets

    def _run(self, root: Path, datasets: dict) -> dict:
        with patch(
            "nfl_source_data_lib.schedule_odds_materialize._observation_season",
            return_value=2026,
        ):
            return materialize_schedule_odds(root, datasets)

    def test_odds_only_writes_and_second_pass_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datasets = self._fixture(root, [game()])
            schedule = root / DATA_SOURCE_ROOT / "nfl/schedules/2026.json"
            before = schedule.read_bytes()
            first = self._run(root, datasets)
            self.assertEqual(1, first["oddsFilesChanged"])
            self.assertEqual(
                ["data-source/nfl/schedule-odds/2026.json"], first["oddsChangedPaths"]
            )
            self.assertEqual(before, schedule.read_bytes())
            second = self._run(root, datasets)
            self.assertEqual(0, second["oddsFilesChanged"])
            self.assertEqual([], second["oddsChangedPaths"])
            self.assertEqual(before, schedule.read_bytes())

    def test_odd_changes_match_existing_full_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datasets = self._fixture(root, [game()])
            self._run(root, datasets)
            odds = datasets["nflverse.schedule-odds"]
            write_upstream(odds.raw_path, [game(spread_line="4.5")])
            result = self._run(root, datasets)
            self.assertEqual(1, result["oddsFilesChanged"])
            _, _, _, idx = _build_schedules(
                root, datasets["nflverse.schedules"], 2026, force=False
            )
            expected, _, _ = _build_schedule_odds(
                root, odds, idx, 2026, force=False
            )
            actual = json.loads(
                (root / DATA_SOURCE_ROOT / "nfl/schedule-odds/2026.json").read_text()
            )
            self.assertEqual(expected[0][1], actual)
            self.assertEqual(4.5, actual["Games"][0]["SpreadLine"])

    def test_stale_or_missing_published_schedule_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datasets = self._fixture(root, [game()])
            write_upstream(
                datasets["nflverse.schedules"].raw_path, [game(gametime="20:20")]
            )
            with self.assertRaisesRegex(ValueError, "missing or stale"):
                self._run(root, datasets)
            self.assertFalse(
                (root / DATA_SOURCE_ROOT / "nfl/schedule-odds/2026.json").exists()
            )
            (root / DATA_SOURCE_ROOT / "nfl/schedules/2026.json").unlink()
            with self.assertRaisesRegex(ValueError, "missing or stale"):
                self._run(root, datasets)

    def test_invalid_or_incomplete_odds_never_publish_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datasets = self._fixture(
                root, [game(), game("2026_01_CCC_DDD")]
            )
            odds = datasets["nflverse.schedule-odds"]
            write_upstream(odds.raw_path, [game()])
            with self.assertRaisesRegex(ValueError, "missing from odds source"):
                self._run(root, datasets)
            write_upstream(
                odds.raw_path,
                [game(spread_line="inf"), game("2026_01_CCC_DDD")],
            )
            with self.assertRaisesRegex(ValueError, "Invalid NFL odds number"):
                self._run(root, datasets)
            self.assertFalse(
                (root / DATA_SOURCE_ROOT / "nfl/schedule-odds/2026.json").exists()
            )

    def test_historical_partition_stays_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datasets = self._fixture(
                root, [game("2025_01_AAA_BBB", season="2025")]
            )
            odds = datasets["nflverse.schedule-odds"]
            self.assertEqual(1, self._run(root, datasets)["oddsFilesChanged"])
            path = root / DATA_SOURCE_ROOT / "nfl/schedule-odds/2025.json"
            before = path.read_bytes()
            write_upstream(
                odds.raw_path, [game("2025_01_AAA_BBB", season="2025", spread_line="9")]
            )
            result = self._run(root, datasets)
            self.assertEqual(0, result["oddsFilesChanged"])
            self.assertEqual(1, result["oddsPartitionsPreserved"])
            self.assertEqual(before, path.read_bytes())


class FinalityScopeExcludesOddsTests(unittest.TestCase):
    def test_finality_scope_syncs_the_schedule_but_never_the_odds_dataset(self) -> None:
        source = (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn('raw_sync_args+=(--dataset "nflverse.schedules")', source)
        # A scoped Odds-only caller can appear elsewhere in the workflow, but
        # the game-finality raw dataset set itself must never include Odds.
        self.assertNotIn('raw_sync_args+=(--dataset "nflverse.schedule-odds")', source)
        self.assertIn('if [[ "${DATASET:-}" != "nflverse.game-finality" ]]', source)
        self.assertIn("inputs.materialization_scope != 'game-finality'", source)


if __name__ == "__main__":
    unittest.main()
