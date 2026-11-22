"""Fast cases for the InjuryImpact App generator (Issue #1621): pure reduction of the persisted product, no derivation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import injury_impact_app_publish as publisher  # noqa: E402


def document():
    team = {"CanonicalLeagueRosterID": "r1", "ProjectedBest": 10.0, "ProjectedBestHealthy": 8.0, "Impact": 2.0, "IsLowerBound": True,
            "HasUnknownEvidence": False, "Counts": {"Usable": 1}, "Injured": [{"CanonicalPlayerID": "P1", "SingleReturnImpact": 2.0}, {"CanonicalPlayerID": "P3", "SingleReturnImpact": 0.0}]}
    return {
        "Season": 2026, "Models": {"InjuryImpact": "injury-impact-v1"}, "AsOf": {"LeagueScoredWeek": 1},
        "Inputs": {"ScoringSettingsHash": "x"},
        "Weeks": [{"Week": 1, "Inputs": {"AvailabilityDigest": "d"}, "Teams": [team]}],
        "UnavailableWeeks": [{"Week": 2, "Reason": "no partition"}],
        "SeasonTotals": [{"CanonicalLeagueRosterID": "r1", "Impact": 2.0, "TopPlayers": [
            {"CanonicalPlayerID": "P1", "SingleReturnImpact": 2.0, "Weeks": 1},
            {"CanonicalPlayerID": "P2", "SingleReturnImpact": 1.0, "Weeks": 1}]}],
    }


class SlimSeasonTests(unittest.TestCase):
    def test_week_rows_keep_only_display_fields(self):
        slim = publisher.slim_season(document(), [{"CanonicalLeagueRosterID": "r1", "TeamID": 1}], {})
        self.assertEqual(slim["Weeks"], [{"Week": 1, "Teams": [{"CanonicalLeagueRosterID": "r1", "Impact": 2.0, "IsLowerBound": True, "HasUnknownEvidence": False, "CostlyPlayers": 1}]}])
        self.assertNotIn("Inputs", slim)
        self.assertEqual(slim["UnavailableWeeks"], [{"Week": 2, "Reason": "no partition"}])
        self.assertEqual(slim["SeasonTotals"], [{**document()["SeasonTotals"][0], "CostlyPlayersPerWeek": 1.0}])

    def test_player_refs_cover_every_top_player_and_never_drop_unknown_ones(self):
        profiles = {"P1": {"DisplayName": "A Player", "Position": "WR", "Headshot": None}}
        refs = publisher.slim_season(document(), [], profiles)["PlayerRefs"]
        self.assertEqual(refs["P1"], {"Name": "A Player", "Position": "WR", "Picture": None})
        self.assertEqual(refs["P2"], {"Name": None, "Position": None, "Picture": None})


if __name__ == "__main__":
    unittest.main()
