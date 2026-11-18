"""I3: historical playoff paths cannot use later winners or later-seeded entrants (#1519)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from derived_data_lib.models.schedule_outlook import v1 as model  # noqa: E402

ROOT = TOOLS.parent


def synthetic_bracket():
    return [
        {"Match": 1, "Round": 1, "Placement": None,
         "Team1CanonicalLeagueRosterID": "a", "Team2CanonicalLeagueRosterID": "b",
         "Team1Source": None, "Team2Source": None,
         "WinnerCanonicalLeagueRosterID": "a", "LoserCanonicalLeagueRosterID": "b"},
        {"Match": 2, "Round": 1, "Placement": None,
         "Team1CanonicalLeagueRosterID": "c", "Team2CanonicalLeagueRosterID": "d",
         "Team1Source": None, "Team2Source": None,
         "WinnerCanonicalLeagueRosterID": "c", "LoserCanonicalLeagueRosterID": "d"},
        {"Match": 3, "Round": 2, "Placement": 1,
         "Team1CanonicalLeagueRosterID": "a", "Team2CanonicalLeagueRosterID": "c",
         "Team1Source": {"Match": 1, "Outcome": "Winner"},
         "Team2Source": {"Match": 2, "Outcome": "Winner"},
         "WinnerCanonicalLeagueRosterID": "a", "LoserCanonicalLeagueRosterID": "c"},
        {"Match": 4, "Round": 2, "Placement": 3,
         "Team1CanonicalLeagueRosterID": "b", "Team2CanonicalLeagueRosterID": "d",
         "Team1Source": {"Match": 1, "Outcome": "Loser"},
         "Team2Source": {"Match": 2, "Outcome": "Loser"},
         "WinnerCanonicalLeagueRosterID": "b", "LoserCanonicalLeagueRosterID": "d"},
    ]


def structure(round_type=2, rounds=2, start=14):
    return {"PlayoffStartWeek": start, "PlayoffRoundType": round_type, "PlayoffRoundCount": rounds,
            "PlayoffTeams": 4, "ObservedPlayoffFormat": "two-week-rounds",
            "ProjectedPlayoffFormat": None}


def compute(asof, *, winners=None, losers=None, spec=None):
    return model.compute_playoff_paths(
        structure=structure() if spec is None else spec,
        winners_bracket=synthetic_bracket() if winners is None else winners,
        losers_bracket=[] if losers is None else losers,
        canonical_roster_ids={"a", "b", "c", "d"},
        after_week=asof,
        regular_season_last_week=13,
    )


def find(result, match, bracket="winners"):
    return next(p for p in result["Paths"] if p["Match"] == match and p["Bracket"] == bracket)


class PlayoffCutoffTests(unittest.TestCase):
    def test_regular_season_hides_final_seeds_and_winners(self):
        v = compute(10)
        one = find(v, 1)
        self.assertEqual("not-started", one["RoundState"])
        self.assertEqual("unknown", one["ParticipantCertainty"])
        self.assertEqual([None, None], [p["CanonicalLeagueRosterID"] for p in one["Participants"]])
        self.assertIsNone(one["WinnerCanonicalLeagueRosterID"])
        late = find(v, 3)
        self.assertEqual("conditional", late["ParticipantCertainty"])
        self.assertEqual([None, None], [p["CanonicalLeagueRosterID"] for p in late["Participants"]])

    def test_after_rs_finalizes_seeds_not_future_match_results(self):
        v = compute(13)
        one = find(v, 1)
        self.assertEqual("confirmed", one["ParticipantCertainty"])
        self.assertEqual(["a", "b"], [p["CanonicalLeagueRosterID"] for p in one["Participants"]])
        self.assertIsNone(one["WinnerCanonicalLeagueRosterID"])
        self.assertEqual("conditional", find(v, 3)["ParticipantCertainty"])

    def test_two_week_round_not_final_after_first_leg(self):
        v = compute(14)
        first = find(v, 1)
        self.assertEqual("in-progress", first["RoundState"])
        self.assertIsNone(first["WinnerCanonicalLeagueRosterID"])
        self.assertEqual("conditional", find(v, 3)["ParticipantCertainty"])
        self.assertEqual([[14, 15], [16, 17]], v["Format"]["RoundWeeks"])

    def test_final_first_round_resolves_conditional_final_slots(self):
        v = compute(15)
        first, finale, placement = find(v, 1), find(v, 3), find(v, 4)
        self.assertEqual("final", first["RoundState"])
        self.assertEqual("a", first["WinnerCanonicalLeagueRosterID"])
        self.assertEqual("not-started", finale["RoundState"])
        self.assertEqual("confirmed", finale["ParticipantCertainty"])
        self.assertEqual(["a", "c"], [p["CanonicalLeagueRosterID"] for p in finale["Participants"]])
        self.assertEqual(["b", "d"], [p["CanonicalLeagueRosterID"] for p in placement["Participants"]])
        self.assertIsNone(finale["WinnerCanonicalLeagueRosterID"])

    def test_two_week_final_not_resolved_after_first_leg(self):
        v = compute(16)
        self.assertEqual("in-progress", find(v, 3)["RoundState"])
        self.assertIsNone(find(v, 3)["WinnerCanonicalLeagueRosterID"])
        self.assertEqual("a", find(compute(17), 3)["WinnerCanonicalLeagueRosterID"])

    def test_mixed_round_type_one_has_two_leg_final_only(self):
        spec = structure(round_type=1, rounds=2)
        early = compute(14, spec=spec)
        self.assertEqual([[14], [15, 16]], early["Format"]["RoundWeeks"])
        self.assertEqual("final", find(early, 1)["RoundState"])
        self.assertEqual("not-started", find(early, 3)["RoundState"])
        partial_final = compute(15, spec=spec)
        self.assertEqual("in-progress", find(partial_final, 3)["RoundState"])
        self.assertIsNone(find(partial_final, 3)["WinnerCanonicalLeagueRosterID"])
        self.assertEqual("a", find(compute(16, spec=spec), 3)["WinnerCanonicalLeagueRosterID"])

    def test_invalid_routing_and_impossible_winners_fail_closed(self):
        broken = synthetic_bracket()
        broken[2]["Team1Source"] = {"Match": 3, "Outcome": "Winner"}
        with self.assertRaisesRegex(model.ScheduleOutlookError, "forward"):
            compute(15, winners=broken)
        broken = synthetic_bracket()
        broken[0]["WinnerCanonicalLeagueRosterID"] = "d"
        with self.assertRaisesRegex(model.ScheduleOutlookError, "Invalid confirmed"):
            compute(15, winners=broken)

    def test_unknown_playoff_format_fails_closed(self):
        with self.assertRaisesRegex(model.ScheduleOutlookError, "Unknown"):
            compute(13, spec={"PlayoffStartWeek": 14, "PlayoffRoundType": 99, "PlayoffRoundCount": 2})

    def test_2024_actual_one_week_bracket_and_byes(self):
        season_dir = ROOT / "data-source" / "leagues" / "nfl-reise" / "seasons" / "2024"
        league = json.loads((season_dir / "league.json").read_text(encoding="utf-8"))
        winners = json.loads((season_dir / "winners-bracket.json").read_text(encoding="utf-8"))
        rosters = json.loads((season_dir / "rosters.json").read_text(encoding="utf-8"))
        ids = {t["CanonicalLeagueRosterID"] for t in rosters}
        args = dict(structure=league["WeekStructure"], winners_bracket=winners,
                    losers_bracket=[], canonical_roster_ids=ids, regular_season_last_week=14)
        pre = model.compute_playoff_paths(after_week=6, **args)
        self.assertEqual([[15], [16], [17]], pre["Format"]["RoundWeeks"])
        self.assertTrue(all(p["WinnerCanonicalLeagueRosterID"] is None for p in pre["Paths"]))
        week15 = model.compute_playoff_paths(after_week=15, **args)
        round2 = [p for p in week15["Paths"] if p["Round"] == 2 and p["Category"] == "championship"]
        self.assertEqual(2, len(round2))
        self.assertTrue(all(p["ParticipantCertainty"] == "confirmed" for p in round2))
        self.assertEqual(2, sum(bool(x["DirectSeed"]) for g in round2 for x in g["Participants"]))

    def test_2025_actual_two_week_first_leg_does_not_leak(self):
        season_dir = ROOT / "data-source" / "leagues" / "nfl-reise" / "seasons" / "2025"
        league = json.loads((season_dir / "league.json").read_text(encoding="utf-8"))
        winners = json.loads((season_dir / "winners-bracket.json").read_text(encoding="utf-8"))
        losers = json.loads((season_dir / "losers-bracket.json").read_text(encoding="utf-8"))
        rosters = json.loads((season_dir / "rosters.json").read_text(encoding="utf-8"))
        ids = {t["CanonicalLeagueRosterID"] for t in rosters}
        args = dict(structure=league["WeekStructure"], winners_bracket=winners,
                    losers_bracket=losers, canonical_roster_ids=ids, regular_season_last_week=13)
        week14 = model.compute_playoff_paths(after_week=14, **args)
        self.assertTrue(all(p["WinnerCanonicalLeagueRosterID"] is None for p in week14["Paths"]))
        self.assertEqual(1, sum(p["Category"] == "consolation" for p in week14["Paths"]))
        week15 = model.compute_playoff_paths(after_week=15, **args)
        finale = next(p for p in week15["Paths"] if p["Category"] == "championship" and p["Round"] == 2)
        self.assertEqual("confirmed", finale["ParticipantCertainty"])
        self.assertIsNone(finale["WinnerCanonicalLeagueRosterID"])

    def test_2026_current_projected_seeds_stay_unknown(self):
        season_dir = ROOT / "data-source" / "leagues" / "nfl-reise" / "seasons" / "2026"
        league = json.loads((season_dir / "league.json").read_text(encoding="utf-8"))
        winners = json.loads((season_dir / "winners-bracket.json").read_text(encoding="utf-8"))
        losers = json.loads((season_dir / "losers-bracket.json").read_text(encoding="utf-8"))
        rosters = json.loads((season_dir / "rosters.json").read_text(encoding="utf-8"))
        ids = {t["CanonicalLeagueRosterID"] for t in rosters}
        result = model.compute_playoff_paths(
            structure=league["WeekStructure"], winners_bracket=winners,
            losers_bracket=losers, canonical_roster_ids=ids, after_week=10, regular_season_last_week=13)
        self.assertEqual("projected", result["Format"]["FormatEvidence"])
        self.assertTrue(all(p["WinnerCanonicalLeagueRosterID"] is None for p in result["Paths"]))
        self.assertTrue(all(p["ParticipantCertainty"] != "confirmed" for p in result["Paths"]))


if __name__ == "__main__":
    unittest.main()
