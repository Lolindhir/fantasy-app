from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from team_week_performance_sources import (  # noqa: E402
    WeekSourceNotReady,
    load_verified_week_inputs,
    resolve_slots_from_league,
    resolve_week_positions,
    validate_final_week,
)


class SourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        league_dir = self.root / "data-source/leagues/nfl-reise/seasons/2024"
        league_dir.mkdir(parents=True)
        (league_dir / "league.json").write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Season": 2024,
            "RosterPositions": ["WR", "FLEX", "REC_FLEX", "BN"],
            "Settings": {"num_teams": 1},
            "ScoringSettings": {"rec": 1},
            "WeekStructure": {"Season": 2024, "StartWeek": 1,
                              "ExpectedLastLeagueWeek": 17, "LastScoredLeg": 4},
        }), encoding="utf-8")
        (league_dir / "matchups").mkdir()
        self.roster = [{"CanonicalLeagueRosterID": "rosterA", "Week": 4,
                        "Players": [{"CanonicalPlayerID": "a"}, {"CanonicalPlayerID": "b"}],
                        "Starters": [{"CanonicalPlayerID": "a"}],
                        "Points": 1,
                        "PlayerPoints": [], "StarterPoints": []}]
        (league_dir / "matchups/week-4.json").write_text(json.dumps(self.roster), encoding="utf-8")
        nfl = self.root / "data-source/nfl/weekly-rosters/2024"
        nfl.mkdir(parents=True)
        (nfl / "04.json").write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"},
                        {"CanonicalPlayerID": "b", "Position": "RB"}]}), encoding="utf-8")
        self.league = json.loads((league_dir / "league.json").read_text())
        self.calls = []

    def final(self, *args, **kwargs):
        self.calls.append(kwargs)
        return True, {"gameA"}

    def test_2024_matchup_and_positions_and_slots_and_finality(self):
        params = load_verified_week_inputs(
            self.root, "nfl-reise", 2024, 4, nfl_finality=self.final
        )
        self.assertEqual(params["position_by_player"], {"a": "WR", "b": "RB"})
        self.assertEqual([s.slot_id for s in params["slots"]], ["WR-1", "FLEX-1", "REC_FLEX-1"])
        self.assertTrue(params["finalized"])
        self.assertEqual(params["finality_evidence"],
                         "data-source/nfl/game-finality/2024.json:REG-W4;league:scored-week-confirmed")
        self.assertEqual(self.calls, [{"season": 2024, "week": 4}])
        self.assertEqual(params["matchup_rows"], self.roster)

    def test_finality_evidence_is_stable_when_later_weeks_are_scored(self):
        before = validate_final_week(self.root, self.league, 2024, 4, nfl_finality=self.final)
        self.league["WeekStructure"]["LastScoredLeg"] = 5
        after = validate_final_week(self.root, self.league, 2024, 4, nfl_finality=self.final)
        self.assertEqual(before, after)
        self.assertNotIn("LastScoredLeg=", after)

    def test_league_scoring_gate_blocks_unfinalized_week(self):
        self.league["WeekStructure"]["LastScoredLeg"] = 3
        with self.assertRaisesRegex(WeekSourceNotReady, "not final"):
            validate_final_week(self.root, self.league, 2024, 4, nfl_finality=self.final)
        self.assertEqual(self.calls, [])

    def test_nfl_finality_gate_blocks_when_no_games_final(self):
        with self.assertRaisesRegex(WeekSourceNotReady, "NFL regular season"):
            validate_final_week(self.root, self.league, 2024, 4,
                                nfl_finality=lambda *a, **kw: (False, set()))

    def test_current_roster_cannot_substitute_missing_week_position(self):
        roster_file = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        roster_file.write_text(json.dumps({"Season": 2024, "Week": 4,
                                           "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        with self.assertRaisesRegex(WeekSourceNotReady, "Missing historical week .*fantasy positions"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_prior_week_positions_can_cover_injured_or_taxi_players(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024"
        (weekly / "04.json").write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        (weekly / "03.json").write_text(json.dumps({"Season": 2024, "Week": 3,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        self.assertEqual(resolve_week_positions(self.root, 2024, 4, self.roster), {"a": "WR", "b": "RB"})

    def test_finalized_same_season_roster_fills_remaining_positions(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        season = self.root / "data-source/nfl/rosters/2024.json"
        season.parent.mkdir(parents=True)
        season.write_text(json.dumps({"Season": 2024, "Finalized": True,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        self.assertEqual(resolve_week_positions(self.root, 2024, 4, self.roster), {"a": "WR", "b": "RB"})

    def test_unfinalized_season_roster_cannot_backfill_historical_position(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        season = self.root / "data-source/nfl/rosters/2024.json"
        season.parent.mkdir(parents=True)
        season.write_text(json.dumps({"Season": 2024, "Finalized": False,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        with self.assertRaisesRegex(WeekSourceNotReady, "Missing historical week"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_conflicting_prior_week_position_evidence_is_rejected(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024"
        (weekly / "04.json").write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        for week, pos in [(2, "RB"), (3, "WR")]:
            (weekly / f"{week:02d}.json").write_text(json.dumps({"Season": 2024, "Week": week,
                "Records": [{"CanonicalPlayerID": "b", "Position": pos}]}))
        with self.assertRaisesRegex(WeekSourceNotReady, "Conflicting prior-week"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_canonical_weekly_roster_is_authoritative_without_transactions(self):
        # No transaction directory/snapshots exist in the fixture by design.
        params = load_verified_week_inputs(
            self.root, "nfl-reise", 2024, 4, nfl_finality=self.final
        )
        self.assertEqual(params["matchup_rows"][0]["Players"], self.roster[0]["Players"])
        self.assertFalse((self.root / "data-source/leagues/nfl-reise/seasons/2024/transactions").exists())

    def test_prior_finalized_season_resolves_inactive_player_position(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        historical = self.root / "data-source/nfl/rosters/2023.json"
        historical.parent.mkdir(parents=True)
        historical.write_text(json.dumps({"Season": 2023, "Finalized": True,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        self.assertEqual(resolve_week_positions(self.root, 2024, 4, self.roster),
                         {"a": "WR", "b": "RB"})

    def test_same_season_finalized_position_takes_precedence_over_older_seasons(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        historical = self.root / "data-source/nfl/rosters"
        historical.mkdir(parents=True)
        (historical / "2024.json").write_text(json.dumps({
            "Season": 2024, "Finalized": True,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        (historical / "2023.json").write_text(json.dumps({
            "Season": 2023, "Finalized": True,
            "Records": [{"CanonicalPlayerID": "b", "Position": "WR"}]}))
        self.assertEqual(resolve_week_positions(self.root, 2024, 4, self.roster),
                         {"a": "WR", "b": "RB"})

    def test_prior_season_fallback_rejects_unfinalized_or_future_data(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        historical = self.root / "data-source/nfl/rosters/2023.json"
        historical.parent.mkdir(parents=True)
        historical.write_text(json.dumps({"Season": 2023, "Finalized": False,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        future = historical.parent / "2025.json"
        future.write_text(json.dumps({"Season": 2025, "Finalized": True,
            "Records": [{"CanonicalPlayerID": "b", "Position": "RB"}]}))
        with self.assertRaisesRegex(WeekSourceNotReady, "Missing historical week"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_conflicting_finalized_prior_seasons_fail_closed(self):
        weekly = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        weekly.write_text(json.dumps({"Season": 2024, "Week": 4,
            "Records": [{"CanonicalPlayerID": "a", "Position": "WR"}]}))
        historical = self.root / "data-source/nfl/rosters"
        historical.mkdir(parents=True)
        for year, position in [(2022, "WR"), (2023, "RB")]:
            (historical / f"{year}.json").write_text(json.dumps({
                "Season": year, "Finalized": True,
                "Records": [{"CanonicalPlayerID": "b", "Position": position}]}))
        with self.assertRaisesRegex(WeekSourceNotReady, "Conflicting finalized prior-season"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_incomplete_weekly_team_population_fails_closed(self):
        league_file = self.root / "data-source/leagues/nfl-reise/seasons/2024/league.json"
        league = json.loads(league_file.read_text())
        league["Settings"]["num_teams"] = 2
        league_file.write_text(json.dumps(league))
        with self.assertRaisesRegex(WeekSourceNotReady, "Incomplete weekly fantasy team population"):
            load_verified_week_inputs(
                self.root, "nfl-reise", 2024, 4, nfl_finality=self.final
            )

    def test_week_identity_mismatch_is_rejected(self):
        roster_file = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        roster_file.write_text(json.dumps({"Season": 2024, "Week": 5, "Records": []}))
        with self.assertRaisesRegex(WeekSourceNotReady, "season/week mismatch"):
            resolve_week_positions(self.root, 2024, 4, self.roster)

    def test_2024_special_flex_matches_legacy_slot_contract(self):
        slots = resolve_slots_from_league(
            ["QB", "WR", "RB", "FLEX", "WRRB_FLEX", "REC_FLEX", "SUPER_FLEX", "K", "BN"],
            {"p": "WR", "q": "RB", "r": "QB", "s": "TE", "k": "K"},
        )
        self.assertEqual([s.slot_id for s in slots],
                         ["QB-1", "WR-1", "RB-1", "FLEX-1", "WRRB_FLEX-1", "REC_FLEX-1", "SUPER_FLEX-1", "K-1"])
        by_id = {s.slot_id: s.eligible_positions for s in slots}
        self.assertEqual(by_id["FLEX-1"], frozenset({"RB", "WR", "TE"}))
        self.assertEqual(by_id["WRRB_FLEX-1"], frozenset({"RB", "WR"}))
        self.assertEqual(by_id["REC_FLEX-1"], frozenset({"WR", "TE"}))
        self.assertEqual(by_id["SUPER_FLEX-1"], frozenset({"QB", "RB", "WR", "TE"}))
        self.assertEqual(by_id["K-1"], frozenset({"K"}))

    def test_2025_and_2026_flex_slots_preserve_ordinals_and_full_eligibility(self):
        for year in (2025, 2026):
            with self.subTest(year=year):
                slots = resolve_slots_from_league(["QB", "FLEX", "FLEX", "BN", "FLEX"], {"only": "QB"})
                self.assertEqual([s.slot_id for s in slots], ["QB-1", "FLEX-1", "FLEX-2", "FLEX-3"])
                self.assertEqual([s.eligible_positions for s in slots[1:]],
                                 [frozenset({"RB", "WR", "TE"})] * 3)

    def test_unfillable_or_bench_only_lineup_fails_closed(self):
        with self.assertRaisesRegex(WeekSourceNotReady, "no eligible position"):
            resolve_slots_from_league(["DL"], {"p": "WR"})
        with self.assertRaisesRegex(WeekSourceNotReady, "Cannot resolve canonical starting slots"):
            resolve_slots_from_league(["BN"], {"p": "WR"})
        with self.assertRaisesRegex(WeekSourceNotReady, "Cannot resolve canonical starting slots"):
            resolve_slots_from_league(None, {"p": "WR"})

    def test_conflicting_historical_positions_fail_closed(self):
        roster_file = self.root / "data-source/nfl/weekly-rosters/2024/04.json"
        data = json.loads(roster_file.read_text())
        data["Records"].append({"CanonicalPlayerID": "a", "Position": "QB"})
        roster_file.write_text(json.dumps(data))
        with self.assertRaisesRegex(WeekSourceNotReady, "Conflicting historical positions"):
            resolve_week_positions(self.root, 2024, 4, self.roster)


if __name__ == "__main__":
    unittest.main()
