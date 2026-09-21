from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fantasy_football_calculator_quality import (
    FfcQualityPolicyError,
    evaluate_dataset_coverage,
    load_quality_policy,
)


class FfcQualityPolicyTests(unittest.TestCase):
    def policy(self):
        return {
            "schema_version": 1,
            "source_id": "fantasy-football-calculator",
            "season_context_id": "nfl-regular-season-context",
            "datasets": {
                "redraft-ppr-8-team": {
                    "phases": {
                        "pre_regular_season": {
                            "active": True,
                            "expected_minimum_rows": 80,
                            "minimum_usable_rows": 50,
                        },
                        "regular_season": {
                            "active": True,
                            "expected_minimum_rows": 50,
                            "minimum_usable_rows": 50,
                        },
                        "post_regular_season": {
                            "active": False,
                            "expected_minimum_rows": 0,
                            "minimum_usable_rows": 0,
                        },
                    }
                }
            },
        }

    def test_preseason_reduced_coverage_remains_usable(self):
        result = evaluate_dataset_coverage(
            self.policy(),
            dataset_id="redraft-ppr-8-team",
            phase="pre_regular_season",
            row_count=72,
        )
        self.assertEqual("reduced_coverage", result["status"])
        self.assertTrue(result["usable"])

    def test_regular_season_43_rows_is_insufficient_without_redefining_minimum(self):
        result = evaluate_dataset_coverage(
            self.policy(),
            dataset_id="redraft-ppr-8-team",
            phase="regular_season",
            row_count=43,
        )
        self.assertEqual("insufficient_coverage", result["status"])
        self.assertFalse(result["usable"])
        self.assertEqual(50, result["minimum_usable_rows"])

    def test_post_regular_source_is_inactive(self):
        result = evaluate_dataset_coverage(
            self.policy(),
            dataset_id="redraft-ppr-8-team",
            phase="post_regular_season",
            row_count=120,
        )
        self.assertEqual("inactive_for_phase", result["status"])
        self.assertFalse(result["usable"])

    def test_policy_validation_rejects_expected_below_minimum(self):
        value = self.policy()
        value["datasets"]["redraft-ppr-8-team"]["phases"]["regular_season"]["expected_minimum_rows"] = 40
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(FfcQualityPolicyError, "invalid row thresholds"):
                load_quality_policy(path)


if __name__ == "__main__":
    unittest.main()
