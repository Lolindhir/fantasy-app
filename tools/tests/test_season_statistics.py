"""season-stats-v1 and the season-statistics product (Issue #506). Synthetic weeks for the model; invariants on persisted state for the product."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.season_stats import v1  # noqa: E402
from derived_data_lib.models.team_range import v1 as team_range  # noqa: E402
from derived_data_lib.models.win_prob import v1 as win_prob  # noqa: E402
from derived_data_lib import season_statistics as ss  # noqa: E402
from derived_data_lib import weekly_recaps as wr  # noqa: E402
from season_statistics_app_publish import with_team_abbreviations  # noqa: E402
from derived_data_lib.league_teams import team_abbreviation  # noqa: E402

REPO = TOOLS.parent


def game(a, pa, b, pb, chance=None, proj_a=None, proj_b=None):
    return {"Teams": [{"TeamID": a, "Points": pa, "PregameProjection": proj_a}, {"TeamID": b, "Points": pb, "PregameProjection": proj_b}], "WinProbability": chance}


def bb_game(a, b, **values):
    """Game with best-ball inputs: values keyed like ``bb_a``, ``bb_b``, ``eff_a``, ``eff_b``, ``pa``, ``pb``."""
    return {"Teams": [
        {"TeamID": a, "Points": 100, "PregameProjection": values.get("pa"), "ProjectedBestBallPoints": values.get("bb_a"), "LineupEfficiencyActual": values.get("eff_a")},
        {"TeamID": b, "Points": 90, "PregameProjection": values.get("pb"), "ProjectedBestBallPoints": values.get("bb_b"), "LineupEfficiencyActual": values.get("eff_b")},
    ], "WinProbability": None}


def week(number, *games):
    return {"Week": number, "Games": list(games)}


def team(result, team_id):
    return next(t for t in result["Teams"] if t["TeamID"] == team_id)


class BestBallTests(unittest.TestCase):
    def test_efficiencies_means_and_strength(self) -> None:
        weeks = [week(1, bb_game(1, 2, pa=90, bb_a=100, eff_a=80, pb=50, bb_b=100, eff_b=70)),
                 week(2, bb_game(1, 2, pa=80, bb_a=100, eff_a=82, pb=60, bb_b=None, eff_b=None))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertEqual([90.0, 80.0], [g["LineupEfficiencyProjected"] for g in one["GameLog"]])
        self.assertEqual(85.0, one["LineupEfficiencyProjected"])
        self.assertEqual(81.0, one["LineupEfficiencyActual"])
        self.assertEqual(100.0, one["ProjectedBestBallPoints"])
        self.assertEqual(85.0, one["ProjectedBestBallStrength"])
        # unknown best ball (week 2) stays unknown, never zero
        self.assertEqual(1, two["BestBallGames"])
        self.assertIsNone(two["GameLog"][1]["LineupEfficiencyProjected"])
        self.assertIsNone(two["GameLog"][1]["LineupEfficiencyActual"])

    def test_no_best_ball_gives_null_values(self) -> None:
        result = v1.compute([1, 2], [week(1, bb_game(1, 2))])
        self.assertIsNone(team(result, 1)["ProjectedBestBallStrength"])
        self.assertEqual(0, team(result, 1)["BestBallGames"])


class ProjectedBestBallTests(unittest.TestCase):
    PLAYERS = [
        {"PlayerID": "a", "IsStarter": True}, {"PlayerID": "b", "IsStarter": False},
        {"PlayerID": "c", "IsStarter": False}, {"PlayerID": "d", "IsStarter": False},
    ]
    IDENTITY = {"ByPlayer": {k: {"CanonicalPlayerID": k.upper(), "Position": p} for k, p in
                             {"a": "QB", "b": "RB", "c": "RB", "d": "WR"}.items()}, "ByCanonical": {}}

    @staticmethod
    def proj(points):
        return {"Status": "available", "Points": points, "PredictionRanges": [{"Level": 0.9, "Lower": points - 5, "Upper": points + 5}]}

    def slots(self):
        from weekly_lineup_optimizer import StartingSlot
        return [StartingSlot("QB1", frozenset({"QB"})), StartingSlot("RB1", frozenset({"RB"})),
                StartingSlot("FLEX1", frozenset({"RB", "WR"}))]

    def test_flex_takes_the_best_remaining_player(self) -> None:
        projections = {"A": self.proj(20), "B": self.proj(10), "C": self.proj(12), "D": self.proj(8)}
        points, excluded = ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots())
        self.assertEqual((42.0, 0), (points, excluded))  # QB 20 + RB 12 + FLEX RB 10

    def test_bench_player_without_projection_is_excluded_and_counted(self) -> None:
        projections = {"A": self.proj(20), "B": self.proj(10), "C": {"Status": "insufficient-history"}, "D": self.proj(8)}
        points, excluded = ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots())
        self.assertEqual((38.0, 1), (points, excluded))  # QB 20 + RB 10 + FLEX WR 8

    def test_starter_without_projection_makes_it_unknown(self) -> None:
        projections = {"B": self.proj(10), "C": self.proj(12), "D": self.proj(8)}
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, self.IDENTITY, projections, team_range, self.slots()))

    def test_missing_identity_or_slots_is_unknown(self) -> None:
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, None, {}, team_range, self.slots()))
        self.assertEqual((None, 0), ss.projected_best_ball(self.PLAYERS, self.IDENTITY, {}, team_range, []))


class AllPlayTests(unittest.TestCase):
    def test_expected_wins_luck_and_all_play_record(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90), game(3, 80, 4, 120)), week(2, game(1, 70, 3, 70), game(2, 60, 4, 50))]
        result = v1.compute([1, 2, 3, 4], weeks)
        # week 1 shares: 4->3/3, 1->2/3, 2->1/3, 3->0 ; week 2: 1 and 3 tie on top (2.5/3... below both 2 teams) -> (2+0.5)/3
        one = team(result, 1)
        self.assertAlmostEqual(2 / 3 + 2.5 / 3, one["ExpectedWins"], places=4)
        self.assertEqual((1, 1), (one["Wins"], one["Ties"]))
        self.assertAlmostEqual(1.5 - one["ExpectedWins"], one["Luck"], places=4)
        self.assertEqual({"Wins": 4, "Losses": 1, "Ties": 1}, one["AllPlay"])

    def test_expected_wins_sum_equals_games_times_half_the_league(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90), game(3, 80, 4, 120)), week(2, game(1, 70, 3, 75), game(2, 60, 4, 50))]
        result = v1.compute([1, 2, 3, 4], weeks)
        self.assertAlmostEqual(2 * 4 / 2, sum(t["ExpectedWins"] for t in result["Teams"]), places=3)
        self.assertAlmostEqual(0.0, sum(t["Luck"] for t in result["Teams"]), places=3)

    def test_progression_has_one_entry_per_week_and_ends_at_the_final_values(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90)), week(2, game(1, 70, 2, 75))]
        result = v1.compute([1, 2], weeks)
        self.assertEqual([1, 2], [w["Week"] for w in result["Weeks"]])
        last = next(t for t in result["Weeks"][-1]["Teams"] if t["TeamID"] == 1)
        self.assertEqual(team(result, 1)["ExpectedWins"], last["ExpectedWins"])
        self.assertEqual(team(result, 1)["Luck"], last["Luck"])

    def test_no_played_week_gives_unknown_values_not_zero(self) -> None:
        result = v1.compute([1, 2], [])
        self.assertIsNone(team(result, 1)["ExpectedWins"])
        self.assertIsNone(team(result, 1)["Luck"])
        self.assertIsNone(result["BiggestUpset"])


class PointFiguresTests(unittest.TestCase):
    def test_point_figures_are_plain_arithmetic_on_the_totals(self) -> None:
        figures = ss._point_figures({"Games": 3, "Points": 850.0, "PointsAgainst": 790.0}, v1.DIGITS)
        self.assertEqual(figures["PointDifferential"], 60.0)
        self.assertAlmostEqual(figures["PointsPerGame"], 283.3333, places=4)
        self.assertAlmostEqual(figures["PointsAgainstPerGame"], 263.3333, places=4)

    def test_no_game_gives_null_never_zero(self) -> None:
        figures = ss._point_figures({"Games": 0, "Points": 0, "PointsAgainst": 0}, v1.DIGITS)
        self.assertEqual(set(figures.values()), {None})

    def test_negative_zero_is_normalized(self) -> None:
        figures = ss._point_figures({"Games": 2, "Points": 10.0, "PointsAgainst": 10.0}, v1.DIGITS)
        self.assertEqual(str(figures["PointDifferential"]), "0.0")

    def test_persisted_products_carry_consistent_point_figures(self) -> None:
        for path in (REPO / "data-derived" / "season-statistics").glob("*/*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("SchemaVersion", 1) < 2:
                continue  # older files are replaced by the next full materialization
            for item in doc["Teams"]:
                self.assertEqual({k: item[k] for k in ("PointDifferential", "PointsPerGame", "PointsAgainstPerGame")},
                                 ss._point_figures(item, v1.DIGITS), path.name)


class StrengthAndTimingTests(unittest.TestCase):
    def test_strength_schedule_burden_and_timing(self) -> None:
        weeks = [week(1, game(1, 120, 2, 80)), week(2, game(1, 100, 2, 100))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertAlmostEqual(110 / 100, one["RelativeScoringStrength"], places=4)
        self.assertAlmostEqual(0.9, one["StrengthOfSchedule"], places=4)  # opponent strength 90/100
        self.assertAlmostEqual(1.1, two["StrengthOfSchedule"], places=4)
        self.assertAlmostEqual(90 / 100, one["PointsAgainstBurden"], places=4)
        self.assertAlmostEqual((80 - 90 + 100 - 90) / 2, one["OpponentTiming"], places=4)
        self.assertEqual(1, two["AboveAverageOpponents"])

    def test_brick_wall_base_counts_wins_against_above_average_opponents(self) -> None:
        weeks = [week(1, game(1, 120, 2, 80)), week(2, game(1, 60, 2, 100))]
        result = v1.compute([1, 2], weeks)
        # team 2 average 90: team 1 scored 120 (above) in week 1 and 60 (below) in week 2 against team 2's average 90 -> only week 1 counts for team 2
        two = team(result, 2)
        self.assertEqual(1, two["AboveAverageOpponents"])
        self.assertEqual(0, two["AboveAverageOpponentWins"])
        one = team(result, 1)
        self.assertEqual(1, one["AboveAverageOpponents"])  # team 2 scored 100 > 90 in week 2 ... average of team 2 is 90
        self.assertEqual(0, one["AboveAverageOpponentWins"])


class ProjectionTests(unittest.TestCase):
    def test_projection_delta_uses_only_games_with_a_projection(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, proj_a=90, proj_b=None)), week(2, game(1, 80, 2, 70, proj_a=100, proj_b=60))]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertAlmostEqual((10 - 20) / 2, one["ProjectionDelta"], places=4)
        self.assertEqual(2, one["ProjectionGames"])
        self.assertEqual(1, two["ProjectionGames"])
        self.assertIsNone(two["GameLog"][0]["ProjectionDelta"])

    def test_no_projection_at_all_is_none(self) -> None:
        result = v1.compute([1, 2], [week(1, game(1, 100, 2, 90))])
        self.assertIsNone(team(result, 1)["ProjectionDelta"])
        self.assertEqual(0, team(result, 1)["ProjectionGames"])


class UpsetTests(unittest.TestCase):
    def test_thresholds_underdog_and_upset_counts(self) -> None:
        weeks = [
            week(1, game(1, 100, 2, 90, chance=0.30)),   # team 1 wins with 30 percent: upset
            week(2, game(1, 100, 2, 90, chance=0.45)),   # team 1 wins with 45 percent: underdog win, no upset
            week(3, game(1, 100, 2, 90, chance=0.60)),   # favorite wins
            week(4, game(1, 80, 2, 90, chance=0.70)),    # team 1 loses as favorite, team 2 won with 30 percent
            week(5, game(1, 80, 2, 90, chance=None)),    # unknown chance counts nowhere
        ]
        result = v1.compute([1, 2], weeks)
        one, two = team(result, 1), team(result, 2)
        self.assertEqual((2, 1, 1, 1, 4), (one["UnderdogWins"], one["UpsetWins"], one["FavoriteLosses"], one["UpsetLosses"], one["KnownChanceGames"]))
        self.assertEqual((1, 1, 2, 1), (two["UnderdogWins"], two["UpsetWins"], two["FavoriteLosses"], two["UpsetLosses"]))

    def test_boundaries_are_strict(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, chance=v1.UPSET_THRESHOLD)), week(2, game(1, 100, 2, 90, chance=v1.UNDERDOG_THRESHOLD))]
        one = team(v1.compute([1, 2], weeks), 1)
        self.assertEqual((1, 0), (one["UnderdogWins"], one["UpsetWins"]))

    def test_biggest_upset_lowest_chance_and_none_without_upset(self) -> None:
        weeks = [week(1, game(1, 100, 2, 90, chance=0.30)), week(2, game(1, 80, 2, 90, chance=0.90)), week(3, game(1, 100, 2, 90, chance=0.34))]
        upset = v1.compute([1, 2], weeks)["BiggestUpset"]
        self.assertEqual((2, 2, 0.1), (upset["Week"], upset["WinnerTeamID"], upset["WinnerPregameWinProbability"]))
        self.assertIsNone(v1.compute([1, 2], [week(1, game(1, 100, 2, 90, chance=0.50))])["BiggestUpset"])

    def test_tie_in_points_is_no_upset_and_equal_chances_pick_the_earlier_week(self) -> None:
        self.assertIsNone(v1.compute([1, 2], [week(1, game(1, 100, 2, 100, chance=0.2))])["BiggestUpset"])
        weeks = [week(1, game(1, 100, 2, 90, chance=0.2)), week(2, game(1, 100, 2, 90, chance=0.2))]
        self.assertEqual(1, v1.compute([1, 2], weeks)["BiggestUpset"]["Week"])


class WeekGamesTests(unittest.TestCase):
    def test_chance_comes_from_the_team_range_and_win_prob_models_and_is_unknown_without_projection(self) -> None:
        z = team_range.z_for_level(0.9)

        def projection(points, sigma):
            return {"Status": "available", "Points": points, "PredictionRanges": [{"Level": 0.9, "Lower": points - sigma * z, "Upper": points + sigma * z}]}

        def side(team_id, player, score):
            return {"FantasyTeamID": team_id, "FinalScore": score, "Players": [{"PlayerID": player, "IsStarter": True, "CanonicalPlayerID": f"c-{player}"}]}

        facts = [{"FantasyMatchupID": "m1", "Teams": [side("1", "p1", 100.0), side("2", "p2", 90.0)]}]
        games = ss.week_games(facts, None, {"c-p1": projection(120, 10), "c-p2": projection(100, 10)}, team_range, win_prob)
        expected = win_prob.win_probability(120, 10, 100, 10)
        self.assertAlmostEqual(expected, games[0]["WinProbability"], places=9)
        self.assertEqual([120.0, 100.0], [t["PregameProjection"] for t in games[0]["Teams"]])
        missing = ss.week_games(facts, None, {"c-p1": projection(120, 10)}, team_range, win_prob)
        self.assertIsNone(missing[0]["WinProbability"])
        self.assertIsNone(missing[0]["Teams"][1]["PregameProjection"])


    def test_historical_recap_and_statistics_legacy_projection_parity(self) -> None:
        z = team_range.z_for_level(0.9)

        def projection(points, sigma):
            return {"Status": "available", "Points": points,
                    "PredictionRanges": [{"Level": 0.9, "Lower": points - sigma * z,
                                          "Upper": points + sigma * z}]}

        facts = [{"FantasyMatchupID": "m", "Teams": [
            {"FantasyTeamID": "1", "FinalScore": 90, "Players": [
                {"PlayerID": " p1 ", "CanonicalPlayerID": " c1 ", "IsStarter": True},
                {"PlayerID": "bench", "IsStarter": False},
            ]},
            {"FantasyTeamID": "2", "FinalScore": 100, "Players": [
                {"PlayerID": "p2", "CanonicalPlayerID": "", "IsStarter": True},
            ]},
        ]}]
        identity = {"ByPlayer": {
            "p1": {"CanonicalPlayerID": "wrong"},
            "p2": {"CanonicalPlayerID": " c2 "},
        }, "ByCanonical": {}}
        team_values = {"1": 1, "2": 2}
        cases = [
            ({"c1": projection(120, 10), "c2": projection(100, 10)}, 120.0, 100.0,
             win_prob.win_probability(120, 10, 100, 10)),
            ({"c1": projection(-5, 0), "c2": projection(-5, 0)}, -5.0, -5.0, 0.5),
            ({"c1": projection(0, 0), "c2": projection(-5, 0)}, 0.0, -5.0, 1.0),
            ({"c1": projection(100, 10)}, 100.0, None, None),
            ({"c1": projection(100, 10), "c2": {"Status": "insufficient-history"}}, 100.0, None, None),
            ({}, None, None, None),
        ]
        for projections, a, b, raw in cases:
            with self.subTest(projections=projections):
                # The identity embedded in the matchup takes precedence over
                # conflicting fallback evidence, and unknown bench players do not count.
                projections = {**projections, "wrong": projection(999, 0)}
                stats = ss.week_games(facts, identity, projections, team_range, win_prob)[0]
                recap = wr.pregame_win_probabilities(
                    facts, team_values, identity, projections, team_range, win_prob,
                )[0]
                self.assertEqual([a, b], [t["PregameProjection"] for t in stats["Teams"]])
                self.assertEqual(raw, stats["WinProbability"])
                pair = win_prob.percent_pair(raw)
                self.assertEqual(list(pair) if pair else [None, None],
                                 [t["PregameWinProbability"] for t in recap["Teams"]])
                winner_probability = 1.0 - raw if raw is not None else None
                self.assertEqual(win_prob.is_upset(winner_probability), recap["Upset"])
                self.assertEqual(win_prob.upset_level(winner_probability), recap["UpsetLevel"])

class TeamAbbreviationTests(unittest.TestCase):
    """Issue #1621: the season-specific abbreviation follows the rule of League.json TeamAbbr (tools/derived_data_lib/league_teams.py team_abbreviation)."""

    def test_rule_by_word_count_and_stop_words(self) -> None:
        self.assertEqual(team_abbreviation("Mighty Giants", 1), "MiG")
        self.assertEqual(team_abbreviation("Ruhr Valley Packers", 2), "RVP")
        self.assertEqual(team_abbreviation("Just Bill", 3), "JuB")
        self.assertEqual(team_abbreviation("Team DennisLACards", 5), "DLC")
        self.assertEqual(team_abbreviation("Team TimpaBay", 6), "TiB")
        self.assertEqual(team_abbreviation("Cowboys", 7), "Cow")

    def test_missing_name_falls_back_to_the_team_id(self) -> None:
        self.assertEqual(team_abbreviation(None, 4), "T04")
        self.assertEqual(team_abbreviation("  ", "x"), "TBD")
        self.assertEqual(team_abbreviation("Team", 9), "T09")

    def test_app_rows_get_the_abbreviation_of_their_season_name(self) -> None:
        document = {"Season": 2024, "Teams": [{"TeamID": 2, "TeamName": "ND - Fighting Childish"}]}
        self.assertEqual(with_team_abbreviations(document)["Teams"][0]["TeamAbbr"], "NFC")
        self.assertNotIn("TeamAbbr", document["Teams"][0])


