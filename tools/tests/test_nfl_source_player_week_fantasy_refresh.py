from __future__ import annotations

import contextlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import player_week_fantasy_refresh as refresh  # noqa: E402
from player_week_fantasy_materialize import _target_roster  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_repo(root: Path) -> None:
    write_json(
        root / "data-source" / "leagues" / "league-a" / "seasons" / "2026" / "league.json",
        {
            "CanonicalLeagueID": "league-a",
            "Season": 2026,
            "WeekStructure": {"Season": 2026, "LastScoredLeg": 2},
        },
    )


CONTEXT = {"Season": 2026, "Week": 4}


def target(week, league_ids=("league-a",)):
    """Patch the lifecycle target resolution: one configured league in season 2026 whose LineupWeek is ``week``."""
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.object(refresh, "list_league_ids", return_value=list(league_ids)))
    stack.enter_context(mock.patch.object(refresh, "league_manifest", return_value={}))
    stack.enter_context(mock.patch.object(refresh, "current_season", return_value=2026))
    stack.enter_context(mock.patch.object(refresh, "resolve_lifecycle", return_value={"LineupWeek": week}))
    return stack


class ResolveTargetTests(unittest.TestCase):
    AT = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)

    def test_resolves_league_season_and_lineup_week_from_the_lifecycle(self) -> None:
        with target(4):
            self.assertEqual(refresh.resolve_target(Path("."), self.AT), ("league-a", 2026, 4))

    def test_the_lifecycle_is_asked_at_the_given_instant(self) -> None:
        with target(4) as stack, mock.patch.object(refresh, "resolve_lifecycle", return_value={"LineupWeek": 4}) as life:
            refresh.resolve_target(Path("."), self.AT)
        life.assert_called_once_with(Path("."), "league-a", 2026, self.AT)

    def test_invalid_week_fails_closed(self) -> None:
        for week in (0, -1, "4x", None, True, 4.0):
            with self.subTest(week=week), target(week):
                with self.assertRaises(ValueError):
                    refresh.resolve_target(Path("."), self.AT)

    def test_not_exactly_one_league_fails_closed(self) -> None:
        for league_ids in ((), ("league-a", "league-b")):
            with self.subTest(league_ids=league_ids), target(4, league_ids):
                with self.assertRaisesRegex(ValueError, "exactly one configured league"):
                    refresh.resolve_target(Path("."), self.AT)

    def test_the_refresh_reads_nothing_from_public_data(self) -> None:
        self.assertNotIn("public/data", Path(refresh.__file__).read_text(encoding="utf-8"))


