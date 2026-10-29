"""Tests for the past-season Schedule archive generator (Issue #999 step 7b).

Parity with the published public/data/Schedule.json is the command `python3 tools/schedule_archive.py
compare-current`; it is not a unit test because Schedule.json and the canonical sources are refreshed by
different workflows. These tests pin the conversion rules with a constructed tree.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import schedule_archive as sa  # noqa: E402

TEAMS = {"Teams": [
    {"TeamAbbr": "LA", "Aliases": [{"Alias": "LAR", "Kind": "provider-spelling"}, {"Alias": "STL", "Kind": "historical", "LastSeason": 2015}]},
    {"TeamAbbr": "WAS", "Aliases": [{"Alias": "WSH", "Kind": "provider-spelling"}]},
    {"TeamAbbr": "JAX", "Aliases": []},
    {"TeamAbbr": "BUF", "Aliases": []},
    {"TeamAbbr": "CIN", "Aliases": []},
]}


def game(game_id, game_type, week, day, time, away, home, espn, **extra):
    row = {"GameID": game_id, "GameType": game_type, "Week": week, "GameDay": day, "GameTime": time,
           "AwayTeam": away, "HomeTeam": home, "AwayScore": 20, "HomeScore": 17.0, "Overtime": "0",
           "Location": "Home", "ProviderGameIDs": {"ESPN": espn}}
    row.update(extra)
    return row


def make_tree(root: Path, season: int, games, final) -> None:
    base = root / "data-source" / "nfl"
    (base / "schedules").mkdir(parents=True)
    (base / "game-finality").mkdir(parents=True)
    (base / "teams.json").write_text(json.dumps(TEAMS), encoding="utf-8")
    (base / "schedules" / f"{season}.json").write_text(
        json.dumps({"Season": season, "SourceDataset": "nflverse.schedules", "Games": games}), encoding="utf-8")
    (base / "game-finality" / f"{season}.json").write_text(json.dumps({
        "Season": season, "SourceDataset": "nflverse.game-finality",
        "Games": [{"GameID": g["GameID"], "Final": final[g["GameID"]]} for g in games]}), encoding="utf-8")


class ConversionTests(unittest.TestCase):
    def test_kickoff_uses_the_eastern_zone_of_the_day(self):
        self.assertEqual("1725582000.0", sa.kickoff_epoch("2024-09-05", "20:20"))  # EDT
        self.assertEqual("1735020000.0", sa.kickoff_epoch("2024-12-24", "01:00"))  # EST
        self.assertIsNone(sa.kickoff_epoch("2024-09-05", ""))

    def test_dst_gap_and_overlap_fail_closed(self):
        with self.assertRaises(sa.ScheduleArchiveError):
            sa.kickoff_epoch("2024-03-10", "02:30")
        with self.assertRaises(sa.ScheduleArchiveError):
            sa.kickoff_epoch("2024-11-03", "01:30")

    def test_game_time_text(self):
        self.assertEqual("12:30p", sa.game_time_text("12:30"))
        self.assertEqual("8:20p", sa.game_time_text("20:20"))
        self.assertEqual("12:05a", sa.game_time_text("00:05"))
        self.assertEqual("TBD", sa.game_time_text(None))

    def test_season_type(self):
        self.assertEqual("Regular Season", sa.season_type("REG"))
        self.assertEqual("Post Season", sa.season_type("SB"))
        with self.assertRaises(sa.ScheduleArchiveError):
            sa.season_type("PRE")


class BuildTests(unittest.TestCase):
    def build(self, games, final, season=2023):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, season, games, final)
            return sa.build_schedule(root, season)

    def test_record_shape_provider_spelling_scores_and_sorting(self):
        games = [
            game("g2", "SB", 22, "2024-02-11", "18:30", "JAX", "WAS", "2"),
            game("g1", "REG", 1, "2023-09-10", "13:00", "LA", "WAS", "1", Overtime="1"),
        ]
        records = self.build(games, {"g1": True, "g2": False})
        self.assertEqual(["g1", "g2"], [r["CanonicalGameID"] for r in records])
        first = records[0]
        self.assertEqual("20230910_LAR@WSH", first["gameID"])
        self.assertEqual("Final/OT", first["gameStatus"])
        self.assertEqual((20, 17), (first["awayPts"], first["homePts"]))
        self.assertEqual(["LA", "WAS"], [first["away"], first["home"]])
        self.assertTrue(first["cbsLink"].endswith("NFL_20230910_LAR@WAS"))
        self.assertEqual("Post Season", records[1]["seasonType"])
        self.assertEqual("Scheduled", records[1]["gameStatus"])
        self.assertNotIn("awayPts", records[1])
        self.assertTrue(records[1]["cbsLink"].endswith("NFL_20240211_JAC@WAS"))

    def test_finality_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            games = [game("g1", "REG", 1, "2023-09-10", "13:00", "LA", "WAS", "1")]
            make_tree(root, 2023, games, {"g1": True})
            path = root / "data-source" / "nfl" / "game-finality" / "2023.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["Games"] = []
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(sa.ScheduleArchiveError):
                sa.build_schedule(root, 2023)

    def test_duplicate_espn_id_fails_closed(self):
        games = [game("g1", "REG", 1, "2023-09-10", "13:00", "LA", "WAS", "1"),
                 game("g2", "REG", 1, "2023-09-17", "13:00", "WAS", "LA", "1")]
        with self.assertRaises(sa.ScheduleArchiveError):
            self.build(games, {"g1": True, "g2": True})

    def test_supplement_is_added_as_canceled_game(self):
        games = [game("2022_01", "REG", 1, "2022-09-11", "13:00", "BUF", "JAX", "9")]
        records = self.build(games, {"2022_01": True}, season=2022)
        cancelled = [r for r in records if r["gameStatus"] == "Canceled"]
        self.assertEqual(1, len(cancelled))
        self.assertEqual("20230102_BUF@CIN", cancelled[0]["gameID"])
        self.assertEqual("0", cancelled[0]["gameStatusCode"])
        self.assertNotIn("awayPts", cancelled[0])


class FirstNeededSeasonTests(unittest.TestCase):
    def test_comes_from_league_seasons_and_the_salary_model_history(self):
        from derived_data_lib.models.registry import get_model

        history = get_model("salary-v1").HISTORY_SEASONS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = {"2030": {"Models": {"Salary": "salary-v1", "SalaryCap": "salary-cap-v1", "Grading": "grading-v1"}}}
            with unittest.mock.patch.object(sa, "load_all_league_metadata", return_value={"x": {"Seasons": meta}}):
                self.assertEqual(2030 - history, sa.first_needed_season(root))
