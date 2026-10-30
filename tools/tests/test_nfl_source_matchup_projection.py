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

import matchup_projection  # noqa: E402
from derived_data_lib.models.team_range import v1 as team_range_v1  # noqa: E402
from matchup_projection import (  # noqa: E402
    AXIS_PADDING,
    METHOD_ID,
    build_matchup_projections,
    player_sigma,
    publish_matchup_projections,
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


class PublicationTests(unittest.TestCase):
    AT = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)

    def _publish(self, root: Path, context: dict, model: dict, *, windows=None) -> dict:
        """Publish with a stand-in data-meta (team-range-v1 chosen for the season) and stand-in Decision Windows."""
        metadata = {"CanonicalLeagueID": "league-a", "Seasons": {"2026": {"Models": {"TeamRange": "team-range-v1"}}}}
        with mock.patch("matchup_projection.load_league_metadata", return_value=metadata), mock.patch(
            "matchup_projection._decision_windows", return_value=windows
        ):
            return publish_matchup_projections(root, context, model, league_id="league-a", at_utc=self.AT)

    def _windows(self, *, week: int, state: str) -> dict:
        return {"Season": 2026, "LineupWeek": week, "ScoringAvailabilityObservations": [{"PlayerID": "p1", "State": state}]}

    def _payload(self, root: Path) -> dict:
        return json.loads((root / "public/data/MatchupProjections.json").read_text(encoding="utf-8"))

    def test_publication_writes_once_and_is_a_semantic_no_op_afterwards(self) -> None:
        root = Path(tempfile.mkdtemp())

        first = self._publish(root, default_context(), default_model())
        second = self._publish(root, default_context(), default_model())

        self.assertEqual(first["Status"], "published")
        self.assertTrue(first["Changed"])
        self.assertFalse(second["Changed"])
        self.assertEqual(first["AvailableTeamCount"], 2)
        self.assertEqual(self._payload(root)["Week"], 3)

    def test_week_mismatch_keeps_the_existing_publication(self) -> None:
        model = default_model()
        model["Week"] = 2
        root = Path(tempfile.mkdtemp())
        existing = root / "public/data/MatchupProjections.json"
        existing.parent.mkdir(parents=True)
        existing.write_text("previous", encoding="utf-8")

        result = self._publish(root, default_context(), model)

        self.assertEqual(result["Status"], "skipped-week-mismatch")
        self.assertEqual(existing.read_text(encoding="utf-8"), "previous")

    def test_publication_applies_availability_of_the_same_week(self) -> None:
        root = Path(tempfile.mkdtemp())

        self._publish(root, default_context(), default_model(), windows=self._windows(week=3, state="out"))

        self.assertEqual(self._payload(root)["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], ["p1"])

    def test_publication_ignores_availability_of_another_week(self) -> None:
        root = Path(tempfile.mkdtemp())

        self._publish(root, default_context(), default_model(), windows=self._windows(week=2, state="out"))

        self.assertEqual(self._payload(root)["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], [])

    def test_function_failure_keeps_projections_without_availability(self) -> None:
        root = Path(tempfile.mkdtemp())

        result = self._publish(root, default_context(), default_model(), windows=None)

        self.assertEqual("published", result["Status"])
        self.assertEqual(self._payload(root)["Matchups"][0]["Teams"][0]["OutStarterPlayerIDs"], [])

    def test_decision_windows_are_resolved_for_the_context_season_at_the_given_instant(self) -> None:
        with mock.patch("matchup_projection.resolve_decision_windows", return_value={"Season": 2026}) as resolve:
            matchup_projection._decision_windows(Path("."), "league-a", 2026, self.AT)
        resolve.assert_called_once_with(Path("."), "league-a", 2026, self.AT)

    def test_decision_windows_failure_is_reported_and_yields_none(self) -> None:
        with mock.patch("matchup_projection.resolve_decision_windows", side_effect=ValueError("boom")):
            self.assertIsNone(matchup_projection._decision_windows(Path("."), "league-a", 2026, self.AT))

    def test_the_method_comes_from_the_season_model_and_the_numbers_are_unchanged(self) -> None:
        root = Path(tempfile.mkdtemp())
        self._publish(root, default_context(), default_model())
        direct = build_matchup_projections(default_context(), default_model())

        self.assertEqual(self._payload(root), direct)
        self.assertEqual(direct["Method"]["Id"], METHOD_ID)
        self.assertEqual(team_range_v1.MODEL_ID, "team-range-v1")

    def test_an_unknown_model_choice_fails_closed(self) -> None:
        root = Path(tempfile.mkdtemp())
        metadata = {"CanonicalLeagueID": "league-a", "Seasons": {"2026": {"Models": {"TeamRange": "team-range-v9"}}}}
        with mock.patch("matchup_projection.load_league_metadata", return_value=metadata):
            with self.assertRaises(ValueError):
                publish_matchup_projections(root, default_context(), default_model(), league_id="league-a", at_utc=self.AT)

    def test_the_projections_read_nothing_from_public_data(self) -> None:
        self.assertNotIn("public/data/FantasyGame", Path(matchup_projection.__file__).read_text(encoding="utf-8"))
        self.assertNotIn("public/data/PlayerWeek", Path(matchup_projection.__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
