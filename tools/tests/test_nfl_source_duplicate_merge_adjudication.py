"""``confirmed-canonical-duplicate-merge`` current identity adjudication (G5 AP0a)."""

from __future__ import annotations

import copy
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
    MERGE_KIND,
    load_current_identity_adjudications,
    validate_current_identity_adjudications_against_state,
)
from nfl_source_data_lib.identity import (  # noqa: E402
    CURRENT_ADJUDICATION_PROVENANCE,
    IdentityCandidate,
    _apply_current_adjudications,
    _apply_duplicate_merges,
    _build_components,
    _component_members,
    _seed_for_component,
)
from nfl_source_data_lib.common import stable_internal_id  # noqa: E402
from nfl_source_data_lib.provider_mappings import retire_merged_duplicate_mappings  # noqa: E402

SEASON = 2026
TARGET = "NFLP-target"
PHANTOM = "NFLP-phantom"
BIRTH = "2001-03-27"


def candidate(ids, *, source, existing=None, name="Gregory Desrosiers", birth=BIRTH,
              position="RB"):
    return IdentityCandidate(
        ids=dict(ids), name=name, first_name=None, last_name=None, birth_date=birth,
        position=position, latest_team="LAC", source=source, priority=10,
        existing_internal_id=existing,
    )


def target_candidate(**overrides):
    return candidate({"GSIS": "00-0041376", "Tank01": "4691889", "Sleeper": "13603"},
                     source="canonical-existing", existing=TARGET, **overrides)


def duplicate_ids():
    return {"Sleeper": "13603", "ESPN": "4691889", "MFL": "17821"}


def duplicate_id_of(cands):
    return stable_internal_id(_seed_for_component(cands))


def merge_decision(duplicate: str, **overrides) -> dict[str, Any]:
    value = {
        "AdjudicationID": "test-merge",
        "Season": SEASON,
        "Status": "confirmed",
        "DecisionAuthority": "repository-owner-approved-review",
        "DecisionDate": "2026-11-08",
        "ResolutionKind": MERGE_KIND,
        "ConflictPolicy": "reject-conflict-outside-declared-pair",
        "TargetCanonicalPlayerID": TARGET,
        "DuplicateCanonicalPlayerIDs": [duplicate],
        "SourceCanonicalPlayerIDs": [],
        "ProviderAssignments": [],
        "SubjectLabel": "Gregory Desrosiers (duplicate record)",
        "Rationale": "Reviewed: both records are the same person.",
        "IndependentAnchors": [
            {"Kind": "cross-provider-id-equality", "TargetProvider": "Tank01",
             "DuplicateProvider": "ESPN", "ExternalID": "4691889",
             "Summary": "Tank01 4691889 equals ESPN 4691889."},
            {"Kind": "attribute-agreement", "Fields": ["BirthDate", "NormalizedName", "Position"],
             "Summary": "Equal birth date, name and position."},
        ],
        "Evidence": [{"Source": "test-fixture", "Summary": "Independent review."}],
    }
    value.update(overrides)
    return value


def loaded(decision: dict[str, Any], known: set[str] | None = None) -> dict[str, Any]:
    return loaded_many([decision], known)[0]


def loaded_many(entries: list[dict[str, Any]], known: set[str] | None = None) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "data-source/nfl/identities/current-identity-adjudications.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"SchemaVersion": 1, "Adjudications": entries}), encoding="utf-8")
        return load_current_identity_adjudications(
            Path(tmp), known if known is not None else {TARGET, PHANTOM}, SEASON
        )


def run_merge(cands, decision):
    uf = _build_components(cands)
    transfers = _apply_duplicate_merges(uf, cands, [decision])
    return uf, transfers


