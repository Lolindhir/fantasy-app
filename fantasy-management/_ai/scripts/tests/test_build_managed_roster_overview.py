from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from build_managed_roster_overview import build, render_markdown  # noqa: E402


class ManagedRosterOverviewTests(unittest.TestCase):
    def test_build_separates_deterministic_structure_from_hybrid_classification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            result = build(root, root / "fantasy-management/automation/managed-roster-overview.json")

            self.assertEqual("managed-roster-overview", result["dataset_id"])
            self.assertEqual("pre_lock", result["structure"]["taxi"]["phase"])
            self.assertFalse(result["structure"]["taxi"]["binding"])
            self.assertEqual(6, result["structure"]["capacity"]["regular_active_capacity"])
            self.assertEqual(3, result["structure"]["capacity"]["current_active_count"])
            self.assertEqual(1, result["structure"]["lineup"]["fixed_starters"]["QB"])
            self.assertEqual(3, result["structure"]["skill_pool"]["required_skill_lineup_slots"])
            self.assertEqual(1, result["structure"]["skill_pool"]["startable_skill_pool"])
            self.assertEqual(-2, result["structure"]["skill_pool"]["skill_pool_margin"])

            quarterback = next(item for item in result["players"] if item["name"] == "Quarter Back")
            prospect = next(item for item in result["players"] if item["name"] == "Rookie Runner")
            self.assertEqual("backup", quarterback["roster_role"])
            self.assertEqual("coverage_reserve", quarterback["structural_function"])
            self.assertTrue(quarterback["coverage_protected"])
            self.assertFalse(quarterback["churn_eligible"])
            self.assertEqual("prospect", prospect["roster_role"])
            self.assertEqual("conditional", prospect["roster_security"])
            self.assertTrue(prospect["potential_churn_after_taxi_reassignment"])
            self.assertEqual("warning", result["quality"]["status"])
            self.assertEqual(1, result["evaluation"]["unclassified_count"])

            markdown = render_markdown(result)
            self.assertIn("# Mighty Giants – Current Roster Overview", markdown)
            self.assertIn("Rookie Runner", markdown)
            self.assertIn("provisional_requires_virtual_taxi_assignment", markdown)

    def test_user_override_wins_over_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            state_path = root / "fantasy-management/automation/roster-evaluation-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["user_overrides"] = [
                {
                    "name": "Rookie Runner",
                    "position": "RB",
                    "roster_security": "hold",
                    "notes": ["User wants to protect this player for now."],
                }
            ]
            state_path.write_text(json.dumps(state), encoding="utf-8")

            result = build(root, root / "fantasy-management/automation/managed-roster-overview.json")
            prospect = next(item for item in result["players"] if item["name"] == "Rookie Runner")
            self.assertEqual("hold", prospect["roster_security"])
            self.assertTrue(prospect["classification"]["user_override"])
            self.assertFalse(prospect["potential_churn_after_taxi_reassignment"])
            self.assertEqual(1, result["evaluation"]["user_override_count"])

    def _write_fixture(self, root: Path) -> None:
        for path in (
            "public/data",
            "fantasy-management/generated/operations",
            "fantasy-management/automation",
        ):
            (root / path).mkdir(parents=True, exist_ok=True)

        self._write_json(
            root / "fantasy-management/automation/managed-roster-overview.json",
            {
                "schema_version": 1,
                "managed_team": {"team_id": 1},
                "sources": {
                    "league": "public/data/League.json",
                    "managed_roster_signals": "fantasy-management/generated/operations/managed-roster-signals.json",
                    "evaluation_state": "fantasy-management/automation/roster-evaluation-state.json",
                },
                "policies": {"flex_eligible_positions": ["RB", "WR", "TE"], "general_churn_target": 2},
                "outputs": {
                    "json": "fantasy-management/generated/operations/managed-roster-overview.json",
                    "markdown": "fantasy-management/generated/operations/managed-roster-overview.md",
                },
            },
        )
        self._write_json(
            root / "public/data/League.json",
            {
                "Status": "Draft-Season",
                "Phase": "Pre Draft",
                "FinalScoredWeek": 0,
                "RosterSize": ["QB", "RB", "WR", "FLEX", "K", "BN"],
                "Settings": {"taxi_slots": 1, "reserve_slots": 1},
                "Teams": [
                    {
                        "TeamID": 1,
                        "Team": "Mighty Giants",
                        "TeamAbbr": "MiG",
                        "Roster": ["1", "2", "3", "4"],
                        "Taxi": ["4"],
                        "Reserve": [],
                    }
                ],
            },
        )
        self._write_json(
            root / "fantasy-management/generated/operations/managed-roster-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "managed-roster-signals",
                "generated_at": "2026-08-20T08:00:00Z",
                "managed_team": {"team_id": 1, "name": "Mighty Giants"},
                "players": [
                    self._signal("1", "Quarter Back", "QB", ["roster"]),
                    self._signal("2", "Starting Runner", "RB", ["roster"]),
                    self._signal("3", "Starting Receiver", "WR", ["roster"]),
                    self._signal("4", "Rookie Runner", "RB", ["roster", "taxi"]),
                ],
            },
        )
        self._write_json(
            root / "fantasy-management/automation/roster-evaluation-state.json",
            {
                "schema_version": 1,
                "team_id": 1,
                "evaluation_mode": "hybrid_manual_v1",
                "as_of": "2026-08-19",
                "coverage_targets": {"QB": {"floor": 1, "preferred": 2}},
                "classifications": [
                    {
                        "name": "Quarter Back",
                        "position": "QB",
                        "roster_role": "backup",
                        "roster_security": "conditional",
                    },
                    {
                        "name": "Starting Runner",
                        "position": "RB",
                        "roster_role": "core_starter",
                        "roster_security": "locked",
                    },
                    {
                        "name": "Rookie Runner",
                        "position": "RB",
                        "roster_role": "prospect",
                        "roster_security": "conditional",
                        "boundary_priority": 10,
                    },
                ],
                "user_overrides": [],
            },
        )

    @staticmethod
    def _signal(player_id: str, name: str, position: str, sections: list[str]) -> dict[str, object]:
        return {
            "player_id": player_id,
            "name": name,
            "position": position,
            "nfl_team": "AAA",
            "roster_sections": sections,
            "app_data": {},
            "injury": {},
            "market": {},
        }

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
