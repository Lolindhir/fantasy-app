"""Tests for the PlayerValuation shadow comparison (Issue #919 step 4). Synthetic rows only."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import player_valuation_shadow as shadow  # noqa: E402


def _inputs(avg_potential: float, avg: float) -> dict:
    block = {"AvgPotentialGame": avg_potential, "AvgGame": avg}
    return {"Current": dict(block), "SeasonMinus1": dict(block), "SeasonMinus2": dict(block), "SeasonMinus3": dict(block)}


def _snap_row(pid: str = "1") -> dict:
    return {
        "CanonicalPlayerID": "c" + pid, "PlayerID": pid, "Position": "WR", "Population": ["roster"], "Hold": None,
        "Inputs": _inputs(10.5, 9.5), "Salary": 1000.0, "SalaryProjected": 900.0,
        "Ranking": [{"Type": "Total", "Value": 3}, {"Type": "Combined_Pos", "Value": 2}],
        "Grading": [{"Type": "Rank", "Value": 2, "Rank": 2, "Grade": "B"}],
    }


def _published(pid: str = "1") -> dict:
    return {
        "ID": pid, "Name": "Test Player", "Position": "WR", "Salary": 1000.0, "SalaryProjected": 900.0,
        "Ranking": [{"Type": "Combined_Pos", "Value": 2}, {"Type": "Total", "Value": 3}],
        "Grading": [{"Type": "Form", "Value": []}, {"Type": "Rank", "Value": 2, "Rank": 2, "Grade": "B"}],
        "FantasyPointsAvgPotentialGame": 10.5, "FantasyPointsAvgGame": 9.5,
        "PointHistory": {k: {"AvgPotentialGame": 10.5, "AvgGame": 9.5} for k in shadow.HISTORY_KEYS},
    }


def _snapshot(rows: list[dict]) -> dict:
    return {"Season": 2026, "AsOfFinalScoredWeek": 5, "Players": rows,
            "League": {"SalaryCap": 100, "SalaryCapProjected": 120, "TopN": 4}}


class ComparePlayerTests(unittest.TestCase):
    def test_identical_rows_have_no_differences_regardless_of_ranking_order(self) -> None:
        self.assertEqual(shadow.compare_player(_snap_row(), _published()), [])

    def test_salary_difference_is_exact_without_tolerance(self) -> None:
        pub = _published()
        pub["Salary"] = 1000.0000001
        fields = [d["Field"] for d in shadow.compare_player(_snap_row(), pub)]
        self.assertEqual(fields, ["Salary"])

    def test_missing_ranking_type_and_grade_difference_are_reported(self) -> None:
        pub = _published()
        pub["Ranking"] = [r for r in pub["Ranking"] if r["Type"] != "Total"]
        pub["Grading"][1]["Grade"] = "C"
        fields = {d["Field"] for d in shadow.compare_player(_snap_row(), pub)}
        self.assertEqual(fields, {"Ranking.Total", "Grading.Rank.Grade"})

    def test_input_averages_are_compared_for_current_and_history(self) -> None:
        pub = _published()
        pub["FantasyPointsAvgGame"] = 9.6
        pub["PointHistory"]["SeasonMinus2"]["AvgPotentialGame"] = 1.0
        fields = {d["Field"] for d in shadow.compare_player(_snap_row(), pub)}
        self.assertEqual(fields, {"Inputs.Current.AvgGame", "Inputs.SeasonMinus2.AvgPotentialGame"})

    def test_snapshot_row_without_inputs_is_a_difference(self) -> None:
        row = _snap_row()
        row["Inputs"] = None
        self.assertIn("Inputs", [d["Field"] for d in shadow.compare_player(row, _published())])

    def test_duplicate_rank_rows_fail_closed(self) -> None:
        pub = _published()
        pub["Grading"].append(copy.deepcopy(pub["Grading"][1]))
        with self.assertRaises(shadow.ShadowError):
            shadow.compare_player(_snap_row(), pub)


class CompareSnapshotTests(unittest.TestCase):
    LEAGUE = {"SalaryCap": 100, "SalaryCapProjected": 120}

    def test_exact_snapshot_reports_no_differences(self) -> None:
        result = shadow.compare_snapshot(_snapshot([_snap_row("1"), _snap_row("2")]), [_published("1"), _published("2")], self.LEAGUE)
        self.assertEqual((result["Compared"], result["FieldDifferences"], result["CapDifferences"]), (2, [], []))
        self.assertEqual((result["PublishedOnly"], result["SnapshotOnly"]), ([], []))

    def test_coverage_gaps_and_cap_differences_are_reported(self) -> None:
        result = shadow.compare_snapshot(_snapshot([_snap_row("1"), _snap_row("3")]), [_published("1"), _published("2")],
                                         {"SalaryCap": 101, "SalaryCapProjected": 120})
        self.assertEqual((result["PublishedOnly"], result["SnapshotOnly"]), (["2"], ["3"]))
        self.assertEqual([d["Field"] for d in result["CapDifferences"]], ["SalaryCap"])

    def test_duplicate_published_id_fails_closed(self) -> None:
        with self.assertRaises(shadow.ShadowError):
            shadow.compare_snapshot(_snapshot([_snap_row("1")]), [_published("1"), _published("1")], self.LEAGUE)

    def test_rows_without_sleeper_id_are_counted_not_compared(self) -> None:
        row = _snap_row("9")
        row["PlayerID"] = None
        result = shadow.compare_snapshot(_snapshot([_snap_row("1"), row]), [_published("1")], self.LEAGUE)
        self.assertEqual(result["SnapshotRowsWithoutSleeperID"], 1)
        self.assertEqual(result["SnapshotOnly"], [])


class PublishedWeekTests(unittest.TestCase):
    def test_non_integer_week_fails_closed(self) -> None:
        with self.assertRaises(shadow.ShadowError):
            shadow.published_week({"FinalScoredWeek": "5"}, [{"ID": "1"}])

    def test_empty_players_fail_closed(self) -> None:
        with self.assertRaises(shadow.ShadowError):
            shadow.published_week({"FinalScoredWeek": 5}, [])


class PlausibilityTests(unittest.TestCase):
    def test_holds_and_valued_rows_are_counted(self) -> None:
        held = _snap_row("2")
        held["Hold"] = {"Reason": "ambiguous", "SourceWeek": None}
        held["Inputs"] = None
        report = shadow.plausibility(_snapshot([_snap_row("1"), held]))
        self.assertEqual((report["Rows"], report["Valued"], report["Held"], report["HeldWithoutInputs"]), (2, 1, 1, 1))
        self.assertEqual(report["ByPosition"], {"WR": 2})


if __name__ == "__main__":
    unittest.main()
