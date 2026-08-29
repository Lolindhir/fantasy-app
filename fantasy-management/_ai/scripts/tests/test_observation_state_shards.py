import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_observation_state_shards.py"
spec = importlib.util.spec_from_file_location("observation_shards", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def profile(state_hash="a" * 64):
    return {
        "status": "baseline",
        "last_checked_at": "2026-08-30T00:00:00Z",
        "state_hash": state_hash,
        "material_state": {"value": 1},
        "confidence": "high",
        "source_fingerprints": ["source:a"],
        "last_material_change_at": None,
        "last_error": None,
    }


def target(fingerprint="player:sleeper_id:1", value=1):
    p = profile()
    p["material_state"] = {"value": value}
    return {
        "entity_fingerprint": fingerprint,
        "target_set_ids": ["watch"],
        "last_checked_at": "2026-08-30T00:00:00Z",
        "status": "active",
        "observations": {"injury-status": p},
    }


def base():
    return {
        "job_id": "entity-observation",
        "revision": 17,
        "job_state": {"target_sets": {}, "targets": {"player-1": target()}},
    }


class ObservationShardTests(unittest.TestCase):
    def test_base_only_is_lossless(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.json"
            write_json(base_path, base())
            merged = module.effective_state(base_path, root / "shards")
            self.assertEqual(merged, base())

    def test_shard_replaces_one_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.json"
            shard_dir = root / "shards"
            write_json(base_path, base())
            replacement = target(value=2)
            write_json(shard_dir / "player-1.json", {
                "schema_version": 1,
                "target_id": "player-1",
                "base_state_revision": 17,
                "write_id": "approved:player-1:2026-08-30",
                "updated_at": "2026-08-30T00:00:00Z",
                "target": replacement,
            })
            merged = module.effective_state(base_path, shard_dir)
            self.assertEqual(merged["job_state"]["targets"]["player-1"], replacement)

    def test_identity_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.json"
            shard_dir = root / "shards"
            write_json(base_path, base())
            write_json(shard_dir / "player-1.json", {
                "schema_version": 1,
                "target_id": "player-1",
                "base_state_revision": 17,
                "write_id": "approved:bad",
                "updated_at": "2026-08-30T00:00:00Z",
                "target": target(fingerprint="player:sleeper_id:2"),
            })
            with self.assertRaises(module.ValidationError):
                module.effective_state(base_path, shard_dir)

    def test_filename_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.json"
            shard_dir = root / "shards"
            write_json(base_path, base())
            write_json(shard_dir / "wrong.json", {
                "schema_version": 1,
                "target_id": "player-1",
                "base_state_revision": 17,
                "write_id": "approved:mismatch",
                "updated_at": "2026-08-30T00:00:00Z",
                "target": target(),
            })
            with self.assertRaises(module.ValidationError):
                module.effective_state(base_path, shard_dir)


if __name__ == "__main__":
    unittest.main()
