from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from apply_observation_state_batch import (  # noqa: E402
    StateBatchError,
    apply_checkpoint,
    material_state_hash,
)


class ObservationStateBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = {
            "schema_version": 1,
            "job_id": "entity-observation",
            "status": "pending",
            "revision": 4,
            "last_evaluated_at": "2026-08-04T07:01:12+02:00",
            "last_successful_run": "2026-08-04T07:01:12+02:00",
            "last_processed_key": "old-checkpoint",
            "last_input_fingerprints": {"old": "fingerprint"},
            "pending": True,
            "last_error": None,
            "last_material_change": None,
            "recent_events": [],
            "job_state": {
                "target_sets": {},
                "targets": {
                    "existing-player": {
                        "entity_fingerprint": "player:sleeper_id:1",
                        "target_set_ids": ["managed-roster-health"],
                        "last_checked_at": "2026-08-04T07:01:12+02:00",
                        "status": "active",
                        "observations": {
                            "market-movement": {
                                "status": "baseline",
                                "last_checked_at": "2026-08-04T07:01:12+02:00",
                                "state_hash": material_state_hash({"value": 10}),
                                "material_state": {"value": 10},
                                "confidence": "high",
                                "source_fingerprints": ["old-source"],
                                "last_material_change_at": None,
                                "last_error": None,
                            }
                        },
                    }
                },
            },
        }
        self.checkpoint = {
            "schema_version": 1,
            "job_id": "entity-observation",
            "checkpoint_id": "bootstrap:market:2026-08-05",
            "mode": "bootstrap",
            "evaluated_at": "2026-08-05T22:00:00+02:00",
            "expected_revision": 4,
            "expected_parent_sha": "a" * 40,
            "expected_state_blob_sha": "b" * 40,
            "status_after": "pending",
            "pending_after": True,
            "input_fingerprints": {"market": "new-fingerprint"},
            "pair_results": [
                {
                    "target_id": "new-player",
                    "entity_fingerprint": "player:sleeper_id:2",
                    "target_set_ids": ["managed-roster-health"],
                    "expected_profile_ids": [
                        "injury-status",
                        "market-movement",
                        "redraft-adp-movement",
                        "role-opportunity",
                    ],
                    "profile_id": "market-movement",
                    "outcome": "baseline",
                    "material_state": {"tier": "10", "value": 1234},
                    "confidence": "high",
                    "source_fingerprints": ["source-b", "source-a"],
                }
            ],
            "recent_event": {
                "at": "2026-08-05T22:00:00+02:00",
                "type": "pending",
                "severity": "info",
                "summary": "Markt-Bootstrap gespeichert.",
            },
        }

    def test_hash_is_independent_of_object_key_order(self) -> None:
        self.assertEqual(
            material_state_hash({"b": 2, "a": {"y": 2, "x": 1}}),
            material_state_hash({"a": {"x": 1, "y": 2}, "b": 2}),
        )

    def test_checkpoint_adds_baseline_and_preserves_untouched_state(self) -> None:
        original_existing = copy.deepcopy(
            self.state["job_state"]["targets"]["existing-player"]
        )
        replacement = apply_checkpoint(self.state, self.checkpoint)

        self.assertEqual(5, replacement["revision"])
        self.assertEqual(
            original_existing,
            replacement["job_state"]["targets"]["existing-player"],
        )
        profile = replacement["job_state"]["targets"]["new-player"][
            "observations"
        ]["market-movement"]
        self.assertEqual("baseline", profile["status"])
        new_target = replacement["job_state"]["targets"]["new-player"]
        self.assertEqual("pending", new_target["status"])
        self.assertEqual(
            "never_checked",
            new_target["observations"]["injury-status"]["status"],
        )
        self.assertEqual(
            material_state_hash({"tier": "10", "value": 1234}),
            profile["state_hash"],
        )
        self.assertEqual(["source-a", "source-b"], profile["source_fingerprints"])
        self.assertEqual(
            "new-fingerprint",
            replacement["last_input_fingerprints"]["market"],
        )

    def test_stale_revision_is_rejected(self) -> None:
        self.checkpoint["expected_revision"] = 3
        with self.assertRaisesRegex(StateBatchError, "Expected revision 3"):
            apply_checkpoint(self.state, self.checkpoint)

    def test_duplicate_pair_is_rejected(self) -> None:
        self.checkpoint["pair_results"].append(
            copy.deepcopy(self.checkpoint["pair_results"][0])
        )
        with self.assertRaisesRegex(StateBatchError, "duplicate pair"):
            apply_checkpoint(self.state, self.checkpoint)

    def test_pending_result_preserves_previous_good_state(self) -> None:
        self.checkpoint["pair_results"] = [
            {
                "target_id": "existing-player",
                "entity_fingerprint": "player:sleeper_id:1",
                "target_set_ids": ["managed-roster-health"],
                "expected_profile_ids": ["market-movement"],
                "profile_id": "market-movement",
                "outcome": "pending",
                "source_fingerprints": ["retry-source"],
                "last_error": "Provider temporarily unavailable.",
                "preserve_previous_good_state": True,
            }
        ]
        replacement = apply_checkpoint(self.state, self.checkpoint)
        profile = replacement["job_state"]["targets"]["existing-player"][
            "observations"
        ]["market-movement"]

        self.assertEqual("pending", profile["status"])
        self.assertEqual({"value": 10}, profile["material_state"])
        self.assertEqual(material_state_hash({"value": 10}), profile["state_hash"])
        self.assertEqual("Provider temporarily unavailable.", profile["last_error"])

    def test_changed_entity_fingerprint_is_rejected(self) -> None:
        self.checkpoint["pair_results"] = [
            {
                "target_id": "existing-player",
                "entity_fingerprint": "player:sleeper_id:999",
                "target_set_ids": ["managed-roster-health"],
                "expected_profile_ids": ["market-movement"],
                "profile_id": "market-movement",
                "outcome": "unchanged",
                "material_state": {"value": 10},
                "confidence": "high",
                "source_fingerprints": ["source"],
            }
        ]
        with self.assertRaisesRegex(StateBatchError, "Entity fingerprint changed"):
            apply_checkpoint(self.state, self.checkpoint)

    def test_bootstrap_material_change_is_rejected(self) -> None:
        self.checkpoint["pair_results"][0]["outcome"] = "material_change"
        self.checkpoint["pair_results"][0]["last_material_change_at"] = (
            self.checkpoint["evaluated_at"]
        )
        with self.assertRaisesRegex(StateBatchError, "cannot contain material_change"):
            apply_checkpoint(self.state, self.checkpoint)

    def test_pending_status_requires_pending_flag(self) -> None:
        self.checkpoint["pending_after"] = False
        with self.assertRaisesRegex(StateBatchError, "requires pending_after true"):
            apply_checkpoint(self.state, self.checkpoint)


if __name__ == "__main__":
    unittest.main()
