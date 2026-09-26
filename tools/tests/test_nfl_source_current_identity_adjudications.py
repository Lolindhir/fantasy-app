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

from nfl_source_data_lib.current_identity_adjudications import (  # noqa: E402
    load_current_identity_adjudications,
    validate_current_identity_adjudications_against_state,
)


class CurrentIdentityAdjudicationTests(unittest.TestCase):
    @staticmethod
    def _entry(
        *,
        adjudication_id: str = "2026-sleeper-14071-grant-finley",
        season: int = 2026,
        target_id: str = "NFLP-target",
        source_id: str = "NFLP-provisional",
        assignments: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return {
            "AdjudicationID": adjudication_id,
            "Season": season,
            "ResolutionKind": "current-provider-reassignment",
            "ConflictPolicy": "reject-active-conflict",
            "TargetCanonicalPlayerID": target_id,
            "SourceCanonicalPlayerIDs": [source_id],
            "ProviderAssignments": assignments
            or [
                {"Provider": "Sleeper", "ExternalID": "14071"},
                {"Provider": "Tank01", "ExternalID": "5393270"},
            ],
            "SubjectLabel": "Example Player",
            "Status": "confirmed",
            "DecisionAuthority": "repository-owner-approved-review",
            "DecisionDate": "2026-09-26",
            "Rationale": "Explicit current-season review confirms the bounded provider reassignment.",
            "Evidence": [
                {
                    "Source": "test-fixture",
                    "Summary": "Independent evidence for the exact provider reassignment.",
                }
            ],
        }

    @classmethod
    def _write_source(cls, root: Path, entries: list[dict[str, Any]]) -> None:
        path = root / "source-data/nfl/identities/current-identity-adjudications.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"SchemaVersion": 1, "Adjudications": entries}, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_confirmed_decision_is_bounded_to_exact_observation_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._entry()])

            current = load_current_identity_adjudications(
                root,
                {"NFLP-target", "NFLP-provisional"},
                2026,
            )
            expired = load_current_identity_adjudications(
                root,
                {"NFLP-target", "NFLP-provisional"},
                2027,
            )

            self.assertEqual(1, len(current))
            self.assertEqual([], expired)
            self.assertEqual("NFLP-target", current[0]["TargetCanonicalPlayerID"])
            self.assertEqual(
                "manual.current-identity-adjudication:2026-sleeper-14071-grant-finley",
                current[0]["Provenance"],
            )

    def test_source_rejects_unknown_ids_unconfirmed_rows_and_duplicate_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._entry(target_id="NFLP-missing")])
            with self.assertRaisesRegex(ValueError, "existing canonical player"):
                load_current_identity_adjudications(
                    root,
                    {"NFLP-target", "NFLP-provisional"},
                    2026,
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self._entry()
            row["Status"] = "proposed"
            self._write_source(root, [row])
            with self.assertRaisesRegex(ValueError, "Status must be 'confirmed'"):
                load_current_identity_adjudications(
                    root,
                    {"NFLP-target", "NFLP-provisional"},
                    2026,
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(
                root,
                [
                    self._entry(adjudication_id="first"),
                    self._entry(adjudication_id="second", target_id="NFLP-other"),
                ],
            )
            with self.assertRaisesRegex(ValueError, "same provider token and season"):
                load_current_identity_adjudications(
                    root,
                    {"NFLP-target", "NFLP-other", "NFLP-provisional"},
                    2026,
                )

    def test_state_guard_allows_only_declared_provisional_owner(self) -> None:
        decision = {
            "AdjudicationID": "test",
            "Season": 2026,
            "TargetCanonicalPlayerID": "NFLP-target",
            "SourceCanonicalPlayerIDs": ["NFLP-provisional"],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "14071"}],
            "Provenance": "manual.current-identity-adjudication:test",
        }
        canonical = [
            {
                "CanonicalPlayerID": "NFLP-target",
                "IDs": {"GSIS": "00-0041585"},
                "IDAliases": {},
            },
            {
                "CanonicalPlayerID": "NFLP-provisional",
                "IDs": {"Sleeper": "14071"},
                "IDAliases": {},
            },
        ]

        validate_current_identity_adjudications_against_state(
            [decision],
            canonical,
            [],
            2026,
        )

    def test_state_guard_rejects_different_target_provider_value(self) -> None:
        decision = {
            "AdjudicationID": "sam-like",
            "Season": 2026,
            "TargetCanonicalPlayerID": "NFLP-target",
            "SourceCanonicalPlayerIDs": ["NFLP-provisional"],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "11558"}],
            "Provenance": "manual.current-identity-adjudication:sam-like",
        }
        canonical = [
            {
                "CanonicalPlayerID": "NFLP-target",
                "IDs": {"Sleeper": "11376", "ESPN": "4361994"},
                "IDAliases": {},
            },
            {
                "CanonicalPlayerID": "NFLP-provisional",
                "IDs": {"Sleeper": "11558", "Tank01": "4361994"},
                "IDAliases": {},
            },
        ]

        with self.assertRaisesRegex(ValueError, "already has a different active Sleeper value"):
            validate_current_identity_adjudications_against_state(
                [decision],
                canonical,
                [],
                2026,
            )

    def test_state_guard_rejects_active_conflict_and_undeclared_owner(self) -> None:
        decision = {
            "AdjudicationID": "test",
            "Season": 2026,
            "TargetCanonicalPlayerID": "NFLP-target",
            "SourceCanonicalPlayerIDs": ["NFLP-provisional"],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "14071"}],
            "Provenance": "manual.current-identity-adjudication:test",
        }
        canonical = [
            {"CanonicalPlayerID": "NFLP-target", "IDs": {}, "IDAliases": {}},
            {
                "CanonicalPlayerID": "NFLP-provisional",
                "IDs": {"Sleeper": "14071"},
                "IDAliases": {},
            },
        ]
        conflicts = [
            {
                "Provider": "Sleeper",
                "ExternalID": "14071",
                "CanonicalPlayerIDs": ["NFLP-provisional", "NFLP-other"],
                "FirstObservedSeason": 2026,
                "LastObservedSeason": 2026,
            }
        ]
        with self.assertRaisesRegex(ValueError, "cannot override active provider conflict"):
            validate_current_identity_adjudications_against_state(
                [decision],
                canonical,
                conflicts,
                2026,
            )

        canonical.append(
            {
                "CanonicalPlayerID": "NFLP-other",
                "IDs": {"Sleeper": "14071"},
                "IDAliases": {},
            }
        )
        with self.assertRaisesRegex(ValueError, "undeclared current owners"):
            validate_current_identity_adjudications_against_state(
                [decision],
                canonical,
                [],
                2026,
            )

    def test_repository_source_is_valid_and_currently_empty(self) -> None:
        path = ROOT / "source-data/nfl/identities/current-identity-adjudications.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        known_ids = {
            str(item.get("CanonicalPlayerID") or "")
            for item in json.loads(
                (ROOT / "source-data/nfl/identities/players.json").read_text(
                    encoding="utf-8-sig"
                )
            ).get("Players", [])
            if str(item.get("CanonicalPlayerID") or "")
        }

        self.assertEqual([], payload["Adjudications"])
        self.assertEqual(
            [],
            load_current_identity_adjudications(ROOT, known_ids, 2026),
        )


if __name__ == "__main__":
    unittest.main()
