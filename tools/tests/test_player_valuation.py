"""PlayerValuation snapshot builder, canonical-source adapter and materializer (Issue #919, step 3).

The unit tests use hand-computed values and synthetic players. The integration tests read the
repository's canonical facts but only assert invariants, never specific players or point values.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import derived_data  # noqa: E402
import league_metadata  # noqa: E402
import player_valuation_sources as sources  # noqa: E402
from data_roots import DATA_SOURCE_ROOT, data_meta_dir  # noqa: E402
from derived_data_lib import player_valuation as pv  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.registry import UnknownModelError, get_model  # noqa: E402
from derived_data_lib.ranking import RankingInput, compute_rankings  # noqa: E402
from player_week_fantasy import scoring_settings_fingerprint  # noqa: E402

MODEL_IDS = {"Salary": "salary-v1", "SalaryCap": "salary-cap-v1", "Grading": "grading-v1"}
PROFILE = {"CanonicalLeagueID": "test-league", "Season": 2030, "SettingsHash": "sha256:test", "FingerprintVersion": 1, "ActiveSettingsCount": 1}


def week(points: float, snaps: float = 50, kick_attempts: float = 0) -> dict:
    return {"Points": points, "Snaps": snaps, "KickAttempts": kick_attempts}


def context(as_of: int = 5, season: int = 2030, team_count: int = 1, bye_weeks: dict | None = None,
            model_ids: dict | None = None) -> pv.SnapshotContext:
    return pv.SnapshotContext(
        league_id="test-league", season=season, as_of_final_scored_week=as_of, scoring_profile=PROFILE,
        model_ids=model_ids or MODEL_IDS, team_count=team_count, last_league_week=17,
        bye_weeks=bye_weeks if bye_weeks is not None else {"AAA": 3, "BBB": 9},
    )


def basis(sleeper_id: str | None, cid: str | None, position: str = "WR", team: str | None = "AAA",
          status: str = pv.STATUS_RESOLVED, weeks: dict | None = None) -> pv.PlayerBasis:
    return pv.PlayerBasis(sleeper_id=sleeper_id, canonical_id=cid, position=position, team=team,
                          population=("nfl_roster_current_season",), identity_status=status, weeks=weeks or {})


def no_hold(_key: str):
    return None, None


class SeasonValuesTests(unittest.TestCase):
    """SeasonValues and FormGames (ContractVersion 3, Issue #1236), synthetic players only."""

    def test_history_values_use_the_rounded_total_and_last_league_week(self) -> None:
        rows = {1: week(10.004), 2: week(20.0), 3: week(0.0, snaps=0), 20: week(99.0)}
        values = pv.history_values(rows, "WR", 17)
        self.assertEqual({"Total": 30.0, "AvgGame": 15.0, "AvgPotentialGame": 1.88, "GamesPlayed": 2,
                          "PotentialGames": 16}, values)

    def test_historical_fantasy_relevant_games_preserve_positive_and_negative_st_scoring(self) -> None:
        rows = {1: week(10.0), 2: week(0.0, snaps=0), 3: week(2.0, snaps=0),
                4: week(-2.0, snaps=0), 5: week(0.0, snaps=10), 18: week(50.0)}
        values = pv.history_values(rows, "WR", 17)
        self.assertEqual(4, values["GamesPlayed"])
        self.assertEqual(10.0, values["Total"])
        self.assertEqual(2.5, values["AvgGame"])
        self.assertEqual(0.62, values["AvgPotentialGame"])
        self.assertEqual({"AvgPotentialGame": 0.62, "AvgGame": 2.5},
                         pv.history_inputs(rows, "WR", 17))

    def test_history_inputs_stay_a_projection_of_history_values(self) -> None:
        rows = {1: week(10.0), 2: week(20.0)}
        values = pv.history_values(rows, "WR", 17)
        self.assertEqual({"AvgPotentialGame": values["AvgPotentialGame"], "AvgGame": values["AvgGame"]},
                         pv.history_inputs(rows, "WR", 17))

    def test_games_potential_drops_a_passed_bye_and_is_zero_without_games(self) -> None:
        self.assertEqual(4, pv.games_potential(5, 3, True))
        self.assertEqual(5, pv.games_potential(5, 9, True))
        self.assertEqual(0, pv.games_potential(5, 3, False))

    def test_current_values_sum_counting_stats_and_ignore_later_weeks(self) -> None:
        rows = {
            1: {"Points": 10.0, "Snaps": 40, "KickAttempts": 0, "Attempts": 20, "TdPass": 1, "TdRec": 0, "TdRush": 0},
            2: {"Points": 5.5, "Snaps": 60, "KickAttempts": 0, "Attempts": 10, "TdPass": 0, "TdRec": 1, "TdRush": 2},
            3: {"Points": 99.0, "Snaps": 60, "KickAttempts": 0, "Attempts": 10, "TdPass": 5, "TdRec": 5, "TdRush": 5},
        }
        values = pv.current_values(rows, "QB", 2, 9, True)
        self.assertEqual(2, values["GamesPlayed"])
        self.assertEqual(2, values["GamesPotential"])
        self.assertEqual(100, values["SnapsTotal"])
        self.assertEqual(30, values["AttemptsTotal"])
        self.assertEqual(15.5, values["FantasyPointsTotal"])
        self.assertEqual(7.75, values["FantasyPointsAvgGame"])
        self.assertEqual(0.155, values["FantasyPointsAvgSnap"])
        self.assertEqual((1, 1, 2, 4), (values["TouchdownsPassing"], values["TouchdownsReceiving"],
                                         values["TouchdownsRushing"], values["TouchdownsTotal"]))

    def test_fantasy_relevant_games_keep_dylan_sampson_style_scoreless_st_out(self) -> None:
        rows = {1: week(10.0), 2: week(0.0, snaps=0), 3: week(2.0, snaps=0),
                4: week(-2.0, snaps=0), 5: week(0.0, snaps=10), 6: week(100.0, snaps=0)}
        self.assertEqual([10.0, 2.0, -2.0, 0.0], pv.played_points(rows, "RB", 5))
        self.assertEqual({"AvgPotentialGame": 2.0, "AvgGame": 2.5},
                         pv.current_inputs(rows, "RB", 5, 9))
        values = pv.current_values(rows, "RB", 5, 9, True)
        self.assertEqual(4, values["GamesPlayed"])
        self.assertEqual(10.0, values["FantasyPointsTotal"])
        self.assertEqual(2.5, values["FantasyPointsAvgGame"])
        self.assertEqual(60, values["SnapsTotal"])
        sampson = {1: week(10.7), 2: week(0.0, snaps=0)}
        self.assertEqual([10.7], pv.played_points(sampson, "RB", 2))
        self.assertEqual({"AvgPotentialGame": 5.35, "AvgGame": 10.7},
                         pv.current_inputs(sampson, "RB", 2, 9))

    def test_current_values_of_a_player_without_games_are_zero(self) -> None:
        values = pv.current_values({}, "WR", 5, 3, False)
        self.assertEqual(0, values["GamesPlayed"])
        self.assertEqual(0, values["GamesPotential"])
        self.assertEqual(0, values["FantasyPointsAvgGame"])

    def test_form_games_take_the_newest_four_final_games_up_to_the_as_of_week(self) -> None:
        games = tuple(pv.GameRef(f"g{w}", w, final) for w, final in
                      [(9, True), (8, False), (7, True), (6, True), (5, True), (4, True), (3, True)])
        self.assertEqual(["g7", "g6", "g5", "g4"], pv.form_games(games, 8, 17))
        self.assertEqual(["g5", "g4", "g3"], pv.form_games(games, 5, 17))
        self.assertEqual(["g4", "g3"], pv.form_games(games, 9, 4))

    def test_snapshot_rows_carry_season_values_and_hold_rows_take_held_values(self) -> None:
        resolved = pv.PlayerBasis(sleeper_id="1", canonical_id="c1", position="WR", team="AAA",
                                  population=("nfl_roster_current_season",), identity_status=pv.STATUS_RESOLVED,
                                  weeks={2030: {1: week(10.0)}}, games=(pv.GameRef("g1", 1, True),))
        held = basis("2", None, status="identity_unresolved")
        held_inputs = {"Current": {"AvgPotentialGame": 1.0, "AvgGame": 1.0}}
        for name in pv.HISTORY_KEYS:
            held_inputs[name] = {"AvgPotentialGame": 1.0, "AvgGame": 1.0}
        held_values = {"Current": {"GamesPlayed": 3}}
        snapshot = pv.build_snapshot(
            context(as_of=1), [resolved, held], lambda key: (held_inputs, 0) if key == "2" else (None, None),
            lambda key: (held_values, 0) if key == "2" else (None, None))
        rows = {r["PlayerID"]: r for r in snapshot["Players"]}
        self.assertEqual(["g1"], rows["1"]["FormGames"])
        self.assertEqual(1, rows["1"]["SeasonValues"]["Current"]["GamesPlayed"])
        self.assertEqual(held_values, rows["2"]["SeasonValues"])
        self.assertEqual([], rows["2"]["FormGames"])


class AggregationTests(unittest.TestCase):
    def test_scaled_round_rounds_half_to_even_after_scaling(self) -> None:
        self.assertEqual(0.12, pv.scaled_round(0.125, 2))   # 12.5 -> 12
        self.assertEqual(0.14, pv.scaled_round(0.135, 2))   # 13.5 -> 14
        self.assertEqual(1.0, pv.scaled_round(1.005, 2))    # 1.005 * 100 = 100.49999999999999

    def test_scaled_round_keeps_the_sign_of_a_negative_zero_like_net(self) -> None:
        import math
        self.assertEqual(-1.0, math.copysign(1.0, pv.scaled_round(-0.004, 2)))
        self.assertEqual(1.0, math.copysign(1.0, pv.scaled_round(0.004, 2)))
        self.assertEqual(-0.01, pv.scaled_round(-0.011, 2))

    def test_played_points_filters_position_rule_week_and_orders_by_week(self) -> None:
        rows = {3: week(7.0), 1: week(10.0), 2: week(0.0, snaps=0), 6: week(50.0)}
        self.assertEqual([10.0, 7.0], pv.played_points(rows, "WR", 5))
        kicker = {1: week(4.0, snaps=0, kick_attempts=2), 2: week(9.0, snaps=60, kick_attempts=0)}
        self.assertEqual([4.0], pv.played_points(kicker, "K", 5))

    def test_current_inputs_potential_games_exclude_a_passed_bye_week(self) -> None:
        rows = {1: week(10.0), 2: week(20.0), 3: week(0.0, snaps=0)}
        # played: 10 + 20 = 30 over 2 games; as-of 3 with bye 2 -> potential 2
        self.assertEqual({"AvgPotentialGame": 15.0, "AvgGame": 15.0}, pv.current_inputs(rows, "WR", 3, 2))
        # bye after the as-of week -> potential 3
        self.assertEqual({"AvgPotentialGame": 10.0, "AvgGame": 15.0}, pv.current_inputs(rows, "WR", 3, 5))
        # no team means bye week 0, which counts as passed (RequestPlayers.ps1 parity)
        self.assertEqual({"AvgPotentialGame": 15.0, "AvgGame": 15.0}, pv.current_inputs(rows, "WR", 3, 0))

    def test_current_inputs_without_potential_or_games_are_zero_not_missing(self) -> None:
        self.assertEqual({"AvgPotentialGame": 0.0, "AvgGame": 0.0}, pv.current_inputs({1: week(10.0)}, "WR", 0, 4))
        self.assertEqual({"AvgPotentialGame": 0.0, "AvgGame": 0.0}, pv.current_inputs({}, "WR", 4, 9))

    def test_current_inputs_use_the_exact_total_history_inputs_the_rounded_total(self) -> None:
        rows = {1: week(10.004), 2: week(10.004), 3: week(10.004)}
        # exact 30.012: 30.012 / 3 = 10.004 -> 10.0 ; 30.012 / 4 potential = 7.503 -> 7.5
        self.assertEqual({"AvgPotentialGame": 7.5, "AvgGame": 10.0}, pv.current_inputs(rows, "WR", 4, 9))
        # history: total rounded first to 30.01; 30.01 / 16 = 1.875625 -> 1.88 ; 30.01 / 3 = 10.0033 -> 10.0
        self.assertEqual({"AvgPotentialGame": 1.88, "AvgGame": 10.0}, pv.history_inputs(rows, "WR", 17))

    def test_history_inputs_count_weeks_up_to_last_league_week_only(self) -> None:
        rows = {17: week(16.0), 18: week(500.0)}
        self.assertEqual({"AvgPotentialGame": 1.0, "AvgGame": 16.0}, pv.history_inputs(rows, "WR", 17))

    def test_bye_week_of_defaults_to_zero(self) -> None:
        self.assertEqual(3, pv.bye_week_of("AAA", {"AAA": 3}))
        self.assertEqual(0, pv.bye_week_of(None, {"AAA": 3}))
        self.assertEqual(0, pv.bye_week_of("ZZZ", {"AAA": 3}))


class SnapshotTests(unittest.TestCase):
    def players(self) -> list[pv.PlayerBasis]:
        return [
            basis("20", "NFLP-b", "RB", "BBB", weeks={2030: {1: week(12.0), 2: week(18.0), 3: week(9.0)},
                                                       2029: {1: week(15.0), 2: week(14.0)}}),
            basis("10", "NFLP-a", "WR", "AAA", weeks={2030: {1: week(30.0), 2: week(22.0)},
                                                       2029: {1: week(25.0), 2: week(25.0), 3: week(20.0)},
                                                       2028: {1: week(11.0)}}),
            basis("30", None, "K", None, status="ambiguous", weeks={}),
            basis("40", "NFLP-d", "TE", "AAA", weeks={}),
        ]

    def test_rows_are_sorted_by_key_and_prefer_the_canonical_id(self) -> None:
        snapshot = pv.build_snapshot(context(), self.players(), no_hold)
        self.assertEqual(["30", "NFLP-a", "NFLP-b", "NFLP-d"], [r["CanonicalPlayerID"] or r["PlayerID"] for r in snapshot["Players"]])
        self.assertEqual("10", snapshot["Players"][1]["PlayerID"])

    def test_root_and_row_shape_follow_the_contract(self) -> None:
        snapshot = pv.build_snapshot(context(), self.players(), no_hold)
        self.assertEqual(["ContractVersion", "CanonicalLeagueID", "Season", "AsOfFinalScoredWeek", "ScoringProfile",
                          "Models", "League", "Players"], list(snapshot))
        self.assertEqual(["CanonicalPlayerID", "PlayerID", "Position", "Population", "Hold", "Inputs", "SeasonValues", "FormGames", "Salary",
                          "SalaryProjected", "Ranking", "Grading"], list(snapshot["Players"][1]))
        self.assertEqual(["Current", "SeasonMinus1", "SeasonMinus2", "SeasonMinus3"], list(snapshot["Players"][1]["Inputs"]))
        self.assertEqual(MODEL_IDS, snapshot["Models"])
        self.assertEqual({"TeamCount", "SalaryRelevantTeamSize", "TopN", "SalaryCap", "SalaryCapProjected"}, set(snapshot["League"]))

    def test_values_equal_the_models_applied_to_the_inputs(self) -> None:
        snapshot = pv.build_snapshot(context(as_of=3), self.players(), no_hold)
        salary_model = get_model("salary-v1")
        by_key = {r["CanonicalPlayerID"]: r for r in snapshot["Players"] if r["CanonicalPlayerID"]}
        row = by_key["NFLP-a"]
        i = row["Inputs"]
        expected = salary_model.compute(*(salary_model.SeasonInput(i[n]["AvgPotentialGame"], i[n]["AvgGame"])
                                          for n in ("Current", "SeasonMinus1", "SeasonMinus2", "SeasonMinus3")), 3)
        self.assertEqual((expected.salary, expected.salary_projected), (row["Salary"], row["SalaryProjected"]))
        # hand-computed Inputs: AAA bye 3 <= as-of 3 -> potential 2; total 52 -> 26.0 / 26.0
        self.assertEqual({"AvgPotentialGame": 26.0, "AvgGame": 26.0}, i["Current"])
        # previous season: 70 over 16 potential games = 4.375 -> 4.38 ; per game 70 / 3 = 23.33
        self.assertEqual({"AvgPotentialGame": 4.38, "AvgGame": 23.33}, i["SeasonMinus1"])

    def test_ranking_and_grading_follow_the_ranking_function(self) -> None:
        snapshot = pv.build_snapshot(context(as_of=3), self.players(), no_hold)
        rows = {r["CanonicalPlayerID"] or r["PlayerID"]: r for r in snapshot["Players"]}
        ranking = compute_rankings([
            RankingInput(k, r["Position"], r["Inputs"]["Current"]["AvgPotentialGame"], r["Inputs"]["Current"]["AvgGame"],
                         r["Inputs"]["SeasonMinus1"]["AvgPotentialGame"], r["Inputs"]["SeasonMinus1"]["AvgGame"])
            for k, r in rows.items() if r["Inputs"] is not None
        ])
        for key, row in rows.items():
            if row["Inputs"] is not None:
                self.assertEqual(ranking[key], row["Ranking"])
                combined_pos = next((x["Value"] for x in row["Ranking"] if x["Type"] == "Combined_Pos"), None)
                self.assertEqual([get_model("grading-v1").rank_row(combined_pos, row["Position"])], row["Grading"])
        # a player without any points is unranked and gets no grade (null rank, null grade)
        self.assertEqual([], rows["NFLP-d"]["Ranking"])
        self.assertEqual([{"Type": "Rank", "Value": None, "Rank": None, "Grade": None}], rows["NFLP-d"]["Grading"])

    def test_salary_cap_comes_from_the_cap_model_over_all_valued_rows(self) -> None:
        snapshot = pv.build_snapshot(context(as_of=3, team_count=2), self.players(), no_hold)
        cap_model = get_model("salary-cap-v1")
        valued = [r for r in snapshot["Players"] if r["Inputs"] is not None]
        self.assertEqual(cap_model.compute([r["Salary"] for r in valued], 2).cap, snapshot["League"]["SalaryCap"])
        self.assertEqual(cap_model.compute([r["SalaryProjected"] for r in valued], 2).cap, snapshot["League"]["SalaryCapProjected"])
        self.assertEqual(40, snapshot["League"]["TopN"])

    def test_unresolved_identity_without_hold_source_is_unknown_not_zero(self) -> None:
        snapshot = pv.build_snapshot(context(), self.players(), no_hold)
        row = snapshot["Players"][0]
        self.assertEqual("30", row["PlayerID"])
        self.assertEqual({"Reason": "ambiguous", "SourceWeek": None}, row["Hold"])
        self.assertIsNone(row["Inputs"])
        self.assertIsNone(row["Salary"])
        self.assertIsNone(row["SalaryProjected"])
        self.assertEqual([], row["Ranking"])
        self.assertEqual([], row["Grading"])

    def test_held_inputs_are_recomputed_and_ranked_with_everyone_else(self) -> None:
        held = {name: {"AvgPotentialGame": 9.0, "AvgGame": 9.5} for name in ("Current", "SeasonMinus1", "SeasonMinus2", "SeasonMinus3")}
        snapshot = pv.build_snapshot(context(as_of=4), self.players(), lambda key: (held, 2) if key == "30" else (None, None))
        row = snapshot["Players"][0]
        self.assertEqual({"Reason": "ambiguous", "SourceWeek": 2}, row["Hold"])
        self.assertEqual(held, row["Inputs"])
        salary_model = get_model("salary-v1")
        expected = salary_model.compute(*(salary_model.SeasonInput(9.0, 9.5) for _ in range(4)), 4)
        self.assertEqual((expected.salary, expected.salary_projected), (row["Salary"], row["SalaryProjected"]))
        self.assertTrue(any(r["Type"] == "Combined_Pos" for r in row["Ranking"]))
        held["Current"]["AvgGame"] = 0.0  # the snapshot owns a copy of the held inputs
        self.assertEqual(9.5, row["Inputs"]["Current"]["AvgGame"])

    def test_results_ignore_weeks_after_the_as_of_week(self) -> None:
        players = self.players()
        base = pv.build_snapshot(context(as_of=2), players, no_hold)
        leaked = copy.deepcopy(players)
        leaked[0] = basis("20", "NFLP-b", "RB", "BBB", weeks={**leaked[0].weeks, 2030: {**leaked[0].weeks[2030], 3: week(900.0), 9: week(900.0)}})
        self.assertEqual(base, pv.build_snapshot(context(as_of=2), leaked, no_hold))

    def test_build_is_deterministic_and_leaves_the_input_untouched(self) -> None:
        players = self.players()
        before = copy.deepcopy(players)
        first = pv.build_snapshot(context(), players, no_hold)
        self.assertEqual(json.dumps(first), json.dumps(pv.build_snapshot(context(), players, no_hold)))
        self.assertEqual(before, players)

    def test_duplicate_row_keys_fail_closed(self) -> None:
        players = [basis("1", "NFLP-x"), basis("2", "NFLP-x")]
        with self.assertRaisesRegex(ValueError, "Duplicate player row key"):
            pv.build_snapshot(context(), players, no_hold)

    def test_a_row_without_any_id_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "without CanonicalPlayerID"):
            pv.build_snapshot(context(), [basis(None, None)], no_hold)

    def test_unknown_or_wrongly_typed_models_fail_closed(self) -> None:
        with self.assertRaises(UnknownModelError):
            pv.build_snapshot(context(model_ids={**MODEL_IDS, "Salary": "salary-v99"}), self.players(), no_hold)
        with self.assertRaises(UnknownModelError):
            pv.build_snapshot(context(model_ids={**MODEL_IDS, "Salary": "grading-v1"}), self.players(), no_hold)
        with self.assertRaisesRegex(ValueError, "model_ids"):
            pv.build_snapshot(context(model_ids={"Salary": "salary-v1"}), self.players(), no_hold)

    def test_a_snapshot_without_any_valued_player_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "No valued players"):
            pv.build_snapshot(context(), [basis("30", None, status="unmapped")], no_hold)

    def test_non_finite_points_fail_closed(self) -> None:
        bad = basis("1", "NFLP-x", weeks={2030: {1: week(float("nan"))}})
        with self.assertRaises(ValueError):
            pv.build_snapshot(context(), [bad], no_hold)


