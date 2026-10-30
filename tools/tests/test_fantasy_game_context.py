"""FantasyGameContext of one matchup week (ADR-075, Issue #1199 section 3, step 3). Ported from the PowerShell regression tests
FantasyGameContext, FantasyGameContextScore, FantasyGameContextSleeperShape, FantasyMatchupPreview, FantasyWeeklyWatch and the
context part of FantasyRelevanceV2; no real league, player or schedule data is hard-wired."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import fantasy_game_context as fgc  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError, parse_instant_text  # noqa: E402


def identity_key(value):
    return None if value is None else str(value)


def lock(team, player, game, starter, nfl="A", kind="scheduled"):
    return {
        "FantasyTeamID": team, "PlayerID": player, "NFLTeamID": nfl, "Kind": kind, "GameID": game,
        "DecisionWindowID": "dw-a" if game else None, "StartsAtUtc": "2026-09-10T00:00:00Z" if game else None, "IsStarter": starter,
    }


def decision_facts():
    return {
        "DecisionWindows": [
            {
                "DecisionWindowID": "dw-a",
                "StartsAtUtc": "2026-09-10T00:00:00Z",
                "Games": [{"GameID": "g-a", "AwayTeamID": "A", "AwayTeamAbbr": "AAA", "HomeTeamID": "H", "HomeTeamAbbr": "HHH"}],
            }
        ],
        "PlayerLockFacts": [
            lock("1", "p1", "g-a", True), lock("1", "p2", "g-a", False), lock("2", "p3", "g-a", True, "H"),
            lock("2", "p4", None, False, None, "unknown"),
        ],
    }


def sleeper_rows():
    return [
        {"matchup_id": 9, "roster_id": 1, "players": ["p1", "p2"], "starters": ["p1"], "players_points": {"p1": 18.0, "p2": 7.0}, "points": 30.0, "custom_points": None},
        {"matchup_id": 9, "roster_id": 2, "players": ["p3", "p4"], "starters": ["p3"], "players_points": {"p3": 5.0, "p4": 2.0}, "points": 20.0, "custom_points": None},
    ]


def build(facts, schedule, final, decision=None, **kwargs):
    return fgc.build_fantasy_game_context(
        "league", "2026", 1, decision if decision is not None else decision_facts(), facts, schedule, final, identity_key, parse_instant_text, **kwargs
    )


class CurrentFactsTests(unittest.TestCase):
    def test_pairing_identity_and_counterfactual(self):
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        self.assertEqual(1, len(facts))
        self.assertRegex(facts[0]["FantasyMatchupID"], r"^fgm-[0-9a-f]{24}$")
        context = build(facts, [{"gameID": "g-a", "gameStatus": "Final", "gameWeek": "Week 1"}], True)
        game = context["Games"][0]
        self.assertEqual(3, game["Relevance"]["RosteredPlayerCount"])
        self.assertEqual(2, game["Relevance"]["StarterCount"])
        self.assertEqual(2, game["Relevance"]["FantasyTeamCount"])
        self.assertEqual(1, game["Relevance"]["FantasyMatchupCount"])
        self.assertEqual(30.0, game["Impact"]["RosteredPoints"])
        self.assertEqual(23.0, game["Impact"]["StarterPoints"])
        self.assertEqual("final", game["Impact"]["State"])
        self.assertEqual(1, game["Impact"]["OutcomeSwingMatchupCount"])
        self.assertEqual("available", context["FantasyMatchups"][0]["CounterfactualState"])
        self.assertEqual("final", context["ScoringState"])
        self.assertTrue(any(a["PlayerID"] == "p4" and a["Kind"] == "unknown" for a in context["NonGameAssociations"]))

    def test_sleeper_shape_uses_keyed_player_points(self):
        rows = sleeper_rows()
        rows[0]["players_points"] = {"p1": 18.5, "p2": 4.25}
        rows[0]["starters_points"] = [18.5]
        facts = fgc.current_matchup_facts("2026", 1, rows)
        team_one = next(t for t in facts[0]["Teams"] if t["FantasyTeamID"] == "1")
        starter = next(p for p in team_one["Players"] if p["PlayerID"] == "p1")
        bench = next(p for p in team_one["Players"] if p["PlayerID"] == "p2")
        self.assertTrue(starter["IsStarter"])
        self.assertEqual(18.5, starter["Points"])
        self.assertEqual(4.25, bench["Points"])

    def test_custom_score_disables_counterfactual(self):
        rows = sleeper_rows()
        rows[0]["custom_points"] = 31.0
        context = build(fgc.current_matchup_facts("2026", 1, rows), [{"gameID": "g-a", "gameStatus": "Final"}], True)
        self.assertEqual("unavailable-custom-score", context["FantasyMatchups"][0]["CounterfactualState"])
        self.assertEqual(0, context["Games"][0]["Impact"]["OutcomeSwingMatchupCount"])

    def test_not_final_week_has_no_counterfactual(self):
        context = build(fgc.current_matchup_facts("2026", 1, sleeper_rows()), [{"gameID": "g-a", "gameStatus": "Scheduled"}], False)
        self.assertEqual("unavailable-not-final", context["FantasyMatchups"][0]["CounterfactualState"])
        self.assertIsNone(context["FantasyMatchups"][0]["FinalScores"])
        self.assertEqual("partial", context["ScoringState"])

    def test_week_final_flag_alone_decides_the_counterfactual(self):
        """M2: the week-final rule is an input (LeagueScoredWeek), never read from the rows."""
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        schedule = [{"gameID": "g-a", "gameStatus": "Final"}]
        self.assertEqual("unavailable-not-final", build(facts, schedule, False)["FantasyMatchups"][0]["CounterfactualState"])
        self.assertEqual("available", build(facts, schedule, True)["FantasyMatchups"][0]["CounterfactualState"])

    def test_malformed_pairing_is_excluded(self):
        row = {"matchup_id": 2, "roster_id": 1, "players": ["x"], "starters": ["x"], "players_points": {"x": 1}, "points": 1}
        self.assertEqual([], fgc.current_matchup_facts("2026", 1, [row]))

    def test_rows_without_matchup_or_team_are_skipped(self):
        self.assertEqual([], fgc.current_matchup_facts("2026", 1, [{"matchup_id": None, "roster_id": 1}, {"matchup_id": 3, "roster_id": None}]))

    def test_duplicate_ownership_fails_closed(self):
        rows = [
            {"matchup_id": 2, "roster_id": 1, "players": ["dup"], "starters": ["dup"], "players_points": {"dup": 1}, "points": 1},
            {"matchup_id": 2, "roster_id": 2, "players": ["dup"], "starters": ["dup"], "players_points": {"dup": 2}, "points": 2},
        ]
        with self.assertRaises(MatchupContextError):
            fgc.current_matchup_facts("2026", 1, rows)

    def test_starter_outside_players_fails_closed(self):
        with self.assertRaises(MatchupContextError):
            fgc.current_matchup_facts("2026", 1, [{"matchup_id": 1, "roster_id": 1, "players": ["a"], "starters": ["b"]}])

    def test_team_in_two_matchups_fails_closed(self):
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        facts.append({**copy.deepcopy(facts[0]), "FantasyMatchupID": "fgm-other"})
        with self.assertRaises(MatchupContextError):
            build(facts, [], False)

    def test_player_without_fact_is_a_non_game_association(self):
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        decision = decision_facts()
        decision["PlayerLockFacts"].append(lock("1", "ghost", "g-a", True))
        context = build(facts, [{"gameID": "g-a", "gameStatus": "Scheduled"}], False, decision)
        ghost = next(a for a in context["NonGameAssociations"] if a["PlayerID"] == "ghost")
        self.assertEqual("missing-weekly-player-scoring-fact", ghost["Reason"])

    def test_unknown_game_is_a_non_game_association(self):
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        decision = decision_facts()
        decision["PlayerLockFacts"].append(lock("1", "p2", "g-missing", False))
        context = build(facts, [], False, decision)
        self.assertTrue(any(a["Reason"] == "missing-game-fact" for a in context["NonGameAssociations"]))


class ScoreAndMarketTests(unittest.TestCase):
    def test_score_projection(self):
        context = {"SchemaVersion": 2, "Games": [
            {"GameID": "g-final", "Status": "Final"}, {"GameID": "g-future", "Status": "Scheduled"}, {"GameID": "g-missing", "Status": "Final"}]}
        schedule = [
            {"gameID": "g-final", "gameStatus": "Final", "awayPts": "24", "homePts": "0"},
            {"gameID": "g-future", "gameStatus": "Scheduled", "awayPts": "17", "homePts": "20"},
            {"gameID": "g-missing", "gameStatus": "Final", "awayPts": "21", "homePts": None},
        ]
        result = fgc.add_score_context(context, schedule)
        final, future, missing = result["Games"]
        self.assertEqual(3, result["SchemaVersion"])
        self.assertEqual((24.0, 0.0), (final["AwayScore"], final["HomeScore"]))
        self.assertEqual((None, None), (future["AwayScore"], future["HomeScore"]))
        self.assertEqual((None, None), (missing["AwayScore"], missing["HomeScore"]))
        with self.assertRaises(MatchupContextError):
            fgc.add_score_context({"SchemaVersion": 2, "Games": [{"GameID": "dup", "Status": "Final"}]},
                                  [{"gameID": "dup", "awayPts": 10, "homePts": 7}] * 2)

    def market_fixture(self):
        context = {"SchemaVersion": 5, "Games": [
            {"GameID": "display-pit-no", "AwayTeamID": "PIT", "HomeTeamID": "NO", "Status": "Scheduled"},
            {"GameID": "display-ne-chi", "AwayTeamID": "NE", "HomeTeamID": "CHI", "Status": "Final"},
            {"GameID": "display-unmatched", "AwayTeamID": "CAR", "HomeTeamID": "TB", "Status": "Scheduled"}]}
        schedule = [
            {"gameID": "display-pit-no", "CanonicalGameID": "2026_07_PIT_NO"},
            {"gameID": "display-ne-chi", "CanonicalGameID": "2026_07_NE_CHI"},
            {"gameID": "display-unmatched", "CanonicalGameID": "2026_07_CAR_TB"},
        ]
        derived = {"SchemaVersion": 1, "Season": 2026, "Games": [
            {"GameID": "2026_07_PIT_NO", "Week": 7, "AwayTeam": "PIT", "HomeTeam": "NO",
             "Market": {"SpreadLine": -3, "TotalLine": 44.5, "ImpliedAwayPoints": 23.75, "ImpliedHomePoints": 20.75}},
            {"GameID": "2026_07_NE_CHI", "Week": 7, "AwayTeam": "NE", "HomeTeam": "CHI",
             "Market": {"SpreadLine": 3, "TotalLine": 50.5, "ImpliedAwayPoints": 23.75, "ImpliedHomePoints": 26.75}}]}
        return context, schedule, derived

    def test_market_joins_only_through_canonical_game_id(self):
        context, schedule, derived = self.market_fixture()
        result = fgc.add_market_context(context, schedule, "2026", 7, derived)
        pit, ne, unmatched = result["Games"]
        self.assertEqual(6, result["SchemaVersion"])
        self.assertEqual({"SpreadLine": -3.0, "TotalLine": 44.5, "ImpliedAwayPoints": 23.75, "ImpliedHomePoints": 20.75}, pit["Market"])
        self.assertEqual(23.75, ne["Market"]["ImpliedAwayPoints"])
        self.assertIsNone(unmatched["Market"])

    def test_missing_derived_partition_adds_no_odds(self):
        context, schedule, _ = self.market_fixture()
        result = fgc.add_market_context(context, schedule, "2026", 7, None)
        self.assertTrue(all(g["Market"] is None for g in result["Games"]))
        self.assertEqual(6, result["SchemaVersion"])

    def test_market_identity_and_season_fail_closed(self):
        context, schedule, derived = self.market_fixture()
        swapped = copy.deepcopy(derived)
        swapped["Games"][0].update({"AwayTeam": "NO", "HomeTeam": "PIT"})
        with self.assertRaises(MatchupContextError):
            fgc.add_market_context(copy.deepcopy(context), schedule, "2026", 7, swapped)
        with self.assertRaises(MatchupContextError):
            fgc.add_market_context({"SchemaVersion": 5, "Games": []}, [], "2025", 7, derived)
        with self.assertRaises(MatchupContextError):
            fgc.add_market_context(copy.deepcopy(context), schedule, "2026", 8, derived)

    def test_market_is_omitted_for_the_historical_schema(self):
        facts = fgc.current_matchup_facts("2026", 1, sleeper_rows())
        context = build(facts, [{"gameID": "g-a", "gameStatus": "Final"}], True)
        self.assertEqual(4, context["SchemaVersion"])
        self.assertNotIn("Market", context["Games"][0])
        self.assertNotIn("RemainingRelevance", context["Games"][0])
        self.assertEqual({"AwayScore": None, "HomeScore": None}, {k: context["Games"][0][k] for k in ("AwayScore", "HomeScore")})


WINDOW_OPTION = "2026-09-10T00:20:00Z"
WINDOW_STARTER = "2026-09-11T00:35:00Z"


def player(player_id, game, window, placement="starter", state="unlocked", bench=False, direct=None):
    result = {
        "PlayerID": player_id, "Placement": placement, "GameState": state, "GameID": game, "DecisionWindowID": window,
        "StartsAtUtc": window, "IsBenchCandidate": bench,
    }
    if direct is not None:
        result["HasDirectScoringPath"] = direct
    return result


def preview(matchup_id, team_ids, teams):
    context = {"SchemaVersion": 4, "FantasyMatchups": [{"FantasyMatchupID": matchup_id, "TeamIDs": team_ids, "Games": [], "RemainingRelevance": {}}]}
    decision = {"FantasyRelevance": {"Teams": teams}}
    return fgc.add_preview_context(context, decision, parse_instant_text)


class PreviewTests(unittest.TestCase):
    def test_option_window_stays_a_lineup_decision(self):
        teams = [
            {"FantasyTeamID": "1", "Players": [
                player("kicker-option", "g-option", WINDOW_OPTION, "bench", bench=True),
                player("a-1", "g-a", WINDOW_STARTER), player("b-1", "g-b", WINDOW_STARTER)]},
            {"FantasyTeamID": "2", "Players": [player("a-2", "g-a", WINDOW_STARTER), player("a-opt", "g-a", WINDOW_STARTER, "bench", bench=True)]},
        ]
        result = preview("m1", ["1", "2"], teams)
        remaining = result["FantasyMatchups"][0]["RemainingRelevance"]
        self.assertEqual(5, result["SchemaVersion"])
        self.assertEqual(WINDOW_OPTION, remaining["NextLineupDecisionWindowID"])
        self.assertEqual("g-option", remaining["NextLineupDecisionPrimaryGameID"])
        self.assertEqual(0, remaining["NextLineupDecisionStarterCount"])
        self.assertEqual(1, remaining["NextLineupDecisionOptionCount"])
        self.assertIsNone(remaining["ActiveScoringWindowID"])
        self.assertEqual([], remaining["ActiveScoringGameIDs"])
        self.assertEqual(WINDOW_STARTER, remaining["NextScoringWindowID"])
        self.assertEqual("g-a", remaining["NextScoringPrimaryGameID"])
        self.assertEqual(2, remaining["NextScoringWindowGameCount"])
        self.assertEqual(0, remaining["NextScoringLockedActiveStarterCount"])
        self.assertEqual(2, remaining["NextScoringUnlockedStarterCount"])
        self.assertEqual(1, remaining["NextScoringOptionCount"])
        self.assertIn("g-b", remaining["NextScoringGameIDs"])

    def test_live_next_and_later_windows(self):
        live, nxt, later = "2026-09-13T17:00:00Z", "2026-09-13T20:25:00Z", "2026-09-14T00:20:00Z"
        teams = [
            {"FantasyTeamID": "3", "Players": [
                player("completed", "g-completed", "2026-09-12T00:00:00Z", state="completed"),
                player("live-a", "g-live-a", live, state="locked-active"), player("next-a", "g-next", nxt), player("later-a", "g-later", later)]},
            {"FantasyTeamID": "4", "Players": [
                player("live-b", "g-live-b", live, state="locked-active"), player("next-b", "g-next", nxt),
                player("option-between", "g-option-between", "2026-09-13T19:00:00Z", "bench", bench=True)]},
        ]
        remaining = preview("m", ["3", "4"], teams)["FantasyMatchups"][0]["RemainingRelevance"]
        self.assertEqual(live, remaining["ActiveScoringWindowID"])
        self.assertEqual({"g-live-a", "g-live-b"}, set(remaining["ActiveScoringGameIDs"]))
        self.assertEqual(nxt, remaining["NextScoringWindowID"])
        self.assertEqual("g-next", remaining["NextScoringPrimaryGameID"])
        self.assertNotIn("g-later", remaining["NextScoringGameIDs"])
        self.assertEqual("2026-09-13T19:00:00Z", remaining["NextLineupDecisionWindowID"])

    def test_live_final_window_has_no_future_next(self):
        live, later = "2026-09-13T17:00:00Z", "2026-09-14T00:20:00Z"
        teams = [
            {"FantasyTeamID": "5", "Players": [player("live-final", "g-live-final", live, state="locked-active"),
                                                player("late-option", "g-late-option", later, "bench", bench=True)]},
            {"FantasyTeamID": "6", "Players": []},
        ]
        remaining = preview("m", ["5", "6"], teams)["FantasyMatchups"][0]["RemainingRelevance"]
        self.assertEqual(live, remaining["ActiveScoringWindowID"])
        self.assertIsNone(remaining["NextScoringWindowID"])
        self.assertEqual([], remaining["NextScoringGameIDs"])
        self.assertEqual(later, remaining["NextLineupDecisionWindowID"])

    def test_option_only_never_becomes_scoring(self):
        teams = [{"FantasyTeamID": "7", "Players": [player("only-opt", "g-only", WINDOW_OPTION, "bench", bench=True)]}, {"FantasyTeamID": "8", "Players": []}]
        remaining = preview("m", ["7", "8"], teams)["FantasyMatchups"][0]["RemainingRelevance"]
        self.assertEqual("g-only", remaining["NextLineupDecisionPrimaryGameID"])
        self.assertIsNone(remaining["ActiveScoringWindowID"])
        self.assertIsNone(remaining["NextScoringPrimaryGameID"])
        self.assertEqual(1, remaining["NextLineupDecisionOptionCount"])

    def test_second_enrichment_is_stable(self):
        live, nxt = "2026-09-13T17:00:00Z", "2026-09-13T20:25:00Z"
        teams = [{"FantasyTeamID": "3", "Players": [player("a", "g-live", live, state="locked-active"), player("b", "g-next", nxt)]},
                 {"FantasyTeamID": "4", "Players": []}]
        once = preview("m", ["3", "4"], teams)
        first = json.dumps(once, sort_keys=True)
        twice = fgc.add_preview_context(once, {"FantasyRelevance": {"Teams": teams}}, parse_instant_text)
        self.assertEqual(first, json.dumps(twice, sort_keys=True))

    def test_without_relevance_the_context_is_unchanged(self):
        context = {"SchemaVersion": 1, "FantasyMatchups": []}
        self.assertEqual({"SchemaVersion": 1, "FantasyMatchups": []}, fgc.add_preview_context(context, {}, parse_instant_text))


def watch_team(team, matchup, starters):
    return {"FantasyTeamID": team, "FantasyMatchupID": matchup, "StarterCount": starters}


def watch_game(game_id, starts, status, teams, locked=0, remaining=True):
    return {
        "GameID": game_id, "DecisionWindowID": starts, "StartsAtUtc": starts, "Status": status,
        "Relevance": {"StarterCount": sum(t["StarterCount"] for t in teams)}, "FantasyTeams": teams,
        "RemainingRelevance": {
            "HasRemainingRelevance": remaining, "CommittedFinalWindowMatchupCount": 0, "LockedActiveStarterCount": locked,
            "DirectStarterFantasyTeamCount": 0, "DirectStarterFantasyTeamIDs": [], "UnlockedStarterCount": 0,
            "TwoSidedFantasyMatchupCount": 0, "FantasyMatchupCount": 0, "FinalWindowFantasyMatchupCount": 0, "EligibleBenchCandidateCount": 0,
        },
    }


class WeeklyWatchTests(unittest.TestCase):
    def games(self):
        final_broad = watch_game("g-final-broad", "2026-09-10T00:20:00Z", "Final",
                                 [watch_team("1", "m1", 1), watch_team("2", "m1", 1), watch_team("3", "m2", 1), watch_team("4", "m2", 1)], remaining=False)
        live = watch_game("g-live-concentrated", "2026-09-11T00:35:00Z", "Scheduled", [watch_team("1", "m1", 3), watch_team("2", "m1", 3)], locked=6)
        wide = watch_game("g-upcoming-wide", "2026-09-13T17:00:00Z", "Scheduled", [watch_team("1", "m1", 1), watch_team("3", "m2", 1), watch_team("5", "m3", 1)])
        options = watch_game("g-options-only", "2026-09-14T00:20:00Z", "Scheduled", [watch_team("6", "m3", 0)])
        return final_broad, live, wide, options

    def test_ranking_is_starter_exposure_driven(self):
        final_broad, live, wide, options = self.games()
        context = {"SchemaVersion": 3, "Games": [live, wide, final_broad, options], "MustWatchGames": []}
        result = fgc.add_weekly_watch_context(context)
        ids = [g["GameID"] for g in result["MustWatchGames"]]
        self.assertEqual(4, result["SchemaVersion"])
        self.assertEqual(["g-final-broad", "g-upcoming-wide", "g-live-concentrated"], ids)
        first = result["MustWatchGames"][0]
        self.assertEqual(4, first["DirectStarterFantasyTeamCount"])
        self.assertEqual(2, first["FantasyMatchupCount"])
        self.assertIn("4", first["DirectStarterFantasyTeamIDs"])
        self.assertEqual(1, final_broad["RemainingRelevance"]["MustWatchRank"])
        self.assertIsNone(options["RemainingRelevance"]["MustWatchRank"])

    def test_state_changes_do_not_reorder(self):
        final_broad, live, wide, options = self.games()
        context = {"SchemaVersion": 3, "Games": [live, wide, final_broad, options]}
        fgc.add_weekly_watch_context(context)
        live["Status"] = "Final"
        live["RemainingRelevance"].update({"HasRemainingRelevance": False, "LockedActiveStarterCount": 0})
        final_broad["Status"] = "Scheduled"
        final_broad["RemainingRelevance"].update({"HasRemainingRelevance": True, "LockedActiveStarterCount": 4})
        again = fgc.add_weekly_watch_context(context)
        self.assertEqual(["g-final-broad", "g-upcoming-wide", "g-live-concentrated"], [g["GameID"] for g in again["MustWatchGames"]])

    def test_games_without_remaining_relevance_rank_with_zero_counts(self):
        game = {"GameID": "g", "DecisionWindowID": "w", "StartsAtUtc": "2026-09-10T00:00:00Z", "Relevance": {"StarterCount": 1},
                "FantasyTeams": [watch_team("1", "m", 1)]}
        row = fgc.add_weekly_watch_context({"SchemaVersion": 1, "Games": [game]})["MustWatchGames"][0]
        self.assertEqual(0, row["UnlockedStarterCount"])
        self.assertEqual(1, row["DirectStarterFantasyTeamCount"])


class RelevanceContextTests(unittest.TestCase):
    def test_remaining_relevance_and_breadth_ranking(self):
        wide_time, concentrated_time = "2026-09-13T17:00:00Z", "2026-09-13T20:25:00Z"

        def team(team_id, players):
            return {"FantasyTeamID": team_id, "Players": players}

        teams = [
            team("1", [player("w1", "g-wide", wide_time), player("c1", "g-concentrated", concentrated_time), player("c2", "g-concentrated", concentrated_time)]),
            team("2", [player("w2", "g-wide", wide_time), player("c3", "g-concentrated", concentrated_time), player("c4", "g-concentrated", concentrated_time)]),
            team("3", [player("w3", "g-wide", wide_time)]),
            team("4", []),
        ]
        matchups = [
            {"FantasyMatchupID": "m12", "TeamIDs": ["1", "2"], "Teams": []},
            {"FantasyMatchupID": "m34", "TeamIDs": ["3", "4"], "Teams": []},
        ]
        games = [
            {"GameID": "g-concentrated", "DecisionWindowID": concentrated_time, "StartsAtUtc": concentrated_time, "Relevance": {"StarterCount": 4}, "FantasyTeams": [
                watch_team("1", "m12", 2), watch_team("2", "m12", 2)]},
            {"GameID": "g-wide", "DecisionWindowID": wide_time, "StartsAtUtc": wide_time, "Relevance": {"StarterCount": 3}, "FantasyTeams": [
                watch_team("1", "m12", 1), watch_team("2", "m12", 1), watch_team("3", "m34", 1)]},
        ]
        context = {"SchemaVersion": 1, "FantasyMatchups": matchups, "Games": games}
        fgc.add_relevance_context(context, {"FantasyRelevance": {"Teams": teams}}, parse_instant_text)
        wide = next(g for g in games if g["GameID"] == "g-wide")
        concentrated = next(g for g in games if g["GameID"] == "g-concentrated")
        self.assertEqual(3, wide["RemainingRelevance"]["DirectStarterFantasyTeamCount"])
        self.assertEqual(2, concentrated["RemainingRelevance"]["DirectStarterFantasyTeamCount"])
        self.assertEqual(4, concentrated["RemainingRelevance"]["UnlockedStarterCount"])
        self.assertEqual(2, context["SchemaVersion"])
        fgc.add_weekly_watch_context(context)
        self.assertEqual("g-wide", context["MustWatchGames"][0]["GameID"])
        first = matchups[0]["RemainingRelevance"]
        self.assertEqual("both-sides", first["State"])
        self.assertEqual(wide_time, first["NextScoringWindowID"])
        self.assertEqual(concentrated_time, first["FinalScoringWindowID"])
        # a one-game final window is a scalar in the delivery, as the PowerShell serialization produced it
        self.assertEqual("g-concentrated", first["FinalScoringGameIDs"])
        self.assertEqual("left-only", matchups[1]["RemainingRelevance"]["State"])

    def test_locked_starter_needs_a_direct_scoring_path(self):
        teams = [{"FantasyTeamID": "1", "Players": [player("p", "g", "2026-09-13T17:00:00Z", state="locked-active", direct=False)]}]
        context = {"SchemaVersion": 1, "FantasyMatchups": [{"FantasyMatchupID": "m", "TeamIDs": ["1", "2"], "Teams": []}],
                   "Games": [{"GameID": "g", "DecisionWindowID": "2026-09-13T17:00:00Z", "StartsAtUtc": "2026-09-13T17:00:00Z", "FantasyTeams": []}]}
        fgc.add_relevance_context(context, {"FantasyRelevance": {"Teams": teams}}, parse_instant_text)
        self.assertEqual("none", context["FantasyMatchups"][0]["RemainingRelevance"]["State"])
        self.assertFalse(context["Games"][0]["RemainingRelevance"]["HasRemainingRelevance"])


if __name__ == "__main__":
    unittest.main()
