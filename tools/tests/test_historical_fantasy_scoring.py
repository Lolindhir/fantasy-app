from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_fantasy_scoring import score_record  # noqa: E402


class HistoricalFantasyScoringTests(unittest.TestCase):
    def test_skill_player_can_be_rescored_with_explicit_profile(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {
                "receptions": 8,
                "receiving_yards": 125,
                "receiving_tds": 1,
                "rushing_yards": 4,
                "rushing_tds": 0,
                "receiving_fumbles_lost": 0,
            },
        }
        scoring = {
            "rec": 1.0,
            "rec_yd": 0.1,
            "rec_td": 6.0,
            "rush_yd": 0.1,
            "rush_td": 6.0,
            "fum_lost": -2.0,
            "def_td": 6.0,
        }
        result = score_record(record, scoring)
        self.assertAlmostEqual(result["FantasyPoints"], 26.9)
        self.assertEqual(result["UnsupportedNonZeroSettings"], [])

    def test_profile_change_recalculates_without_changing_raw_facts(self) -> None:
        record = {
            "Position": "WR",
            "Stats": {"receptions": 10, "receiving_yards": 100, "receiving_tds": 0},
        }
        ppr = score_record(record, {"rec": 1.0, "rec_yd": 0.1})
        half_ppr = score_record(record, {"rec": 0.5, "rec_yd": 0.1})
        self.assertEqual(ppr["FantasyPoints"], 20.0)
        self.assertEqual(half_ppr["FantasyPoints"], 15.0)
        self.assertEqual(record["Stats"]["receptions"], 10)

    def test_missing_applicable_mapping_is_explicit(self) -> None:
        record = {"Position": "WR", "Stats": {"receiving_yards": 100}}
        result = score_record(record, {"bonus_rec_yd_100": 3.0})
        self.assertEqual(result["UnsupportedNonZeroSettings"], ["bonus_rec_yd_100"])


if __name__ == "__main__":
    unittest.main()
