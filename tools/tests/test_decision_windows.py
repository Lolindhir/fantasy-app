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


class RelevanceTests(unittest.TestCase):
    POSITIONS = ["QB", "RB", "FLEX", "BN", "BN"]
    POS = {"p1": "QB", "p2": "RB", "p3": "WR", "p4": "TE", "p5": "RB", "p6": "QB"}
    STATUS = {"w1a": "Final", "w1b": "Scheduled", "w1c": "Scheduled"}

    def model(self, rosters, at="2030-09-08T17:10:00Z", status=None):
        base = dw.build_base_model("L", SEASON, 1, 18, GAMES, rosters, ASSIGN, 3, key)
        when = dw.parse_instant(at, "at")
        dw.add_relevance(base, self.POSITIONS, rosters, self.POS, self.STATUS if status is None else status, when)
        return dw.add_scoring_path(base)

    def team(self, model):
        return model["FantasyRelevance"]["Teams"][0]

    def test_slots_follow_roster_positions_without_the_bench(self):
        definitions = dw.slot_definitions(["QB", "FLEX", "FLEX", "BN"])
        self.assertEqual(["QB-1", "FLEX-1", "FLEX-2"], [d["SlotID"] for d in definitions])
        self.assertEqual([0, 1, 2], [d["SlotIndex"] for d in definitions])
        with self.assertRaises(dw.DecisionWindowsError):
            dw.slot_definitions(["BN"])

    def test_flex_family_eligibility(self):
        self.assertTrue(dw.slot_eligible("te", "FLEX"))
        self.assertFalse(dw.slot_eligible("QB", "FLEX"))
        self.assertTrue(dw.slot_eligible("QB", "SUPER_FLEX"))
        self.assertTrue(dw.slot_eligible("TE", "REC_FLEX"))
        self.assertFalse(dw.slot_eligible("RB", "REC_FLEX"))
        self.assertTrue(dw.slot_eligible("K", "K"))
        self.assertFalse(dw.slot_eligible(None, "K"))

    def test_slot_states_follow_the_instant(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p3"], "StarterIDs": ["p1", "p2", "p3"]}]
        team = self.team(self.model(r))
        # p1 (AAA, w1a) is final, p2 (CCC, w1b) kicked off at 17:00, p3 (EEE, w1c) kicks off at 17:20.
        self.assertEqual(["completed", "locked-active", "unlocked"], [s["State"] for s in team["Slots"]])
        early = self.team(self.model(r, at="2030-09-08T16:59:59Z", status={}))
        self.assertEqual(["unlocked"] * 3, [s["State"] for s in early["Slots"]])
        self.assertEqual((1, 1, 1), (team["CompletedStarterCount"], team["LockedActiveStarterCount"], team["UnlockedStarterCount"]))

    def test_kickoff_instant_locks_and_bye_or_unknown_are_their_own_states(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p3", "p4", "p6"], "StarterIDs": ["p3", "p4", "p6"]}]
        exactly = self.team(self.model(r, at="2030-09-08T17:20:00Z", status={}))
        self.assertEqual("locked-active", exactly["Slots"][0]["State"])
        self.assertEqual("bye", exactly["Slots"][1]["State"])
        self.assertEqual("unknown", exactly["Slots"][2]["State"])

    def test_empty_slot_keeps_its_position_and_is_unlocked(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p2", "p3"], "StarterIDs": ["p2", "p3"], "StarterSlots": [None, "p2", "p3"]}]
        slots = self.team(self.model(r))["Slots"]
        self.assertEqual([None, "p2", "p3"], [s["CurrentStarterID"] for s in slots])
        self.assertEqual("unlocked", slots[0]["State"])
        self.assertEqual("RB-1", [p for p in self.team(self.model(r))["Players"] if p["PlayerID"] == "p2"][0]["LineupSlotID"])

    def test_bench_candidates_are_eligible_for_unlocked_slots_only(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p3"], "StarterIDs": ["p1", "p2"]}]
        early = {p["PlayerID"]: p for p in self.team(self.model(r, at="2030-09-08T16:00:00Z", status={}))["Players"]}
        self.assertEqual(["FLEX-1"], early["p3"]["EligibleUnlockedSlotIDs"])
        self.assertTrue(early["p3"]["IsBenchCandidate"] and early["p3"]["HasAlternativePath"])
        locked = {p["PlayerID"]: p for p in self.team(self.model(r, at="2030-09-08T17:30:00Z"))["Players"]}
        self.assertEqual([], locked["p3"]["EligibleUnlockedSlotIDs"])
        self.assertFalse(locked["p3"]["IsBenchCandidate"])
        self.assertFalse(locked["p1"]["HasDirectScoringPath"])

    def test_ir_and_taxi_players_are_counted_outside_the_active_roster(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p5", "p6"], "StarterIDs": ["p1"], "ReserveIDs": ["p2"], "TaxiIDs": ["p6"]}]
        team = self.team(self.model(r))
        self.assertEqual((2, 1, 1, 1, 1), (team["ActiveRosterPlayerCount"], team["StarterCount"], team["BenchCount"], team["IRCount"], team["TaxiCount"]))
        self.assertEqual({"ir", "taxi"}, {p["Placement"] for p in team["Players"]} - {"starter", "bench"})

    def test_starter_on_ir_or_taxi_and_starter_overflow_fail_closed(self):
        with self.assertRaises(dw.DecisionWindowsError):
            self.model([{"FantasyTeamID": 1, "PlayerIDs": ["p1"], "StarterIDs": ["p1"], "ReserveIDs": ["p1"]}])
        with self.assertRaises(dw.DecisionWindowsError):
            self.model([{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p3", "p4"], "StarterIDs": ["p1", "p2", "p3", "p4"]}])

    def test_teams_and_players_are_ordered_as_strings(self):
        rosters = [{"FantasyTeamID": n, "PlayerIDs": [], "StarterIDs": []} for n in (2, 10, 1)]
        model = self.model(rosters)
        self.assertEqual(["1", "10", "2"], [t["FantasyTeamID"] for t in model["FantasyRelevance"]["Teams"]])

    def test_scoring_path_state(self):
        ready = {"State": "ready"}
        self.assertEqual("open", dw.remaining_scoring_path_state({"HasRemainingScoringPath": True, "Slots": []}, None))
        self.assertEqual("open", dw.remaining_scoring_path_state({"HasRemainingScoringPath": False, "Slots": [{"Repairability": {"State": "repairable"}}]}, None))
        self.assertEqual("unknown", dw.remaining_scoring_path_state({"HasRemainingScoringPath": False, "Slots": []}, None))
        self.assertEqual("unknown", dw.remaining_scoring_path_state({"HasRemainingScoringPath": False, "Slots": []}, {"State": "review"}))
        self.assertEqual("unknown", dw.remaining_scoring_path_state({"HasRemainingScoringPath": False, "Slots": [{"Repairability": {"State": "unknown"}}]}, ready))
        self.assertEqual("none", dw.remaining_scoring_path_state({"HasRemainingScoringPath": False, "Slots": [{"State": "completed"}]}, ready))

    def test_versions_and_scoring_path_on_a_model(self):
        model = self.model([{"FantasyTeamID": 1, "PlayerIDs": ["p1"], "StarterIDs": ["p1"]}], at="2030-09-08T16:00:00Z", status={})
        self.assertEqual(3, model["FantasyRelevance"]["Version"])
        self.assertEqual(2, model["SchemaVersion"])
        self.assertEqual("open", self.team(model)["RemainingScoringPathState"])


class AvailabilityTests(unittest.TestCase):
    ROSTERS = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p3"], "StarterIDs": ["p1", "p2", "p3"]}]
    IDENTITIES = [{"IDs": {"Sleeper": "p1", "ESPN": "e1"}}, {"IDs": {"Sleeper": "p2", "ESPN": "e2"}}, {"IDs": {"Sleeper": "p3", "ESPN": "e3"}}]
    SNAPSHOT = {"Season": 2030, "Players": [
        {"ESPNPlayerID": "e1", "ProviderStatus": "out", "StatusSinceUtc": "2030-09-01T10:00:00+02:00"},
        {"ESPNPlayerID": "e2", "ProviderStatus": "QUESTIONABLE", "StatusSinceUtc": "2030-09-02T10:00:00Z"},
        {"ESPNPlayerID": "e3", "ProviderStatus": "SUSPENDED", "StatusSinceUtc": None},
    ]}

    def observe(self, identities=None, snapshot="default", rosters=None):
        return dw.scoring_availability_observations(
            2030, self.ROSTERS if rosters is None else rosters, {"p1", "p2", "p3"},
            self.IDENTITIES if identities is None else identities, self.SNAPSHOT if snapshot == "default" else snapshot)

    def test_status_maps_to_state_and_since_is_the_first_observation(self):
        observations = {o["PlayerID"]: o for o in self.observe()}
        self.assertEqual(("out", "OUT", "2030-09-01T08:00:00Z"), (observations["p1"]["State"], observations["p1"]["ProviderStatus"], observations["p1"]["FirstObservedAtUtc"]))
        self.assertEqual(observations["p1"]["FirstObservedAtUtc"], observations["p1"]["ObservedAtUtc"])
        self.assertEqual("uncertain", observations["p2"]["State"])
        self.assertEqual(("unknown", None), (observations["p3"]["State"], observations["p3"]["FirstObservedAtUtc"]))

    def test_missing_other_season_or_unmapped_evidence_stays_unknown(self):
        self.assertEqual([], self.observe(snapshot=None))
        self.assertEqual([], self.observe(snapshot={**self.SNAPSHOT, "Season": 2029}))
        self.assertEqual({"p2", "p3"}, {o["PlayerID"] for o in self.observe(identities=self.IDENTITIES[1:])})
        self.assertEqual({"p1"}, {o["PlayerID"] for o in self.observe(rosters=[{"FantasyTeamID": 1, "PlayerIDs": ["p1"], "StarterIDs": ["p1"]}])})

    def test_ambiguous_identity_mappings_are_skipped(self):
        twice = self.IDENTITIES + [{"IDs": {"Sleeper": "p1", "ESPN": "eX"}}]
        self.assertNotIn("p1", {o["PlayerID"] for o in self.observe(identities=twice)})
        shared = self.IDENTITIES + [{"IDs": {"Sleeper": "p9", "ESPN": "e2"}}]
        self.assertNotIn("p2", {o["PlayerID"] for o in self.observe(identities=shared)})

    def test_explicit_out_removes_the_direct_path_unless_the_game_is_completed(self):
        r = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p2", "p3"], "StarterIDs": ["p1", "p2", "p3"]}]
        base = dw.build_base_model("L", SEASON, 1, 18, GAMES, r, ASSIGN, 3, key)
        dw.add_relevance(base, ["QB", "RB", "WR"], r, {}, {"w1c": "Final"}, dw.parse_instant("2030-09-08T16:00:00Z", "at"))
        out = [{"PlayerID": p, "State": "out", "ProviderStatus": "OUT", "Source": "ESPN", "FirstObservedAtUtc": None, "ObservedAtUtc": None} for p in ("p1", "p3")]
        dw.add_availability(base, out)
        team = base["FantasyRelevance"]["Teams"][0]
        players = {p["PlayerID"]: p for p in team["Players"]}
        self.assertFalse(players["p1"]["HasDirectScoringPath"])      # p1 plays AAA, OUT and not completed
        self.assertFalse(players["p3"]["HasDirectScoringPath"])      # p3 plays EEE, OUT and completed: no direct path anyway
        self.assertEqual("unknown", players["p2"]["ScoringAvailability"]["State"])
        self.assertEqual(1, team["UnlockedStarterCount"])
        self.assertTrue(team["HasRemainingScoringPath"])
        self.assertEqual(4, base["FantasyRelevance"]["Version"])
        self.assertEqual(3, base["SchemaVersion"])
        self.assertEqual(out, base["ScoringAvailabilityObservations"])


class RepairabilityTests(unittest.TestCase):
    model = dw.get_model("repairability-v1", "repairability")
    AT = dw.parse_instant("2030-09-08T16:00:00Z", "at")

    def slot(self, slot_id, slot_type):
        return {"SlotID": slot_id, "SlotType": slot_type}

    def test_acquisition_bridge_is_waiver_only_and_never_guesses(self):
        known = self.model.resolve_acquisition(True, "2030-09-07T11:00:00+00:00")
        self.assertEqual(("known", "2030-09-07T11:00:00Z", False, False), (known["State"], known["NextWaiverRun"], known["ImmediateFreeAgentAddsAllowed"], known["TradeRepairAllowed"]))
        self.assertEqual("unknown", self.model.resolve_acquisition(True, None)["State"])
        self.assertEqual("unknown", self.model.resolve_acquisition(True, "garbage")["State"])
        self.assertEqual("unknown", self.model.resolve_acquisition(None, "2030-09-07T11:00:00Z")["State"])
        self.assertEqual("unknown", self.model.resolve_acquisition(False, "2030-09-07T11:00:00Z")["State"])
        closed = self.model.resolve_acquisition(False, None)
        self.assertEqual(("known", False, None), (closed["State"], closed["ExternalAddsAllowed"], closed["NextWaiverRun"]))

    def test_assignment_uses_augmenting_paths_and_flex_reshuffle(self):
        cand = lambda i, pos: {"PlayerID": i, "Position": pos}
        slots = [self.slot("RB-1", "RB"), self.slot("FLEX-1", "FLEX")]
        # The only RB must take RB-1 although the WR would also fit FLEX-1 first by name.
        self.assertTrue(self.model.complete_assignment(slots, [cand("a", "RB"), cand("b", "WR")], dw.slot_eligible))
        self.assertFalse(self.model.complete_assignment(slots, [cand("a", "WR"), cand("b", "WR")], dw.slot_eligible))
        self.assertFalse(self.model.complete_assignment(slots, [cand("a", "RB")], dw.slot_eligible))
        self.assertTrue(self.model.complete_assignment([], [], dw.slot_eligible))
        with self.assertRaises(ValueError):
            self.model.complete_assignment(slots, [cand("a", "RB"), cand("a", "RB")], dw.slot_eligible)

    def test_state_resolution_order(self):
        slots = [self.slot("RB-1", "RB")]
        rb = [{"PlayerID": "a", "Position": "RB"}]
        r = lambda internal, external, iu, es, eu: self.model.resolve_state(slots, internal, external, iu, es, eu, dw.slot_eligible)
        self.assertEqual(("repairable", "internal-roster"), (r(rb, [], False, "unavailable", False)["State"], r(rb, [], False, "unavailable", False)["Path"]))
        self.assertEqual("external-acquisition", r([], rb, False, "available", False)["Path"])
        self.assertEqual("LINEUP_EVIDENCE_UNKNOWN", r([], [], True, "unavailable", False)["ReasonCode"])
        self.assertEqual("ACQUISITION_EVIDENCE_UNKNOWN", r([], [], False, "unknown", False)["ReasonCode"])
        self.assertEqual("EXTERNAL_PLAYER_EVIDENCE_UNKNOWN", r([], [], False, "available", True)["ReasonCode"])
        self.assertEqual("irreparable", r([], [], False, "unavailable", False)["State"])
        self.assertEqual("unknown", self.model.resolve_state([], [], [], False, "unavailable", False, dw.slot_eligible)["State"])

    def evidence(self, players, acquisition, owned=(), at=None):
        games = [
            {"Week": 1, "HomeTeamID": "BBB", "AwayTeamID": "AAA", "StartsAtUtc": "2030-09-08T17:00:00Z", "Status": "Scheduled"},
            {"Week": 1, "HomeTeamID": "DDD", "AwayTeamID": "CCC", "StartsAtUtc": "2030-09-08T15:00:00Z", "Status": "Scheduled"},
            {"Week": 2, "HomeTeamID": "EEE", "AwayTeamID": "FFF", "StartsAtUtc": "2030-09-15T17:00:00Z", "Status": "Scheduled"},
        ]
        return self.model.external_evidence(players, set(owned), games, [self.slot("RB-1", "RB")], acquisition, 1, at or self.AT, key, dw.slot_eligible)

    def test_waiver_must_run_strictly_before_kickoff_and_the_game_must_be_open(self):
        players = [{"PlayerID": "free", "Position": "RB", "TeamID": "AAA"}, {"PlayerID": "locked", "Position": "RB", "TeamID": "CCC"},
                   {"PlayerID": "owned", "Position": "RB", "TeamID": "AAA"}, {"PlayerID": "wr", "Position": "WR", "TeamID": "AAA"}]
        waiver = lambda run: self.model.resolve_acquisition(True, run)
        found = self.evidence(players, waiver("2030-09-08T11:00:00Z"), owned={"owned"})
        self.assertEqual(["free"], sorted(c["PlayerID"] for c in found["Candidates"]))
        at_kickoff = self.evidence(players, waiver("2030-09-08T17:00:00Z"), owned={"owned"})
        self.assertEqual([], [c for c in at_kickoff["Candidates"] if c["PlayerID"] == "free"])   # run == kickoff misses the lock
        self.assertEqual("unavailable", self.evidence(players, self.model.resolve_acquisition(False, None))["State"])
        self.assertEqual("unknown", self.evidence(players, self.model.resolve_acquisition(True, None))["State"])

    def test_unknown_team_or_missing_position_marks_player_evidence_unknown(self):
        acquisition = self.model.resolve_acquisition(True, "2030-09-08T11:00:00Z")
        self.assertTrue(self.evidence([{"PlayerID": "x", "Position": "RB", "TeamID": "ZZZ"}], acquisition)["PlayerEvidenceUnknown"])
        self.assertTrue(self.evidence([{"PlayerID": "x", "Position": None, "TeamID": "AAA"}], acquisition)["PlayerEvidenceUnknown"])
        self.assertFalse(self.evidence([{"PlayerID": "x", "Position": "RB", "TeamID": None}], acquisition)["PlayerEvidenceUnknown"])
        self.assertEqual([], self.evidence([{"PlayerID": "x", "Position": "RB", "TeamID": "EEE"}], acquisition)["Candidates"])  # bye in week 1

    def test_add_repairability_marks_problem_slots_only(self):
        rosters = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p3", "p5"], "StarterIDs": ["p1"], "StarterSlots": [None, "p1"]}]
        base = dw.build_base_model("L", SEASON, 1, 18, GAMES, rosters, ASSIGN, 2, key)
        dw.add_relevance(base, ["RB", "RB", "BN"], rosters, {"p1": "RB", "p3": "RB"}, {}, dw.parse_instant("2030-09-08T16:00:00Z", "at"))
        dw.add_availability(base, [])
        acquisition = self.model.resolve_acquisition(False, None)
        dw.add_repairability(base, self.model, rosters, [], [], acquisition, key, self.AT)
        slots = base["FantasyRelevance"]["Teams"][0]["Slots"]
        self.assertEqual("OPEN_STARTER_SLOT", slots[0]["Repairability"]["ProblemCode"])
        self.assertIsNone(slots[1]["Repairability"])
        # p3 (CCC, unlocked) is an internal bench candidate for the open RB slot, but p1 (AAA) also sits in a mutable slot.
        self.assertEqual("repairable", slots[0]["Repairability"]["State"])

    def test_locked_unavailable_starter_is_irreparable_and_other_open_slots_stay_separate(self):
        rosters = [{"FantasyTeamID": 1, "PlayerIDs": ["p1", "p3"], "StarterIDs": ["p3"], "StarterSlots": [None, "p3"]}]
        base = dw.build_base_model("L", SEASON, 1, 18, GAMES, rosters, ASSIGN, 2, key)
        dw.add_relevance(base, ["RB", "RB"], rosters, {"p1": "RB", "p3": "RB"}, {}, dw.parse_instant("2030-09-08T17:30:00Z", "at"))
        out = [{"PlayerID": "p3", "State": "out", "ProviderStatus": "OUT", "Source": "ESPN", "FirstObservedAtUtc": None, "ObservedAtUtc": None}]
        dw.add_availability(base, out)
        dw.add_repairability(base, self.model, rosters, [], [], self.model.resolve_acquisition(False, None), key, dw.parse_instant("2030-09-08T17:30:00Z", "at"))
        slots = base["FantasyRelevance"]["Teams"][0]["Slots"]
        self.assertEqual(("STARTER_UNAVAILABLE", "irreparable", "NO_LEGAL_REPAIR_PATH"),
                         (slots[1]["Repairability"]["ProblemCode"], slots[1]["Repairability"]["State"], slots[1]["Repairability"]["ReasonCode"]))
        self.assertEqual("OPEN_STARTER_SLOT", slots[0]["Repairability"]["ProblemCode"])


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
