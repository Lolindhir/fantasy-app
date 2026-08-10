from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import jsonschema

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location(
    "build_kicker_weekly_research_plan",
    SCRIPTS_DIR / "build_kicker_weekly_research_plan.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KickerWeeklyResearchPlanTests(unittest.TestCase):
    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = Path(__file__).resolve().parents[4]
        source = json.loads((root / "fantasy-management/generated/operations/kicker-streaming-inputs.json").read_text(encoding="utf-8"))
        analysis_config = json.loads((root / "fantasy-management/_ai/kicker-streaming-analysis-config.json").read_text(encoding="utf-8"))
        research_config = json.loads((root / "fantasy-management/_ai/kicker-weekly-research-config.json").read_text(encoding="utf-8"))
        schedule = json.loads((root / "public/data/Schedule.json").read_text(encoding="utf-8-sig"))
        schema = json.loads((root / "fantasy-management/_ai/schemas/kicker-weekly-research-plan.schema.json").read_text(encoding="utf-8"))

        payload = MODULE.build_research_plan(source, analysis_config, research_config, schedule)
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)

        self.assertEqual(payload["dataset_id"], "kicker-weekly-research-plan")
        self.assertEqual(payload["season"], "2026")
        self.assertEqual(payload["week"], 1)
        self.assertEqual(payload["population"]["held_count"], 1)
        self.assertEqual(payload["population"]["shortlisted_free_agent_count"], 8)
        self.assertEqual(payload["population"]["candidate_count"], 9)

        held = next(candidate for candidate in payload["candidates"] if candidate["availability"] == "held")
        self.assertEqual(held["name"], "Jake Bates")
        self.assertEqual(held["nfl_team"], "DET")
        self.assertEqual(held["schedule"]["game_id"], "20260913_NO@DET")
        self.assertEqual(held["schedule"]["opponent"], "NO")
        self.assertEqual(held["schedule"]["team_side"], "home")
        self.assertEqual(held["venue_research"]["expected_home_team"], "DET")

    def test_schedule_resolution_supports_bye(self) -> None:
        games = [{"game_id": "g1", "home": "LAR", "away": "SF", "neutral_site": True}]
        bye = MODULE.resolve_team_schedule("DET", games)
        self.assertEqual(bye["status"], "bye")
        self.assertEqual(bye["team_side"], "bye")
        self.assertIsNone(bye["game_id"])

    def test_multiple_games_fail_closed(self) -> None:
        games = [
            {"game_id": "g1", "home": "DET", "away": "NO"},
            {"game_id": "g2", "home": "DET", "away": "GB"},
        ]
        with self.assertRaises(MODULE.KickerWeeklyResearchPlanError):
            MODULE.resolve_team_schedule("DET", games)


if __name__ == "__main__":
    unittest.main()
