from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.week_structure import (  # noqa: E402
    derive_season_week_structures,
    resolve_nfl_regular_season_week_ceiling,
)


class LeagueSourceWeekStructureTests(unittest.TestCase):
    def _write_schedule(self, root: Path, season: int, week_count: int, *, missing_week: int | None = None) -> None:
        games = []
        for week in range(1, week_count + 1):
            if week == missing_week:
                continue
            games.append(
                {
                    "GameID": f"{season}_{week:02d}_A_B",
                    "GameType": "REG",
                    "Week": week,
                }
            )
        path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"SchemaVersion": 2, "Season": season, "Games": games}),
            encoding="utf-8",
        )

    def test_nfl_week_ceiling_is_dynamic_per_season(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_schedule(root, 2026, 18)
            self._write_schedule(root, 2027, 19)
            self.assertEqual(resolve_nfl_regular_season_week_ceiling(root, 2026), 18)
            self.assertEqual(resolve_nfl_regular_season_week_ceiling(root, 2027), 19)

    def test_nfl_week_ceiling_fails_closed_on_missing_or_gapped_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                resolve_nfl_regular_season_week_ceiling(root, 2026)
            self._write_schedule(root, 2026, 18, missing_week=7)
            with self.assertRaises(ValueError):
                resolve_nfl_regular_season_week_ceiling(root, 2026)

    @staticmethod
    def _league(
        season: int,
        *,
        status: str,
        playoff_start: int,
        playoff_teams: int,
        playoff_round_type: int,
        last_scored_leg: int | None,
    ) -> dict:
        settings = {
            "start_week": 1,
            "playoff_week_start": playoff_start,
            "playoff_teams": playoff_teams,
            "playoff_round_type": playoff_round_type,
        }
        if last_scored_leg is not None:
            settings["last_scored_leg"] = last_scored_leg
        return {"season": str(season), "status": status, "settings": settings}

    @staticmethod
    def _bracket(rounds: int) -> list[dict]:
        return [{"r": round_number, "m": round_number} for round_number in range(1, rounds + 1)]

    @staticmethod
    def _matchups(last_week: int, ceiling: int = 18) -> dict[int, object]:
        return {
            week: ([{"roster_id": 1, "matchup_id": 1}] if week <= last_week else [])
            for week in range(1, ceiling + 1)
        }

    def test_playoff_format_is_season_specific_and_projects_only_from_history(self) -> None:
        structures = derive_season_week_structures(
            [
                (
                    self._league(
                        2024,
                        status="complete",
                        playoff_start=16,
                        playoff_teams=4,
                        playoff_round_type=1,
                        last_scored_leg=17,
                    ),
                    self._bracket(2),
                    self._matchups(17),
                    18,
                ),
                (
                    self._league(
                        2025,
                        status="complete",
                        playoff_start=14,
                        playoff_teams=4,
                        playoff_round_type=2,
                        last_scored_leg=17,
                    ),
                    self._bracket(2),
                    self._matchups(17),
                    18,
                ),
                (
                    self._league(
                        2026,
                        status="in_season",
                        playoff_start=14,
                        playoff_teams=4,
                        playoff_round_type=2,
                        last_scored_leg=None,
                    ),
                    [],
                    self._matchups(1),
                    18,
                ),
            ]
        )
        by_season = {item["Season"]: item for item in structures}
        self.assertEqual(by_season[2024]["ObservedPlayoffFormat"], "one-week-rounds")
        self.assertEqual(by_season[2024]["FinalLeagueWeek"], 17)
        self.assertEqual(by_season[2025]["ObservedPlayoffFormat"], "two-week-rounds")
        self.assertEqual(by_season[2025]["FinalLeagueWeek"], 17)
        self.assertEqual(by_season[2026]["ProjectedPlayoffFormat"], "two-week-rounds")
        self.assertEqual(by_season[2026]["ExpectedLastLeagueWeek"], 17)
        self.assertEqual(
            by_season[2026]["ProjectionEvidence"],
            {"Source": "historical-same-playoff-round-type", "EvidenceSeasons": [2025]},
        )

    def test_same_provider_round_type_with_conflicting_history_fails_closed(self) -> None:
        inputs = [
            (
                self._league(
                    2024,
                    status="complete",
                    playoff_start=16,
                    playoff_teams=4,
                    playoff_round_type=2,
                    last_scored_leg=17,
                ),
                self._bracket(2),
                self._matchups(17),
                18,
            ),
            (
                self._league(
                    2025,
                    status="complete",
                    playoff_start=14,
                    playoff_teams=4,
                    playoff_round_type=2,
                    last_scored_leg=17,
                ),
                self._bracket(2),
                self._matchups(17),
                18,
            ),
        ]
        with self.assertRaises(ValueError):
            derive_season_week_structures(inputs)


if __name__ == "__main__":
    unittest.main()
