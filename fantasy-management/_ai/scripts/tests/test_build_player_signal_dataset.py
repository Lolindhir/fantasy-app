from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_player_signal_dataset.py"
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("build_player_signal_dataset", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PlayerSignalDatasetTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def write_text(self, root: Path, relative: str, value: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def source_definition(
        self,
        *,
        source_id: str,
        provider: str,
        dataset_id: str,
        pointer: str,
        section: str,
        key: str,
        signals: list[dict[str, str]],
        primary: bool = False,
    ) -> dict[str, object]:
        return {
            "source_id": source_id,
            "active": True,
            "source_kind": "adp" if section == "redraft_adp" else "projection",
            "provider": provider,
            "dataset_id": dataset_id,
            "access": {
                "type": "repo_latest_pointer",
                "location": pointer,
                "ranking_path_field": "ranking_file",
                "timestamp_fields": ["ranking_fetched_at"],
            },
            "applicability": {"entity_types": ["player"], "positions": ["K"]},
            "absence_policy": {
                "inapplicable": "not_applicable",
                "missing": "not_listed",
                "ambiguous": "ambiguous_join",
            },
            "join": {
                "strategies": [
                    {
                        "type": "name_position",
                        "method": "normalized_name_position",
                        "name_field": "name",
                        "position_field": "position",
                        "team_field": "team",
                    }
                ]
            },
            "output": {"section": section, "key": key, "signals": signals},
            "roles": {"primary_for_positions": ["K"]} if primary else {},
            "quality": {
                "minimum_rows": 1,
                "missing_severity": "none",
                "ambiguous_severity": "warning",
                "row_count_severity": "error",
            },
            "freshness": {"max_age_hours": 2},
            "format_context": {"position_scope": "K"},
        }

    def prepare_root(self, root: Path) -> Path:
        self.write_json(
            root,
            "public/data/League.json",
            {
                "Teams": [
                    {
                        "TeamID": 1,
                        "Team": "Mighty Giants",
                        "TeamAbbr": "MiG",
                        "Roster": ["1"],
                        "Reserve": [],
                        "Taxi": [],
                    },
                    {
                        "TeamID": 2,
                        "Team": "Opponent",
                        "TeamAbbr": "OPP",
                        "Roster": [],
                        "Reserve": [],
                        "Taxi": [],
                    },
                ]
            },
        )
        self.write_json(
            root,
            "fantasy-management/league-context/owner-registry.json",
            {
                "version": 3,
                "canonical_league_id": "test-league",
                "owners": [
                    {
                        "name": "Owner One",
                        "team_id": 1,
                        "canonical_league_member_id": "member-1",
                    },
                    {
                        "name": "Owner Two",
                        "team_id": 2,
                        "canonical_league_member_id": "member-2",
                    },
                ],
            },
        )
        self.write_json(
            root,
            "source-data/leagues/test-league/manifest.json",
            {
                "CanonicalLeagueID": "test-league",
                "CurrentCanonicalLeagueSeasonID": "test-league-2026",
                "Seasons": [
                    {
                        "CanonicalLeagueSeasonID": "test-league-2026",
                        "Season": 2026,
                    }
                ],
            },
        )
        self.write_json(
            root,
            "source-data/leagues/test-league/seasons/2026/league.json",
            {
                "CanonicalLeagueID": "test-league",
                "Season": 2026,
                "Settings": {"num_teams": 2},
            },
        )
        self.write_json(
            root,
            "source-data/leagues/test-league/seasons/2026/members.json",
            [
                {
                    "CanonicalLeagueMemberID": "member-1",
                    "DisplayName": "owner-one",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderUserID": "user-1"}
                    ],
                },
                {
                    "CanonicalLeagueMemberID": "member-2",
                    "DisplayName": "owner-two",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderUserID": "user-2"}
                    ],
                },
            ],
        )
        self.write_json(
            root,
            "source-data/leagues/test-league/seasons/2026/rosters.json",
            [
                {
                    "CanonicalLeagueMemberID": "member-1",
                    "CanonicalLeagueRosterID": "roster-1",
                    "ProviderOwnerUserID": "user-1",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderRosterID": "91"}
                    ],
                    "Players": [self.canonical_player("1")],
                    "Reserve": [],
                    "Taxi": [],
                    "Starters": [self.canonical_player("1")],
                },
                {
                    "CanonicalLeagueMemberID": "member-2",
                    "CanonicalLeagueRosterID": "roster-2",
                    "ProviderOwnerUserID": "user-2",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderRosterID": "92"}
                    ],
                    "Players": [],
                    "Reserve": [],
                    "Taxi": [],
                    "Starters": [],
                },
            ],
        )
        self.write_json(
            root,
            "source-data/nfl/identities/players.json",
            {
                "Players": [
                    {
                        "CanonicalPlayerID": "canonical-1",
                        "Name": "Kicker One",
                        "IDs": {"Sleeper": "1", "ESPN": "101"},
                    },
                    {
                        "CanonicalPlayerID": "canonical-2",
                        "Name": "Kicker Two",
                        "IDs": {"Sleeper": "2", "ESPN": "202"},
                    },
                    {
                        "CanonicalPlayerID": "canonical-3",
                        "Name": "Inactive Free Agent",
                        "IDs": {"Sleeper": "3", "ESPN": "303"},
                    },
                ]
            },
        )
        self.write_json(
            root,
            "source-data/nfl/platform/sleeper/players.json",
            {
                "Records": [
                    {
                        "CanonicalPlayerID": "canonical-1",
                        "SleeperPlayerID": "1",
                        "Status": "Active",
                        "Team": "AAA",
                        "Position": "K",
                        "FantasyPositions": ["K"],
                        "DepthChartPosition": "K",
                        "DepthChartOrder": 1,
                    },
                    {
                        "CanonicalPlayerID": "canonical-2",
                        "SleeperPlayerID": "2",
                        "Status": "Active",
                        "Team": "BBB",
                        "Position": "K",
                        "FantasyPositions": ["K"],
                        "DepthChartPosition": None,
                        "DepthChartOrder": None,
                    },
                    {
                        "CanonicalPlayerID": "canonical-3",
                        "SleeperPlayerID": "3",
                        "Status": "Inactive",
                        "Team": None,
                        "Position": "K",
                        "FantasyPositions": ["K"],
                        "DepthChartPosition": None,
                        "DepthChartOrder": None,
                    },
                ]
            },
        )
        self.write_json(
            root,
            "public/data/Players.json",
            [
                {
                    "ID": "1",
                    "Name": "Kicker One",
                    "Position": "K",
                    "TeamAbbr": "AAA",
                    "Status": "Active",
                    "Age": 28,
                    "Year": 4,
                    "Salary": 5,
                    "SalaryProjected": 6,
                    "IsFreeAgent": False,
                    "ESPNID": "101",
                    "SleeperDepthChartPosition": "K",
                    "SleeperDepthChartOrder": 1,
                    "Injured": False,
                },
                {
                    "ID": "2",
                    "Name": "Kicker Two",
                    "Position": "K",
                    "TeamAbbr": "BBB",
                    "Status": "Active",
                    "Age": 24,
                    "Year": 1,
                    "IsFreeAgent": False,
                    "Injured": False,
                },
                {
                    "ID": "3",
                    "Name": "Inactive Free Agent",
                    "Position": "K",
                    "TeamAbbr": "",
                    "Status": "Inactive",
                    "Injured": False,
                },
            ],
        )
        self.write_json(
            root,
            "public/data/Timestamps.json",
            {"League": "2026-08-08T06:00:00Z", "Players": "2026-08-08T05:50:00Z"},
        )
        self.write_json(
            root,
            "fantasy-management/generated/operations/external-signal-relevance.json",
            {
                "generated_at": "2026-08-08T05:45:00Z",
                "source_states": [
                    {
                        "source_id": "sleeper-trending",
                        "provider": "sleeper",
                        "dataset_id": "nfl-roster-activity-24h-top100",
                        "source_timestamp": "2026-08-08T05:40:00Z",
                        "comparison": {"baseline": False, "comparable": True},
                    }
                ],
                "views": {
                    "sleeper-trending": {
                        "add": [
                            {
                                "rank": 1,
                                "player_id": "2",
                                "name": "Kicker Two",
                                "position": "K",
                                "nfl_team": "BBB",
                                "count": 55,
                                "ownership_status": "fantasy_free_agent",
                                "owner_teams": [],
                            }
                        ],
                        "drop": [],
                    }
                },
                "quality": {"status": "ok", "issues": []},
            },
        )

        base = "fantasy-management/sources/test"
        self.write_json(
            root,
            f"{base}/ffc/latest.json",
            {"ranking_file": f"{base}/ffc/ranking.csv", "ranking_fetched_at": "2026-08-08T05:30:00Z"},
        )
        self.write_text(
            root,
            f"{base}/ffc/ranking.csv",
            "name,Rank,position,team,adp,times_drafted,stdev\n"
            "Kicker One,1,K,AAA,70.0,100,4.0\n"
            "Kicker Two,2,K,BBB,90.0,20,8.0\n",
        )
        self.write_json(
            root,
            f"{base}/fftoday/latest.json",
            {"ranking_file": f"{base}/fftoday/ranking.csv", "ranking_fetched_at": "2026-08-08T05:35:00Z"},
        )
        self.write_text(
            root,
            f"{base}/fftoday/ranking.csv",
            "name,Rank,position,team,fgm,fga,projected_fantasy_points\n"
            "Kicker Two,1,K,BBB,30,34,150\n"
            "Kicker One,2,K,AAA,28,32,140\n",
        )
        self.write_json(
            root,
            f"{base}/cbs/latest.json",
            {"ranking_file": f"{base}/cbs/ranking.csv", "ranking_fetched_at": "2026-08-08T05:38:00Z"},
        )
        self.write_text(
            root,
            f"{base}/cbs/ranking.csv",
            "name,Rank,position,team,fgm,fga,projected_fantasy_points,projected_fantasy_points_per_game\n"
            "Kicker One,1,K,AAA,31,35,155,9.1\n"
            "Kicker Two,2,K,BBB,29,33,145,8.5\n",
        )

        rank_signal = {"target": "rank", "source_field": "Rank", "type": "number"}
        percentile_signal = {
            "target": "percentile",
            "source_field": "Rank",
            "type": "number",
            "transform": "percentile_from_rank",
        }
        catalog = {
            "schema_version": 1,
            "catalog_id": "test-catalog",
            "purpose": "test",
            "sources": [
                self.source_definition(
                    source_id="ffc-k",
                    provider="fantasy-football-calculator",
                    dataset_id="ffc-k",
                    pointer=f"{base}/ffc/latest.json",
                    section="redraft_adp",
                    key="kicker",
                    signals=[
                        rank_signal,
                        percentile_signal,
                        {"target": "adp", "source_field": "adp", "type": "number"},
                        {"target": "times_drafted", "source_field": "times_drafted", "type": "number"},
                        {"target": "stdev", "source_field": "stdev", "type": "number"},
                    ],
                    primary=True,
                ),
                self.source_definition(
                    source_id="fftoday-k",
                    provider="fftoday",
                    dataset_id="fftoday-k",
                    pointer=f"{base}/fftoday/latest.json",
                    section="projections",
                    key="fftoday",
                    signals=[
                        rank_signal,
                        percentile_signal,
                        {"target": "fgm", "source_field": "fgm", "type": "number"},
                        {"target": "fga", "source_field": "fga", "type": "number"},
                        {
                            "target": "projected_fantasy_points",
                            "source_field": "projected_fantasy_points",
                            "type": "number",
                        },
                    ],
                ),
                self.source_definition(
                    source_id="cbs-k",
                    provider="cbs-sports",
                    dataset_id="cbs-k",
                    pointer=f"{base}/cbs/latest.json",
                    section="projections",
                    key="cbs_sports",
                    signals=[
                        rank_signal,
                        percentile_signal,
                        {"target": "fgm", "source_field": "fgm", "type": "number"},
                        {"target": "fga", "source_field": "fga", "type": "number"},
                        {
                            "target": "projected_fantasy_points",
                            "source_field": "projected_fantasy_points",
                            "type": "number",
                        },
                        {
                            "target": "projected_fantasy_points_per_game",
                            "source_field": "projected_fantasy_points_per_game",
                            "type": "number",
                        },
                    ],
                ),
            ],
            "derived_views": {"redraft_adp": {}},
        }
        self.write_json(root, "fantasy-management/_ai/operations-source-catalog.json", catalog)

        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        self.write_json(
            root,
            "fantasy-management/automation/player-signal-materialization.json",
            {
                "schema_version": 1,
                "materialization_id": "test-player-signals",
                "managed_team": {"team_id": 1},
                "canonical_league": {"canonical_league_id": "test-league"},
                "sources": {
                    "league_display": "public/data/League.json",
                    "players": "public/data/Players.json",
                    "canonical_player_identities": "source-data/nfl/identities/players.json",
                    "canonical_sleeper_players": "source-data/nfl/platform/sleeper/players.json",
                    "timestamps": "public/data/Timestamps.json",
                    "external_signal_relevance": "fantasy-management/generated/operations/external-signal-relevance.json",
                },
                "source_catalog": "fantasy-management/_ai/operations-source-catalog.json",
                "population": {"positions": ["K"]},
                "output": {"player_signals": "fantasy-management/generated/operations/player-signals.json"},
            },
        )
        return config_path

    @staticmethod
    def canonical_player(player_id: str) -> dict[str, object]:
        return {
            "CanonicalPlayerID": f"canonical-{player_id}",
            "ProviderMappings": [
                {"Provider": "Sleeper", "ProviderPlayerID": player_id}
            ],
        }

    def test_builds_free_agent_kicker_signals_without_averaging_provider_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)
            result = MODULE.build(root, config_path)

            self.assertEqual(result["dataset_id"], "player-signals")
            self.assertEqual(result["population"]["player_count"], 2)
            players = {player["player_id"]: player for player in result["players"]}
            self.assertEqual(players["1"]["ownership"]["status"], "mighty_giants")
            self.assertEqual(players["2"]["ownership"]["status"], "fantasy_free_agent")
            self.assertNotIn("3", players)

            kicker = players["2"]
            self.assertEqual(kicker["redraft_adp"]["primary_source_id"], "ffc-k")
            self.assertEqual(kicker["redraft_adp"]["primary"]["adp"], 90)
            self.assertEqual(kicker["activity"]["add"], {"status": "listed", "rank": 1, "count": 55})
            self.assertEqual(kicker["activity"]["drop"]["status"], "not_listed")
            self.assertIsNone(kicker["activity"]["drop"]["count"])

            projections = kicker["projections"]
            self.assertEqual(projections["summary"]["listed_provider_count"], 2)
            self.assertEqual(projections["summary"]["consensus_percentile"], 50.0)
            self.assertEqual(projections["summary"]["percentile_spread"], 100.0)
            self.assertEqual(
                projections["summary"]["provider_fantasy_points_policy"],
                "kept_separate_not_averaged",
            )
            self.assertEqual(projections["providers"]["fftoday"]["projected_fantasy_points"], 150)
            self.assertEqual(projections["providers"]["cbs_sports"]["projected_fantasy_points"], 145)
            self.assertNotIn("projected_fantasy_points", projections["summary"])

    def test_legacy_league_rosters_do_not_control_player_signal_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)

            league_path = root / "public/data/League.json"
            league = json.loads(league_path.read_text(encoding="utf-8"))
            league["Teams"][0]["Roster"] = []
            league["Teams"][1]["Roster"] = ["1", "2"]
            league_path.write_text(json.dumps(league, indent=2) + "\n", encoding="utf-8")

            result = MODULE.build(root, config_path)
            players = {player["player_id"]: player for player in result["players"]}

            self.assertEqual("mighty_giants", players["1"]["ownership"]["status"])
            self.assertEqual("fantasy_free_agent", players["2"]["ownership"]["status"])
            self.assertIn("league_owned", players["1"]["population_reasons"])
            self.assertNotIn("league_owned", players["2"]["population_reasons"])
            self.assertEqual("Mighty Giants", result["managed_team"]["name"])

            source_ids = {source["id"] for source in result["sources"]}
            self.assertIn("league_display", source_ids)
            self.assertIn("canonical_league_manifest", source_ids)
            self.assertIn("canonical_league_rosters", source_ids)
            self.assertIn("canonical_player_identities", source_ids)
            self.assertIn("canonical_sleeper_players", source_ids)

    def test_canonical_identity_and_sleeper_fields_override_legacy_player_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)

            players_path = root / "public/data/Players.json"
            players = json.loads(players_path.read_text(encoding="utf-8"))
            players[0].update(
                {
                    "Name": "Wrong Legacy Name",
                    "Position": "WR",
                    "Status": "Legacy Status",
                    "ESPNID": "999999",
                    "SleeperDepthChartPosition": "WR",
                    "SleeperDepthChartOrder": 9,
                    "Salary": 55,
                    "SalaryProjected": 66,
                    "TeamAbbr": "AAA",
                }
            )
            players_path.write_text(json.dumps(players, indent=2) + "\n", encoding="utf-8")

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            sleeper["Records"][0]["Position"] = "DB"
            sleeper["Records"][0]["FantasyPositions"] = ["DB", "K"]
            sleeper_path.write_text(json.dumps(sleeper, indent=2) + "\n", encoding="utf-8")

            result = MODULE.build(root, config_path)
            player = next(item for item in result["players"] if item["player_id"] == "1")

            self.assertEqual("Kicker One", player["name"])
            self.assertEqual("K", player["position"])
            self.assertEqual("AAA", player["nfl_team"])
            self.assertEqual("Active", player["app_data"]["status"])
            self.assertEqual("101", player["app_data"]["espn_id"])
            self.assertEqual(55, player["app_data"]["salary"])
            self.assertEqual(66, player["app_data"]["salary_projected"])
            self.assertEqual("K", player["role"]["sleeper_depth_chart_position"])
            self.assertEqual(1, player["role"]["sleeper_depth_chart_order"])
            self.assertEqual("listed", player["source_signals"]["ffc-k"]["coverage_status"])
            self.assertEqual(
                "normalized_name_position",
                player["source_signals"]["ffc-k"]["join_method"],
            )

    def test_canonical_player_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            sleeper["Records"][0]["CanonicalPlayerID"] = "canonical-other"
            sleeper_path.write_text(json.dumps(sleeper, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                MODULE.PlayerSignalMaterializationError,
                "Canonical Sleeper player identity mismatch",
            ):
                MODULE.build(root, config_path)

    def test_malformed_canonical_fantasy_positions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            sleeper["Records"][0]["FantasyPositions"] = "K"
            sleeper_path.write_text(json.dumps(sleeper, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                MODULE.PlayerSignalMaterializationError,
                "FantasyPositions must be an array",
            ):
                MODULE.build(root, config_path)

    def test_preserves_top_n_absence_and_nominal_role_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)
            result = MODULE.build(root, config_path)
            players = {player["player_id"]: player for player in result["players"]}

            rostered = players["1"]
            self.assertEqual(rostered["activity"]["coverage_status"], "not_listed_in_current_union")
            self.assertIsNone(rostered["activity"]["add"]["rank"])
            self.assertIsNone(rostered["activity"]["add"]["count"])
            self.assertIn("never zero activity", rostered["activity"]["absence_semantics"])
            self.assertEqual(rostered["role"]["sleeper_depth_chart_order"], 1)
            self.assertEqual(rostered["role"]["interpretation"], "nominal_depth_chart_only_not_usage")
            self.assertEqual(rostered["source_signals"]["cbs-k"]["freshness"]["status"], "current")

    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        schema_path = root / "fantasy-management/_ai/schemas/player-signal-dataset.schema.json"

        result = MODULE.build(root, config_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)

        self.assertGreater(result["population"]["player_count"], 100)
        self.assertNotEqual(result["quality"]["status"], "error")
        kickers = [player for player in result["players"] if player["position"] == "K"]
        self.assertTrue(kickers)
        self.assertTrue(any(player["ownership"]["status"] == "fantasy_free_agent" for player in kickers))
        self.assertTrue(
            any(player["projections"]["summary"]["listed_provider_count"] >= 1 for player in kickers)
        )

    def test_current_repository_ownership_and_population_reasons_match_published_state(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/player-signal-materialization.json"
        published_path = root / "fantasy-management/generated/operations/player-signals.json"

        published = json.loads(published_path.read_text(encoding="utf-8"))
        roster_source = next(
            (
                source
                for source in published["sources"]
                if source.get("id") == "canonical_league_rosters"
            ),
            None,
        )
        self.assertIsNotNone(roster_source)
        roster_path = root / roster_source["path"]
        current_roster_hash = MODULE.ops.sha256_text(
            roster_path.read_text(encoding="utf-8")
        )
        if roster_source.get("content_sha256") != current_roster_hash:
            self.skipTest(
                "published player-signals is stale relative to current canonical "
                "league rosters; the materializer is expected to rebuild it"
            )

        result = MODULE.build(root, config_path)
        published_by_id = {
            str(player["player_id"]): player
            for player in published["players"]
        }
        result_by_id = {
            str(player["player_id"]): player
            for player in result["players"]
        }

        common_ids = set(published_by_id) & set(result_by_id)
        self.assertGreater(len(common_ids), 100)
        for player_id in common_ids:
            published_player = published_by_id[player_id]
            result_player = result_by_id[player_id]
            self.assertEqual(
                published_player["ownership"],
                result_player["ownership"],
                f"ownership drift for player {player_id}",
            )
            self.assertEqual(
                "league_owned" in published_player["population_reasons"],
                "league_owned" in result_player["population_reasons"],
                f"league_owned population reason drift for player {player_id}",
            )

        self.assertEqual(published["managed_team"], result["managed_team"])

    def test_production_workflow_materializes_player_signals_after_external_signals(self) -> None:
        root = SCRIPT_PATH.parents[3]
        workflow_path = root / ".github/workflows/materialize-fantasy-operations-inputs.yml"
        workflow = workflow_path.read_text(encoding="utf-8")

        external_command = "python fantasy-management/_ai/scripts/materialize_external_signals.py"
        player_command = "python fantasy-management/_ai/scripts/build_player_signal_dataset.py"
        player_output = "fantasy-management/generated/operations/player-signals.json"

        self.assertIn("fantasy-management/_ai/scripts/tests/test_build_player_signal_dataset.py", workflow)
        self.assertIn(external_command, workflow)
        self.assertIn(player_command, workflow)
        self.assertLess(workflow.index(external_command), workflow.index(player_command))
        self.assertIn(player_output, workflow)


if __name__ == "__main__":
    unittest.main()
