from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import players_league_scoring as scoring_export  # noqa: E402
import players_league_scoring_shadow as shadow  # noqa: E402


def _player(pid: str, position: str, avg_potential: float, avg_game: float, prev: tuple[float, float] = (0, 0)) -> dict:
    return {
        "ID": pid,
        "Position": position,
        "FantasyPointsAvgPotentialGame": avg_potential,
        "FantasyPointsAvgGame": avg_game,
        "PointHistory": {"SeasonMinus1": {"AvgPotentialGame": prev[0], "AvgGame": prev[1]}},
    }


class PureFunctionTests(unittest.TestCase):
    def test_net_round_rounds_half_to_even_on_the_scaled_value(self) -> None:
        # 22.8 / 128 = 0.178125; .NET [math]::Round(x, 5) scales first and rounds half to even.
        self.assertEqual(0.17812, shadow.net_round(22.8 / 128, 5))
        self.assertEqual(0.0, shadow.net_round(0.0, 2))

    def test_salary_is_zero_when_the_two_newest_seasons_are_zero(self) -> None:
        self.assertEqual(0.0, shadow.salary_with_floor(0, 0, 12.0))

    def test_salary_floor_lifts_low_seasons_to_a_share_of_the_maximum(self) -> None:
        floored = shadow.salary_with_floor(10.0, 0.0, 0.0)
        unfloored = shadow.ps_round(shadow.map_salary_nonlinear(10.0 / 3))
        self.assertGreater(floored, unfloored)

    def test_rankings_share_ranks_on_ties_and_skip_inactive_players(self) -> None:
        players = [
            _player("a", "WR", 10, 10),
            _player("b", "WR", 10, 10),
            _player("c", "WR", 5, 5),
            _player("d", "WR", 0, 0),
        ]
        ranks = shadow.compute_rankings(players, 0.5, 0.5)
        total = {pid: next(r["Value"] for r in rows if r["Type"] == "Total") for pid, rows in ranks.items() if rows}
        self.assertEqual({"a": 1, "b": 1, "c": 3}, total)
        self.assertEqual([], ranks["d"])

    def test_previous_season_ranking_uses_only_players_with_history(self) -> None:
        players = [_player("a", "QB", 4, 4, (9, 9)), _player("b", "QB", 4, 4, (3, 3)), _player("c", "QB", 4, 4)]
        ranks = shadow.compute_rankings(players, 0.5, 0.5)
        previous = {pid: next((r["Value"] for r in rows if r["Type"] == "Combined_Previous"), None)
                    for pid, rows in ranks.items()}
        self.assertEqual({"a": 1, "b": 2, "c": None}, previous)

    def test_letter_grade_scales_with_position(self) -> None:
        self.assertEqual("A", shadow.letter_grade(6, "K"))
        self.assertEqual("B", shadow.letter_grade(7, "K"))
        self.assertEqual("A", shadow.letter_grade(12, "WR"))
        self.assertEqual("F", shadow.letter_grade(46, "QB"))
        self.assertEqual("A", shadow.letter_grade(None, "QB"))

    def test_residual_classification_is_derived_from_the_scoring_weights(self) -> None:
        weights = [0.04, 0.1, 1.0, 4.0, 6.0]
        self.assertEqual("yardage-correction", shadow.classify_residual(0.5, weights))
        self.assertEqual("yardage-correction", shadow.classify_residual(-0.3, weights))
        # as large as a discrete event (reception, fumble): not explainable by a yardage correction
        self.assertIsNone(shadow.classify_residual(1.0, weights))
        # not a multiple of any yardage weight
        self.assertIsNone(shadow.classify_residual(0.07, weights))
        self.assertIsNone(shadow.classify_residual(0.5, [1.0, 6.0]))

    def test_gate_thresholds(self) -> None:
        ok = {"Diff": 0.5, "Class": "yardage-correction"}
        self.assertTrue(shadow.evaluate_gate(1000, 999, [ok], {}, {})["passed"])
        self.assertFalse(shadow.evaluate_gate(0, 0, [], {}, {})["passed"])
        low_rate = shadow.evaluate_gate(1000, 990, [ok] * 10, {}, {})
        self.assertFalse(low_rate["passed"])
        self.assertIn("exact rate", low_rate["failures"][0])
        self.assertFalse(shadow.evaluate_gate(1000, 999, [{"Diff": 2.5, "Class": "yardage-correction"}], {}, {})["passed"])
        self.assertFalse(shadow.evaluate_gate(1000, 999, [{"Diff": 0.5, "Class": "unclassified"}], {}, {})["passed"])
        self.assertFalse(shadow.evaluate_gate(1000, 1000, [], {}, {(2026, "some_key"): 1})["passed"])