class SourceAdapterTests(unittest.TestCase):
    def write_schedule(self, root: Path, games: list[dict], dataset: str = "nflverse.schedules", season: int = 2030) -> None:
        path = root / DATA_SOURCE_ROOT / "nfl/schedules" / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"Season": season, "SourceDataset": dataset, "Games": games}), encoding="utf-8")

    @staticmethod
    def game(week_no: int, home: str, away: str, game_type: str = "REG") -> dict:
        return {"GameID": f"{week_no}_{home}_{away}", "GameType": game_type, "Week": week_no, "HomeTeam": home, "AwayTeam": away}

    def test_bye_weeks_are_the_single_regular_week_without_a_game(self) -> None:
        games = [self.game(1, "AAA", "BBB"), self.game(2, "AAA", "CCC"), self.game(3, "BBB", "CCC"),
                 self.game(4, "BBB", "AAA", game_type="POST")]
        with tempfile.TemporaryDirectory() as tmp:
            self.write_schedule(Path(tmp), games)
            self.assertEqual({"AAA": 3, "BBB": 2, "CCC": 1}, sources.team_bye_weeks(Path(tmp), 2030))

    def test_bye_weeks_fail_closed_on_bad_schedules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(sources.SourceError, "required for bye weeks"):
                sources.team_bye_weeks(root, 2030)
            self.write_schedule(root, [self.game(1, "AAA", "BBB")], dataset="other")
            with self.assertRaisesRegex(sources.SourceError, "Unexpected canonical NFL schedule"):
                sources.team_bye_weeks(root, 2030)
            self.write_schedule(root, [self.game(1, "AAA", "BBB"), self.game(1, "AAA", "CCC")])
            with self.assertRaisesRegex(sources.SourceError, "twice in week"):
                sources.team_bye_weeks(root, 2030)
            # four weeks, team BBB plays only weeks 1 and 4 -> two byes
            self.write_schedule(root, [self.game(1, "AAA", "BBB"), self.game(2, "AAA", "CCC"),
                                       self.game(3, "AAA", "CCC"), self.game(4, "AAA", "BBB")][:3] + [self.game(4, "CCC", "BBB")])
            with self.assertRaisesRegex(sources.SourceError, "expected one bye"):
                sources.team_bye_weeks(root, 2030)

    def test_repository_schedule_gives_every_team_exactly_one_bye(self) -> None:
        manifest = sources.league_manifest(REPO_ROOT, "nfl-reise")
        byes = sources.team_bye_weeks(REPO_ROOT, sources.current_season(manifest))
        self.assertGreaterEqual(len(byes), 30)
        self.assertTrue(all(isinstance(w, int) and w >= 1 for w in byes.values()))


