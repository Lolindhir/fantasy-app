import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset, load_registry, planned_dataset_ids
from nfl_source_data_lib.phase1 import build_phase1_outputs


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def seasonal_dataset(root: Path, dataset_id: str, partition_key: str = "season") -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/raw-{season}.csv",
        raw_path=root / dataset_id / "raw-{season}.csv",
        metadata_path=root / dataset_id / "metadata-{season}.json",
        required_columns=("season",),
        minimum_rows=1,
        kind="test",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key=partition_key,
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="csv",
        availability_policy="current-season-may-be-unavailable",
        materialize=True,
    )


def fixed_seasonal_dataset(root: Path, dataset_id: str) -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/raw.csv",
        raw_path=root / dataset_id / "raw.csv",
        metadata_path=root / dataset_id / "metadata.json",
        required_columns=("game_id",),
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
        materialize=True,
    )


def sleeper_dataset(root: Path) -> Dataset:
    return Dataset(
        id="sleeper.players",
        provider="sleeper",
        upstream="test",
        source_url="https://example.invalid/players.json",
        raw_path=root / "sleeper" / "players.json",
        metadata_path=root / "sleeper" / "metadata.json",
        required_columns=("player_id",),
        minimum_rows=1,
        kind="test",
        refresh_policy="periodic",
        retention_policy="latest-with-git-history",
        license="test",
        attribution="test",
        lifecycle_class="dynamic",
        partition_key="none",
        finalization_policy="never",
        repair_policy="normal",
        source_mode="fixed",
        source_format="json",
        availability_policy="required",
        materialize=True,
    )


CANONICAL = [{
    "CanonicalPlayerID": "NFLP-one",
    "IDs": {
        "GSIS": "00-TEST",
        "PFR": "TestPl00",
        "Sleeper": "123",
    },
    "IDAliases": {},
}]


