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
    return {"Name": "Best Performer", "Type": {"Name": "RegularSeason", "DisplayText": "Regular Season", "Order": 2}, "IconUnicode": "1F525", "StatDisplay": "1", "TeamID": team_id, "Owner": f"o{team_id}", "TeamName": f"t{team_id}"}


def document(season, with_movement):
    return {
        "RegularSeason": [regular(1, 1, with_movement), regular(2, 2, with_movement)],
        "Playoffs": [playoff(1, 1), playoff(2, 2)],
        "Awards": [award(1)],
        "Teams": [{"TeamID": 1}, {"TeamID": 2}],
        "AllTime": {
            "ThroughSeason": season,
            "Playoffs": [
                {"Place": 1, "TeamID": 1, "Owner": "o1", "TeamName": "t1", "Championships": 1, "RunnerUps": 0, "Thirds": 0},
                {"Place": 2, "TeamID": 2, "Owner": "o2", "TeamName": "t2", "Championships": 0, "RunnerUps": 1, "Thirds": 0},
            ],
            "RegularSeason": [regular(1, 1, False), regular(2, 2, False)],
        },
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

    def test_current_weekly_standings_are_copied_only_into_current_season(self):
        current_weeks = [{"Week": 1, "Teams": [
            {"TeamID": 1, "Place": 1, "Wins": 1, "Losses": 0, "Ties": 0,
             "Points": 125.5, "PointsAgainst": 85.0, "Streak": "1W"},
            {"TeamID": 2, "Place": 2, "Wins": 0, "Losses": 1, "Ties": 0,
             "Points": 85.0, "PointsAgainst": 125.5, "Streak": "1L"},
        ]}]
        self.documents[2025]["Weeks"] = current_weeks
        self.documents[2024]["Weeks"] = current_weeks
        rendered = app.render_standings(self.documents, 2025)
        self.assertEqual(current_weeks, rendered[1]["Weeks"])
        self.assertNotIn("Weeks", rendered[0])
        self.assertNotIn("Weeks", rendered[2])
        self.assertNotIn("Weeks", app.render_placements(rendered, [1, 2], 2025)[1]["Current"])
        self.assertNotIn("Weeks", app.render_standings(self.documents, 2024)[1])  # a non-current year

    def test_avatar_id_becomes_cdn_url_and_is_not_kept(self):
        row = app.render_standings(self.documents, 2025)[1]["Playoffs"][0]
        self.assertEqual("https://sleepercdn.com/avatars/av1", row["OwnerAvatar"])
        self.assertNotIn("OwnerAvatarID", row)

    def test_all_time_comes_from_newest_document(self):
        self.documents[2025]["AllTime"]["ThroughSeason"] = 2025
        self.documents[2025]["AllTime"]["Playoffs"][0]["Place"] = 7
        self.assertEqual(7, app.render_standings(self.documents, 2025)[0]["Playoffs"][0]["Place"])

    def test_legacy_highlights_use_shared_results_in_a_stable_order(self):
        legacy = app.render_standings(self.documents, 2025)[0]["LegacyHighlights"]
        self.assertEqual([
            {"Key": "ChampOfChamps", "TeamID": 1},
            {"Key": "RegularSeasonKing", "TeamID": 1},
            {"Key": "PodiumMachine", "TeamID": 1, "Count": 1},
            {"Key": "AwardCollector", "TeamID": 1, "Count": 2},
        ], legacy)
        self.assertNotIn("LegacyHighlights", self.documents[2025]["AllTime"])

    def test_podium_and_award_tiebreakers_do_not_recompute_in_angular(self):
        # Two podiums beat one regardless of all-time place.
        second = self.documents[2025]["AllTime"]["Playoffs"][1]
        second.update({"Championships": 1, "RunnerUps": 1, "Thirds": 0})
        highlights = app.render_legacy_highlights(self.documents, 2025)
        self.assertEqual({"Key": "PodiumMachine", "TeamID": 2, "Count": 2}, highlights[2])

        # Award counts, then distinct names, then overall place, exactly as the former UI.
        self.documents[2024]["Awards"] = [{"Name": "A", "TeamID": 1}, {"Name": "B", "TeamID": 1}]
        self.documents[2025]["Awards"] = [{"Name": "A", "TeamID": 2}, {"Name": "B", "TeamID": 2},
                                           {"Name": "Regular Season King", "TeamID": 2}]
        winner = app.render_legacy_highlights(self.documents, 2025)[-1]
        self.assertEqual({"Key": "AwardCollector", "TeamID": 1, "Count": 2}, winner)
        self.documents[2025]["Awards"][1]["Name"] = "C"
        self.documents[2025]["Awards"].append({"Name": "D", "TeamID": 2})
        winner = app.render_legacy_highlights(self.documents, 2025)[-1]
        self.assertEqual({"Key": "AwardCollector", "TeamID": 2, "Count": 3}, winner)

    def test_legacy_restricts_placement_winners_to_current_rosters(self):
        self.documents[2025]["Teams"] = [{"TeamID": 2}]
        legacy = app.render_legacy_highlights(self.documents, 2025)
        self.assertEqual([2, 2, 2], [row["TeamID"] for row in legacy[:3]])
        # Historical award holders remain eligible even if no longer on a current roster.
        self.assertEqual(1, legacy[-1]["TeamID"])

    def test_legacy_missing_current_season_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "2027"):
            app.render_legacy_highlights(self.documents, 2027)

    def test_award_legend_aggregates_existing_shared_award_types(self):
        expected = [{"Key": "RegularSeason", "DisplayText": "Regular Season", "IconUnicode": "1F525",
                     "Order": 2, "Occurrences": 2}]
        self.assertEqual(expected, app.render_award_legend(self.documents))
        self.assertEqual(expected, app.render_standings(self.documents, 2025)[0]["AwardLegend"])
        self.assertNotIn("AwardLegend", self.documents[2025]["AllTime"])
        self.documents[2025]["Awards"].append({
            "Name": "Regular Season King", "Type": {"Name": "RegularSeason", "DisplayText": "Regular Season", "Order": 2},
            "TeamID": 2, "IconUnicode": "1F451",
        })
        self.assertEqual(expected, app.render_award_legend(self.documents))

    def test_award_legend_order_and_first_source_icon_are_stable(self):
        self.documents[2025]["Awards"].append({
            "Name": "Weekly Star", "Type": {"Name": "Playoffs", "DisplayText": "Playoffs", "Order": 1},
            "TeamID": 2, "IconUnicode": "2605",
        })
        legend = app.render_award_legend(self.documents)
        self.assertEqual(["Playoffs", "RegularSeason"], [entry["Key"] for entry in legend])
        self.assertEqual("1F525", legend[1]["IconUnicode"])
        self.assertEqual(2, legend[1]["Occurrences"])

    def test_award_legend_is_deterministic_and_does_not_mutate_derived_documents(self):
        import copy
        before = copy.deepcopy(self.documents)
        first = app.render_award_legend(self.documents)
        second = app.render_award_legend(self.documents)
        self.assertEqual(first, second)
        self.assertEqual(before, self.documents)

    def test_award_legend_fails_closed_on_invalid_award_type(self):
        self.documents[2025]["Awards"][0]["Type"] = "not-an-award-type"
        with self.assertRaisesRegex(ValueError, "Invalid award Type"):
            app.render_award_legend(self.documents)

    def test_all_time_percentage_display_uses_existing_model_format(self):
        for pct, expected in ((0.7037, ".704"), (1.0, "1.000"), (0.0, ".000"), (-1, None), (None, None)):
            with self.subTest(pct=pct):
                self.documents[2025]["AllTime"]["RegularSeason"][0]["WinPercentage"] = pct
                rendered = app.render_standings(self.documents, 2025)
                self.assertEqual(expected, rendered[0]["RegularSeason"][0]["WinPercentageDisplay"])
                placements = app.render_placements(rendered, [1, 2], 2025)
                self.assertEqual(expected, placements[1]["AllTime"]["Regular"]["WinPercentageDisplay"])
                self.assertNotIn("WinPercentageDisplay", self.documents[2025]["AllTime"]["RegularSeason"][0])

    def test_all_time_percentage_display_rejects_invalid_values(self):
        for pct in (float("nan"), float("inf"), True, "0.5", 1.2):
            with self.subTest(pct=pct):
                self.documents[2025]["AllTime"]["RegularSeason"][0]["WinPercentage"] = pct
                with self.assertRaises(ValueError):
                    app.render_standings(self.documents, 2025)

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
        # Season awards stay in the Standings sections; placements carry no copy (Issue #1195).
        for team_id in (1, 2):
            for key in ("AllTime", "Current", "Previous"):
                self.assertNotIn("Awards", placements[team_id][key])


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


