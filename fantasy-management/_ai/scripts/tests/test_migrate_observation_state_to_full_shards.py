import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_observation_state_to_full_shards import build_candidate, reconstruct_from_full_shards


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def profile(value: str):
    return {
        "status": "baseline",
        "last_checked_at": "2026-08-30T00:00:00Z",
        "state_hash": value,
        "material_state": {"value": value},
        "confidence": "high",
        "source_fingerprints": [f"source:{value}"],
        "last_material_change_at": None,
        "last_error": None,
    }


def target(sleeper_id: str, value: str):
    return {
        "entity_fingerprint": f"player:sleeper_id:{sleeper_id}",
        "target_set_ids": ["managed-roster-health"],
        "last_checked_at": "2026-08-30T00:00:00Z",
        "status": "active",
        "observations": {"injury-status": profile(value)},
    }


class FullShardMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = self.tmp / "entity-observation.json"
        self.legacy_shards = self.tmp / "legacy-shards"
        self.output = self.tmp / "out"
        self.legacy_shards.mkdir()
        self.base_state = {
            "schema_version": 1,
            "job_id": "entity-observation",
            "status": "pending",
            "revision": 17,
            "last_evaluated_at": "2026-08-30T00:00:00Z",
            "last_successful_run": None,
            "last_processed_key": "test",
            "last_input_fingerprints": {},
            "pending": False,
            "last_error": None,
            "last_material_change": None,
            "recent_events": [],
            "job_state": {
                "target_sets": {
                    "managed-roster-health": {
                        "last_resolved_at": "2026-08-30T00:00:00Z",
                        "resolved_target_ids": ["managed-roster-player-1", "managed-roster-player-2"],
                    }
                },
                "targets": {
                    "managed-roster-player-1": target("1", "old-1"),
                    "managed-roster-player-2": target("2", "base-2"),
                },
            },
        }
        write_json(self.base, self.base_state)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_build_candidate_is_lossless_and_preserves_overlay_bytes(self):
        overlay = {
            "schema_version": 1,
            "target_id": "managed-roster-player-1",
            "base_state_revision": 17,
            "write_id": "interactive-approved-baseline:managed-roster-player-1:2026-08-30",
            "updated_at": "2026-08-30T00:00:00Z",
            "target": target("1", "new-1"),
        }
        overlay_path = self.legacy_shards / "managed-roster-player-1.json"
        write_json(overlay_path, overlay)
        original_bytes = overlay_path.read_bytes()

        manifest = build_candidate(self.base, self.legacy_shards, self.output)

        self.assertEqual(manifest["target_count"], 2)
        self.assertEqual(manifest["preserved_existing_shards"], ["managed-roster-player-1"])
        self.assertEqual(manifest["generated_shards"], ["managed-roster-player-2"])
        self.assertEqual(
            (self.output / "entity-observation-targets/managed-roster-player-1.json").read_bytes(),
            original_bytes,
        )
        rebuilt = reconstruct_from_full_shards(
            self.output / "entity-observation-index.json",
            self.output / "entity-observation-targets",
        )
        expected = json.loads(self.base.read_text(encoding="utf-8"))
        expected["job_state"]["targets"]["managed-roster-player-1"] = overlay["target"]
        self.assertEqual(rebuilt, expected)
        self.assertNotIn("targets", json.loads((self.output / "entity-observation-index.json").read_text())["job_state"])

    def test_generated_shard_uses_migration_write_id(self):
        manifest = build_candidate(self.base, self.legacy_shards, self.output)
        shard = json.loads(
            (self.output / "entity-observation-targets/managed-roster-player-2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(shard["base_state_revision"], 17)
        self.assertEqual(shard["write_id"], "migration:full-shard:revision-17:managed-roster-player-2")
        self.assertEqual(shard["target"], self.base_state["job_state"]["targets"]["managed-roster-player-2"])
        self.assertEqual(manifest["generated_shards"], ["managed-roster-player-1", "managed-roster-player-2"])

    def test_existing_overlay_is_used_as_effective_target(self):
        overlay = {
            "schema_version": 1,
            "target_id": "managed-roster-player-1",
            "base_state_revision": 17,
            "write_id": "approved-newer-state",
            "updated_at": "2026-08-30T00:00:00Z",
            "target": target("1", "different"),
        }
        write_json(self.legacy_shards / "managed-roster-player-1.json", overlay)
        manifest = build_candidate(self.base, self.legacy_shards, self.output)
        self.assertEqual(manifest["preserved_existing_shards"], ["managed-roster-player-1"])
        rebuilt = reconstruct_from_full_shards(
            self.output / "entity-observation-index.json",
            self.output / "entity-observation-targets",
        )
        self.assertEqual(rebuilt["job_state"]["targets"]["managed-roster-player-1"], overlay["target"])


if __name__ == "__main__":
    unittest.main()
