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


class AggregationTests(unittest.TestCase):
    def test_scaled_round_rounds_half_to_even_after_scaling(self) -> None:
        self.assertEqual(0.12, pv.scaled_round(0.125, 2))   # 12.5 -> 12
        self.assertEqual(0.14, pv.scaled_round(0.135, 2))   # 13.5 -> 14
        self.assertEqual(1.0, pv.scaled_round(1.005, 2))    # 1.005 * 100 = 100.49999999999999

    def test_played_points_filters_position_rule_week_and_orders_by_week(self) -> None:
        rows = {3: week(7.0), 1: week(10.0), 2: week(99.0, snaps=0), 6: week(50.0)}
        self.assertEqual([10.0, 7.0], pv.played_points(rows, "WR", 5))
        kicker = {1: week(4.0, snaps=0, kick_attempts=2), 2: week(9.0, snaps=60, kick_attempts=0)}
        self.assertEqual([4.0], pv.played_points(kicker, "K", 5))

    def test_current_inputs_potential_games_exclude_a_passed_bye_week(self) -> None:
        rows = {1: week(10.0), 2: week(20.0), 3: week(5.0, snaps=0)}
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
        self.assertEqual(["CanonicalPlayerID", "PlayerID", "Position", "Population", "Hold", "Inputs", "Salary",
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
                        for name, kind in (("Standings", "standings"), ("Awards", "awards"), ("Lifecycle", "lifecycle"), ("Repairability", "repairability"))})
        # Transitional (Issue #1199 section 3): team-range-v1 is catalogued in data-meta since step 1 and registered in step 6.
        known = {name: set(ids) for name, ids in league_metadata.KNOWN_MODEL_IDS.items() if name != "TeamRange"}
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


class HoldSeedTests(unittest.TestCase):
    """Cutover hold seed (Issue #919 step 5): values of the last published Players.json for identity-hold rows."""

    @staticmethod
    def _player(player_id: str, base: float) -> dict:
        return {
            "ID": player_id,
            "FantasyPointsAvgPotentialGame": base,
            "FantasyPointsAvgGame": base + 1,
            "PointHistory": {
                name: {"AvgPotentialGame": base + i, "AvgGame": base + i + 0.5}
                for i, name in enumerate(("SeasonMinus1", "SeasonMinus2", "SeasonMinus3"), start=2)
            },
        }

    def test_seed_maps_published_fields_to_inputs_by_sleeper_id(self):
        import json
        import tempfile
        from pathlib import Path

        import derived_data

        broken = {"ID": "9", "FantasyPointsAvgGame": 1.0}  # no PointHistory: cannot seed, must be skipped
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Players.json"
            path.write_text(json.dumps([self._player("1", 10.0), broken]), encoding="utf-8")
            seed = derived_data.load_hold_seed(path)
        self.assertEqual(set(seed), {"1"})
        self.assertEqual(seed["1"]["Current"], {"AvgPotentialGame": 10.0, "AvgGame": 11.0})
        self.assertEqual(seed["1"]["SeasonMinus1"], {"AvgPotentialGame": 12.0, "AvgGame": 12.5})
        self.assertEqual(seed["1"]["SeasonMinus3"], {"AvgPotentialGame": 14.0, "AvgGame": 14.5})

    def test_seed_is_only_a_fallback_behind_persisted_snapshots(self):
        import derived_data

        persisted = {"A": ({"Current": "snapshot"}, 3)}
        lookup = derived_data._with_seed(lambda key: persisted.get(key, (None, None)),
                                         {"A": {"Current": "seed"}, "B": {"Current": "seed"}}, 5)
        self.assertEqual(lookup("A"), ({"Current": "snapshot"}, 3))
        self.assertEqual(lookup("B"), ({"Current": "seed"}, 5))
        self.assertEqual(lookup("C"), (None, None))
