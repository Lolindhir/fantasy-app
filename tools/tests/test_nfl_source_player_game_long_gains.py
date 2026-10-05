from __future__ import annotations

import csv
import gzip
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.nfl_source_data_lib import common as common_mod
from tools.nfl_source_data_lib.phase1 import _build_player_game_long_gains
from tools.nfl_source_data_lib.source_projection import (
    PLAYER_GAME_LONG_GAINS_FIELDS,
    PLAYER_GAME_LONG_GAINS_PROJECTION_ID,
    PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION,
    project_player_game_long_gains,
)

PBP_FIELDS = (
    "season",
    "season_type",
    "week",
    "game_id",
    "play_id",
    "home_team",
    "away_team",
    "posteam",
    "two_point_attempt",
    "complete_pass",
    "rusher_player_id",
    "rushing_yards",
    "receiver_player_id",
    "receiving_yards",
)


def pbp_row(**overrides: str) -> dict[str, str]:
    row = {field: "" for field in PBP_FIELDS}
    row.update(
        {
            "season": "2025",
            "season_type": "REG",
            "week": "7",
            "game_id": "2025_07_AAA_BBB",
            "play_id": "10",
            "home_team": "BBB",
            "away_team": "AAA",
            "posteam": "AAA",
            "two_point_attempt": "0",
        }
    )
    row.update(overrides)
    return row


def write_pbp(path: Path, rows: list[dict[str, str]], fields: tuple[str, ...] = PBP_FIELDS) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def long_gains_dataset(root: Path) -> common_mod.Dataset:
    return common_mod.Dataset(
        id="nflverse.player-game-long-gains",
        provider="nflverse",
        upstream="nflverse/nflverse-data",
        source_url="https://example.invalid/play_by_play_{season}.csv.gz",
        raw_path=root / "source-data/providers/nflverse/player-game-long-gains/raw-{season}.json",
        metadata_path=root / "source-data/providers/nflverse/player-game-long-gains/metadata-{season}.json",
        required_columns=tuple(PLAYER_GAME_LONG_GAINS_FIELDS),
        minimum_rows=0,
        kind="player-game-long-gain-evidence",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="json",
        availability_policy="current-season-may-be-unavailable",
        materialize=True,
        source_projection_id=PLAYER_GAME_LONG_GAINS_PROJECTION_ID,
        source_projection_version=PLAYER_GAME_LONG_GAINS_PROJECTION_VERSION,
        upstream_format="csv.gz",
    )


