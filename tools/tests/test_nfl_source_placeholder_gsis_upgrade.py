import re
import sys
import unittest
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import load_registry
from nfl_source_data_lib.identity import (
    IdentityCandidate,
    build_identities,
    UnionFind,
    _apply_placeholder_gsis_upgrades,
    _component_members,
    _placeholder_gsis_upgrades,
)
from nfl_source_data_lib.provider_mappings import _retire_transferred_claims

SEASON = 2026


def candidate(ids, *, source="nflverse.players", birth_date="2002-01-01", existing=None):
    if existing:
        source = "canonical-existing"
    return IdentityCandidate(
        ids=dict(ids),
        name="Test Player",
        first_name=None,
        last_name=None,
        birth_date=birth_date,
        position="TE",
        latest_team=None,
        source=source,
        priority=10,
        existing_internal_id=existing,
    )


def components(groups):
    """Build candidates and a union-find from groups of candidates."""
    candidates = [item for group in groups for item in group]
    uf = UnionFind()
    for _ in candidates:
        uf.add()
    position = 0
    for group in groups:
        for offset in range(1, len(group)):
            uf.union(position, position + offset)
        position += len(group)
    return uf, candidates


def placeholder_group(esb="ABC123456", **extra):
    return [
        candidate({"GSIS": esb, "ESB": esb, **extra}, existing="NFLP-placeholder"),
        candidate({"GSIS": esb, "ESB": esb, "Sleeper": "900", **extra}, source="app.Players"),
    ]


def valid_group(esb="ABC123456", gsis="00-0012345", **extra):
    return [
        candidate({"GSIS": gsis, "ESB": esb, "NFL": "5", **extra}, existing="NFLP-valid"),
    ]


class PlaceholderGsisUpgradeRuleTests(unittest.TestCase):
    def test_shared_esb_bridges_placeholder_to_valid_gsis(self):
        uf, candidates = components([placeholder_group(), valid_group()])
        upgrades = _placeholder_gsis_upgrades(uf, candidates)
        self.assertEqual(
            {uf.find(0): (uf.find(len(placeholder_group())), "ABC123456")}, upgrades
        )

    def test_missing_gsis_counts_as_placeholder(self):
        placeholder = [candidate({"ESB": "ABC123456", "Sleeper": "900"}, existing="NFLP-placeholder")]
        uf, candidates = components([placeholder, valid_group()])
        self.assertEqual(1, len(_placeholder_gsis_upgrades(uf, candidates)))

    def test_requires_exactly_one_valid_gsis_side(self):
        for groups in (
            [valid_group(), valid_group(gsis="00-0099999")],
            [placeholder_group(), placeholder_group()],
        ):
            uf, candidates = components(groups)
            self.assertEqual({}, _placeholder_gsis_upgrades(uf, candidates))

    def test_esb_must_occur_on_exactly_two_components(self):
        uf, candidates = components(
            [placeholder_group(), valid_group(), valid_group(gsis="00-0099999")]
        )
        self.assertEqual({}, _placeholder_gsis_upgrades(uf, candidates))

    def test_other_shared_provider_disagreement_blocks_the_bridge(self):
        uf, candidates = components(
            [placeholder_group(PFR="Aaaa00"), valid_group(PFR="Bbbb00")]
        )
        self.assertEqual({}, _placeholder_gsis_upgrades(uf, candidates))

    def test_agreeing_or_one_sided_providers_do_not_block(self):
        uf, candidates = components(
            [placeholder_group(PFR="Aaaa00", OTC="7"), valid_group(PFR="Aaaa00", PFF="9")]
        )
        self.assertEqual(1, len(_placeholder_gsis_upgrades(uf, candidates)))

    def test_conflicting_birth_dates_block_the_bridge(self):
        placeholder = placeholder_group()
        for item in placeholder:
            item.birth_date = "2001-05-05"
        uf, candidates = components([placeholder, valid_group()])
        self.assertEqual({}, _placeholder_gsis_upgrades(uf, candidates))

    def test_different_esb_values_are_not_bridged(self):
        uf, candidates = components([placeholder_group(esb="AAA111111"), valid_group(esb="BBB222222")])
        self.assertEqual({}, _placeholder_gsis_upgrades(uf, candidates))


class PlaceholderGsisUpgradeApplyTests(unittest.TestCase):
    def test_current_evidence_moves_and_persisted_identities_stay(self):
        uf, candidates = components([placeholder_group(), valid_group()])
        moved = _apply_placeholder_gsis_upgrades(uf, candidates)

        members = _component_members(uf, candidates)
        by_existing = {
            candidate.existing_internal_id: uf.find(idx)
            for idx, candidate in enumerate(candidates)
            if candidate.existing_internal_id
        }
        self.assertEqual({1: ("ABC123456", "NFLP-placeholder")}, moved)
        # Persisted records keep separate components, so no CanonicalPlayerID is merged.
        self.assertNotEqual(by_existing["NFLP-placeholder"], by_existing["NFLP-valid"])
        # The placeholder GSIS is not transferred; the app claim is.
        self.assertEqual(by_existing["NFLP-valid"], uf.find(1))
        self.assertEqual("900", candidates[1].ids["Sleeper"])
        self.assertNotIn("GSIS", candidates[1].ids)
        self.assertEqual(sum(len(indexes) for indexes in members.values()), len(candidates))

    def test_second_application_is_a_no_op(self):
        uf, candidates = components([placeholder_group(), valid_group()])
        first = _apply_placeholder_gsis_upgrades(uf, candidates)
        snapshot = [dict(item.ids) for item in candidates]
        groups_before = {idx: uf.find(idx) for idx in range(len(candidates))}
        second = _apply_placeholder_gsis_upgrades(uf, candidates)
        self.assertTrue(first)
        # The valid component now owns the current evidence; the persisted
        # placeholder record is unchanged and nothing moves again.
        self.assertEqual(snapshot, [dict(item.ids) for item in candidates])
        self.assertEqual(groups_before, {idx: uf.find(idx) for idx in range(len(candidates))})
        self.assertEqual({}, second)

    def test_no_upgrade_leaves_components_untouched(self):
        uf, candidates = components([valid_group(), valid_group(gsis="00-0099999", esb="ZZZ999999")])
        self.assertEqual({}, _apply_placeholder_gsis_upgrades(uf, candidates))


