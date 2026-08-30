import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_observation_state_shards import ValidationError, effective_state


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def profile(value):
    return {
        "status": "baseline", "last_checked_at": "2026-08-30T00:00:00Z",
        "state_hash": value, "material_state": {"value": value}, "confidence": "high",
        "source_fingerprints": [f"source:{value}"], "last_material_change_at": None, "last_error": None,
    }


def target(sleeper_id, value):
    return {
        "entity_fingerprint": f"player:sleeper_id:{sleeper_id}",
        "target_set_ids": ["managed-roster-health"],
        "last_checked_at": "2026-08-30T00:00:00Z", "status": "active",
        "observations": {"injury-status": profile(value)},
    }


class FullShardStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "entity-observation.json"
        self.shards = self.tmp / "entity-observation-targets"
        self.shards.mkdir()
        write_json(self.state, {
            "schema_version": 1, "job_id": "entity-observation", "status": "pending", "revision": 17,
            "last_evaluated_at": None, "last_successful_run": None, "last_processed_key": None,
            "last_input_fingerprints": {}, "pending": False, "last_error": None,
            "last_material_change": None, "recent_events": [],
            "job_state": {"target_sets": {"managed-roster-health": {"resolved_target_ids": []}}, "targets": {}},
        })

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def shard(self, target_id, sleeper_id, value, write_id=None):
        write_json(self.shards / f"{target_id}.json", {
            "schema_version": 1, "target_id": target_id, "base_state_revision": 17,
            "write_id": write_id or f"write:{target_id}", "updated_at": "2026-08-30T00:00:00Z",
            "target": target(sleeper_id, value),
        })

    def test_materializes_targets_from_shards(self):
        self.shard("managed-roster-player-1", "1", "one")
        self.shard("managed-roster-player-2", "2", "two")
        merged = effective_state(self.state, self.shards)
        self.assertEqual(sorted(merged["job_state"]["targets"]), ["managed-roster-player-1", "managed-roster-player-2"])

    def test_embedded_target_payload_fails_closed(self):
        data = json.loads(self.state.read_text())
        data["job_state"]["targets"] = {"managed-roster-player-1": target("1", "one")}
        write_json(self.state, data)
        self.shard("managed-roster-player-1", "1", "one")
        with self.assertRaises(ValidationError):
            effective_state(self.state, self.shards)

    def test_filename_target_mismatch_fails_closed(self):
        write_json(self.shards / "wrong.json", {
            "schema_version": 1, "target_id": "different", "base_state_revision": 17,
            "write_id": "write:different", "updated_at": "2026-08-30T00:00:00Z",
            "target": target("1", "one"),
        })
        with self.assertRaises(ValidationError):
            effective_state(self.state, self.shards)

    def test_duplicate_entity_fingerprint_fails_closed(self):
        self.shard("managed-roster-player-1", "1", "one")
        self.shard("managed-roster-player-other", "1", "two")
        with self.assertRaises(ValidationError):
            effective_state(self.state, self.shards)


if __name__ == "__main__":
    unittest.main()