def _resolver(mappings: list[tuple[str, int, int, str]], conflicts: list[tuple[str, int, int, list[str]]] = (),
              empty: tuple[str, ...] = ()) -> scoring_export.SleeperIdentityResolver:
    return scoring_export.SleeperIdentityResolver(
        {
            "Mappings": [
                {"Provider": "Sleeper", "ExternalID": sid, "CanonicalPlayerID": cid,
                 "FirstObservedSeason": first, "LastObservedSeason": last}
                for sid, first, last, cid in mappings
            ],
            "Conflicts": [
                {"Provider": "Sleeper", "ExternalID": sid, "CanonicalPlayerIDs": parties,
                 "FirstObservedSeason": first, "LastObservedSeason": last}
                for sid, first, last, parties in conflicts
            ],
        },
        {"Players": [{"CanonicalPlayerID": cid, "IDs": {}} for cid in empty]
         + [{"CanonicalPlayerID": cid, "IDs": {"GSIS": "x"}} for cid in ("A", "B", "C")]},
    )


class SleeperIdentityResolverTests(unittest.TestCase):
    def test_a_mapping_covers_the_seasons_it_was_observed_in(self) -> None:
        resolver = _resolver([("1", 2025, 2025, "A"), ("1", 2026, 2026, "B")])
        self.assertEqual(("A", "resolved"), resolver.resolve("1", 2025))
        self.assertEqual(("B", "resolved"), resolver.resolve("1", 2026))

    def test_seasons_before_the_first_observation_use_the_earliest_mapping(self) -> None:
        resolver = _resolver([("1", 2025, 2025, "A"), ("1", 2026, 2026, "B")])
        self.assertEqual(("A", "resolved"), resolver.resolve("1", 2023))
        # a gap between observations stays unmapped; later seasons without any mapping too
        gap = _resolver([("1", 2023, 2023, "A"), ("1", 2026, 2026, "B")])
        self.assertEqual((None, "unmapped"), gap.resolve("1", 2025))
        self.assertEqual((None, "unmapped"), resolver.resolve("1", 2027))

    def test_an_unknown_id_is_unmapped(self) -> None:
        self.assertEqual((None, "unmapped"), _resolver([]).resolve("9", 2026))

    def test_conflict_parties_are_candidates_and_an_empty_record_cannot_own_stats(self) -> None:
        resolver = _resolver([("1", 2026, 2026, "EMPTY")], [("1", 2026, 2026, ["A", "EMPTY"])], empty=("EMPTY",))
        self.assertEqual(("A", "resolved"), resolver.resolve("1", 2026))

    def test_two_records_with_identifiers_stay_ambiguous(self) -> None:
        resolver = _resolver([("1", 2026, 2026, "A")], [("1", 2026, 2026, ["A", "B"])])
        self.assertEqual((None, "ambiguous"), resolver.resolve("1", 2026))

    def test_a_record_without_identifiers_alone_is_unmapped(self) -> None:
        resolver = _resolver([("1", 2026, 2026, "EMPTY")], empty=("EMPTY",))
        self.assertEqual((None, "unmapped"), resolver.resolve("1", 2026))


class RepositoryDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = shadow.build_shadow(ROOT)

    def test_port_reproduces_the_committed_players_json(self) -> None:
        port = self.result["portValidation"]
        self.assertGreater(port["players"], 0)
        self.assertEqual({}, port["mismatches"])
        self.assertTrue(port["capMatchesPublished"])

    def test_sleeper_gate_passes(self) -> None:
        report = shadow.sleeper_gate(ROOT)
        self.assertGreater(report["compared"], 0)
        self.assertTrue(report["passed"], report["failures"])

    def test_shadow_keeps_row_set_and_identity_hold_rows(self) -> None:
        legacy, new = self.result["legacy"], self.result["shadow"]
        self.assertEqual([p["ID"] for p in legacy], [p["ID"] for p in new])
        held = {row["SleeperID"] for row in self.result["identityHold"]}
        for old, updated in zip(legacy, new):
            if updated["ID"] in held:
                for field in shadow.SCALAR_FIELDS:
                    self.assertEqual(old[field], updated[field], (updated["ID"], field))

    def test_shadow_rows_are_internally_consistent(self) -> None:
        last_week = self.result["lastWeek"]
        for player in self.result["shadow"]:
            self.assertGreaterEqual(player["Salary"], 0)
            self.assertGreaterEqual(player["SalaryProjected"], 0)
            self.assertLessEqual(player["GamesPlayed"], last_week)
            self.assertEqual(
                player["TouchdownsTotal"],
                player["TouchdownsPassing"] + player["TouchdownsReceiving"] + player["TouchdownsRushing"],
            )
            if player["GamesPlayed"]:
                self.assertAlmostEqual(
                    player["FantasyPointsAvgGame"], player["FantasyPointsTotal"] / player["GamesPlayed"], places=2)
            ranking = {r["Type"]: r["Value"] for r in player["Ranking"]}
            if "Combined_Pos" in ranking:
                self.assertGreaterEqual(ranking["Combined_Pos"], 1)
                rank_grading = next(g for g in player["Grading"] if g.get("Type") == "Rank")
                self.assertEqual(ranking["Combined_Pos"], rank_grading["Rank"])

    def test_shadow_cap_follows_the_shadow_salaries(self) -> None:
        # the cap is recomputed from the same salaries the shadow reports
        league_cap = self.result["cap"]
        self.assertEqual(2, len(league_cap["shadow"]))
        self.assertTrue(all(value > 0 for value in league_cap["shadow"]))

    def test_every_lost_history_row_is_reported(self) -> None:
        reported = {row["SleeperID"] for row in self.result["historyLoss"]}
        for old, new in zip(self.result["legacy"], self.result["shadow"]):
            if old["ID"] in {r["SleeperID"] for r in self.result["identityHold"]}:
                continue
            lost = any(
                old["PointHistory"][k]["GamesPlayed"] > 0 and new["PointHistory"][k]["GamesPlayed"] == 0
                for k in shadow.HISTORY_SEASONS
            ) or (old["GamesPlayed"] > 0 and new["GamesPlayed"] == 0)
            if lost:
                self.assertIn(old["ID"], reported)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import json

        cls.players = json.loads((ROOT / "public/data/Players.json").read_text(encoding="utf-8-sig"))
        cls.league = json.loads((ROOT / "public/data/League.json").read_text(encoding="utf-8-sig"))
        cls.season = int(cls.league["Season"])
        cls.export = scoring_export.build_export(
            ROOT, scoring_export.LEAGUE_ID, cls.season, [str(p["ID"]) for p in cls.players],
        )

    def test_export_is_deterministic_and_identified_by_the_scoring_profile(self) -> None:
        again = scoring_export.build_export(
            ROOT, scoring_export.LEAGUE_ID, self.season, [str(p["ID"]) for p in reversed(self.players)],
        )
        self.assertEqual(self.export, again)
        profile = self.export["ScoringProfile"]
        self.assertEqual(scoring_export.LEAGUE_ID, profile["CanonicalLeagueID"])
        self.assertEqual(self.season, profile["Season"])
        self.assertTrue(profile["SettingsHash"])

    def test_every_league_owned_player_resolves_and_current_rows_are_final_weeks_only(self) -> None:
        owned = scoring_export.league_owned_sleeper_ids(ROOT, scoring_export.LEAGUE_ID, self.season)
        final_weeks = set(self.export["FinalRegularWeeksCurrent"])
        self.assertTrue(final_weeks)
        for sleeper_id, entry in self.export["Players"].items():
            if sleeper_id in owned:
                self.assertEqual("resolved", entry["Status"], sleeper_id)
            if entry["Status"] != "resolved":
                self.assertEqual({}, entry["Seasons"])
                continue
            self.assertLessEqual({int(w) for w in entry["Seasons"][str(self.season)]}, final_weeks)

    def test_export_aggregates_to_the_shadow(self) -> None:
        # the shadow (approved D3 diff) is the expectation; the export rows must aggregate to it
        result = shadow.build_shadow(ROOT)
        last_week = result["lastWeek"]
        checked = 0
        for player in result["shadow"]:
            entry = self.export["Players"][str(player["ID"])]
            if entry["Status"] != "resolved":
                continue
            seasons = entry["Seasons"]
            for offset, key in enumerate(shadow.HISTORY_SEASONS, start=1):
                rows = {int(w): {
                    "points": r["Points"], "snaps": r["Snaps"], "kick_attempts": r["KickAttempts"],
                    "attempts": r["Attempts"], "td_pass": r["TdPass"], "td_rec": r["TdRec"], "td_rush": r["TdRush"],
                } for w, r in seasons[str(self.season - offset)].items()}
                expected = scoring_export.season_view(rows, player["Position"], last_week, last_week - 1)
                self.assertEqual(expected, player["PointHistory"][key], (player["ID"], key))
            checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
