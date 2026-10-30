"""Matchups season model (ADR-075, Issue #1199 section 3, step 2): pairings in neutral order, effective scores, the per-matchup
CompletionState and the Summary with constructed seasons. Ported from MatchupReadModelRegressionTest.ps1; no real league, player
or schedule data is hard-wired."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import matchup_context as mc  # noqa: E402

LEAGUE = "test-league"
SEASON = 2030


def at(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def row(team, canonical_player, points, custom=None, matchup=1, week=1, clmup="clmup-test"):
    return {
        "CanonicalLeagueMatchupID": clmup,
        "CanonicalLeagueRosterID": f"clr-{team}",
        "CustomPoints": custom,
        "Points": points,
        "ProviderMappings": [{"Provider": "Sleeper", "ProviderMatchupID": matchup, "ProviderRosterID": str(team)}],
        "StarterPoints": [{"Player": {"CanonicalPlayerID": canonical_player, "ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": f"P{team}"}]}, "Points": points}],
        "Week": week,
    }


def decision_facts(team1_path=False, team2_path=False, team1_repairable=False, omit_team2_evaluation=False):
    slots = [{"SlotID": "QB-1", "State": "unlocked", "Repairability": {"State": "repairable"}}] if team1_repairable else []
    evaluations = [{"FantasyTeamID": 1, "State": "valid"}]
    if not omit_team2_evaluation:
        evaluations.append({"FantasyTeamID": 2, "State": "valid"})
    return {
        "Season": str(SEASON),
        "LineupWeek": 1,
        "FantasyRelevance": {"Teams": [
            {"FantasyTeamID": 1, "HasRemainingScoringPath": team1_path, "Slots": slots},
            {"FantasyTeamID": 2, "HasRemainingScoringPath": team2_path, "Slots": []},
        ]},
        "TeamLineupEvaluations": evaluations,
    }


ORDER = {"2": 0, "1": 1}  # team 2 ranks ahead of team 1 in the All-Time Overall order


class Fixture:
    """A temporary repository root with one constructed league season."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.season_dir = self.root / "data-source/leagues" / LEAGUE / "seasons" / str(SEASON)
        self.league = {
            "Season": SEASON, "Status": "in_season", "RosterPositions": ["QB", "BN"],
            "Settings": {"leg": 1, "start_week": 1, "playoff_week_start": 2, "playoff_round_type": 0},
            "WeekStructure": {"StartWeek": 1, "PlayoffStartWeek": 2, "PlayoffRoundType": 0, "ExpectedLastLeagueWeek": 3, "FinalLeagueWeek": None},
        }
        self.team1, self.team2 = row(1, "NFLP-1", 10.0), row(2, "NFLP-2", 7.0)
        self.write_league()
        self.write_week(1, [self.team1, self.team2])
        self.write_week(2, [row(1, "NFLP-1", 0.0, matchup=2, week=2), row(2, "NFLP-2", 0.0, matchup=2, week=2)])
        games = [
            {"GameID": "g1", "GameType": "REG", "Week": 1, "GameDay": "2030-09-10", "GameTime": "20:15", "AwayTeam": "AAA", "HomeTeam": "BBB"},
            {"GameID": "g2", "GameType": "REG", "Week": 1, "GameDay": "2030-09-14", "GameTime": "20:15", "AwayTeam": "CCC", "HomeTeam": "DDD"},
            {"GameID": "g3", "GameType": "REG", "Week": 2, "GameDay": "2030-09-17", "GameTime": "20:15", "AwayTeam": "AAA", "HomeTeam": "CCC"},
        ]
        self.write(self.root / f"data-source/nfl/schedules/{SEASON}.json", {"SchemaVersion": 2, "Season": SEASON, "Games": games})
        self.write_finality(g1=True, g2=False)
        self.write(self.root / f"data-source/nfl/weekly-rosters/{SEASON}/01.json", {"SchemaVersion": 2, "Season": SEASON, "Week": 1, "Records": [
            {"CanonicalPlayerID": "NFLP-1", "Team": "AAA"}, {"CanonicalPlayerID": "NFLP-2", "Team": "AAA"}]})

    def close(self):
        self.tmp.cleanup()

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def write_league(self):
        self.write(self.season_dir / "league.json", self.league)

    def write_week(self, week, rows):
        self.write(self.season_dir / "matchups" / f"week-{week}.json", rows)

    def write_finality(self, g1, g2):
        self.write(self.root / f"data-source/nfl/game-finality/{SEASON}.json", {"SchemaVersion": 2, "Season": SEASON, "Games": [
            {"GameID": "g1", "GameType": "REG", "Week": 1, "Final": g1}, {"GameID": "g2", "GameType": "REG", "Week": 1, "Final": g2}]})

    def model(self, now="2030-09-15T18:00:00Z", facts=None, live=None, live_week=0, evidence=True):
        return mc.build_matchups_model(self.root, LEAGUE, SEASON, ORDER, at(now), facts, live, live_week, evidence)


