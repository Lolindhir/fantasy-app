from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib import matchup_projection  # noqa: E402
from derived_data_lib.models.team_range import v1 as team_range_v1  # noqa: E402
from derived_data_lib.matchup_projection import (  # noqa: E402
    AXIS_PADDING,
    METHOD_ID,
    build_matchup_projections,
    player_sigma,
    compute_matchup_projections,
    team_ranges,
    z_for_level,
)

Z90 = z_for_level(0.9)


def projection(points: float, sigma: float = 10.0, status: str = "available") -> dict:
    if status != "available":
        return {"Status": status, "Points": None, "PredictionRange": None, "PredictionRanges": []}
    half = Z90 * sigma
    primary = {"Level": 0.9, "Lower": points - half, "Upper": points + half}
    return {
        "Status": "available",
        "Points": points,
        "PredictionRange": primary,
        "PredictionRanges": [primary],
    }


def player_model(**records: dict) -> dict:
    return {
        "Season": 2026,
        "Week": 3,
        "CanonicalLeagueID": "league-a",
        "Records": [
            {"PlayerID": player_id, "CanonicalPlayerID": f"NFLP-{player_id}", "Projection": value}
            for player_id, value in records.items()
        ],
    }


def default_model() -> dict:
    return player_model(
        p1=projection(10.0, 10.0),
        p2=projection(99.0, 10.0),
        p3=projection(20.0, 10.0),
        p4=projection(5.0, 5.0),
    )


def default_context() -> dict:
    def team(team_id, players):
        return {"FantasyTeamID": team_id, "FantasyMatchupID": "m1", "Players": players}

    return {
        "Season": "2026",
        "Week": 3,
        "Games": [
            {
                "GameID": "g1",
                "Status": "Scheduled",
                "FantasyTeams": [
                    team(1, [
                        {"PlayerID": "p1", "IsStarter": True, "Points": None},
                        {"PlayerID": "p2", "IsStarter": False, "Points": None},
                    ]),
                    team(2, [{"PlayerID": "p3", "IsStarter": True, "Points": None}]),
                ],
            },
            {
                "GameID": "g2",
                "Status": "Scheduled",
                "FantasyTeams": [team(1, [{"PlayerID": "p4", "IsStarter": True, "Points": None}])],
            },
        ],
        "FantasyMatchups": [{"FantasyMatchupID": "m1", "TeamIDs": [1, 2]}],
        "NonGameAssociations": [
            {
                "FantasyTeamID": 2,
                "FantasyMatchupID": "m1",
                "PlayerID": "p5",
                "IsStarter": True,
                "Kind": "bye",
            }
        ],
    }


def team_of(result: dict, team_id: int) -> dict:
    return next(
        team for team in result["Matchups"][0]["Teams"] if team["FantasyTeamID"] == team_id
    )


def range_at(team: dict, level: float) -> dict:
    return next(item for item in team["Ranges"] if item["Level"] == level)


class TeamRangeMathTests(unittest.TestCase):
    def test_level_quantiles_are_the_central_normal_quantiles(self) -> None:
        self.assertAlmostEqual(z_for_level(0.5), 0.6744897502, places=9)
        self.assertAlmostEqual(z_for_level(0.8), 1.2815515655, places=9)
        self.assertAlmostEqual(z_for_level(0.9), 1.6448536270, places=9)

    def test_player_sigma_recovers_the_standard_deviation_of_the_basis_interval(self) -> None:
        self.assertAlmostEqual(player_sigma(10 - Z90 * 7, 10 + Z90 * 7), 7.0, places=9)

    def test_team_ranges_are_symmetric_and_nested_by_level(self) -> None:
        ranges = team_ranges(200.0, 100.0)

        self.assertEqual([item["Level"] for item in ranges], [0.5, 0.8, 0.9])
        self.assertAlmostEqual(ranges[2]["Lower"], 200 - Z90 * 10, places=3)
        self.assertAlmostEqual(ranges[2]["Upper"], 200 + Z90 * 10, places=3)
        for narrow, wide in zip(ranges, ranges[1:]):
            self.assertLess(wide["Lower"], narrow["Lower"])
            self.assertGreater(wide["Upper"], narrow["Upper"])

    def test_summing_player_bounds_would_be_far_wider_than_the_team_range(self) -> None:
        sigma, count = 9.0, 12
        team = team_ranges(0.0, count * sigma * sigma)[2]
        naive_half = count * Z90 * sigma

        self.assertLess(team["Upper"], naive_half / 3)


