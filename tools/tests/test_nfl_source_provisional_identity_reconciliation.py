from __future__ import annotations

import unittest

from tools.nfl_source_data_lib.identity_sources import _corroborated_ff_birthdate_correction
from tools.nfl_source_data_lib.provisional_reconciliation import (
    reconcile_provisional_app_mappings,
)


class ProvisionalIdentityReconciliationTests(unittest.TestCase):
    def test_ff_birthdate_correction_requires_three_consistent_strong_anchors(self) -> None:
        ids = {
            "GSIS": "00-1",
            "ESPN": "111",
            "PFR": "TestPl00",
            "PFF": "999",
            "Sleeper": "S1",
        }
        anchors = {
            ("GSIS", "00-1"): {"2001-11-11"},
            ("ESPN", "111"): {"2001-11-11"},
            ("PFR", "TestPl00"): {"2001-11-11"},
            ("PFF", "999"): {"2001-11-11"},
        }
        self.assertEqual(
            "2001-11-11",
            _corroborated_ff_birthdate_correction(ids, "2001-11-01", anchors),
        )

        only_two = dict(anchors)
        only_two.pop(("PFR", "TestPl00"))
        only_two.pop(("PFF", "999"))
        self.assertIsNone(
            _corroborated_ff_birthdate_correction(ids, "2001-11-01", only_two)
        )

        conflicting = dict(anchors)
        conflicting[("PFF", "999")] = {"2002-02-02"}
        self.assertIsNone(
            _corroborated_ff_birthdate_correction(ids, "2001-11-01", conflicting)
        )

    @staticmethod
    def _payload(*, first: int = 2025, last: int = 2026, source: str = "app.Players") -> dict:
        return {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerID": "NFLP-provisional",
                    "FirstObservedSeason": first,
                    "LastObservedSeason": last,
                    "Sources": [source, "app.Players.git.2025@abc"]
                    if source == "app.Players"
                    else [source],
                }
            ],
            "Conflicts": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "S1",
                    "CanonicalPlayerIDs": ["NFLP-durable", "NFLP-provisional"],
                    "FirstObservedSeason": season,
                    "LastObservedSeason": season,
                    "Status": "ambiguous",
                    "Reason": "historical_mapping_overlap",
                }
                for season in range(first, last + 1)
            ],
        }

    @staticmethod
    def _external_claim(season: int) -> dict:
        return {
            "Provider": "Sleeper",
            "ExternalID": "S1",
            "CanonicalPlayerID": "NFLP-durable",
            "ObservedSeason": season,
            "Sources": [f"dynastyprocess.ff-player-ids-history.git.{season}.opening@deadbeef"],
        }

    def test_external_history_replaces_only_provisional_app_mapping_and_is_idempotent(self) -> None:
        payload = self._payload()
        claims = [self._external_claim(2025), self._external_claim(2026)]

        first = reconcile_provisional_app_mappings(payload, claims)
        second = reconcile_provisional_app_mappings(first, claims)

        self.assertEqual(first, second)
        self.assertEqual([], first["Conflicts"])
        self.assertEqual(1, len(first["Mappings"]))
        mapping = first["Mappings"][0]
        self.assertEqual("NFLP-durable", mapping["CanonicalPlayerID"])
        self.assertEqual((2025, 2026), (mapping["FirstObservedSeason"], mapping["LastObservedSeason"]))
        self.assertEqual(2, len(first["HistoricalMappingReconciliations"]))
        self.assertTrue(
            all(
                row["RetiredCanonicalPlayerIDs"] == ["NFLP-provisional"]
                for row in first["HistoricalMappingReconciliations"]
            )
        )

    def test_reconciliation_is_season_local_and_preserves_surrounding_history(self) -> None:
        payload = self._payload(first=2024, last=2026)
        payload["Conflicts"] = [payload["Conflicts"][1]]

        result = reconcile_provisional_app_mappings(payload, [self._external_claim(2025)])
        by_owner = {}
        for row in result["Mappings"]:
            by_owner.setdefault(row["CanonicalPlayerID"], []).append(
                (row["FirstObservedSeason"], row["LastObservedSeason"])
            )

        self.assertEqual([(2025, 2025)], by_owner["NFLP-durable"])
        self.assertEqual([(2024, 2024), (2026, 2026)], by_owner["NFLP-provisional"])
        self.assertEqual([], result["Conflicts"])

    def test_app_only_history_cannot_replace_provisional_mapping(self) -> None:
        payload = self._payload(first=2025, last=2025)
        claim = self._external_claim(2025)
        claim["Sources"] = ["app.PastPlayers.2025"]

        result = reconcile_provisional_app_mappings(payload, [claim])

        self.assertEqual(payload["Mappings"], result["Mappings"])
        self.assertEqual(payload["Conflicts"], result["Conflicts"])
        self.assertEqual([], result["HistoricalMappingReconciliations"])

    def test_non_provisional_competing_mapping_remains_fail_closed(self) -> None:
        payload = self._payload(first=2025, last=2025, source="trusted-provider-history")

        result = reconcile_provisional_app_mappings(payload, [self._external_claim(2025)])

        self.assertEqual(payload["Mappings"], result["Mappings"])
        self.assertEqual(payload["Conflicts"], result["Conflicts"])
        self.assertEqual([], result["HistoricalMappingReconciliations"])


if __name__ == "__main__":
    unittest.main()
