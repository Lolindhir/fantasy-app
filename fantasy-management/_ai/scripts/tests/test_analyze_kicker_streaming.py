from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "analyze_kicker_streaming.py"
SPEC = importlib.util.spec_from_file_location("analyze_kicker_streaming", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KickerStreamingAnalysisTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def candidate(
        self,
        player_id: str,
        name: str,
        availability: str,
        *,
        cbs_midpoint: float,
        fftoday_percentile: float,
        ffc_percentile: float,
        add_count: int,
    ) -> dict:
        return {
            "player_id": player_id,
            "name": name,
            "nfl_team": "AAA",
            "availability": availability,
            "ownership": {
                "status": "mighty_giants" if availability == "held" else "fantasy_free_agent",
                "teams": [],
            },
            "injury": {
                "coverage_status": "no_current_injury_signal",
                "is_injured": False,
                "designation": None,
                "external_verification_priority": "routine",
            },
            "role": {
                "sleeper_depth_chart_position": "K",
                "sleeper_depth_chart_order": 1,
                "coverage_status": "available",
                "interpretation": "nominal_depth_chart_only_not_usage",
            },
            "market": {},
            "redraft_adp": {
                "primary": {
                    "listed": True,
                    "applicable": True,
                    "percentile": ffc_percentile,
                }
            },
            "projections": {
                "providers": {
                    "fftoday": {
                        "listed": True,
                        "percentile": fftoday_percentile,
                    }
                }
            },
            "activity": {
                "add": {
                    "status": "listed",
                    "count": add_count,
                }
            },
            "league_scoring_projection": {
                "cbs_sports": {
                    "status": "bounded",
                    "points_min": cbs_midpoint - 1,
                    "points_max": cbs_midpoint + 1,
                    "provider_projected_fantasy_points": cbs_midpoint - 10,
                    "reason": "synthetic",
                    "components": {},
                },
                "fftoday": {
                    "status": "bounded",
                    "points_min": 100,
                    "points_max": 180,
                    "provider_projected_fantasy_points": 120,
                    "reason": "synthetic",
                    "components": {},
                },
            },
        }

    def config(self) -> dict:
        return {
            "schema_version": 1,
            "analysis_id": "kicker-streaming",
            "source": "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            "baseline": {
                "minimum_core_signal_count": 2,
                "shortlist_free_agent_count": 2,
                "weights": {
                    "cbs_league_scoring_percentile": 0.42,
                    "fftoday_projection_percentile": 0.37,
                    "ffc_kicker_adp_percentile": 0.21,
                },
                "activity_policy": "research_tiebreaker_only",
            },
            "weekly": {
                "weights": {
                    "baseline_score": 0.35,
                    "matchup_score": 0.10,
                    "offense_scoring_environment_score": 0.15,
                    "field_goal_opportunity_score": 0.20,
                    "weather_stadium_score": 0.10,
                    "qb_injury_context_score": 0.10,
                },
                "switch_threshold_points": 5.0,
                "allowed_job_security": ["confirmed_starter", "probable_starter"],
                "disqualifying_player_injury_status": ["out"],
            },
            "persistence": {
                "default": "stdout_only",
                "repository_analysis_write_requires_explicit_approval": True,
            },
        }

    def prepare_root(self, root: Path) -> tuple[Path, str]:
        fingerprint = "a" * 64
        source = {
            "schema_version": 1,
            "dataset_id": "kicker-streaming-inputs",
            "generated_at": "2026-08-10T08:00:00Z",
            "input_fingerprint": fingerprint,
            "managed_team": {"team_id": 1, "name": "Mighty Giants"},
            "league": {
                "season": "2026",
                "phase": "Regular Season",
                "current_week": 1,
            },
            "population": {
                "position": "K",
                "held_count": 1,
                "free_agent_count": 2,
                "candidate_count": 3,
            },
            "candidates": [
                self.candidate(
                    "1",
                    "Held Kicker",
                    "held",
                    cbs_midpoint=150,
                    fftoday_percentile=70,
                    ffc_percentile=70,
                    add_count=20,
                ),
                self.candidate(
                    "2",
                    "Best Free Kicker",
                    "free_agent",
                    cbs_midpoint=180,
                    fftoday_percentile=90,
                    ffc_percentile=90,
                    add_count=100,
                ),
                self.candidate(
                    "3",
                    "Other Free Kicker",
                    "free_agent",
                    cbs_midpoint=130,
                    fftoday_percentile=60,
                    ffc_percentile=50,
                    add_count=10,
                ),
            ],
            "quality": {"status": "ok"},
        }
        self.write_json(
            root,
            "fantasy-management/generated/operations/kicker-streaming-inputs.json",
            source,
        )
        config_path = self.write_json(
            root,
            "fantasy-management/_ai/kicker-streaming-analysis-config.json",
            self.config(),
        )
        return config_path, fingerprint

    def weekly_context(self, fingerprint: str, *, held_job: str = "confirmed_starter") -> dict:
        def player(player_id: str, job: str, base: int) -> dict:
            return {
                "player_id": player_id,
                "job_security": job,
                "player_injury_status": "clear",
                "matchup_score": base,
                "offense_scoring_environment_score": base,
                "field_goal_opportunity_score": base,
                "weather_stadium_score": base,
                "qb_injury_context_score": base,
                "evidence": [
                    {
                        "source_type": "analysis",
                        "note": "Synthetic current-week evidence",
                        "checked_at": "2026-09-08T12:00:00Z",
                    }
                ],
            }

        return {
            "schema_version": 1,
            "source_input_fingerprint": fingerprint,
            "season": "2026",
            "week": 1,
            "checked_at": "2026-09-08T12:00:00Z",
            "players": [
                player("1", held_job, 60),
                player("2", "confirmed_starter", 90),
                player("3", "confirmed_starter", 50),
            ],
        }

    def test_baseline_builds_shortlist_without_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, _ = self.prepare_root(root)
            result = MODULE.build(root, config_path)

            self.assertEqual(result["mode"], "baseline")
            self.assertEqual(result["ranking"][0]["player_id"], "2")
            self.assertEqual(result["recommendation"]["status"], "weekly_context_required")
            self.assertEqual(result["recommendation"]["held_player_id"], "1")
            self.assertEqual(result["research_shortlist_ids"], ["1", "2", "3"])
            self.assertIsNone(result["ranking"][0]["weekly"])

    def test_weekly_context_recommends_material_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, fingerprint = self.prepare_root(root)
            weekly_path = self.write_json(root, "weekly.json", self.weekly_context(fingerprint))
            result = MODULE.build(root, config_path, weekly_path)

            self.assertEqual(result["mode"], "weekly")
            self.assertEqual(result["recommendation"]["status"], "switch_recommended")
            self.assertEqual(result["recommendation"]["target_player_id"], "2")
            self.assertGreater(result["recommendation"]["score_delta"], 5)

    def test_weekly_context_can_recommend_no_switch_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, fingerprint = self.prepare_root(root)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["weekly"]["switch_threshold_points"] = 40
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            weekly_path = self.write_json(root, "weekly.json", self.weekly_context(fingerprint))
            result = MODULE.build(root, config_path, weekly_path)

            self.assertEqual(result["recommendation"]["status"], "no_switch_recommended")
            self.assertEqual(result["recommendation"]["target_player_id"], "2")

    def test_unconfirmed_held_job_can_force_switch_to_verified_alternative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, fingerprint = self.prepare_root(root)
            weekly_path = self.write_json(
                root,
                "weekly.json",
                self.weekly_context(fingerprint, held_job="not_current_starter"),
            )
            result = MODULE.build(root, config_path, weekly_path)

            self.assertEqual(result["recommendation"]["status"], "switch_recommended")
            self.assertIn("held_kicker_not_weekly_eligible", result["recommendation"]["reason_codes"])

    def test_rejects_weekly_context_from_old_input_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path, fingerprint = self.prepare_root(root)
            context = self.weekly_context(fingerprint)
            context["source_input_fingerprint"] = "b" * 64
            weekly_path = self.write_json(root, "weekly.json", context)

            with self.assertRaisesRegex(MODULE.KickerStreamingAnalysisError, "fingerprint"):
                MODULE.build(root, config_path, weekly_path)

    def test_current_repository_baseline_validates(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/_ai/kicker-streaming-analysis-config.json"
        schema_path = root / "fantasy-management/_ai/schemas/kicker-streaming-analysis.schema.json"

        result = MODULE.build(root, config_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)

        self.assertEqual(result["mode"], "baseline")
        self.assertEqual(result["recommendation"]["status"], "weekly_context_required")
        self.assertEqual(result["quality"]["held_count"], 1)
        self.assertGreater(result["quality"]["comparable_candidate_count"], 1)
        held = [row for row in result["ranking"] if row["availability"] == "held"]
        self.assertEqual(len(held), 1)
        self.assertEqual(held[0]["name"], "Jake Bates")
        self.assertGreater(len(result["research_shortlist_ids"]), 1)


if __name__ == "__main__":
    unittest.main()
