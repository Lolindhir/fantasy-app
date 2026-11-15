"""Weekly player awards of weekly-recap-v2 (Issue #499). The weeks are constructed; no real league, player or points are hard-wired."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib import weekly_recaps as wr  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.weekly_recap import v1, v2  # noqa: E402
from weekly_lineup_optimizer import StartingSlot  # noqa: E402

SLOTS = [
    StartingSlot("QB-1", frozenset({"QB"})),
    StartingSlot("RB-1", frozenset({"RB"})),
    StartingSlot("WR-1", frozenset({"WR"})),
    StartingSlot("FLEX-1", frozenset({"RB", "WR", "TE"})),
]


def p(pid, position, points, starter=True):
    return {"PlayerID": pid, "CanonicalPlayerID": f"c-{pid}", "Position": position, "Points": points, "IsStarter": starter}


def team(team_id, score, *players):
    return {"FantasyTeamID": team_id, "Score": score, "Players": list(players)}


def matchup(matchup_id, first, second):
    return {"FantasyMatchupID": matchup_id, "Teams": [first, second]}


def ids(entries):
    return [entry["PlayerID"] for entry in entries]


class MvpTests(unittest.TestCase):
    def test_mvp_is_the_best_starter_league_wide_and_ignores_the_bench(self) -> None:
        week = [
            matchup("m1", team(1, 50, p("a", "QB", 30), p("b", "RB", 20), p("x", "WR", 99, False)), team(2, 40, p("c", "QB", 25), p("d", "RB", 15))),
            matchup("m2", team(3, 31, p("e", "QB", 31)), team(4, 10, p("f", "QB", 10))),
        ]
        self.assertEqual(["e"], ids(v2.player_awards(week, SLOTS)["MVP"]))

    def test_tied_best_starters_all_receive_the_award(self) -> None:
        week = [matchup("m1", team(1, 30, p("a", "QB", 30)), team(2, 30, p("b", "QB", 30)))]
        self.assertEqual(["a", "b"], ids(v2.player_awards(week, SLOTS)["MVP"]))


class HeroAndHeartbreakerTests(unittest.TestCase):
    def test_hero_needs_a_swing_larger_than_the_margin(self) -> None:
        # Team 1 wins by 5; QB a (30) has no bench QB, swing 30 > 5 -> decisive. RB b (10) has bench RB 8: swing 2, not decisive.
        week = [matchup("m1", team(1, 40, p("a", "QB", 30), p("b", "RB", 10), p("bn", "RB", 8, False)), team(2, 35, p("c", "QB", 35)))]
        awards = v2.player_awards(week, SLOTS)
        self.assertEqual(["a"], ids(awards["MatchupHero"]))
        self.assertEqual(30, awards["MatchupHero"][0]["Swing"])
        self.assertEqual(5, awards["MatchupHero"][0]["Margin"])

    def test_hero_is_absent_when_a_bench_player_covers_every_starter(self) -> None:
        week = [matchup("m1", team(1, 40, p("a", "QB", 30), p("bq", "QB", 29, False)), team(2, 20, p("c", "QB", 20)))]
        self.assertEqual([], v2.player_awards(week, SLOTS)["MatchupHero"])

    def test_hero_is_the_largest_swing_and_only_in_a_win(self) -> None:
        week = [
            matchup("m1", team(1, 60, p("a", "QB", 30), p("b", "RB", 30)), team(2, 10, p("c", "QB", 40))),
            matchup("m2", team(3, 20, p("d", "QB", 20)), team(4, 70, p("e", "QB", 70))),
        ]
        awards = v2.player_awards(week, SLOTS)
        # Team 1 wins by 50: neither a (30) nor b (30) is decisive. Team 4 wins by 50: e (70, no bench) has swing 70 > 50.
        self.assertEqual(["e"], ids(awards["MatchupHero"]))
        self.assertNotIn("d", ids(awards["MatchupHero"]))

    def test_heartbreaker_is_the_best_starter_of_a_lost_matchup_and_may_be_the_mvp(self) -> None:
        week = [matchup("m1", team(1, 40, p("a", "QB", 20)), team(2, 60, p("c", "QB", 50), p("d", "RB", 10)))]
        awards = v2.player_awards(week, SLOTS)
        self.assertEqual(["a"], ids(awards["Heartbreaker"]))
        self.assertEqual(["c"], ids(awards["MVP"]))
        week = [matchup("m1", team(1, 40, p("a", "QB", 60)), team(2, 61, p("c", "QB", 61)))]
        awards = v2.player_awards(week, SLOTS)
        self.assertEqual(["a"], ids(awards["Heartbreaker"]))
        self.assertEqual(["c"], ids(awards["MVP"]))

    def test_a_tied_matchup_has_no_winner_and_no_loser_awards(self) -> None:
        week = [matchup("m1", team(1, 30, p("a", "QB", 30), p("bn", "QB", 90, False)), team(2, 30, p("b", "QB", 30)))]
        awards = v2.player_awards(week, SLOTS)
        for key in ("MatchupHero", "Heartbreaker", "UnsungHero"):
            self.assertEqual([], awards[key])

    def test_tied_heartbreakers_share_the_award(self) -> None:
        week = [matchup("m1", team(1, 40, p("a", "QB", 20), p("b", "RB", 20)), team(2, 60, p("c", "QB", 60)))]
        self.assertEqual(["a", "b"], ids(v2.player_awards(week, SLOTS)["Heartbreaker"]))


class UnsungHeroTests(unittest.TestCase):
    def test_a_bench_player_who_flips_the_matchup_wins_with_the_largest_gain(self) -> None:
        week = [matchup("m1", team(1, 20, p("a", "QB", 20), p("w", "WR", 0), p("bn", "WR", 15, False), p("bs", "WR", 7, False)), team(2, 25, p("c", "QB", 25)))]
        awards = v2.player_awards(week, SLOTS)
        self.assertEqual(["bn"], ids(awards["UnsungHero"]))
        entry = awards["UnsungHero"][0]
        self.assertEqual((15, "w", 5), (entry["Gain"], entry["ReplacedPlayerID"], entry["Margin"]))
        self.assertEqual("w", entry["ReplacedPlayerID"])
        self.assertNotIn("bn", ids(awards["MVP"] + awards["Heartbreaker"] + awards["MatchupHero"]))

    def test_the_swap_must_flip_the_result_strictly(self) -> None:
        week = [matchup("m1", team(1, 20, p("a", "QB", 20), p("w", "WR", 0), p("bn", "WR", 5, False)), team(2, 25, p("c", "QB", 25)))]
        self.assertEqual([], v2.player_awards(week, SLOTS)["UnsungHero"])

    def test_flex_eligibility_is_checked_per_slot_and_the_lineup_must_stay_legal(self) -> None:
        starters = (p("q", "QB", 20), p("r", "RB", 10), p("w", "WR", 10), p("t", "TE", 0))
        opponent = team(2, 25, p("c", "QB", 25))
        # A bench WR may replace the TE: the TE only occupied the FLEX slot, so the WR fits FLEX (or WR) and the lineup stays legal.
        week = [matchup("m1", team(1, 40, *starters, p("bn", "WR", 40, False)), opponent)]
        losing = [matchup("m1", team(1, 20, *starters, p("bn", "WR", 40, False)), opponent)]
        entry = v2.player_awards(losing, SLOTS)["UnsungHero"][0]
        self.assertEqual(("bn", "t"), (entry["PlayerID"], entry["ReplacedPlayerID"]))
        self.assertEqual([], v2.player_awards(week, SLOTS)["UnsungHero"])
        # A bench kicker is eligible for no slot, so no swap with him is legal however many points he scored.
        kicker = [matchup("m1", team(1, 20, *starters, p("k", "K", 40, False)), opponent)]
        self.assertEqual([], v2.player_awards(kicker, SLOTS)["UnsungHero"])

    def test_a_bench_player_may_fill_an_empty_slot(self) -> None:
        week = [matchup("m1", team(1, 20, p("a", "QB", 20), p("bn", "RB", 12, False)), team(2, 25, p("c", "QB", 25)))]
        awards = v2.player_awards(week, SLOTS)
        self.assertEqual(["bn"], ids(awards["UnsungHero"]))
        self.assertIsNone(awards["UnsungHero"][0]["ReplacedPlayerID"])

    def test_only_losing_teams_have_an_unsung_hero(self) -> None:
        week = [matchup("m1", team(1, 50, p("a", "QB", 50), p("bn", "RB", 90, False)), team(2, 25, p("c", "QB", 25)))]
        self.assertEqual([], v2.player_awards(week, SLOTS)["UnsungHero"])


class EvidenceTests(unittest.TestCase):
    def test_missing_points_or_position_raise_and_unavailable_marks_the_week(self) -> None:
        week = [matchup("m1", team(1, 20, p("a", "QB", 20), p("bn", "RB", None, False)), team(2, 25, p("c", "QB", 25)))]
        with self.assertRaises(ValueError):
            v2.player_awards(week, SLOTS)
        week = [matchup("m1", team(1, 20, p("a", "", 20)), team(2, 25, p("c", "QB", 25)))]
        with self.assertRaises(ValueError):
            v2.player_awards(week, SLOTS)
        self.assertEqual({"State": "unavailable", "MVP": [], "MatchupHero": [], "Heartbreaker": [], "UnsungHero": []}, v2.unavailable())

    def test_a_player_holds_at_most_two_awards_in_a_week(self) -> None:
        week = [
            matchup("m1", team(1, 60, p("a", "QB", 50), p("b", "RB", 10), p("bn", "RB", 8, False)), team(2, 30, p("c", "QB", 30))),
            matchup("m2", team(3, 20, p("d", "QB", 20), p("e", "RB", 0), p("bm", "RB", 30, False)), team(4, 40, p("f", "QB", 40))),
        ]
        awards = v2.player_awards(week, SLOTS)
        counts: dict[str, int] = {}
        for key in v2.AWARD_KEYS:
            for entry in awards[key]:
                counts[entry["PlayerID"]] = counts.get(entry["PlayerID"], 0) + 1
        self.assertTrue(all(count <= 2 for count in counts.values()))


class ModelTests(unittest.TestCase):
    def test_v1_is_the_baseline_without_awards_and_both_are_registered(self) -> None:
        self.assertFalse(v1.PLAYER_AWARDS)
        self.assertTrue(v2.PLAYER_AWARDS)
        self.assertIs(v1, registry.get_model("weekly-recap-v1", "weekly-recap"))
        self.assertIs(v2, registry.get_model("weekly-recap-v2", "weekly-recap"))
        self.assertFalse(hasattr(v1, "player_awards"))


class HistoryTests(unittest.TestCase):
    @staticmethod
    def refs(player_id, season):
        return {"CanonicalPlayerID": f"c-{player_id}", "Name": f"Player {player_id}", "Position": "QB", "Picture": None}

    def test_counts_week_lists_and_unavailable_weeks(self) -> None:
        def entry(pid, **extra):
            return {"PlayerID": pid, "CanonicalPlayerID": f"c-{pid}", "Position": "QB", "FantasyTeamID": 1, "FantasyMatchupID": "m", "Points": 10, **extra}

        def awards(**kwargs):
            return {"State": "available", "MVP": [], "MatchupHero": [], "Heartbreaker": [], "UnsungHero": [], **kwargs}

        models = {
            2024: {"Weeks": [{"Week": 1, "PlayerAwards": awards(MVP=[entry("a")], Heartbreaker=[entry("a")])}, {"Week": 2, "PlayerAwards": awards(MVP=[entry("b")])}]},
            2025: {"Weeks": [{"Week": 1, "PlayerAwards": {"State": "unavailable", "MVP": [], "MatchupHero": [], "Heartbreaker": [], "UnsungHero": []}},
                             {"Week": 2, "PlayerAwards": awards(MVP=[entry("a")], UnsungHero=[entry("c", Gain=5)])}]},
            2026: {"Weeks": [{"Week": 1}]},
        }
        history = wr.player_award_history(models, self.refs)
        self.assertEqual([{"Season": 2024, "Weeks": [1, 2]}, {"Season": 2025, "Weeks": [2]}], history["Seasons"])
        by_id = {item["PlayerID"]: item for item in history["Players"]}
        self.assertEqual({"MVP": 2, "MatchupHero": 0, "Heartbreaker": 1, "UnsungHero": 0}, by_id["a"]["Counts"])
        self.assertEqual(3, by_id["a"]["Total"])
        self.assertEqual("a", history["Players"][0]["PlayerID"])
        self.assertEqual([(2024, 1, "MVP"), (2024, 1, "Heartbreaker"), (2025, 2, "MVP")], [(e["Season"], e["Week"], e["Award"]) for e in by_id["a"]["Entries"]])
        self.assertEqual(5, by_id["c"]["Entries"][0]["Gain"])
        self.assertNotIn("PlayerID", by_id["c"]["Entries"][0])

    def test_leaders_share_ties_and_skip_unwon_awards(self) -> None:
        def entry(pid):
            return {"PlayerID": pid, "CanonicalPlayerID": f"c-{pid}", "Position": "QB", "FantasyTeamID": 1, "FantasyMatchupID": "m", "Points": 10}

        def awards(**kwargs):
            return {"State": "available", "MVP": [], "MatchupHero": [], "Heartbreaker": [], "UnsungHero": [], **kwargs}

        models = {2024: {"Weeks": [
            {"Week": 1, "PlayerAwards": awards(MVP=[entry("a")], Heartbreaker=[entry("b")])},
            {"Week": 2, "PlayerAwards": awards(MVP=[entry("a")], Heartbreaker=[entry("c")])},
            {"Week": 3, "PlayerAwards": awards(MVP=[entry("b")], Heartbreaker=[entry("b")])},
        ]}}
        leaders = wr.player_award_history(models, self.refs)["Leaders"]
        self.assertEqual([("a", 2)], [(p["PlayerID"], p["Count"]) for p in leaders["MVP"]])
        self.assertEqual([("b", 2)], [(p["PlayerID"], p["Count"]) for p in leaders["Heartbreaker"]])
        self.assertEqual([], leaders["MatchupHero"])
        self.assertEqual([], leaders["UnsungHero"])
        tie = wr.player_award_history({2024: {"Weeks": [{"Week": 1, "PlayerAwards": awards(MVP=[entry("a"), entry("b")])}]}}, self.refs)["Leaders"]
        self.assertEqual(["a", "b"], [p["PlayerID"] for p in tie["MVP"]])


if __name__ == "__main__":
    unittest.main()