class Phase1SourceDataTests(unittest.TestCase):
    def test_repository_registry_activates_all_phase1_datasets(self):
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        expected = {
            "nflverse.schedules",
            "nflverse.game-finality",
            "nflverse.player-stats",
            "nflverse.snap-counts",
            "nflverse.weekly-rosters",
            "nflverse.rosters",
            "sleeper.players",
        }
        self.assertTrue(expected.issubset(active))
        self.assertTrue(all(active[dataset_id].materialize for dataset_id in expected))
        planned = set(planned_dataset_ids(REPO_ROOT))
        self.assertTrue(expected.isdisjoint(planned))
        self.assertEqual({"nflverse.depth-charts", "nflverse.contracts"}, planned)

    def test_finality_uses_released_game_evidence_not_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schedules = fixed_seasonal_dataset(root / "raw", "nflverse.schedules")
            finality = fixed_seasonal_dataset(root / "raw", "nflverse.game-finality")
            fields = [
                "game_id", "season", "game_type", "week", "gameday", "weekday", "gametime",
                "away_team", "away_score", "home_team", "home_score",
            ]
            write_csv(schedules.raw_path, fields, [
                {
                    "game_id": "2022_17_BUF_CIN", "season": 2022, "game_type": "REG", "week": 17,
                    "gameday": "2023-01-02", "weekday": "Monday", "gametime": "20:30",
                    "away_team": "BUF", "away_score": 3, "home_team": "CIN", "home_score": 7,
                },
                {
                    "game_id": "2022_17_MIN_GB", "season": 2022, "game_type": "REG", "week": 17,
                    "gameday": "2023-01-01", "weekday": "Sunday", "gametime": "16:25",
                    "away_team": "MIN", "away_score": 17, "home_team": "GB", "home_score": 41,
                },
            ])
            write_csv(finality.raw_path, ["game_id"], [{"game_id": "2022_17_MIN_GB"}])

            outputs, audit, _ = build_phase1_outputs(
                root,
                {schedules.id: schedules, finality.id: finality},
                CANONICAL,
                2026,
            )
            finality_payload = next(
                payload for path, payload in outputs if path.name == "2022.json" and "game-finality" in str(path)
            )
            by_game = {game["GameID"]: game for game in finality_payload["Games"]}
            self.assertFalse(by_game["2022_17_BUF_CIN"]["Final"])
            self.assertTrue(by_game["2022_17_MIN_GB"]["Final"])
            week = next(item for item in finality_payload["Weeks"] if item["Week"] == 17)
            self.assertFalse(week["WeekFinal"])
            self.assertEqual(1, week["FinalGameCount"])
            self.assertEqual(1, audit["gameFinality"]["releasedEvidenceCount"])

    def test_duplicate_schedule_game_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schedules = fixed_seasonal_dataset(root / "raw", "nflverse.schedules")
            fields = ["game_id", "season", "game_type", "week", "away_team", "home_team"]
            row = {
                "game_id": "2026_01_A_B", "season": 2026, "game_type": "REG",
                "week": 1, "away_team": "A", "home_team": "B",
            }
            write_csv(schedules.raw_path, fields, [row, row])
            with self.assertRaises(ValueError):
                build_phase1_outputs(root, {schedules.id: schedules}, CANONICAL, 2026)

    def test_rosters_stats_and_snaps_resolve_only_provider_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rosters = seasonal_dataset(root / "raw", "nflverse.rosters", "season")
            weekly = seasonal_dataset(root / "raw", "nflverse.weekly-rosters", "season-week")
            stats = seasonal_dataset(root / "raw", "nflverse.player-stats", "season-week")
            snaps = seasonal_dataset(root / "raw", "nflverse.snap-counts", "season-week")

            roster_fields = [
                "season", "team", "position", "depth_chart_position", "jersey_number", "status",
                "full_name", "birth_date", "height", "weight", "college", "gsis_id",
                "espn_id", "pfr_id", "pff_id", "sleeper_id", "week", "game_type",
            ]
            roster_row = {
                "season": 2026, "team": "NYG", "position": "WR", "depth_chart_position": "WR",
                "jersey_number": 10, "status": "ACT", "full_name": "Different Display Name",
                "birth_date": "2000-01-01", "height": 72, "weight": 200, "college": "Test",
                "gsis_id": "00-TEST", "pfr_id": "TestPl00", "sleeper_id": "123",
                "week": 1, "game_type": "REG",
            }
            write_csv(rosters.raw_path_for(2026), roster_fields, [roster_row])
            write_csv(weekly.raw_path_for(2026), roster_fields, [roster_row])

            stat_fields = [
                "player_id", "player_name", "player_display_name", "position", "position_group",
                "season", "week", "season_type", "team", "opponent_team",
                "passing_attempts", "carries", "targets", "field_goal_attempts",
                "pat_attempts", "kickoff_return_yards", "punt_return_yards",
            ]
            write_csv(stats.raw_path_for(2026), stat_fields, [{
                "player_id": "00-TEST", "player_name": "X", "player_display_name": "Wrong Name Is Fine",
                "position": "WR", "position_group": "WR", "season": 2026, "week": 1,
                "season_type": "REG", "team": "NYG", "opponent_team": "DAL",
                "passing_attempts": 0, "carries": 1, "targets": 5, "field_goal_attempts": 0,
                "pat_attempts": 0, "kickoff_return_yards": 42, "punt_return_yards": 11,
            }])

            snap_fields = [
                "game_id", "pfr_game_id", "season", "game_type", "week", "player",
                "pfr_player_id", "position", "team", "opponent", "offense_snaps",
                "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct",
            ]
            write_csv(snaps.raw_path_for(2026), snap_fields, [{
                "game_id": "2026_01_DAL_NYG", "pfr_game_id": "x", "season": 2026,
                "game_type": "REG", "week": 1, "player": "Also Wrong Name",
                "pfr_player_id": "TestPl00", "position": "WR", "team": "NYG", "opponent": "DAL",
                "offense_snaps": 50, "offense_pct": 0.8, "defense_snaps": 0,
                "defense_pct": 0, "st_snaps": 5, "st_pct": 0.2,
            }])

            outputs, audit, _ = build_phase1_outputs(
                root,
                {item.id: item for item in (rosters, weekly, stats, snaps)},
                CANONICAL,
                2026,
            )
            roster_payload = next(payload for path, payload in outputs if "rosters/2026.json" in str(path))
            self.assertEqual("NFLP-one", roster_payload["Records"][0]["CanonicalPlayerID"])

            stats_payload = next(payload for path, payload in outputs if "player-stats" in str(path))
            self.assertEqual("NFLP-one", stats_payload["Records"][0]["CanonicalPlayerID"])
            self.assertEqual(42, stats_payload["Records"][0]["Stats"]["kickoff_return_yards"])
            self.assertEqual(11, stats_payload["Records"][0]["Stats"]["punt_return_yards"])

            snaps_payload = next(payload for path, payload in outputs if "snap-counts" in str(path))
            self.assertEqual("NFLP-one", snaps_payload["Records"][0]["CanonicalPlayerID"])
            self.assertEqual(50, snaps_payload["Records"][0]["OffenseSnaps"])
            self.assertEqual(1, audit["playerStats"]["resolvedIdentityCount"])
            self.assertEqual(1, audit["snapCounts"]["resolvedIdentityCount"])

    def test_sleeper_platform_state_maps_by_sleeper_id_and_keeps_injury_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleeper = sleeper_dataset(root / "raw")
            sleeper.raw_path.parent.mkdir(parents=True, exist_ok=True)
            sleeper.raw_path.write_text(json.dumps({
                "123": {
                    "player_id": "123",
                    "status": "Active",
                    "team": "NYG",
                    "position": "WR",
                    "fantasy_positions": ["WR"],
                    "injury_status": "Questionable",
                    "injury_start_date": "2026-08-20",
                    "practice_participation": "Limited",
                    "depth_chart_position": "WR",
                    "depth_chart_order": 2,
                }
            }), encoding="utf-8")

            outputs, audit, _ = build_phase1_outputs(
                root, {sleeper.id: sleeper}, CANONICAL, 2026
            )
            payload = outputs[0][1]
            record = payload["Records"][0]
            self.assertEqual("NFLP-one", record["CanonicalPlayerID"])
            self.assertEqual("Questionable", record["InjuryStatus"])
            self.assertEqual("2026-08-20", record["InjuryStartDate"])
            self.assertEqual("Limited", record["PracticeParticipation"])
            self.assertEqual(1, audit["sleeperPlayers"]["resolvedIdentityCount"])

    def test_sleeper_object_key_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleeper = sleeper_dataset(root / "raw")
            sleeper.raw_path.parent.mkdir(parents=True, exist_ok=True)
            sleeper.raw_path.write_text(
                json.dumps({"123": {"player_id": "456", "position": "WR", "status": "Active"}}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                build_phase1_outputs(root, {sleeper.id: sleeper}, CANONICAL, 2026)


if __name__ == "__main__":
    unittest.main()