class WriteTests(unittest.TestCase):
    """write: product first, Standings.json only on a semantic difference, Timestamps stamped then."""

    def setUp(self):
        import tempfile
        from datetime import datetime, timezone
        from unittest.mock import patch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = self.root / "public" / "data"
        data.mkdir(parents=True)
        (data / "League.json").write_text('{"Season": "2025"}', encoding="utf-8")
        self.documents = {2024: document(2024, False), 2025: document(2025, True)}
        self.now = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)
        patcher = patch.multiple(
            app,
            build_league_standings=lambda root, league: self.documents,
            materialize_league_standings=lambda root, out, league, seasons, check: {
                "Seasons": [{"Season": 2025, "Written": 1}, {"Season": 2024, "Written": 0}]},
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        manifest_patcher = patch.multiple(
            app.standings_sources,
            manifest=lambda root, league: {"CurrentCanonicalLeagueSeasonID": "league-a-2025"},
            current_season=lambda manifest: 2025,
        )
        manifest_patcher.start()
        self.addCleanup(manifest_patcher.stop)

    def test_write_does_not_require_published_league(self):
        import json
        (self.root / "public/data/League.json").unlink()
        app.write_standings(self.root, "league-a", self.now)
        delivered = json.loads((self.root / "public/data/Standings.json").read_text())
        self.assertIn("PreviousWeekPlace", delivered[1]["RegularSeason"][0])
        self.assertNotIn("PreviousWeekPlace", delivered[2]["RegularSeason"][0])

    def test_stale_published_league_season_does_not_change_output(self):
        import json
        (self.root / "public/data/League.json").write_text('{"Season": "2024"}')
        app.write_standings(self.root, "league-a", self.now)
        delivered = json.loads((self.root / "public/data/Standings.json").read_text())
        self.assertEqual("2025", delivered[1]["Season"])
        self.assertIn("PreviousWeekPlace", delivered[1]["RegularSeason"][0])
        self.assertNotIn("PreviousWeekPlace", delivered[2]["RegularSeason"][0])

    def test_missing_manifest_fails_before_any_publication(self):
        from unittest.mock import patch
        with patch.object(app.standings_sources, "manifest", side_effect=FileNotFoundError("manifest missing")):
            with patch.object(app, "materialize_league_standings", side_effect=AssertionError("must not materialize")):
                with self.assertRaises(FileNotFoundError):
                    app.write_standings(self.root, "league-a", self.now)
        self.assertFalse((self.root / "public/data/Standings.json").exists())

    def test_inconsistent_current_season_fails_before_any_publication(self):
        from unittest.mock import patch
        with patch.object(app.standings_sources, "current_season", return_value=2026):
            with patch.object(app, "materialize_league_standings", side_effect=AssertionError("must not materialize")):
                with self.assertRaisesRegex(ValueError, "2026 missing"):
                    app.write_standings(self.root, "league-a", self.now)
        self.assertFalse((self.root / "public/data/Standings.json").exists())

    def test_first_write_creates_file_and_timestamp_second_is_noop(self):
        changed = app.write_standings(self.root, "league-a", self.now)
        self.assertEqual(["data-derived/league-standings/league-a/2025.json", "public/data/Standings.json", "public/data/Timestamps.json"], changed)
        import json
        stamps = json.loads((self.root / "public/data/Timestamps.json").read_text())
        self.assertEqual("2026-10-29T12:00:00Z", stamps["Standings"])
        text = (self.root / "public/data/Standings.json").read_text()
        self.assertTrue(text.endswith("}\n]\n"))
        self.assertEqual(["data-derived/league-standings/league-a/2025.json"], app.write_standings(self.root, "league-a", self.now))
        self.assertEqual(text, (self.root / "public/data/Standings.json").read_text())

    def test_change_rewrites_and_keeps_other_timestamps(self):
        import json
        (self.root / "public/data/Timestamps.json").write_text('{"League": "x"}')
        app.write_standings(self.root, "league-a", self.now)
        self.documents[2025]["RegularSeason"][0]["Wins"] = 9
        self.assertIn("public/data/Standings.json", app.write_standings(self.root, "league-a", self.now))
        stamps = json.loads((self.root / "public/data/Timestamps.json").read_text())
        self.assertEqual({"League": "x", "Standings": "2026-10-29T12:00:00Z"}, stamps)


class RenderFromProductTests(unittest.TestCase):
    """render: the consumer read of RequestLeague and the recaps comes from the persisted product, fail-closed."""

    def setUp(self):
        import tempfile
        from unittest.mock import patch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = patch.multiple(
            app.standings_sources,
            manifest=lambda root, league: {},
            manifest_seasons=lambda data: [2024, 2025],
            current_season=lambda data: 2025,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, season, doc):
        import json
        path = self.root / "data-derived" / "league-standings" / "league-a" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_renders_same_content_as_in_memory_render(self):
        documents = {2024: document(2024, False), 2025: document(2025, True)}
        for season, doc in documents.items():
            self._write(season, doc)
        self.assertEqual(app.render_standings(documents, 2025), app.render_from_product(self.root, "league-a"))

    def test_missing_season_file_fails_closed(self):
        self._write(2025, document(2025, True))
        with self.assertRaises(FileNotFoundError):
            app.render_from_product(self.root, "league-a")


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