class RegistryAlignmentTests(unittest.TestCase):
    def test_league_metadata_model_catalogue_matches_the_registry(self) -> None:
        by_kind = {name: {mid for mid in registry.model_ids() if get_model(mid).KIND == kind}
                   for name, kind in pv.MODEL_KINDS.items()}
        by_kind.update({name: {mid for mid in registry.model_ids() if get_model(mid).KIND == kind}
                        for name, kind in (("Standings", "standings"), ("Awards", "awards"), ("Lifecycle", "lifecycle"), ("Repairability", "repairability"), ("TeamRange", "team-range"), ("RosterCap", "roster-cap"), ("AutoCut", "auto-cut"))})
        known = {name: set(ids) for name, ids in league_metadata.KNOWN_MODEL_IDS.items()}
        self.assertEqual(by_kind, known)


class MaterializerIntegrationTests(unittest.TestCase):
    """Reads the repository's canonical facts for the current league season; asserts invariants only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.league_id = "nfl-reise"
        cls.manifest = sources.league_manifest(REPO_ROOT, cls.league_id)
        cls.season = sources.current_season(cls.manifest)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out_root = Path(cls.tmp.name)
        cls.first = derived_data.materialize_player_valuation(REPO_ROOT, cls.out_root, cls.league_id, [cls.season], False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def season_files(self) -> list[Path]:
        return sorted((self.out_root / "player-valuation" / self.league_id / str(self.season)).glob("week-*.json"))

    def test_one_snapshot_per_as_of_week_from_zero_to_the_final_scored_week(self) -> None:
        summary = self.first["Seasons"][0]
        names = [p.name for p in self.season_files()]
        self.assertEqual([f"week-{n:02d}.json" for n in range(summary["FinalScoredWeek"] + 1)], names)
        self.assertEqual(summary["Snapshots"], summary["Written"])

    def test_second_run_is_a_file_level_no_op(self) -> None:
        before = {p.name: p.read_bytes() for p in self.season_files()}
        again = derived_data.materialize_player_valuation(REPO_ROOT, self.out_root, self.league_id, [self.season], True)
        summary = again["Seasons"][0]
        self.assertEqual(0, summary["WouldWrite"])
        self.assertEqual(summary["Snapshots"], summary["Unchanged"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.season_files()})

    def test_snapshots_satisfy_the_contract_invariants(self) -> None:
        metadata = league_metadata.load_league_metadata(self.league_id, league_metadata.data_meta_root(REPO_ROOT))
        settings = json.loads((REPO_ROOT / DATA_SOURCE_ROOT / "leagues" / self.league_id / "seasons" / str(self.season) / "league.json").read_text(encoding="utf-8"))["ScoringSettings"]
        for path in self.season_files():
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(int(path.stem.split("-")[1]), snapshot["AsOfFinalScoredWeek"])
            self.assertEqual(self.season, snapshot["Season"])
            self.assertEqual(scoring_settings_fingerprint(settings), snapshot["ScoringProfile"]["SettingsHash"])
            self.assertEqual({k: league_metadata.model_for(metadata, self.season, k) for k in pv.MODEL_KINDS}, snapshot["Models"])
            keys = [r["CanonicalPlayerID"] or r["PlayerID"] for r in snapshot["Players"]]
            self.assertEqual(sorted(keys), keys)
            self.assertEqual(len(keys), len(set(keys)))
            salary_model = get_model(snapshot["Models"]["Salary"])
            valued = [r for r in snapshot["Players"] if r["Inputs"] is not None]
            self.assertTrue(valued)
            for row in valued:
                i = row["Inputs"]
                expected = salary_model.compute(*(salary_model.SeasonInput(i[n]["AvgPotentialGame"], i[n]["AvgGame"])
                                                  for n in ("Current", "SeasonMinus1", "SeasonMinus2", "SeasonMinus3")),
                                                snapshot["AsOfFinalScoredWeek"])
                self.assertEqual((expected.salary, expected.salary_projected), (row["Salary"], row["SalaryProjected"]))
                self.assertIsNone(row["Hold"] if row["Hold"] is None else None)
            cap_model = get_model(snapshot["Models"]["SalaryCap"])
            league = snapshot["League"]
            self.assertEqual(cap_model.compute([r["Salary"] for r in valued], league["TeamCount"]).cap, league["SalaryCap"])
            self.assertEqual(cap_model.compute([r["SalaryProjected"] for r in valued], league["TeamCount"]).cap, league["SalaryCapProjected"])

    def test_week_zero_depends_only_on_previous_seasons(self) -> None:
        snapshot = json.loads(self.season_files()[0].read_text(encoding="utf-8"))
        for row in snapshot["Players"]:
            if row["Inputs"] is not None:
                self.assertEqual({"AvgPotentialGame": 0.0, "AvgGame": 0.0}, row["Inputs"]["Current"])

    def test_v3_current_source_points_match_final_player_week_fantasy(self) -> None:
        """Permanent Fast guard: corrected new v3 scoring agrees with the other
        independently scored current-season PWF Actual path on canonical facts.
        """
        snapshot = json.loads(self.season_files()[-1].read_text(encoding="utf-8"))
        self.assertEqual(3, snapshot["ContractVersion"])
        final_week = snapshot["AsOfFinalScoredWeek"]
        root = REPO_ROOT / "data-derived" / "player-week-fantasy" / self.league_id / str(self.season)
        points: dict[str, float] = {}
        for week_no in range(1, final_week + 1):
            path = root / f"{week_no:02d}.json"
            if not path.is_file():
                self.skipTest(f"persisted current-season PWF missing for week {week_no}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            for record in payload["Records"]:
                actual = record.get("Actual") or {}
                if actual.get("State") == "final" and actual.get("Points") is not None:
                    cid = record["CanonicalPlayerID"]
                    points[cid] = points.get(cid, 0.0) + actual["Points"]
        differences = []
        checked = 0
        for row in snapshot["Players"]:
            cid = row.get("CanonicalPlayerID")
            current = (row.get("SeasonValues") or {}).get("Current") or {}
            if not cid or row.get("Hold") or current.get("FantasyPointsTotal") is None:
                continue
            checked += 1
            total = current["FantasyPointsTotal"]
            expected = points.get(cid, 0.0)
            if abs(total - expected) > 0.05:
                differences.append((cid, total, round(expected, 2)))
        self.assertGreater(checked, 0)
        self.assertEqual([], differences, f"new v3 score path diverges from PWF: {differences[:10]}")

    def test_unknown_season_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(sources.SourceError, "not in the league manifest"):
                derived_data.materialize_player_valuation(REPO_ROOT, Path(tmp), self.league_id, [1999], True)

    def test_completed_season_population_follows_the_roster_rule(self) -> None:
        completed = [s for s in sources.manifest_seasons(self.manifest) if s < self.season]
        if not completed:
            self.skipTest("league has no completed season")
        season = completed[-1]
        population, skipped = sources.historical_population(REPO_ROOT, self.league_id, season)
        self.assertTrue(population)
        ids = [row["SleeperID"] for row in population]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(row["Position"] in sources.APP_FANTASY_POSITIONS for row in population))
        self.assertTrue(all(sources.REASON_ROSTER in row["Reasons"] for row in population))
        owned = sources.league_owned_sleeper_ids(REPO_ROOT, self.league_id, season)
        self.assertEqual(set(ids) & owned, {row["SleeperID"] for row in population if sources.REASON_LEAGUE in row["Reasons"]})


class HoldSourceTests(unittest.TestCase):
    def write_snapshot(self, out_root: Path, week_no: int, key: str, inputs: dict | None) -> None:
        path = derived_data.snapshot_path(out_root, "test-league", 2030, week_no)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"Players": [{"CanonicalPlayerID": None, "PlayerID": key, "Inputs": inputs}]}), encoding="utf-8")

    def test_hold_lookup_prefers_the_same_week_then_the_newest_earlier_week(self) -> None:
        a, b = {"Current": {"AvgPotentialGame": 1.0, "AvgGame": 1.0}}, {"Current": {"AvgPotentialGame": 2.0, "AvgGame": 2.0}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_snapshot(out, 1, "77", a)
            self.write_snapshot(out, 3, "77", b)
            self.write_snapshot(out, 4, "77", None)  # a persisted row without inputs is no hold source
            existing = derived_data.ExistingSnapshots(out, "test-league", 2030)
            self.assertEqual((b, 3), existing.lookup_for(3)("77"))
            self.assertEqual((b, 3), existing.lookup_for(5)("77"))
            self.assertEqual((a, 1), existing.lookup_for(2)("77"))
            self.assertEqual((None, None), existing.lookup_for(0)("77"))
            self.assertEqual((None, None), existing.lookup_for(5)("unknown"))

    def test_serialization_is_compact_deterministic_and_newline_terminated(self) -> None:
        text = derived_data.serialize({"B": 1, "A": [1, 2], "C": "ä"})
        self.assertEqual('{"B":1,"A":[1,2],"C":"ä"}\n', text)


if __name__ == "__main__":
    unittest.main()


class RetiredHoldSeedContractTests(unittest.TestCase):
    """ADR-076: valuation holds come only from persisted snapshots."""

    def test_published_players_seed_interface_is_retired(self):
        import inspect
        from unittest import mock

        self.assertNotIn("hold_seed", inspect.signature(derived_data.materialize_player_valuation).parameters)
        self.assertFalse(hasattr(derived_data, "load_hold_seed"))
        self.assertFalse(hasattr(derived_data, "_with_seed"))
        with mock.patch("sys.argv", [
            "derived_data.py", "materialize", "--product", "player-valuation",
            "--hold-seed-players-file", "/tmp/retired.json"
        ]):
            with self.assertRaises(SystemExit) as error:
                derived_data.parse_args()
            self.assertEqual(2, error.exception.code)

    def test_hold_lookup_still_reuses_last_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = derived_data.snapshot_path(root, "test-league", 2030, 4)
            path.parent.mkdir(parents=True, exist_ok=True)
            inputs = {"Current": {"AvgPotentialGame": 9.0, "AvgGame": 8.0}}
            path.write_text(json.dumps({"Players": [
                {"CanonicalPlayerID": None, "PlayerID": "hold-9", "Inputs": inputs}
            ]}), encoding="utf-8")
            existing = derived_data.ExistingSnapshots(root, "test-league", 2030)
            self.assertEqual((inputs, 4), existing.lookup_for(5)("hold-9"))
            self.assertEqual((None, None), existing.lookup_for(5)("missing"))
