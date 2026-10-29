import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nfl_source_data_lib.common import Dataset, load_registry
from nfl_source_data_lib.phase1 import build_phase1_outputs
from test_nfl_source_phase1_datasets import fixed_seasonal_dataset, write_csv

CANONICAL = [
    {"CanonicalPlayerID": "NFLP-one", "IDs": {"GSIS": "00-ONE", "ESPN": "111"}, "IDAliases": {}},
]

SCHEDULE_FIELDS = [
    "game_id", "season", "game_type", "week", "gameday", "weekday", "gametime",
    "away_team", "away_score", "home_team", "home_score", "espn",
]
QBR_FIELDS = [
    "season", "season_type", "game_id", "week_num", "player_id", "name_display", "team_abb",
    "opp_abb", "rank", "qbr_total", "qbr_raw", "pts_added", "qb_plays", "epa_total",
    "pass", "run", "exp_sack", "penalty", "sack", "qualified",
]


def qbr_dataset(root: Path) -> Dataset:
    dataset = fixed_seasonal_dataset(root, "nflverse.espn-qbr-week")
    return dataset


def schedule_row(game_id: str, week: int, espn: str, away: str = "AAA", home: str = "BBB") -> dict[str, object]:
    return {
        "game_id": game_id, "season": 2026, "game_type": "REG", "week": week,
        "gameday": "2026-09-13", "weekday": "Sunday", "gametime": "13:00",
        "away_team": away, "away_score": 10, "home_team": home, "home_score": 20, "espn": espn,
    }


def qbr_row(game_id: str, player_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season": 2026, "season_type": "Regular", "game_id": game_id, "week_num": 1,
        "player_id": player_id, "name_display": "Some QB", "team_abb": "AAA", "opp_abb": "BBB",
        "rank": 3, "qbr_total": 61.5, "qbr_raw": 58.0, "pts_added": 2.5, "qb_plays": 30,
        "epa_total": 2.1, "pass": 1.5, "run": 0.4, "exp_sack": 0, "penalty": 0.2, "sack": -0.1,
        "qualified": "TRUE",
    }
    row.update(overrides)
    return row


