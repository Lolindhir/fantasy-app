"""Tests for the WeeklyRecaps consumer generator (ADR-063, Issue #1199 section 4 step 4); constructed repositories only."""
from __future__ import annotations

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

import weekly_recaps_app_publish as publish  # noqa: E402
from derived_data_lib.weekly_recaps import WeeklyRecapsError  # noqa: E402

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
LEAGUE = "test-league"


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class PublishCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.data = self.root / "public" / "data"
        write_json(self.data / "Timestamps.json", {"WeeklyRecaps": "old", "League": "keep"})
        for name, value in (("current_season", 2026), ("manifest", {})):
            patcher = mock.patch.object(publish, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def stamps(self):
        return json.loads((self.data / "Timestamps.json").read_text(encoding="utf-8"))


class WriteTests(PublishCase):
    def test_current_is_written_and_stamped(self):
        with mock.patch.object(publish, "resolve_weekly_recaps", return_value={"Season": "2026", "Weeks": []}):
            writer = publish.Writer(self.root, NOW)
            publish.write_current(self.root, LEAGUE, writer)
            changed = writer.finish()
        self.assertIn("public/data/WeeklyRecaps.json", changed)
        self.assertEqual("2026-10-30T12:00:00Z", self.stamps()["WeeklyRecaps"])
        self.assertEqual("keep", self.stamps()["League"])

    def test_semantic_no_op_keeps_file_and_timestamp(self):
        write_json(self.data / "WeeklyRecaps.json", {"Season": "2026", "Weeks": [{"Week": 1, "Points": 3}]})
        with mock.patch.object(publish, "resolve_weekly_recaps", return_value={"Season": "2026", "Weeks": [{"Week": 1, "Points": 3.0}]}):
            writer = publish.Writer(self.root, NOW)
            publish.write_current(self.root, LEAGUE, writer)
            self.assertEqual([], writer.finish())
        self.assertEqual("old", self.stamps()["WeeklyRecaps"])

    def test_history_writes_each_season_without_timestamp_and_skips_broken_one(self):
        def fake(root, league, season):
            if season == 2024:
                raise WeeklyRecapsError("contradiction")
            return {"Season": str(season), "Weeks": []}

        with mock.patch.object(publish, "history_matchup_seasons", return_value=[2024, 2025]), \
                mock.patch.object(publish, "resolve_weekly_recaps", side_effect=fake):
            writer = publish.Writer(self.root, NOW)
            publish.write_history(self.root, LEAGUE, writer)
            changed = writer.finish()
        self.assertEqual(["public/data/past_seasons/WeeklyRecaps/WeeklyRecaps_2025.json"], changed)
        self.assertEqual("old", self.stamps()["WeeklyRecaps"])


class RunTests(PublishCase):
    def args(self, *extra):
        return publish.parse_args(["--repo-root", str(self.root), "write", "--league", LEAGUE, *extra])

    def test_current_error_exit_code_depends_on_flag(self):
        with mock.patch.object(publish, "resolve_weekly_recaps", side_effect=WeeklyRecapsError("bad")):
            self.assertEqual(0, publish.run_write(self.args()))
            self.assertEqual(1, publish.run_write(self.args("--fail-on-error")))
        self.assertFalse((self.data / "WeeklyRecaps.json").exists())

    def test_without_league_exactly_one_league_is_required(self):
        with mock.patch.object(publish, "list_league_ids", return_value=["a", "b"]):
            with self.assertRaises(WeeklyRecapsError):
                publish.leagues(self.root, None)
        with mock.patch.object(publish, "list_league_ids", return_value=["a"]):
            self.assertEqual(["a"], publish.leagues(self.root, None))


if __name__ == "__main__":
    unittest.main()
