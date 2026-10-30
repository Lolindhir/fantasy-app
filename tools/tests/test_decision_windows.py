"""Decision Windows base (ADR-074, Issue #1199 section 2, step 2): windows, locks, lineup evaluation and lookahead with
constructed weeks. The derivation core takes explicit data only, so no real league, player or schedule data is hard-wired."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import decision_windows as cli  # noqa: E402
from derived_data_lib import decision_windows as dw  # noqa: E402

SEASON = "2030"


def key(value):
    """Team join key stand-in: legacy numeric IDs join the canonical abbreviation."""
    text = str(value).strip() if value is not None else ""
    return {"1": "AAA", "2": "BBB"}.get(text, text) or None


def game(game_id, week, starts, away, home):
    return {"GameID": game_id, "Week": week, "StartsAtUtc": starts, "AwayTeamID": away, "AwayTeamAbbr": away,
            "HomeTeamID": home, "HomeTeamAbbr": home}


# Week 1: AAA@BBB and CCC@DDD kick off together, EEE@FFF twenty minutes later; GGG and HHH have a bye.
GAMES = [
    game("w1a", 1, "2030-09-08T17:00:00Z", "AAA", "BBB"),
    game("w1b", 1, "2030-09-08T17:00:00Z", "CCC", "DDD"),
    game("w1c", 1, "2030-09-08T17:20:00Z", "EEE", "FFF"),
    game("w2a", 2, "2030-09-15T17:00:00Z", "AAA", "CCC"),
    game("w2b", 2, "2030-09-15T20:25:00Z", "EEE", "GGG"),
]
ASSIGN = [
    {"PlayerID": "p1", "NFLTeamID": "AAA"}, {"PlayerID": "p2", "NFLTeamID": "CCC"}, {"PlayerID": "p3", "NFLTeamID": "EEE"},
    {"PlayerID": "p4", "NFLTeamID": "GGG"}, {"PlayerID": "p5", "NFLTeamID": None}, {"PlayerID": "p6", "NFLTeamID": "ZZZ"},
]


def roster(team, players, starters):
    return {"FantasyTeamID": team, "PlayerIDs": players, "StarterIDs": starters}


def facts(rosters, assignments=None, games=None, week=1, expected=2):
    return dw.derive_facts(SEASON, week, GAMES if games is None else games, rosters, ASSIGN if assignments is None else assignments, expected, key)


def issues(evaluation):
    return {(i["Code"], i["PlayerID"], i["Count"]) for i in evaluation["Issues"]}


class WindowTests(unittest.TestCase):
    def test_simultaneous_kickoffs_share_one_window_and_offset_kickoffs_are_separate(self):
        windows = facts([])["DecisionWindows"]
        self.assertEqual(["2030-09-08T17:00:00Z", "2030-09-08T17:20:00Z"], [w["StartsAtUtc"] for w in windows])
        self.assertEqual(["w1a", "w1b"], [g["GameID"] for g in windows[0]["Games"]])
        self.assertEqual(["AAA", "BBB", "CCC", "DDD"], windows[0]["ParticipatingNFLTeamIDs"])
        self.assertEqual("available", windows[0]["FantasyContextState"])

    def test_only_the_lineup_week_games_form_windows(self):
        self.assertEqual(["2030-09-15T17:00:00Z", "2030-09-15T20:25:00Z"], [w["StartsAtUtc"] for w in facts([], week=2)["DecisionWindows"]])

    def test_offsets_normalize_to_utc(self):
        games = [game("x", 1, "2030-09-08T13:00:00-04:00", "AAA", "BBB")]
        self.assertEqual("2030-09-08T17:00:00Z", facts([], games=games)["DecisionWindows"][0]["StartsAtUtc"])


class LockFactTests(unittest.TestCase):
    def test_kinds_scheduled_bye_no_team_and_unknown(self):
        result = facts([roster(1, ["p1", "p4", "p5", "p6", "p9"], ["p1"])])
        kinds = {f["PlayerID"]: f["Kind"] for f in result["PlayerLockFacts"]}
        self.assertEqual({"p1": "scheduled", "p4": "bye", "p5": "no-team", "p6": "unknown", "p9": "unknown"}, kinds)
        scheduled = next(f for f in result["PlayerLockFacts"] if f["PlayerID"] == "p1")
        self.assertEqual(("w1a", "2030-09-08T17:00:00Z", True), (scheduled["GameID"], scheduled["DecisionWindowID"], scheduled["IsStarter"]))

    def test_team_join_uses_the_canonical_key(self):
        result = facts([roster(1, ["p1"], [])], assignments=[{"PlayerID": "p1", "NFLTeamID": "1"}])
        self.assertEqual("scheduled", result["PlayerLockFacts"][0]["Kind"])
        self.assertEqual("1", result["PlayerLockFacts"][0]["NFLTeamID"])

    def test_ambiguous_player_assignment_is_unknown(self):
        result = facts([roster(1, ["p1"], [])], assignments=[{"PlayerID": "p1", "NFLTeamID": "AAA"}, {"PlayerID": "p1", "NFLTeamID": "CCC"}])
        self.assertEqual("unknown", result["PlayerLockFacts"][0]["Kind"])

    def test_team_with_two_games_in_the_week_is_unknown(self):
        games = GAMES + [game("w1d", 1, "2030-09-12T00:15:00Z", "AAA", "HHH")]
        self.assertEqual("unknown", facts([roster(1, ["p1"], [])], games=games)["PlayerLockFacts"][0]["Kind"])

    def test_affected_fantasy_teams_per_window_are_sorted_as_text(self):
        result = facts([roster(10, ["p1"], ["p1"]), roster(2, ["p2"], []), roster(1, ["p3"], [])])
        first = result["DecisionWindows"][0]["AffectedFantasyTeams"]
        self.assertEqual([10, 2], [t["FantasyTeamID"] for t in first])
        self.assertEqual((1, 1), (first[0]["AffectedRosteredPlayerCount"], first[0]["AffectedStarterCount"]))
        self.assertEqual([1], [t["FantasyTeamID"] for t in result["DecisionWindows"][1]["AffectedFantasyTeams"]])
        self.assertEqual([1, 10, 2], [e["FantasyTeamID"] for e in result["TeamLineupEvaluations"]])


class LineupEvaluationTests(unittest.TestCase):
    def evaluate(self, rosters, **kw):
        return facts(rosters, **kw)["TeamLineupEvaluations"]

    def test_ready_lineup(self):
        evaluation = self.evaluate([roster(1, ["p1", "p2"], ["p1", "p2"])])[0]
        self.assertEqual(("ready", 2, 2, 0, []), (evaluation["State"], evaluation["ExpectedStarterCount"], evaluation["StarterCount"], evaluation["OpenStarterSlots"], evaluation["Issues"]))

    def test_open_slots_and_empty_slot_marker(self):
        evaluation = self.evaluate([roster(1, ["p1"], ["p1", "0", None])], expected=3)[0]
        self.assertEqual("action-required", evaluation["State"])
        self.assertEqual({("OPEN_STARTER_SLOT", None, 2)}, issues(evaluation))
        self.assertEqual(2, evaluation["OpenStarterSlots"])

    def test_starter_overflow_is_unknown(self):
        evaluation = self.evaluate([roster(1, ["p1", "p2", "p3"], ["p1", "p2", "p3"])])[0]
        self.assertEqual("unknown", evaluation["State"])
        self.assertIn(("STARTER_COUNT_OVERFLOW", None, 1), issues(evaluation))
        self.assertEqual(0, evaluation["OpenStarterSlots"])

    def test_starter_on_bye_needs_action_and_bench_bye_is_ignored(self):
        self.assertEqual({("STARTER_ON_BYE", "p4", None)}, issues(self.evaluate([roster(1, ["p1", "p4"], ["p1", "p4"])])[0]))
        self.assertEqual([], self.evaluate([roster(1, ["p1", "p4"], ["p1"])], expected=1)[0]["Issues"])

    def test_starter_without_team_is_review_and_unresolved_players_are_unknown(self):
        review = self.evaluate([roster(1, ["p1", "p5"], ["p1", "p5"])])[0]
        self.assertEqual(("review", {("STARTER_WITHOUT_NFL_TEAM", "p5", None)}), (review["State"], issues(review)))
        unknown = self.evaluate([roster(1, ["p1", "p6", "p9"], ["p1", "p6"])], expected=2)[0]
        self.assertEqual("unknown", unknown["State"])
        self.assertEqual({("STARTER_LOCK_UNKNOWN", "p6", None), ("UNRESOLVED_ROSTER_PLAYER", "p9", None)}, issues(unknown))

    def test_structure_problems_are_unknown_not_guessed(self):
        evaluation = self.evaluate([{"FantasyTeamID": 1, "PlayerIDs": "p1", "StarterIDs": ["p1", "p1", "p7", ["x"]]}], expected=0)[0]
        codes = {i["Code"] for i in evaluation["Issues"]}
        self.assertEqual({"MALFORMED_ROSTER_STRUCTURE", "DUPLICATE_STARTER", "STARTER_NOT_IN_ROSTER", "MALFORMED_STARTER_PLAYER", "STARTER_COUNT_OVERFLOW"}, codes)
        self.assertEqual("unknown", evaluation["State"])
        missing = self.evaluate([{"FantasyTeamID": 1}], expected=0)[0]
        self.assertEqual({"MALFORMED_ROSTER_STRUCTURE", "MALFORMED_STARTER_STRUCTURE"}, {i["Code"] for i in missing["Issues"]})

    def test_duplicate_roster_players_and_sorted_unique_issues(self):
        evaluation = self.evaluate([roster(1, ["p2", "p1", "p2", "p1"], ["p1", "p2"])])[0]
        self.assertEqual([("DUPLICATE_ROSTER_PLAYER", "p1"), ("DUPLICATE_ROSTER_PLAYER", "p2")], [(i["Code"], i["PlayerID"]) for i in evaluation["Issues"]])

    def test_issue_state_precedence(self):
        both = self.evaluate([roster(1, ["p4", "p6"], ["p4", "p6"])])[0]
        self.assertEqual("unknown", both["State"])

    def test_fail_closed_inputs(self):
        with self.assertRaises(dw.DecisionWindowsError):
            facts([roster(1, ["p1"], []), roster(2, ["p1"], [])])  # one player on two fantasy teams
        with self.assertRaises(dw.DecisionWindowsError):
            facts([roster(1, [], []), roster(1, [], [])])  # duplicate fantasy team
        with self.assertRaises(dw.DecisionWindowsError):
            facts([roster(None, [], [])])
        with self.assertRaises(dw.DecisionWindowsError):
            facts([], games=GAMES + [GAMES[0]])  # duplicate GameID
        with self.assertRaises(dw.DecisionWindowsError):
            facts([], games=[game("x", 1, "not a time", "AAA", "BBB")])
        with self.assertRaises(dw.DecisionWindowsError):
            facts([], assignments=[{"PlayerID": "0", "NFLTeamID": "AAA"}])
        with self.assertRaises(dw.DecisionWindowsError):
            facts([], games=[dict(GAMES[0], Week=None)])


class ModelTests(unittest.TestCase):
    def model(self, lineup_week, last=3, rosters=None):
        return dw.build_base_model("L1", SEASON, lineup_week, last, GAMES, rosters if rosters is not None else [roster(2, ["p1"], []), roster(1, [], [])], ASSIGN, 2, key)

    def test_current_week_carries_a_pending_lookahead_of_the_next_week(self):
        model = self.model(1)
        self.assertEqual(("L1", SEASON, 1, 3, 1), (model["LeagueID"], model["Season"], model["LineupWeek"], model["LastLineupWeek"], model["SchemaVersion"]))
        lookahead = model["LookaheadDecisionWindow"]
        self.assertEqual(("2030-09-15T17:00:00Z", 2, "pending", []), (lookahead["StartsAtUtc"], lookahead["Week"], lookahead["FantasyContextState"], lookahead["AffectedFantasyTeams"]))
        self.assertEqual(2, len(model["DecisionWindows"]))

    def test_last_lineup_week_has_no_lookahead(self):
        self.assertIsNone(self.model(3)["LookaheadDecisionWindow"])

    def test_next_week_without_games_has_no_lookahead(self):
        self.assertIsNone(dw.build_base_model("L1", SEASON, 2, 3, GAMES, [], [], 2, key)["LookaheadDecisionWindow"])

    def test_before_week_one_everything_is_pending_with_the_first_window_as_lookahead(self):
        model = self.model(0)
        self.assertEqual([], model["DecisionWindows"] + model["PlayerLockFacts"])
        self.assertEqual("2030-09-08T17:00:00Z", model["LookaheadDecisionWindow"]["StartsAtUtc"])
        self.assertEqual("pending", model["LookaheadDecisionWindow"]["FantasyContextState"])
        self.assertEqual([1, 2], [e["FantasyTeamID"] for e in model["TeamLineupEvaluations"]])
        self.assertEqual(("pending", 2, None, None, []), tuple(model["TeamLineupEvaluations"][0][k] for k in ("State", "ExpectedStarterCount", "StarterCount", "OpenStarterSlots", "Issues")))

    def test_after_the_last_lineup_week_everything_is_pending_without_lookahead(self):
        model = self.model(4)
        self.assertEqual(([], None), (model["DecisionWindows"], model["LookaheadDecisionWindow"]))
        self.assertEqual("pending", model["TeamLineupEvaluations"][0]["State"])

    def test_last_lineup_week_must_be_positive(self):
        with self.assertRaises(dw.DecisionWindowsError):
            self.model(1, last=0)

    def test_same_inputs_give_the_same_result(self):
        self.assertEqual(self.model(1), self.model(1))


class AdapterTests(unittest.TestCase):
    def record(self, game_id, week, epoch, season="2030"):
        return {"gameID": game_id, "season": season, "gameWeek": f"Week {week}", "gameTime_epoch": epoch,
                "teamIDAway": "AAA", "teamIDHome": "BBB", "away": "AAA", "home": "BBB"}

    def test_schedule_games_converts_epoch_and_filters_season_and_week_label(self):
        records = [self.record("g1", 1, "1920000000.0"), self.record("g2", 1, "1920000000", season="2029"),
                   dict(self.record("g3", 1, "1920000000"), gameWeek="Wildcard")]
        games = dw.schedule_games(records, "2030", 1, 3)
        self.assertEqual(["g1"], [g["GameID"] for g in games])
        self.assertEqual("2030-11-04T05:20:00Z", games[0]["StartsAtUtc"])

    def test_missing_epoch_fails_only_for_required_weeks(self):
        far = self.record("g9", 9, "")
        self.assertEqual([], dw.schedule_games([far], "2030", 1, 17))
        with self.assertRaises(dw.DecisionWindowsError):
            dw.schedule_games([self.record("g1", 1, "")], "2030", 1, 17)
        with self.assertRaises(dw.DecisionWindowsError):
            dw.schedule_games([self.record("g2", 2, "")], "2030", 1, 17)  # lookahead week is required too
        self.assertEqual([], dw.schedule_games([self.record("g2", 2, "")], "2030", 1, 1))  # last lineup week: no lookahead
        with self.assertRaises(dw.DecisionWindowsError):
            dw.schedule_games([self.record("g1", 1, "")], "2030", 0, 17)

    def test_unparseable_epoch_and_missing_identity(self):
        with self.assertRaises(dw.DecisionWindowsError):
            dw.schedule_games([self.record("g1", 1, "soon")], "2030", 1, 17)
        with self.assertRaises(dw.DecisionWindowsError):
            dw.schedule_games([dict(self.record("g1", 1, "1920000000"), teamIDHome="")], "2030", 1, 17)

    def test_expected_starter_count_excludes_bench(self):
        self.assertEqual(3, dw.expected_starter_count(["QB", "RB", "FLEX", "BN", " bn ", ""]))
        for bad in (None, ["BN", "BN"]):
            with self.assertRaises(dw.DecisionWindowsError):
                dw.expected_starter_count(bad)

    def test_canonical_rosters_use_the_sleeper_ids_and_provider_roster_id(self):
        def ref(sleeper):
            return {"CanonicalPlayerID": f"NFLP-{sleeper}", "ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": sleeper}]}

        def canonical(roster_id, players, starters):
            return {"CanonicalLeagueRosterID": f"clr-{roster_id}", "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": roster_id}],
                    "Players": [ref(p) for p in players], "Starters": [ref(s) for s in starters]}

        result = dw.rosters_from_canonical([canonical("10", ["1", "2"], ["1"]), canonical("2", ["3"], [])], "test")
        self.assertEqual([2, 10], [r["FantasyTeamID"] for r in result])
        self.assertEqual((["1", "2"], ["1"]), (result[1]["PlayerIDs"], result[1]["StarterIDs"]))
        broken = canonical("1", ["1"], [])
        broken["Players"][0]["ProviderMappings"] = []
        with self.assertRaises(dw.DecisionWindowsError):
            dw.rosters_from_canonical([broken], "test")


class CliTests(unittest.TestCase):
    def test_missing_inputs_fail_closed_with_a_message(self):
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run(
                [sys.executable, str(TOOLS / "decision_windows.py"), "resolve", "--league", "none", "--season", "2030", "--repo-root", root],
                capture_output=True, text=True, check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("decision_windows:", result.stderr)
        self.assertEqual("", result.stdout)

    def test_cli_main_rejects_a_naive_instant(self):
        self.assertEqual(1, cli.main(["resolve", "--league", "none", "--season", "2030", "--at", "2030-09-08T17:00:00"]))


if __name__ == "__main__":
    unittest.main()
