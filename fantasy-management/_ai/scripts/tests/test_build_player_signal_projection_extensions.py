import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_player_signal_dataset_with_projection_extensions as module


SCORING = {
    "pass_yd": 0.04,
    "pass_td": 4,
    "pass_int": -1,
    "rush_yd": 0.1,
    "rush_td": 6,
    "rec": 1,
    "rec_yd": 0.1,
    "rec_td": 6,
    "pass_2pt": 2,
    "rush_2pt": 2,
    "rec_2pt": 2,
    "fum_lost": -2,
}


class ProjectionExtensionTests(unittest.TestCase):
    def test_qb_core_scoring_uses_league_multipliers(self):
        result = {
            "listed": True,
            "signals": {
                "pass_yards": 4000,
                "pass_touchdowns": 30,
                "interceptions": 10,
                "rush_yards": 500,
                "rush_touchdowns": 5,
            },
        }
        view = module.league_scoring_view("QB", result, SCORING)
        self.assertEqual("reconciled_core", view["status"])
        self.assertEqual(350.0, view["core_points"])
        self.assertEqual(
            {"pass_2pt", "rush_2pt", "fum_lost"},
            {item["scoring_key"] for item in view["excluded_nonzero_components"]},
        )

    def test_rb_ppr_core_scoring(self):
        result = {
            "listed": True,
            "signals": {
                "rush_yards": 1000,
                "rush_touchdowns": 8,
                "receptions": 50,
                "receiving_yards": 400,
                "receiving_touchdowns": 2,
            },
        }
        view = module.league_scoring_view("RB", result, SCORING)
        self.assertEqual(250.0, view["core_points"])

    def test_missing_core_stat_fails_closed(self):
        result = {"listed": True, "signals": {"receptions": 80, "receiving_yards": 1000}}
        view = module.league_scoring_view("TE", result, SCORING)
        self.assertEqual("incomplete_core_stats", view["status"])
        self.assertIsNone(view["core_points"])
        self.assertIn("receiving_touchdowns", view["missing_core_stats"])

    def test_unlisted_provider_never_gets_inferred_points(self):
        view = module.league_scoring_view("WR", {"listed": False, "signals": {}}, SCORING)
        self.assertEqual("not_listed", view["status"])
        self.assertIsNone(view["core_points"])


if __name__ == "__main__":
    unittest.main()
