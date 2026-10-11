from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.nfl_source_data_lib import common as common_mod
from tools.nfl_source_data_lib.source_projection import (
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

    def test_odds_are_raw_only_and_schedule_requires_no_odds_column(self) -> None:
        self.assertFalse(self.datasets["nflverse.schedule-odds"].materialize)
        self.assertTrue(self.datasets["nflverse.schedules"].materialize)
        for column in SCHEDULE_ODDS_COLUMNS:
            self.assertNotIn(column, self.datasets["nflverse.schedules"].required_columns)

    def test_no_canonical_materializer_reads_odds_columns(self) -> None:
        lib = ROOT / "tools/nfl_source_data_lib"
        for path in lib.glob("*.py"):
            if path.name == "source_projection.py":
                continue
            text = path.read_text(encoding="utf-8")
            for column in SCHEDULE_ODDS_COLUMNS:
                self.assertNotIn(column, text, f"{path.name} must not read odds column {column}")


class FinalityScopeExcludesOddsTests(unittest.TestCase):
    def test_finality_scope_syncs_the_schedule_but_never_the_odds_dataset(self) -> None:
        source = (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn('raw_sync_args+=(--dataset "nflverse.schedules")', source)
        self.assertNotIn("schedule-odds", source)


if __name__ == "__main__":
    unittest.main()