class RefreshTests(unittest.TestCase):
    def test_unsynced_weekly_roster_skips_without_materializing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            with mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build, mock.patch.object(
                refresh, "materialize_app_player_week_fantasy"
            ) as publish:
                with target(4):
                    result = refresh.refresh(root)
            build.assert_not_called()
            publish.assert_not_called()
            self.assertEqual(result["Status"], "skipped-weekly-roster-not-synced")
            self.assertEqual((result["Season"], result["Week"]), (2026, 4))

    def test_synced_week_materializes_then_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            write_json(refresh.weekly_roster_path(root, 2026, 4), {"Records": []})
            calls: list[str] = []
            dataset = {"Records": []}

            def fake_build(repo_root, **kwargs):
                calls.append("build")
                self.assertEqual(kwargs, {"league_id": "league-a", "season": 2026, "week": 4})
                return dataset

            def fake_write(path, payload):
                calls.append("write")
                self.assertEqual(
                    path, root / "data-derived" / "player-week-fantasy" / "league-a" / "2026" / "04.json"
                )
                self.assertIs(payload, dataset)
                return True

            def fake_publish(repo_root, league_id, season, week):
                calls.append("publish")
                self.assertEqual((league_id, season, week), ("league-a", 2026, 4))
                return {"Records": [1, 2, 3]}, False

            def fake_matchups(repo_root, context, player_model, *, league_id, at_utc):
                calls.append("matchups")
                self.assertEqual(repo_root, root.resolve())
                self.assertIs(context, CONTEXT)
                self.assertEqual(player_model, {"Records": [1, 2, 3]})
                self.assertEqual(league_id, "league-a")
                return {"Status": "published", "Changed": True}

            with mock.patch.object(refresh, "build_player_week_fantasy_dataset", fake_build), mock.patch.object(
                refresh, "write_dataset", fake_write
            ), mock.patch.object(refresh, "materialize_app_player_week_fantasy", fake_publish), mock.patch.object(
                refresh, "publish_matchup_projections", fake_matchups
            ), mock.patch.object(refresh, "resolve_current_context", return_value=CONTEXT), target(4):
                result = refresh.refresh(root)

            self.assertEqual(calls, ["build", "write", "publish", "matchups"])
            self.assertEqual(result["MatchupProjections"], {"Status": "published", "Changed": True})
            self.assertEqual(result["Status"], "published")
            self.assertTrue(result["DerivedChanged"])
            self.assertFalse(result["AppChanged"])
            self.assertEqual(result["RecordCount"], 3)

    def test_missing_current_week_uses_previous_roster_for_current_app_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            write_json(refresh.weekly_roster_path(root, 2026, 3), {"Season": 2026, "Week": 3, "Records": []})
            kwargs_seen = []
            dataset = {"Records": []}
            with mock.patch.object(
                refresh, "build_player_week_fantasy_dataset",
                side_effect=lambda repo_root, **kwargs: (kwargs_seen.append(kwargs) or dataset),
            ), mock.patch.object(refresh, "write_dataset", return_value=True), mock.patch.object(
                refresh, "materialize_app_player_week_fantasy", return_value=({"Records": []}, True)
            ), mock.patch.object(
                refresh, "publish_matchup_projections", return_value={"Status": "published"}
            ), mock.patch.object(refresh, "resolve_current_context", return_value={"Season": 2026}), target(4):
                result = refresh.refresh(root)
            self.assertEqual(result["Status"], "published")
            self.assertEqual(result["RosterSourceWeek"], 3)
            self.assertTrue(result["RosterProvisional"])
            self.assertEqual(kwargs_seen, [{
                "league_id": "league-a", "season": 2026, "week": 4,
                "allow_provisional_roster": True,
            }])

    def test_without_a_matchup_context_the_projections_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            write_json(refresh.weekly_roster_path(root, 2026, 4), {"Records": []})
            with mock.patch.object(refresh, "build_player_week_fantasy_dataset", return_value={"Records": []}), \
                    mock.patch.object(refresh, "write_dataset", return_value=False), \
                    mock.patch.object(refresh, "materialize_app_player_week_fantasy", return_value=({"Records": []}, False)), \
                    mock.patch.object(refresh, "resolve_current_context", return_value=None), \
                    mock.patch.object(refresh, "publish_matchup_projections") as publish, target(4):
                result = refresh.refresh(root)
            publish.assert_not_called()
            self.assertEqual(result["MatchupProjections"], {"Status": "skipped-no-matchup-context"})

    def test_week_one_does_not_use_previous_season_roster(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            with target(1):
                result = refresh.refresh(root)
            self.assertEqual(result["Status"], "skipped-weekly-roster-not-synced")


class PreviousFinalizedWeekCatchupTests(unittest.TestCase):
    def _root(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        build_repo(root)
        path = root / "data-source/leagues/league-a/seasons/2026/league.json"
        league = json.loads(path.read_text(encoding="utf-8"))
        league["WeekStructure"]["LastScoredLeg"] = 6
        write_json(path, league)
        write_json(refresh.weekly_roster_path(root, 2026, 6), {"Records": []})
        return root

    def test_replays_exact_prior_final_scored_week_without_app_republication(self):
        root = self._root()
        calls = []
        candidate = {
            "Records": [{"CanonicalPlayerID": "player",
                         "Actual": {"State": "final", "Points": 4.7}}],
            "Materialization": {
                "ActualScoringEvidenceFinalized": True,
                "TargetRosterProvisional": False,
            },
        }

        def build(repo_root, **kwargs):
            calls.append(("build", kwargs))
            return candidate

        def write(path, payload):
            calls.append(("write", path.relative_to(root).as_posix()))
            return path.name == "06.json"

        with mock.patch.object(refresh, "stats_complete_weeks", return_value={6}), \
             mock.patch.object(refresh, "_week_finality", return_value=(True, {"game1"})), \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset", side_effect=build), \
             mock.patch.object(refresh, "write_dataset", side_effect=write), \
             mock.patch.object(refresh, "materialize_app_player_week_fantasy",
                               return_value=({"Records": []}, False)) as app_publish, \
             mock.patch.object(refresh, "resolve_current_context", return_value={"Season": 2026}), \
             mock.patch.object(refresh, "publish_matchup_projections", return_value={"Status": "ok"}), target(7):
            result = refresh.refresh(root)

        self.assertEqual([x[1]["week"] for x in calls if x[0] == "build"], [7, 6])
        self.assertEqual([x[1] for x in calls if x[0] == "write"], [
            "data-derived/player-week-fantasy/league-a/2026/07.json",
            "data-derived/player-week-fantasy/league-a/2026/06.json",
        ])
        self.assertEqual(result["FinalizedPreviousWeek"], {
            "Season": 2026, "Week": 6, "DerivedChanged": True, "RecordCount": 1,
        })
        app_publish.assert_called_once_with(root, "league-a", 2026, 7)
        self.assertFalse(result["AppChanged"])

    def test_no_replay_if_provider_has_not_scored_predecessor(self):
        root = self._root()
        path = root / "data-source/leagues/league-a/seasons/2026/league.json"
        league = json.loads(path.read_text(encoding="utf-8"))
        league["WeekStructure"]["LastScoredLeg"] = 5
        write_json(path, league)
        with mock.patch.object(refresh, "_week_finality") as final, \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build:
            self.assertIsNone(refresh.refresh_previous_scored_week(
                root, league_id="league-a", season=2026, current_week=7))
            build.assert_not_called()
            final.assert_not_called()

    def test_league_scored_week_waits_for_stats_coverage(self):
        root = self._root()
        with mock.patch.object(refresh, "stats_complete_weeks", return_value=set()), \
             mock.patch.object(refresh, "_week_finality", return_value=(True, {"game1"})), \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build, \
             mock.patch.object(refresh, "write_dataset") as write:
            result = refresh.refresh_previous_scored_week(
                root, league_id="league-a", season=2026, current_week=7)
        self.assertEqual({"Season": 2026, "Week": 6, "Status": "awaiting-stats-coverage"}, result)
        build.assert_not_called()
        write.assert_not_called()

    def test_unfinalized_nfl_week_fails_closed_even_when_league_scored(self):
        root = self._root()
        with mock.patch.object(refresh, "_week_finality", return_value=(False, set())), \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build, \
             mock.patch.object(refresh, "write_dataset") as write:
            with self.assertRaisesRegex(ValueError, "lacks canonical NFL finality"):
                refresh.refresh_previous_scored_week(
                    root, league_id="league-a", season=2026, current_week=7)
            build.assert_not_called()
            write.assert_not_called()

    def test_incomplete_final_actual_never_writes_derived(self):
        root = self._root()
        payload = {
            "Records": [{"CanonicalPlayerID": "p"}],
            "Materialization": {"ActualScoringEvidenceFinalized": False,
                                "TargetRosterProvisional": False},
        }
        with mock.patch.object(refresh, "stats_complete_weeks", return_value={6}), \
             mock.patch.object(refresh, "_week_finality", return_value=(True, {"game1"})), \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset", return_value=payload), \
             mock.patch.object(refresh, "write_dataset") as write:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                refresh.refresh_previous_scored_week(
                    root, league_id="league-a", season=2026, current_week=7)
            write.assert_not_called()

    def test_finished_snapshot_can_be_a_noop(self):
        root = self._root()
        payload = {"Records": [{"CanonicalPlayerID": "p"}],
                   "Materialization": {"ActualScoringEvidenceFinalized": True,
                                       "TargetRosterProvisional": False}}
        with mock.patch.object(refresh, "stats_complete_weeks", return_value={6}), \
             mock.patch.object(refresh, "_week_finality", return_value=(True, {"game1"})), \
             mock.patch.object(refresh, "build_player_week_fantasy_dataset", return_value=payload), \
             mock.patch.object(refresh, "write_dataset", return_value=False) as write:
            first = refresh.refresh_previous_scored_week(root, league_id="league-a", season=2026, current_week=7)
            second = refresh.refresh_previous_scored_week(root, league_id="league-a", season=2026, current_week=7)
        self.assertFalse(first["DerivedChanged"])
        self.assertEqual(first, second)
        self.assertEqual(write.call_count, 2)

    def test_replay_rejects_missing_canonical_league_scoring_bounds(self):
        root = self._root()
        path = root / "data-source/leagues/league-a/seasons/2026/league.json"
        league = json.loads(path.read_text(encoding="utf-8"))
        del league["WeekStructure"]
        write_json(path, league)
        with mock.patch.object(refresh, "_week_finality") as final:
            with self.assertRaisesRegex(ValueError, "scored-week boundary"):
                refresh.refresh_previous_scored_week(
                    root, league_id="league-a", season=2026, current_week=7)
            final.assert_not_called()

    def test_week_one_never_replays_previous_season(self):
        root = self._root()
        with mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build:
            self.assertIsNone(refresh.refresh_previous_scored_week(
                root, league_id="league-a", season=2026, current_week=1))
            build.assert_not_called()