LIVE = [{"roster_id": 1, "matchup_id": 1, "points": 0.0, "custom_points": 0.0}, {"roster_id": 2, "matchup_id": 1, "points": 7.0, "custom_points": None}]


class ActiveWeekTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def test_final_matchup_follows_neutral_order_and_effective_scores(self):
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(), LIVE, 1)
        self.assertEqual(1, len(model["Weeks"]), "future playoff pairings are not materialized before playoff start")
        week = model["Weeks"][0]
        self.assertEqual(("regular-season", "final", "final"), (week["Stage"], week["CompletionState"], week["Matchups"][0]["CompletionState"]))
        matchup = week["Matchups"][0]
        self.assertEqual([2, 1], [p["TeamID"] for p in matchup["Participants"]])
        self.assertEqual((0.0, "adjusted"), (matchup["Participants"][1]["Points"], matchup["Participants"][1]["ScoreKind"]))
        self.assertEqual({"Type": "win", "WinnerTeamID": 2}, matchup["Result"])
        self.assertEqual({"LastCompletedWeek": 1, "ActiveOrNextWeek": None}, model["Summary"])

    def test_live_rows_of_another_week_never_overwrite_the_active_week(self):
        wrong = [{"roster_id": 1, "matchup_id": 1, "points": 0.0, "custom_points": None}, {"roster_id": 2, "matchup_id": 1, "points": 0.0, "custom_points": None}]
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(), wrong, 2)
        points = {p["TeamID"]: p["Points"] for p in model["Weeks"][0]["Matchups"][0]["Participants"]}
        self.assertEqual({1: 10.0, 2: 7.0}, points)
        self.assertEqual("final", model["Weeks"][0]["CompletionState"])

    def test_remaining_scoring_path_keeps_the_week_open(self):
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(team1_path=True), LIVE, 1)
        self.assertEqual("open", model["Weeks"][0]["CompletionState"])
        self.assertIsNone(model["Weeks"][0]["Matchups"][0]["Result"])
        self.assertEqual({"LastCompletedWeek": None, "ActiveOrNextWeek": 1}, model["Summary"])

    def test_repairable_lineup_counts_as_a_remaining_path(self):
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(team1_repairable=True), LIVE, 1)
        self.assertEqual("open", model["Weeks"][0]["Matchups"][0]["CompletionState"])

    def test_missing_lineup_evidence_fails_closed_to_unknown(self):
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(omit_team2_evaluation=True), LIVE, 1)
        self.assertEqual("unknown", model["Weeks"][0]["Matchups"][0]["CompletionState"])
        self.assertIsNone(model["Weeks"][0]["Matchups"][0]["Result"])

    def test_unavailable_active_score_evidence_is_unknown_even_when_the_lineup_is_decided(self):
        model = self.fx.model("2030-09-13T18:00:00Z", decision_facts(), [], 0, evidence=False)
        self.assertEqual("unknown", model["Weeks"][0]["Matchups"][0]["CompletionState"])

    def test_decision_facts_of_another_season_do_not_make_a_week_active(self):
        other = decision_facts()
        other["Season"] = "1999"
        self.assertEqual("final", self.fx.model("2030-09-15T18:00:00Z", other, LIVE, 1)["Weeks"][0]["CompletionState"])


class HistoricalStyleTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def test_an_unrelated_unfinished_game_does_not_block_finality(self):
        model = self.fx.model()
        self.assertEqual(("final", "final"), (model["Weeks"][0]["CompletionState"], model["Weeks"][0]["Matchups"][0]["CompletionState"]))

    def test_weekly_roster_teams_resolve_the_starter_game(self):
        assignments = mc.weekly_assignment_map(self.fx.root, SEASON, 1)
        self.assertEqual(["AAA"], assignments["NFLP-1"])
        games = [g for g in mc.schedule_games(self.fx.root, SEASON) if g["Week"] == 1]
        finality = mc.finality_map(self.fx.root, SEASON)
        self.assertEqual("final", mc.starter_game_resolution(self.fx.team1["StarterPoints"][0], games, assignments, finality))

    def test_a_running_starter_game_keeps_the_matchup_open(self):
        self.fx.write_finality(g1=False, g2=False)
        self.assertEqual("open", self.fx.model()["Weeks"][0]["CompletionState"])

    def test_missing_finality_or_roster_evidence_is_unknown(self):
        (self.fx.root / f"data-source/nfl/game-finality/{SEASON}.json").unlink()
        self.assertEqual("unknown", self.fx.model()["Weeks"][0]["CompletionState"])

    def test_a_matchup_before_the_first_kickoff_is_open_with_starter_evidence(self):
        self.assertEqual("open", self.fx.model("2030-09-01T00:00:00Z")["Weeks"][0]["Matchups"][0]["CompletionState"])
        self.fx.team1["StarterPoints"], self.fx.team2["StarterPoints"] = [], []
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        self.assertEqual("unknown", self.fx.model("2030-09-01T00:00:00Z")["Weeks"][0]["Matchups"][0]["CompletionState"])

    def test_first_kickoff_is_the_earliest_eastern_kickoff_in_utc(self):
        self.assertEqual("2030-09-11T00:15:00Z", self.fx.model()["Weeks"][0]["FirstKickoffUtc"])

    def test_stage_follows_the_playoff_start_week(self):
        self.fx.league["WeekStructure"]["ExpectedLastLeagueWeek"] = 2
        self.fx.league["Settings"]["leg"] = 2
        self.fx.write_league()
        stages = [w["Stage"] for w in self.fx.model()["Weeks"]]
        self.assertEqual(["regular-season", "playoffs"], stages)

    def test_a_tie_has_no_winner(self):
        self.fx.write_week(1, [row(1, "NFLP-1", 5.0), row(2, "NFLP-2", 5.0)])
        self.assertEqual({"Type": "tie", "WinnerTeamID": None}, self.fx.model()["Weeks"][0]["Matchups"][0]["Result"])


class EmptyStarterSlotTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)
        # Week-7 production analogue: Sleeper sent one explicit "0" slot and one real player instead of two real starters.
        self.fx.league["RosterPositions"] = ["QB", "RB", "BN"]
        self.fx.write_league()

    def state(self):
        return self.fx.model()["Weeks"][0]["CompletionState"]

    def test_a_missing_starter_without_explicit_empty_slot_evidence_stays_unknown(self):
        self.assertEqual("unknown", self.state())

    def test_an_explicit_empty_slot_allows_final_without_changing_scores(self):
        self.fx.team1["EmptyStarterSlots"] = self.fx.team2["EmptyStarterSlots"] = 1
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        model = self.fx.model()
        self.assertEqual("final", model["Weeks"][0]["CompletionState"])
        self.assertEqual({"LastCompletedWeek": 1, "ActiveOrNextWeek": None}, model["Summary"])
        self.assertEqual(1, model["Weeks"][0]["Matchups"][0]["Result"]["WinnerTeamID"])

    def test_inconsistent_slot_and_starter_counts_fail_closed(self):
        self.fx.team1["EmptyStarterSlots"], self.fx.team2["EmptyStarterSlots"] = 1, 2
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        self.assertEqual("unknown", self.state())

    def test_a_non_integer_slot_count_fails_closed(self):
        self.fx.team1["EmptyStarterSlots"] = self.fx.team2["EmptyStarterSlots"] = 1.0
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        self.assertEqual("unknown", self.state())

    def test_a_real_starter_without_team_evidence_stays_unknown(self):
        self.fx.team1["EmptyStarterSlots"] = self.fx.team2["EmptyStarterSlots"] = 1
        self.fx.team2["StarterPoints"][0]["Player"]["CanonicalPlayerID"] = "NFLP-UNMAPPED"
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        self.assertEqual("unknown", self.state())

    def test_a_running_starter_game_wins_over_the_empty_slot(self):
        self.fx.team1["EmptyStarterSlots"] = self.fx.team2["EmptyStarterSlots"] = 1
        self.fx.write_week(1, [self.fx.team1, self.fx.team2])
        self.fx.write_finality(g1=False, g2=False)
        self.assertEqual("open", self.state())