class RegistryTests(unittest.TestCase):
    def test_model_is_registered_with_its_kind(self) -> None:
        self.assertIs(v1, registry.get_model("season-stats-v1", "season-stats"))
        self.assertEqual(0.35, v1.PARAMS["UpsetThreshold"])


class PersistedProductTests(unittest.TestCase):
    """Invariants of the persisted documents; no player, team or value is hard-wired."""

    def documents(self):
        root = REPO / "data-derived" / "season-statistics"
        files = sorted(root.glob("*/*.json"))
        self.assertTrue(files, "no persisted season-statistics document")
        return [json.loads(path.read_text(encoding="utf-8")) for path in files]

    def test_documents_are_consistent(self) -> None:
        for doc in self.documents():
            self.assertEqual("season-statistics", doc["Product"])
            teams = doc["Teams"]
            completed = doc["AsOf"]["CompletedWeeks"]
            self.assertEqual(completed, len(doc["Weeks"]))
            if completed:
                self.assertAlmostEqual(completed * len(teams) / 2, sum(t["ExpectedWins"] for t in teams), delta=0.01 * len(teams))
                self.assertAlmostEqual(0.0, sum(t["Luck"] for t in teams), delta=0.01 * len(teams))
            for entry in teams:
                self.assertEqual(entry["Games"], len(entry["GameLog"]))
                self.assertEqual(entry["Wins"] + entry["Losses"] + entry["Ties"], entry["Games"])
                self.assertLessEqual(entry["UpsetWins"], entry["UnderdogWins"])
            upset = doc["BiggestUpset"]
            if upset is not None:
                self.assertLess(upset["WinnerPregameWinProbability"], doc["Thresholds"]["UpsetWinProbability"])

    def test_materialization_is_a_noop_on_unchanged_inputs(self) -> None:
        import derived_data

        out_root = REPO / "data-derived"
        for league in sorted({p.parent.name for p in (out_root / "season-statistics").glob("*/*.json")}):
            summary = derived_data.materialize_season_statistics(REPO, out_root, league, None, True)
            self.assertEqual([], [s["Season"] for s in summary["Seasons"] if s.get("WouldWrite")])



