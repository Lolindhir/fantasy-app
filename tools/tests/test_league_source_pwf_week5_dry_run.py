"""Non-writing Week-5 PlayerWeekFantasy recomputation diagnostic (Refs #697/#355).

This test deliberately calls only the pure dataset builder and never calls the
writer or App publisher. Its diagnostic output distinguishes stale stored Actual
values from a materializer/scoring error using current canonical matchup facts.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy_materialize import build_player_week_fantasy_dataset  # noqa: E402

SOURCE = ROOT / "source-data/leagues/nfl-reise/seasons/2026/matchups/week-5.json"
STORED = ROOT / "derived-data/player-week-fantasy/nfl-reise/2026/05.json"
TOLERANCE = 0.010001


class PlayerWeekFantasyWeek5DryRun(unittest.TestCase):
    def test_current_inputs_regenerate_final_matchup_actuals_without_writing(self) -> None:
        canonical = json.loads(SOURCE.read_text(encoding="utf-8"))
        stored = json.loads(STORED.read_text(encoding="utf-8"))
        self.assertEqual(stored["Season"], 2026)
        self.assertEqual(stored["Week"], 5)
        # No call to write_dataset or App publisher. The in-memory result is
        # intentionally discarded at the end of the test.
        fresh = build_player_week_fantasy_dataset(
            ROOT, league_id="nfl-reise", season=2026, week=5
        )
        self.assertEqual(fresh["Season"], 2026)
        self.assertEqual(fresh["Week"], 5)
        self.assertEqual(fresh["ScoringProfile"], stored["ScoringProfile"])
        original = {r["CanonicalPlayerID"]: r["Actual"] for r in stored["Records"]}
        rebuilt = {r["CanonicalPlayerID"]: r["Actual"] for r in fresh["Records"]}
        facts = {}
        for team in canonical:
            for row in team["PlayerPoints"]:
                player_id = row["Player"]["CanonicalPlayerID"]
                self.assertNotIn(player_id, facts)
                facts[player_id] = float(row["Points"])
        old_differences = []
        fresh_differences = []
        missing_nonzero = []
        for player_id, official_points in facts.items():
            if player_id in original and original[player_id]["State"] == "final":
                old_points = float(original[player_id]["Points"])
                if abs(old_points - official_points) > TOLERANCE:
                    old_differences.append([player_id, old_points, official_points])
            actual = rebuilt.get(player_id)
            if actual is None:
                if abs(official_points) > TOLERANCE:
                    missing_nonzero.append([player_id, official_points])
                continue
            if actual["State"] != "final":
                fresh_differences.append([player_id, actual, official_points])
                continue
            if abs(float(actual["Points"]) - official_points) > TOLERANCE:
                fresh_differences.append([player_id, actual["Points"], official_points])
        print("PWF_WEEK5_DRY_RUN_SUMMARY=" + json.dumps({
            "sourcePlayers": len(facts),
            "storedRecords": len(original),
            "freshRecords": len(rebuilt),
            "storedDiscrepancies": len(old_differences),
            "freshDiscrepancies": len(fresh_differences),
            "freshMissingWithNonzeroPoints": len(missing_nonzero),
            "storedSample": sorted(old_differences)[:12],
            "freshSample": sorted(fresh_differences)[:12],
            "missingNonzeroSample": sorted(missing_nonzero)[:12],
        }, sort_keys=True), flush=True)
        self.assertEqual(fresh_differences, [], "Current materializer disagrees with canonical matchup points")
        self.assertEqual(missing_nonzero, [], "Current materializer omits scored matchup players")


if __name__ == "__main__":
    unittest.main()
