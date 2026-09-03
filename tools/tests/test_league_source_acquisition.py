from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.acquire import persist_raw_plans, plan_raw_acquisition  # noqa: E402
from league_source_data_lib.core import SleeperLeagueInstance  # noqa: E402
from league_source_data_lib.registry import load_league_registry  # noqa: E402
from league_source_data_lib.week_structure import resolve_nfl_regular_season_week_ceiling  # noqa: E402


class LeagueSourceAcquisitionTests(unittest.TestCase):
    def _root_with_registry(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        target = root / "source-data"
        target.mkdir(parents=True)
        source = Path(__file__).resolve().parents[2] / "source-data/league-registry.json"
        target.joinpath("league-registry.json").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return temporary, root

    @staticmethod
    def _write_schedule(root: Path, season: int, last_week: int) -> None:
        schedule_path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        schedule_path.parent.mkdir(parents=True, exist_ok=True)
        games = [
            {"GameID": f"{season}_{week:02d}_A_B", "GameType": "REG", "Week": week}
            for week in range(1, last_week + 1)
        ]
        games.append({"GameID": f"{season}_WC_A_B", "GameType": "WC", "Week": 1})
        schedule_path.write_text(
            json.dumps(
                {"SchemaVersion": 2, "Season": season, "SourceDataset": "nflverse.schedules", "Games": games}
            ),
            encoding="utf-8",
        )

    def test_registry_uses_dynamic_schedule_bound_for_week_scopes(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            datasets = {item.id: item for item in load_league_registry(root)}
            self.assertEqual(len(datasets), 11)
            matchups = datasets["sleeper.matchups"]
            self.assertEqual(matchups.scope, "week")
            self.assertEqual(matchups.week_start, 1)
            self.assertEqual(matchups.week_end_source, "nfl-regular-season-schedule")
            self.assertIn("{week}", matchups.endpoint)
            self.assertEqual(matchups.lifecycle["class"], "seasonal-finalizable")
        finally:
            temporary.cleanup()

    def test_week_ceiling_comes_from_canonical_schedule(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2026, 18)
            self.assertEqual(resolve_nfl_regular_season_week_ceiling(root, 2026), 18)
            self._write_schedule(root, 2027, 19)
            self.assertEqual(resolve_nfl_regular_season_week_ceiling(root, 2027), 19)
        finally:
            temporary.cleanup()

    def test_week_ceiling_fails_closed_without_complete_schedule_evidence(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            with self.assertRaises(FileNotFoundError):
                resolve_nfl_regular_season_week_ceiling(root, 2026)

            self._write_schedule(root, 2026, 18)
            schedule_path = root / "source-data" / "nfl" / "schedules" / "2026.json"
            payload = json.loads(schedule_path.read_text(encoding="utf-8"))
            payload["Games"] = [g for g in payload["Games"] if g.get("Week") != 9]
            schedule_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not contiguous"):
                resolve_nfl_regular_season_week_ceiling(root, 2026)
        finally:
            temporary.cleanup()

    def test_plans_all_current_raw_partitions_to_dynamic_schedule_ceiling(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2026, 18)
            registry = load_league_registry(root)
            league_payload = {
                "league_id": "1354177383984267264",
                "season": "2026",
                "previous_league_id": None,
            }
            lineage = [SleeperLeagueInstance("1354177383984267264", 2026, None, league_payload)]

            def fetch(url: str) -> object:
                if url.endswith("/users"):
                    return [{"user_id": "u1"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1, "owner_id": "u1"}]
                if url.endswith("/drafts"):
                    return [{"draft_id": "1354177383996866560"}]
                if url.endswith("/v1/draft/1354177383996866560"):
                    return {"draft_id": "1354177383996866560", "season": "2026"}
                return []

            plans = plan_raw_acquisition(root, lineage, registry, fetch)
            self.assertEqual(len(plans), 45)
            matchup_paths = [p.raw_path for p in plans if p.dataset_id == "sleeper.matchups"]
            transaction_paths = [p.raw_path for p in plans if p.dataset_id == "sleeper.transactions"]
            self.assertEqual(len(matchup_paths), 18)
            self.assertEqual(len(transaction_paths), 18)
            self.assertTrue(any(path.name == "week-18.json" for path in matchup_paths))
            self.assertFalse(any(path.name == "week-19.json" for path in matchup_paths))
        finally:
            temporary.cleanup()

    def test_future_nfl_expansion_requires_no_registry_change(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2027, 19)
            registry = load_league_registry(root)
            lineage = [
                SleeperLeagueInstance(
                    "2000000000000000000",
                    2027,
                    None,
                    {"league_id": "2000000000000000000", "season": "2027", "previous_league_id": None},
                )
            ]

            def fetch(url: str) -> object:
                if url.endswith("/users"):
                    return [{"user_id": "u1"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1}]
                return []

            plans = plan_raw_acquisition(root, lineage, registry, fetch)
            matchups = [p for p in plans if p.dataset_id == "sleeper.matchups"]
            self.assertEqual(len(matchups), 19)
            self.assertEqual(max(int(p.partition["Week"]) for p in matchups), 19)
        finally:
            temporary.cleanup()

    def test_persisted_raw_partitions_are_semantic_noops(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2026, 18)
            registry = load_league_registry(root)
            league_payload = {
                "league_id": "1354177383984267264",
                "season": "2026",
                "previous_league_id": None,
            }
            lineage = [SleeperLeagueInstance("1354177383984267264", 2026, None, league_payload)]

            def fetch(url: str) -> object:
                if url.endswith("/users"):
                    return [{"user_id": "u1"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1}]
                return []

            plans = plan_raw_acquisition(root, lineage, registry, fetch)
            first = persist_raw_plans(plans)
            second_plans = plan_raw_acquisition(root, lineage, registry, fetch)
            second = persist_raw_plans(second_plans)
            self.assertGreater(first["RawFilesChanged"], 0)
            self.assertGreater(first["MetadataFilesChanged"], 0)
            self.assertEqual(second["RawFilesChanged"], 0)
            self.assertEqual(second["MetadataFilesChanged"], 0)
        finally:
            temporary.cleanup()

    def test_historical_existing_partition_is_frozen_without_fetch(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2025, 18)
            self._write_schedule(root, 2026, 18)
            registry = load_league_registry(root)
            current = SleeperLeagueInstance(
                "1354177383984267264", 2026, "1257421353431080960",
                {"league_id": "1354177383984267264", "season": "2026", "previous_league_id": "1257421353431080960"},
            )
            historical = SleeperLeagueInstance(
                "1257421353431080960", 2025, None,
                {"league_id": "1257421353431080960", "season": "2025", "previous_league_id": None},
            )

            def seed_fetch(url: str) -> object:
                if url.endswith("/users"):
                    return [{"user_id": "old"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1}]
                return []
            persist_raw_plans(plan_raw_acquisition(root, [historical], registry, seed_fetch))

            calls: list[str] = []
            def current_fetch(url: str) -> object:
                calls.append(url)
                if "1257421353431080960" in url:
                    raise AssertionError("Historical persisted partition must not refetch")
                if url.endswith("/users"):
                    return [{"user_id": "current"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1}]
                return []

            plan_raw_acquisition(root, [current, historical], registry, current_fetch)
            self.assertTrue(calls)
            self.assertFalse(any("1257421353431080960" in url for url in calls))
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