def reference_biggest_upset(documents):
    """Frozen pre-ADR-100 selection, retained only for migration regression tests."""
    candidates = [{"Season": year, **doc["BiggestUpset"]} for year, doc in documents.items()
                  if doc["BiggestUpset"] is not None]
    return min(candidates, key=lambda x: (x["WinnerPregameWinProbability"], x["Season"], x["Week"]),
               default=None)


class LeagueRecordsFoundationTests(unittest.TestCase):
    def source(self, year, chance=None, week=3):
        return {
            "Product": "season-statistics", "SchemaVersion": 2,
            "CanonicalLeagueID": "league-test", "Season": year,
            "Models": {"SeasonStats": "season-stats-v1", "WinProb": "win-prob-v1"},
            "Thresholds": {"UpsetWinProbability": 0.35},
            "AsOf": {"LeagueScoredWeek": 4, "CompletedWeeks": 4},
            "RegularSeasonGames": 14,
            "Teams": [{"TeamID": i, "CanonicalLeagueRosterID": f"league-test-{year}-{i}",
                       "KnownChanceGames": 4} for i in (1, 2)],
            "BiggestUpset": None if chance is None else {
                "Week": week, "WinnerTeamID": 1, "LoserTeamID": 2,
                "WinnerPoints": 100.0, "LoserPoints": 90.0,
                "WinnerPregameWinProbability": chance,
            },
        }

    def test_ties_and_identity_and_null(self):
        from derived_data_lib.league_records import build, legacy_biggest_upset
        docs = {2025: self.source(2025, 0.1, 1), 2024: self.source(2024, 0.1, 3)}
        result = build("league-test", [2025, 2024], docs)
        self.assertEqual(2024, legacy_biggest_upset(result)["Season"])
        self.assertEqual("league-test-2024-1", result["Records"]["BiggestUpset"]["WinnerCanonicalLeagueRosterID"])
        self.assertEqual(result, build("league-test", [2024, 2025], dict(reversed(list(docs.items())))))
        self.assertIsNone(legacy_biggest_upset(build("league-test", [2024], {2024: self.source(2024)})))

    def test_rejects_missing_season_and_wrong_identity_and_incomplete_weeks(self):
        from derived_data_lib.league_records import build
        doc = self.source(2024, 0.1)
        with self.assertRaises(ValueError):
            build("league-test", [2024, 2025], {2024: doc})
        with self.assertRaises(ValueError):
            build("wrong-league", [2024], {2024: doc})
        doc["AsOf"]["CompletedWeeks"] = 3
        with self.assertRaises(ValueError):
            build("league-test", [2024], {2024: doc})

    def test_materializer_noop_and_legacy_parity(self):
        import tempfile
        from league_records_materialize import materialize
        from derived_data_lib.league_records import legacy_biggest_upset
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            source = output / "season-statistics" / "league-test"
            source.mkdir(parents=True)
            docs = {2024: self.source(2024, 0.2), 2025: self.source(2025, 0.1)}
            for year, doc in docs.items():
                (source / f"{year}.json").write_text(json.dumps(doc), encoding="utf-8")
            from unittest.mock import patch
            lineage = {"CanonicalLeagueID": "league-test", "CurrentCanonicalLeagueSeasonID": "league-test-2025",
                       "Seasons": [{"Season": year} for year in docs]}
            with patch("league_records_materialize.manifest", return_value=lineage):
                preview = materialize(REPO, output, "league-test")
                path = output / "league-records" / "league-test.json"
                self.assertFalse(path.exists())
                self.assertEqual(1, preview["WouldWrite"])
                first = materialize(REPO, output, "league-test", write=True)
                self.assertEqual(1, first["Written"])
                before = path.read_bytes()
                self.assertEqual(0, materialize(REPO, output, "league-test", write=True)["Written"])
                self.assertEqual(before, path.read_bytes())
                self.assertEqual(reference_biggest_upset(docs), legacy_biggest_upset(first["Document"]))
                (source / "2024.json").unlink()
                with self.assertRaises(OSError):
                    materialize(REPO, output, "league-test", write=True)
                self.assertEqual(before, path.read_bytes())

    def test_delivery_and_compatibility_field_read_same_persisted_record(self):
        import tempfile
        from datetime import datetime, timezone
        from unittest.mock import patch
        from app_delivery import Writer
        from derived_data_lib.league_records import build, legacy_biggest_upset
        from league_records_app_publish import publish as publish_records
        from season_statistics_app_publish import publish as publish_stats
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "data-derived"
            source = output / "season-statistics" / "league-test"
            source.mkdir(parents=True)
            docs = {2024: self.source(2024, 0.1), 2025: self.source(2025, 0.2)}
            for year, doc in docs.items():
                (source / f"{year}.json").write_text(json.dumps(doc), encoding="utf-8")
            product = build("league-test", list(docs), docs)
            folder = output / "league-records"
            folder.mkdir()
            path = folder / "league-test.json"
            path.write_text(json.dumps(product), encoding="utf-8")
            lineage = {"CurrentCanonicalLeagueSeasonID": "league-test-2025"}
            with patch("season_statistics_app_publish.manifest", return_value=lineage):
                first = Writer(root, datetime(2026, 1, 1, tzinfo=timezone.utc))
                publish_records(root, "league-test", first)
                publish_stats(root, "league-test", "current", first)
                first.finish()
                records = json.loads((first.data / "LeagueRecords.json").read_text())
                statistics = json.loads((first.data / "SeasonStatistics.json").read_text())
                self.assertEqual(product, records)
                self.assertEqual(legacy_biggest_upset(product), statistics["BiggestUpsetAllTime"])
                second = Writer(root, datetime(2026, 1, 2, tzinfo=timezone.utc))
                publish_records(root, "league-test", second)
                publish_stats(root, "league-test", "current", second)
                self.assertEqual([], second.finish())
                path.unlink()
                with self.assertRaises(OSError):
                    publish_records(root, "league-test", second)
                publish_stats(root, "league-test", "current", second)
                statistics = json.loads((second.data / "SeasonStatistics.json").read_text())
                self.assertEqual(legacy_biggest_upset(product), statistics["BiggestUpsetAllTime"])
                self.assertEqual([], second.finish())

    def test_persisted_inputs_match_existing_selection(self):
        from derived_data_lib.league_records import legacy_biggest_upset
        from league_records_materialize import resolve
        from season_statistics_app_publish import persisted_documents
        output = REPO / "data-derived"
        for league in sorted(p.name for p in (output / "season-statistics").iterdir() if p.is_dir()):
            self.assertEqual(reference_biggest_upset(persisted_documents(output, league)),
                             legacy_biggest_upset(resolve(REPO, output, league)))

if __name__ == "__main__":
    unittest.main()