class FinalActualCoverageGateTests(unittest.TestCase):
    """Shared week-final definition (ADR-071): incomplete stats coverage never yields final 0 points."""

    def _repo(self, root: Path, covered_teams: list[str]) -> None:
        write_json(root / "data-source/nfl/game-finality/2026.json", {
            "Season": 2026,
            "Weeks": [{"GameType": "REG", "Week": 3, "ApplicableGameCount": 2,
                       "FinalGameCount": 2, "WeekFinal": True}],
            "Games": [{"GameType": "REG", "Week": 3, "GameID": g, "Final": True} for g in ("g1", "g2")],
        })
        write_json(root / "data-source/nfl/schedules/2026.json", {"Games": [
            {"GameType": "REG", "Week": 3, "HomeTeam": "AAA", "AwayTeam": "BBB"},
            {"GameType": "REG", "Week": 3, "HomeTeam": "CCC", "AwayTeam": "DDD"},
        ]})
        write_json(root / "data-source/nfl/player-stats/2026/03.json", {
            "Season": 2026, "Week": 3,
            "Records": [{"CanonicalPlayerID": f"p-{team}", "Team": team, "SeasonType": "REG",
                         "Stats": {"game_id": "g1"}} for team in covered_teams],
        })

    def test_missing_team_coverage_keeps_actual_unavailable(self):
        from player_week_fantasy_materialize import _final_actual_inputs
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root, ["AAA", "BBB", "CCC"])
            self.assertEqual((False, {}, {}), _final_actual_inputs(root, season=2026, week=3, scoring={}))

    def test_full_team_coverage_finalizes_actual(self):
        from player_week_fantasy_materialize import _final_actual_inputs
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root, ["AAA", "BBB", "CCC", "DDD"])
            finalized, stats, _events = _final_actual_inputs(root, season=2026, week=3, scoring={})
            self.assertTrue(finalized)
            self.assertEqual(4, len(stats))


