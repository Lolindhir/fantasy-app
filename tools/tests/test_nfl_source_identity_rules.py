import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.canonical_identity import provider_mapping_lookup
from nfl_source_data_lib.identity import (
    IdentityCandidate,
    _can_merge_on_anchor,
    _seed_for_component,
)


def candidate(ids, birth_date="2000-01-01", name="Test Player", source="test"):
    return IdentityCandidate(
        ids=ids,
        name=name,
        first_name=None,
        last_name=None,
        birth_date=birth_date,
        position="WR",
        latest_team=None,
        source=source,
        priority=10,
    )


class NflSourceIdentityRuleTests(unittest.TestCase):
    def test_espn_alias_accepts_one_other_strong_corroborator(self):
        left = candidate({"PFR": "Same00", "ESPN": "111"})
        right = candidate({"PFR": "Same00", "ESPN": "222"})
        self.assertTrue(_can_merge_on_anchor(left, right, "PFR"))

    def test_pfr_alias_requires_two_other_strong_corroborators(self):
        left = candidate({"GSIS": "00-1", "ESPN": "111", "PFR": "Old00"})
        right = candidate({"GSIS": "00-1", "ESPN": "111", "PFR": "New00"})
        self.assertTrue(_can_merge_on_anchor(left, right, "GSIS"))

        weak_left = candidate({"GSIS": "00-1", "PFR": "Old00"})
        weak_right = candidate({"GSIS": "00-1", "PFR": "New00"})
        self.assertFalse(_can_merge_on_anchor(weak_left, weak_right, "GSIS"))

    def test_birthdate_conflict_never_merges_shared_anchor(self):
        left = candidate({"GSIS": "00-1", "PFR": "Same00"}, "1980-01-01")
        right = candidate({"GSIS": "00-1", "PFR": "Same00"}, "1990-01-01")
        self.assertFalse(_can_merge_on_anchor(left, right, "GSIS"))

    def test_persisted_birthdate_correction_requires_three_matching_strong_anchors(self):
        existing = candidate(
            {"GSIS": "00-1", "ESPN": "111", "PFF": "222"},
            "1980-01-01",
            source="canonical-existing",
        )
        current = candidate(
            {"GSIS": "00-1", "ESPN": "111", "PFF": "222"},
            "1990-01-01",
            source="nflverse.players",
        )
        self.assertTrue(_can_merge_on_anchor(existing, current, "GSIS"))

        two_anchor_current = candidate(
            {"GSIS": "00-1", "ESPN": "111"},
            "1990-01-01",
            source="nflverse.players",
        )
        self.assertFalse(_can_merge_on_anchor(existing, two_anchor_current, "GSIS"))

    def test_current_birthdate_conflict_still_fails_closed_with_three_matching_anchors(self):
        left = candidate(
            {"GSIS": "00-1", "ESPN": "111", "PFF": "222"},
            "1980-01-01",
            source="nflverse.players",
        )
        right = candidate(
            {"GSIS": "00-1", "ESPN": "111", "PFF": "222"},
            "1990-01-01",
            source="test-current-provider",
        )
        self.assertFalse(_can_merge_on_anchor(left, right, "GSIS"))

    def test_component_seed_disambiguates_shared_provider_id(self):
        old_player = candidate({"GSIS": "00-shared", "PFR": "Old00"}, "1980-01-01", "Old Player")
        new_player = candidate({"GSIS": "00-shared", "PFR": "New00"}, "1990-01-01", "New Player")
        self.assertNotEqual(_seed_for_component([old_player]), _seed_for_component([new_player]))

    def test_provider_mapping_lookup_is_season_aware(self):
        payload = {
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1000",
                    "CanonicalPlayerID": "NFLP-old",
                    "FirstObservedSeason": 2024,
                    "LastObservedSeason": 2028,
                },
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1000",
                    "CanonicalPlayerID": "NFLP-new",
                    "FirstObservedSeason": 2036,
                    "LastObservedSeason": 2038,
                },
            ],
            "Conflicts": [],
        }
        self.assertEqual("NFLP-old", provider_mapping_lookup(payload, "Sleeper", "1000", 2026))
        self.assertIsNone(provider_mapping_lookup(payload, "Sleeper", "1000", 2030))
        self.assertEqual("NFLP-new", provider_mapping_lookup(payload, "Sleeper", "1000", 2037))

    def test_provider_mapping_lookup_fails_closed_during_conflict(self):
        payload = {
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "133",
                    "CanonicalPlayerID": "NFLP-a",
                    "FirstObservedSeason": 2026,
                    "LastObservedSeason": 2026,
                }
            ],
            "Conflicts": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "133",
                    "CanonicalPlayerIDs": ["NFLP-a", "NFLP-b"],
                    "FirstObservedSeason": 2026,
                    "LastObservedSeason": 2026,
                    "Status": "ambiguous",
                }
            ],
        }
        self.assertIsNone(provider_mapping_lookup(payload, "Sleeper", "133", 2026))


if __name__ == "__main__":
    unittest.main()
