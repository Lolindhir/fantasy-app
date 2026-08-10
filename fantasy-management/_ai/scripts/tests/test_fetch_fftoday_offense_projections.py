import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fetch_fftoday_offense_projections as module


def fixture(position: str, *, start: int = 0, next_page: bool = False, updated: str = "8/6/2026") -> str:
    config = module.POSITIONS[position]
    rows = []
    for index in range(start, start + 24):
        values = []
        for field in config["fields"]:
            if field == "bye":
                value = 7
            elif field == "projected_fantasy_points":
                value = 300 - index
            else:
                value = max(0, 100 - index)
            values.append(value)
        rows.append(
            f'<tr><td><a href="/stats/players/{2000 + index}/x/">Player {index}</a></td>'
            '<td>DAL</td>'
            + ''.join(f'<td>{value}</td>' for value in values)
            + '</tr>'
        )
    next_link = '<a href="?cur_page=1">Next Page</a>' if next_page else ''
    return (
        f'<html><body><h1>{config["label"]} Projections: 2026</h1>'
        f'<div>Regular Season, Updated: {updated}</div>'
        f'<table>{"".join(rows)}</table>{next_link}</body></html>'
    )


class FFTodayOffenseTests(unittest.TestCase):
    def fetched(self):
        return datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc)

    def test_all_positions_parse(self):
        for position in module.POSITIONS:
            with self.subTest(position=position):
                rows, diagnostics, next_href = module.parse_page(
                    fixture(position), position=position, season=2026, fetched_at=self.fetched()
                )
                self.assertEqual(24, len(rows))
                self.assertEqual(position, rows[0]["position"])
                self.assertEqual("2026-08-06", diagnostics["source_updated_date"])
                self.assertIsNone(next_href)

    def test_next_page_is_discovered(self):
        _, _, next_href = module.parse_page(
            fixture("TE", next_page=True), position="TE", season=2026, fetched_at=self.fetched()
        )
        self.assertEqual("?cur_page=1", next_href)

    def test_wrong_identity_and_stale_data_fail(self):
        with self.assertRaises(module.ProjectionError):
            module.parse_page(fixture("QB"), position="RB", season=2026, fetched_at=self.fetched())
        with self.assertRaisesRegex(module.ProjectionError, "stale"):
            module.parse_page(
                fixture("QB", updated="5/1/2026"), position="QB", season=2026, fetched_at=self.fetched()
            )


if __name__ == "__main__":
    unittest.main()
