from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_free_agent_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_free_agent_dataset", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FreeAgentDatasetTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def player(self, player_id: str, name: str, position: str, ownership_status: str, source_free_agent: bool) -> dict:
        return {
            "player_id": player_id,
            "name": name,
            "position": position,
            "nfl_team": "AAA",
            "population_reasons": ["has_nfl_team"],
            "ownership": {"status": ownership_status, "teams": []},
            "app_data": {
                "status": "Active",
                "age": 27,
                "years_experience": 3,
                "salary": 5,
                "salary_projected": 6,
                "is_free_agent_source_field": source_free_agent,
                "espn_id": None,
            },
            "injury": {},
            "role": {
                "sleeper_depth_chart_position": position,
                "sleeper_depth_chart_order": 1,
                "coverage_status": "available",
                "interpretation": "nominal_depth_chart_only_not_usage",
            },
            "source_signals": {},
            "market": {},
            "redraft_adp": {},
            "projections": {"providers": {}, "summary": {}},
            "activity": {},
        }

    def prepare_root(self, root: Path, *, quality_status: str = "ok") -> Path:
        self.write_json(
            root,
            "fantasy-management/generated/operations/player-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "player-signals",
                "generated_at": "2026-08-10T06:00:00Z",
                "input_fingerprint": "a" * 64,
                "players": [
                    self.player("1", "Rostered Kicker", "K", "mighty_giants", False),
                    self.player("2", "Free Kicker", "K", "fantasy_free_agent", False),
                    self.player("3", "Free Receiver", "WR", "fantasy_free_agent", False),
                    self.player("4", "Rostered Receiver", "WR", "opponent_rostered", True),
                ],
                "quality": {
                    "status": quality_status,
                    "issue_count": 2 if quality_status == "warning" else 0,
                    "issues": [],
                },
            },
        )
        config_path = root / "fantasy-management/automation/free-agent-materialization.json"
        self.write_json(
            root,
            "fantasy-management/automation/free-agent-materialization.json",
            {
                "schema_version": 1,
                "materialization_id": "test-free-agent-materialization",
                "source": {
                    "player_signals": "fantasy-management/generated/operations/player-signals.json"
                },
                "population": {
                    "positions": ["QB", "RB", "WR", "TE", "K"],
                    "ownership_status": "fantasy_free_agent",
                },
                "output": {
                    "free_agent_signals": "fantasy-management/generated/operations/free-agent-signals.json"
                },
            },
        )
        return config_path

    def test_selects_only_fantasy_free_agents_and_ignores_source_is_free_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root)
            result = MODULE.build(root, config_path)

            self.assertEqual(result["dataset_id"], "free-agent-signals")
            self.assertEqual(result["population"]["source_player_count"], 4)
            self.assertEqual(result["population"]["player_count"], 2)
            self.assertEqual(result["population"]["position_counts"], {"K": 1, "WR": 1})
            self.assertEqual([player["player_id"] for player in result["players"]], ["2", "3"])
            self.assertTrue(
                all(player["ownership"]["status"] == "fantasy_free_agent" for player in result["players"])
            )
            self.assertFalse(result["players"][0]["app_data"]["is_free_agent_source_field"])

    def test_propagates_warning_quality_without_inventing_new_player_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root, quality_status="warning")
            result = MODULE.build(root, config_path)

            self.assertEqual(result["quality"]["status"], "warning")
            self.assertEqual(result["quality"]["source_quality_status"], "warning")
            self.assertEqual(result["quality"]["source_issue_count"], 2)
            self.assertNotIn("recommendation", result)
            self.assertNotIn("tier", result)

    def test_rejects_error_quality_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root, quality_status="error")
            with self.assertRaisesRegex(MODULE.FreeAgentMaterializationError, "quality"):
                MODULE.build(root, config_path)

    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/free-agent-materialization.json"
        schema_path = root / "fantasy-management/_ai/schemas/free-agent-dataset.schema.json"

        result = MODULE.build(root, config_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)

        self.assertGreater(result["population"]["player_count"], 0)
        self.assertTrue(any(player["position"] == "K" for player in result["players"]))
        self.assertTrue(
            all(player["ownership"]["status"] == "fantasy_free_agent" for player in result["players"])
        )
        self.assertEqual(
            len({player["player_id"] for player in result["players"]}),
            result["population"]["player_count"],
        )

    def test_production_workflow_materializes_free_agents_after_player_signals(self) -> None:
        root = SCRIPT_PATH.parents[3]
        workflow_path = root / ".github/workflows/materialize-fantasy-operations-inputs.yml"
        workflow = workflow_path.read_text(encoding="utf-8")

        player_command = "python fantasy-management/_ai/scripts/build_player_signal_dataset.py"
        free_agent_command = "python fantasy-management/_ai/scripts/build_free_agent_dataset.py"
        free_agent_output = "fantasy-management/generated/operations/free-agent-signals.json"

        self.assertIn("fantasy-management/automation/free-agent-materialization.json", workflow)
        self.assertIn("fantasy-management/_ai/scripts/tests/test_build_free_agent_dataset.py", workflow)
        self.assertIn("fantasy-management/_ai/schemas/free-agent-dataset.schema.json", workflow)
        self.assertIn(player_command, workflow)
        self.assertIn(free_agent_command, workflow)
        self.assertLess(workflow.index(player_command), workflow.index(free_agent_command))
        self.assertIn(free_agent_output, workflow)
        self.assertIn("fantasy_free_agent", workflow)


if __name__ == "__main__":
    unittest.main()
