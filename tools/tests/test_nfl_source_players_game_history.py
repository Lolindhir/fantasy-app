"""#347 G3: Players.json GameHistory from canonical NFL facts (synthetic fixtures, no real players)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import players_game_history as gh  # noqa: E402

SEASON = 2026
QB, RB, KR = "NFLP-qb", "NFLP-rb", "NFLP-k"


def write(root: Path, relative: str, payload: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def stat_row(cid: str, team: str, game_id: str, week: int, position: str, **stats: object) -> dict:
    return {
        "CanonicalPlayerID": cid, "Position": position, "SeasonType": "REG", "Week": week, "Team": team,
        "Stats": {"game_id": game_id, **stats},
    }


def game(game_id: str, week: int, day: str, away: str, home: str, **extra: object) -> dict:
    return {"GameID": game_id, "GameType": "REG", "Week": week, "GameDay": day, "GameTime": "13:00",
            "AwayTeam": away, "HomeTeam": home, **extra}


class GameHistoryFixture:
    """Two REG games for the Rams/49ers (canonical LA, legacy spelling LAR) plus a third one in week 2."""

    def __init__(self, *, with_qbr: bool = True, long_gain_games: tuple[str, ...] = ("2026_01_SF_LA",)) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "source-data/nfl").mkdir(parents=True)
        shutil.copy(ROOT / "source-data/nfl/teams.json", self.root / "source-data/nfl/teams.json")
        write(self.root, f"source-data/nfl/schedules/{SEASON}.json", {"Season": SEASON, "Games": [
            game("2026_01_SF_LA", 1, "2026-09-13", "SF", "LA", AwayScore=27, HomeScore=7),
            game("2026_02_LA_SF", 2, "2026-09-20", "LA", "SF"),
            game("2026_02_WAS_KC", 2, "2026-09-20", "WAS", "KC"),
        ]})
        write(self.root, f"source-data/nfl/game-finality/{SEASON}.json", {"Season": SEASON, "Weeks": [
            {"GameType": "REG", "Week": 1, "WeekFinal": True}, {"GameType": "REG", "Week": 2, "WeekFinal": False}]})
        write(self.root, f"source-data/nfl/player-stats/{SEASON}/01.json", {"Season": SEASON, "Week": 1, "Records": [
            stat_row(QB, "LA", "2026_01_SF_LA", 1, "QB", attempts=30, completions=20, passing_yards=300, passing_tds=3,
                     passing_interceptions=0, carries=1, rushing_yards=-2),
            stat_row(KR, "SF", "2026_01_SF_LA", 1, "K", fg_att=2, fg_made=1, fg_missed=1, fg_long=44, pat_att=3, pat_made=3),
            stat_row(RB, "SF", "2026_01_SF_LA", 1, "RB", carries=3, rushing_yards=4, targets=2, receptions=1, receiving_yards=5),
        ]})
        write(self.root, f"source-data/nfl/player-stats/{SEASON}/02.json", {"Season": SEASON, "Week": 2, "Records": [
            stat_row(RB, "SF", "2026_02_LA_SF", 2, "RB", carries=5, rushing_yards=11),
        ]})
        write(self.root, f"source-data/nfl/snap-counts/{SEASON}/01.json", {"Season": SEASON, "Week": 1, "Records": [
            {"CanonicalPlayerID": RB, "GameID": "2026_01_SF_LA", "GameType": "REG", "Team": "SF", "OffenseSnaps": 20, "OffensePct": 0.33},
            {"CanonicalPlayerID": QB, "GameID": "2026_01_SF_LA", "GameType": "REG", "Team": "LA", "OffenseSnaps": 60, "OffensePct": 1.0},
        ]})
        write(self.root, f"source-data/nfl/snap-counts/{SEASON}/02.json", {"Season": SEASON, "Week": 2, "Records": [
            # special-teams-only player without a stat line: a played game with zero points
            {"CanonicalPlayerID": QB, "GameID": "2026_02_LA_SF", "GameType": "REG", "Team": "LA", "OffenseSnaps": 0, "OffensePct": 0.0},
        ]})
        write(self.root, f"source-data/nfl/qbr-week/{SEASON}.json", {"Season": SEASON, "Games": [], "Records": (
            [{"CanonicalPlayerID": QB, "GameID": "2026_01_SF_LA", "QBRTotal": 83.6}] if with_qbr else [])})
        write(self.root, f"source-data/nfl/player-game-long-gains/{SEASON}.json", {
            "Season": SEASON,
            "Games": [{"GameID": g} for g in long_gain_games],
            "Records": [
                {"CanonicalPlayerID": QB, "GameID": "2026_01_SF_LA", "GainType": "LongRush", "Yards": -2},
                {"CanonicalPlayerID": RB, "GameID": "2026_01_SF_LA", "GainType": "LongRush", "Yards": 3},
                {"CanonicalPlayerID": RB, "GameID": "2026_01_SF_LA", "GainType": "LongRush", "Yards": 1},
            ]})
        self.points = {QB: {1: {"points": 24.5}}, KR: {1: {"points": 9.0}}, RB: {1: {"points": 5.1}, 2: {"points": 1.1}}}

    def build(self, points_unavailable=None):
        return gh.build_game_histories(self.root, SEASON, {QB, RB, KR}, self.points, points_unavailable)

    def close(self) -> None:
        self.tmp.cleanup()


class RoundingTests(unittest.TestCase):
    def test_half_up_uses_exact_fractions(self) -> None:
        self.assertEqual(gh.half_up(1, 4), 0.3)   # 0.25 -> 0.3 (binary floats would give 0.2)
        self.assertEqual(gh.half_up(5, 40), 0.1)  # 0.125 -> 0.1
        self.assertEqual(gh.half_up(7, 3), 2.3)
        self.assertEqual(gh.half_up(9, 0), 0.0)
        self.assertEqual(gh.half_up(-2, 1), -2.0)

    def test_passer_rating_caps_and_empty(self) -> None:
        self.assertEqual(gh.passer_rating(30, 30, 500, 10, 0), 158.3)
        self.assertEqual(gh.passer_rating(0, 0, 0, 0, 0), 0.0)
        self.assertEqual(gh.passer_rating(0, 10, 0, 0, 5), 0.0)

    def test_passer_rating_matches_reference_line(self) -> None:
        # 25/40, 300 yards, 2 TD, 1 INT: (1.625 + 1.125 + 1.0 + 1.75) / 6 * 100 = 91.666.. -> 91.7
        self.assertEqual(gh.passer_rating(25, 40, 300, 2, 1), 91.7)


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = GameHistoryFixture()
        self.addCleanup(self.fx.close)

    def test_entry_rule_and_order(self) -> None:
        entries, counters = self.fx.build()
        self.assertEqual([e["Week"] for e in entries[QB]], [2, 1], "newest game first")
        self.assertEqual(counters["snap_only_entries"], 1)
        snap_only = entries[QB][0]
        self.assertEqual((snap_only["FantasyPoints"], snap_only["SnapCount"], snap_only["Attempts"]), (0.0, 0, 0))
        for block in ("Passing", "Rushing", "Receiving", "Kicking"):
            self.assertNotIn(block, snap_only)

    def test_game_id_and_team_keys(self) -> None:
        entries, _ = self.fx.build()
        first = entries[QB][1]
        self.assertEqual(first["GameID"], "20260913_SF@LAR", "legacy provider spelling inside GameID")
        self.assertEqual((first["Home"], first["Away"], first["TeamID"], first["TeamAbv"]), ("LA", "SF", "LA", "LA"))
        self.assertEqual((first["HomePoints"], first["AwayPoints"]), (7, 27))
        self.assertTrue(first["WeekFinal"])
        self.assertFalse(entries[QB][0]["WeekFinal"])
        self.assertIsNone(entries[QB][0]["HomePoints"], "no score before the game is final")

    def test_blocks_follow_counting_stats(self) -> None:
        entries, _ = self.fx.build()
        qb = entries[QB][1]
        self.assertEqual(set(qb) & {"Passing", "Rushing", "Receiving", "Kicking"}, {"Passing", "Rushing"})
        self.assertEqual(qb["Passing"]["Rating"], 132.6)
        self.assertEqual(qb["Passing"]["PassAvg"], 10.0)
        self.assertEqual(qb["Passing"]["QBRating"], 83.6)
        self.assertEqual(qb["Rushing"]["RushAvg"], -2.0)
        self.assertEqual(qb["Touchdowns"], 3)
        self.assertEqual(qb["Attempts"], 31)
        self.assertEqual((qb["SnapCount"], qb["SnapPercentage"]), (60, 1.0))

    def test_kicker_uses_attempts_as_snaps(self) -> None:
        entries, _ = self.fx.build()
        kick = entries[KR][0]
        self.assertEqual((kick["SnapCount"], kick["SnapPercentage"]), (5, 1))
        self.assertEqual(kick["Kicking"]["KickingPts"], 6.0)
        self.assertEqual(kick["Kicking"]["FgPct"], 50.0)
        self.assertEqual(kick["Kicking"]["FgLong"], 44)
        self.assertEqual(kick["Kicking"]["XpMissed"], 0)
        self.assertNotIn("Passing", kick)

    def test_long_gains_zero_unknown_and_negative(self) -> None:
        entries, _ = self.fx.build()
        rb_week1 = entries[RB][1]
        self.assertEqual(rb_week1["Rushing"]["LongRush"], 3, "maximum of the records")
        self.assertEqual(rb_week1["Receiving"]["LongReceptions"], 0, "covered game without a record")
        self.assertEqual(entries[QB][1]["Rushing"]["LongRush"], -2, "a negative long gain is kept")
        self.assertIsNone(entries[RB][0]["Rushing"]["LongRush"], "game not yet covered by the dataset is unknown")

    def test_missing_qbr_is_null(self) -> None:
        fx = GameHistoryFixture(with_qbr=False)
        self.addCleanup(fx.close)
        entries, _ = fx.build()
        self.assertIsNone(entries[QB][1]["Passing"]["QBRating"])

    def test_unscorable_game_is_skipped_not_zero(self) -> None:
        entries, counters = self.fx.build({RB: [(SEASON, 1)]})
        self.assertEqual([e["Week"] for e in entries[RB]], [2])
        self.assertEqual(counters["games_skipped_points_unavailable"], 1)

    def test_game_missing_in_schedule_fails_closed(self) -> None:
        write(self.fx.root, f"source-data/nfl/player-stats/{SEASON}/03.json", {"Season": SEASON, "Week": 3, "Records": [
            stat_row(RB, "SF", "2026_03_XX_YY", 3, "RB", carries=1)]})
        with self.assertRaises(gh.GameHistoryError):
            self.fx.build()

    def test_stat_row_without_points_fails_closed(self) -> None:
        del self.fx.points[RB][1]
        with self.assertRaises(gh.GameHistoryError):
            self.fx.build()


class GeneratorContractTests(unittest.TestCase):
    def test_request_players_has_no_games_json_or_tank01_history(self) -> None:
        source = (ROOT / "public/requests/RequestPlayers.ps1").read_text(encoding="utf-8")
        for needle in ("Games.json", "playerStats", "Tank01ID", "$playerHistory", "Update-PlayerGameHistoryLeaguePoints"):
            self.assertNotIn(needle, source)
        self.assertIn("ConvertTo-PlayerGameHistory", source)


if __name__ == "__main__":
    unittest.main()
