"""Fast checks of the league-standings App rendering and the shadow comparison (ADR-072, Issue #987 step 3)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import league_standings_app_publish as app  # noqa: E402


def regular(team_id, place, moves=True):
    row = {"Place": place, "PlaceOrdinal": f"{place}th", "TeamID": team_id, "Owner": f"o{team_id}", "TeamName": f"t{team_id}", "Wins": 3}
    if moves:
        row.update({"PreviousWeekPlace": place + 1, "PlaceDelta": 1, "WeeklyMovements": [{"Week": 2}]})
    return row


def playoff(team_id, place):
    return {"Place": place, "TeamID": team_id, "Owner": f"o{team_id}", "OwnerAvatarID": f"av{team_id}",
            "TeamName": f"t{team_id}", "TeamAvatar": None, "PlaceType": "Playoffs", "PlaceOrdinal": f"{place}th"}


def award(team_id):
    return {"Name": "Best Performer", "Type": "x", "IconUnicode": "i", "StatDisplay": "1", "TeamID": team_id, "Owner": f"o{team_id}", "TeamName": f"t{team_id}"}


def document(season, with_movement):
    return {
        "RegularSeason": [regular(1, 1, with_movement), regular(2, 2, with_movement)],
        "Playoffs": [playoff(1, 1), playoff(2, 2)],
        "Awards": [award(1)],
        "AllTime": {"ThroughSeason": season, "Playoffs": [{"Place": 1, "TeamID": 1, "Owner": "o1", "TeamName": "t1"}],
                    "RegularSeason": [regular(1, 1, False)]},
    }


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.documents = {2024: document(2024, True), 2025: document(2025, True)}

    def test_order_and_movement_only_for_current_season(self):
        rendered = app.render_standings(self.documents, 2025)
        self.assertEqual(["AllTime", "2025", "2024"], [s["Season"] for s in rendered])
        self.assertIn("WeeklyMovements", rendered[1]["RegularSeason"][0])
        for field in app.MOVEMENT_FIELDS:
            self.assertNotIn(field, rendered[2]["RegularSeason"][0])
        self.assertNotIn("Awards", rendered[0])

    def test_avatar_id_becomes_cdn_url_and_is_not_kept(self):
        row = app.render_standings(self.documents, 2025)[1]["Playoffs"][0]
        self.assertEqual("https://sleepercdn.com/avatars/av1", row["OwnerAvatar"])
        self.assertNotIn("OwnerAvatarID", row)

    def test_all_time_comes_from_newest_document(self):
        self.documents[2025]["AllTime"]["ThroughSeason"] = 2025
        self.documents[2025]["AllTime"]["Playoffs"][0]["Place"] = 7
        self.assertEqual(7, app.render_standings(self.documents, 2025)[0]["Playoffs"][0]["Place"])

    def test_empty_documents_fail(self):
        with self.assertRaises(ValueError):
            app.render_standings({}, 2025)

    def test_placements_keys_and_identity_stripping(self):
        rendered = app.render_standings(self.documents, 2025)
        placements = app.render_placements(rendered, [1, 2], 2025)
        self.assertEqual({"AllTime", "Current", "Previous"}, set(placements[1]))
        current = placements[1]["Current"]
        for field in app.IDENTITY_FIELDS:
            self.assertNotIn(field, current["Playoffs"])
            self.assertNotIn(field, current["Regular"])
        self.assertEqual(["Best Performer"], [a["Name"] for a in current["Awards"]])
        self.assertEqual([], placements[2]["Current"]["Awards"])
        self.assertNotIn("TeamID", current["Awards"][0])


class DifferenceTests(unittest.TestCase):
    def test_numbers_compare_by_value(self):
        self.assertEqual([], app.difference({"a": 3.0, "b": [1, 2]}, {"b": [1, 2.0], "a": 3}))

    def test_bool_is_not_a_number(self):
        self.assertTrue(app.difference(True, 1))

    def test_reports_keys_types_length_and_values(self):
        found = app.difference({"a": 1, "b": "x", "c": [1]}, {"a": 2, "d": 1, "b": 1, "c": [1, 2]})
        text = "\n".join(found)
        for expected in ("$.a: 1 != 2", "$.b: type str != int", "$.c: length 1 != 2", "$.d: only in published file"):
            self.assertIn(expected, text)

    def test_null_is_not_zero(self):
        self.assertTrue(app.difference(None, 0))


class RepositoryParityTests(unittest.TestCase):
    """Completed seasons never change with live data, so they must match the published files exactly."""

    def test_completed_seasons_equal_published_standings(self):
        import json
        from derived_data import build_league_standings
        from league_metadata import list_league_ids
        root = TOOLS.parent
        league = json.loads((root / "public/data/League.json").read_text(encoding="utf-8"))
        year = int(league["Season"])
        published = {s["Season"]: s for s in json.loads((root / "public/data/Standings.json").read_text(encoding="utf-8"))}
        for league_id in list_league_ids():
            documents = build_league_standings(root, league_id)
            rendered = {s["Season"]: s for s in app.render_standings(documents, year)}
            completed = [k for k in rendered if k.isdigit() and int(k) < year]
            self.assertTrue(completed)
            for season in completed:
                self.assertEqual([], app.difference(rendered[season], published[season], season))


if __name__ == "__main__":
    unittest.main()
