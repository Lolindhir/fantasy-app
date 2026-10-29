"""Shared week-final definition (ADR-071, Issue #897): synthetic timeline, fail-closed cases, legacy parity."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import players_league_scoring as scoring  # noqa: E402
from derived_data_lib.week_finality import WeekFinalityError, resolve_week_finality  # noqa: E402

REPO_ROOT = TOOLS.parent
LEAGUE = "test-league"
SEASON = 2030
TEAMS = ("AAA", "BBB", "CCC", "DDD")


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build(root: Path, *, scored: int, final_weeks, stats: dict[int, tuple[str, ...]], last=17, extra=None) -> None:
    structure = {"StartWeek": 1, "ExpectedLastLeagueWeek": last, "LastScoredLeg": scored, "PlayoffStartWeek": 14}
    structure.update(extra or {})
    write(root / f"data-source/leagues/{LEAGUE}/seasons/{SEASON}/league.json", {"WeekStructure": structure})
    weeks = [
        {"GameType": "REG", "Week": w, "ApplicableGameCount": 2, "FinalGameCount": 2 if w in final_weeks else 0,
         "WeekFinal": w in final_weeks}
        for w in range(1, last + 1)
    ]
    write(root / f"data-source/nfl/game-finality/{SEASON}.json", {"Finalized": False, "Weeks": weeks})
    games = [
        {"GameType": "REG", "Week": w, "HomeTeam": TEAMS[0], "AwayTeam": TEAMS[1]} for w in range(1, last + 1)
    ] + [
        {"GameType": "REG", "Week": w, "HomeTeam": TEAMS[2], "AwayTeam": TEAMS[3]} for w in range(1, last + 1)
    ]
    write(root / f"data-source/nfl/schedules/{SEASON}.json", {"Games": games})
    for week, teams in stats.items():
        write(root / f"data-source/nfl/player-stats/{SEASON}/{week:02d}.json",
              {"Records": [{"Team": team, "SeasonType": "REG"} for team in teams]})


class SyntheticTimelineTest(unittest.TestCase):
    def resolve(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp), **kwargs)
            return resolve_week_finality(Path(tmp), LEAGUE, SEASON)

    def test_week_seven_timeline(self):
        done = {w: TEAMS for w in range(1, 7)}
        # games final, stats cover 2 of 4 teams, league not scored yet
        step = self.resolve(scored=6, final_weeks=set(range(1, 8)), stats={**done, 7: TEAMS[:2]})
        self.assertEqual((6, 6), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))
        self.assertEqual(["NflStatsComplete", "LeagueScored"], step["Weeks"][6]["Pending"])
        # league scored, stats still incomplete
        step = self.resolve(scored=7, final_weeks=set(range(1, 8)), stats={**done, 7: TEAMS[:2]})
        self.assertEqual((7, 6), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))
        self.assertEqual(["NflStatsComplete"], step["Weeks"][6]["Pending"])
        # stats complete
        step = self.resolve(scored=7, final_weeks=set(range(1, 8)), stats={**done, 7: TEAMS})
        self.assertEqual((7, 7), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))
        self.assertEqual([], step["Weeks"][6]["Pending"])

    def test_stats_before_league_scoring(self):
        step = self.resolve(scored=0, final_weeks={1}, stats={1: TEAMS})
        self.assertEqual((0, 1), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))

    def test_milestones_are_gapless_runs(self):
        step = self.resolve(scored=5, final_weeks={1, 2, 4, 5}, stats={w: TEAMS for w in (1, 2, 4, 5)})
        self.assertEqual((2, 2), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))

    def test_nothing_final_yet_is_zero_not_an_error(self):
        step = self.resolve(scored=0, final_weeks=set(), stats={})
        self.assertEqual((0, 0), (step["LeagueScoredWeek"], step["StatsFinalWeek"]))

    def test_milestones_are_capped_at_last_league_week(self):
        step = self.resolve(scored=3, final_weeks=set(range(1, 4)), stats={w: TEAMS for w in range(1, 4)}, last=3)
        self.assertEqual(3, step["LastLeagueWeek"])
        self.assertEqual(3, len(step["Weeks"]))

    def test_contradicting_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root, scored=20, final_weeks=set(), stats={})
            with self.assertRaises(WeekFinalityError):
                resolve_week_finality(root, LEAGUE, SEASON)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root, scored=1, final_weeks={1}, stats={})
            path = root / f"data-source/nfl/game-finality/{SEASON}.json"
            payload = json.loads(path.read_text())
            payload["Weeks"][0]["FinalGameCount"] = 1
            write(path, payload)
            with self.assertRaises(WeekFinalityError):
                resolve_week_finality(root, LEAGUE, SEASON)
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp), scored=1, final_weeks=set(), stats={}, last=19)
            with self.assertRaises(WeekFinalityError):
                resolve_week_finality(Path(tmp), LEAGUE, SEASON)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WeekFinalityError):
                resolve_week_finality(Path(tmp), LEAGUE, SEASON)

    def test_completed_league_season_without_finality_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root, scored=17, final_weeks=set(range(1, 18)), stats={})
            (root / f"data-source/nfl/game-finality/{SEASON}.json").unlink()
            with self.assertRaises(WeekFinalityError):
                resolve_week_finality(root, LEAGUE, SEASON)

    def test_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp), scored=1, final_weeks={1}, stats={1: TEAMS})
            out = subprocess.run(
                [sys.executable, str(TOOLS / "week_finality.py"), "bounds", "--league", LEAGUE,
                 "--season", str(SEASON), "--repo-root", tmp],
                capture_output=True, text=True, check=True)
            payload = json.loads(out.stdout)
            self.assertEqual((1, 1), (payload["LeagueScoredWeek"], payload["StatsFinalWeek"]))


class LegacyParityTest(unittest.TestCase):
    """The new milestones equal the rules they replace, on whatever canonical seasons exist."""

    def seasons(self):
        base = REPO_ROOT / "data-source/leagues" / scoring.LEAGUE_ID / "seasons"
        return sorted(int(p.name) for p in base.iterdir() if (p / "league.json").is_file())

    def test_stats_final_week_equals_players_rule(self):
        for season in self.seasons():
            with self.subTest(season=season):
                legacy = scoring.resolve_league_week_bounds(REPO_ROOT, scoring.LEAGUE_ID, season)
                new = resolve_week_finality(REPO_ROOT, scoring.LEAGUE_ID, season)
                self.assertEqual(legacy["FinalScoredWeek"], new["StatsFinalWeek"])
                self.assertEqual(legacy["LastLeagueWeek"], new["LastLeagueWeek"])

    def test_league_scored_week_equals_twp_rule(self):
        for season in self.seasons():
            with self.subTest(season=season):
                new = resolve_week_finality(REPO_ROOT, scoring.LEAGUE_ID, season)
                final = scoring.game_final_regular_weeks(REPO_ROOT, season)
                expected = 0
                while expected + 1 in final and expected + 1 <= new["LastScoredLeg"]:
                    expected += 1
                self.assertEqual(expected, new["LeagueScoredWeek"])


if __name__ == "__main__":
    unittest.main()
