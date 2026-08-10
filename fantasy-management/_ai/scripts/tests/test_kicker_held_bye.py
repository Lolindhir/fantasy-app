from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_kicker_weekly_analysis as RUNNER
import validate_kicker_weekly_context as VALIDATOR


class HeldKickerByeTests(unittest.TestCase):
    def schema(self) -> dict:
        root = Path(__file__).resolve().parents[4]
        return json.loads(
            (root / "fantasy-management/_ai/schemas/kicker-weekly-context.schema.json").read_text(encoding="utf-8")
        )

    def research_config(self) -> dict:
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

    def plan(self, *, held_status: str = "bye") -> dict:
        held_schedule = {"status": held_status}
        if held_status == "scheduled":
            held_schedule.update({"game_id": "held-game", "kickoff_epoch": 1789318800.0})
        return {
            "schema_version": 1,
            "dataset_id": "kicker-weekly-research-plan",
            "input_fingerprint": "b" * 64,
            "source_input_fingerprint": "a" * 64,
            "season": "2026",
            "week": 1,
            "candidates": [
                {
                    "player_id": "1",
                    "name": "Held Kicker",
                    "availability": "held",
                    "schedule": held_schedule,
                },
                {
                    "player_id": "2",
                    "name": "Free Kicker",
                    "availability": "free_agent",
                    "schedule": {
                        "status": "scheduled",
                        "game_id": "free-game",
                        "kickoff_epoch": 1789318800.0,
                    },
                },
            ],
        }

    def player_context(self, player_id: str, game_id: str | None) -> dict:
        return {
            "player_id": player_id,
            "game_id": game_id,
            "job_security": "confirmed_starter",
            "job_security_checked_at": "2026-09-08T11:00:00Z",
            "player_injury_status": "clear",
            "player_injury_checked_at": "2026-09-08T11:00:00Z",
            "qb_injury_checked_at": "2026-09-08T11:00:00Z",
            "matchup_score": 75,
            "offense_scoring_environment_score": 75,
            "field_goal_opportunity_score": 75,
            "weather_stadium_score": 75,
            "qb_injury_context_score": 75,
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
                    "note": "Synthetic current-week evidence",
                    "checked_at": "2026-09-08T11:30:00Z",
                }
            ],
        }

    def context(self, *, include_held_bye: bool = False) -> dict:
        players = [self.player_context("2", "free-game")]
        if include_held_bye:
            players.insert(0, self.player_context("1", None))
        return {
            "schema_version": 1,
            "source_input_fingerprint": "a" * 64,
            "research_plan_fingerprint": "b" * 64,
            "context_status": "decision_ready",
            "season": "2026",
            "week": 1,
            "checked_at": "2026-09-08T12:00:00Z",
            "players": players,
        }

    def test_decision_ready_context_allows_held_bye_to_be_omitted(self) -> None:
        result = VALIDATOR.validate_context(
            self.context(),
            self.plan(),
            self.research_config(),
            self.schema(),
            require_decision_ready=True,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["held_bye_player_ids"], ["1"])
        self.assertEqual(result["scheduled_player_count"], 1)

    def test_decision_ready_context_rejects_fake_scoring_row_for_bye(self) -> None:
        with self.assertRaises(VALIDATOR.KickerWeeklyContextValidationError):
            VALIDATOR.validate_context(
                self.context(include_held_bye=True),
                self.plan(),
                self.research_config(),
                self.schema(),
                require_decision_ready=True,
            )

    def test_runner_selects_best_verified_stream_for_held_bye(self) -> None:
        analysis = {
            "ranking": [
                {
                    "player_id": "1",
                    "name": "Held Kicker",
                    "availability": "held",
                    "weekly": None,
                },
                {
                    "player_id": "2",
                    "name": "Free Kicker",
                    "availability": "free_agent",
                    "weekly": {"eligible": True, "final_score": 82.5},
                },
                {
                    "player_id": "3",
                    "name": "Better Free Kicker",
                    "availability": "free_agent",
                    "weekly": {"eligible": True, "final_score": 88.0},
                },
            ],
            "recommendation": {"status": "insufficient_context"},
        }
        plan = self.plan()
        plan["candidates"].append(
            {
                "player_id": "3",
                "name": "Better Free Kicker",
                "availability": "free_agent",
                "schedule": {"status": "scheduled", "game_id": "better-game", "kickoff_epoch": 1789318800.0},
            }
        )

        result = RUNNER.apply_held_bye_recommendation(analysis, plan)
        recommendation = result["recommendation"]
        self.assertEqual(recommendation["status"], "switch_recommended")
        self.assertEqual(recommendation["held_player_id"], "1")
        self.assertEqual(recommendation["target_player_id"], "3")
        self.assertIsNone(recommendation["score_delta"])
        self.assertIn("held_kicker_bye_week", recommendation["reason_codes"])

    def test_runner_does_not_invent_bye_score_delta(self) -> None:
        analysis = {
            "ranking": [
                {"player_id": "1", "name": "Held Kicker", "availability": "held", "weekly": None},
                {"player_id": "2", "name": "Free Kicker", "availability": "free_agent", "weekly": None},
            ],
            "recommendation": {"status": "insufficient_context"},
        }
        result = RUNNER.apply_held_bye_recommendation(analysis, self.plan())
        recommendation = result["recommendation"]
        self.assertEqual(recommendation["status"], "insufficient_context")
        self.assertIsNone(recommendation["score_delta"])
        self.assertIn("no_eligible_free_agent_weekly_context", recommendation["reason_codes"])

    def test_runner_leaves_normal_week_recommendation_unchanged(self) -> None:
        analysis = {
            "ranking": [],
            "recommendation": {
                "status": "no_switch_recommended",
                "held_player_id": "1",
                "target_player_id": "2",
                "score_delta": 1.5,
                "reason_codes": ["no_material_weekly_score_advantage"],
                "summary": "unchanged",
            },
        }
        result = RUNNER.apply_held_bye_recommendation(analysis, self.plan(held_status="scheduled"))
        self.assertEqual(result["recommendation"]["summary"], "unchanged")


if __name__ == "__main__":
    unittest.main()
