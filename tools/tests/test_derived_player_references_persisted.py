"""Fast read-only guard: persisted Shared Derived products reference real players (Issue #1122).

PlayerWeekFantasy and TeamWeekPerformance are rebuilt from canonical facts by
the Deep restore tests. This cheap check catches a pull request that leaves a
derived partition pointing at a CanonicalPlayerID the identity layer no longer
knows, which would otherwise surface only in the full audit.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITIES = ROOT / "data-source/nfl/identities/players.json"
CANONICAL_ID = re.compile(r"NFLP-[0-9a-f]{20}")


@unittest.skipUnless(IDENTITIES.is_file(), "Requires persisted canonical NFL identities")
class DerivedProductsReferenceExistingPlayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        players = json.loads(IDENTITIES.read_text(encoding="utf-8"))["Players"]
        cls.ids = {row["CanonicalPlayerID"] for row in players}

    def check(self, pattern: str):
        files = sorted(ROOT.glob(pattern))
        for path in files:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                referenced = set(CANONICAL_ID.findall(path.read_text(encoding="utf-8")))
                self.assertEqual([], sorted(referenced - self.ids)[:5])
        return files

    def test_player_week_fantasy_partitions_reference_known_players(self):
        for path in self.check("data-derived/player-week-fantasy/*/*/*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(path=path.name):
                self.assertTrue(data["Records"], "Empty PlayerWeekFantasy partition")
                keys = [row["CanonicalPlayerID"] for row in data["Records"]]
                self.assertEqual(len(keys), len(set(keys)), "Duplicate player in one week")

    def test_team_week_performance_partitions_reference_known_players(self):
        self.check("data-derived/team-week-performance/*/*/*.json")


if __name__ == "__main__":
    unittest.main()
