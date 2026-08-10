from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_kicker_streaming_inputs.py"
SPEC = importlib.util.spec_from_file_location("build_kicker_streaming_inputs", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KickerStreamingInputTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def player(self, player_id: str, name: str, ownership_status: str) -> dict:
        return {
            "player_id": player_id,
            "name": name,
            "position": "K",
            "nfl_team": "AAA",
            "ownership": {"status": ownership_status, "teams": []},
            "injury": {},
            "role": {
                "sleeper_depth_chart_position": "K",
                "sleeper_depth_chart_order": 1,
                "coverage_status": "available",
                "interpretation": "nominal_depth_chart_only_not_usage",
            },
            "market": {},
            "redraft_adp": {"primary": {"adp": 140}},
            "activity": {},
            "projections": {
                "providers": {
                    "cbs_sports": {
                        "listed": True,
                        "fg_1_19_made": 0,
                        "fg_1_19_attempts": 0,
                        "fg_20_29_made": 1,
                        "fg_20_29_attempts": 1,
                        "fg_30_39_made": 1,
                        "fg_30_39_attempts": 1,
                        "fg_40_49_made": 1,
                        "fg_40_49_attempts": 1,
                        "fg_50_plus_made": 2,
                        "fg_50_plus_attempts": 2,
                        "xpm": 40,
                        "xpa": 42,
                        "projected_fantasy_points": 155,
                    },
                    "fftoday": {
                        "listed": True,
                        "fgm": 30,
                        "fga": 34,
                        "epm": 40,
                        "epa": 42,
                        "projected_fantasy_points": 150,
                    },
                },
                "summary": {
                    "listed_provider_count": 2,
                    "consensus_percentile": 80,
                },
            },
        }

    def scoring(self) -> dict:
        return {
            "fgm_0_19": 3,
            "fgm_20_29": 3,
            "fgm_30_39": 3,
            "fgm_40_49": 4,
            "fgm_50_59": 5,
            "fgm_60p": 6,
            "fgmiss_0_19": 0,
            "fgmiss_20_29": 0,
            "fgmiss_30_39": 0,
            "fgmiss_40_49": 0,
            "fgmiss_50_59": 0,
            "fgmiss_60p": 0,
            "xpm": 1,
            "xpmiss": -1,
        }

    def prepare_root(self, root: Path, *, fingerprint_match: bool = True) -> Path:
        held = self.player("1", "Held Kicker", "mighty_giants")
        free = self.player("2", "Free Kicker", "fantasy_free_agent")
        opponent = self.player("3", "Opponent Kicker", "opponent_rostered")
        player_fingerprint = "a" * 64
        self.write_json(
            root,
            "public/data/League.json",
            {
                "Season": "2026",
                "Phase": "Pre Draft",
                "CurrentWeek": 1,
                "ScoringType": self.scoring(),
                "Teams": [{"TeamID": 1, "Team": "Mighty Giants"}],
            },
        )
        self.write_json(
            root,
            "fantasy-management/generated/operations/player-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "player-signals",
                "generated_at": "2026-08-10T08:00:00Z",
                "input_fingerprint": player_fingerprint,
                "players": [held, free, opponent],
                "quality": {"status": "ok", "issue_count": 0},
            },
        )
        self.write_json(
            root,
            "fantasy-management/generated/operations/free-agent-signals.json",
            {
                "schema_version": 1,
                "dataset_id": "free-agent-signals",
                "generated_at": "2026-08-10T08:00:00Z",
                "input_fingerprint": "b" * 64,
                "source": {
                    "dataset_id": "player-signals",
                    "path": "fantasy-management/generated/operations/player-signals.json",
                    "input_fingerprint": player_fingerprint if fingerprint_match else "c" * 64,
                },
                "players": [free],
                "quality": {"status": "ok", "source_quality_status": "ok", "source_issue_count": 0},
            },
        )
        config_path = root / "fantasy-management/automation/kicker-streaming-input-materialization.json"
        self.write_json(
            root,
            "fantasy-management/automation/kicker-streaming-input-materialization.json",
            {
                "schema_version": 1,
                "materialization_id": "test-kicker-streaming-inputs",
                "managed_team": {"team_id": 1},
                "sources": {
                    "league": "public/data/League.json",
                    "player_signals": "fantasy-management/generated/operations/player-signals.json",
                    "free_agent_signals": "fantasy-management/generated/operations/free-agent-signals.json",
                },
                "population": {
                    "position": "K",
                    "held_ownership_status": "mighty_giants",
                    "free_agent_ownership_status": "fantasy_free_agent",
                },
                "output": {
                    "kicker_streaming_inputs": "fantasy-management/generated/operations/kicker-streaming-inputs.json"
                },
            },
        )
        return config_path

    def test_selects_held_and_free_agent_kickers_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = MODULE.build(root, self.prepare_root(root))

            self.assertEqual(result["population"]["held_count"], 1)
            self.assertEqual(result["population"]["free_agent_count"], 1)
            self.assertEqual(result["population"]["candidate_count"], 2)
            self.assertEqual(
                [(item["player_id"], item["availability"]) for item in result["candidates"]],
                [("1", "held"), ("2", "free_agent")],
            )
            self.assertNotIn("recommendation", result)

    def test_reconciles_cbs_and_fftoday_as_bounds_without_overwriting_provider_points(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = MODULE.build(root, self.prepare_root(root))
            candidate = result["candidates"][0]

            cbs = candidate["league_scoring_projection"]["cbs_sports"]
            self.assertEqual(cbs["status"], "bounded")
            self.assertEqual(cbs["points_min"], 58)
            self.assertEqual(cbs["points_max"], 60)
            self.assertEqual(cbs["provider_projected_fantasy_points"], 155)

            fftoday = candidate["league_scoring_projection"]["fftoday"]
            self.assertEqual(fftoday["status"], "bounded")
            self.assertEqual(fftoday["points_min"], 128)
            self.assertEqual(fftoday["points_max"], 218)
            self.assertEqual(fftoday["provider_projected_fantasy_points"], 150)

    def test_rejects_free_agent_dataset_from_different_player_signal_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self.prepare_root(root, fingerprint_match=False)
            with self.assertRaisesRegex(MODULE.KickerStreamingInputError, "fingerprint"):
                MODULE.build(root, config_path)

    def test_current_repository_inputs_build_and_validate(self) -> None:
        root = SCRIPT_PATH.parents[3]
        config_path = root / "fantasy-management/automation/kicker-streaming-input-materialization.json"
        schema_path = root / "fantasy-management/_ai/schemas/kicker-streaming-inputs.schema.json"

        result = MODULE.build(root, config_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)

        self.assertGreater(result["population"]["candidate_count"], 1)
        self.assertGreater(result["population"]["free_agent_count"], 0)
        self.assertEqual(result["league"]["kicker_scoring"]["fgm_40_49"], 4)
        self.assertEqual(result["league"]["kicker_scoring"]["fgm_50_59"], 5)
        self.assertEqual(result["league"]["kicker_scoring"]["fgm_60p"], 6)
        self.assertEqual(result["league"]["kicker_scoring"]["xpm"], 1)
        self.assertEqual(result["league"]["kicker_scoring"]["xpmiss"], -1)
        self.assertTrue(all(item["availability"] in {"held", "free_agent"} for item in result["candidates"]))
        self.assertTrue(
            any(
                item["league_scoring_projection"]["cbs_sports"]["status"] in {"exact", "bounded"}
                for item in result["candidates"]
            )
        )
        self.assertTrue(
            any(
                item["league_scoring_projection"]["fftoday"]["status"] in {"exact", "bounded"}
                for item in result["candidates"]
            )
        )


if __name__ == "__main__":
    unittest.main()
