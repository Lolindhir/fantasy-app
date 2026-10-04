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

            with mock.patch.object(refresh, "build_player_week_fantasy_dataset", fake_build), mock.patch.object(
                refresh, "write_dataset", fake_write
            ), mock.patch.object(refresh, "materialize_app_player_week_fantasy", fake_publish):
                result = refresh.refresh(root)

            self.assertEqual(calls, ["build", "write", "publish"])
            self.assertEqual(result["Status"], "published")
            self.assertTrue(result["DerivedChanged"])
            self.assertFalse(result["AppChanged"])
            self.assertEqual(result["RecordCount"], 3)

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
