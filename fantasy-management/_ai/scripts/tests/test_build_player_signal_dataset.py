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
                "sources": {
                    "league": "public/data/League.json",
                    "players": "public/data/Players.json",
                    "timestamps": "public/data/Timestamps.json",
                    "external_signal_relevance": "fantasy-management/generated/operations/external-signal-relevance.json",
                },
                "source_catalog": "fantasy-management/_ai/operations-source-catalog.json",
                "population": {"positions": ["K"]},
                "output": {"player_signals": "fantasy-management/generated/operations/player-signals.json"},
            },
        )
        return config_path

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
