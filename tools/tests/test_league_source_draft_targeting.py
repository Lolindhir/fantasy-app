from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.acquire import plan_raw_acquisition  # noqa: E402
from league_source_data_lib.core import SleeperLeagueInstance, canonical_league_season_id  # noqa: E402
from league_source_data_lib.draft_materialize import (  # noqa: E402
    DRAFT_DATASET_IDS,
    DRAFT_SCOPE_DEPENDENCIES,
    plan_draft_materialization,
    resolve_current_draft_season,
)
from league_source_data_lib.materialize import PlayerMappingResolver, persist_canonical_outputs  # noqa: E402
from league_source_data_lib.registry import load_league_registry  # noqa: E402


class LeagueSourceDraftTargetingTests(unittest.TestCase):
    def _root_with_registry(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = Path(__file__).resolve().parents[2] / "source-data" / "league-registry.json"
        target = root / "source-data" / "league-registry.json"
        target.parent.mkdir(parents=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return temporary, root

    def _write_fixture(
        self,
        root: Path,
        *,
        canonical_league_id: str = "test-league",
        provider_league_id: str = "2000000000000000000",
        season: int = 2026,
        draft_id: str = "3000000000000000000",
    ) -> None:
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

        season_id = canonical_league_season_id(canonical_league_id, season)
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

        draft_root = (
            root
            / "source-data"
            / "providers"
            / "sleeper"
            / "leagues"
            / provider_league_id
            / "drafts"
        )
        draft_root.mkdir(parents=True, exist_ok=True)
        (draft_root / "index.json").write_text(
            json.dumps([{"draft_id": draft_id, "season": str(season)}]),
            encoding="utf-8",
        )
        draft_dir = draft_root / draft_id
        draft_dir.mkdir(parents=True, exist_ok=True)
        (draft_dir / "draft.json").write_text(
            json.dumps(
                {
                    "draft_id": draft_id,
                    "season": str(season),
                    "status": "complete",
                    "type": "linear",
                    "start_time": 1788000000000,
                    "settings": {"rounds": 1, "teams": 1},
                    "metadata": {"name": "Fixture Draft"},
                    "draft_order": {"u1": 1},
                    "slot_to_roster_id": {"1": 1},
                }
            ),
            encoding="utf-8",
        )
        (draft_dir / "picks.json").write_text(
            json.dumps(
                [
                    {
                        "pick_no": 1,
                        "player_id": "p1",
                        "roster_id": 1,
                        "picked_by": "u1",
                        "metadata": {"first_name": "Test", "last_name": "Player"},
                    }
                ]
            ),
            encoding="utf-8",
        )
        (draft_dir / "traded-picks.json").write_text(
            json.dumps(
                [
                    {
                        "season": str(season),
                        "round": 1,
                        "roster_id": 1,
                        "previous_owner_id": 1,
                        "owner_id": 1,
                    }
                ]
            ),
            encoding="utf-8",
        )

    def test_targeted_acquisition_fetches_only_current_draft_datasets(self) -> None:
        temporary, root = self._root_with_registry()
        try:
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
                if url.endswith("/drafts"):
                    return [{"draft_id": "3000000000000000000", "season": "2026"}]
                if url.endswith("/traded_picks"):
                    return []
                if url.endswith("/picks"):
                    return []
                if url.endswith("/v1/draft/3000000000000000000"):
                    return {
                        "draft_id": "3000000000000000000",
                        "season": "2026",
                    }
                raise AssertionError(f"Unexpected URL: {url}")

            plans = plan_raw_acquisition(
                root,
                [instance],
                registry,
                fetch,
                dataset_ids=set(DRAFT_DATASET_IDS),
                seasons={2026},
            )

            self.assertEqual(len(plans), 4)
            self.assertEqual({plan.dataset_id for plan in plans}, set(DRAFT_DATASET_IDS))
            self.assertEqual({plan.season for plan in plans}, {2026})
            self.assertEqual(len(calls), 4)
            self.assertTrue(any(url.endswith("/league/2000000000000000000/drafts") for url in calls))
            self.assertTrue(any(url.endswith("/v1/draft/3000000000000000000") for url in calls))
            self.assertTrue(any(url.endswith("/v1/draft/3000000000000000000/picks") for url in calls))
            self.assertTrue(any(url.endswith("/v1/draft/3000000000000000000/traded_picks") for url in calls))
        finally:
            temporary.cleanup()

    def test_draft_scope_writes_only_drafts_json_and_is_noop_on_repeat(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)
            outputs = plan_draft_materialization(
                root,
                "test-league",
                registry,
                resolver,
                seasons={2026},
            )
            self.assertEqual(len(outputs), 1)
            self.assertEqual(
                outputs[0].path.relative_to(root).as_posix(),
                "source-data/leagues/test-league/seasons/2026/drafts.json",
            )
            self.assertEqual(
                DRAFT_SCOPE_DEPENDENCIES,
                (
                    "canonical-members",
                    "canonical-rosters",
                    "nfl-player-provider-mappings",
                    "raw-sleeper-league-drafts",
                    "raw-sleeper-draft-detail",
                    "raw-sleeper-draft-picks",
                    "raw-sleeper-draft-traded-picks",
                ),
            )
            draft = outputs[0].value[0]
            self.assertEqual(draft["Picks"][0]["Player"]["CanonicalPlayerID"], "cp-one")
            self.assertEqual(draft["TradedPicks"][0]["OwnerCanonicalLeagueRosterID"], "clr-one")

            first = persist_canonical_outputs(outputs)
            second = persist_canonical_outputs(
                plan_draft_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                )
            )
            self.assertEqual(first["CanonicalFiles"], 1)
            self.assertEqual(first["CanonicalFilesChanged"], 1)
            self.assertEqual(second["CanonicalFilesChanged"], 0)
            self.assertFalse((outputs[0].path.parent / "league.json").exists())
            self.assertFalse((outputs[0].path.parent / "transactions").exists())
            self.assertFalse((outputs[0].path.parent / "matchups").exists())
        finally:
            temporary.cleanup()

    def test_current_draft_scope_fails_closed_on_manifest_provider_mismatch(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
            with self.assertRaisesRegex(ValueError, "bootstrap current ProviderLeagueID"):
                resolve_current_draft_season(
                    root,
                    "test-league",
                    "9999999999999999999",
                )
        finally:
            temporary.cleanup()

    def test_draft_scope_fails_closed_when_canonical_roster_dependency_is_missing(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
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
                plan_draft_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                )
        finally:
            temporary.cleanup()


class CurrentRepositoryDraftScopeIntegrationTests(unittest.TestCase):
    def test_current_nfl_reise_drafts_match_existing_canonical_file(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        registry = load_league_registry(repo_root)
        resolver = PlayerMappingResolver.load(repo_root)
        outputs = plan_draft_materialization(
            repo_root,
            "nfl-reise",
            registry,
            resolver,
            seasons={2026},
        )
        self.assertEqual(len(outputs), 1)
        existing = json.loads(outputs[0].path.read_text(encoding="utf-8"))
        self.assertEqual(outputs[0].value, existing)


if __name__ == "__main__":
    unittest.main()
