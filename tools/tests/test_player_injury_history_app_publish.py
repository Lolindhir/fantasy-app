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

PRODUCT = "nfl-player-availability-v3"


def record(pid, week, state="played", team="AAA"):
    return {"Week": week, "CanonicalPlayerID": pid, "Team": team, "GameType": "REG", "GameID": None, "State": state,
            "Available": "no", "Played": False,
            "Participation": {"State": "played", "Evidence": "snap-counts"}, "Report": None, "Roster": {"Status": "RES", "Code": "R01"}}


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

    def test_only_fantasy_relevant_weeks_are_published(self):
        post = dict(record("NFLP-a", 2), GameType="POST")
        seasons = {2024: season_doc(2024, [record("NFLP-a", 17), record("NFLP-a", 18), post]),
                   2010: season_doc(2010, [record("NFLP-a", 17), record("NFLP-a", 18)])}
        doc = publisher.build_document(seasons, [{"ID": "S1"}], {"S1": "NFLP-a"}, {2024: 17})
        by_season = {s["Season"]: [w["Week"] for w in s["Weeks"]] for s in doc["Players"][0]["Seasons"]}
        self.assertEqual(by_season, {2024: [17]})

    def test_healthy_roster_weeks_of_v2_are_not_published(self):
        healthy = dict(record("NFLP-a", 5, "played"), Roster={"Status": "ACT", "Code": "A01"}, Available="yes", Played=True)
        scratch = dict(record("NFLP-a", 6, "healthy-scratch"), Roster={"Status": "INA", "Code": "I01"}, Available="yes", Played=False)
        reported = dict(healthy, Week=7, Report=[{"Game": "Questionable", "Practice": None, "Reasons": []}])
        doc = publisher.build_document({2024: season_doc(2024, [healthy, scratch, reported, record("NFLP-a", 8)])}, [{"ID": "S1"}], {"S1": "NFLP-a"})
        self.assertEqual([w["Week"] for w in doc["Players"][0]["Seasons"][0]["Weeks"]], [7, 8])
        self.assertNotIn("Available", doc["Players"][0]["Seasons"][0]["Weeks"][0])

    def test_league_week_caps_and_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            for season, ws in ((2024, {"ExpectedLastLeagueWeek": 17}), (2026, {"FinalLeagueWeek": 16, "ExpectedLastLeagueWeek": 17})):
                d = Path(tmp) / "data-source" / "leagues" / "x" / "seasons" / str(season)
                d.mkdir(parents=True)
                (d / "league.json").write_text(json.dumps({"WeekStructure": ws}))
            caps = publisher.league_week_caps(Path(tmp))
        self.assertEqual(caps, {2024: 17, 2026: 16})
        self.assertIsNone(publisher._cap_for(2015, caps))
        self.assertEqual(publisher._cap_for(2027, caps), 16)
        self.assertIsNone(publisher._cap_for(2015, {}))

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
