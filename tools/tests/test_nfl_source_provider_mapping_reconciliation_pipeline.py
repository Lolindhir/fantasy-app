from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.nfl_source_data_lib.common import write_json_if_changed
from tools.nfl_source_data_lib.mapping_history import extend_provider_mapping_payload
from tools.nfl_source_data_lib.provider_mappings import build_provider_mapping_payload
from tools.nfl_source_data_lib.provisional_reconciliation import (
    reconcile_provisional_app_mappings,
)


class ProviderMappingReconciliationPipelineTests(unittest.TestCase):
    def test_full_mapping_pipeline_preserves_reconciliation_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source-data/nfl/identities/provider-mappings.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            historical_source = "dynastyprocess.ff-player-ids-history.git.2026.opening@deadbeef"
            persisted = {
                "SchemaVersion": 2,
                "TemporalResolution": "season",
                "Mappings": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerID": "NFLP-durable",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": [historical_source],
                    }
                ],
                "Conflicts": [],
                "HistoricalResolutionConflicts": [],
                "HistoricalMappingReconciliations": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "ObservedSeason": 2026,
                        "CanonicalPlayerID": "NFLP-durable",
                        "RetiredCanonicalPlayerIDs": ["NFLP-provisional"],
                        "RetiredSourcesByCanonicalPlayerID": {
                            "NFLP-provisional": ["app.Players"]
                        },
                        "Sources": [historical_source],
                        "Status": "reconciled",
                        "Reason": "corroborated_historical_claim_replaces_provisional_app_mapping",
                    }
                ],
            }
            path.write_text(json.dumps(persisted), encoding="utf-8")

            current_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-provisional",
                    "Sources": ["app.Players"],
                }
            ]
            historical_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-durable",
                    "ObservedSeason": 2026,
                    "Sources": [historical_source],
                }
            ]

            def replay() -> dict:
                payload = build_provider_mapping_payload(root, current_claims, [], 2026)
                payload = extend_provider_mapping_payload(payload, historical_claims, [])
                return reconcile_provisional_app_mappings(payload, historical_claims)

            first = replay()
            self.assertEqual(persisted, first)
            self.assertFalse(write_json_if_changed(path, first))

            second = replay()
            self.assertEqual(first, second)
            self.assertEqual([], second["Conflicts"])
            self.assertEqual(
                ["NFLP-provisional"],
                second["HistoricalMappingReconciliations"][0]["RetiredCanonicalPlayerIDs"],
            )


if __name__ == "__main__":
    unittest.main()
