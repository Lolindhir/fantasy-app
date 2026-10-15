"""Read-only export of exact production-generated 2026 W5 PlayerWeekFantasy delta.

Diagnostic-only test for approved #697 backfill. No writer is called. The
existing test discovery runs the materializer on a complete checkout.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy_materialize import build_player_week_fantasy_dataset

TARGET = ROOT / "data-derived/player-week-fantasy/nfl-reise/2026/05.json"
MATCHUPS = ROOT / "data-source/leagues/nfl-reise/seasons/2026/matchups/week-5.json"


def git_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


class PlayerWeekFantasyWeek5BackfillExport(unittest.TestCase):
    def test_export_verified_materializer_delta_without_writing(self) -> None:
        original = TARGET.read_text(encoding="utf-8")
        stored = json.loads(original)
        fresh = build_player_week_fantasy_dataset(
            ROOT, league_id="nfl-reise", season=2026, week=5
        )
        self.assertEqual((fresh["CanonicalLeagueID"], fresh["Season"], fresh["Week"]),
                         ("nfl-reise", 2026, 5))
        self.assertEqual(fresh["ScoringProfile"], stored["ScoringProfile"])
        self.assertEqual(len(fresh["Records"]), 784)
        self.assertEqual(len(stored["Records"]), 784)
        facts = {}
        for team in json.loads(MATCHUPS.read_text(encoding="utf-8")):
            for row in team["PlayerPoints"]:
                player_id = row["Player"]["CanonicalPlayerID"]
                self.assertNotIn(player_id, facts)
                facts[player_id] = float(row["Points"])
        old = {r["CanonicalPlayerID"]: r["Actual"] for r in stored["Records"]}
        new = {r["CanonicalPlayerID"]: r["Actual"] for r in fresh["Records"]}
        stale = []
        for player_id, points in facts.items():
            if player_id not in new:
                self.assertAlmostEqual(points, 0.0, places=2)
                continue
            self.assertEqual(new[player_id]["State"], "final")
            self.assertAlmostEqual(float(new[player_id]["Points"]), points, places=2)
            if player_id in old and abs(float(old[player_id]["Points"]) - points) >= .010001:
                stale.append(player_id)
        self.assertEqual(len(facts), 204)
        self.assertEqual(len(stale), 10)
        serialized = json.dumps(fresh, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        before = original.splitlines(keepends=True)
        after = serialized.splitlines(keepends=True)
        sm = difflib.SequenceMatcher(None, before, after)
        patches = [
            [start, end, after[new_start:new_end]]
            for tag, start, end, new_start, new_end in sm.get_opcodes()
            if tag != "equal"
        ]
        payload = {
            "beforeSha": git_sha(original.encode("utf-8")),
            "afterSha": git_sha(serialized.encode("utf-8")),
            "patches": patches,
        }
        wire = base64.b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")
        print("PWF_BACKFILL_META=" + json.dumps({
            "oldSha": payload["beforeSha"], "newSha": payload["afterSha"],
            "deltaHunks": len(patches), "wireChars": len(wire),
            "storedDifferences": len(stale), "freshDifferences": 0,
            "scoringSettingsHash": fresh["ScoringProfile"]["SettingsHash"],
            "records": len(fresh["Records"]), "sourcePlayers": len(facts),
        }, sort_keys=True), flush=True)
        for i in range(0, len(wire), 3000):
            print("PWF_BACKFILL_PART=" + wire[i:i+3000], flush=True)
        self.assertTrue(patches)


if __name__ == "__main__":
    unittest.main()
