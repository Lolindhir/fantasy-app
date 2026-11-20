"""Fast cases for the PlayerInjuryHistory App generator (Issue #1590): pure reshaping, no derivation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import player_injury_history_app_publish as publisher  # noqa: E402

PRODUCT = "nfl-player-availability-v1"


def record(pid, week, state="played", team="AAA"):
    return {"Week": week, "CanonicalPlayerID": pid, "Team": team, "GameType": "REG", "GameID": None, "State": state,
            "Participation": {"State": "played", "Evidence": "snap-counts"}, "Report": None, "Roster": None}


def season_doc(season, records, reports=True):
    return {"ProductVersion": PRODUCT, "Season": season,
            "Inputs": {"InjuryProduct": {"ProductVersion": "nfl-injuries-v1"} if reports else None, "RosterStatusAvailable": True, "SnapCountsAvailable": True},
            "Records": records}


class PublisherTests(unittest.TestCase):
    def test_only_players_in_players_json_are_published_and_grouped_by_season(self):
        bridge = {"S1": "NFLP-a", "S2": "NFLP-b"}
        seasons = {
            2024: season_doc(2024, [record("NFLP-a", 3), record("NFLP-b", 1), record("NFLP-c", 1)]),
            2025: season_doc(2025, [record("NFLP-a", 9), record("NFLP-a", 2)], reports=False),
        }
        doc = publisher.build_document(seasons, [{"ID": "S1"}, {"ID": "S9"}], bridge)
        self.assertEqual([p["ID"] for p in doc["Players"]], ["S1"])
        self.assertEqual([s["Season"] for s in doc["Players"][0]["Seasons"]], [2024, 2025])
        self.assertEqual([w["Week"] for w in doc["Players"][0]["Seasons"][1]["Weeks"]], [2, 9])
        self.assertEqual(doc["Coverage"][1]["ReportsAvailable"], False)
        self.assertEqual(doc["Players"][0]["Seasons"][0]["Weeks"][0]["State"], "played")

    def test_state_is_copied_not_derived(self):
        seasons = {2024: season_doc(2024, [record("NFLP-a", 1, "unknown")])}
        doc = publisher.build_document(seasons, [{"ID": "S1"}], {"S1": "NFLP-a"})
        self.assertEqual(doc["Players"][0]["Seasons"][0]["Weeks"][0]["State"], "unknown")

    def test_ambiguous_sleeper_identity_fails_closed(self):
        with self.assertRaises(publisher.InjuryHistoryError):
            publisher.sleeper_to_canonical({"Players": [
                {"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "S1"}}, {"CanonicalPlayerID": "NFLP-b", "IDs": {"Sleeper": "S1"}}]})

    def test_unsupported_product_version_fails_closed(self):
        bad = season_doc(2024, [])
        bad["ProductVersion"] = "other"
        with self.assertRaises(publisher.InjuryHistoryError):
            publisher.build_document({2024: bad}, [], {})

    def test_write_is_semantic_no_op_on_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data-derived" / "nfl-player-availability").mkdir(parents=True)
            (root / "data-derived" / "nfl-player-availability" / "2024.json").write_text(json.dumps(season_doc(2024, [record("NFLP-a", 1)])))
            (root / "public" / "data").mkdir(parents=True)
            (root / "public" / "data" / "Players.json").write_text(json.dumps([{"ID": "S1"}]))
            ident = root / "data-source" / "nfl" / "identities"
            ident.mkdir(parents=True)
            (ident / "players.json").write_text(json.dumps({"Players": [{"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "S1"}}]}))
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            first = publisher.CompactWriter(root, now)
            publisher.publish(root, first)
            self.assertIn("public/data/PlayerInjuryHistory.json", first.finish())
            second = publisher.CompactWriter(root, now)
            publisher.publish(root, second)
            self.assertEqual(second.finish(), [])


if __name__ == "__main__":
    unittest.main()
