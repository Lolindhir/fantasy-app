from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from nfl_season_context import NflSeasonContextError, resolve_nfl_season_context


class NflSeasonContextTests(unittest.TestCase):
    def write_schedule(self, root: Path, season: int, games: list[dict]) -> None:
        path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "SchemaVersion": 2,
                "Season": season,
                "SourceDataset": "nflverse.schedules",
                "Finalized": False,
                "Games": games,
            }),
            encoding="utf-8",
        )

    def fixture_games(self) -> list[dict]:
        return [
            {"GameID": "a", "GameType": "REG", "Week": 1, "GameDay": "2026-09-10"},
            {"GameID": "b", "GameType": "REG", "Week": 2, "GameDay": "2026-09-17"},
            {"GameID": "c", "GameType": "REG", "Week": 18, "GameDay": "2027-01-10"},
        ]

    def test_resolves_pre_regular_regular_and_post_regular_phases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_schedule(root, 2026, self.fixture_games())

            pre = resolve_nfl_season_context(root, as_of="2026-09-01", season=2026)
            regular = resolve_nfl_season_context(root, as_of="2026-09-21", season=2026)
            post = resolve_nfl_season_context(root, as_of="2027-01-11", season=2026)

            self.assertEqual("pre_regular_season", pre["phase"])
            self.assertIsNone(pre["regular_season"]["current_week"])
            self.assertEqual("regular_season", regular["phase"])
            self.assertEqual(2, regular["regular_season"]["current_week"])
            self.assertEqual("post_regular_season", post["phase"])
            self.assertEqual(18, post["regular_season"]["current_week"])

    def test_auto_selects_schedule_without_sleeper_or_league_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_schedule(root, 2025, [
                {"GameID": "a", "GameType": "REG", "Week": 18, "GameDay": "2026-01-04"},
            ])
            self.write_schedule(root, 2026, self.fixture_games())

            context = resolve_nfl_season_context(root, as_of="2026-09-21")

            self.assertEqual(2026, context["season"])
            self.assertEqual("regular_season", context["phase"])
            self.assertEqual(
                "source-data/nfl/schedules/2026.json",
                context["source"]["path"],
            )

    def test_fails_closed_without_regular_season_games(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_schedule(root, 2026, [
                {"GameID": "x", "GameType": "WC", "Week": 1, "GameDay": "2027-01-16"},
            ])
            with self.assertRaisesRegex(NflSeasonContextError, "no REG games"):
                resolve_nfl_season_context(root, as_of="2026-09-21", season=2026)


if __name__ == "__main__":
    unittest.main()
