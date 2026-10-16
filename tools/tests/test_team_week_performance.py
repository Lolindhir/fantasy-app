from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from team_week_performance import (  # noqa: E402
    build_team_week_performance,
    output_path,
    save_team_week_performance,
)
from weekly_lineup_optimizer import StartingSlot  # noqa: E402


def slot(name: str, *eligible: str) -> StartingSlot:
    return StartingSlot(name, frozenset(eligible))


def ref(player: str) -> dict:
    return {"CanonicalPlayerID": player}


def team(roster_id: str, players: dict[str, float], starters: list[str], week: int = 4,
         official_override: float | None = None) -> dict:
    total = sum(players[item] for item in starters)
    return {
        "CanonicalLeagueRosterID": roster_id,
        "Week": week,
        "Players": [ref(item) for item in players],
        "Starters": [ref(item) for item in starters],
        "PlayerPoints": [{"Player": ref(item), "Points": points} for item, points in players.items()],
        "StarterPoints": [{"Player": ref(item), "Points": players[item]} for item in starters],
        "Points": total if official_override is None else official_override,
    }


def derive(rows: list[dict], positions: dict[str, str], slots: list[StartingSlot] | None = None,
           scoring: dict | None = None, finalized: bool = True,
           expected_team_count: int | None = None) -> dict:
    return build_team_week_performance(
        canonical_league_id="nfl-reise", season=2024, week=4,
        scoring_settings={"rec": 1, "rec_yd": 0.1} if scoring is None else scoring,
        slots=[slot("WR-1", "WR")] if slots is None else slots,
        matchup_rows=rows,
        expected_team_count=len(rows) if expected_team_count is None else expected_team_count,
        position_by_player=positions,
        finalized=finalized, finality_evidence="data-source/nfl/game-finality/2024.json:REG-W4",
    )