class LoaderTests(unittest.TestCase):
    def test_loads_without_requiring_the_duplicate_to_exist(self) -> None:
        decision = loaded(merge_decision("NFLP-not-persisted-yet"))
        self.assertEqual(["NFLP-not-persisted-yet"], decision["DuplicateCanonicalPlayerIDs"])
        self.assertEqual([], decision["ProviderAssignments"])
        self.assertEqual(
            f"{CURRENT_ADJUDICATION_PROVENANCE}:test-merge", decision["Provenance"]
        )

    def test_rejects_malformed_entries(self) -> None:
        base = merge_decision("NFLP-dup")
        cases = {
            "no duplicates": {"DuplicateCanonicalPlayerIDs": []},
            "target as duplicate": {"DuplicateCanonicalPlayerIDs": [TARGET]},
            "source as duplicate": {"SourceCanonicalPlayerIDs": [PHANTOM],
                                    "DuplicateCanonicalPlayerIDs": [PHANTOM]},
            "assignments present": {"ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "1"}]},
            "wrong conflict policy": {"ConflictPolicy": "reject-active-conflict"},
            "single anchor": {"IndependentAnchors": base["IndependentAnchors"][:1]},
            "no attribute anchor": {"IndependentAnchors": [base["IndependentAnchors"][0]] * 2},
            "same provider equality": {"IndependentAnchors": [
                {**base["IndependentAnchors"][0], "DuplicateProvider": "Tank01"},
                base["IndependentAnchors"][1]]},
            "attribute anchor without birth date": {"IndependentAnchors": [
                base["IndependentAnchors"][0],
                {**base["IndependentAnchors"][1], "Fields": ["NormalizedName", "Position"]}]},
            "unknown anchor kind": {"IndependentAnchors": [
                base["IndependentAnchors"][0], {"Kind": "name-only", "Summary": "x"}]},
        }
        for label, overrides in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                loaded(merge_decision("NFLP-dup", **overrides))

    def test_chains_and_double_merges_are_rejected(self) -> None:
        first = merge_decision("NFLP-dup", AdjudicationID="first")
        chained = merge_decision("NFLP-other", AdjudicationID="second",
                                 TargetCanonicalPlayerID="NFLP-dup")
        with self.assertRaises(ValueError):
            loaded_many([first, chained], {TARGET, "NFLP-dup"})
        again = merge_decision("NFLP-dup", AdjudicationID="third")
        with self.assertRaises(ValueError):
            loaded_many([first, again])

    def test_duplicate_as_target_of_another_adjudication_is_rejected(self) -> None:
        merge = merge_decision("NFLP-dup")
        reassignment = {
            "AdjudicationID": "other", "Season": SEASON, "Status": "confirmed",
            "ResolutionKind": "current-provider-reassignment",
            "ConflictPolicy": "reject-active-conflict",
            "TargetCanonicalPlayerID": "NFLP-dup", "SourceCanonicalPlayerIDs": [PHANTOM],
            "ProviderAssignments": [{"Provider": "Sleeper", "ExternalID": "9"}],
            "SubjectLabel": "x", "Rationale": "x", "DecisionAuthority": "x",
            "DecisionDate": "2026-01-01", "Evidence": [{"Source": "x", "Summary": "x"}],
        }
        with self.assertRaises(ValueError):
            loaded_many([merge, reassignment], {TARGET, PHANTOM, "NFLP-dup"})


class StateTests(unittest.TestCase):
    def players(self, **duplicate_overrides) -> list[dict[str, Any]]:
        target = {"CanonicalPlayerID": TARGET, "Name": "Gregory Desrosiers", "BirthDate": BIRTH,
                  "Position": "RB", "IDs": {"GSIS": "00-0041376", "Tank01": "4691889"}}
        duplicate = {"CanonicalPlayerID": "NFLP-dup", "Name": "Gregory  Desrosiers",
                     "BirthDate": BIRTH, "Position": "RB", "IDs": duplicate_ids()}
        duplicate.update(duplicate_overrides)
        return [target, duplicate]

    def validate(self, players, conflicts=(), claims=()):
        return validate_current_identity_adjudications_against_state(
            [loaded(merge_decision("NFLP-dup"), {TARGET, PHANTOM})], players,
            list(conflicts), SEASON, mapping_claims=list(claims),
        )

    def test_valid_pair_is_active_and_missing_duplicate_is_superseded(self) -> None:
        self.assertEqual("active", self.validate(self.players())[0]["Status"])
        self.assertEqual("superseded-by-upstream", self.validate(self.players()[:1])[0]["Status"])

    def test_rejects_unprovable_pairs(self) -> None:
        cases = {
            "birth date differs": self.players(BirthDate="2001-03-28"),
            "birth date missing": self.players(BirthDate=None),
            "position differs": self.players(Position="WR"),
            "name differs": self.players(Name="Greg Other"),
            "no cross-provider anchor": self.players(IDs={**duplicate_ids(), "ESPN": "1"}),
            "contradicting GSIS": self.players(IDs={**duplicate_ids(), "GSIS": "00-0099999"}),
            "contradicting alias": self.players(IDs=duplicate_ids(),
                                                IDAliases={"Tank01": ["777"]}),
        }
        for label, players in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                self.validate(players)

    def test_third_party_in_conflict_owner_or_historical_claim_is_rejected(self) -> None:
        conflict = {"Provider": "MFL", "ExternalID": "17821",
                    "CanonicalPlayerIDs": ["NFLP-dup", "NFLP-fourth"]}
        with self.assertRaises(ValueError):
            self.validate(self.players(), conflicts=[conflict])
        claim = {"Provider": "MFL", "ExternalID": "17821", "CanonicalPlayerID": "NFLP-fourth",
                 "FirstObservedSeason": SEASON, "LastObservedSeason": SEASON}
        with self.assertRaises(ValueError):
            self.validate(self.players(), claims=[claim])
        players = self.players() + [{"CanonicalPlayerID": "NFLP-fourth", "Name": "Other",
                                      "IDs": {"MFL": "17821"}}]
        with self.assertRaises(ValueError):
            self.validate(players)

    def test_conflict_inside_the_declared_pair_and_sources_is_allowed(self) -> None:
        conflict = {"Provider": "Sleeper", "ExternalID": "13603",
                    "CanonicalPlayerIDs": [TARGET, "NFLP-dup", PHANTOM]}
        decision = loaded(merge_decision("NFLP-dup", SourceCanonicalPlayerIDs=[PHANTOM]),
                          {TARGET, PHANTOM})
        statuses = validate_current_identity_adjudications_against_state(
            [decision], self.players() + [{"CanonicalPlayerID": PHANTOM, "Name": "x", "IDs": {}}],
            [conflict], SEASON,
        )
        self.assertEqual("active", statuses[0]["Status"])


class BuilderTests(unittest.TestCase):
    def pass_one(self):
        dup = [
            candidate(duplicate_ids(), source="nflverse.ff-player-ids"),
            candidate({"Sleeper": "13603"}, source="sleeper.players", birth=None),
        ]
        return [target_candidate(), *dup], duplicate_id_of(dup)

    def components_view(self, cands, uf):
        return sorted(
            sorted({f"{k}:{v}" for i in idx for k, v in cands[i].ids.items()})
            for idx in _component_members(uf, cands).values()
        )

    def test_unpersisted_duplicate_is_merged_into_the_target_in_the_same_pass(self) -> None:
        cands, dup_id = self.pass_one()
        decision = loaded(merge_decision(dup_id), {TARGET, PHANTOM})
        uf = _build_components(cands)
        self.assertEqual(2, len(_component_members(uf, cands)))
        transfers = _apply_duplicate_merges(uf, cands, [decision])
        components = _component_members(uf, cands)
        self.assertEqual(1, len(components))
        self.assertEqual({TARGET}, {c.existing_internal_id for c in cands if c.existing_internal_id})
        for token in (("ESPN", "4691889"), ("MFL", "17821"), ("Sleeper", "13603")):
            self.assertEqual(
                (TARGET, (dup_id,), decision["Provenance"]), transfers[token]
            )

    def test_second_pass_with_persisted_duplicate_yields_the_same_merged_component(self) -> None:
        cands, dup_id = self.pass_one()
        decision = loaded(merge_decision(dup_id), {TARGET, PHANTOM})
        first_uf, first_transfers = run_merge(copy.deepcopy(cands), decision)
        persisted_duplicate = candidate(duplicate_ids(), source="canonical-existing",
                                        existing=dup_id)
        second = [*copy.deepcopy(cands), persisted_duplicate]
        second_uf, second_transfers = run_merge(second, decision)
        self.assertEqual(1, len(_component_members(second_uf, second)))
        self.assertEqual(
            {c.existing_internal_id for c in second if c.existing_internal_id}, {TARGET}
        )
        self.assertEqual(first_transfers, second_transfers)
        self.assertEqual(
            self.components_view(second, second_uf)[0],
            sorted({f"{k}:{v}" for c in cands for k, v in c.ids.items()}),
        )

    def test_unrelated_or_absent_duplicate_changes_nothing(self) -> None:
        cands, _ = self.pass_one()
        decision = loaded(merge_decision("NFLP-absent"), {TARGET, PHANTOM})
        uf, transfers = run_merge(cands, decision)
        self.assertEqual({}, transfers)
        self.assertEqual(2, len(_component_members(uf, cands)))

    def test_builder_fails_closed_when_candidate_evidence_does_not_prove_one_person(self) -> None:
        for label, change in {
            "birth date": lambda c: setattr(c, "birth_date", "2000-01-01"),
            "position": lambda c: setattr(c, "position", "QB"),
            "cross anchor": lambda c: c.ids.update({"ESPN": "1"}),
            "gsis contradiction": lambda c: c.ids.update({"GSIS": "00-0000001"}),
        }.items():
            with self.subTest(label):
                cands, _ = self.pass_one()
                change(cands[1])
                # the duplicate ID is a seed of its evidence, so recompute it
                decision = loaded(merge_decision(duplicate_id_of(cands[1:])), {TARGET, PHANTOM})
                with self.assertRaises(ValueError):
                    run_merge(cands, decision)

    def test_declared_merge_leaves_other_adjudication_kinds_untouched(self) -> None:
        cands, dup_id = self.pass_one()
        decision = loaded(merge_decision(dup_id), {TARGET, PHANTOM})
        transfers, overridden = _apply_current_adjudications([decision], cands, [])
        self.assertEqual(({}, []), (transfers, overridden))
        self.assertEqual({"Sleeper": "13603", "ESPN": "4691889", "MFL": "17821"}, cands[1].ids)


SHARED_ANCHOR = {"Kind": "shared-provider-token", "Provider": "GSIS", "ExternalID": "00-0041376",
                 "Summary": "Both records carry the GSIS."}
ATTRIBUTE_ANCHOR = {"Kind": "attribute-agreement", "Fields": ["BirthDate", "NormalizedName", "Position"],
                    "Summary": "Equal birth date, name and position."}
CONTAMINATED = [
    {"Provider": "ESPN", "ExternalID": "9001", "Source": "nflverse.ff-player-ids",
     "Summary": "ESPN 9001 belongs to another person."},
    {"Provider": "PFF", "ExternalID": "9002", "Source": "nflverse.ff-player-ids",
     "Summary": "PFF 9002 belongs to another person."},
]


def contaminated_decision(duplicate: str, **overrides) -> dict[str, Any]:
    base = {"IndependentAnchors": [SHARED_ANCHOR, ATTRIBUTE_ANCHOR],
            "ContaminatedTokens": CONTAMINATED}
    base.update(overrides)
    return merge_decision(duplicate, **base)


def contaminated_ff_ids() -> dict[str, str]:
    return {"GSIS": "00-0041376", "Sleeper": "13603", "ESPN": "9001", "PFF": "9002", "MFL": "17821"}


class ContaminatedTokenTests(unittest.TestCase):
    def target(self):
        return candidate({"GSIS": "00-0041376", "ESPN": "5001", "PFF": "5002"},
                         source="nflverse.players", existing=TARGET)

    def test_loader_accepts_shared_anchor_and_validates_contaminated_tokens(self) -> None:
        decision = loaded(contaminated_decision("NFLP-dup"))
        self.assertEqual(["ESPN", "PFF"], [t["Provider"] for t in decision["ContaminatedTokens"]])
        self.assertEqual([], loaded(merge_decision("NFLP-dup"))["ContaminatedTokens"])
        cases = {
            "empty list": {"ContaminatedTokens": []},
            "missing summary": {"ContaminatedTokens": [{**CONTAMINATED[0], "Summary": ""}]},
            "missing source": {"ContaminatedTokens": [{k: v for k, v in CONTAMINATED[0].items()
                                                       if k != "Source"}]},
            "duplicate entry": {"ContaminatedTokens": [CONTAMINATED[0], CONTAMINATED[0]]},
            "unsupported shared provider": {"IndependentAnchors": [
                {**SHARED_ANCHOR, "Provider": "MFL"}, ATTRIBUTE_ANCHOR]},
            "shared anchor alone": {"IndependentAnchors": [SHARED_ANCHOR]},
        }
        for label, overrides in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                loaded(contaminated_decision("NFLP-dup", **overrides))

    def test_builder_merges_and_drops_contaminated_tokens_without_transferring_them(self) -> None:
        dup = [candidate(contaminated_ff_ids(), source="nflverse.ff-player-ids")]
        dup_id = duplicate_id_of(dup)
        decision = loaded(contaminated_decision(dup_id), {TARGET, PHANTOM})
        cands = [self.target(), *dup]
        uf = _build_components(cands)
        transfers = _apply_duplicate_merges(uf, cands, [decision])
        self.assertEqual(1, len(_component_members(uf, cands)))
        self.assertNotIn(("ESPN", "9001"), transfers)
        self.assertNotIn(("PFF", "9002"), transfers)
        self.assertEqual({"GSIS": "00-0041376", "Sleeper": "13603", "MFL": "17821"}, dup[0].ids)
        self.assertEqual((TARGET, (dup_id,), decision["Provenance"]), transfers[("Sleeper", "13603")])

    def test_contamination_is_not_a_free_pass_for_other_contradictions(self) -> None:
        for label, ids in {
            "undeclared contradicting token": {**contaminated_ff_ids(), "ESPN": "9999"},
            "contradicting GSIS": {**contaminated_ff_ids(), "GSIS": "00-0000001"},
        }.items():
            with self.subTest(label):
                dup = [candidate(ids, source="nflverse.ff-player-ids")]
                decision = loaded(contaminated_decision(duplicate_id_of(dup)), {TARGET, PHANTOM})
                with self.assertRaises(ValueError):
                    run_merge([self.target(), *dup], decision)

    def test_without_the_declaration_the_same_evidence_is_rejected(self) -> None:
        dup = [candidate(contaminated_ff_ids(), source="nflverse.ff-player-ids")]
        decision = loaded(
            merge_decision(duplicate_id_of(dup), IndependentAnchors=[SHARED_ANCHOR, ATTRIBUTE_ANCHOR]),
            {TARGET, PHANTOM},
        )
        with self.assertRaises(ValueError):
            run_merge([self.target(), *dup], decision)

    def test_state_validator_ignores_contaminated_tokens_owned_by_a_third_record(self) -> None:
        players = [
            {"CanonicalPlayerID": TARGET, "Name": "Gregory Desrosiers", "BirthDate": BIRTH,
             "Position": "RB", "IDs": {"GSIS": "00-0041376", "ESPN": "5001"}},
            {"CanonicalPlayerID": "NFLP-dup", "Name": "Gregory Desrosiers", "BirthDate": BIRTH,
             "Position": "RB", "IDs": contaminated_ff_ids()},
            {"CanonicalPlayerID": "NFLP-third", "Name": "Someone Else", "IDs": {"ESPN": "9001"}},
        ]
        decision = loaded(contaminated_decision("NFLP-dup"), {TARGET, PHANTOM})
        statuses = validate_current_identity_adjudications_against_state(
            [decision], players, [], SEASON)
        self.assertEqual("active", statuses[0]["Status"])
        players[2]["IDs"] = {"ESPN": "9001", "MFL": "17821"}  # owns an undeclared, real token
        with self.assertRaises(ValueError):
            validate_current_identity_adjudications_against_state([decision], players, [], SEASON)


class RetireMergedMappingsTests(unittest.TestCase):
    def mapping(self, provider, external, owner, first, last, source="s"):
        return {"Provider": provider, "ExternalID": external, "CanonicalPlayerID": owner,
                "FirstObservedSeason": first, "LastObservedSeason": last, "Sources": [source]}

    def test_mappings_and_conflicts_of_a_retired_duplicate_move_to_the_target(self) -> None:
        decision = loaded(contaminated_decision("NFLP-dup"), {TARGET, PHANTOM})
        payload = {
            "Mappings": [
                self.mapping("Sleeper", "13603", "NFLP-dup", 2025, 2026, "a"),
                self.mapping("Sleeper", "13603", TARGET, 2024, 2025, "b"),
                self.mapping("ESPN", "9001", "NFLP-dup", 2025, 2025),
                self.mapping("MFL", "1", "NFLP-other", 2025, 2025),
            ],
            "Conflicts": [
                {"Provider": "Sleeper", "ExternalID": "13603", "CanonicalPlayerIDs": [TARGET, "NFLP-dup"]},
                {"Provider": "ESPN", "ExternalID": "9001", "CanonicalPlayerIDs": ["NFLP-dup", "NFLP-other"]},
                {"Provider": "MFL", "ExternalID": "5", "CanonicalPlayerIDs": ["NFLP-dup", "NFLP-other"],
                 "SourcesByCanonicalPlayerID": {"NFLP-dup": ["x"]}},
            ],
            "HistoricalResolutionConflicts": [{"keep": "as evidence"}],
        }
        result = retire_merged_duplicate_mappings(copy.deepcopy(payload), [decision])
        keys = {(m["Provider"], m["ExternalID"], m["CanonicalPlayerID"]): m for m in result["Mappings"]}
        self.assertEqual({("Sleeper", "13603", TARGET), ("MFL", "1", "NFLP-other")}, set(keys))
        merged = keys[("Sleeper", "13603", TARGET)]
        self.assertEqual((2024, 2026, ["a", "b"]),
                         (merged["FirstObservedSeason"], merged["LastObservedSeason"], merged["Sources"]))
        self.assertEqual(
            [{"Provider": "MFL", "ExternalID": "5", "CanonicalPlayerIDs": sorted([TARGET, "NFLP-other"]),
              "SourcesByCanonicalPlayerID": {TARGET: ["x"]}}],
            result["Conflicts"],
        )
        self.assertEqual(payload["HistoricalResolutionConflicts"], result["HistoricalResolutionConflicts"])
        self.assertEqual(result, retire_merged_duplicate_mappings(copy.deepcopy(result), [decision]))

    def test_payload_is_untouched_without_a_merge_decision(self) -> None:
        payload = {"Mappings": [self.mapping("Sleeper", "1", "NFLP-dup", 2026, 2026)], "Conflicts": []}
        self.assertIs(payload, retire_merged_duplicate_mappings(payload, []))


if __name__ == "__main__":
    unittest.main()