class PairingTests(unittest.TestCase):
    def test_matchup_id_is_independent_of_row_order_and_participant_order_follows_the_neutral_order(self):
        a, b = row(1, "NFLP-1", 10.0), row(2, "NFLP-2", 7.0)
        first, _ = mc.canonical_pairings(SEASON, 1, [a, b], ORDER)
        second, _ = mc.canonical_pairings(SEASON, 1, [b, a], ORDER)
        self.assertEqual(first[0]["FantasyMatchupID"], second[0]["FantasyMatchupID"])
        self.assertEqual([2, 1], [p["TeamID"] for p in first[0]["Participants"]])

    def test_matchup_id_is_stable(self):
        self.assertEqual(mc.fantasy_matchup_id("2030", 1, [2, 1]), mc.fantasy_matchup_id("2030", 1, ["1", "2"]))
        self.assertRegex(mc.fantasy_matchup_id("2030", 1, [1, 2]), r"^fgm-[0-9a-f]{24}$")
        self.assertNotEqual(mc.fantasy_matchup_id("2030", 1, [1, 2]), mc.fantasy_matchup_id("2030", 2, [1, 2]))
        with self.assertRaises(mc.MatchupContextError):
            mc.fantasy_matchup_id("2030", 1, [1])

    def test_one_sided_malformed_evidence_creates_no_matchup_and_is_surfaced(self):
        malformed = row(1, "NFLP-1", 5.0, matchup=9, clmup="clmup-malformed")
        pairings, found = mc.canonical_pairings(SEASON, 1, [row(1, "NFLP-1", 10.0), row(2, "NFLP-2", 7.0), malformed], ORDER)
        self.assertEqual((1, True), (len(pairings), found))

    def test_a_team_missing_from_the_neutral_order_fails_closed(self):
        with self.assertRaises(mc.MatchupContextError):
            mc.canonical_pairings(SEASON, 1, [row(1, "NFLP-1", 1.0), row(3, "NFLP-3", 2.0)], ORDER)

    def test_a_malformed_week_is_never_final(self):
        fx = Fixture()
        self.addCleanup(fx.close)
        fx.write_week(1, [fx.team1, fx.team2, row(1, "NFLP-1", 5.0, matchup=9, clmup="clmup-malformed")])
        self.assertEqual("unknown", fx.model()["Weeks"][0]["CompletionState"])

    def test_effective_score_prefers_a_custom_score_including_zero(self):
        self.assertEqual({"Points": 3.0, "ScoreKind": "adjusted"}, mc.effective_score(row(1, "N", 12.0, custom=3)))
        self.assertEqual({"Points": 0.0, "ScoreKind": "adjusted"}, mc.effective_score(row(1, "N", 12.0, custom=0.0)))
        self.assertEqual({"Points": None, "ScoreKind": "standard"}, mc.effective_score(row(1, "N", None)))

    def test_a_live_row_of_another_provider_matchup_makes_the_score_evidence_unknown(self):
        live = [{"roster_id": 1, "matchup_id": 7, "points": 1.0, "custom_points": None}]
        pairings, _ = mc.canonical_pairings(SEASON, 1, [row(1, "NFLP-1", 10.0), row(2, "NFLP-2", 7.0)], ORDER, live)
        self.assertTrue(pairings[0]["ScoreEvidenceUnknown"])

    def test_neutral_order_index_uses_the_lowest_place_first_and_fails_closed(self):
        self.assertEqual({"3": 0, "1": 1}, mc.neutral_order_index([{"TeamID": 1, "Place": 2}, {"TeamID": 3, "Place": 1}]))
        for bad in ([], [{"TeamID": 1, "Place": 1}, {"TeamID": 1, "Place": 2}], [{"TeamID": 1, "Place": 1}, {"TeamID": 2, "Place": 1}],
                    [{"TeamID": 1, "Place": 999}], [{"TeamID": "", "Place": 1}]):
            with self.assertRaises(mc.MatchupContextError):
                mc.neutral_order_index(bad)

    def test_participant_order_uses_the_all_time_chain_of_the_product(self):
        product = {"Season": 2030, "AllTime": {"Playoffs": [{"TeamID": 2, "Place": 1}, {"TeamID": 1, "Place": 2}]}}
        self.assertEqual(ORDER, mc.participant_order_from_standings(product))
        with self.assertRaises(mc.MatchupContextError):
            mc.participant_order_from_standings({"Season": 2030, "AllTime": {"Playoffs": []}})


class CurrentRowsTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    @staticmethod
    def full_row(team, week=1):
        player = {"ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": f"P{team}"}]}
        return {"Week": week, "CustomPoints": None, "Points": 3.5, "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": str(team), "ProviderMatchupID": "4"}],
                "Players": [player], "Starters": [player], "PlayerPoints": [{"Player": player, "Points": 3.5}], "StarterPoints": []}

    def test_valid_rows_are_converted_to_the_legacy_shape_and_sorted_by_roster(self):
        self.fx.write_week(1, [self.full_row(2), self.full_row(1)])
        rows = mc.current_matchup_rows(self.fx.root, LEAGUE, SEASON, 1)
        self.assertEqual([1, 2], [r["roster_id"] for r in rows])
        self.assertEqual((4, [3.5], 3.5), (rows[0]["matchup_id"], rows[0]["starters_points"], rows[0]["points"]))

    def test_defects_fail_closed(self):
        broken = self.full_row(1)
        broken["Starters"] = [{"ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": "OUTSIDE"}]}]
        for rows in ([broken], [self.full_row(1), self.full_row(1)], [self.full_row(1, week=2)]):
            self.fx.write_week(1, rows)
            with self.assertRaises(mc.MatchupContextError):
                mc.current_matchup_rows(self.fx.root, LEAGUE, SEASON, 1)
        with self.assertRaises(mc.MatchupContextError):
            mc.current_matchup_rows(self.fx.root, LEAGUE, SEASON, 9)


