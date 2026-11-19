"""Tests for the weekly-recaps product materializer (ADR-089, Issue #1571): layout, byte no-op and scope."""
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

import weekly_recaps_materialize as mat  # noqa: E402
from derived_data_lib.weekly_recaps import WeeklyRecapsError  # noqa: E402

LEAGUE = "test-league"


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_model_is_written_once_and_a_second_run_is_a_byte_no_op(self):
        with mock.patch.object(mat, "resolve_weekly_recaps", return_value={"Season": "2025", "Weeks": []}):
            first = mat.materialize_season(self.root, self.root, LEAGUE, 2025)
            second = mat.materialize_season(self.root, self.root, LEAGUE, 2025)
        self.assertEqual(1, first["Written"])
        self.assertEqual(0, second["Written"])
        self.assertEqual({"Season": "2025", "Weeks": []}, mat.read_model(self.root, LEAGUE, 2025))
        self.assertEqual(self.root / "weekly-recaps" / LEAGUE / "2025.json", mat.product_path(self.root, LEAGUE, 2025))

    def test_check_only_writes_nothing_and_stored_text_has_no_clock(self):
        with mock.patch.object(mat, "resolve_weekly_recaps", return_value={"Season": "2025"}):
            summary = mat.materialize_season(self.root, self.root, LEAGUE, 2025, check_only=True)
        self.assertEqual(1, summary["WouldWrite"])
        self.assertIsNone(mat.read_model(self.root, LEAGUE, 2025))
        self.assertNotIn("AsOfUtc", mat.serialize({"Season": "2025"}))
        self.assertEqual({"Season": "2025"}, json.loads(mat.serialize({"Season": "2025"})))

    def test_scope_selects_current_and_completed_seasons(self):
        with mock.patch.object(mat, "manifest", return_value={}), mock.patch.object(mat, "current_season", return_value=2026), \
                mock.patch.object(mat, "manifest_seasons", return_value=[2024, 2025, 2026]), \
                mock.patch.object(mat, "completed_seasons", return_value=[2024, 2025]):
            self.assertEqual((2026, [2026]), mat.seasons_for_scope(self.root, LEAGUE, "current"))
            self.assertEqual((2026, [2024, 2025]), mat.seasons_for_scope(self.root, LEAGUE, "history"))
            self.assertEqual((2026, [2024, 2025, 2026]), mat.seasons_for_scope(self.root, LEAGUE, "all"))

    def test_history_error_is_skipped_but_running_season_fails_with_flag(self):
        with mock.patch.object(mat, "seasons_for_scope", return_value=(2026, [2025, 2026])), \
                mock.patch.object(mat, "materialize_season", side_effect=WeeklyRecapsError("contradiction")):
            self.assertEqual([], mat.materialize(self.root, self.root, LEAGUE, "all"))
            with self.assertRaises(WeeklyRecapsError):
                mat.materialize(self.root, self.root, LEAGUE, "all", fail_on_error=True)


if __name__ == "__main__":
    unittest.main()
