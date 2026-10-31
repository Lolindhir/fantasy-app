"""Fast tests of the Players shadow comparison (ADR-076, Issue #1226). Synthetic players only."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import players_app_publish as pub  # noqa: E402


def player(pid: str, **extra):
    return {"ID": pid, "Name": f"Player {pid}", "Age": 25.5, **extra}


class DiffPlayersTests(unittest.TestCase):
    def test_identical_lists_have_no_difference(self):
        diff = pub.diff_players([player("1"), player("2")], [player("2"), player("1")])
        self.assertTrue(pub.is_identical(diff))

    def test_written_form_distinguishes_one_and_one_point_zero(self):
        diff = pub.diff_players([player("1", Total=1)], [player("1", Total=1.0)])
        self.assertEqual(diff["DifferingFields"], {"Total": 1})

    def test_missing_and_extra_players_are_listed(self):
        diff = pub.diff_players([player("1"), player("2")], [player("2"), player("3")])
        self.assertEqual(diff["OnlyPublished"], ["1"])
        self.assertEqual(diff["OnlyComputed"], ["3"])
        self.assertFalse(pub.is_identical(diff))

    def test_absent_field_differs_from_null(self):
        diff = pub.diff_players([player("1", Injury=None)], [player("1")])
        self.assertEqual(diff["DifferingFields"], {"Injury": 1})

    def test_examples_are_bounded(self):
        old = [player(str(i), Age=1) for i in range(10)]
        new = [player(str(i), Age=2) for i in range(10)]
        diff = pub.diff_players(old, new)
        self.assertEqual(diff["DifferingFields"], {"Age": 10})
        self.assertEqual(len(diff["Examples"]["Age"]), pub.MAX_EXAMPLES_PER_FIELD)


class ReferenceDateTests(unittest.TestCase):
    def test_utc_zone_takes_the_utc_date(self):
        self.assertEqual(pub.reference_date("2026-10-31T23:30:00Z", "UTC"), date(2026, 10, 31))

    def test_other_zone_can_shift_the_date(self):
        self.assertEqual(pub.reference_date("2026-10-31T23:30:00Z", "Europe/Berlin"), date(2026, 11, 1))

    def test_invalid_instant_fails(self):
        with self.assertRaises(pub.CompareError):
            pub.reference_date("not a date", "UTC")


class _Result:
    def __init__(self, players, warnings=()):
        self.players = players
        self.warnings = list(warnings)


class WriteTests(unittest.TestCase):
    NOW = datetime(2026, 11, 1, 5, 17, 30, tzinfo=timezone.utc)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "public" / "data"
        self.data.mkdir(parents=True)
        (self.data / "Timestamps.json").write_text(json.dumps({"Players": "old", "Other": "x"}), encoding="utf-8")
        patches = [
            mock.patch.object(pub, "load_league_metadata", return_value={"LeagueTimeZone": "UTC"}),
            mock.patch.object(pub.sources, "league_manifest", return_value={}),
            mock.patch.object(pub.sources, "current_season", return_value=2026),
            mock.patch.object(pub.derived_data, "materialize_player_valuation"),
        ]
        self.materialize = patches[3].start()
        for item in patches[:3]:
            item.start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        self.tmp.cleanup()

    def run_write(self, players):
        with mock.patch.object(pub, "resolve", return_value=_Result(players, ["w"])):
            return pub.write(self.root, "league", None, self.NOW)

    def test_first_write_creates_file_and_timestamp_without_backup(self):
        changed, warnings = self.run_write([player("1")])
        self.assertTrue(changed)
        self.assertEqual(warnings, ["w"])
        self.assertEqual(json.loads((self.data / "Players.json").read_text(encoding="utf-8")), [player("1")])
        stamps = json.loads((self.data / "Timestamps.json").read_text(encoding="utf-8"))
        self.assertEqual(stamps, {"Players": "2026-11-01T05:17:30Z", "Other": "x"})
        self.assertFalse((self.data / "backup").exists())
        self.materialize.assert_called_once()

    def test_unchanged_content_writes_nothing(self):
        self.run_write([player("1")])
        (self.data / "Timestamps.json").write_text(json.dumps({"Players": "kept"}), encoding="utf-8")
        changed, _ = self.run_write([player("1")])
        self.assertFalse(changed)
        self.assertEqual(json.loads((self.data / "Timestamps.json").read_text(encoding="utf-8")), {"Players": "kept"})

    def test_change_keeps_a_backup_of_the_old_file(self):
        self.run_write([player("1")])
        changed, _ = self.run_write([player("1", Total=3.5)])
        self.assertTrue(changed)
        backups = list((self.data / "backup").glob("Players_20261101_051730.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), [player("1")])

    def test_unreadable_old_file_counts_as_changed(self):
        (self.data / "Players.json").write_text("{broken", encoding="utf-8")
        changed, _ = self.run_write([player("1")])
        self.assertTrue(changed)


class WorkflowCutoverTests(unittest.TestCase):
    def test_update_players_workflow_calls_the_python_writer_only(self):
        text = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "update-players.yml").read_text(encoding="utf-8")
        self.assertIn("python3 tools/players_app_publish.py write", text)
        self.assertNotIn("RequestPlayers.ps1", text)
        self.assertNotIn("--hold-seed-players-file", text)


if __name__ == "__main__":
    unittest.main()
