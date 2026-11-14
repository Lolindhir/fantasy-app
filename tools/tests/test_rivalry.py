"""Rivalry v1/v2, bracket provenance and the league-rivalry product (Issues #1455/#1470)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import playoff_brackets as pb  # noqa: E402
from derived_data_lib import rivalry  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.rivalry import v1, v2  # noqa: E402

REPO = TOOLS.parent
PRODUCT = REPO / "data-derived" / "league-rivalry" / "nfl-reise.json"


def bracket_game(rnd, match, team1, team2, placement=None):
    return {"Round": rnd, "Match": match, "Placement": placement, "Team1CanonicalLeagueRosterID": team1, "Team2CanonicalLeagueRosterID": team2}


class RoundWindowTests(unittest.TestCase):
    def test_round_types(self):
        self.assertEqual([(15,), (16,), (17,)], pb.round_windows({"PlayoffStartWeek": 15, "PlayoffRoundCount": 3, "PlayoffRoundType": 0}))
        self.assertEqual([(14, 15), (16, 17)], pb.round_windows({"PlayoffStartWeek": 14, "PlayoffRoundCount": 2, "PlayoffRoundType": 2}))
        self.assertEqual([(14,), (15,), (16, 17)], pb.round_windows({"PlayoffStartWeek": 14, "PlayoffRoundCount": 3, "PlayoffRoundType": 1}))

    def test_unknown_or_incomplete_format_is_none(self):
        for structure in (None, {}, {"PlayoffStartWeek": 15, "PlayoffRoundCount": 3}, {"PlayoffStartWeek": 15, "PlayoffRoundCount": 3, "PlayoffRoundType": 7},
                          {"PlayoffStartWeek": 0, "PlayoffRoundCount": 3, "PlayoffRoundType": 0}):
            self.assertIsNone(pb.round_windows(structure))


class ClassifyTests(unittest.TestCase):
    def brackets(self, winners, losers=None, round_type=0):
        structure = {"PlayoffStartWeek": 15, "PlayoffRoundCount": 3, "PlayoffRoundType": round_type}
        return pb.SeasonBrackets(structure, winners, losers or [])

    def test_labels(self):
        b = self.brackets(
            [bracket_game(1, 1, "a", "b"), bracket_game(3, 1, "a", "c", placement=1), bracket_game(3, 2, "d", "e", placement=5)],
            [bracket_game(1, 1, "f", "g", placement=1)],
        )
        self.assertEqual(pb.CHAMPIONSHIP, b.classify(15, ("b", "a")))
        self.assertEqual(pb.CHAMPIONSHIP, b.classify(17, ("a", "c")))
        self.assertEqual(pb.PLACEMENT, b.classify(17, ("d", "e")))
        self.assertEqual(pb.CONSOLATION, b.classify(15, ("f", "g")))

    def test_ambiguous_missing_or_out_of_window_is_unclassified(self):
        b = self.brackets([bracket_game(1, 1, "a", "b"), bracket_game(1, 2, "a", "b")])
        self.assertEqual(pb.UNCLASSIFIED, b.classify(15, ("a", "b")))  # two bracket games for the pair
        self.assertEqual(pb.UNCLASSIFIED, b.classify(15, ("a", "z")))  # pair not in a bracket
        self.assertEqual(pb.UNCLASSIFIED, b.classify(18, ("a", "b")))  # week outside the rounds
        self.assertEqual(pb.UNCLASSIFIED, b.classify(16, ("a", "b")))  # pair is a round 1 game only
        self.assertEqual(pb.UNCLASSIFIED, b.classify(15, ("", "b")))
        self.assertEqual(pb.UNCLASSIFIED, pb.SeasonBrackets(None, [bracket_game(1, 1, "a", "b")], []).classify(15, ("a", "b")))

    def test_two_week_rounds_label_both_weeks(self):
        b = pb.SeasonBrackets({"PlayoffStartWeek": 14, "PlayoffRoundCount": 2, "PlayoffRoundType": 2},
                              [bracket_game(1, 1, "a", "b"), bracket_game(2, 1, "a", "c", placement=1)], [])
        self.assertEqual([pb.CHAMPIONSHIP] * 2, [b.classify(w, ("a", "b")) for w in (14, 15)])
        self.assertEqual([pb.CHAMPIONSHIP] * 2, [b.classify(w, ("c", "a")) for w in (16, 17)])
        self.assertEqual(pb.UNCLASSIFIED, b.classify(16, ("a", "b")))

    def test_missing_bracket_files_classify_nothing(self):
        self.assertEqual(pb.UNCLASSIFIED, pb.SeasonBrackets({"PlayoffStartWeek": 15, "PlayoffRoundCount": 3, "PlayoffRoundType": 0}, None, None).classify(15, ("a", "b")))


class ModelTests(unittest.TestCase):
    def test_registered_and_kind(self):
        self.assertIs(v1, registry.get_model("rivalry-v1", "rivalry"))
        self.assertIn("rivalry-v1", registry.model_ids())
        self.assertIs(v2, registry.get_model("rivalry-v2", "rivalry"))
        self.assertIn("rivalry-v2", registry.model_ids())

    def test_counting_rules(self):
        self.assertTrue(v1.counts("regular-season", None, False))
        self.assertTrue(v1.counts("regular-season", None, True))
        self.assertFalse(v1.counts("playoffs", "championship", False))  # E2: running season
        self.assertTrue(v1.counts("playoffs", "championship", True))
        self.assertTrue(v1.counts("playoffs", "placement", True))  # E1
        self.assertFalse(v1.counts("playoffs", "consolation", True))
        self.assertFalse(v1.counts("playoffs", "unclassified", True))
        self.assertFalse(v1.counts("playoffs", None, True))

    def test_v2_counts_every_final_matchup_independent_of_bracket_and_season(self):
        self.assertTrue(v2.counts("regular-season", None, False))
        self.assertTrue(v2.counts("regular-season", None, True))
        for complete in (False, True):
            for bracket in ("championship", "placement", "consolation", "unclassified", None):
                self.assertTrue(v2.counts("playoffs", bracket, complete), (bracket, complete))
        self.assertFalse(v2.counts("pre-season", None, True))
        # The v1 model is immutable: no broadening of its counting rules.
        self.assertFalse(v1.counts("playoffs", "consolation", True))
        self.assertFalse(v1.counts("playoffs", "championship", False))
        self.assertIs(v2.summarize, v1.summarize)
        self.assertIs(v2.game_record, v1.game_record)

    def game(self, week, outcome, own, other, season="2024"):
        return v1.game_record(season, week, f"m{week}", "regular-season", None, outcome, own, other)

    def test_summary_biggest_closest_and_rounding(self):
        games = [self.game(1, "win", 100.0, 90.0), self.game(2, "win", 120.0, 80.0), self.game(3, "loss", 90.0, 91.5),
                 self.game(4, "loss", 70.0, 95.0), self.game(5, "tie", 100.0, 100.0)]
        s = v1.summarize(games)
        self.assertEqual((2, 2, 1), (s["Wins"], s["Losses"], s["Ties"]))
        self.assertEqual("m2", s["BiggestWinMatchupID"])
        self.assertEqual("m3", s["ClosestLossMatchupID"])
        self.assertEqual(480.0, s["PointsFor"])
        self.assertEqual(456.5, s["PointsAgainst"])

    def test_missing_scores_count_for_record_only(self):
        s = v1.summarize([self.game(1, "win", None, 80.0), self.game(2, "win", 100.0, 90.0)])
        self.assertEqual(2, s["Wins"])
        self.assertEqual("m2", s["BiggestWinMatchupID"])
        self.assertEqual(100.0, s["PointsFor"])
        self.assertIsNone(s["Games"][0]["Margin"])

    def test_ties_keep_the_earlier_game_and_half_up_rounding(self):
        s = v1.summarize([self.game(1, "win", 100.0, 90.0), self.game(2, "win", 110.0, 100.0)])
        self.assertEqual("m1", s["BiggestWinMatchupID"])
        self.assertEqual(1.0, v1.round_points(0.995))
        self.assertEqual(2.68, v1.round_points(2.675))  # the double of 2.675 times 100 is 267.5 exactly


def matchup(mid, a, pa, b, pb, bracket=None, state="final"):
    result = None
    if state == "final":
        result = {"Type": "tie", "WinnerTeamID": None} if pa == pb else {"Type": "win", "WinnerTeamID": a if pa > pb else b}
    return {"FantasyMatchupID": mid, "Participants": [{"TeamID": a, "Points": pa}, {"TeamID": b, "Points": pb}], "CompletionState": state, "Result": result, "Bracket": bracket}


class SeasonGamesTests(unittest.TestCase):
    def season(self):
        return {"Season": "2025", "Weeks": [
            {"Week": 1, "Stage": "regular-season", "Matchups": [matchup("r1", 1, 100.0, 2, 90.0), matchup("r2", 3, 80.0, 4, 80.0, state="open")]},
            {"Week": 15, "Stage": "playoffs", "Matchups": [matchup("p1", 1, 100.0, 2, 110.0, "championship"), matchup("p2", 3, 1.0, 4, 2.0, "consolation"),
                                                          matchup("p3", 5, 1.0, 6, 2.0, "unclassified"), matchup("p4", 1, 90.0, 4, 80.0, "placement")]},
        ]}

    def test_complete_season_counts_title_and_placement_games_only(self):
        rows, stats = rivalry.season_games(self.season(), v1, True)
        self.assertEqual({"CountedRegular": 1, "CountedPlayoffs": 2, "ExcludedConsolation": 1, "ExcludedUnclassified": 1, "ExcludedSeasonIncomplete": 0}, stats)
        self.assertEqual(6, len(rows))  # three games, both directions

    def test_running_season_counts_regular_games_only(self):
        _, stats = rivalry.season_games(self.season(), v1, False)
        self.assertEqual((1, 0, 4), (stats["CountedRegular"], stats["CountedPlayoffs"], stats["ExcludedSeasonIncomplete"]))

    def test_v2_counts_consolation_unclassified_and_in_progress_playoffs(self):
        rows, stats = rivalry.season_games(self.season(), v2, False)
        self.assertEqual({
            "CountedRegular": 1, "CountedPlayoffs": 4,
            "ExcludedConsolation": 0, "ExcludedUnclassified": 0, "ExcludedSeasonIncomplete": 0,
        }, stats)
        self.assertEqual(10, len(rows))  # five final games in two directions; open game omitted
        records = rivalry.build_records(rows, v2)
        by_pair = {(r["TeamID"], r["OpponentID"], r["Filter"]): r for r in records}
        self.assertEqual(1, by_pair[(3, 4, "playoffs")]["Wins"] + by_pair[(3, 4, "playoffs")]["Losses"])
        self.assertEqual(1, by_pair[(5, 6, "playoffs")]["Wins"] + by_pair[(5, 6, "playoffs")]["Losses"])
        self.assertEqual(2, len(by_pair[(1, 2, "all")]["Games"]))

    def test_records_are_mirrored(self):
        rows, _ = rivalry.season_games(self.season(), v1, True)
        records = {(r["TeamID"], r["OpponentID"], r["Filter"]): r for r in rivalry.build_records(rows, v1)}
        a, b = records[(1, 2, "all")], records[(2, 1, "all")]
        self.assertEqual((a["Wins"], a["Losses"]), (b["Losses"], b["Wins"]))
        self.assertEqual((a["PointsFor"], a["PointsAgainst"]), (b["PointsAgainst"], b["PointsFor"]))
        self.assertEqual(2, len(a["Games"]))
        self.assertEqual(1, len(records[(1, 2, "regular")]["Games"]))
        self.assertEqual(1, len(records[(1, 2, "playoffs")]["Games"]))
        self.assertNotIn((1, 3, "all"), records)


class PersistedProductTests(unittest.TestCase):
    """Invariants of the committed product: symmetric records, points mirrored, every referenced game present."""

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PRODUCT.read_text(encoding="utf-8"))
        cls.records = {(r["TeamID"], r["OpponentID"], r["Filter"]): r for r in cls.doc["Records"]}

    def test_shape(self):
        self.assertEqual("league-rivalry", self.doc["Product"])
        self.assertEqual("nfl-reise", self.doc["CanonicalLeagueID"])
        # A committed v1 baseline may coexist temporarily with the v2 model selection
        # until the existing productive rivalry writer publishes the regenerated snapshot.
        selected = {m["Rivalry"] for m in self.doc["Models"].values()}
        self.assertIn(selected, ({"rivalry-v1"}, {"rivalry-v2"}))

    def test_records_are_symmetric(self):
        for (team, opponent, flt), record in self.records.items():
            other = self.records[(opponent, team, flt)]
            self.assertEqual((record["Wins"], record["Losses"], record["Ties"]), (other["Losses"], other["Wins"], other["Ties"]))
            self.assertEqual((record["PointsFor"], record["PointsAgainst"]), (other["PointsAgainst"], other["PointsFor"]))
            self.assertEqual([g["FantasyMatchupID"] for g in record["Games"]], [g["FantasyMatchupID"] for g in other["Games"]])

    def test_all_is_regular_plus_playoffs(self):
        for (team, opponent, flt), record in self.records.items():
            if flt != "all":
                continue
            parts = [len(self.records[(team, opponent, f)]["Games"]) for f in ("regular", "playoffs") if (team, opponent, f) in self.records]
            self.assertEqual(len(record["Games"]), sum(parts))

    def test_playoff_brackets_match_the_persisted_model_version(self):
        selected = {m["Rivalry"] for m in self.doc["Models"].values()}
        if selected == {"rivalry-v1"}:
            for record in self.records.values():
                for game in record["Games"]:
                    if game["Stage"] == "playoffs":
                        self.assertIn(game["Bracket"], ("championship", "placement"))
        else:
            for season in self.doc["Seasons"]:
                self.assertEqual(0, season["ExcludedConsolation"])
                self.assertEqual(0, season["ExcludedUnclassified"])
                self.assertEqual(0, season["ExcludedSeasonIncomplete"])
            self.assertTrue(any(game["Bracket"] == "consolation"
                                for record in self.records.values() for game in record["Games"]),
                            "The v2 historical snapshot should include the known 2025 losers-bracket game")

    def test_references_exist(self):
        for record in self.records.values():
            ids = {g["FantasyMatchupID"] for g in record["Games"]}
            for ref in (record["BiggestWinMatchupID"], record["ClosestLossMatchupID"]):
                self.assertTrue(ref is None or ref in ids)


if __name__ == "__main__":
    unittest.main()


class MatchupBracketLabelTests(unittest.TestCase):
    """Bracket label on the computed matchups of completed seasons: regular season is null, every playoff matchup carries a defined label."""

    def test_completed_season_labels(self):
        from datetime import datetime, timezone

        from derived_data_lib.matchup_context import resolve_matchups

        doc = json.loads(PRODUCT.read_text(encoding="utf-8"))
        completed = [int(s["Season"]) for s in doc["Seasons"] if s["PlayoffsComplete"]]
        self.assertTrue(completed)
        for season in completed:
            model = resolve_matchups(REPO, "nfl-reise", season, datetime.now(timezone.utc))
            for week in model["Weeks"]:
                for matchup in week["Matchups"]:
                    if week["Stage"] == "regular-season":
                        self.assertIsNone(matchup["Bracket"])
                    else:
                        self.assertIn(matchup["Bracket"], pb.BRACKET_LABELS)
