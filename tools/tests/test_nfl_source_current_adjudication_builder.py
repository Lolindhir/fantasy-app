"""Identity-builder integration of confirmed current identity adjudications (#347 B5)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import load_registry  # noqa: E402
from nfl_source_data_lib.materialize import _observation_season  # noqa: E402
from nfl_source_data_lib.identity import (  # noqa: E402
    CURRENT_ADJUDICATION_PROVENANCE,
    UPSTREAM_CLAIM_OVERRIDDEN_REASON,
    IdentityCandidate,
    _adjudicated_tokens,
    _apply_current_adjudications,
    build_identities,
    current_identity_adjudication_state,
)
from nfl_source_data_lib.provider_mappings import (  # noqa: E402
    CURRENT_ADJUDICATION_REASON,
    PLACEHOLDER_GSIS_UPGRADE_REASON,
    _retire_transferred_claims,
)

SEASON = 2026


def candidate(ids, *, source="canonical-existing", existing=None):
    return IdentityCandidate(
        ids=dict(ids),
        name="Test Player",
        first_name=None,
        last_name=None,
        birth_date="2001-01-01",
        position="QB",
        latest_team=None,
        source=source,
        priority=10,
        existing_internal_id=existing,
    )


def reassignment(tokens=(("Sleeper", "900"), ("Tank01", "800"))):
    return {
        "AdjudicationID": "test-reassignment",
        "Season": SEASON,
        "ResolutionKind": "current-provider-reassignment",
        "TargetCanonicalPlayerID": "NFLP-target",
        "SourceCanonicalPlayerIDs": ["NFLP-source"],
        "ProviderAssignments": [{"Provider": p, "ExternalID": e} for p, e in tokens],
        "Provenance": f"{CURRENT_ADJUDICATION_PROVENANCE}:test-reassignment",
    }


def override():
    return {
        "AdjudicationID": "test-override",
        "Season": SEASON,
        "ResolutionKind": "upstream-claim-override",
        "TargetCanonicalPlayerID": "NFLP-target",
        "SourceCanonicalPlayerIDs": ["NFLP-source"],
        "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "900"}],
        "OverriddenUpstreamClaim": {
            "Source": "nflverse.ff-player-ids",
            "Provider": "Sleeper",
            "ExternalID": "111",
        },
        "IndependentAnchors": [
            {"Provider": "ESPN", "ExternalID": "700", "SourceProvider": "Tank01"}
        ],
        "Provenance": f"{CURRENT_ADJUDICATION_PROVENANCE}:test-override",
    }


class ApplyCurrentAdjudicationTests(unittest.TestCase):
    def persisted(self):
        return [
            candidate({"GSIS": "00-0012345", "ESPN": "700"}, existing="NFLP-target"),
            candidate({"Sleeper": "900", "Tank01": "800"}, existing="NFLP-source"),
            candidate({"GSIS": "00-0099999"}, existing="NFLP-bystander"),
        ]

    def test_reassignment_moves_tokens_from_sources_to_target_only(self):
        existing = self.persisted()
        transfers, overridden = _apply_current_adjudications([reassignment()], existing, [])
        target, source, bystander = existing
        self.assertEqual({"GSIS": "00-0012345", "ESPN": "700", "Sleeper": "900", "Tank01": "800"}, target.ids)
        self.assertEqual({}, source.ids)
        self.assertEqual({"GSIS": "00-0099999"}, bystander.ids)
        self.assertEqual([], overridden)
        self.assertEqual(
            {
                ("Sleeper", "900"): ("NFLP-target", ("NFLP-source",), f"{CURRENT_ADJUDICATION_PROVENANCE}:test-reassignment"),
                ("Tank01", "800"): ("NFLP-target", ("NFLP-source",), f"{CURRENT_ADJUDICATION_PROVENANCE}:test-reassignment"),
            },
            transfers,
        )

    def test_reassignment_never_replaces_an_existing_target_value(self):
        existing = self.persisted()
        existing[0].ids["Sleeper"] = "123"
        _apply_current_adjudications([reassignment()], existing, [])
        self.assertEqual("123", existing[0].ids["Sleeper"])

    def test_application_is_idempotent(self):
        existing = self.persisted()
        decisions = [reassignment()]
        first = _apply_current_adjudications(decisions, existing, [])
        snapshot = [dict(item.ids) for item in existing]
        second = _apply_current_adjudications(decisions, existing, [])
        self.assertEqual(snapshot, [dict(item.ids) for item in existing])
        self.assertEqual(first[0], second[0])

    def test_override_removes_only_the_named_upstream_claim(self):
        existing = self.persisted()
        existing[0].ids["Sleeper"] = "111"
        existing[1].ids["Tank01"] = "700"
        named = candidate({"ESPN": "700", "Sleeper": "111"}, source="nflverse.ff-player-ids")
        other_upstream = candidate({"GSIS": "00-0012345", "Sleeper": "111"}, source="nflverse.players")
        app = candidate({"Sleeper": "900", "Tank01": "700"}, source="app.Players")
        transfers, overridden = _apply_current_adjudications(
            [override()], existing, [named, other_upstream, app]
        )
        self.assertNotIn("Sleeper", named.ids)
        # Only the named source's claim is declared wrong; other sources and the
        # current app evidence are left as they are.
        self.assertEqual("111", other_upstream.ids["Sleeper"])
        self.assertEqual({"Sleeper": "900", "Tank01": "700"}, app.ids)
        self.assertEqual("900", existing[0].ids["Sleeper"])
        self.assertEqual(
            [
                {
                    "Source": "identity-resolution",
                    "Reason": UPSTREAM_CLAIM_OVERRIDDEN_REASON,
                    "Provider": "Sleeper",
                    "ExternalID": "111",
                    "UpstreamSource": "nflverse.ff-player-ids",
                    "CanonicalPlayerID": "NFLP-target",
                    "Provenance": f"{CURRENT_ADJUDICATION_PROVENANCE}:test-override",
                }
            ],
            overridden,
        )
        # The anchor link (ESPN on the target equals Tank01 on the source) moves with the replacement token.
        self.assertEqual({("Sleeper", "900"), ("Tank01", "700")}, set(transfers))
        self.assertEqual({}, existing[1].ids)

    def test_adjudicated_tokens_are_assignments_plus_anchor_source_link(self):
        self.assertEqual({("Sleeper", "900"), ("Tank01", "700")}, _adjudicated_tokens(override()))
        self.assertEqual(
            {("Sleeper", "900"), ("Tank01", "800")}, _adjudicated_tokens(reassignment())
        )


class TransferReasonTests(unittest.TestCase):
    def retire(self, sources):
        mappings = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerID": "NFLP-source",
                "FirstObservedSeason": 2025,
                "LastObservedSeason": 2026,
                "Sources": ["app.Players"],
            }
        ]
        conflicts: list[dict] = []
        claims = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerID": "NFLP-target",
                "Sources": sources,
                "TransferredFromCanonicalPlayerIDs": ["NFLP-source"],
            }
        ]
        reconciliations = _retire_transferred_claims(claims, mappings, conflicts, SEASON)
        return mappings, reconciliations

    def test_adjudicated_transfer_retires_only_the_current_season_with_its_own_reason(self):
        mappings, reconciliations = self.retire(
            ["app.Players", f"{CURRENT_ADJUDICATION_PROVENANCE}:x"]
        )
        self.assertEqual(2025, mappings[0]["LastObservedSeason"])
        self.assertEqual([CURRENT_ADJUDICATION_REASON], [item["Reason"] for item in reconciliations])

    def test_placeholder_transfer_keeps_its_reason(self):
        _, reconciliations = self.retire(["auto.placeholder-gsis-upgrade:ABC"])
        self.assertEqual([PLACEHOLDER_GSIS_UPGRADE_REASON], [item["Reason"] for item in reconciliations])


class RepositoryAdjudicationBuilderTests(unittest.TestCase):
    """The confirmed repository decisions are applied by the productive builder.

    Expectations are derived from the adjudication source itself, never from
    hard-wired players. The check holds before the first materialization (the
    builder applies the decision) and after it (replay finds it already applied).
    The sync runs this suite before it materializes, so nothing here may depend on
    the persisted identities being complete for the current Players.json.
    """

    @classmethod
    def setUpClass(cls):
        registry = load_registry(ROOT)
        datasets = {dataset.id: dataset for dataset in registry if dataset.materialize}
        cls.season = _observation_season(ROOT)
        cls.decisions, cls.statuses = current_identity_adjudication_state(ROOT, cls.season)
        if not cls.decisions:
            raise unittest.SkipTest(f"no confirmed current adjudication for season {cls.season}")
        cls.canonical, _, cls.source_conflicts, cls.claims, _ = build_identities(
            ROOT, datasets, cls.season
        )
        cls.persisted = json.loads(
            (ROOT / "source-data/nfl/identities/players.json").read_text(encoding="utf-8-sig")
        )["Players"]

    def test_repository_decisions_are_applicable(self):
        self.assertTrue(
            {item["Status"] for item in self.statuses} <= {"active", "superseded-by-upstream"},
            self.statuses,
        )

    def test_no_persisted_canonical_player_id_is_removed(self):
        # New players may legitimately add IDs; a decision never removes or merges one.
        before = {row["CanonicalPlayerID"] for row in self.persisted}
        after = {row["CanonicalPlayerID"] for row in self.canonical}
        self.assertLessEqual(before, after)

    def test_assigned_tokens_belong_to_the_target_and_not_to_the_sources(self):
        by_id = {row["CanonicalPlayerID"]: row for row in self.canonical}
        current_claims = {
            (claim["Provider"], claim["ExternalID"]): claim for claim in self.claims
        }

        def tokens(row):
            result = {(provider, value) for provider, value in row["IDs"].items()}
            for provider, values in (row.get("IDAliases") or {}).items():
                result.update((provider, value) for value in values)
            return result

        for decision in self.decisions:
            target = by_id[decision["TargetCanonicalPlayerID"]]
            for token in _adjudicated_tokens(decision):
                with self.subTest(decision=decision["AdjudicationID"], token=token):
                    for source_id in decision["SourceCanonicalPlayerIDs"]:
                        self.assertNotIn(token, tokens(by_id[source_id]))
                    # The target carries a token only while current provider
                    # evidence (app.Players or a crosswalk) still claims it.
                    if token in current_claims:
                        self.assertEqual(
                            decision["TargetCanonicalPlayerID"],
                            current_claims[token]["CanonicalPlayerID"],
                        )
                        self.assertIn(token, tokens(target))

    def test_overridden_upstream_claims_leave_the_target_and_stay_visible(self):
        by_id = {row["CanonicalPlayerID"]: row for row in self.canonical}
        for decision in self.decisions:
            claim = decision.get("OverriddenUpstreamClaim")
            if not claim:
                continue
            target = by_id[decision["TargetCanonicalPlayerID"]]
            with self.subTest(decision=decision["AdjudicationID"]):
                values = {target["IDs"].get(claim["Provider"])} | set(
                    (target.get("IDAliases") or {}).get(claim["Provider"], [])
                )
                self.assertNotIn(claim["ExternalID"], values)
                self.assertIn(
                    (claim["Provider"], claim["ExternalID"], decision["TargetCanonicalPlayerID"]),
                    {
                        (item["Provider"], item["ExternalID"], item["CanonicalPlayerID"])
                        for item in self.source_conflicts
                        if item.get("Reason") == UPSTREAM_CLAIM_OVERRIDDEN_REASON
                    },
                )

    def test_applied_claims_carry_the_adjudication_provenance(self):
        owners = {
            (claim["Provider"], claim["ExternalID"]): claim for claim in self.claims
        }
        for decision in self.decisions:
            for provider, external_id in _adjudicated_tokens(decision):
                claim = owners.get((provider, external_id))
                if claim is None:
                    continue  # no current provider evidence carries this token
                with self.subTest(decision=decision["AdjudicationID"], token=(provider, external_id)):
                    self.assertEqual(decision["TargetCanonicalPlayerID"], claim["CanonicalPlayerID"])
                    self.assertIn(decision["Provenance"], claim["Sources"])


if __name__ == "__main__":
    unittest.main()
