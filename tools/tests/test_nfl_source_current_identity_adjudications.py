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

    def test_state_guard_resolves_conflict_between_declared_target_and_source_only(self) -> None:
        decision = {
            "AdjudicationID": "test",
            "Season": 2026,
            "TargetCanonicalPlayerID": "NFLP-target",
            "SourceCanonicalPlayerIDs": ["NFLP-provisional"],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "14071"}],
            "Provenance": "manual.current-identity-adjudication:test",
        }
        canonical = [
            {"CanonicalPlayerID": "NFLP-target", "IDs": {"Sleeper": "14071"}, "IDAliases": {}},
            {"CanonicalPlayerID": "NFLP-provisional", "IDs": {}, "IDAliases": {}},
        ]

        def conflict(members: list[str], first: int = 2026, last: int = 2026) -> dict[str, Any]:
            return {
                "Provider": "Sleeper",
                "ExternalID": "14071",
                "CanonicalPlayerIDs": members,
                "FirstObservedSeason": first,
                "LastObservedSeason": last,
            }

        declared = conflict(["NFLP-provisional", "NFLP-target"])
        statuses = validate_current_identity_adjudications_against_state(
            [decision], canonical, [declared], 2026
        )
        self.assertEqual([{"AdjudicationID": "test", "Status": "active"}], statuses)

        # A third party in any active conflict for the token keeps it fail-closed.
        canonical.append({"CanonicalPlayerID": "NFLP-other", "IDs": {}, "IDAliases": {}})
        third_party = conflict(["NFLP-provisional", "NFLP-other"])
        with self.assertRaisesRegex(ValueError, "cannot override active provider conflict"):
            validate_current_identity_adjudications_against_state(
                [decision], canonical, [declared, third_party], 2026
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

    @staticmethod
    def _override_entry(**overrides: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "AdjudicationID": "2026-sleeper-11558-sam-hartman",
            "Season": 2026,
            "ResolutionKind": "upstream-claim-override",
            "ConflictPolicy": "override-named-upstream-claim",
            "TargetCanonicalPlayerID": "NFLP-target",
            "SourceCanonicalPlayerIDs": ["NFLP-provisional"],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "11558"}],
            "OverriddenUpstreamClaim": {
                "Source": "nflverse.ff-player-ids",
                "Provider": "Sleeper",
                "ExternalID": "11376",
            },
            "IndependentAnchors": [
                {
                    "Provider": "ESPN",
                    "ExternalID": "4361994",
                    "SourceProvider": "Tank01",
                    "Summary": "Durable ESPN ID equals the Tank01 ID of the Sleeper 11558 record.",
                }
            ],
            "ReplacementTokenConsistency": {
                "Position": "QB",
                "Team": "WAS",
                "Summary": "Sleeper 11558 is the QB at WAS.",
            },
            "OverriddenTokenInconsistency": {
                "Summary": "Sleeper 11376 is listed as an OL without team.",
            },
            "SubjectLabel": "Example QB",
            "Status": "confirmed",
            "DecisionAuthority": "repository-owner-approved-review",
            "DecisionDate": "2026-10-04",
            "Rationale": "Upstream crosswalk assigns a Sleeper ID the platform contradicts.",
            "Evidence": [{"Source": "test-fixture", "Summary": "Platform data."}],
        }
        entry.update(overrides)
        return entry

    @staticmethod
    def _override_state() -> list[dict[str, Any]]:
        return [
            {
                "CanonicalPlayerID": "NFLP-target",
                "Position": "QB",
                "IDs": {"GSIS": "00-0039677", "Sleeper": "11376", "ESPN": "4361994"},
                "IDAliases": {},
            },
            {
                "CanonicalPlayerID": "NFLP-provisional",
                "Position": "QB",
                "IDs": {"Sleeper": "11558", "Tank01": "4361994"},
                "IDAliases": {},
            },
        ]

    def test_override_loads_with_claim_anchors_and_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._override_entry()])
            decisions = load_current_identity_adjudications(
                root, {"NFLP-target", "NFLP-provisional"}, 2026
            )
            self.assertEqual("upstream-claim-override", decisions[0]["ResolutionKind"])
            self.assertEqual(
                {"Source": "nflverse.ff-player-ids", "Provider": "Sleeper", "ExternalID": "11376"},
                decisions[0]["OverriddenUpstreamClaim"],
            )
            self.assertEqual("ESPN", decisions[0]["IndependentAnchors"][0]["Provider"])
            self.assertEqual(
                "manual.current-identity-adjudication:2026-sleeper-11558-sam-hartman",
                decisions[0]["Provenance"],
            )

    def test_override_rejects_incomplete_or_weak_entries(self) -> None:
        known = {"NFLP-target", "NFLP-provisional"}
        cases = {
            "ConflictPolicy must be": {"ConflictPolicy": "reject-active-conflict"},
            "exactly one replacement token": {
                "ProviderAssignments": [
                    {"Provider": "Sleeper", "ExternalID": "11558"},
                    {"Provider": "Tank01", "ExternalID": "4361994"},
                ]
            },
            "OverriddenUpstreamClaim must be an object": {"OverriddenUpstreamClaim": None},
            "must equal the replacement token provider": {
                "OverriddenUpstreamClaim": {
                    "Source": "x",
                    "Provider": "Tank01",
                    "ExternalID": "1",
                }
            },
            "must differ from the replacement token": {
                "OverriddenUpstreamClaim": {
                    "Source": "x",
                    "Provider": "Sleeper",
                    "ExternalID": "11558",
                }
            },
            "IndependentAnchors must be a non-empty array": {"IndependentAnchors": []},
            "Provider must be one of": {
                "IndependentAnchors": [
                    {"Provider": "MFL", "ExternalID": "1", "Summary": "weak"}
                ]
            },
            "ReplacementTokenConsistency must be an object": {
                "ReplacementTokenConsistency": None
            },
            "OverriddenTokenInconsistency must be an object": {
                "OverriddenTokenInconsistency": None
            },
        }
        for message, overrides in cases.items():
            with self.subTest(message):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    self._write_source(root, [self._override_entry(**overrides)])
                    with self.assertRaisesRegex(ValueError, message):
                        load_current_identity_adjudications(root, known, 2026)

    def test_reassignment_kind_requires_its_own_conflict_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self._entry()
            row["ConflictPolicy"] = "override-named-upstream-claim"
            self._write_source(root, [row])
            with self.assertRaisesRegex(ValueError, "ConflictPolicy must be"):
                load_current_identity_adjudications(
                    root, {"NFLP-target", "NFLP-provisional"}, 2026
                )

    def test_two_overrides_of_the_same_upstream_claim_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(
                root,
                [
                    self._override_entry(AdjudicationID="a"),
                    self._override_entry(
                        AdjudicationID="b",
                        ProviderAssignments=[{"Provider": "Sleeper", "ExternalID": "99999"}],
                    ),
                ],
            )
            with self.assertRaisesRegex(ValueError, "override the same upstream claim"):
                load_current_identity_adjudications(
                    root, {"NFLP-target", "NFLP-provisional"}, 2026
                )

    def test_override_state_guard_accepts_hartman_shape_and_reports_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._override_entry()])
            decisions = load_current_identity_adjudications(
                root, {"NFLP-target", "NFLP-provisional"}, 2026
            )
        # The overridden Sleeper token on the target is exactly what an override may supersede,
        # while a plain reassignment of the same token must keep failing closed.
        conflicts = [
            {
                "Provider": "Sleeper",
                "ExternalID": "11376",
                "FirstObservedSeason": 2026,
                "LastObservedSeason": 2026,
            }
        ]
        statuses = validate_current_identity_adjudications_against_state(
            decisions, self._override_state(), conflicts, 2026
        )
        self.assertEqual(
            [{"AdjudicationID": "2026-sleeper-11558-sam-hartman", "Status": "active"}],
            statuses,
        )

    def test_override_state_guard_reports_obsolete_and_superseded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._override_entry()])
            decisions = load_current_identity_adjudications(
                root, {"NFLP-target", "NFLP-provisional"}, 2026
            )

        changed = self._override_state()
        changed[0]["IDs"]["Sleeper"] = "22222"
        self.assertEqual(
            "obsolete",
            validate_current_identity_adjudications_against_state(decisions, changed, [], 2026)[0][
                "Status"
            ],
        )

        gone = self._override_state()
        del gone[0]["IDs"]["Sleeper"]
        self.assertEqual(
            "obsolete",
            validate_current_identity_adjudications_against_state(decisions, gone, [], 2026)[0][
                "Status"
            ],
        )

        fixed = self._override_state()
        fixed[0]["IDs"]["Sleeper"] = "11558"
        self.assertEqual(
            "superseded-by-upstream",
            validate_current_identity_adjudications_against_state(decisions, fixed, [], 2026)[0][
                "Status"
            ],
        )

    def test_override_state_guard_fails_closed_on_contradictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_source(root, [self._override_entry()])
            decisions = load_current_identity_adjudications(
                root, {"NFLP-target", "NFLP-provisional"}, 2026
            )

        third = self._override_state() + [
            {"CanonicalPlayerID": "NFLP-third", "IDs": {"Sleeper": "11558"}, "IDAliases": {}}
        ]
        with self.assertRaisesRegex(ValueError, "undeclared current owners"):
            validate_current_identity_adjudications_against_state(decisions, third, [], 2026)

        conflicts = [{"Provider": "Sleeper", "ExternalID": "11558"}]
        with self.assertRaisesRegex(ValueError, "conflict on the replacement token"):
            validate_current_identity_adjudications_against_state(
                decisions, self._override_state(), conflicts, 2026
            )

        no_anchor = self._override_state()
        no_anchor[0]["IDs"]["ESPN"] = "1"
        with self.assertRaisesRegex(ValueError, "is not carried by target"):
            validate_current_identity_adjudications_against_state(decisions, no_anchor, [], 2026)

        unlinked = self._override_state()
        unlinked[1]["IDs"]["Tank01"] = "7"
        with self.assertRaisesRegex(ValueError, "not carried by any declared source record"):
            validate_current_identity_adjudications_against_state(decisions, unlinked, [], 2026)

        wrong_position = self._override_state()
        wrong_position[0]["Position"] = "OL"
        with self.assertRaisesRegex(ValueError, "declares replacement position"):
            validate_current_identity_adjudications_against_state(
                decisions, wrong_position, [], 2026
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
