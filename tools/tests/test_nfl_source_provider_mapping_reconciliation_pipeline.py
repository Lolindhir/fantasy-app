from __future__ import annotations

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
    @staticmethod
    def _historical_claim(source: str) -> dict:
        return {
            "Provider": "Sleeper",
            "ExternalID": "S1",
            "CanonicalPlayerID": "NFLP-durable",
            "ObservedSeason": 2026,
            "Sources": [source],
        }

    @staticmethod
    def _replay(root: Path, current_claims: list[dict], historical_claims: list[dict]) -> dict:
        payload = build_provider_mapping_payload(root, current_claims, [], 2026)
        payload = extend_provider_mapping_payload(payload, historical_claims, [])
        return reconcile_provisional_app_mappings(payload, historical_claims)

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
            self.assertTrue(write_json_if_changed(path, persisted))

            current_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-provisional",
                    "Sources": ["app.Players"],
                }
            ]
            historical_claims = [self._historical_claim(historical_source)]

            first = self._replay(root, current_claims, historical_claims)
            self.assertEqual(persisted, first)
            self.assertFalse(write_json_if_changed(path, first))

            second = self._replay(root, current_claims, historical_claims)
            self.assertEqual(first, second)
            self.assertEqual([], second["Conflicts"])
            self.assertEqual(
                ["NFLP-provisional"],
                second["HistoricalMappingReconciliations"][0]["RetiredCanonicalPlayerIDs"],
            )

    def test_reconciliation_converges_when_current_owner_becomes_durable_on_next_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source-data/nfl/identities/provider-mappings.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            historical_source = "dynastyprocess.ff-player-ids-history.git.2026.opening@deadbeef"
            initial = {
                "SchemaVersion": 2,
                "TemporalResolution": "season",
                "Mappings": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerID": "NFLP-provisional",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["app.Players"],
                    }
                ],
                "Conflicts": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerIDs": ["NFLP-durable", "NFLP-provisional"],
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Status": "ambiguous",
                        "Reason": "historical_mapping_overlap",
                    }
                ],
                "HistoricalResolutionConflicts": [],
            }
            self.assertTrue(write_json_if_changed(path, initial))
            historical_claims = [self._historical_claim(historical_source)]

            provisional_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-provisional",
                    "Sources": ["app.Players"],
                }
            ]
            first = self._replay(root, provisional_claims, historical_claims)
            self.assertEqual([], first["Conflicts"])
            self.assertEqual(1, len(first["Mappings"]))
            self.assertEqual("NFLP-durable", first["Mappings"][0]["CanonicalPlayerID"])
            self.assertEqual(
                ["app.Players", historical_source],
                first["Mappings"][0]["Sources"],
            )
            self.assertTrue(write_json_if_changed(path, first))

            # The first identity replay can make the previously ambiguous current
            # token resolve directly to the durable owner. Provider mappings must
            # already contain that current app provenance from reconciliation so
            # this next same-state pass is a semantic no-op.
            durable_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-durable",
                    "Sources": ["app.Players"],
                }
            ]
            second = self._replay(root, durable_claims, historical_claims)

            self.assertEqual(first, second)
            self.assertFalse(write_json_if_changed(path, second))

    def test_reconciliation_preserves_winning_current_claim_source_in_first_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source-data/nfl/identities/provider-mappings.json"
            path.parent.mkdir(parents=True, exist_ok=True)

            historical_source = "dynastyprocess.ff-player-ids-history.git.2026.opening@deadbeef"
            initial = {
                "SchemaVersion": 2,
                "TemporalResolution": "season",
                "Mappings": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerID": "NFLP-provisional",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["app.Players"],
                    }
                ],
                "Conflicts": [],
                "HistoricalResolutionConflicts": [],
            }
            self.assertTrue(write_json_if_changed(path, initial))
            historical_claims = [self._historical_claim(historical_source)]
            durable_current_claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-durable",
                    "Sources": ["nflverse.ff-player-ids"],
                }
            ]

            first = self._replay(root, durable_current_claims, historical_claims)

            self.assertEqual([], first["Conflicts"])
            self.assertEqual(1, len(first["Mappings"]))
            self.assertEqual("NFLP-durable", first["Mappings"][0]["CanonicalPlayerID"])
            self.assertEqual(
                ["app.Players", historical_source, "nflverse.ff-player-ids"],
                first["Mappings"][0]["Sources"],
            )
            self.assertTrue(write_json_if_changed(path, first))

            second = self._replay(root, durable_current_claims, historical_claims)

            self.assertEqual(first, second)
            self.assertFalse(write_json_if_changed(path, second))


if __name__ == "__main__":
    unittest.main()
