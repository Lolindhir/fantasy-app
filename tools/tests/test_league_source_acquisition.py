from __future__ import annotations

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


class LeagueSourceAcquisitionTests(unittest.TestCase):
    def _root_with_registry(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        target = root / "source-data"
        target.mkdir(parents=True)
        source = Path(__file__).resolve().parents[2] / "source-data/league-registry.json"
        target.joinpath("league-registry.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return temporary, root

    def test_registry_includes_matchups_as_week_partitioned_required_scope(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            datasets = {item.id: item for item in load_league_registry(root)}
            self.assertEqual(len(datasets), 11)
            matchups = datasets["sleeper.matchups"]
            self.assertEqual(matchups.scope, "week")
            self.assertEqual((matchups.week_start, matchups.week_end), (1, 20))
            self.assertIn("{week}", matchups.endpoint)
            self.assertEqual(matchups.lifecycle["class"], "seasonal-finalizable")
        finally:
            temporary.cleanup()

    def test_plans_all_current_league_raw_partitions_including_matchups_and_drafts(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            registry = load_league_registry(root)
            league_payload = {
                "league_id": "1354177383984267264",
                "season": "2026",
                "previous_league_id": None,
            }
            lineage = [
                SleeperLeagueInstance("1354177383984267264", 2026, None, league_payload)
            ]

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
            self.assertEqual(len(plans), 49)
            matchup_paths = [plan.raw_path for plan in plans if plan.dataset_id == "sleeper.matchups"]
            self.assertEqual(len(matchup_paths), 20)
            self.assertTrue(any(path.name == "week-1.json" for path in matchup_paths))
            self.assertTrue(any(path.name == "week-20.json" for path in matchup_paths))
            draft_ids = {plan.partition.get("DraftID") for plan in plans if plan.dataset_id.startswith("sleeper.draft-")}
            self.assertEqual(draft_ids, {"1354177383996866560"})
        finally:
            temporary.cleanup()

    def test_persisted_raw_partitions_are_semantic_noops(self) -> None:
        temporary, root = self._root_with_registry()
        try:
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
            historical_plans = plan_raw_acquisition(root, [historical], registry, seed_fetch)
            persist_raw_plans(historical_plans)

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
