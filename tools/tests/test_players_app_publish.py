"""Fast tests of the Players shadow comparison (ADR-076, Issue #1226). Synthetic players only."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