def project(rows: list[dict[str, str]]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "pbp.csv.gz"
        output = Path(tmp) / "out.json"
        write_pbp(source, rows)
        project_player_game_long_gains(source, output)
        return json.loads(output.read_text(encoding="utf-8"))


class LongGainsProjectionTests(unittest.TestCase):
    def test_keeps_only_maximum_per_player_game_and_type_with_play_evidence(self) -> None:
        payload = project(
            [
                pbp_row(play_id="1", rusher_player_id="00-R", rushing_yards="4"),
                pbp_row(play_id="2", rusher_player_id="00-R", rushing_yards="23"),
                pbp_row(play_id="3", rusher_player_id="00-R", rushing_yards="9"),
                pbp_row(
                    play_id="4",
                    complete_pass="1",
                    receiver_player_id="00-W",
                    receiving_yards="12",
                ),
                pbp_row(
                    play_id="5",
                    complete_pass="1",
                    receiver_player_id="00-W",
                    receiving_yards="31",
                ),
            ]
        )
        rows = {(r["gain_type"], r["player_id"]): r for r in payload["Records"]}
        self.assertEqual(2, len(rows))
        self.assertEqual((23, 2), (rows[("rush", "00-R")]["yards"], rows[("rush", "00-R")]["play_id"]))
        self.assertEqual((31, 5), (rows[("reception", "00-W")]["yards"], rows[("reception", "00-W")]["play_id"]))
        self.assertEqual("AAA", rows[("rush", "00-R")]["team"])

    def test_negative_only_gains_are_kept_not_zeroed(self) -> None:
        payload = project(
            [
                pbp_row(play_id="1", rusher_player_id="00-R", rushing_yards="-3"),
                pbp_row(play_id="2", rusher_player_id="00-R", rushing_yards="-1"),
                pbp_row(play_id="3", complete_pass="1", receiver_player_id="00-W", receiving_yards="-1"),
            ]
        )
        by_type = {r["gain_type"]: r["yards"] for r in payload["Records"]}
        self.assertEqual({"rush": -1, "reception": -1}, by_type)

    def test_excludes_two_point_attempts_and_incomplete_passes(self) -> None:
        payload = project(
            [
                pbp_row(play_id="1", two_point_attempt="1", rusher_player_id="00-R", rushing_yards="2"),
                pbp_row(play_id="2", two_point_attempt="1", complete_pass="1", receiver_player_id="00-W", receiving_yards="2"),
                pbp_row(play_id="3", complete_pass="0", receiver_player_id="00-W", receiving_yards="40"),
            ]
        )
        self.assertEqual([], payload["Records"])
        self.assertEqual(1, len(payload["Games"]))

    def test_tie_selects_lowest_play_id_deterministically(self) -> None:
        rows = [
            pbp_row(play_id="9", rusher_player_id="00-R", rushing_yards="15"),
            pbp_row(play_id="3", rusher_player_id="00-R", rushing_yards="15"),
        ]
        forward = project(rows)
        backward = project(list(reversed(rows)))
        self.assertEqual(forward, backward)
        self.assertEqual(3, forward["Records"][0]["play_id"])

    def test_games_without_records_stay_listed_as_covered(self) -> None:
        payload = project(
            [
                pbp_row(play_id="1", rusher_player_id="00-R", rushing_yards="5"),
                pbp_row(game_id="2025_07_CCC_DDD", home_team="DDD", away_team="CCC", posteam="CCC", play_id="1"),
            ]
        )
        self.assertEqual(
            ["2025_07_AAA_BBB", "2025_07_CCC_DDD"],
            [game["game_id"] for game in payload["Games"]],
        )
        self.assertEqual(1, len(payload["Records"]))

    def test_missing_source_column_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "pbp.csv.gz"
            fields = tuple(field for field in PBP_FIELDS if field != "rushing_yards")
            write_pbp(source, [{field: "" for field in fields}], fields)
            with self.assertRaisesRegex(ValueError, "rushing_yards"):
                project_player_game_long_gains(source, Path(tmp) / "out.json")


class SharedUpstreamDownloadTests(unittest.TestCase):
    def test_two_projections_of_one_pbp_url_download_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "upstream.csv.gz"
            write_pbp(upstream, [pbp_row(play_id="1", rusher_player_id="00-R", rushing_yards="5")])
            first = long_gains_dataset(root / "a")
            second = long_gains_dataset(root / "b")

            def fake_download(_url: str, target: Path) -> None:
                shutil.copyfile(upstream, target)

            cache_dir = root / "cache"
            cache_dir.mkdir()
            cache = common_mod.UpstreamDownloadCache(cache_dir)
            with patch.object(common_mod, "download", side_effect=fake_download) as mocked:
                for dataset in (first, second):
                    result = common_mod.sync_dataset(
                        dataset,
                        season=2025,
                        current_season=2025,
                        upstream_cache=cache,
                    )
                    self.assertEqual("updated", result["status"])
                    self.assertEqual(1, result["rowCount"])
            self.assertEqual(1, mocked.call_count)


class LongGainsCanonicalTests(unittest.TestCase):
    def _write_raw(self, dataset: common_mod.Dataset, season: int, records: list[dict], games: list[dict]) -> None:
        raw = dataset.raw_path_for(season)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(
            json.dumps(
                {
                    "SchemaVersion": 1,
                    "Columns": list(PLAYER_GAME_LONG_GAINS_FIELDS),
                    "Games": games,
                    "Records": records,
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _game(game_id: str = "2025_07_AAA_BBB", week: str = "7") -> dict:
        return {"game_id": game_id, "season_type": "REG", "week": week, "home_team": "BBB", "away_team": "AAA"}

    @staticmethod
    def _record(player: str, gain_type: str, yards: int, play_id: int = 2, season: str = "2025") -> dict:
        return {
            "season": season,
            "season_type": "REG",
            "week": "7",
            "game_id": "2025_07_AAA_BBB",
            "gain_type": gain_type,
            "player_id": player,
            "team": "AAA",
            "play_id": play_id,
            "yards": yards,
        }

    def test_materializes_identity_play_evidence_and_covered_games(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = long_gains_dataset(root)
            self._write_raw(
                dataset,
                2026,
                [self._record("00-1", "rush", 23, season="2026"), self._record("00-2", "reception", -1, 4, season="2026")],
                [self._game("2026_07_AAA_BBB"), self._game("2026_07_CCC_DDD")],
            )
            raw = json.loads(dataset.raw_path_for(2026).read_text(encoding="utf-8"))
            for record in raw["Records"]:
                record["game_id"] = "2026_07_AAA_BBB"
            dataset.raw_path_for(2026).write_text(json.dumps(raw), encoding="utf-8")
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": "00-1"}}]

            outputs, audit, preserved = _build_player_game_long_gains(root, dataset, canonical, 2026, force=False)

            self.assertEqual(0, preserved)
            ((path, payload),) = outputs
            self.assertEqual("source-data/nfl/player-game-long-gains/2026.json", str(path.relative_to(root)))
            self.assertFalse(payload["Finalized"])
            self.assertEqual(["2026_07_AAA_BBB", "2026_07_CCC_DDD"], [g["GameID"] for g in payload["Games"]])
            rush = next(r for r in payload["Records"] if r["GainType"] == "LongRush")
            self.assertEqual(("NFLP-1", 23, 2), (rush["CanonicalPlayerID"], rush["Yards"], rush["PlayID"]))
            reception = next(r for r in payload["Records"] if r["GainType"] == "LongReception")
            self.assertIsNone(reception["CanonicalPlayerID"])
            self.assertEqual(-1, reception["Yards"])
            self.assertEqual(1, audit["resolvedIdentityCount"])
            self.assertEqual(["00-2"], audit["unresolvedGSISIDs"])
            again, _, _ = _build_player_game_long_gains(root, dataset, canonical, 2026, force=False)
            self.assertEqual(outputs[0][1], again[0][1])

    def test_historical_unresolved_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = long_gains_dataset(root)
            self._write_raw(dataset, 2025, [self._record("00-9", "rush", 5)], [self._game()])
            with self.assertRaisesRegex(ValueError, "cannot resolve GSIS 00-9"):
                _build_player_game_long_gains(root, dataset, [], 2026, force=False)

    def test_prior_season_partition_is_frozen_unless_forced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = long_gains_dataset(root)
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": "00-1"}}]
            self._write_raw(dataset, 2025, [self._record("00-1", "rush", 5)], [self._game()])
            ((path, payload),) = _build_player_game_long_gains(root, dataset, canonical, 2026, force=False)[0]
            self.assertTrue(payload["Finalized"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")

            self._write_raw(dataset, 2025, [self._record("00-1", "rush", 99)], [self._game()])
            frozen, _, preserved = _build_player_game_long_gains(root, dataset, canonical, 2026, force=False)
            self.assertEqual(1, preserved)
            self.assertEqual(5, frozen[0][1]["Records"][0]["Yards"])
            repaired, _, preserved = _build_player_game_long_gains(root, dataset, canonical, 2026, force=True)
            self.assertEqual(0, preserved)
            self.assertEqual(99, repaired[0][1]["Records"][0]["Yards"])

    def test_record_outside_covered_games_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = long_gains_dataset(root)
            self._write_raw(dataset, 2026, [self._record("00-1", "rush", 5, season="2026")], [self._game("2026_08_XXX_YYY", "8")])
            with self.assertRaisesRegex(ValueError, "outside the covered games"):
                _build_player_game_long_gains(root, dataset, [], 2026, force=False)


class LongGainsRegistryTests(unittest.TestCase):
    def test_repository_registry_declares_projected_dataset(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        datasets = {dataset.id: dataset for dataset in common_mod.load_registry(repo_root)}
        dataset = datasets["nflverse.player-game-long-gains"]
        self.assertEqual(PLAYER_GAME_LONG_GAINS_PROJECTION_ID, dataset.source_projection_id)
        self.assertTrue(dataset.is_season_partitioned)
        self.assertEqual("current-season-may-be-unavailable", dataset.availability_policy)
        self.assertTrue(dataset.materialize)
        # The same play-by-play artifact serves the special-teams fumble projection.
        self.assertEqual(
            datasets["nflverse.special-teams-fumble-events"].source_url,
            dataset.source_url,
        )


if __name__ == "__main__":
    unittest.main()
