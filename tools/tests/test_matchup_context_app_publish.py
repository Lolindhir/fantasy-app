"""Tests for the matchup-context consumer generator (ADR-075, Issue #1199 section 3 step 7).

The exact comparison against the committed public/data files is `python3 tools/matchup_context.py compare`; these tests
pin the write rules (semantic no-op, Timestamps, fail-closed behaviour, season selection) with constructed repositories.
"""
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

import matchup_context_app_publish as publish  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError  # noqa: E402

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
LEAGUE = "test-league"


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.data = self.root / "public" / "data"
        write_json(self.data / "Timestamps.json", {"Matchups": "old", "League": "keep"})
        patcher = mock.patch.object(publish, "current_season", return_value=2026)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(publish, "manifest", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def stamps(self):
        return json.loads((self.data / "Timestamps.json").read_text(encoding="utf-8"))


class WriterTests(RepoCase):
    def test_changed_file_is_written_and_stamped_only_for_current_keys(self):
        writer = publish.Writer(self.root, NOW)
        writer.put("Matchups.json", {"Season": 2026}, "Matchups")
        writer.put("past_seasons/Matchups/Matchups_2025.json", {"Season": 2025})
        changed = writer.finish()
        self.assertIn("public/data/Matchups.json", changed)
        self.assertIn("public/data/Timestamps.json", changed)
        self.assertEqual({"Matchups": "2026-10-30T12:00:00Z", "League": "keep"}, self.stamps())

    def test_semantic_no_op_keeps_file_and_timestamp(self):
        write_json(self.data / "Matchups.json", {"Season": 2026, "Score": 1})
        writer = publish.Writer(self.root, NOW)
        writer.put("Matchups.json", {"Season": 2026, "Score": 1.0}, "Matchups")
        self.assertEqual([], writer.finish())
        self.assertEqual("old", self.stamps()["Matchups"])


class CurrentTests(RepoCase):
    def test_context_none_keeps_previous_file(self):
        write_json(self.data / "FantasyGameContext.json", {"Week": 7})
        with mock.patch.object(publish, "resolve_matchups", return_value={"Season": 2026}), \
                mock.patch.object(publish, "resolve_current_context", return_value=None):
            writer = publish.Writer(self.root, NOW)
            publish.write_current(self.root, LEAGUE, writer, NOW)
            writer.finish()
        self.assertEqual({"Week": 7}, json.loads((self.data / "FantasyGameContext.json").read_text(encoding="utf-8")))
        self.assertTrue((self.data / "Matchups.json").is_file())

    def test_context_error_warns_and_keeps_file(self):
        with mock.patch.object(publish, "resolve_matchups", return_value={"Season": 2026}), \
                mock.patch.object(publish, "resolve_current_context", side_effect=MatchupContextError("no evidence")):
            writer = publish.Writer(self.root, NOW)
            publish.write_current(self.root, LEAGUE, writer, NOW)
        self.assertFalse((self.data / "FantasyGameContext.json").exists())

    def test_matchups_error_fails_closed_with_flag(self):
        args = publish.parse_args(["--repo-root", str(self.root), "write", "--league", LEAGUE, "--fail-on-error"])
        with mock.patch.object(publish, "resolve_matchups", side_effect=MatchupContextError("incomplete")):
            self.assertEqual(1, publish.run_write(args))
        args = publish.parse_args(["--repo-root", str(self.root), "write", "--league", LEAGUE])
        with mock.patch.object(publish, "resolve_matchups", side_effect=MatchupContextError("incomplete")):
            self.assertEqual(0, publish.run_write(args))
        self.assertFalse((self.data / "Matchups.json").exists())


class HistoryTests(RepoCase):
    def make_season(self, season: int, status: str) -> None:
        write_json(self.root / "data-source" / "leagues" / LEAGUE / "seasons" / str(season) / "league.json", {"Status": status})

    def test_matchup_history_seasons_are_complete_earlier_seasons(self):
        for season, status in ((2024, "complete"), (2025, "complete"), (2026, "in_season"), (2023, "drafting")):
            self.make_season(season, status)
        with mock.patch.object(publish, "DATA_SOURCE_ROOT", "data-source"):
            self.assertEqual([2024, 2025], publish.history_matchup_seasons(self.root, LEAGUE, 2026))

    def test_context_history_seasons_are_previous_plus_existing_files(self):
        write_json(self.data / "past_seasons" / "FantasyGameContext" / "FantasyGameContext_2023.json", {})
        write_json(self.data / "past_seasons" / "FantasyGameContext" / "FantasyGameContext_2026.json", {})
        self.assertEqual([2023, 2025], publish.history_context_seasons(self.root, 2026))
        self.assertEqual([], publish.history_context_seasons(self.root / "none", 2022))

    def test_incomplete_season_keeps_last_file_and_others_are_written(self):
        write_json(self.data / "past_seasons" / "Matchups" / "Matchups_2024.json", {"Old": True})

        def resolve(root, league, season, at):
            if season == 2024:
                raise MatchupContextError("missing")
            return {"Season": season}

        for season in (2024, 2025):
            self.make_season(season, "complete")
        with mock.patch.object(publish, "DATA_SOURCE_ROOT", "data-source"), \
                mock.patch.object(publish, "resolve_matchups", side_effect=resolve), \
                mock.patch.object(publish, "resolve_historical_season", return_value={"Season": 2025}):
            writer = publish.Writer(self.root, NOW)
            publish.write_history(self.root, LEAGUE, writer, NOW)
            writer.finish()
        self.assertEqual({"Old": True}, json.loads((self.data / "past_seasons" / "Matchups" / "Matchups_2024.json").read_text(encoding="utf-8")))
        self.assertTrue((self.data / "past_seasons" / "Matchups" / "Matchups_2025.json").is_file())
        self.assertTrue((self.data / "past_seasons" / "FantasyGameContext" / "FantasyGameContext_2025.json").is_file())


if __name__ == "__main__":
    unittest.main()
