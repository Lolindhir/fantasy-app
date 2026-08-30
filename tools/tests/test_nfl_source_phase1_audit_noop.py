import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.materialize import _persisted_phase1_audit


class Phase1AuditNoopTests(unittest.TestCase):
    def test_persisted_audit_ignores_frozen_partition_execution_count(self):
        semantic = {
            "activeDatasetIDs": ["nflverse.schedules"],
            "canonicalOutputFileCount": 59,
            "schedules": {"gameCount": 7548},
        }
        first_pass = {**semantic, "frozenPartitionsPreserved": 0}
        second_pass = {**semantic, "frozenPartitionsPreserved": 54}

        self.assertEqual(
            _persisted_phase1_audit(first_pass),
            _persisted_phase1_audit(second_pass),
        )
        self.assertNotIn(
            "frozenPartitionsPreserved",
            _persisted_phase1_audit(second_pass),
        )
        self.assertEqual(54, second_pass["frozenPartitionsPreserved"])


if __name__ == "__main__":
    unittest.main()
