"""Weekly Recaps (ADR-063, Issue #1199 section 4, step 2). Ported from WeeklyRecapRegressionTest.ps1; the inputs are synthetic and
no real league, player or schedule data is hard-wired."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import weekly_recaps as wr  # noqa: E402

ALIASES = {"WSH": "WAS", "LAR": "LA"}


def team_key(value):
    text = None if value is None else str(value).strip()
    return ALIASES.get(text, text)


def player(player_id, canonical, points, starter=True):
    return {"PlayerID": player_id, "CanonicalPlayerID": canonical, "IsStarter": starter, "HasPoints": True, "Points": points}


def fixture():
    matchup_ids = {"fgm-a", "fgm-b", "fgm-c"}
    team_values = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6}
    facts = [
        {"FantasyMatchupID": "fgm-a", "Teams": [
            {"FantasyTeamID": "1", "Players": [player("p1", "c1", 20), player("bench", "cb", 99, False)]},
            {"FantasyTeamID": "2", "Players": [player("p2", "c2", 20)]}]},
        {"FantasyMatchupID": "fgm-b", "Teams": [
            {"FantasyTeamID": "3", "Players": [player("p3", "c3", 18), player("p4", "c4", 12)]},
            {"FantasyTeamID": "4", "Players": [player("p5", "c5", 10)]}]},
        {"FantasyMatchupID": "fgm-c", "Teams": [
            {"FantasyTeamID": "5", "Players": [player("p6", "c6", 20)]},
            {"FantasyTeamID": "6", "Players": [player("p7", "c7", 5)]}]},
    ]
    schedule = [
        {"gameID": "game-a", "gameWeek": "Week 4", "gameTime_epoch": "1000", "away": "AAA", "home": "BBB", "teamIDAway": "11", "teamIDHome": "12"},
        {"gameID": "game-b", "gameWeek": "Week 4", "gameTime_epoch": "1100", "away": "WSH", "home": "DDD", "teamIDAway": "13", "teamIDHome": "14"},
        {"gameID": "game-c", "gameWeek": "Week 4", "gameTime_epoch": "1200", "away": "FFF", "home": "LAR", "teamIDAway": "15", "teamIDHome": "16"},
    ]
    canonical = [
        {"Week": 4, "AwayTeam": "AAA", "HomeTeam": "BBB", "AwayScore": 21, "HomeScore": 17},
        {"Week": 4, "AwayTeam": "WAS", "HomeTeam": "DDD", "AwayScore": 24, "HomeScore": 20},
        {"Week": 4, "AwayTeam": "FFF", "HomeTeam": "LA", "AwayScore": 10, "HomeScore": 7},
    ]
    rows = [
        {"CanonicalPlayerID": "c1", "SourceIDs": {"Sleeper": "p1"}, "Team": "AAA", "Position": "QB"},
        {"CanonicalPlayerID": "cb", "SourceIDs": {"Sleeper": "bench"}, "Team": "AAA", "Position": "WR"},
        {"CanonicalPlayerID": "c2", "SourceIDs": {"Sleeper": "p2"}, "Team": "BBB", "Position": "WR"},
        {"CanonicalPlayerID": "c3", "SourceIDs": {"Sleeper": "p3"}, "Team": "AAA", "Position": "RB"},
        {"CanonicalPlayerID": "c4", "SourceIDs": {"Sleeper": "p4"}, "Team": "WAS", "Position": "WR"},
        {"CanonicalPlayerID": "c5", "SourceIDs": {"Sleeper": "p5"}, "Team": "DDD", "Position": "TE"},
        {"CanonicalPlayerID": "c6", "SourceIDs": {"Sleeper": "p6"}, "Team": "LA", "Position": "WR"},
        {"CanonicalPlayerID": "c7", "SourceIDs": {"Sleeper": "p7"}, "Team": "FFF", "Position": "RB"},
    ]
    order = {"1": 1, "2": 4, "3": 3, "4": 5, "5": 2, "6": 6}
    return matchup_ids, team_values, facts, schedule, canonical, wr.roster_identity_map(rows), order


def build(facts=None, schedule=None, canonical=None):
    matchup_ids, team_values, base_facts, base_schedule, base_canonical, identity, order = fixture()
    return wr.build_week_recap(
        4, matchup_ids, team_values, base_facts if facts is None else facts, base_schedule if schedule is None else schedule,
        base_canonical if canonical is None else canonical, identity, order, team_key,
    )


class WeekRecapTests(unittest.TestCase):
    def test_selection_and_identity(self):
        recap = build()
        self.assertEqual(2, len(recap["KeyGames"]))
        self.assertEqual(3, len(recap["KeyPlayers"]))
        self.assertEqual("game-a", recap["KeyGames"][0]["GameID"], "starter points rank first; bench points do not count")
        self.assertEqual(58, recap["KeyGames"][0]["StarterPoints"])
        self.assertNotIn("bench", [p["PlayerID"] for p in recap["KeyPlayers"]])
        self.assertEqual(["p1", "p6", "p2"], [p["PlayerID"] for p in recap["KeyPlayers"]], "equal points use neutral team order")
        self.assertEqual(1, recap["KeyPlayers"][0]["FantasyTeamID"])
        self.assertEqual("11", recap["KeyPlayers"][0]["NFLTeamID"])
        self.assertEqual("16", recap["KeyPlayers"][1]["NFLTeamID"], "canonical LA maps to the provider-spelled LAR schedule team")
        self.assertEqual("QB", recap["KeyPlayers"][0]["Position"])
        self.assertEqual(21, recap["KeyGames"][0]["AwayScore"])
        self.assertIn("fgm-a", recap["KeyGames"][0]["FantasyMatchupIDs"])
        self.assertIn("fgm-b", recap["KeyGames"][0]["FantasyMatchupIDs"])
        self.assertEqual(sorted(recap), sorted(["Week", "KeyGames", "KeyPlayers"]))

    def test_deterministic(self):
        self.assertEqual(json.dumps(build()), json.dumps(build()))

    def test_stat_correction_changes_ranking(self):
        facts = fixture()[2]
        facts[2]["Teams"][0]["Players"][0]["Points"] = 70
        recap = build(facts)
        self.assertEqual("p6", recap["KeyPlayers"][0]["PlayerID"])
        self.assertEqual("game-c", recap["KeyGames"][0]["GameID"])

    def test_key_game_density_tiebreaks(self):
        facts = fixture()[2]
        facts[0]["Teams"][0]["Players"][0]["Points"] = 10
        facts[0]["Teams"][1]["Players"][0]["Points"] = 10
        facts[1]["Teams"][0]["Players"][0]["Points"] = 0
        facts[1]["Teams"][0]["Players"][1]["Points"] = 10
        facts[1]["Teams"][1]["Players"][0]["Points"] = 10
        facts[2]["Teams"][0]["Players"][0]["Points"] = 10
        facts[2]["Teams"][1]["Players"][0]["Points"] = 0
        self.assertEqual("game-a", build(facts)["KeyGames"][0]["GameID"])

    def test_defense_identity_without_roster_row(self):
        facts = fixture()[2]
        facts[2]["Teams"][1]["Players"][0] = player("fff", None, 30)
        recap = build(facts)
        top = recap["KeyPlayers"][0]
        self.assertEqual(("fff", "DEF"), (top["PlayerID"], top["Position"]))

    def test_evidence_gaps_are_marked(self):
        facts = fixture()[2]
        facts[0]["Teams"][0]["Players"][0] = player("unknown-player", None, 5)
        with self.assertRaises(wr.EvidenceGap):
            build(facts)
        facts = fixture()[2]
        facts[0]["Teams"][0]["Players"][0]["HasPoints"] = False
        with self.assertRaises(wr.EvidenceGap):
            build(facts)
        canonical = fixture()[4]
        canonical[0]["AwayScore"] = None
        with self.assertRaises(wr.EvidenceGap):
            build(canonical=canonical)

    def test_fewer_than_required_fails_closed(self):
        facts = fixture()[2][:1]
        with self.assertRaises(wr.WeeklyRecapsError):
            build(facts)

    def test_contradicting_matchup_is_not_an_evidence_gap(self):
        facts = fixture()[2]
        facts[0]["FantasyMatchupID"] = "fgm-unknown"
        with self.assertRaises(wr.WeeklyRecapsError) as caught:
            build(facts)
        self.assertNotIsInstance(caught.exception, wr.EvidenceGap)


class TeamAwardsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.rows = [
            {"Week": 4, "CanonicalLeagueRosterID": f"roster-{i}", "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": str(i)}]}
            for i in range(1, 7)
        ]
        self.participants = {str(i) for i in range(1, 7)}
        self.derived = {
            "ContractVersion": 1, "CanonicalLeagueID": "test-league", "Season": 2026, "Week": 4,
            "FinalityEvidence": "data-source/nfl/game-finality/2026.json:REG-W4;league:scored-week-confirmed",
            "LineupDefinitionHash": "sha256:lineup", "ScoringProfile": {"SettingsHash": "sha256:scoring"},
            "Teams": [
                {"CanonicalLeagueRosterID": f"roster-{i}", "PotentialPoints": 100 + i, "ActualStarterPoints": 80 + i, "MissedPoints": 20, "EfficiencyPercent": 80}
                for i in range(1, 7)
            ],
            "Awards": {"BestManagerRosterIDs": ["roster-2"], "BestCoachRosterIDs": ["roster-4", "roster-6"]},
        }

    def write(self, derived=None):
        path = self.root / "data-derived" / "team-week-performance" / "test-league" / "2026" / "04.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.derived if derived is None else derived), encoding="utf-8")

    def awards(self, rows=None):
        return wr.team_awards(self.root, "test-league", 2026, 4, self.rows if rows is None else rows, self.participants)

    def test_missing_partition_is_unavailable(self):
        result = self.awards()
        self.assertEqual({"State": "unavailable", "BestManager": [], "BestCoach": []}, result)

    def test_available_projection_without_recalculation(self):
        self.write()
        result = self.awards()
        self.assertEqual("available", result["State"])
        self.assertEqual([{"CanonicalLeagueRosterID": "roster-2", "FantasyTeamID": 2, "PotentialPoints": 102}], result["BestManager"])
        self.assertEqual([4, 6], [w["FantasyTeamID"] for w in result["BestCoach"]], "tied coaches are all kept, sorted")
        self.assertNotIn("Owner", result["BestManager"][0])
        self.assertEqual(json.dumps(result), json.dumps(self.awards()))

    def test_empty_winners_are_legitimate(self):
        self.derived["Awards"] = {"BestManagerRosterIDs": [], "BestCoachRosterIDs": []}
        self.write()
        result = self.awards()
        self.assertEqual(("available", [], []), (result["State"], result["BestManager"], result["BestCoach"]))

    def test_contradicting_partitions_fail_closed(self):
        mutations = {
            "week": lambda d: d.update(Week=3),
            "finality": lambda d: d.update(FinalityEvidence="x"),
            "unknown winner": lambda d: d["Awards"].update(BestManagerRosterIDs=["unknown-roster"]),
            "duplicate winner": lambda d: d["Awards"].update(BestCoachRosterIDs=["roster-4", "roster-4"]),
            "missing winners": lambda d: d.update(Awards={}),
            "missing team": lambda d: d["Teams"].pop(),
        }
        for name, mutate in mutations.items():
            derived = copy.deepcopy(self.derived)
            mutate(derived)
            self.write(derived)
            with self.subTest(name), self.assertRaises(wr.WeeklyRecapsError):
                self.awards()

    def test_roster_join_failure_fails_closed(self):
        self.write()
        rows = copy.deepcopy(self.rows)
        rows[0]["ProviderMappings"][0]["ProviderRosterID"] = "99"
        with self.assertRaises(wr.WeeklyRecapsError):
            self.awards(rows)


if __name__ == "__main__":
    unittest.main()