class RealFinalWeekScoringRegression(unittest.TestCase):
    def test_w06_canonical_source_scores_kaelon_black_four_point_seven(self):
        from player_week_fantasy_materialize import build_player_week_fantasy_dataset
        root = TOOLS.parent
        dataset = build_player_week_fantasy_dataset(
            root, league_id="nfl-reise", season=2026, week=6,
        )
        player = next(
            row for row in dataset["Records"]
            if row["CanonicalPlayerID"] == "NFLP-1756c2a36e6d88906258"
        )
        self.assertEqual(player["Actual"], {"Points": 4.7, "State": "final"})
        self.assertTrue(dataset["Materialization"]["ActualScoringEvidenceFinalized"])
        self.assertFalse(dataset["Materialization"]["TargetRosterProvisional"])



class TargetWeeklyRosterFallbackTests(unittest.TestCase):
    def test_current_week_is_authoritative_even_when_provisional_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(refresh.weekly_roster_path(root, 2026, 3), {
                "Season": 2026, "Week": 3,
                "Records": [{"Position": "WR", "CanonicalPlayerID": "previous", "Team": "OLD"}],
            })
            write_json(refresh.weekly_roster_path(root, 2026, 4), {
                "Season": 2026, "Week": 4,
                "Records": [{"Position": "WR", "CanonicalPlayerID": "current", "Team": "NEW"}],
            })
            roster, finalized, source_week = _target_roster(
                root, 2026, 4, allow_provisional_roster=True
            )
            self.assertEqual(source_week, 4)
            self.assertFalse(finalized)
            self.assertEqual([(p["CanonicalPlayerID"], p["Team"]) for p in roster], [("current", "NEW")])

    def test_provisional_uses_only_immediately_previous_week_in_same_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(refresh.weekly_roster_path(root, 2026, 3), {
                "Season": 2026, "Week": 3,
                "Records": [
                    {"Position": "WR", "CanonicalPlayerID": "known", "Team": "SEA"},
                    {"Position": "DB", "CanonicalPlayerID": "ignored", "Team": "SEA"},
                    {"Position": "QB", "CanonicalPlayerID": "retired", "Team": "SEA", "Status": "RET"},
                ],
            })
            roster, finalized, source_week = _target_roster(
                root, 2026, 4, allow_provisional_roster=True
            )
            self.assertEqual(source_week, 3)
            self.assertFalse(finalized)
            self.assertEqual([p["CanonicalPlayerID"] for p in roster], ["known"])
            with self.assertRaises(ValueError):
                _target_roster(root, 2026, 4)  # Historical/backtest mode: fail closed.
            with self.assertRaises(ValueError):
                _target_roster(root, 2026, 5, allow_provisional_roster=True)
            with self.assertRaises(ValueError):
                _target_roster(root, 2027, 4, allow_provisional_roster=True)

    def test_provisional_rejects_wrong_week_and_duplicate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = refresh.weekly_roster_path(root, 2026, 3)
            write_json(previous, {
                "Season": 2026, "Week": 2, "Records": []
            })
            with self.assertRaisesRegex(ValueError, "season/week mismatch"):
                _target_roster(root, 2026, 4, allow_provisional_roster=True)
            write_json(previous, {
                "Season": 2026, "Week": 3,
                "Records": [
                    {"Position": "WR", "CanonicalPlayerID": "same", "Team": "SEA"},
                    {"Position": "RB", "CanonicalPlayerID": "same", "Team": "DEN"},
                ],
            })
            with self.assertRaisesRegex(ValueError, "Duplicate CanonicalPlayerID"):
                _target_roster(root, 2026, 4, allow_provisional_roster=True)


class RefreshErrorTests(unittest.TestCase):
    def test_generator_failure_is_not_swallowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            write_json(refresh.weekly_roster_path(root, 2026, 4), {"Records": []})
            with mock.patch.object(
                refresh, "build_player_week_fantasy_dataset", side_effect=ValueError("broken input")
            ):
                with target(4), self.assertRaises(ValueError):
                    refresh.refresh(root)


if __name__ == "__main__":
    unittest.main()
