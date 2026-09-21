import json
import tempfile
import unittest
from pathlib import Path

from tools.nfl_season_context import (
    NflSeasonContextError,
    resolve_nfl_season_context,
    resolve_season_for_date,
)


class NflSeasonContextTests(unittest.TestCase):
    def write_schedule(self, root: Path, season: int, games: list[dict]) -> None:
        path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "Season": season,
                    "SourceDataset": "nflverse.schedules",
                    "Finalized": False,
                    "Games": games,
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def game(game_type: str, week: int, day: str) -> dict:
        return {
            "GameID": f"2026_{week:02d}_{game_type}",
            "GameType": game_type,
            "Week": week,
            "GameDay": day,
        }

    def test_resolves_phase_boundaries_from_canonical_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_schedule(
                root,
                2026,
                [
                    self.game("REG", 1, "2026-09-09"),
                    self.game("REG", 18, "2027-01-10"),
                    self.game("WC", 19, "2027-01-16"),
                    self.game("SB", 22, "2027-02-14"),
                ],
            )
            self.assertEqual(
                "pre_regular_season",
                resolve_nfl_season_context(root, as_of="2026-08-01", season=2026)["phase"],
            )
            regular = resolve_nfl_season_context(root, as_of="2026-09-21", season=2026)
            self.assertEqual("regular_season", regular["phase"])
            self.assertEqual(1, regular["current_week"])
            self.assertEqual(
                "postseason",
                resolve_nfl_season_context(root, as_of="2027-01-12", season=2026)["phase"],
            )
            self.assertEqual(
                "post_regular_season",
                resolve_nfl_season_context(root, as_of="2027-02-20", season=2026)["phase"],
            )

    def test_auto_selects_upcoming_same_year_season_before_week_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_schedule(
                root,
                2025,
                [self.game("REG", 1, "2025-09-04"), self.game("REG", 18, "2026-01-04")],
            )
            self.write_schedule(
                root,
                2026,
                [self.game("REG", 1, "2026-09-09"), self.game("REG", 18, "2027-01-10")],
            )
            self.assertEqual(2026, resolve_season_for_date(root, "2026-07-01"))

    def test_missing_schedule_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(NflSeasonContextError):
                resolve_nfl_season_context(Path(directory), as_of="2026-09-21", season=2026)


if __name__ == "__main__":
    unittest.main()
