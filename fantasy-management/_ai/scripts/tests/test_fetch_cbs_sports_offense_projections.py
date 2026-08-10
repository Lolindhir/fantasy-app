import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fetch_cbs_sports_offense_projections as module


def fixture(
    position: str,
    *,
    duplicate: bool = False,
    next_page: bool = False,
    source_position: str | None = None,
    negative_field: str | None = None,
) -> str:
    config = module.POSITIONS[position]
    row_position = source_position or position
    rows = []
    for index in range(24):
        player_id = 1000 + index
        if duplicate and index == 1:
            player_id = 1000
        values = []
        for field in config["fields"]:
            if negative_field == field and index == 0:
                value = -1
            elif field == "games_played":
                value = 17
            elif field == "projected_fantasy_points":
                value = 170 - index
            elif field == "projected_fantasy_points_per_game":
                value = round((170 - index) / 17, 1)
            elif field == "passer_rating":
                value = 95.5
            else:
                value = max(0, 40 - index)
            values.append(value)
        rows.append(
            f'<tr><td><a href="/nfl/players/{player_id}/x/">P. {index}</a>'
            f'<a href="/nfl/players/{player_id}/x/">Player {index}</a> {row_position} DAL</td>'
            + ''.join(f'<td>{value}</td>' for value in values)
            + '</tr>'
        )
    next_link = '<a href="?page=2">Next Page</a>' if next_page else ''
    return (
        f'<html><body><h1>2026 Projections Fantasy Football {config["label"]} Stats</h1>'
        f'<div>Non-PPR</div><table>{"".join(rows)}</table>{next_link}</body></html>'
    )


class CBSSportsOffenseTests(unittest.TestCase):
    def test_all_positions_parse(self):
        for position in module.POSITIONS:
            with self.subTest(position=position):
                rows, diagnostics = module.parse_projection_html(fixture(position), position=position, season=2026)
                self.assertEqual(24, len(rows))
                self.assertEqual(position, rows[0]["position"])
                self.assertEqual(position, rows[0]["source_position"])
                self.assertEqual(1, rows[0]["Rank"])
                self.assertFalse(diagnostics["source_update_timestamp_available"])

    def test_hybrid_pages_preserve_fullback_source_position(self):
        for position in ("RB", "TE"):
            with self.subTest(position=position):
                rows, _ = module.parse_projection_html(
                    fixture(position, source_position="FB"), position=position, season=2026
                )
                self.assertEqual(position, rows[0]["position"])
                self.assertEqual("FB", rows[0]["source_position"])
                self.assertEqual("DAL", rows[0]["team"])

    def test_signed_yardage_is_preserved_but_counts_remain_nonnegative(self):
        rows, _ = module.parse_projection_html(
            fixture("WR", negative_field="rush_yards"), position="WR", season=2026
        )
        first = next(row for row in rows if row["source_player_id"] == "1000")
        self.assertEqual(-1, first["rush_yards"])
        with self.assertRaisesRegex(module.ProjectionError, "Invalid CBS rush_attempts"):
            module.parse_projection_html(
                fixture("WR", negative_field="rush_attempts"), position="WR", season=2026
            )

    def test_position_contracts_have_distinct_source_routes_and_ranking_ids(self):
        urls = set()
        ranking_ids = set()
        for position in module.POSITIONS:
            with self.subTest(position=position):
                url = module.source_url(position, 2026)
                self.assertIn(f"/stats/{position}/2026/season/projections/nonppr/", url)
                self.assertEqual(f"redraft-{position.lower()}-preseason", module.ranking_id(position))
                urls.add(url)
                ranking_ids.add(module.ranking_id(position))
        self.assertEqual(len(module.POSITIONS), len(urls))
        self.assertEqual(len(module.POSITIONS), len(ranking_ids))

    def test_duplicate_and_pagination_fail_closed(self):
        with self.assertRaisesRegex(module.ProjectionError, "Duplicate"):
            module.parse_projection_html(fixture("QB", duplicate=True), position="QB", season=2026)
        with self.assertRaisesRegex(module.ProjectionError, "paginated"):
            module.parse_projection_html(fixture("RB", next_page=True), position="RB", season=2026)

    def test_wrong_position_identity_fails(self):
        with self.assertRaises(module.ProjectionError):
            module.parse_projection_html(fixture("WR"), position="TE", season=2026)


if __name__ == "__main__":
    unittest.main()
