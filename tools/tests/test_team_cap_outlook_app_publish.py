"""Synthetic Fast regressions for the central L10 App delivery model (#1237)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import team_cap_outlook_app_publish as pub  # noqa: E402


def rosters():
    return [{"ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": "1"}],
             "Players": [{"ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": str(i)}]}
                         for i in range(1, 8)]}]


def valuation():
    return {"CanonicalLeagueID": "league", "Season": 2026, "AsOfFinalScoredWeek": 7,
            "League": {"SalaryRelevantTeamSize": 20, "TeamCount": 1,
                       "SalaryCap": 250, "SalaryCapProjected": 500},
            "Players": [{"PlayerID": str(i), "Salary": value, "SalaryProjected": value + 10}
                        for i, value in enumerate((70, 60, 50, 40, 30, 20, 10), 1)]}


def metadata():
    return {"CurrentProviderLeagueID": "123456", "Seasons": {"2026": {"Models": {
        "RosterCap": "roster-cap-v1", "AutoCut": "auto-cut-v1", "SalaryCap": "salary-cap-v1"}}}}


class TeamCapOutlookTests(unittest.TestCase):
    def test_witness_and_projected_cuts(self):
        # The productive salary-cap-v1 uses TopN=20; with fewer players all salaries contribute.
        value = valuation()
        value["League"]["SalaryCap"] = 250
        result = pub.build("league", 2026, rosters(), value, metadata())
        team = result["Teams"][0]
        self.assertEqual(("ready", 280), (team["Status"], team["Current"]["Usage"]))
        self.assertEqual(["6", "7"], [c["PlayerID"] for c in team["Current"]["Cuts"]])
        self.assertEqual((280, 260), (team["Current"]["Cuts"][0]["CapBeforeCut"],
                                      team["Current"]["Cuts"][0]["CapAfterCut"]))
        self.assertEqual(350, team["Projected"]["Usage"])
        self.assertEqual([], team["Projected"]["Cuts"])
        self.assertEqual("1", team["InputRoster"][0]["PlayerID"])
        self.assertEqual(20, result["SalaryRelevantTeamSize"])

    def test_missing_salary_fails_closed_per_team(self):
        value = valuation()
        value["Players"] = value["Players"][:-1]
        team = pub.build("league", 2026, rosters(), value, metadata())["Teams"][0]
        self.assertEqual("unavailable", team["Status"])
        self.assertEqual(["7"], team["MissingPlayerIDs"])
        self.assertNotIn("Current", team)

    def test_conflicting_identity_and_population_fail_closed(self):
        value = valuation()
        value["League"]["TeamCount"] = 2
        with self.assertRaises(pub.OutlookError):
            pub.build("league", 2026, rosters(), value, metadata())
        value = valuation()
        broken = rosters()
        broken[0]["Players"].append(broken[0]["Players"][0])
        with self.assertRaises(pub.OutlookError):
            pub.build("league", 2026, broken, value, metadata())

    def test_live_write_fail_soft_and_explicit_check_fails_closed(self):
        with mock.patch.object(pub, "write", side_effect=pub.OutlookError("source unavailable")):
            self.assertEqual(0, pub.main(["write", "--league", "league"]))
        with mock.patch.object(pub, "load", side_effect=pub.OutlookError("source unavailable")):
            self.assertEqual(1, pub.main(["check", "--league", "league"]))

    def test_published_file_semantic_noop_and_stale_detection_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(pub, "load", return_value=pub.build("league", 2026, rosters(), valuation(), metadata())):
                self.assertTrue(pub.write(root, "league"))
                self.assertFalse(pub.write(root, "league"))
                output = json.loads((root / "public/data/TeamCapOutlook.json").read_text())
                self.assertEqual(output["Models"], {"RosterCap": "roster-cap-v1", "AutoCut": "auto-cut-v1"})
                self.assertEqual(len(output["Teams"][0]["InputRoster"]), 7)


if __name__ == "__main__":
    unittest.main()
