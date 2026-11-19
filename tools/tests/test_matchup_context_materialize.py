"""Tests for the matchup-context product materializer (ADR-089, Issue #1571): layout, byte no-op, optional documents and scope."""
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

import matchup_context_materialize as mat  # noqa: E402
from derived_data_lib.matchup_context import MatchupContextError  # noqa: E402

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
LEAGUE = "test-league"


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def patch_builders(self, builders):
        patcher = mock.patch.object(mat, "build_documents", return_value=builders)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_documents_are_written_once_and_a_second_run_is_a_byte_no_op(self):
        self.patch_builders({mat.MATCHUPS: lambda: {"Season": 2025}, mat.CONTEXT_HISTORY: lambda: {"Weeks": []}})
        first = mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW)
        second = mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW)
        self.assertEqual(2, first["Written"])
        self.assertEqual(0, second["Written"])
        self.assertEqual(2, second["Unchanged"])
        self.assertEqual({"Season": 2025}, mat.read_document(self.root, LEAGUE, 2025, mat.MATCHUPS))

    def test_check_only_writes_nothing(self):
        self.patch_builders({mat.MATCHUPS: lambda: {"Season": 2025}})
        summary = mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW, check_only=True)
        self.assertEqual(1, summary["WouldWrite"])
        self.assertIsNone(mat.read_document(self.root, LEAGUE, 2025, mat.MATCHUPS))

    def test_optional_document_error_is_skipped_but_required_one_raises(self):
        def broken():
            raise MatchupContextError("no evidence")

        self.patch_builders({mat.MATCHUPS: lambda: {"Season": 2025}, mat.CONTEXT_HISTORY: broken})
        summary = mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW)
        self.assertEqual([mat.CONTEXT_HISTORY], summary["Skipped"])
        self.patch_builders({mat.MATCHUPS: broken})
        with self.assertRaises(MatchupContextError):
            mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW)

    def test_documents_carry_no_clock(self):
        self.patch_builders({mat.MATCHUPS: lambda: {"Season": 2025}})
        mat.materialize_season(self.root, self.root, LEAGUE, 2025, 2026, NOW)
        text = (mat.product_dir(self.root, LEAGUE, 2025) / mat.MATCHUPS).read_text(encoding="utf-8")
        self.assertNotIn("AsOfUtc", text)
        self.assertEqual({"Season": 2025}, json.loads(text))

    def test_scope_selects_current_and_completed_seasons(self):
        with mock.patch.object(mat, "manifest", return_value={}), mock.patch.object(mat, "current_season", return_value=2026), \
                mock.patch.object(mat, "manifest_seasons", return_value=[2024, 2025, 2026]), \
                mock.patch.object(mat, "completed_seasons", return_value=[2024, 2025]):
            self.assertEqual((2026, [2026]), mat.seasons_for_scope(self.root, LEAGUE, "current"))
            self.assertEqual((2026, [2024, 2025]), mat.seasons_for_scope(self.root, LEAGUE, "history"))
            self.assertEqual((2026, [2024, 2025, 2026]), mat.seasons_for_scope(self.root, LEAGUE, "all"))

    def test_running_season_builds_current_document_and_completed_season_does_not(self):
        with mock.patch.object(mat, "resolve_matchups", return_value={}), \
                mock.patch.object(mat, "resolve_current_season_history", return_value={}), \
                mock.patch.object(mat, "resolve_historical_season", return_value={}):
            self.assertEqual({mat.MATCHUPS, mat.CONTEXT_HISTORY, mat.CURRENT}, set(mat.build_documents(self.root, LEAGUE, 2026, 2026, NOW)))
            self.assertEqual({mat.MATCHUPS, mat.CONTEXT_HISTORY}, set(mat.build_documents(self.root, LEAGUE, 2025, 2026, NOW)))
            self.assertEqual({mat.MATCHUPS}, set(mat.build_documents(self.root, LEAGUE, 2021, 2026, NOW)))

    def test_running_season_error_fails_only_with_flag(self):
        with mock.patch.object(mat, "seasons_for_scope", return_value=(2026, [2026])), \
                mock.patch.object(mat, "materialize_season", side_effect=MatchupContextError("incomplete")):
            self.assertEqual([], mat.materialize(self.root, self.root, LEAGUE, "current", NOW))
            with self.assertRaises(MatchupContextError):
                mat.materialize(self.root, self.root, LEAGUE, "current", NOW, fail_on_error=True)


if __name__ == "__main__":
    unittest.main()
