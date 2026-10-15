"""One-off read-only real-data historical PWF W03 reconstruction audit (#697).

Remove after validation; this test is not part of the permanent main suite.
It uses the production PlayerWeekFantasy builder, never the JSON writer.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT  # noqa: E402
from player_week_fantasy_materialize import build_player_week_fantasy_dataset  # noqa: E402


class HistoricalPlayerWeekFantasyAudit(unittest.TestCase):
    def test_rebuild_2026_w03_from_canonical_sources_without_writes(self) -> None:
        season, week, league = 2026, 3, "nfl-reise"
        existing = json.loads((ROOT / DATA_DERIVED_ROOT / "player-week-fantasy"
                               / league / str(season) / f"{week:02d}.json").read_text())
        matchups = json.loads((ROOT / DATA_SOURCE_ROOT / "leagues" / league
                               / "seasons" / str(season) / "matchups"
                               / f"week-{week}.json").read_text())
        # No write_dataset, no changed derived or app partitions.
        model = build_player_week_fantasy_dataset(
            ROOT, league_id=league, season=season, week=week
        )
        self.assertEqual(model["CanonicalLeagueID"], league)
        self.assertEqual(model["Season"], season)
        self.assertEqual(model["Week"], week)
        self.assertEqual(model["ScoringProfile"]["SettingsHash"],
                         existing["ScoringProfile"]["SettingsHash"])
        records = {r["CanonicalPlayerID"]: r for r in model["Records"]}
        self.assertEqual(len(records), len(model["Records"]))
        missing_zero, compared, errors, nonfinal = 0, 0, [], []
        seen = set()
        for team in matchups:
            for player in team["PlayerPoints"]:
                pid = player["Player"]["CanonicalPlayerID"]
                self.assertNotIn(pid, seen, f"Duplicate fantasy matchup player: {pid}")
                seen.add(pid)
                league_points = float(player["Points"])
                record = records.get(pid)
                if record is None:
                    if league_points:
                        errors.append({"id": pid, "why": "missing-nonzero", "league": league_points})
                    else:
                        missing_zero += 1
                    continue
                actual = record["Actual"]
                if actual["State"] != "final" or actual["Points"] is None:
                    nonfinal.append({"id": pid, "state": actual["State"], "league": league_points})
                    continue
                observed = float(actual["Points"])
                if not math.isfinite(observed) or abs(observed - league_points) > .010001:
                    errors.append({"id": pid, "why": "mismatch", "league": league_points, "pwf": observed})
                compared += 1
        old = {r["CanonicalPlayerID"]: r["Actual"] for r in existing["Records"]}
        changed = sum(
            1 for r in model["Records"]
            if old.get(r["CanonicalPlayerID"]) != r["Actual"]
        )
        report = {
            "league": league, "season": season, "week": week,
            "generated": len(model["Records"]), "fantasyOwned": len(seen),
            "compared": compared, "missingZero": missing_zero,
            "nonFinal": len(nonfinal), "invalid": len(errors),
            "oldUnavailable": sum(r["Actual"]["State"] == "unavailable"
                                  for r in existing["Records"]),
            "newActualStateCounts": model["Materialization"]["ActualStateCounts"],
            "newActualEvidenceFinal": model["Materialization"]["ActualScoringEvidenceFinalized"],
            "changedActualRows": changed,
            "firstInvalid": errors[:10], "firstNonFinal": nonfinal[:10],
        }
        print("PWF_W3_READONLY_AUDIT=" + json.dumps(report, sort_keys=True), flush=True)
        self.assertTrue(model["Materialization"]["ActualScoringEvidenceFinalized"])
        self.assertGreater(compared, 0)
        self.assertEqual(nonfinal, [], "Canonical roster contains non-final rebuilt PWF Actual")
        self.assertEqual(errors, [], "PWF scores disagree with canonical fantasy matchups")


if __name__ == "__main__":
    unittest.main()
