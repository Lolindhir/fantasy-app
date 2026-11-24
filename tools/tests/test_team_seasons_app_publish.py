"""Fast cases for the TeamSeasons App generator (Issue #774): pure rendering of the league-teams product, no derivation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import team_seasons_app_publish as publisher  # noqa: E402
from derived_data import league_teams_path  # noqa: E402
from data_roots import data_derived_dir  # noqa: E402
from app_delivery import Writer  # noqa: E402

LEAGUE = "test-league"


def product():
    team = {"TeamID": "1", "OwnerID": "u1", "Owner": "Ann", "OwnerAvatar": None, "TeamName": "Alpha", "TeamNameSource": "provider",
            "TeamAbbr": "ALP", "TeamAvatar": None}
    return {"SchemaVersion": 1, "Product": "league-teams", "CanonicalLeagueID": LEAGUE, "CurrentSeason": "2025",
            "Seasons": [{"Season": "2024", "Teams": [team]}, {"Season": "2025", "Teams": [dict(team, TeamName="Beta", TeamAbbr="BET")]}]}


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "public" / "data").mkdir(parents=True)
        path = league_teams_path(data_derived_dir(self.root), LEAGUE)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(product()), encoding="utf-8")

    def write(self):
        writer = Writer(self.root, datetime(2026, 11, 23, tzinfo=timezone.utc))
        publisher.publish(self.root, LEAGUE, writer)
        return writer.finish()

    def test_app_file_equals_product_and_second_run_is_noop(self):
        self.assertEqual(self.write(), ["public/data/TeamSeasons.json", "public/data/Timestamps.json"])
        written = json.loads((self.root / "public" / "data" / "TeamSeasons.json").read_text(encoding="utf-8"))
        self.assertEqual(written, product())
        self.assertIn("TeamSeasons", json.loads((self.root / "public" / "data" / "Timestamps.json").read_text(encoding="utf-8")))
        self.assertEqual(self.write(), [])

    def test_missing_product_fails_closed(self):
        league_teams_path(data_derived_dir(self.root), LEAGUE).unlink()
        with self.assertRaises(publisher.LeagueTeamsError):
            self.write()


if __name__ == "__main__":
    unittest.main()
