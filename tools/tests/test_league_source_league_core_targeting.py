from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.acquire import plan_raw_acquisition  # noqa: E402
from league_source_data_lib.core import (  # noqa: E402
    SleeperLeagueInstance,
    canonical_league_season_id,
)
from league_source_data_lib.league_core_materialize import (  # noqa: E402
    LEAGUE_CORE_DATASET_IDS,
    LEAGUE_CORE_SCOPE_DEPENDENCIES,
    plan_league_core_materialization,
    resolve_current_league_core_season,
)
from league_source_data_lib.materialize import (  # noqa: E402
    PlayerMappingResolver,
    _canonicalize_bracket,
    persist_canonical_outputs,
)
from league_source_data_lib.registry import load_league_registry  # noqa: E402


class LeagueSourceCoreTargetingTests(unittest.TestCase):
    def _root_with_registry(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = Path(__file__).resolve().parents[2] / "source-data" / "league-registry.json"
        target = root / "source-data" / "league-registry.json"
        target.parent.mkdir(parents=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        schedule_source = Path(__file__).resolve().parents[2] / "source-data" / "nfl" / "schedules" / "2026.json"
        schedule_target = root / "source-data" / "nfl" / "schedules" / "2026.json"
        schedule_target.parent.mkdir(parents=True, exist_ok=True)
        schedule_target.write_text(schedule_source.read_text(encoding="utf-8"), encoding="utf-8")
        return temporary, root

    def _write_fixture(
        self,
        root: Path,
        *,
        canonical_league_id: str = "test-league",
        provider_league_id: str = "2000000000000000000",
        season: int = 2026,
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
        provider_mapping = {
            "Provider": "Sleeper",
            "ProviderLeagueID": provider_league_id,
            "PreviousProviderLeagueID": None,
        }
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
                            "ProviderMappings": [provider_mapping],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        season_root = league_root / "seasons" / str(season)
        season_root.mkdir(parents=True, exist_ok=True)
        (season_root / "league.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "CanonicalLeagueID": canonical_league_id,
                    "CanonicalLeagueSeasonID": season_id,
                    "Season": season,
                    "ProviderMappings": [provider_mapping],
                    "WeekStructure": {
                        "Season": season,
                        "FinalLeagueWeek": 17,
                        "HighestAssignedMatchupWeek": 2,
                    },
                }
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
        )
        raw_root.mkdir(parents=True, exist_ok=True)
        (raw_root / "league.json").write_text(
            json.dumps(
                {
                    "league_id": provider_league_id,
                    "season": str(season),
                    "name": "Fixture League",
                    "status": "in_season",
                    "season_type": "regular",
                    "avatar": None,
                    "settings": {"trade_deadline": 99, "leg": 2, "last_scored_leg": 1},
                    "scoring_settings": {"pass_td": 4},
                    "roster_positions": ["QB", "BN"],
                }
            ),
            encoding="utf-8",
        )
        (raw_root / "members.json").write_text(
            json.dumps(
                [
                    {
                        "user_id": "u1",
                        "display_name": "Owner",
                        "avatar": None,
                        "is_owner": True,
                        "metadata": {"team_name": "Fixture Team"},
                    }
                ]
            ),
            encoding="utf-8",
        )
        (raw_root / "rosters.json").write_text(
            json.dumps(
                [
                    {
                        "roster_id": 1,
                        "owner_id": "u1",
                        "settings": {"wins": 1},
                        "metadata": {},
                        "players": ["p1"],
                        "reserve": [],
                        "taxi": [],
                        "starters": ["p1"],
                    }
                ]
            ),
            encoding="utf-8",
        )
        (raw_root / "winners-bracket.json").write_text("[]", encoding="utf-8")
        (raw_root / "losers-bracket.json").write_text("[]", encoding="utf-8")
        matchup_root = raw_root / "matchups"
        matchup_root.mkdir(parents=True, exist_ok=True)
        (matchup_root / "week-2.json").write_text(
            json.dumps(
                [
                    {
                        "roster_id": 1,
                        "matchup_id": 1,
                        "points": 7.0,
                        "custom_points": None,
                        "players": ["p1"],
                        "starters": ["p1"],
                        "players_points": {"p1": 7.0},
                        "starters_points": [7.0],
                    }
                ]
            ),
            encoding="utf-8",
        )

    def test_targeted_acquisition_fetches_current_league_core_and_active_matchup(self) -> None:
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
                if url.endswith("/users"):
                    return [{"user_id": "u1"}]
                if url.endswith("/rosters"):
                    return [{"roster_id": 1, "owner_id": "u1"}]
                if url.endswith("/winners_bracket") or url.endswith("/losers_bracket"):
                    return []
                raise AssertionError(f"Unexpected URL: {url}")

            plans = plan_raw_acquisition(
                root,
                [instance],
                registry,
                fetch,
                dataset_ids=set(LEAGUE_CORE_DATASET_IDS),
                seasons={2026},
                weeks={2},
            )

            self.assertEqual(len(plans), 6)
            self.assertEqual(
                {plan.dataset_id for plan in plans},
                set(LEAGUE_CORE_DATASET_IDS),
            )
            self.assertEqual({plan.season for plan in plans}, {2026})
            self.assertEqual(len(calls), 5)
            self.assertEqual(sum("/matchups/2" in url for url in calls), 1)
            self.assertFalse(any("/transactions/" in url for url in calls))
            self.assertFalse(any("/draft" in url for url in calls))
        finally:
            temporary.cleanup()

    def test_league_core_scope_writes_core_plus_active_matchup_and_is_noop_on_repeat(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)

            outputs = plan_league_core_materialization(
                root,
                "test-league",
                registry,
                resolver,
                seasons={2026},
            )
            relative_paths = {
                output.path.relative_to(root).as_posix()
                for output in outputs
            }
            self.assertEqual(
                relative_paths,
                {
                    "source-data/leagues/test-league/seasons/2026/league.json",
                    "source-data/leagues/test-league/seasons/2026/members.json",
                    "source-data/leagues/test-league/seasons/2026/rosters.json",
                    "source-data/leagues/test-league/seasons/2026/winners-bracket.json",
                    "source-data/leagues/test-league/seasons/2026/losers-bracket.json",
                    "source-data/leagues/test-league/seasons/2026/matchups/week-2.json",
                },
            )
            self.assertEqual(
                LEAGUE_CORE_SCOPE_DEPENDENCIES,
                (
                    "raw-sleeper-league",
                    "raw-sleeper-league-members",
                    "raw-sleeper-league-rosters",
                    "raw-sleeper-winners-bracket",
                    "raw-sleeper-losers-bracket",
                    "raw-sleeper-matchups",
                    "nfl-player-provider-mappings",
                    "canonical-week-structure",
                ),
            )
            league_output = next(
                output for output in outputs if output.path.name == "league.json"
            )
            self.assertEqual(
                league_output.value["WeekStructure"],
                {
                    "Season": 2026,
                    "FinalLeagueWeek": 17,
                    "HighestAssignedMatchupWeek": 2,
                },
            )

            first = persist_canonical_outputs(outputs)
            second = persist_canonical_outputs(
                plan_league_core_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                )
            )
            self.assertEqual(first["CanonicalFiles"], 6)
            self.assertEqual(second["CanonicalFilesChanged"], 0)
            season_root = root / "source-data/leagues/test-league/seasons/2026"
            self.assertTrue((season_root / "matchups" / "week-2.json").exists())
            self.assertFalse((season_root / "transactions").exists())
            self.assertFalse((season_root / "drafts.json").exists())
        finally:
            temporary.cleanup()

    def test_bracket_routing_is_canonicalized_provider_neutrally(self) -> None:
        raw = [
            {"r": 1, "m": 1, "t1": 1, "t2": 2, "w": None, "l": None},
            {
                "r": 2,
                "m": 2,
                "p": 1,
                "t1": None,
                "t2": None,
                "t1_from": {"w": 1},
                "t2_from": {"l": 1},
                "w": None,
                "l": None,
            },
        ]
        actual = _canonicalize_bracket(
            raw,
            {"1": "clr-one", "2": "clr-two"},
            "winners",
        )
        self.assertEqual(
            actual[1]["Team1Source"],
            {"Outcome": "Winner", "Match": 1},
        )
        self.assertEqual(
            actual[1]["Team2Source"],
            {"Outcome": "Loser", "Match": 1},
        )
        self.assertNotIn("w", actual[1]["Team1Source"])
        self.assertNotIn("l", actual[1]["Team2Source"])

    def test_bracket_routing_fails_closed_on_unknown_or_forward_reference(self) -> None:
        with self.assertRaisesRegex(ValueError, "references unknown match 99"):
            _canonicalize_bracket(
                [
                    {"r": 1, "m": 1, "t1": 1, "t2": 2},
                    {"r": 2, "m": 2, "t1_from": {"w": 99}},
                ],
                {"1": "clr-one", "2": "clr-two"},
                "winners",
            )

        with self.assertRaisesRegex(ValueError, "earlier-round match"):
            _canonicalize_bracket(
                [
                    {"r": 1, "m": 1, "t1": 1, "t2": 2},
                    {"r": 1, "m": 2, "t1_from": {"w": 1}},
                ],
                {"1": "clr-one", "2": "clr-two"},
                "winners",
            )

    def test_bracket_routing_fails_closed_on_ambiguous_source_or_match_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one of w/l"):
            _canonicalize_bracket(
                [
                    {"r": 1, "m": 1, "t1": 1, "t2": 2},
                    {"r": 2, "m": 2, "t1_from": {"w": 1, "l": 1}},
                ],
                {"1": "clr-one", "2": "clr-two"},
                "winners",
            )

        with self.assertRaisesRegex(ValueError, "globally unique"):
            _canonicalize_bracket(
                [
                    {"r": 1, "m": 1, "t1": 1, "t2": 2},
                    {"r": 2, "m": 1, "t1": 1, "t2": 2},
                ],
                {"1": "clr-one", "2": "clr-two"},
                "winners",
            )

    def test_current_scope_fails_closed_on_manifest_provider_mismatch(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
            with self.assertRaisesRegex(ValueError, "bootstrap current ProviderLeagueID"):
                resolve_current_league_core_season(
                    root,
                    "test-league",
                    "9999999999999999999",
                )
        finally:
            temporary.cleanup()

    def test_league_core_scope_requires_existing_week_structure(self) -> None:
        temporary, root = self._root_with_registry()
        try:
            self._write_fixture(root)
            league_path = (
                root
                / "source-data"
                / "leagues"
                / "test-league"
                / "seasons"
                / "2026"
                / "league.json"
            )
            baseline = json.loads(league_path.read_text(encoding="utf-8"))
            baseline.pop("WeekStructure")
            league_path.write_text(json.dumps(baseline), encoding="utf-8")
            registry = load_league_registry(root)
            resolver = PlayerMappingResolver.load(root)
            with self.assertRaisesRegex(ValueError, "accepted canonical WeekStructure"):
                plan_league_core_materialization(
                    root,
                    "test-league",
                    registry,
                    resolver,
                    seasons={2026},
                )
        finally:
            temporary.cleanup()


class CurrentRepositoryLeagueCoreScopeIntegrationTests(unittest.TestCase):
    def test_current_nfl_reise_core_matches_existing_canonical_files(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        manifest_path = repo_root / "source-data" / "leagues" / "nfl-reise" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        provider_league_id = str(manifest["CurrentProviderLeagueID"])
        season = resolve_current_league_core_season(
            repo_root,
            "nfl-reise",
            provider_league_id,
        )
        registry = load_league_registry(repo_root)
        resolver = PlayerMappingResolver.load(repo_root)
        outputs = plan_league_core_materialization(
            repo_root,
            "nfl-reise",
            registry,
            resolver,
            seasons={season},
        )
        self.assertEqual(len(outputs), 6)
        for output in outputs:
            existing = json.loads(output.path.read_text(encoding="utf-8"))
            self.assertEqual(
                output.value,
                existing,
                f"League Core parity drift for {output.path.relative_to(repo_root)}",
            )

        winners_output = next(
            output for output in outputs if output.path.name == "winners-bracket.json"
        )
        by_match = {item["Match"]: item for item in winners_output.value}
        self.assertEqual(
            by_match[3]["Team1Source"],
            {"Outcome": "Winner", "Match": 1},
        )
        self.assertEqual(
            by_match[3]["Team2Source"],
            {"Outcome": "Winner", "Match": 2},
        )
        self.assertEqual(
            by_match[4]["Team1Source"],
            {"Outcome": "Loser", "Match": 1},
        )
        self.assertEqual(
            by_match[4]["Team2Source"],
            {"Outcome": "Loser", "Match": 2},
        )


if __name__ == "__main__":
    unittest.main()