class MatchupProjectionTests(unittest.TestCase):
    def test_pregame_team_value_range_and_state(self) -> None:
        result = build_matchup_projections(default_context(), default_model())
        team1 = team_of(result, 1)

        self.assertEqual(team1["State"], "available")
        self.assertEqual(team1["StarterCount"], 2)
        self.assertEqual(team1["ProjectedFinalScore"], 15.0)
        self.assertEqual(team1["PregameProjectedScore"], 15.0)
        self.assertEqual(team1["ScoredPoints"], 0.0)
        self.assertAlmostEqual(team1["StandardDeviation"], math.sqrt(125), places=3)
        self.assertAlmostEqual(range_at(team1, 0.9)["Lower"], 15 - Z90 * math.sqrt(125), places=3)
        self.assertEqual(result["Method"]["Id"], METHOD_ID)
        self.assertEqual(result["DisplayLevel"], 0.9)

    def test_final_game_starters_count_actual_points_without_variance(self) -> None:
        context = default_context()
        context["Games"][0]["Status"] = "Final"
        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0

        team1 = team_of(build_matchup_projections(context, default_model()), 1)

        self.assertEqual(team1["ProjectedFinalScore"], 23.0)
        self.assertEqual(team1["ScoredPoints"], 18.0)
        self.assertEqual(team1["FinalStarterCount"], 1)
        self.assertAlmostEqual(team1["StandardDeviation"], 5.0, places=3)
        self.assertEqual(team1["PregameProjectedScore"], 15.0)

    def test_live_points_of_a_game_that_is_not_final_are_ignored(self) -> None:
        baseline = default_context()
        running = copy.deepcopy(baseline)
        running["Games"][0]["Status"] = "In Progress"
        running["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 40.0

        self.assertEqual(
            team_of(build_matchup_projections(running, default_model()), 1)["ProjectedFinalScore"], 15.0
        )

    def test_out_starter_counts_zero_without_variance_and_is_listed(self) -> None:
        team1 = team_of(
            build_matchup_projections(default_context(), default_model(), availability={"p1": "out"}), 1
        )

        self.assertEqual(team1["State"], "available")
        self.assertEqual(team1["ProjectedFinalScore"], 5.0)
        self.assertEqual(team1["PregameProjectedScore"], 5.0)
        self.assertEqual(team1["OutStarterPlayerIDs"], ["p1"])
        self.assertAlmostEqual(team1["StandardDeviation"], 5.0, places=3)

    def test_uncertain_starter_keeps_its_projection_and_is_listed(self) -> None:
        team1 = team_of(
            build_matchup_projections(default_context(), default_model(), availability={"p1": "uncertain"}), 1
        )

        self.assertEqual(team1["ProjectedFinalScore"], 15.0)
        self.assertEqual(team1["UncertainStarterPlayerIDs"], ["p1"])
        self.assertEqual(team1["OutStarterPlayerIDs"], [])

    def test_availability_never_overrides_the_result_of_a_final_game(self) -> None:
        context = default_context()
        context["Games"][0]["Status"] = "Final"
        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0

        team1 = team_of(build_matchup_projections(context, default_model(), availability={"p1": "out"}), 1)

        self.assertEqual(team1["ProjectedFinalScore"], 23.0)
        self.assertEqual(team1["OutStarterPlayerIDs"], [])

    def test_final_game_starter_needs_no_projection_but_needs_points(self) -> None:
        context = default_context()
        context["Games"][0]["Status"] = "Final"
        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0
        model = default_model()
        model["Records"][0]["Projection"] = projection(0, status="insufficient-history")

        team1 = team_of(build_matchup_projections(context, model), 1)
        self.assertEqual(team1["ProjectedFinalScore"], 23.0)
        self.assertIsNone(team1["PregameProjectedScore"])

        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = None
        broken = team_of(build_matchup_projections(context, model), 1)
        self.assertEqual(broken["State"], "partial")
        self.assertIsNone(broken["ProjectedFinalScore"])
        self.assertEqual(broken["Ranges"], [])
        self.assertEqual(broken["UnavailableStarterPlayerIDs"], ["p1"])

    def test_bye_starter_counts_as_resolved_zero(self) -> None:
        team2 = team_of(build_matchup_projections(default_context(), default_model()), 2)

        self.assertEqual(team2["State"], "available")
        self.assertEqual(team2["StarterCount"], 2)
        self.assertEqual(team2["ProjectedFinalScore"], 20.0)
        self.assertEqual(team2["PregameProjectedScore"], 20.0)
        self.assertEqual(team2["ByeStarterPlayerIDs"], ["p5"])
        self.assertAlmostEqual(team2["StandardDeviation"], 10.0, places=3)

    def test_unknown_or_teamless_association_stays_unresolved(self) -> None:
        for kind in ("unknown", "no-team"):
            context = default_context()
            context["NonGameAssociations"][0]["Kind"] = kind

            team2 = team_of(build_matchup_projections(context, default_model()), 2)

            self.assertEqual(team2["State"], "partial")
            self.assertIsNone(team2["ProjectedFinalScore"])
            self.assertIsNone(team2["StandardDeviation"])
            self.assertEqual(team2["Ranges"], [])
            self.assertEqual(team2["ByeStarterPlayerIDs"], [])
            self.assertEqual(team2["UnavailableStarterPlayerIDs"], ["p5"])

    def test_bench_player_on_a_bye_is_ignored(self) -> None:
        context = default_context()
        context["NonGameAssociations"][0]["IsStarter"] = False

        team2 = team_of(build_matchup_projections(context, default_model()), 2)

        self.assertEqual(team2["StarterCount"], 1)
        self.assertEqual(team2["ByeStarterPlayerIDs"], [])

    def test_missing_projection_makes_the_team_partial_and_unavailable_without_starters(self) -> None:
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")

        team1 = team_of(build_matchup_projections(default_context(), model), 1)
        self.assertEqual(team1["State"], "partial")
        self.assertEqual(team1["ResolvedStarterCount"], 1)
        self.assertEqual(team1["UnavailableStarterPlayerIDs"], ["p4"])

        context = default_context()
        context["FantasyMatchups"].append({"FantasyMatchupID": "m2", "TeamIDs": [7, 8]})
        empty = build_matchup_projections(context, default_model())["Matchups"][1]["Teams"][0]
        self.assertEqual(empty["State"], "unavailable")
        self.assertEqual(empty["StarterCount"], 0)

    def test_season_bestball_efficiency_fallback_keeps_original_forecast_unknown(self) -> None:
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")
        stats = {
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 2},
            "Teams": [
                {"TeamID": 1, "ProjectedBestBallPoints": 220.0, "LineupEfficiencyActual": 85.0},
                {"TeamID": 2, "ProjectedBestBallPoints": 180.0, "LineupEfficiencyActual": 80.0},
            ],
        }

        result = build_matchup_projections(default_context(), model, season_statistics=stats)
        partial, complete = team_of(result, 1), team_of(result, 2)
        self.assertEqual(partial["State"], "partial")
        self.assertIsNone(partial["ProjectedFinalScore"])
        self.assertIsNone(partial["StandardDeviation"])
        self.assertEqual(partial["Ranges"], [])
        self.assertEqual(partial["DisplayProjectedScore"], 187.0)
        self.assertEqual(partial["DisplayProjectionMethod"], matchup_projection.FALLBACK_METHOD)
        self.assertEqual(partial["BestBallEfficiencyFallback"]["SourceThroughWeek"], 2)
        self.assertIsNone(partial["WinProbability"])
        self.assertEqual(complete["ProjectedFinalScore"], 20.0)
        self.assertEqual(complete["DisplayProjectedScore"], 20.0)
        self.assertEqual(complete["DisplayProjectionMethod"], METHOD_ID)
        self.assertEqual(complete["BestBallEfficiencyFallback"]["Points"], 144.0)

    def test_fallback_rejects_missing_future_wrong_league_or_invalid_data(self) -> None:
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")
        valid = {
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 2},
            "Teams": [{"TeamID": 1, "ProjectedBestBallPoints": 220.0, "LineupEfficiencyActual": 85.0}],
        }
        bad = [
            None, {}, {**valid, "CanonicalLeagueID": "other"},
            {**valid, "Season": 2025},
            {**valid, "AsOf": {"CompletedWeeks": 3}},
            {**valid, "AsOf": {"CompletedWeeks": 0}},
            {**valid, "Teams": [*valid["Teams"], valid["Teams"][0]]},
            {**valid, "Teams": [{"TeamID": 1, "ProjectedBestBallPoints": float("nan"), "LineupEfficiencyActual": 85.0}]},
            {**valid, "Teams": [{"TeamID": 1, "ProjectedBestBallPoints": 220.0, "LineupEfficiencyActual": 101.0}]},
        ]
        for stats in bad:
            with self.subTest(stats=stats):
                partial = team_of(build_matchup_projections(default_context(), model, season_statistics=stats), 1)
                self.assertIsNone(partial["DisplayProjectedScore"])
                self.assertIsNone(partial["BestBallEfficiencyFallback"])

    def test_bestball_fallback_does_not_replace_partial_live_score(self) -> None:
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")
        ctx = default_context()
        ctx["Games"][0]["Status"] = "Final"
        ctx["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0
        stats = {
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 2},
            "Teams": [{"TeamID": 1, "ProjectedBestBallPoints": 220.0, "LineupEfficiencyActual": 85.0}],
        }
        team = team_of(build_matchup_projections(ctx, model, season_statistics=stats), 1)
        self.assertIsNone(team["DisplayProjectedScore"])
        self.assertIsNotNone(team["BestBallEfficiencyFallback"])

    @staticmethod
    def display_win_test_fixture() -> tuple[dict, dict, dict]:
        context = default_context()
        context["Week"] = 4
        player = default_model()
        player["Week"] = 4
        # Team 1 lacks a starter projection; team 2 still has a complete lineup.
        player["Records"][3]["Projection"] = projection(0, status="insufficient-history")
        player["Records"][2]["Projection"] = projection(180.0, sigma=10.0)
        stats = {
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 3},
            "Teams": [
                {"TeamID": 1, "ProjectedBestBallPoints": 220, "LineupEfficiencyActual": 85,
                 "GameLog": [{"Week": 1, "Points": 100}, {"Week": 2, "Points": 130}, {"Week": 3, "Points": 160}]},
                {"TeamID": 2, "ProjectedBestBallPoints": 190, "LineupEfficiencyActual": 90,
                 "GameLog": [{"Week": 1, "Points": 180}, {"Week": 2, "Points": 200}, {"Week": 3, "Points": 170}]},
            ],
        }
        return context, player, stats

    def test_partial_team_gets_estimated_chance_without_modifying_original_v1_values(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        result = build_matchup_projections(context, player, season_statistics=stats)
        partial, complete = team_of(result, 1), team_of(result, 2)
        self.assertIsNone(partial["WinProbability"])
        self.assertIsNone(complete["WinProbability"])
        self.assertIsNone(partial["WinProbabilityRaw"])
        self.assertIsNone(partial["StandardDeviation"])
        self.assertEqual(partial["DisplayProjectedScore"], 187.0)
        self.assertEqual(partial["BestBallEfficiencyFallback"]["ScoreStandardDeviation"], 30.0)
        self.assertEqual(partial["BestBallEfficiencyFallback"]["ScoreVolatilityGames"], 3)
        self.assertEqual(partial["BestBallEfficiencyFallback"]["ScoreVolatilityMethod"], matchup_projection.FALLBACK_VOLATILITY_METHOD)
        self.assertEqual(complete["DisplayProjectedScore"], 180.0)
        raw = matchup_projection.win_prob_v1.win_probability(187.0, 30.0, 180.0, 10.0)
        self.assertEqual(
            (partial["DisplayWinProbability"], complete["DisplayWinProbability"]),
            matchup_projection.win_prob_v1.percent_pair(raw),
        )
        self.assertAlmostEqual(partial["DisplayWinProbabilityRaw"], raw)
        self.assertAlmostEqual(
            complete["DisplayWinProbabilityRaw"],
            matchup_projection.win_prob_v1.win_probability(180.0, 10.0, 187.0, 30.0),
        )
        self.assertFalse(partial["DisplayWinProbabilityIsDeterministic"])
        self.assertEqual(partial["DisplayWinProbabilityBasis"], matchup_projection.DISPLAY_CHANCE_ESTIMATE)
        self.assertEqual(complete["DisplayWinProbabilityBasis"], matchup_projection.DISPLAY_CHANCE_ESTIMATE)

    def test_complete_matchup_retains_original_win_probabilities_even_with_season_stats(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        player["Records"][3]["Projection"] = projection(5.0, sigma=5.0)
        result = build_matchup_projections(context, player, season_statistics=stats)
        for team in result["Matchups"][0]["Teams"]:
            self.assertEqual(team["DisplayWinProbability"], team["WinProbability"])
            self.assertEqual(team["DisplayWinProbabilityRaw"], team["WinProbabilityRaw"])
            self.assertEqual(team["DisplayWinProbabilityIsDeterministic"], team["WinProbabilityIsDeterministic"])
            self.assertEqual(team["DisplayWinProbabilityBasis"], "lineup")

    def test_both_teams_can_use_estimated_chance_from_the_same_history_cutoff(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        player["Records"][2]["Projection"] = projection(0, status="insufficient-history")
        result = build_matchup_projections(context, player, season_statistics=stats)
        left, right = team_of(result, 1), team_of(result, 2)
        self.assertIsNone(left["WinProbability"])
        self.assertIsNone(right["WinProbability"])
        self.assertEqual(left["DisplayWinProbability"] + right["DisplayWinProbability"], 100)
        self.assertEqual(left["DisplayWinProbabilityBasis"], matchup_projection.DISPLAY_CHANCE_ESTIMATE)
        self.assertEqual(right["DisplayWinProbabilityBasis"], matchup_projection.DISPLAY_CHANCE_ESTIMATE)

    def test_bad_or_inadequate_history_keeps_points_but_no_estimated_chance(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        histories = [
            [], [{"Week": 1, "Points": 100}, {"Week": 2, "Points": 200}],
            [{"Week": 1, "Points": 100}, {"Week": 2, "Points": 100}, {"Week": 3, "Points": 100}],
            [{"Week": 1, "Points": 100}, {"Week": 1, "Points": 110}, {"Week": 3, "Points": 120}],
            [{"Week": 1, "Points": 100}, {"Week": 2, "Points": 110}, {"Week": 4, "Points": 120}],
            [{"Week": 1, "Points": 100}, {"Week": 2, "Points": float("nan")}, {"Week": 3, "Points": 120}],
            [{"Week": 1, "Points": 100}, {"Week": 2, "Points": None}, {"Week": 3, "Points": 120}],
            [{"Week": 1, "Points": 100}, {"Week": 2, "Points": 150}, {"Week": 3, "Points": 120}, {"Week": 3, "Points": 130}],
        ]
        for games in histories:
            with self.subTest(games=games):
                case = copy.deepcopy(stats)
                case["Teams"][0]["GameLog"] = games
                partial = team_of(build_matchup_projections(context, player, season_statistics=case), 1)
                self.assertEqual(partial["DisplayProjectedScore"], 187.0)
                self.assertIsNone(partial["BestBallEfficiencyFallback"]["ScoreStandardDeviation"])
                self.assertIsNone(partial["DisplayWinProbability"])
                self.assertIsNone(partial["DisplayWinProbabilityBasis"])

    def test_started_matchup_does_not_mix_partial_live_with_season_fallback_probability(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        context["Games"][0]["Status"] = "Final"
        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0
        partial = team_of(build_matchup_projections(context, player, season_statistics=stats), 1)
        self.assertIsNone(partial["DisplayProjectedScore"])
        self.assertIsNone(partial["DisplayWinProbability"])
        self.assertIsNone(partial["DisplayWinProbabilityBasis"])

    def test_other_team_final_disables_baseline_chance_even_if_fallback_team_has_not_started(self) -> None:
        context, player, stats = self.display_win_test_fixture()
        context["Games"][0]["FantasyTeams"][1]["Players"] = []
        context["Games"].append({
            "GameID": "g3", "Status": "Final",
            "FantasyTeams": [{
                "FantasyTeamID": 2, "FantasyMatchupID": "m1",
                "Players": [{"PlayerID": "p3", "IsStarter": True, "Points": 190.0}],
            }],
        })
        result = build_matchup_projections(context, player, season_statistics=stats)
        fallback, finished = team_of(result, 1), team_of(result, 2)
        self.assertEqual(fallback["DisplayProjectedScore"], 187.0)
        self.assertEqual(fallback["FinalStarterCount"], 0)
        self.assertEqual(finished["FinalStarterCount"], 1)
        self.assertIsNone(fallback["WinProbability"])
        self.assertIsNone(fallback["DisplayWinProbability"])
        self.assertIsNone(finished["DisplayWinProbability"])

    def test_axis_covers_both_display_ranges_on_a_snapped_scale(self) -> None:
        result = build_matchup_projections(default_context(), default_model())
        axis = result["Matchups"][0]["Axis"]
        bounds = [range_at(team, 0.9) for team in result["Matchups"][0]["Teams"]]

        self.assertEqual(axis["Step"], 20)
        self.assertEqual(axis["Min"] % 20, 0)
        self.assertEqual(axis["Max"] % 20, 0)
        self.assertLessEqual(axis["Min"], min(item["Lower"] for item in bounds) - AXIS_PADDING)
        self.assertGreaterEqual(axis["Max"], max(item["Upper"] for item in bounds) + AXIS_PADDING)

    def test_axis_is_absent_when_a_team_has_no_range(self) -> None:
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")

        self.assertIsNone(build_matchup_projections(default_context(), model)["Matchups"][0]["Axis"])

    def test_projection_without_multi_level_ranges_falls_back_to_the_primary_range(self) -> None:
        model = default_model()
        for record in model["Records"]:
            record["Projection"].pop("PredictionRanges")

        team1 = team_of(build_matchup_projections(default_context(), model), 1)

        self.assertEqual(team1["ProjectedFinalScore"], 15.0)

    def test_week_mismatch_and_duplicate_player_ids_fail_closed(self) -> None:
        stale = default_model()
        stale["Week"] = 2
        with self.assertRaisesRegex(ValueError, "different weeks"):
            build_matchup_projections(default_context(), stale)

        duplicate = default_model()
        duplicate["Records"].append(copy.deepcopy(duplicate["Records"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate App PlayerID"):
            build_matchup_projections(default_context(), duplicate)

    def test_display_level_must_be_a_published_level(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a published interval level"):
            build_matchup_projections(default_context(), default_model(), display_level=0.95)

    def test_display_level_selects_the_axis_basis(self) -> None:
        wide = build_matchup_projections(default_context(), default_model(), display_level=0.9)
        narrow = build_matchup_projections(default_context(), default_model(), display_level=0.5)

        self.assertEqual(narrow["DisplayLevel"], 0.5)
        self.assertLessEqual(wide["Matchups"][0]["Axis"]["Min"], narrow["Matchups"][0]["Axis"]["Min"])


class TeamRangeModelTests(unittest.TestCase):
    def test_the_model_is_registered_and_pins_the_v1_method(self) -> None:
        from derived_data_lib.models.registry import get_model

        model = get_model("team-range-v1", "team-range")
        self.assertIs(model, team_range_v1)
        self.assertEqual(dict(model.PARAMS), {"MethodId": "normal-independent-v1", "Levels": (0.5, 0.8, 0.9), "SigmaBasisLevel": 0.9})
        self.assertEqual(model.METHOD["Id"], "normal-independent-v1")
        self.assertEqual(model.METHOD["Levels"], [0.5, 0.8, 0.9])

    def test_the_model_reads_no_file_and_no_clock(self) -> None:
        source = Path(team_range_v1.__file__).read_text(encoding="utf-8")
        for forbidden in ("open(", "read_text", "datetime", "time.", "environ"):
            self.assertNotIn(forbidden, source)


class ComputationTests(unittest.TestCase):
    """compute_matchup_projections is a pure function: nothing is written (Issue #1645)."""

    AT = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)

    def _compute(self, root: Path, context: dict, model: dict, *, windows=None):
        """Compute with a stand-in data-meta (team-range-v1 chosen for the season) and stand-in Decision Windows."""
        metadata = {"CanonicalLeagueID": "league-a", "Seasons": {"2026": {"Models": {"TeamRange": "team-range-v1", "WinProb": "win-prob-v1"}}}}
        with mock.patch("derived_data_lib.matchup_projection.load_league_metadata", return_value=metadata), mock.patch(
            "derived_data_lib.matchup_projection._decision_windows", return_value=windows
        ):
            return compute_matchup_projections(root, context, model, league_id="league-a", at_utc=self.AT)

    def _windows(self, *, week: int, state: str) -> dict:
        return {"Season": 2026, "LineupWeek": week, "ScoringAvailabilityObservations": [{"PlayerID": "p1", "State": state}]}

    def test_computation_uses_existing_shared_derived_season_statistics(self) -> None:
        root = Path(tempfile.mkdtemp())
        stats_path = root / "data-derived/season-statistics/league-a/2026.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps({
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 2},
            "Teams": [{"TeamID": 1, "ProjectedBestBallPoints": 220.0, "LineupEfficiencyActual": 85.0}],
        }), encoding="utf-8")
        model = default_model()
        model["Records"][3]["Projection"] = projection(0, status="insufficient-history")
        team = self._compute(root, default_context(), model)["Matchups"][0]["Teams"][0]
        self.assertIsNone(team["ProjectedFinalScore"])
        self.assertEqual(team["DisplayProjectedScore"], 187.0)

    def test_estimated_chance_is_computed_and_nothing_is_written(self) -> None:
        root = Path(tempfile.mkdtemp())
        context, player, stats = MatchupProjectionTests.display_win_test_fixture()
        target = root / "data-derived/season-statistics/league-a/2026.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(stats), encoding="utf-8")
        before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())

        payload = self._compute(root, context, player)
        again = self._compute(root, context, player)

        self.assertEqual(payload, again)
        self.assertEqual(before, sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()))
        self.assertEqual(payload["BestBallFallbackVolatilityMethod"], matchup_projection.FALLBACK_VOLATILITY_METHOD)
        teams = payload["Matchups"][0]["Teams"]
        self.assertIsNone(teams[0]["WinProbability"])
        self.assertIsNotNone(teams[0]["DisplayWinProbability"])
        self.assertEqual(sum(t["DisplayWinProbability"] for t in teams), 100)

    def test_week_mismatch_returns_none(self) -> None:
        model = default_model()
        model["Week"] = 2
        self.assertIsNone(self._compute(Path(tempfile.mkdtemp()), default_context(), model))

    def test_applies_availability_of_the_same_week(self) -> None:
        payload = self._compute(Path(tempfile.mkdtemp()), default_context(), default_model(), windows=self._windows(week=3, state="out"))
        self.assertEqual(payload["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], ["p1"])

    def test_ignores_availability_of_another_week(self) -> None:
        payload = self._compute(Path(tempfile.mkdtemp()), default_context(), default_model(), windows=self._windows(week=2, state="out"))
        self.assertEqual(payload["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], [])

    def test_function_failure_keeps_projections_without_availability(self) -> None:
        payload = self._compute(Path(tempfile.mkdtemp()), default_context(), default_model(), windows=None)
        self.assertEqual(payload["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], [])

    def test_decision_windows_are_resolved_for_the_context_season_at_the_given_instant(self) -> None:
        with mock.patch("derived_data_lib.matchup_projection.resolve_decision_windows", return_value={"Season": 2026}) as resolve:
            matchup_projection._decision_windows(Path("."), "league-a", 2026, self.AT)
        resolve.assert_called_once_with(Path("."), "league-a", 2026, self.AT)

    def test_decision_windows_failure_is_reported_and_yields_none(self) -> None:
        with mock.patch("derived_data_lib.matchup_projection.resolve_decision_windows", side_effect=ValueError("boom")):
            self.assertIsNone(matchup_projection._decision_windows(Path("."), "league-a", 2026, self.AT))

    def test_the_method_comes_from_the_season_model_and_the_numbers_are_unchanged(self) -> None:
        computed = self._compute(Path(tempfile.mkdtemp()), default_context(), default_model())
        direct = build_matchup_projections(default_context(), default_model())

        self.assertEqual(computed, direct)
        self.assertEqual(direct["Method"]["Id"], METHOD_ID)
        self.assertEqual(team_range_v1.MODEL_ID, "team-range-v1")

    def test_an_unknown_model_choice_fails_closed(self) -> None:
        metadata = {"CanonicalLeagueID": "league-a", "Seasons": {"2026": {"Models": {"TeamRange": "team-range-v9"}}}}
        with mock.patch("derived_data_lib.matchup_projection.load_league_metadata", return_value=metadata):
            with self.assertRaises(ValueError):
                compute_matchup_projections(Path(tempfile.mkdtemp()), default_context(), default_model(), league_id="league-a", at_utc=self.AT)

    def test_the_projections_read_nothing_from_public_data_and_write_nothing(self) -> None:
        source = Path(matchup_projection.__file__).read_text(encoding="utf-8")
        for forbidden in ("write_text", "write_json", "open(", "OUTPUT_PATH"):
            self.assertNotIn(forbidden, source)
        self.assertFalse((TOOLS / "matchup_projection.py").exists(), "the computation lives in derived_data_lib")


class HybridExpectedPreviewTests(unittest.TestCase):
    """CP2 additive shadow output; existing displayed scores/chances never change."""

    @staticmethod
    def fixture() -> tuple[dict, dict, dict, dict]:
        context = default_context()
        player = default_model()
        player["Records"] += [
            {"PlayerID": pid, "CanonicalPlayerID": f"NFLP-{pid}", "Projection": projection(points)}
            for pid, points in (
                ("p6", 30.0), ("p7", 40.0), ("p8", 200.0), ("p9", 150.0),
                ("p10", 100.0), ("p11", 80.0), ("p12", 70.0),
            )
        ]
        slots = [
            {"SlotID": "QB-1", "SlotType": "QB", "CurrentStarterID": "p1", "State": "unlocked"},
            {"SlotID": "FLEX-1", "SlotType": "FLEX", "CurrentStarterID": "p4", "State": "unlocked"},
        ]

        def member(pid: str, placement: str, position: str, *, game: str = "unlocked",
                   availability: str = "available", slot: str | None = None) -> dict:
            return {
                "PlayerID": pid, "Placement": placement, "Position": position,
                "GameState": game, "LineupSlotID": slot,
                "ScoringAvailability": {"State": availability},
            }

        members = [
            member("p1", "starter", "QB", slot="QB-1"),
            member("p4", "starter", "TE", slot="FLEX-1"),
            member("p2", "bench", "RB"),
            member("p6", "bench", "QB"),
            member("p7", "bench", "WR"),
            member("p8", "taxi", "QB"),
            member("p9", "ir", "RB"),
            member("p10", "bench", "RB", game="bye"),
            member("p11", "bench", "WR", availability="out"),
            member("p12", "bench", "WR", game="unknown"),
        ]
        windows = {
            "Season": "2026", "LineupWeek": 3,
            "FantasyRelevance": {
                "SlotDefinitions": [
                    {"SlotID": item["SlotID"], "SlotType": item["SlotType"]} for item in slots
                ],
                "Teams": [{"FantasyTeamID": "1", "Slots": slots, "Players": members}],
            },
        }
        stats = {
            "CanonicalLeagueID": "league-a", "Season": 2026,
            "AsOf": {"CompletedWeeks": 2},
            "Teams": [
                {"TeamID": 1, "ProjectedBestBallPoints": 220, "LineupEfficiencyActual": 80},
                {"TeamID": 2, "ProjectedBestBallPoints": 180, "LineupEfficiencyActual": 75},
            ],
        }
        return context, player, windows, stats

    @staticmethod
    def preview(context: dict, player: dict, windows: dict, stats: dict) -> dict:
        result = build_matchup_projections(
            context, player, decision_windows=windows, season_statistics=stats
        )
        return team_of(result, 1)["HybridExpected"]

    def test_unlocked_lineup_uses_weekly_global_best_ball_not_current_starters(self) -> None:
        context, player, windows, stats = self.fixture()
        result = build_matchup_projections(
            context, player, decision_windows=windows, season_statistics=stats
        )
        team = team_of(result, 1)
        preview = team["HybridExpected"]
        self.assertEqual(preview["State"], "available")
        self.assertEqual(preview["Method"], "weekly-hybrid-actual-efficiency-preview-v1")
        self.assertEqual(preview["PoolBasis"], "active-roster-only")
        self.assertEqual(preview["SourceThroughWeek"], 2)
        self.assertEqual(preview["ManagerEfficiencyPercent"], 80)
        self.assertAlmostEqual(preview["RemainingBestBallPoints"], 129)
        self.assertAlmostEqual(preview["ExpectedPoints"], 103.2)
        self.assertEqual(set(preview["OptimalRemainingPlayerIDs"]), {"p6", "p2"})
        self.assertEqual(preview["ExcludedPlayerCounts"]["taxi"], 1)
        self.assertEqual(preview["ExcludedPlayerCounts"]["ir"], 1)
        self.assertEqual(preview["ExcludedPlayerCounts"]["bye"], 1)
        self.assertEqual(preview["ExcludedPlayerCounts"]["confirmed-out"], 1)
        self.assertEqual(preview["ExcludedPlayerCounts"]["unknown-game"], 1)
        self.assertEqual(team["ProjectedFinalScore"], 15.0)
        self.assertEqual(team["DisplayProjectedScore"], 15.0)
        self.assertEqual(team["DisplayWinProbability"], team["WinProbability"])
        self.assertIsNone(team_of(result, 2)["HybridExpected"])

    def test_thursday_locked_starter_and_locked_bench_are_not_reselected(self) -> None:
        context, player, windows, stats = self.fixture()
        windows["FantasyRelevance"]["Teams"][0]["Slots"][0]["State"] = "locked-active"
        members = windows["FantasyRelevance"]["Teams"][0]["Players"]
        next(p for p in members if p["PlayerID"] == "p1")["GameState"] = "locked-active"
        next(p for p in members if p["PlayerID"] == "p2")["GameState"] = "locked-active"
        preview = self.preview(context, player, windows, stats)

        self.assertEqual(preview["State"], "available")
        self.assertAlmostEqual(preview["LockedProjectedPoints"], 10.0)
        self.assertEqual(preview["LockedActualPoints"], 0.0)
        self.assertEqual(preview["LockedStarterPlayerIDs"], ["p1"])
        self.assertEqual(preview["OptimalRemainingPlayerIDs"], ["p7"])
        self.assertAlmostEqual(preview["RemainingBestBallPoints"], 40.0)
        self.assertAlmostEqual(preview["ExpectedPoints"], 42.0)
        self.assertEqual(preview["ExcludedPlayerCounts"]["locked-bench"], 1)

    def test_after_final_the_locked_player_uses_actual_points_and_not_live_score(self) -> None:
        context, player, windows, stats = self.fixture()
        windows["FantasyRelevance"]["Teams"][0]["Slots"][0]["State"] = "locked-active"
        members = windows["FantasyRelevance"]["Teams"][0]["Players"]
        next(p for p in members if p["PlayerID"] == "p1")["GameState"] = "locked-active"
        next(p for p in members if p["PlayerID"] == "p2")["GameState"] = "locked-active"
        running = copy.deepcopy(context)
        running["Games"][0]["Status"] = "In Progress"
        running["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 90.0
        before = self.preview(running, player, windows, stats)
        self.assertAlmostEqual(before["LockedProjectedPoints"], 10.0)
        self.assertAlmostEqual(before["ExpectedPoints"], 42.0)  # locked bench p2 cannot be reselected

        windows["FantasyRelevance"]["Teams"][0]["Slots"][0]["State"] = "completed"
        next(p for p in members if p["PlayerID"] == "p1")["GameState"] = "completed"
        next(p for p in members if p["PlayerID"] == "p2")["GameState"] = "completed"
        running["Games"][0]["Status"] = "Final"
        running["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0
        final = self.preview(running, player, windows, stats)
        self.assertEqual(final["LockedProjectedPoints"], 0.0)
        self.assertAlmostEqual(final["LockedActualPoints"], 18.0)
        self.assertAlmostEqual(final["ExpectedPoints"], 50.0)

    def test_locked_flex_is_fixed_and_remaining_qb_can_be_optimized(self) -> None:
        context, player, windows, stats = self.fixture()
        windows["FantasyRelevance"]["Teams"][0]["Slots"][1]["State"] = "locked-active"
        next(p for p in windows["FantasyRelevance"]["Teams"][0]["Players"] if p["PlayerID"] == "p4")["GameState"] = "locked-active"
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["LockedStarterPlayerIDs"], ["p4"])
        self.assertEqual(preview["OptimalRemainingPlayerIDs"], ["p6"])
        self.assertAlmostEqual(preview["ExpectedPoints"], 29.0)

    def test_nonfillable_qb_slot_is_explicitly_incomplete_not_a_full_score(self) -> None:
        context, player, windows, stats = self.fixture()
        relevance = windows["FantasyRelevance"]
        extra = {"SlotID": "QB-2", "SlotType": "QB", "CurrentStarterID": None, "State": "unlocked"}
        relevance["SlotDefinitions"].insert(1, {"SlotID": "QB-2", "SlotType": "QB"})
        relevance["Teams"][0]["Slots"].insert(1, extra)
        next(p for p in relevance["Teams"][0]["Players"] if p["PlayerID"] == "p6")["GameState"] = "bye"
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["State"], "incomplete")
        self.assertEqual(preview["Reason"], "unfilled-required-slots")
        self.assertIsNone(preview["ExpectedPoints"])
        self.assertEqual(preview["UnfilledSlotIDs"], ["QB-2"])
        self.assertGreater(preview["RemainingBestBallPoints"], 0)

    def test_out_and_uncertain_candidates_preserve_availability_semantics(self) -> None:
        context, player, windows, stats = self.fixture()
        members = windows["FantasyRelevance"]["Teams"][0]["Players"]
        next(p for p in members if p["PlayerID"] == "p2")["ScoringAvailability"]["State"] = "out"
        next(p for p in members if p["PlayerID"] == "p7")["ScoringAvailability"]["State"] = "uncertain"
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["State"], "available")
        self.assertEqual(preview["OptimalRemainingPlayerIDs"], ["p6", "p7"])
        self.assertAlmostEqual(preview["ExpectedPoints"], 56.0)
        self.assertEqual(preview["ConditionalAvailabilityPlayerIDs"], ["p7"])
        self.assertEqual(preview["ExcludedPlayerCounts"]["confirmed-out"], 2)

    def test_mismatched_window_and_missing_efficiency_fail_closed(self) -> None:
        context, player, windows, stats = self.fixture()
        windows["LineupWeek"] = 2
        result = build_matchup_projections(
            context, player, decision_windows=windows, season_statistics=stats
        )
        self.assertIsNone(team_of(result, 1)["HybridExpected"])
        windows["LineupWeek"] = 3
        stats["AsOf"]["CompletedWeeks"] = 3  # current-week lookahead forbidden
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["State"], "unavailable")
        self.assertEqual(preview["Reason"], "missing-or-invalid-historical-efficiency")
        self.assertIsNone(preview["ExpectedPoints"])

    def test_bad_lock_evidence_fails_closed_without_touching_primary_forecast(self) -> None:
        context, player, windows, stats = self.fixture()
        windows["FantasyRelevance"]["Teams"][0]["Slots"][0]["State"] = "completed"
        next(p for p in windows["FantasyRelevance"]["Teams"][0]["Players"] if p["PlayerID"] == "p1")["GameState"] = "completed"
        result = build_matchup_projections(
            context, player, decision_windows=windows, season_statistics=stats
        )
        team = team_of(result, 1)
        self.assertEqual(team["HybridExpected"]["State"], "unavailable")
        self.assertEqual(team["HybridExpected"]["Reason"], "missing-final-starter-points")
        self.assertEqual(team["ProjectedFinalScore"], 15.0)
        self.assertEqual(team["DisplayProjectedScore"], 15.0)

    def test_all_slots_locked_use_only_actual_and_locked_projection_without_efficiency(self) -> None:
        context, player, windows, stats = self.fixture()
        slots = windows["FantasyRelevance"]["Teams"][0]["Slots"]
        members = windows["FantasyRelevance"]["Teams"][0]["Players"]
        slots[0]["State"] = "completed"
        slots[1]["State"] = "locked-active"
        next(p for p in members if p["PlayerID"] == "p1")["GameState"] = "completed"
        next(p for p in members if p["PlayerID"] == "p2")["GameState"] = "completed"
        next(p for p in members if p["PlayerID"] == "p4")["GameState"] = "locked-active"
        context["Games"][0]["Status"] = "Final"
        context["Games"][0]["FantasyTeams"][0]["Players"][0]["Points"] = 18.0
        stats["AsOf"]["CompletedWeeks"] = 3  # invalid for historical efficiency, but no flexible slots
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["State"], "available")
        self.assertEqual(preview["ExpectedPoints"], 23.0)
        self.assertEqual(preview["RemainingBestBallPoints"], 0.0)
        self.assertEqual(preview["LockedActualPoints"], 18.0)
        self.assertEqual(preview["LockedProjectedPoints"], 5.0)

    def test_missing_projection_uses_eligible_alternative_or_incomplete(self) -> None:
        context, player, windows, stats = self.fixture()
        # Preferred projected QB becomes unprojectable, but p1 remains selectable.
        next(r for r in player["Records"] if r["PlayerID"] == "p6")["Projection"] = projection(
            0, status="insufficient-history"
        )
        preview = self.preview(context, player, windows, stats)
        self.assertEqual(preview["State"], "available")
        self.assertEqual(set(preview["OptimalRemainingPlayerIDs"]), {"p1", "p2"})
        self.assertAlmostEqual(preview["ExpectedPoints"], 87.2)
        self.assertEqual(preview["ExcludedPlayerCounts"]["missing-projection"], 1)

    def test_preview_is_part_of_the_computed_document_and_deterministic(self) -> None:
        context, player, windows, stats = self.fixture()
        root = Path(tempfile.mkdtemp())
        target = root / "data-derived/season-statistics/league-a/2026.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(stats), encoding="utf-8")
        computation = ComputationTests()
        first = computation._compute(root, context, player, windows=windows)
        second = computation._compute(root, context, player, windows=windows)
        self.assertEqual(first, second)
        self.assertEqual(first["Matchups"][0]["Teams"][0]["HybridExpected"]["State"], "available")


if __name__ == "__main__":
    unittest.main()
