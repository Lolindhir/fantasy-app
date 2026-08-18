from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build_free_agent_movement_events.py"
SPEC = importlib.util.spec_from_file_location("build_free_agent_movement_events", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MovementEventTests(unittest.TestCase):
    def write_json(self, root: Path, relative: str, value: object) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def discovery(self, player_id: str, position: str, priority: str = "medium", *, families=None, replacement="near_rostered_boundary", threshold_kind="percentile_movement", structural=None) -> dict:
        families = families or ["redraft_adp"]
        threshold = {
            "family": families[0],
            "kind": threshold_kind,
            "severity": "medium",
            "window_days": 7,
            "delta": 12,
            "threshold": 10,
        }
        return {
            "player_id": player_id,
            "name": player_id,
            "position": position,
            "nfl_team": "AAA",
            "ownership": {"status": "fantasy_free_agent"},
            "replacement_relevance": {"classification": replacement},
            "movement": {
                "cross_signal_patterns": [],
                "structural_day_over_day": {"changes": structural or []},
            },
            "activity": {},
            "materiality": {
                "research_priority": priority,
                "material_families": families,
                "thresholds_crossed": [threshold],
                "coverage_changes": [],
                "reasons": ["material_movement_threshold"],
                "final_roster_recommendation": None,
            },
        }

    def movement(self, discoveries: list[dict], fingerprint: str) -> dict:
        return {
            "schema_version": 1,
            "dataset_id": "free-agent-movement-signals",
            "generated_at": "2026-08-17T06:30:00Z",
            "input_fingerprint": fingerprint,
            "population": {"positions": ["QB", "RB", "WR", "TE", "K"], "discovery_count": len(discoveries)},
            "discoveries": discoveries,
            "quality": {"status": "ok"},
        }

    def with_metadata(self, movement: dict, *, contract: str, evidence: str, version: int = 1) -> dict:
        movement["materiality_contract"] = {"version": version, "fingerprint": contract * 64}
        movement["evidence"] = {"input_fingerprint": evidence * 64}
        return movement

    def config(self, root: Path) -> Path:
        return self.write_json(root, "config.json", {
            "schema_version": 1,
            "source": {"movement_signals": "movement.json"},
            "output": {"movement_events": "events.json"},
        })

    def test_initial_run_is_silent_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(root, "movement.json", self.movement([self.discovery("fa-k", "K")], "a" * 64))
            result = MODULE.build(root, self.config(root))
            self.assertEqual(result["population"]["baseline_mode"], "initial_baseline")
            self.assertEqual(result["population"]["event_count"], 0)
            self.assertEqual(result["contract_migration"]["status"], "not_applicable")

    def test_unchanged_window_churn_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = self.discovery("fa-wr", "WR")
            previous = self.discovery("fa-wr", "WR")
            current["materiality"]["thresholds_crossed"][0]["window_days"] = 14
            self.write_json(root, "movement.json", self.movement([current], "b" * 64))
            previous_path = self.write_json(root, "previous.json", self.movement([previous], "a" * 64))
            result = MODULE.build(root, self.config(root), previous_path)
            self.assertEqual(result["population"]["event_count"], 0)

    def test_new_changed_structural_and_resolved_events_include_kicker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = [
                self.discovery("changed-wr", "WR", "medium"),
                self.discovery("struct-rb", "RB", "medium"),
                self.discovery("resolved-te", "TE", "high"),
            ]
            changed = self.discovery("changed-wr", "WR", "high", families=["redraft_adp", "season_projection"])
            structural = self.discovery("struct-rb", "RB", "medium", structural=[{
                "family": "role_opportunity", "kind": "depth_chart_order_change", "severity": "medium", "from": 3, "to": 2
            }])
            new_kicker = self.discovery("new-k", "K", "high", families=["redraft_adp", "season_projection"])
            self.write_json(root, "movement.json", self.movement([changed, structural, new_kicker], "b" * 64))
            previous_path = self.write_json(root, "previous.json", self.movement(previous, "a" * 64))
            result = MODULE.build(root, self.config(root), previous_path)
            by_id = {event["player_id"]: event for event in result["events"]}
            self.assertEqual(by_id["changed-wr"]["event_type"], "changed")
            self.assertEqual(by_id["struct-rb"]["event_type"], "structural_change")
            self.assertEqual(by_id["new-k"]["event_type"], "new")
            self.assertEqual(by_id["resolved-te"]["event_type"], "resolved")
            self.assertEqual(by_id["new-k"]["position"], "K")
            self.assertEqual(by_id["new-k"]["event_priority"], "high")

    def test_same_contract_with_changed_evidence_keeps_normal_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "medium")], "a" * 64),
                contract="1",
                evidence="a",
            )
            current = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "high")], "b" * 64),
                contract="1",
                evidence="b",
            )
            self.write_json(root, "movement.json", current)
            previous_path = self.write_json(root, "previous.json", previous)
            result = MODULE.build(root, self.config(root), previous_path)
            self.assertEqual(result["population"]["baseline_mode"], "comparison")
            self.assertEqual(result["contract_migration"]["status"], "not_needed")
            self.assertEqual(result["population"]["event_count"], 1)
            self.assertEqual(result["events"][0]["event_type"], "changed")

    def test_changed_contract_with_identical_evidence_is_silent_rebaseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "medium")], "a" * 64),
                contract="1",
                evidence="a",
            )
            current = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "high")], "b" * 64),
                contract="2",
                evidence="a",
                version=2,
            )
            self.write_json(root, "movement.json", current)
            previous_path = self.write_json(root, "previous.json", previous)
            result = MODULE.build(root, self.config(root), previous_path)
            self.assertEqual(result["population"]["baseline_mode"], "contract_migration")
            self.assertEqual(result["contract_migration"]["status"], "silent_rebaseline")
            self.assertTrue(result["contract_migration"]["contract_changed"])
            self.assertFalse(result["contract_migration"]["evidence_changed"])
            self.assertEqual(result["population"]["event_count"], 0)
            self.assertEqual(result["contract_migration"]["comparison_event_count_before_suppression"], 1)
            self.assertEqual(result["contract_migration"]["suppressed_event_count"], 1)
            self.assertEqual(result["contract_migration"]["suppressed_event_type_counts"], {"changed": 1})

    def test_changed_contract_and_evidence_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "medium")], "a" * 64),
                contract="1",
                evidence="a",
            )
            current = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "high")], "b" * 64),
                contract="2",
                evidence="b",
                version=2,
            )
            self.write_json(root, "movement.json", current)
            previous_path = self.write_json(root, "previous.json", previous)
            result = MODULE.build(root, self.config(root), previous_path)
            self.assertEqual(result["population"]["baseline_mode"], "contract_migration_with_evidence_change")
            self.assertEqual(result["contract_migration"]["status"], "fail_open_evidence_changed")
            self.assertTrue(result["contract_migration"]["contract_changed"])
            self.assertTrue(result["contract_migration"]["evidence_changed"])
            self.assertEqual(result["population"]["event_count"], 1)
            self.assertEqual(result["quality"]["status"], "warning")
            self.assertEqual(result["contract_migration"]["suppressed_event_count"], 0)

    def test_silent_contract_migration_rebases_following_unchanged_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "medium")], "a" * 64),
                contract="1",
                evidence="a",
            )
            migrated = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "high")], "b" * 64),
                contract="2",
                evidence="a",
                version=2,
            )
            self.write_json(root, "movement.json", migrated)
            old_path = self.write_json(root, "old.json", old)
            first = MODULE.build(root, self.config(root), old_path)
            self.assertEqual(first["population"]["baseline_mode"], "contract_migration")
            self.assertEqual(first["population"]["event_count"], 0)

            self.write_json(root, "movement.json", migrated)
            migrated_previous = self.write_json(root, "migrated-previous.json", migrated)
            second = MODULE.build(root, self.config(root), migrated_previous)
            self.assertEqual(second["population"]["baseline_mode"], "comparison")
            self.assertEqual(second["contract_migration"]["status"], "not_needed")
            self.assertEqual(second["population"]["event_count"], 0)

    def test_legacy_previous_state_never_enables_silent_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = self.movement([self.discovery("fa-wr", "WR", "medium")], "a" * 64)
            current = self.with_metadata(
                self.movement([self.discovery("fa-wr", "WR", "high")], "b" * 64),
                contract="2",
                evidence="a",
                version=2,
            )
            self.write_json(root, "movement.json", current)
            previous_path = self.write_json(root, "previous.json", previous)
            result = MODULE.build(root, self.config(root), previous_path)
            self.assertEqual(result["contract_migration"]["status"], "metadata_unavailable")
            self.assertEqual(result["population"]["baseline_mode"], "comparison")
            self.assertEqual(result["population"]["event_count"], 1)

    def test_current_repository_initial_baseline_validates(self) -> None:
        root = SCRIPT_PATH.parents[3]
        result = MODULE.build(root, root / "fantasy-management/automation/free-agent-movement-event-materialization.json")
        schema = json.loads((root / "fantasy-management/_ai/schemas/free-agent-movement-events.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(result)
        self.assertEqual(result["population"]["baseline_mode"], "initial_baseline")
        self.assertEqual(result["population"]["event_count"], 0)
        self.assertEqual(set(result["population"]["positions"]), {"QB", "RB", "WR", "TE", "K"})
        self.assertIsNotNone(result["contract_migration"]["current_materiality_contract_fingerprint"])
        self.assertIsNotNone(result["contract_migration"]["current_evidence_fingerprint"])

    def test_production_workflow_persists_previous_movement_for_event_comparison(self) -> None:
        root = SCRIPT_PATH.parents[3]
        workflow = (root / ".github/workflows/materialize-fantasy-operations-inputs.yml").read_text(encoding="utf-8")
        self.assertIn("free-agent-movement-signals.previous.json", workflow)
        self.assertIn("build_free_agent_movement_events.py", workflow)
        self.assertIn("free-agent-movement-events.json", workflow)
        self.assertLess(workflow.index("build_free_agent_movement_dataset.py"), workflow.index("build_free_agent_movement_events.py"))


if __name__ == "__main__":
    unittest.main()