class QbrWeekTests(unittest.TestCase):
    def build(self, root: Path, schedule_rows, qbr_rows, canonical=CANONICAL):
        schedules = fixed_seasonal_dataset(root / "raw", "nflverse.schedules")
        qbr = qbr_dataset(root / "raw")
        write_csv(schedules.raw_path, SCHEDULE_FIELDS, schedule_rows)
        write_csv(qbr.raw_path, QBR_FIELDS, qbr_rows)
        return build_phase1_outputs(
            root, {schedules.id: schedules, qbr.id: qbr}, canonical, 2026
        )

    def partition(self, outputs, season=2026):
        return next(
            payload for path, payload in outputs
            if path.parts[-2:] == ("qbr-week", f"{season}.json")
        )

    def test_repository_registry_activates_qbr_as_fixed_seasonal_dataset(self):
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        dataset = active["nflverse.espn-qbr-week"]
        self.assertTrue(dataset.materialize)
        self.assertEqual("fixed", dataset.source_mode)
        self.assertEqual("required", dataset.availability_policy)
        self.assertEqual("seasonal-finalizable", dataset.lifecycle_class)
        self.assertEqual("season", dataset.partition_key)

    def test_join_uses_espn_athlete_id_and_schedule_espn_game_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs, audit, _ = self.build(
                Path(tmp),
                [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                [qbr_row("9001", "111", name_display="Wrong Name Is Fine")],
            )
            payload = self.partition(outputs)
            record = payload["Records"][0]
            self.assertEqual("NFLP-one", record["CanonicalPlayerID"])
            self.assertEqual("2026_01_AAA_BBB", record["GameID"])
            self.assertEqual({"ESPN": "9001"}, record["ProviderGameIDs"])
            self.assertEqual(61.5, record["QBRTotal"])
            self.assertEqual(-0.1, record["Components"]["Sack"])
            self.assertEqual(1, audit["qbrWeek"]["resolvedIdentityCount"])
            self.assertEqual(0, audit["qbrWeek"]["unresolvedIdentityCount"])

    def test_unpublished_game_is_distinct_from_rated_game_and_never_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs, audit, _ = self.build(
                Path(tmp),
                [
                    schedule_row("2026_01_AAA_BBB", 1, "9001"),
                    schedule_row("2026_04_CCC_DDD", 4, "9004", "CCC", "DDD"),
                ],
                [qbr_row("9001", "111")],
            )
            payload = self.partition(outputs)
            status = {game["GameID"]: game["QBRStatus"] for game in payload["Games"]}
            self.assertEqual("published", status["2026_01_AAA_BBB"])
            self.assertEqual("not-yet-available", status["2026_04_CCC_DDD"])
            self.assertEqual(1, len(payload["Records"]))
            self.assertEqual(1, audit["qbrWeek"]["publishedGameCount"])
            self.assertEqual(1, audit["qbrWeek"]["notYetAvailableGameCount"])

    def test_missing_metric_stays_null_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs, _, _ = self.build(
                Path(tmp),
                [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                [qbr_row("9001", "111", qbr_total="NA", exp_sack="")],
            )
            record = self.partition(outputs)["Records"][0]
            self.assertIsNone(record["QBRTotal"])
            self.assertIsNone(record["Components"]["ExpSack"])

    def test_unmapped_espn_player_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs, audit, _ = self.build(
                Path(tmp),
                [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                [qbr_row("9001", "999")],
            )
            record = self.partition(outputs)["Records"][0]
            self.assertIsNone(record["CanonicalPlayerID"])
            self.assertEqual("unresolved", record["IdentityResolution"]["Status"])
            self.assertEqual(1, audit["qbrWeek"]["unresolvedIdentityCount"])

    def test_unknown_game_duplicate_row_and_season_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                self.build(
                    Path(tmp) / "a",
                    [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                    [qbr_row("4242", "111")],
                )
            with self.assertRaises(ValueError):
                self.build(
                    Path(tmp) / "b",
                    [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                    [qbr_row("9001", "111"), qbr_row("9001", "111")],
                )
            old_game = schedule_row("2025_01_AAA_BBB", 1, "8001")
            old_game["season"] = 2025
            with self.assertRaises(ValueError):
                self.build(
                    Path(tmp) / "c",
                    [schedule_row("2026_01_AAA_BBB", 1, "9001"), old_game],
                    [qbr_row("8001", "111", season=2026)],
                )

    def test_source_team_is_kept_verbatim_even_when_it_is_not_a_game_participant(self):
        # ESPN labels a traded QB with the later team; the materializer must not reject or rewrite it.
        with tempfile.TemporaryDirectory() as tmp:
            outputs, _, _ = self.build(
                Path(tmp),
                [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                [qbr_row("9001", "111", team_abb="ZZZ")],
            )
            self.assertEqual("ZZZ", self.partition(outputs)["Records"][0]["SourceTeam"])

    def test_only_current_and_persisted_seasons_are_materialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [schedule_row("2026_01_AAA_BBB", 1, "9001")]
            old = schedule_row("2025_01_AAA_BBB", 1, "8001")
            old["season"] = 2025
            outputs, _, _ = self.build(
                root,
                rows + [old],
                [qbr_row("9001", "111"), qbr_row("8001", "111", season=2025)],
            )
            seasons = sorted(
                int(path.stem) for path, _ in outputs if path.parent.name == "qbr-week"
            )
            self.assertEqual([2026], seasons)

    def test_materialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = (
                [schedule_row("2026_01_AAA_BBB", 1, "9001")],
                [qbr_row("9001", "111")],
            )
            first, _, _ = self.build(Path(tmp) / "x", *args)
            second, _, _ = self.build(Path(tmp) / "y", *args)
            self.assertEqual(
                json.dumps(self.partition(first), sort_keys=True),
                json.dumps(self.partition(second), sort_keys=True),
            )


if __name__ == "__main__":
    unittest.main()