class TeamWeekPerformanceTests(unittest.TestCase):
    def test_all_roster_points_and_award_winners(self) -> None:
        rows = [team("rosterA", {"a_start": 8, "a_taxi": 16, "a_ir": 22}, ["a_start"]),
                team("rosterB", {"b_start": 13, "b_bench": 15}, ["b_start"])]
        result = derive(rows, {key: "WR" for row in rows for key in (p["CanonicalPlayerID"] for p in row["Players"])})
        by_id = {x["CanonicalLeagueRosterID"]: x for x in result["Teams"]}
        self.assertEqual(by_id["rosterA"]["PotentialPoints"], 22)
        self.assertEqual(by_id["rosterA"]["EfficiencyPercent"], 36.3636)
        self.assertEqual(by_id["rosterA"]["MissedPoints"], 14)
        self.assertEqual(by_id["rosterA"]["OptimalLineup"][0]["CanonicalPlayerID"], "a_ir")
        self.assertEqual(result["Awards"]["BestManagerRosterIDs"], ["rosterA"])
        self.assertEqual(result["Awards"]["BestCoachRosterIDs"], ["rosterB"])

    def test_2024_special_flex_global_matching(self) -> None:
        roster = team("rosterA", {"rb": 30, "wr": 25, "te": 10}, ["wr", "te"])
        result = derive([roster], {"rb": "RB", "wr": "WR", "te": "TE"},
                        [slot("FLEX-1", "RB", "WR", "TE"), slot("REC_FLEX-1", "WR", "TE")])
        self.assertEqual(result["Teams"][0]["PotentialPoints"], 55)
        self.assertEqual(result["Teams"][0]["EfficiencyPercent"], 63.6364)

    def test_scoring_settings_and_slots_change_identity_fingerprints(self) -> None:
        row = team("rosterA", {"p": 5}, ["p"])
        original = derive([row], {"p": "WR"})
        different_settings = derive([row], {"p": "WR"}, scoring={"rec": 0.5})
        different_slots = derive([row], {"p": "WR"}, slots=[slot("FLEX-1", "RB", "WR", "TE")])
        self.assertNotEqual(original["ScoringProfile"]["SettingsHash"], different_settings["ScoringProfile"]["SettingsHash"])
        self.assertNotEqual(original["LineupDefinitionHash"], different_slots["LineupDefinitionHash"])

    def test_ties_are_shared_and_reordering_does_not_change_contract(self) -> None:
        rows = [team("Z", {"z": 9}, ["z"]), team("A", {"a": 9}, ["a"])]
        positions = {"z": "WR", "a": "WR"}
        result = derive(rows, positions)
        self.assertEqual(result, derive(list(reversed(rows)), positions))
        self.assertEqual(result["Awards"]["BestManagerRosterIDs"], ["A", "Z"])
        self.assertEqual(result["Awards"]["BestCoachRosterIDs"], ["A", "Z"])

    def test_zero_potential_returns_no_efficiency_award(self) -> None:
        data = derive([team("Z", {"z": 0}, ["z"])], {"z": "WR"})
        self.assertIsNone(data["Teams"][0]["EfficiencyPercent"])
        self.assertEqual(data["Awards"]["BestManagerRosterIDs"], [])
        self.assertEqual(data["Awards"]["BestCoachRosterIDs"], [])

    def test_negative_scores_and_commissioner_adjustment_are_separate(self) -> None:
        data = derive([team("Z", {"z": -2}, ["z"], official_override=0)], {"z": "WR"})
        row = data["Teams"][0]
        self.assertEqual(row["PotentialPoints"], 0)
        self.assertEqual(row["ActualStarterPoints"], -2)
        self.assertEqual(row["OfficialMatchupPoints"], 0)
        self.assertIsNone(row["EfficiencyPercent"])

    def test_missing_positions_or_ownership_conflicts_fail_closed(self) -> None:
        a = team("A", {"shared": 2}, ["shared"])
        b = team("B", {"shared": 2}, ["shared"])
        with self.assertRaisesRegex(ValueError, "historical fantasy position"):
            derive([a], {})
        with self.assertRaisesRegex(ValueError, "multiple fantasy teams"):
            derive([a, b], {"shared": "WR"})

    def test_incomplete_score_and_starter_evidence_fail_closed(self) -> None:
        a = team("A", {"a": 2, "b": 3}, ["a"])
        a["PlayerPoints"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete player/point ownership"):
            derive([a], {"a": "WR", "b": "WR"})
        a = team("A", {"a": 2}, ["a"])
        a["StarterPoints"][0]["Points"] = 99
        with self.assertRaisesRegex(ValueError, "Inconsistent starter/player"):
            derive([a], {"a": "WR"})

    def test_unfinalized_week_cannot_be_materialized(self) -> None:
        with self.assertRaisesRegex(ValueError, "Finality evidence required"):
            derive([team("A", {"a": 2}, ["a"])], {"a": "WR"}, finalized=False)

    def test_incomplete_team_week_population_fails_closed(self) -> None:
        rows = [team("A", {"a": 8}, ["a"])]
        with self.assertRaisesRegex(ValueError, "Incomplete weekly fantasy teams"):
            derive(rows, {"a": "WR"}, expected_team_count=2)

    def test_actual_starters_must_fit_historical_lineup_slots(self) -> None:
        rows = [team("A", {"rb": 7, "wr": 6}, ["rb", "wr"])]
        with self.assertRaisesRegex(ValueError, "Historical starters cannot fit lineup slots"):
            derive(rows, {"rb": "RB", "wr": "WR"}, slots=[slot("WR-1", "WR")])
        with self.assertRaisesRegex(ValueError, "Historical starters cannot fit lineup slots"):
            derive([team("A", {"rb": 7}, ["rb"])], {"rb": "RB"}, slots=[slot("WR-1", "WR")])

    def test_multiple_overlapping_slots_accept_actual_starters(self) -> None:
        rows = [team("A", {"rb": 7, "wr": 6}, ["rb", "wr"])]
        data = derive(rows, {"rb": "RB", "wr": "WR"},
                      slots=[slot("FLEX-1", "RB", "WR", "TE"),
                             slot("REC_FLEX-1", "WR", "TE")])
        self.assertEqual(data["Teams"][0]["ActualStarterPoints"], 13)
        self.assertEqual(data["Teams"][0]["PotentialPoints"], 13)
        self.assertEqual(data["Teams"][0]["EfficiencyPercent"], 100)

    def test_output_path_and_semantic_noop_persistence(self) -> None:
        payload = derive([team("A", {"a": 2}, ["a"])], {"a": "WR"})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = output_path(root, payload)
            self.assertEqual(path.relative_to(root).as_posix(), "data-derived/team-week-performance/nfl-reise/2024/04.json")
            self.assertTrue(save_team_week_performance(root, payload))
            before = path.read_bytes()
            self.assertFalse(save_team_week_performance(root, payload))
            self.assertEqual(path.read_bytes(), before)
            updated = dict(payload, FinalityEvidence="changed-finality-evidence")
            self.assertTrue(save_team_week_performance(root, updated))
            self.assertNotEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
