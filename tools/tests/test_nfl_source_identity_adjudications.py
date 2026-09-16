from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import PlayerMappingResolver  # noqa: E402
from nfl_source_data_lib.identity_adjudications import (  # noqa: E402
    apply_identity_adjudications,
    load_identity_adjudication_claims,
)
from nfl_source_data_lib.provider_mappings import build_provider_mapping_payload  # noqa: E402


class HistoricalIdentityAdjudicationTests(unittest.TestCase):
    @staticmethod
    def _entry(
        *,
        adjudication_id: str = "test-2024-sleeper-1",
        season: int = 2024,
        external_id: str = "1",
        canonical_id: str = "NFLP-a",
    ) -> dict[str, Any]:
        return {
            "AdjudicationID": adjudication_id,
            "Season": season,
            "Provider": "Sleeper",
            "ExternalID": external_id,
            "CanonicalPlayerID": canonical_id,
            "SubjectLabel": "Example Player",
            "Status": "confirmed",
            "DecisionAuthority": "repository-owner-approved-review",
            "DecisionDate": "2026-09-16",
            "Rationale": "Explicit human review resolves an otherwise fail-closed historical identity gap.",
            "Evidence": [
                {
                    "Source": "test-fixture",
                    "Summary": "Independent review evidence for the exact historical provider token.",
                }
            ],
        }

    @classmethod
    def _write_source(cls, root: Path, entries: list[dict[str, Any]]) -> None:
        path = root / "source-data/nfl/identities/historical-identity-adjudications.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"SchemaVersion": 1, "Adjudications": entries}, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _resolver(payload: dict[str, Any]) -> PlayerMappingResolver:
        mappings: dict[tuple[str, str], list[dict[str, Any]]] = {}
        conflicts: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in payload.get("Mappings", []) or []:
            key = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
            mappings.setdefault(key, []).append(item)
        for item in payload.get("Conflicts", []) or []:
            key = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
            conflicts.setdefault(key, []).append(item)
        return PlayerMappingResolver(mappings=mappings, conflicts=conflicts)

    def test_confirmed_source_emits_one_season_local_claim_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._entry()])

            claims = load_identity_adjudication_claims(root, {"NFLP-a"})

            self.assertEqual(
                [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "1",
                        "CanonicalPlayerID": "NFLP-a",
                        "ObservedSeason": 2024,
                        "Sources": ["manual.identity-adjudication:test-2024-sleeper-1"],
                    }
                ],
                claims,
            )

    def test_source_rejects_unknown_canonical_identity_and_duplicate_token_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._entry(canonical_id="NFLP-missing")])
            with self.assertRaisesRegex(ValueError, "existing canonical player"):
                load_identity_adjudication_claims(root, {"NFLP-a"})

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(
                root,
                [
                    self._entry(adjudication_id="first"),
                    self._entry(adjudication_id="second", canonical_id="NFLP-b"),
                ],
            )
            with self.assertRaisesRegex(ValueError, "same provider token and season"):
                load_identity_adjudication_claims(root, {"NFLP-a", "NFLP-b"})

    def test_confirmation_fills_only_observed_season_and_joins_contiguous_same_owner(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "5133",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2021,
                    "LastObservedSeason": 2023,
                    "Sources": ["older"],
                },
                {
                    "Provider": "Sleeper",
                    "ExternalID": "5133",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2025,
                    "LastObservedSeason": 2026,
                    "Sources": ["newer"],
                },
            ],
            "Conflicts": [],
        }
        claim = {
            "Provider": "Sleeper",
            "ExternalID": "5133",
            "CanonicalPlayerID": "NFLP-a",
            "ObservedSeason": 2024,
            "Sources": ["manual.identity-adjudication:conklin"],
        }

        result = apply_identity_adjudications(payload, [claim])

        self.assertEqual(1, len(result["Mappings"]))
        mapping = result["Mappings"][0]
        self.assertEqual(2021, mapping["FirstObservedSeason"])
        self.assertEqual(2026, mapping["LastObservedSeason"])
        self.assertIn("manual.identity-adjudication:conklin", mapping["Sources"])

    def test_confirmation_does_not_bridge_an_unobserved_gap_or_override_conflict(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2021,
                    "LastObservedSeason": 2022,
                    "Sources": ["old"],
                },
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2025,
                    "LastObservedSeason": 2026,
                    "Sources": ["new"],
                },
            ],
            "Conflicts": [],
        }
        claim = {
            "Provider": "Sleeper",
            "ExternalID": "1",
            "CanonicalPlayerID": "NFLP-a",
            "ObservedSeason": 2024,
            "Sources": ["manual.identity-adjudication:test"],
        }
        result = apply_identity_adjudications(payload, [claim])
        spans = [
            (item["FirstObservedSeason"], item["LastObservedSeason"])
            for item in result["Mappings"]
        ]
        self.assertEqual([(2021, 2022), (2024, 2026)], spans)

        conflicting = {
            **payload,
            "Conflicts": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1",
                    "CanonicalPlayerIDs": ["NFLP-a", "NFLP-b"],
                    "FirstObservedSeason": 2024,
                    "LastObservedSeason": 2024,
                    "Status": "ambiguous",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "cannot override an active provider conflict"):
            apply_identity_adjudications(conflicting, [claim])

    def test_provider_mapping_build_applies_versioned_adjudication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping_path = root / "source-data/nfl/identities/provider-mappings.json"
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
            mapping_path.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 2,
                        "TemporalResolution": "season",
                        "Mappings": [
                            {
                                "Provider": "Sleeper",
                                "ExternalID": "11539",
                                "CanonicalPlayerID": "NFLP-a",
                                "FirstObservedSeason": 2025,
                                "LastObservedSeason": 2026,
                                "Sources": ["existing"],
                            }
                        ],
                        "Conflicts": [],
                    }
                ),
                encoding="utf-8",
            )
            self._write_source(
                root,
                [self._entry(external_id="11539", canonical_id="NFLP-a")],
            )

            result = build_provider_mapping_payload(
                root,
                [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "11539",
                        "CanonicalPlayerID": "NFLP-a",
                        "Sources": ["current"],
                    }
                ],
                [],
                2026,
            )

            resolver = self._resolver(result)
            self.assertEqual("NFLP-a", resolver.resolve("Sleeper", "11539", 2024))
            self.assertEqual("NFLP-a", resolver.resolve("Sleeper", "11539", 2026))
            mapping = next(
                item
                for item in result["Mappings"]
                if item["Provider"] == "Sleeper" and item["ExternalID"] == "11539"
            )
            self.assertEqual(2024, mapping["FirstObservedSeason"])
            self.assertIn(
                "manual.identity-adjudication:test-2024-sleeper-1",
                mapping["Sources"],
            )

    def test_repository_adjudications_resolve_bates_and_conklin_in_2024(self) -> None:
        mapping_path = ROOT / "source-data/nfl/identities/provider-mappings.json"
        payload = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
        known_canonical_ids = {
            str(item.get("CanonicalPlayerID") or "")
            for item in payload.get("Mappings", [])
            if str(item.get("CanonicalPlayerID") or "")
        }
        claims = load_identity_adjudication_claims(ROOT, known_canonical_ids)
        result = apply_identity_adjudications(payload, claims)
        resolver = self._resolver(result)

        self.assertEqual(
            "NFLP-5252cab09debe77a2d9a",
            resolver.resolve("Sleeper", "11539", 2024),
        )
        self.assertEqual(
            "NFLP-e63b49e13fe976be3c12",
            resolver.resolve("Sleeper", "5133", 2024),
        )


if __name__ == "__main__":
    unittest.main()
