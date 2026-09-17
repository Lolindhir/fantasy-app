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
from league_source_data_lib.core import SleeperLeagueInstance, canonical_league_season_id  # noqa: E402
from league_source_data_lib.materialize import PlayerMappingResolver, persist_canonical_outputs  # noqa: E402
from league_source_data_lib.registry import load_league_registry  # noqa: E402
from league_source_data_lib.transaction_materialize import (  # noqa: E402
    TRANSACTION_SCOPE_DEPENDENCIES,
    plan_transaction_materialization,
)


class LeagueSourceTransactionTargetingTests(unittest.TestCase):
    def _root_with_registry(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = Path(__file__).resolve().parents[2] / "source-data" / "league-registry.json"
        target = root / "source-data" / "league-registry.json"
        target.parent.mkdir(parents=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return temporary, root

    @staticmethod
    def _write_schedule(root: Path, season: int, last_week: int = 18) -> None:
        path = root / "source-data" / "nfl" / "schedules" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "Season": season,
                    "Games": [
                        {
                            "GameID": f"{season}_{week:02d}_A_B",
                            "GameType": "REG",
                            "Week": week,
                        }
                        for week in range(1, last_week + 1)
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _write_transaction_scope_fixture(
        self,
        root: Path,
        *,
        canonical_league_id: str = "test-league",
        provider_league_id: str = "2000000000000000000",
        season: int = 2026,
        week: int = 7,
    ) -> None:
        self._write_schedule(root, season)
        season_id = canonical_league_season_id(canonical_league_id, season)

        mappings = root / "source-data" / "nfl" / "identities" / "provider-mappings.json"
        mappings.parent.mkdir(parents=True, exist_ok=True)
        mappings.write_text(
            json.dumps(
                {
                    "Mappings": [
                        {
                            "Provider": "Sleeper",
                            "ExternalID": "p1",
                            "CanonicalPlayerID": "cp-one",
                            "FirstObservedSeason": season,
                            "LastObservedSeason": season,
                            "Sources": ["fixture"],
                        }
                    ],
                    "Conflicts": [],
                }
            ),
            encoding="utf-8",
        )

        league_root = root / "source-data" / "leagues" / canonical_league_id
        league_root.mkdir(parents=True, exist_ok=True)
        (league_root / "manifest.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "CanonicalLeagueID": canonical_league_id,
                    "Provider": "Sleeper",
                    "CurrentCanonicalLeagueSeasonID": season_id,
                    "CurrentProviderLeagueID": provider_league_id,
                    "Seasons": [
                        {
                            "CanonicalLeagueSeasonID": season_id,
                            "Season": season,
                            "PreviousCanonicalLeagueSeasonID": None,
                            "ProviderMappings": [
                                {
                                    "Provider": "Sleeper",
                                    "ProviderLeagueID": provider_league_id,
                                    "PreviousProviderLeagueID": None,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        season_root = league_root / "seasons" / str(season)
        season_root.mkdir(parents=True, exist_ok=True)
        (season_root / "members.json").write_text(
            json.dumps(
                [
                    {
                        "CanonicalLeagueMemberID": "clm-one",
                        "ProviderMappings": [
                            {"Provider": "Sleeper", "ProviderUserID": "u1"}
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        (season_root / "rosters.json").write_text(
            json.dumps(
                [
                    {
                        "CanonicalLeagueRosterID": "clr-one",
                        "ProviderMappings": [
                            {"Provider": "Sleeper", "ProviderRosterID": "1"}
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )

        raw_root = (
            root
            / "source-data"
            / "providers"
            / "sleeper"
            / "leagues"
            / provider_league_id
            / "transactions"
        )
        raw_root.mkdir(parents=True, exist_ok=True)
        (raw_root / f"week-{week}.json").write_text(
            json.dumps(
                [
                    {
                        "transaction_id": "tx1",
                        "leg": week,
                        "type": "waiver",
                        "status": "complete",
                        "creator": "u1",
                        "created": 1789000000000,
                        "roster_ids": [1],
                        "adds": {"p1": 1},
                        "drops": {},
                        "draft_picks": [],
                        "metadata": {"notes": "fixture"},
                    }
                ]
            ),
            encoding="utf-8",
        )

    def test_targeted_acquisition_limits_dataset_season_and_week(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2026)
            registry = load_league_registry(root)
            instance = SleeperLeagueInstance(
                "2000000000000000000",
                2026,
                None,
                {
                    "league_id": "2000000000000000000",
                    "season": "2026",
                    "previous_league_id": None,
                },
            )
            calls: list[str] = []

            def fetch(url: str) -> object:
                calls.append(url)
                return []

            plans = plan_raw_acquisition(
                root,
                [instance],
                registry,
                fetch,
                dataset_ids={"sleeper.transactions"},
                seasons={2026},
                weeks={7},
            )

            self.assertEqual(len(plans), 1)
            self.assertEqual(plans[0].dataset_id, "sleeper.transactions")
            self.assertEqual(plans[0].season, 2026)
            self.assertEqual(plans[0].partition, {"Week": 7})
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0].endswith("/transactions/7"))
        finally:
            temporary.cleanup()

    def test_targeted_acquisition_rejects_unknown_dataset_and_week(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_schedule(root, 2026)
            registry = load_league_registry(root)
            instance = SleeperLeagueInstance(
                "2000000000000000000",
                2026,
                None,
                {
                    "league_id": "2000000000000000000",
                    "season": "2026",
                    "previous_league_id": None,
                },
            )
            with self.assertRaisesRegex(ValueError, "Unknown League dataset"):
                plan_raw_acquisition(
                    root,
                    [instance],
                    registry,
                    lambda _: [],
                    dataset_ids={"missing.dataset"},
                )
            with self.assertRaisesRegex(ValueError, "outside sleeper.transactions range"):
                plan_raw_acquisition(
                    root,
                    [instance],
                    registry,
                    lambda _: [],
                    dataset_ids={"sleeper.transactions"},
                    weeks={19},
                )
        finally:
            temporary.cleanup()

    def test_transaction_scope_writes_only_requested_partition_and_is_noop_on_repeat(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_transaction_scope_fixture(root)
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)

            outputs = plan_transaction_materialization(
                root,
                "test-league",
                registry,
                resolver,
                seasons={2026},
                weeks={7},
            )
            self.assertEqual(len(outputs), 1)
            self.assertEqual(
                outputs[0].path.relative_to(root).as_posix(),
                "source-data/leagues/test-league/seasons/2026/transactions/week-7.json",
            )
            self.assertEqual(
                TRANSACTION_SCOPE_DEPENDENCIES,
                (
                    "canonical-members",
                    "canonical-rosters",
                    "nfl-player-provider-mappings",
                    "raw-sleeper-transactions",
                ),
            )
            self.assertEqual(outputs[0].value[0]["Adds"][0]["Player"]["CanonicalPlayerID"], "cp-one")

            first = persist_canonical_outputs(outputs)
            second = persist_canonical_outputs(
                plan_transaction_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                    weeks={7},
                )
            )
            self.assertEqual(first["CanonicalFiles"], 1)
            self.assertEqual(first["CanonicalFilesChanged"], 1)
            self.assertEqual(second["CanonicalFilesChanged"], 0)

            season_root = root / "source-data" / "leagues" / "test-league" / "seasons" / "2026"
            self.assertFalse((season_root / "league.json").exists())
            self.assertFalse((season_root / "drafts.json").exists())
            self.assertFalse((season_root / "matchups").exists())
        finally:
            temporary.cleanup()

    def test_transaction_scope_fails_closed_when_canonical_roster_dependency_is_missing(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_transaction_scope_fixture(root)
            roster_path = (
                root
                / "source-data"
                / "leagues"
                / "test-league"
                / "seasons"
                / "2026"
                / "rosters.json"
            )
            roster_path.unlink()
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)
            with self.assertRaises(FileNotFoundError):
                plan_transaction_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                    weeks={7},
                )
        finally:
            temporary.cleanup()


class CurrentRepositoryTransactionScopeIntegrationTests(unittest.TestCase):
    def test_current_nfl_reise_week_one_matches_existing_canonical_partition(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        registry = load_league_registry(repo_root)
        resolver = PlayerMappingResolver.load(repo_root)
        outputs = plan_transaction_materialization(
            repo_root,
            "nfl-reise",
            registry,
            resolver,
            seasons={2026},
            weeks={1},
        )
        self.assertEqual(len(outputs), 1)
        existing = json.loads(outputs[0].path.read_text(encoding="utf-8"))
        self.assertEqual(outputs[0].value, existing)


if __name__ == "__main__":
    unittest.main()
