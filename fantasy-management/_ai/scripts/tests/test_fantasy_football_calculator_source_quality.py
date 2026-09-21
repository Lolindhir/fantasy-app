from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "fantasy_football_calculator_source_quality.py"
)
spec = importlib.util.spec_from_file_location("ffc_source_quality", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FantasyFootballCalculatorSourceQualityTests(unittest.TestCase):
    @staticmethod
    def contract():
        return {
            "datasets": {
                "redraft-ppr-8-team": {
                    "minimum_usable_rows": 50,
                    "expected_minimum_rows": 80,
                    "phase_overrides": {
                        "regular_season": {"expected_minimum_rows": 50}
                    },
                }
            }
        }

    def test_pre_regular_72_rows_are_reduced_but_usable(self):
        result = module.evaluate_dataset_coverage(
            self.contract(),
            dataset_id="redraft-ppr-8-team",
            phase="pre_regular_season",
            observed_rows=72,
        )
        self.assertEqual("reduced_coverage", result["coverage_status"])
        self.assertTrue(result["publishable"])
        self.assertEqual(80, result["expected_minimum_rows"])

    def test_regular_season_43_rows_are_insufficient(self):
        result = module.evaluate_dataset_coverage(
            self.contract(),
            dataset_id="redraft-ppr-8-team",
            phase="regular_season",
            observed_rows=43,
        )
        self.assertEqual("insufficient_coverage", result["coverage_status"])
        self.assertFalse(result["publishable"])
        self.assertEqual(50, result["minimum_usable_rows"])
        self.assertEqual(50, result["expected_minimum_rows"])

    def test_regular_season_50_rows_are_usable(self):
        result = module.evaluate_dataset_coverage(
            self.contract(),
            dataset_id="redraft-ppr-8-team",
            phase="regular_season",
            observed_rows=50,
        )
        self.assertEqual("usable", result["coverage_status"])
        self.assertTrue(result["publishable"])

    def test_invalid_threshold_contract_fails_closed(self):
        contract = self.contract()
        contract["datasets"]["redraft-ppr-8-team"]["minimum_usable_rows"] = 90
        with self.assertRaises(module.FantasyFootballCalculatorQualityError):
            module.evaluate_dataset_coverage(
                contract,
                dataset_id="redraft-ppr-8-team",
                phase="pre_regular_season",
                observed_rows=100,
            )


if __name__ == "__main__":
    unittest.main()
