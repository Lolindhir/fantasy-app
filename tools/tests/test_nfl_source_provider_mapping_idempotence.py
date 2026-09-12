from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.nfl_source_data_lib.common import write_json_if_changed
from tools.nfl_source_data_lib.mapping_history import extend_provider_mapping_payload
from tools.nfl_source_data_lib.provider_mappings import build_provider_mapping_payload


class ProviderMappingIdempotenceTests(unittest.TestCase):
    @staticmethod
    def _write_mapping_payload(root: Path, mappings: list[dict[str, object]]) -> Path:
        path = root / "source-data/nfl/identities/provider-mappings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "TemporalResolution": "season",
                    "Mappings": mappings,
                    "Conflicts": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_historical_mapping_replay_does_not_extend_into_current_owner_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider_ids = {"Sleeper": "S1", "Tank01": "T1"}
            path = self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": provider,
                        "ExternalID": external_id,
                        "CanonicalPlayerID": "NFLP-persisted",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["app.Players"],
                    }
                    for provider, external_id in provider_ids.items()
                ],
            )
            current_claims = [
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerID": "NFLP-current",
                    "Sources": ["app.Players"],
                }
                for provider, external_id in provider_ids.items()
            ]
            historical_claims = [
                {**claim, "ObservedSeason": 2025, "Sources": ["app.PastPlayers.2025"]}
                for claim in current_claims
            ]

            def replay() -> dict[str, object]:
                return extend_provider_mapping_payload(
                    build_provider_mapping_payload(root, current_claims, [], 2026),
                    historical_claims,
                    [],
                )

            first = replay()
            self.assertTrue(write_json_if_changed(path, first))
            second = replay()
            self.assertEqual(first, second)
            self.assertFalse(write_json_if_changed(path, second))
            self.assertEqual(4, len(second["Mappings"]))
            self.assertEqual(2, len(second["Conflicts"]))
            for row in second["Mappings"]:
                if row["CanonicalPlayerID"] == "NFLP-current":
                    self.assertEqual((2025, 2025), (row["FirstObservedSeason"], row["LastObservedSeason"]))
                    self.assertEqual(["app.PastPlayers.2025"], row["Sources"])
            for conflict in second["Conflicts"]:
                self.assertEqual(["NFLP-current", "NFLP-persisted"], conflict["CanonicalPlayerIDs"])
                self.assertEqual("ambiguous", conflict["Status"])
                self.assertEqual((2026, 2026), (conflict["FirstObservedSeason"], conflict["LastObservedSeason"]))

    def test_exact_mapping_extends_when_other_owner_does_not_overlap_current_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerID": owner,
                        "FirstObservedSeason": season,
                        "LastObservedSeason": season,
                        "Sources": ["historical"],
                    }
                    for owner, season in [("NFLP-old", 2024), ("NFLP-current", 2025)]
                ],
            )
            claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-current",
                    "Sources": ["app.Players"],
                }
            ]

            first = build_provider_mapping_payload(root, claims, [], 2026)
            rows = {row["CanonicalPlayerID"]: row for row in first["Mappings"]}
            self.assertEqual((2024, 2024), (rows["NFLP-old"]["FirstObservedSeason"], rows["NFLP-old"]["LastObservedSeason"]))
            self.assertEqual((2025, 2026), (rows["NFLP-current"]["FirstObservedSeason"], rows["NFLP-current"]["LastObservedSeason"]))
            self.assertEqual(["app.Players", "historical"], rows["NFLP-current"]["Sources"])
            self.assertEqual([], first["Conflicts"])
            self.assertTrue(write_json_if_changed(path, first))
            second = build_provider_mapping_payload(root, claims, [], 2026)
            self.assertEqual(first, second)
            self.assertFalse(write_json_if_changed(path, second))


if __name__ == "__main__":
    unittest.main()
