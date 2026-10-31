"""Players read model (ADR-076, Issue #1226 step 3b): assembly, hold rule, Age and change detection on synthetic players.

Port of public/requests/PlayersChangeDetectionRegressionTest.ps1 plus the Players parts of the PowerShell tests. No real
player, league or point value is hard-wired; the real-data comparison is the shadow of step 4.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import derived_data_lib.players_read_model as prm  # noqa: E402

AS_OF = date(2030, 10, 1)
BOUNDS = prm.WeekBounds(last_league_week=17, playoff_start_week=15, final_scored_week=5)
CURRENT = {
    "GamesPlayed": 3, "GamesPotential": 4, "SnapsTotal": 100, "AttemptsTotal": 20, "FantasyPointsTotal": 30.5,
    "FantasyPointsAvgGame": 10.17, "FantasyPointsAvgPotentialGame": 7.63, "FantasyPointsAvgSnap": 0.305,
    "FantasyPointsAvgAttempt": 1.525, "TouchdownsTotal": 3, "TouchdownsPassing": 1, "TouchdownsReceiving": 1,
    "TouchdownsRushing": 1,
}
HISTORY = {"Total": 12.0, "AvgGame": 6.0, "AvgPotentialGame": 0.75, "GamesPlayed": 2, "PotentialGames": 16}


def entry(sleeper_id: str, **overrides) -> dict:
    base = {
        "SleeperID": sleeper_id, "Position": "WR", "TeamAbbr": "AAA", "TeamID": "AAA", "IsFreeAgent": False,
        "Status": "Active", "FullName": f"Player {sleeper_id}", "FirstName": "P", "LastName": sleeper_id,
        "YearsExp": 2, "College": "State", "HighSchool": "High", "Number": 12, "NameShort": "P. X",
        "Picture": "pic", "PictureLarge": "pic-l", "FantasyPros": "fp", "ESPN": "espn", "BirthDate": "2000-10-01",
        "Injury": {"Status": None, "StartDate": None, "BodyPart": "Knee", "Notes": "stale"},
    }
    base.update(overrides)
    return base


def game(game_id: str, week: int, final: bool = True, **extra) -> dict:
    base = {
        "GameID": game_id, "Week": week, "WeekFinal": final, "Date": "20301001", "Home": "AAA", "Away": "BBB",
        "HomePoints": 21, "AwayPoints": 14, "TeamID": "AAA", "TeamAbv": "AAA", "FantasyPoints": 10.004,
        "Touchdowns": 1, "SnapCount": 40, "SnapPercentage": 0.8, "Attempts": 5,
    }
    base.update(extra)
    return base


def valuation(**overrides) -> dict:
    base = {
        "Hold": None, "Salary": 1000, "SalaryProjected": 900,
        "Ranking": [{"Type": "Total", "Value": 3}],
        "Grading": [{"Type": "Rank", "Value": 3, "Rank": 3, "Grade": "B"}],
        "SeasonValues": {"Current": dict(CURRENT), "SeasonMinus1": dict(HISTORY), "SeasonMinus2": dict(HISTORY),
                         "SeasonMinus3": dict(HISTORY)},
        "FormGames": ["g3", "g2"],
    }
    base.update(overrides)
    return base


def inputs(population=None, rows=None, histories=None, depth=None, bye=None, basis=None) -> prm.ReadModelInputs:
    population = population if population is not None else [entry("1")]
    return prm.ReadModelInputs(
        league_id="test-league", season=2030, bounds=BOUNDS, population=population,
        valuation_rows=rows if rows is not None else {"1": valuation()},
        game_histories=histories if histories is not None else {"1": [game("g3", 3), game("g2", 2), game("g1", 1)]},
        depth_charts=depth if depth is not None else {"1": {"Position": "WR", "Order": 2}},
        bye_weeks=bye if bye is not None else {"AAA": 7}, roster_basis=basis or {},
    )


class AgeAndInjuryTests(unittest.TestCase):
    def test_age_uses_the_reference_date_and_net_rounding(self) -> None:
        self.assertEqual(30.0, prm.age_at("2000-10-01", AS_OF))
        self.assertGreater(prm.age_at("2000-10-01", date(2031, 4, 1)), prm.age_at("2000-10-01", AS_OF))

    def test_age_is_none_for_a_missing_or_unparsable_birth_date(self) -> None:
        for value in (None, "", "2000/10/01", "not-a-date"):
            self.assertIsNone(prm.age_at(value, AS_OF))

    def test_injury_description_only_exists_with_a_designation(self) -> None:
        injured, details = prm.injury_details({"Status": " Questionable ", "Notes": "", "BodyPart": "Knee"})
        self.assertTrue(injured)
        self.assertEqual({"ReturnDate": None, "Description": "Knee", "Date": "", "Designation": "Questionable"}, details)
        injured, details = prm.injury_details({"Status": None, "Notes": "stale", "BodyPart": "Knee", "StartDate": "2030-01-01"})
        self.assertFalse(injured)
        self.assertEqual("", details["Description"])
        self.assertEqual("2030-01-01", details["Date"])
        self.assertEqual((False, {"ReturnDate": None, "Description": "", "Date": "", "Designation": ""}),
                         prm.injury_details(None))


class GameHistoryTests(unittest.TestCase):
    def test_week_flags_follow_the_league_week_structure(self) -> None:
        regular = prm.game_history_entry(game("a", 14), 15, 17)["GameDetails"]
        playoff = prm.game_history_entry(game("b", 15), 15, 17)["GameDetails"]
        after = prm.game_history_entry(game("c", 18), 15, 17)["GameDetails"]
        self.assertEqual((False, True), (regular["WeekPlayoff"], regular["WeekScored"]))
        self.assertEqual((True, True), (playoff["WeekPlayoff"], playoff["WeekScored"]))
        self.assertEqual((True, False), (after["WeekPlayoff"], after["WeekScored"]))
        self.assertFalse(prm.game_history_entry(game("d", 16), 0, 17)["GameDetails"]["WeekPlayoff"])

    def test_blocks_exist_only_when_the_export_has_them_and_unknown_stays_null(self) -> None:
        plain = prm.game_history_entry(game("a", 1), 15, 17)
        self.assertEqual({"GameID", "GameDetails", "TeamID", "TeamAbv", "FantasyPoints", "Touchdowns", "SnapCount",
                          "SnapPercentage", "Attempts"}, set(plain))
        self.assertEqual(10.0, plain["FantasyPoints"])
        rich = prm.game_history_entry(game("a", 1, Rushing={"RushAvg": 4, "RushYards": 8, "Carries": 2, "LongRush": None,
                                                              "RushTDs": 0}), 15, 17)
        self.assertIsNone(rich["Rushing"]["LongRush"])
        self.assertIsInstance(rich["Rushing"]["RushAvg"], float)

    def test_form_value_keeps_the_published_shape(self) -> None:
        self.assertIsNone(prm.form_value([]))
        self.assertEqual({"GameID": "x"}, prm.form_value([{"GameID": "x"}]))
        self.assertEqual([{"GameID": "x"}, {"GameID": "y"}], prm.form_value([{"GameID": "x"}, {"GameID": "y"}]))


class AssembleTests(unittest.TestCase):
    def test_row_copies_the_product_values_and_keeps_the_contract_keys(self) -> None:
        row = prm.assemble(inputs(), AS_OF).players[0]
        self.assertEqual(["ID", "Name", "NameFirst", "NameLast", "NameShort", "TeamID", "TeamAbbr", "ByeWeek", "Status",
                          "IsFreeAgent", "Position", "Age", "Year", "Number", "Salary", "SalaryProjected", "Picture",
                          "PictureLarge", "FantasyPros", "ESPN", "SleeperDepthChartPosition", "SleeperDepthChartOrder",
                          "College", "HighSchool", "Injured", "InjuryDetails", "GamesPlayed", "GamesPotential",
                          "SnapsTotal", "AttemptsTotal", "FantasyPointsTotal", "FantasyPointsAvgGame",
                          "FantasyPointsAvgPotentialGame", "FantasyPointsAvgSnap", "FantasyPointsAvgAttempt", "Ranking",
                          "Grading", "PointHistory", "TouchdownsTotal", "TouchdownsPassing", "TouchdownsReceiving",
                          "TouchdownsRushing", "GameHistory"], list(row))
        self.assertEqual((1000.0, 900.0, 3, "12", 7, 30.0),
                         (row["Salary"], row["SalaryProjected"], row["Year"], row["Number"], row["ByeWeek"], row["Age"]))
        self.assertIsInstance(row["Salary"], float)
        for name, value in CURRENT.items():
            self.assertEqual(value, row[name], name)
        self.assertEqual({"SeasonMinus1": HISTORY, "SeasonMinus2": HISTORY, "SeasonMinus3": HISTORY}, row["PointHistory"])
        self.assertEqual([{"Type": "Total", "Value": 3}], row["Ranking"])
        self.assertEqual("Rank", row["Grading"][1]["Type"])
        self.assertEqual(3, len(row["GameHistory"]))

    def test_form_selects_games_by_id_in_product_order(self) -> None:
        row = prm.assemble(inputs(rows={"1": valuation(FormGames=["g2", "g1"])}), AS_OF).players[0]
        form = row["Grading"][0]
        self.assertEqual("Form", form["Type"])
        self.assertEqual(["g2", "g1"], [g["GameID"] for g in form["Value"]])
        single = prm.assemble(inputs(rows={"1": valuation(FormGames=["g1"])}), AS_OF).players[0]["Grading"][0]["Value"]
        self.assertEqual("g1", single["GameID"])
        none = prm.assemble(inputs(rows={"1": valuation(FormGames=[])}), AS_OF).players[0]["Grading"][0]["Value"]
        self.assertIsNone(none)

    def test_age_is_the_only_value_that_moves_with_the_reference_date(self) -> None:
        a = prm.assemble(inputs(), date(2030, 10, 1)).players
        b = prm.assemble(inputs(), date(2031, 1, 1)).players
        self.assertNotEqual(a[0]["Age"], b[0]["Age"])
        a[0]["Age"] = b[0]["Age"]
        self.assertEqual(a, b)

    def test_rows_are_sorted_by_id_and_a_player_without_age_is_not_published(self) -> None:
        population = [entry("30"), entry("100", BirthDate=None), entry("2")]
        rows = {key: valuation() for key in ("30", "100", "2")}
        result = prm.assemble(inputs(population, rows, {}, {}), AS_OF)
        self.assertEqual(["2", "30"], [p["ID"] for p in result.players])

    def test_player_without_team_has_bye_week_zero_and_unknown_depth_is_a_warning(self) -> None:
        free_agent = entry("1", TeamAbbr=None, TeamID=None, IsFreeAgent=True)
        result = prm.assemble(inputs([free_agent], depth={}), AS_OF)
        row = result.players[0]
        self.assertEqual(0, row["ByeWeek"])
        self.assertTrue(row["IsFreeAgent"])
        self.assertEqual((None, None), (row["SleeperDepthChartPosition"], row["SleeperDepthChartOrder"]))
        self.assertTrue(any("Depth chart unknown" in w for w in result.warnings))

    def test_population_and_snapshot_must_agree(self) -> None:
        with self.assertRaises(prm.PlayersReadModelError):
            prm.assemble(inputs(rows={}), AS_OF)
        with self.assertRaises(prm.PlayersReadModelError):
            prm.assemble(inputs(rows={"1": valuation(Grading=[])}), AS_OF)

    def test_previous_season_roster_is_reported(self) -> None:
        basis = {"UsedPreviousSeasonRoster": True, "Season": 2030, "RosterSeason": 2029}
        self.assertTrue(any("2029" in w for w in prm.assemble(inputs(basis=basis), AS_OF).warnings))

    def test_identity_hold_takes_held_values_and_has_no_game_history(self) -> None:
        held = valuation(Hold={"Reason": "unresolved", "SourceWeek": 4}, FormGames=[])
        result = prm.assemble(inputs(rows={"1": held}), AS_OF)
        row = result.players[0]
        self.assertEqual([], row["GameHistory"])
        self.assertIsNone(row["Grading"][0]["Value"])
        self.assertEqual(CURRENT["GamesPlayed"], row["GamesPlayed"])
        self.assertTrue(any("GameHistory is empty" in w for w in result.warnings))

    def test_identity_hold_without_values_is_a_visible_gap_not_an_old_value(self) -> None:
        gap = valuation(Hold={"Reason": "unresolved", "SourceWeek": None}, Salary=None, SalaryProjected=None, SeasonValues=None)
        result = prm.assemble(inputs([entry("1"), entry("2")], {"1": valuation(), "2": gap}, {}, {}), AS_OF)
        self.assertEqual(["1"], [p["ID"] for p in result.players])
        self.assertTrue(any("left out" in w and "Player 2" in w for w in result.warnings))

    def test_inputs_are_not_modified(self) -> None:
        source = inputs()
        before = copy.deepcopy((source.valuation_rows, source.game_histories, source.population))
        prm.assemble(source, AS_OF)
        self.assertEqual(before, (source.valuation_rows, source.game_histories, source.population))


class ChangeDetectionTests(unittest.TestCase):
    """Compare-Players semantics (port of PlayersChangeDetectionRegressionTest.ps1)."""

    @staticmethod
    def players(count: int) -> list[dict]:
        return [{"ID": str(i), "Name": f"Test Player {i}", "Salary": 100.0 + i, "Ranking": [], "PointHistory": None,
                 "Grading": [{"Type": "Form", "Value": [{"GameID": f"game_{i}",
                                                           "GameDetails": {"Week": 1, "WeekFinal": True, "Home": "AAA"}}]}]}
                for i in range(1, count + 1)]

    def test_identical_rebuild_and_reloaded_file_are_no_change(self) -> None:
        old = json.loads(prm.serialize_players(self.players(3)))
        self.assertFalse(prm.players_differ(old, self.players(3)))
        self.assertEqual("AAA", old[0]["Grading"][0]["Value"][0]["GameDetails"]["Home"])

    def test_order_does_not_matter_but_a_changed_field_and_the_count_do(self) -> None:
        old = self.players(3)
        self.assertFalse(prm.players_differ(old, list(reversed(self.players(3)))))
        edited = self.players(3)
        edited[1]["Salary"] = 999.0
        self.assertTrue(prm.players_differ(old, edited))
        self.assertTrue(prm.players_differ(old, self.players(4)))

    def test_no_published_file_counts_as_changed(self) -> None:
        self.assertTrue(prm.players_differ(None, self.players(2)))
        self.assertTrue(prm.players_differ([], self.players(2)))

    def test_missing_or_duplicate_ids_fail_closed(self) -> None:
        duplicate = self.players(2) + [dict(self.players(1)[0])]
        with self.assertRaises(prm.PlayersReadModelError):
            prm.players_differ(None, duplicate)
        with self.assertRaises(prm.PlayersReadModelError):
            prm.players_differ(self.players(2), [{"ID": "", "Name": "x"}])

    def test_int_and_float_values_are_different_published_forms(self) -> None:
        a, b = self.players(1), self.players(1)
        b[0]["Salary"] = 101
        self.assertTrue(prm.players_differ(a, b))

    def test_written_text_has_two_space_indent_and_one_trailing_newline(self) -> None:
        text = prm.serialize_players(self.players(1))
        self.assertTrue(text.startswith('[\n  {\n    "ID": "1"'))
        self.assertTrue(text.endswith("}\n]\n"))


if __name__ == "__main__":
    unittest.main()
