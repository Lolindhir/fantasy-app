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

import player_week_fantasy_refresh as refresh  # noqa: E402
from player_week_fantasy_materialize import _target_roster  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_repo(root: Path, *, context: dict | None = None, mappings: list | None = None) -> None:
    write_json(
        root / "public" / "data" / "FantasyGameContext.json",
        context if context is not None else {"LeagueID": "999", "Season": "2026", "Week": 4},
    )
    write_json(
        root / "source-data" / "leagues" / "league-a" / "seasons" / "2026" / "league.json",
        {
            "CanonicalLeagueID": "league-a",
            "ProviderMappings": mappings
            if mappings is not None
            else [{"Provider": "Sleeper", "ProviderLeagueID": "999"}],
        },
    )


class ResolveTargetTests(unittest.TestCase):
    def test_resolves_canonical_league_season_and_week_from_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            self.assertEqual(refresh.resolve_target(root), ("league-a", 2026, 4))

    def test_integer_season_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root, context={"LeagueID": "999", "Season": 2026, "Week": 4})
            self.assertEqual(refresh.resolve_target(root), ("league-a", 2026, 4))

    def test_unmapped_league_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root, mappings=[{"Provider": "Sleeper", "ProviderLeagueID": "other"}])
            with self.assertRaises(ValueError):
                refresh.resolve_target(root)

    def test_non_sleeper_mapping_does_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root, mappings=[{"Provider": "Other", "ProviderLeagueID": "999"}])
            with self.assertRaises(ValueError):
                refresh.resolve_target(root)

    def test_invalid_week_fails_closed(self) -> None:
        for week in (0, -1, "4x", None, True, 4.0):
            with self.subTest(week=week), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                build_repo(root, context={"LeagueID": "999", "Season": "2026", "Week": week})
                with self.assertRaises(ValueError):
                    refresh.resolve_target(root)

    def test_missing_context_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                refresh.resolve_target(Path(tmp))


class RefreshTests(unittest.TestCase):
    def test_unsynced_weekly_roster_skips_without_materializing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root)
            with mock.patch.object(refresh, "build_player_week_fantasy_dataset") as build, mock.patch.object(
                refresh, "materialize_app_player_week_fantasy"
            ) as publish:
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
                    path, root / "derived-data" / "player-week-fantasy" / "league-a" / "2026" / "04.json"
                )
                self.assertIs(payload, dataset)
                return True

            def fake_publish(repo_root, league_id, season, week):
                calls.append("publish")
                self.assertEqual((league_id, season, week), ("league-a", 2026, 4))
                return {"Records": [1, 2, 3]}, False

            def fake_matchups(repo_root):
                calls.append("matchups")
                self.assertEqual(repo_root, root.resolve())
                return {"Status": "published", "Changed": True}

            with mock.patch.object(refresh, "build_player_week_fantasy_dataset", fake_build), mock.patch.object(
                refresh, "write_dataset", fake_write
            ), mock.patch.object(refresh, "materialize_app_player_week_fantasy", fake_publish), mock.patch.object(
                refresh, "publish_matchup_projections", fake_matchups
            ):
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
            ):
                result = refresh.refresh(root)
            self.assertEqual(result["Status"], "published")
            self.assertEqual(result["RosterSourceWeek"], 3)
            self.assertTrue(result["RosterProvisional"])
            self.assertEqual(kwargs_seen, [{
                "league_id": "league-a", "season": 2026, "week": 4,
                "allow_provisional_roster": True,
            }])

    def test_week_one_does_not_use_previous_season_roster(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root, context={"LeagueID": "999", "Season": 2026, "Week": 1})
            result = refresh.refresh(root)
            self.assertEqual(result["Status"], "skipped-weekly-roster-not-synced")


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
                with self.assertRaises(ValueError):
                    refresh.refresh(root)


if __name__ == "__main__":
    unittest.main()
