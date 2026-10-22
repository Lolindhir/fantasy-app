"""Fast read-only identity guards over the persisted canonical state (Issue #1122).

The full real-source replay (test_nfl_source_historical_identity_replay.py) stays
the Deep proof that a clean rebuild reproduces these files. These checks catch
the most common identity regressions of a pull request in seconds, without any
materialization: duplicate or dangling canonical IDs, provider tokens claimed by
two people, overlapping provider-mapping validity spans and weekly roster rows
without an owner. Nothing here names a player; every check discovers its data.
"""
from __future__ import annotations

import json
import re
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITIES = ROOT / "data-source/nfl/identities"
# Providers whose primary token identifies exactly one person (ADR-025). Other
# providers (MFL, CBS, ...) are known to be ambiguous and are quarantined as
# Conflicts in provider-mappings.json instead.
ANCHOR_PROVIDERS = ("GSIS", "Sleeper", "ESPN", "PFR", "PFF", "Yahoo")
CANONICAL_ID = re.compile(r"^NFLP-[0-9a-f]{20}$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@unittest.skipUnless((IDENTITIES / "players.json").is_file(), "Requires persisted canonical NFL identities")
class PersistedIdentityInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.players = load(IDENTITIES / "players.json")["Players"]
        cls.mappings = load(IDENTITIES / "provider-mappings.json")
        cls.ids = {row["CanonicalPlayerID"] for row in cls.players}

    def test_canonical_ids_are_unique_and_well_formed(self):
        listed = [row["CanonicalPlayerID"] for row in self.players]
        self.assertEqual(len(listed), len(self.ids), "Duplicate CanonicalPlayerID")
        self.assertEqual([], [i for i in listed if not CANONICAL_ID.match(i)])

    def test_anchor_provider_tokens_have_exactly_one_owner(self):
        owners = defaultdict(set)
        for row in self.players:
            for provider in ANCHOR_PROVIDERS:
                token = (row.get("IDs") or {}).get(provider)
                if token:
                    owners[(provider, str(token))].add(row["CanonicalPlayerID"])
        shared = {key: sorted(value) for key, value in owners.items() if len(value) > 1}
        self.assertEqual({}, dict(list(shared.items())[:5]), "Anchor provider token claimed by several people")

    def test_provider_mappings_reference_existing_players_with_valid_spans(self):
        mappings = self.mappings["Mappings"]
        self.assertEqual([], [m for m in mappings if m["CanonicalPlayerID"] not in self.ids][:5])
        self.assertEqual([], [m for m in mappings
                              if int(m["FirstObservedSeason"]) > int(m["LastObservedSeason"])][:5])

    def test_no_provider_token_has_overlapping_spans_for_different_people(self):
        spans = defaultdict(list)
        for m in self.mappings["Mappings"]:
            spans[(m["Provider"], str(m["ExternalID"]))].append(
                (int(m["FirstObservedSeason"]), int(m["LastObservedSeason"]), m["CanonicalPlayerID"]))
        overlaps = []
        for key, rows in spans.items():
            rows.sort()
            for before, after in zip(rows, rows[1:]):
                if after[0] <= before[1] and after[2] != before[2]:
                    overlaps.append((key, before, after))
        self.assertEqual([], overlaps[:5], "A provider token maps to two people in the same season")

    def test_quarantined_conflicts_are_resolvable_and_never_silently_merged(self):
        for conflict in self.mappings["Conflicts"]:
            with self.subTest(provider=conflict["Provider"], external=conflict["ExternalID"]):
                owners = conflict["CanonicalPlayerIDs"]
                self.assertGreaterEqual(len(set(owners)), 2)
                self.assertTrue(set(owners) <= self.ids)
                self.assertEqual("ambiguous", conflict["Status"])

    def test_weekly_roster_rows_have_an_existing_canonical_owner(self):
        files = sorted((ROOT / "data-source/nfl/weekly-rosters").glob("*/*.json"))
        self.assertTrue(files, "No weekly roster partitions found")
        unowned = []
        for path in files:
            for row in load(path)["Records"]:
                if row.get("CanonicalPlayerID") not in self.ids:
                    unowned.append((path.name, row.get("CanonicalPlayerID")))
        self.assertEqual([], unowned[:5], "Weekly roster rows without a canonical identity")


if __name__ == "__main__":
    unittest.main()
