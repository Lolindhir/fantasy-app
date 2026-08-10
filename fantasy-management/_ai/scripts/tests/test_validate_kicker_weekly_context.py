from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "validate_kicker_weekly_context.py"
SPEC = importlib.util.spec_from_file_location("validate_kicker_weekly_context", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KickerWeeklyContextValidationTests(unittest.TestCase):
    def config(self) -> dict:
        return {
            "schema_version": 1,
            "research_id": "kicker-weekly-context",
            "research": {
                "decision_ready_max_hours_before_kickoff": 168,
                "weather_max_age_hours": 24,
                "job_security_max_age_hours": 24,
                "player_injury_max_age_hours": 24,
                "qb_injury_max_age_hours": 24,
                "venue_max_age_hours": 168,
            },
        }

    def plan(self) -> dict:
        def candidate(player_id: str, availability: str, game_id: str) -> dict:
            return {
                "player_id": player_id,
                "availability": availability,
                "schedule": {
                    "status": "scheduled",
                    "game_id": game_id,
                    "kickoff_epoch": 1789318800.0,
                },
            }

        return {
            "schema_version": 1,
            "dataset_id": "kicker-weekly-research-plan",
            "input_fingerprint": "b" * 64,
            "source_input_fingerprint": "a" * 64,
            "season": "2026",
            "week": 1,
            "candidates": [
                candidate("1", "held", "held-game"),
                candidate("2", "free_agent", "free-game"),
            ],
        }

    def context(self) -> dict:
        def player(player_id: str, game_id: str) -> dict:
            return {
                "player_id": player_id,
                "game_id": game_id,
                "job_security": "confirmed_starter",
                "job_security_checked_at": "2026-09-08T11:00:00Z",
                "player_injury_status": "clear",
                "player_injury_checked_at": "2026-09-08T11:00:00Z",
                "qb_injury_checked_at": "2026-09-08T11:00:00Z",
                "matchup_score": 70,
                "offense_scoring_environment_score": 70,
                "field_goal_opportunity_score": 70,
                "weather_stadium_score": 70,
                "qb_injury_context_score": 70,
                "venue": {
                    "name": "Synthetic Stadium",
                    "location": "Synthetic City",
                    "roof_type": "open_air",
                    "roof_state": "not_applicable",
                    "weather_exposure": "exposed",
                    "checked_at": "2026-09-08T10:00:00Z",
                    "source_type": "official",
                    "reference": None,
                },
                "weather": {
                    "applicable": True,
                    "checked_at": "2026-09-08T11:30:00Z",
                    "source_type": "official_weather_service",
                    "summary": "Synthetic calm forecast",
                    "wind_mph": 5,
                    "precip_probability_pct": 10,
                    "temperature_f": 70,
                    "reference": None,
                },
                "evidence": [
                    {
                        "source_type": "official",
                        "note": "Synthetic evidence",
                        "checked_at": "2026-09-08T11:30:00Z",
                    }
                ],
            }

        return {
            "schema_version": 1,
            "source_input_fingerprint": "a" * 64,
            "research_plan_fingerprint": "b" * 64,
            "context_status": "decision_ready",
            "season": "2026",
            "week": 1,
            "checked_at": "2026-09-08T12:00:00Z",
            "players": [
                player("1", "held-game"),
                player("2", "free-game"),
            ],
        }

    def schema(self) -> dict:
        root = Path(__file__).resolve().parents[4]
        return json.loads(
            (root / "fantasy-management/_ai/schemas/kicker-weekly-context.schema.json").read_text(encoding="utf-8")
        )

    def test_decision_ready_context_passes(self) -> None:
        result = MODULE.validate_context(
            self.context(),
            self.plan(),
            self.config(),
            self.schema(),
            require_decision_ready=True,
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["decision_ready"])
        self.assertEqual(result["player_count"], 2)

    def test_rejects_wrong_game_mapping(self) -> None:
        context = self.context()
        context["players"][1]["game_id"] = "wrong-game"
        with self.assertRaises(MODULE.KickerWeeklyContextValidationError):
            MODULE.validate_context(context, self.plan(), self.config(), self.schema(), require_decision_ready=True)

    def test_rejects_context_outside_decision_window(self) -> None:
        context = self.context()
        context["checked_at"] = "2026-09-01T12:00:00Z"
        with self.assertRaises(MODULE.KickerWeeklyContextValidationError):
            MODULE.validate_context(context, self.plan(), self.config(), self.schema(), require_decision_ready=True)

    def test_rejects_stale_weather(self) -> None:
        context = self.context()
        context["players"][1]["weather"]["checked_at"] = "2026-09-07T00:00:00Z"
        with self.assertRaises(MODULE.KickerWeeklyContextValidationError):
            MODULE.validate_context(context, self.plan(), self.config(), self.schema(), require_decision_ready=True)

    def test_preliminary_context_cannot_run_decision(self) -> None:
        context = self.context()
        context["context_status"] = "preliminary"
        with self.assertRaises(MODULE.KickerWeeklyContextValidationError):
            MODULE.validate_context(context, self.plan(), self.config(), self.schema(), require_decision_ready=True)


if __name__ == "__main__":
    unittest.main()
