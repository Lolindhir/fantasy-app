"""Real-source integration gate for #355 (requires pwsh and canonical repo data).

This test runs only on an environment with the production PowerShell bridge.
It must never publish derived data, even for a final historical week.
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from team_week_performance import build_team_week_performance  # noqa: E402
from team_week_performance_sources import (  # noqa: E402
    load_verified_week_inputs,
    resolve_slots_from_existing_rules,
)

REPO_ROOT = TOOLS.parent


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell CLI is required for real-source integration")
class TeamWeekPerformanceIntegrationTests(unittest.TestCase):
    def test_real_2024_slot_bridge_preserves_special_flex(self) -> None:
        league_path = REPO_ROOT / "source-data/leagues/nfl-reise/seasons/2024/league.json"
        slots = resolve_slots_from_existing_rules(
            REPO_ROOT, league_path,
            {"qb": "QB", "rb": "RB", "wr": "WR", "te": "TE", "k": "K"},
        )
        self.assertEqual(len(slots), 12)
        by_name = {slot.slot_id: slot.eligible_positions for slot in slots}
        self.assertEqual(by_name["WRRB_FLEX-1"], frozenset({"RB", "WR"}))
        self.assertEqual(by_name["REC_FLEX-1"], frozenset({"WR", "TE"}))
        self.assertEqual(by_name["FLEX-1"], frozenset({"RB", "WR", "TE"}))
        self.assertEqual(by_name["K-1"], frozenset({"K"}))

    def test_real_final_weeks_match_independent_shadow_audit(self) -> None:
        # Independent full-roster, position-constrained DP audit values.
        cases = [
            (2024, 14, 246.58, 90.9201),
            (2025, 8, 250.38, 90.1538),
            (2026, 3, 258.38, 92.7319),
            (2026, 4, 304.34, 85.5761),
            (2026, 5, 264.50, 93.8913),
        ]
        for season, week, best_potential, coach_percent in cases:
            with self.subTest(season=season, week=week):
                inputs = load_verified_week_inputs(REPO_ROOT, "nfl-reise", season, week)
                result = build_team_week_performance(**inputs)
                self.assertEqual(len(result["Teams"]), inputs["expected_team_count"])
                self.assertEqual(max(t["PotentialPoints"] for t in result["Teams"]), best_potential)
                self.assertEqual(max(t["EfficiencyPercent"] for t in result["Teams"]), coach_percent)
                for team in result["Teams"]:
                    self.assertLessEqual(team["ActualStarterPoints"], team["PotentialPoints"])
                    self.assertAlmostEqual(
                        team["ActualStarterPoints"], team["OfficialMatchupPoints"], places=2
                    )
                self.assertTrue(result["Awards"]["BestManagerRosterIDs"])
                self.assertTrue(result["Awards"]["BestCoachRosterIDs"])


if __name__ == "__main__":
    unittest.main()
