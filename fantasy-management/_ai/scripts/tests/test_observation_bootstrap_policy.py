from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


class ObservationBootstrapPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[4]
        self.policy_path = (
            self.root
            / "fantasy-management/automation/bootstrap/entity-observation-bootstrap.json"
        )
        self.policy_schema_path = (
            self.root
            / "fantasy-management/_ai/schemas/automation-bootstrap-policy.schema.json"
        )
        self.batch_schema_path = (
            self.root
            / "fantasy-management/_ai/schemas/automation-observation-state-batch.schema.json"
        )

    @staticmethod
    def load_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_bootstrap_schemas_are_valid(self) -> None:
        Draft202012Validator.check_schema(self.load_json(self.policy_schema_path))
        Draft202012Validator.check_schema(self.load_json(self.batch_schema_path))

    def test_repository_bootstrap_policy_is_valid(self) -> None:
        policy = self.load_json(self.policy_path)
        schema = self.load_json(self.policy_schema_path)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(policy),
            key=lambda error: list(error.path),
        )
        self.assertEqual([], [error.message for error in errors])

    def test_runtime_and_publication_contracts_are_safe(self) -> None:
        policy = self.load_json(self.policy_path)
        runtime = policy["runtime_budget"]
        self.assertLess(runtime["soft_minutes"], runtime["hard_minutes"])

        publication = policy["checkpoint_publication"]
        required_paths = (
            "state_batch_schema",
            "state_batch_helper",
            "state_schema",
            "cross_file_validator",
            "publication_workflow",
        )
        for key in required_paths:
            self.assertFalse(Path(publication[key]).is_absolute(), key)

        always_local = ("state_batch_schema", "state_batch_helper")
        for key in always_local:
            self.assertTrue((self.root / publication[key]).is_file(), key)

        if (self.root / "AGENTS.md").is_file():
            for key in required_paths:
                self.assertTrue((self.root / publication[key]).is_file(), key)

        self.assertTrue(publication["require_complete_replacement_state"])
        self.assertTrue(publication["require_parent_sha_match"])
        self.assertTrue(publication["require_state_blob_sha_match"])

    def test_all_observation_profiles_have_a_bootstrap_phase(self) -> None:
        policy = self.load_json(self.policy_path)
        configured_profiles = {
            profile
            for phase in policy["phases"]
            for profile in phase["profiles"]
        }
        self.assertEqual(
            {
                "injury-status",
                "market-movement",
                "redraft-adp-movement",
                "role-opportunity",
            },
            configured_profiles,
        )


if __name__ == "__main__":
    unittest.main()
