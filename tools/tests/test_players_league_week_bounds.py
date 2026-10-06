"""Week bounds of the Players generator come from canonical facts only (#347 I1)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import players_league_scoring as scoring  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAGUE = "test-league"
SEASON = 2030


def write(root: Path, structure, final_weeks, incomplete_stats_weeks=()) -> None:
    league_dir = root / "source-data/leagues" / LEAGUE / "seasons" / str(SEASON)
    league_dir.mkdir(parents=True)
    payload = {} if structure is None else {"WeekStructure": structure}
    (league_dir / "league.json").write_text(json.dumps(payload), encoding="utf-8")
    finality = root / "source-data/nfl/game-finality"
    finality.mkdir(parents=True)
    weeks = [{"GameType": "REG", "Week": w, "WeekFinal": final} for w, final in final_weeks]
    (finality / f"{SEASON}.json").write_text(json.dumps({"Weeks": weeks}), encoding="utf-8")
    schedules = root / "source-data/nfl/schedules"
    schedules.mkdir(parents=True)
    games = [{"GameType": "REG", "Week": w, "HomeTeam": "AAA", "AwayTeam": "BBB"} for w, _ in final_weeks]
    (schedules / f"{SEASON}.json").write_text(json.dumps({"Games": games}), encoding="utf-8")
    stats = root / "source-data/nfl/player-stats" / str(SEASON)
    stats.mkdir(parents=True)
    for week, _ in final_weeks:
        teams = ["AAA"] if week in incomplete_stats_weeks else ["AAA", "BBB"]
        records = [{"SeasonType": "REG", "Team": team} for team in teams]
        (stats / f"{week:02d}.json").write_text(json.dumps({"Records": records}), encoding="utf-8")


class WeekBoundsTest(unittest.TestCase):
    def bounds(self, structure, final_weeks, incomplete_stats_weeks=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, structure, final_weeks, incomplete_stats_weeks)
            return scoring.resolve_league_week_bounds(root, LEAGUE, SEASON)

    def test_bounds_follow_week_structure_and_final_prefix(self) -> None:
        weeks = [(1, True), (2, True), (3, True), (4, False), (5, True)]
        result = self.bounds({"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 14}, weeks)
        self.assertEqual({"LastLeagueWeek": 17, "PlayoffStartWeek": 14, "FinalScoredWeek": 3}, result)

    def test_week_with_incomplete_stats_is_not_scored_final(self) -> None:
        weeks = [(1, True), (2, True), (3, True), (4, True)]
        result = self.bounds({"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 14}, weeks, incomplete_stats_weeks=(4,))
        self.assertEqual(3, result["FinalScoredWeek"])

    def test_missing_stats_partition_is_not_scored_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, {"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 14}, [(1, True), (2, True)])
            (root / "source-data/nfl/player-stats" / str(SEASON) / "02.json").unlink()
            result = scoring.resolve_league_week_bounds(root, LEAGUE, SEASON)
        self.assertEqual(1, result["FinalScoredWeek"])

    def test_final_week_is_capped_at_last_league_week(self) -> None:
        weeks = [(w, True) for w in range(1, 19)]
        result = self.bounds({"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 14}, weeks)
        self.assertEqual(17, result["FinalScoredWeek"])

    def test_final_league_week_is_the_fallback_for_last_week(self) -> None:
        result = self.bounds({"FinalLeagueWeek": 16, "PlayoffStartWeek": 13}, [(1, True)])
        self.assertEqual(16, result["LastLeagueWeek"])

    def test_missing_week_structure_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.bounds(None, [(1, True)])

    def test_missing_playoff_start_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.bounds({"ExpectedLastLeagueWeek": 17}, [(1, True)])

    def test_missing_last_week_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.bounds({"PlayoffStartWeek": 14}, [(1, True)])

    def test_missing_league_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scoring.resolve_league_week_bounds(Path(tmp), LEAGUE, SEASON)

    def test_committed_bounds_agree_with_published_league_json(self) -> None:
        league = json.loads((REPO_ROOT / "public/data/League.json").read_text(encoding="utf-8-sig"))
        season = int(league["Season"])
        result = scoring.resolve_league_week_bounds(REPO_ROOT, scoring.LEAGUE_ID, season)
        for key in ("LastLeagueWeek", "PlayoffStartWeek"):
            self.assertEqual(int(league[key]), result[key], key)
        # Both finality values wait for derived data (Sleeper scoring resp. nflverse stats), so either
        # may lag the other, but neither may run ahead of the NFL game finality.
        games_final = 0
        game_final_weeks = scoring.game_final_regular_weeks(REPO_ROOT, season)
        while games_final + 1 in game_final_weeks:
            games_final += 1
        self.assertLessEqual(result["FinalScoredWeek"], games_final)
        self.assertLessEqual(int(league["FinalScoredWeek"]), games_final)


if __name__ == "__main__":
    unittest.main()
