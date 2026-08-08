import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "fetch_cbs_sports_kicker_projections.py"
spec = importlib.util.spec_from_file_location("cbs_kicker_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def fixture(*, changed=False, duplicate=False, next_page=False, wrong_title=False):
    rows = []
    for index in range(24):
        player_id = 2815718 if index == 0 else 3000000 + index
        if duplicate and index == 1:
            player_id = 2815718
        gp = 17
        if index == 23:
            fgm = fga = xpm = xpa = points = 0
            fppg = 0.0
            values = ["—"] * 10
        else:
            fgm = max(10, 39 - index)
            fga = fgm + 4
            xpm = max(20, 50 - index)
            xpa = xpm + 1
            points = fgm * 3 + xpm - (1 if changed and index == 0 else 0)
            fppg = round(points / gp, 1)
            made_bins = [0.3, 8.0, 10.0, 11.0, max(0.0, fgm - 29.3)]
            attempt_bins = [0.3, 8.5, 10.5, 11.5, max(0.0, fgm - 27.3)]
            values = []
            for made, attempt in zip(made_bins, attempt_bins):
                values.extend([made, attempt])
        rows.append(
            '<tr>'
            f'<td><a href="/nfl/players/{player_id}/kicker-{index}/">K. {index}</a> '
            f'<a href="/nfl/players/{player_id}/kicker-{index}/">Kicker Player {index}</a> K DAL</td>'
            f'<td>{gp}</td><td>{fgm}</td><td>{fga}</td><td>—</td>'
            + ''.join(f'<td>{value}</td>' for value in values)
            + f'<td>{xpm}</td><td>{xpa}</td><td>{points}</td><td>{fppg}</td></tr>'
        )
    title = (
        '2026 Projections Fantasy Football Running Back Stats'
        if wrong_title
        else '2026 Projections Fantasy Football Kicker Stats'
    )
    next_link = '<a href="?page=2">Next Page</a>' if next_page else ''
    headers = (
        'Games Played Field Goals Made Field Goal Attempts Longest Field Goal '
        'Field Goals 1-19 Yards Field Goals 1-19 Yard Attempts '
        'Field Goals 20-29 Yards Field Goals 20-29 Yard Attempts '
        'Field Goals 30-39 Yards Field Goals 30-39 Yard Attempts '
        'Field Goals 40-49 Yards Field Goals 40-49 Yard Attempts '
        'Field Goals 50+ Yards Field Goals 50+ Yards Attempts '
        'Extra Points Made Extra Points Attempted Fantasy Points Fantasy Points Per Game'
    )
    return (
        f'<html><body><h1>{title}</h1><div>Non-PPR</div><div>{headers}</div>'
        f'<table>{"".join(rows)}</table>{next_link}</body></html>'
    )


class CBSSportsTests(unittest.TestCase):
    def fetched(self):
        return datetime(2026, 8, 8, 20, 0, tzinfo=timezone.utc)

    def test_parses_complete_kicker_projection_table(self):
        rows, diagnostics = module.parse_projection_html(
            fixture(), season=2026, fetched_at=self.fetched()
        )
        self.assertEqual(24, len(rows))
        self.assertEqual('K', rows[0]['position'])
        self.assertEqual(1, rows[0]['Rank'])
        self.assertEqual('2815718', rows[0]['source_player_id'])
        self.assertEqual('', rows[0]['longest_field_goal'])
        self.assertEqual(0, rows[-1]['fg_50_plus_attempts'])
        self.assertFalse(diagnostics['source_update_timestamp_available'])

    def test_rejects_wrong_identity_duplicate_pagination_and_bad_stats(self):
        with self.assertRaises(module.CBSSportsProjectionError):
            module.parse_projection_html(
                fixture(wrong_title=True), season=2026, fetched_at=self.fetched()
            )
        with self.assertRaisesRegex(module.CBSSportsProjectionError, 'Duplicate'):
            module.parse_projection_html(
                fixture(duplicate=True), season=2026, fetched_at=self.fetched()
            )
        with self.assertRaisesRegex(module.CBSSportsProjectionError, 'paginated'):
            module.parse_projection_html(
                fixture(next_page=True), season=2026, fetched_at=self.fetched()
            )
        bad = fixture().replace('<td>39</td><td>43</td>', '<td>44</td><td>43</td>', 1)
        with self.assertRaisesRegex(module.CBSSportsProjectionError, 'FGM exceeds FGA'):
            module.parse_projection_html(bad, season=2026, fetched_at=self.fetched())

    def test_latest_raw_and_skip_unchanged(self):
        rows, diagnostics = module.parse_projection_html(
            fixture(), season=2026, fetched_at=self.fetched()
        )
        with tempfile.TemporaryDirectory() as directory:
            kwargs = dict(
                repo_root=Path(directory),
                rows=rows,
                html=fixture(),
                diagnostics=diagnostics,
                source_url_value=module.source_url(2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            paths, created = module.write_projection(fetched_at=self.fetched(), **kwargs)
            self.assertTrue(created)
            self.assertEqual(4, len(paths))
            paths, created = module.write_projection(
                fetched_at=datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc), **kwargs
            )
            self.assertFalse(created)
            self.assertEqual(2, len(paths))
            latest = json.loads(
                (module.ranking_root(Path(directory)) / 'latest.json').read_text()
            )
            self.assertEqual('2026-08-08', latest['snapshot_date'])
            self.assertFalse(latest['source_update_timestamp_available'])

    def test_changed_projection_creates_snapshot(self):
        rows, diagnostics = module.parse_projection_html(
            fixture(), season=2026, fetched_at=self.fetched()
        )
        with tempfile.TemporaryDirectory() as directory:
            module.write_projection(
                repo_root=Path(directory),
                rows=rows,
                html=fixture(),
                diagnostics=diagnostics,
                fetched_at=self.fetched(),
                source_url_value=module.source_url(2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            rows2, diagnostics2 = module.parse_projection_html(
                fixture(changed=True), season=2026, fetched_at=self.fetched()
            )
            _, created = module.write_projection(
                repo_root=Path(directory),
                rows=rows2,
                html=fixture(changed=True),
                diagnostics=diagnostics2,
                fetched_at=datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc),
                source_url_value=module.source_url(2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            self.assertTrue(created)


if __name__ == '__main__':
    unittest.main()