class KnownLastWeekTests(unittest.TestCase):
    def source(self, **overrides):
        value = {"Status": "in_season", "Settings": {"leg": 4, "playoff_week_start": 15}, "WeekStructure": {"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 15, "PlayoffRoundType": 0}}
        value.update(copy.deepcopy(overrides))
        return value

    def test_regular_season_reveals_weeks_up_to_the_playoff_start_and_playoffs_up_to_the_leg(self):
        self.assertEqual(14, mc.known_last_week(self.source()))
        self.assertEqual(15, mc.known_last_week(self.source(Settings={"leg": 15, "playoff_week_start": 15})))
        self.assertEqual(16, mc.known_last_week(self.source(Settings={"leg": 16, "playoff_week_start": 15})))

    def test_two_week_playoff_rounds_reveal_the_round_pair(self):
        value = self.source(Settings={"leg": 16, "playoff_week_start": 15}, WeekStructure={"ExpectedLastLeagueWeek": 17, "PlayoffStartWeek": 15, "PlayoffRoundType": 2})
        self.assertEqual(16, mc.known_last_week(value))
        value["Settings"]["leg"] = 17
        self.assertEqual(17, mc.known_last_week(value))

    def test_a_complete_league_uses_the_final_league_week_and_an_unresolved_week_fails(self):
        self.assertEqual(16, mc.known_last_week(self.source(Status="complete", WeekStructure={"ExpectedLastLeagueWeek": 17, "FinalLeagueWeek": 16})))
        with self.assertRaises(mc.MatchupContextError):
            mc.known_last_week({"Settings": {}, "WeekStructure": {}})


class LoadWeekTests(unittest.TestCase):
    def test_the_load_week_is_the_capped_lineup_week_and_zero_without_a_lineup(self):
        self.assertEqual(5, mc.matchup_load_week({"LineupWeek": 5}, 17, False))
        self.assertEqual(17, mc.matchup_load_week({"LineupWeek": 20}, 17, False))
        self.assertEqual(0, mc.matchup_load_week({"LineupWeek": 5}, 17, True))
        self.assertEqual(0, mc.matchup_load_week({"LineupWeek": 0}, 17, False))
        self.assertEqual(0, mc.matchup_load_week(None, 17, False))


if __name__ == "__main__":
    unittest.main()


class ShadowCompareTests(unittest.TestCase):
    """The shadow compares computed models exactly with published files; synthetic data only."""

    def setUp(self):
        import matchup_context as cli

        self.cli = cli

    def test_exact_differences_by_path(self):
        published = {"Season": "2030", "Weeks": [{"Week": 1, "CompletionState": "unknown", "Matchups": []}]}
        computed = copy.deepcopy(published)
        self.assertEqual([], self.cli.diff_values(published, computed))
        computed["Weeks"][0]["CompletionState"] = "final"
        self.assertEqual(["Weeks[0].CompletionState: published 'unknown' != computed 'final'"], self.cli.diff_values(published, computed))
        computed["Weeks"].append({})
        self.assertEqual(["Weeks: published 1 items != computed 2"], self.cli.diff_values(published, computed))
        self.assertEqual(["Extra: missing in published file"], self.cli.diff_values({}, {"Extra": 1}))
        self.assertEqual(1, len(self.cli.diff_values({"Id": 1}, {"Id": True})))

    def test_compare_reports_every_file_and_never_writes(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as root:
            data = Path(root) / "public" / "data"
            (data / "past_seasons" / "Matchups").mkdir(parents=True)
            (data / "past_seasons" / "FantasyGameContext").mkdir(parents=True)
            stamp = "2030-09-08T12:00:00Z"
            (data / "Timestamps.json").write_text(json.dumps({"Matchups": stamp, "FantasyGameContext": stamp}), encoding="utf-8")
            (data / "Matchups.json").write_text(json.dumps({"Season": "2030", "Weeks": []}), encoding="utf-8")
            (data / "FantasyGameContext.json").write_text(json.dumps({"Season": "2030", "Week": 1}), encoding="utf-8")
            (data / "past_seasons" / "Matchups" / "Matchups_2029.json").write_text(json.dumps({"Season": "2029"}), encoding="utf-8")
            (data / "past_seasons" / "FantasyGameContext" / "FantasyGameContext_2029.json").write_text(json.dumps({"Season": "2029"}), encoding="utf-8")
            before = sorted(str(p) for p in Path(root).rglob("*"))
            with (
                mock.patch.object(self.cli, "resolve_matchups", side_effect=lambda r, l, s, at: {"Season": str(s), "Weeks": []} if s == 2030 else {"Season": str(s), "X": 1}),
                mock.patch.object(self.cli, "resolve_current_context", return_value=None),
                mock.patch.object(self.cli, "resolve_historical_season", return_value={"Season": "2029"}),
            ):
                report = self.cli.compare_with_published(Path(root), "league", None)
            self.assertEqual([], report["Matchups.json"])
            self.assertIn("not comparable", report["FantasyGameContext.json"])
            self.assertEqual(["X: missing in published file"], report["past_seasons/Matchups/Matchups_2029.json"])
            self.assertEqual([], report["past_seasons/FantasyGameContext/FantasyGameContext_2029.json"])
            self.assertEqual(before, sorted(str(p) for p in Path(root).rglob("*")))