class TransferredClaimRetirementTests(unittest.TestCase):
    def claim(self):
        return {
            "Provider": "Sleeper",
            "ExternalID": "900",
            "CanonicalPlayerID": "NFLP-valid",
            "Sources": ["app.Players", "auto.placeholder-gsis-upgrade:ABC123456"],
            "TransferredFromCanonicalPlayerIDs": ["NFLP-placeholder"],
        }

    def test_previous_owner_mapping_and_conflict_season_are_retired(self):
        mappings = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerID": "NFLP-placeholder",
                "FirstObservedSeason": SEASON - 1,
                "LastObservedSeason": SEASON,
                "Sources": ["app.Players"],
            },
            {
                "Provider": "Sleeper",
                "ExternalID": "901",
                "CanonicalPlayerID": "NFLP-placeholder",
                "FirstObservedSeason": SEASON,
                "LastObservedSeason": SEASON,
                "Sources": ["app.Players"],
            },
        ]
        conflicts = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerIDs": ["NFLP-other", "NFLP-placeholder"],
                "FirstObservedSeason": SEASON,
                "LastObservedSeason": SEASON,
                "Status": "ambiguous",
            }
        ]
        reconciliations = _retire_transferred_claims([self.claim()], mappings, conflicts, SEASON)

        self.assertEqual(SEASON - 1, mappings[0]["LastObservedSeason"])
        self.assertEqual("901", mappings[1]["ExternalID"])
        self.assertEqual([], conflicts)
        self.assertEqual(1, len(reconciliations))
        self.assertEqual(["NFLP-placeholder"], reconciliations[0]["RetiredCanonicalPlayerIDs"])
        self.assertEqual("NFLP-valid", reconciliations[0]["CanonicalPlayerID"])

    def test_retirement_is_idempotent(self):
        mappings = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerID": "NFLP-placeholder",
                "FirstObservedSeason": SEASON,
                "LastObservedSeason": SEASON,
                "Sources": ["app.Players"],
            }
        ]
        conflicts: list = []
        self.assertEqual(1, len(_retire_transferred_claims([self.claim()], mappings, conflicts, SEASON)))
        self.assertEqual([], mappings)
        self.assertEqual([], _retire_transferred_claims([self.claim()], mappings, conflicts, SEASON))

    def test_claims_without_transfer_are_ignored(self):
        claim = self.claim()
        del claim["TransferredFromCanonicalPlayerIDs"]
        mappings = [
            {
                "Provider": "Sleeper",
                "ExternalID": "900",
                "CanonicalPlayerID": "NFLP-placeholder",
                "FirstObservedSeason": SEASON,
                "LastObservedSeason": SEASON,
                "Sources": [],
            }
        ]
        self.assertEqual([], _retire_transferred_claims([claim], mappings, [], SEASON))
        self.assertEqual(1, len(mappings))


class PlaceholderGsisUpgradeRepositoryTests(unittest.TestCase):
    def test_rebuilt_identities_leave_no_current_app_claim_on_a_placeholder_record(self):
        """Derived from repository data: no player names are wired in.

        For every ESB value that occurs on exactly two rebuilt records, one with a
        valid GSIS and one with a placeholder or missing GSIS and no disagreeing
        shared provider ID, the current Sleeper/Tank01 app claim must sit on the
        valid record.
        """
        root = Path(__file__).resolve().parents[2]
        datasets = {dataset.id: dataset for dataset in load_registry(root)}
        rebuilt, _, _, _, _ = build_identities(root, datasets)

        valid_gsis = re.compile(r"^00-\d{7}$")
        esb_counts = Counter(
            (record.get("IDs") or {}).get("ESB")
            for record in rebuilt
            if (record.get("IDs") or {}).get("ESB")
        )
        by_esb: dict[str, list[dict]] = {}
        for record in rebuilt:
            esb = (record.get("IDs") or {}).get("ESB")
            if esb and esb_counts[esb] == 2:
                by_esb.setdefault(esb, []).append(record)

        stuck = []
        for esb, pair in by_esb.items():
            valid = [r for r in pair if valid_gsis.match((r["IDs"].get("GSIS") or ""))]
            placeholder = [r for r in pair if r not in valid]
            if len(valid) != 1 or len(placeholder) != 1:
                continue
            shared = (set(valid[0]["IDs"]) & set(placeholder[0]["IDs"])) - {"GSIS"}
            if any(valid[0]["IDs"][k] != placeholder[0]["IDs"][k] for k in shared):
                continue
            if any(placeholder[0]["IDs"].get(k) for k in ("Sleeper", "Tank01")):
                stuck.append(esb)
        self.assertEqual([], stuck)


if __name__ == "__main__":
    unittest.main()
