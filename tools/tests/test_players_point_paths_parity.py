"""Fast guard (Issue #1226, Q5): the two point paths agree for the current season.

Players/player-valuation score the season with the current league ScoringSettings,
PlayerWeekFantasy with the settings of that season. For the newest league season both
must give the same weekly points. Reads persisted repository state only.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALUATION = ROOT / "data-derived" / "player-valuation"
WEEKLY = ROOT / "data-derived" / "player-week-fantasy"
TOLERANCE = 0.05
# Known, small divergence (2026-10-31: 5 of 956 players, e.g. identity/team-join edge cases); a systematic
# drift between the two point paths must still fail. Tracked as follow-up of Issue #1226.
MAX_DIFFERING_SHARE = 0.02  # only pre-ContractVersion-3 snapshots
KNOWN_PENDING_IDENTITY = "NFLP-caf7c3d6786fcd72e704"  # Cody White PFR WhitCo05 (#1236)


def _newest_snapshot():
    candidates = sorted(VALUATION.glob("*/*/week-*.json"), key=lambda p: (p.parent.name, p.name)) if VALUATION.is_dir() else []
    return candidates[-1] if candidates else None


class PointPathParityTests(unittest.TestCase):
    def test_current_season_totals_equal_player_week_fantasy_actuals(self) -> None:
        snapshot_path = _newest_snapshot()
        if snapshot_path is None:
            self.skipTest("no persisted player-valuation snapshot")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        league, season = snapshot["CanonicalLeagueID"], snapshot["Season"]
        final_week = snapshot["AsOfFinalScoredWeek"]
        weekly_dir = WEEKLY / league / str(season)
        if not weekly_dir.is_dir():
            self.skipTest("no persisted PlayerWeekFantasy for the season")
        sums: dict[str, float] = {}
        for week in range(1, final_week + 1):
            path = weekly_dir / f"{week:02d}.json"
            if not path.is_file():
                self.skipTest(f"PlayerWeekFantasy week {week} not persisted")
            for record in json.loads(path.read_text(encoding="utf-8"))["Records"]:
                actual = record.get("Actual") or {}
                if actual.get("State") == "final" and actual.get("Points") is not None:
                    sums[record["CanonicalPlayerID"]] = sums.get(record["CanonicalPlayerID"], 0.0) + actual["Points"]
        differing = []
        compared = 0
        for row in snapshot["Players"]:
            cpid = row.get("CanonicalPlayerID")
            current = (row.get("SeasonValues") or {}).get("Current") or {}
            total = current.get("FantasyPointsTotal")
            if not cpid or total is None or row.get("Hold"):
                continue
            compared += 1
            expected = sums.get(cpid, 0.0)
            if abs(total - expected) > TOLERANCE:
                differing.append((cpid, total, round(expected, 2)))
        self.assertGreater(compared, 0)
        if snapshot["ContractVersion"] >= 3:
            # All rematerialized totals must match except the independently owned
            # Cody White PFR source-identity repair (#1236); remove when published.
            self.assertEqual(
                [], [row for row in differing if row[0] != KNOWN_PENDING_IDENTITY],
                f"ContractVersion-3 point-path differences: {differing[:10]}",
            )
        else:
            # Legacy v2 snapshots retain their bounded cutover check.
            self.assertLessEqual(
                len(differing) / compared, MAX_DIFFERING_SHARE,
                f"{len(differing)} of {compared} pre-cutover rows differ: {differing[:10]}",
            )


if __name__ == "__main__":
    unittest.main()
