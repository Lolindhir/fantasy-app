import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from external_source import http  # noqa: E402

SCRIPT = TOOLS_DIR / "external_source" / "fftoday_kicker.py"
spec = importlib.util.spec_from_file_location("fftoday_kicker_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def fixture(*, updated="8/6/2026", changed=False, duplicate=False, next_page=False):
    rows = []
    for index in range(24):
        player_id = 18715 if index == 0 else 20000 + index
        if duplicate and index == 1:
            player_id = 18715
        fgm = 35 - (index // 4)
        fga = fgm + 4
        fg_pct = round(fgm / fga * 100, 1)
        epm = 45 - (index // 3)
        epa = epm + 1
        points = fgm * 3 + epm - (1 if changed and index == 0 else 0)
        rows.append(
            f'<tr><td></td><td><a href="/stats/players/{player_id}/Kicker_{index}">'
            f'Kicker {index}</a></td><td>DAL</td><td>14</td><td>{fgm}</td>'
            f'<td>{fga}</td><td>{fg_pct}%</td><td>{epm}</td><td>{epa}</td>'
            f'<td>{points}.0</td></tr>'
        )
    next_link = '<a href="?cur_page=2">Next Page</a>' if next_page else ""
    return (
        '<html><body><h1>Kicker Projections: 2026</h1>'
        f'<div>Regular Season, Updated: {updated}</div>'
        '<div>FFToday Half-PPR Scoring: Review Scoring</div>'
        f'<table>{"".join(rows)}</table>{next_link}</body></html>'
    )


class FFTodayTests(unittest.TestCase):
    def fetched(self):
        return datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc)

    def test_parses_complete_kicker_projection_table(self):
        rows, diagnostics = module.parse_projection_html(
            fixture(), season=2026, fetched_at=self.fetched()
        )
        self.assertEqual(24, len(rows))
        self.assertEqual("K", rows[0]["position"])
        self.assertEqual(1, rows[0]["Rank"])
        self.assertEqual("2026-08-06", diagnostics["source_updated_date"])
        self.assertEqual("18715", rows[0]["source_player_id"])

    def test_rejects_wrong_identity_stale_duplicate_and_pagination(self):
        with self.assertRaises(module.FFTodayProjectionError):
            module.parse_projection_html(
                fixture().replace("Kicker Projections: 2026", "Kicker Rankings: 2026"),
                season=2026,
                fetched_at=self.fetched(),
            )
        with self.assertRaisesRegex(module.FFTodayProjectionError, "stale"):
            module.parse_projection_html(
                fixture(updated="5/1/2026"), season=2026, fetched_at=self.fetched()
            )
        with self.assertRaisesRegex(module.FFTodayProjectionError, "Duplicate"):
            module.parse_projection_html(
                fixture(duplicate=True), season=2026, fetched_at=self.fetched()
            )
        with self.assertRaisesRegex(module.FFTodayProjectionError, "paginated"):
            module.parse_projection_html(
                fixture(next_page=True), season=2026, fetched_at=self.fetched()
            )

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
            raw = Path(directory) / "data-source" / "providers" / "fftoday" / module.RANKING_ID / "raw-latest.html"
            self.assertTrue(raw.is_file())
            snapshot_metadata = json.loads(next(p for p in paths if p.name == "metadata.json").read_text())
            self.assertEqual(2, snapshot_metadata["schema_version"])
            self.assertNotIn("actual_league_team_count", snapshot_metadata["format"])
            self.assertNotIn("actual_fixed_kicker_starters", snapshot_metadata["format"])
            paths, created = module.write_projection(
                fetched_at=datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc), **kwargs
            )
            self.assertFalse(created)
            self.assertEqual(2, len(paths))
            latest = json.loads(
                (module.ranking_root(Path(directory)) / "latest.json").read_text()
            )
            self.assertEqual("2026-08-08", latest["snapshot_date"])

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
                fetched_at=datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc),
                source_url_value=module.source_url(2026),
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            self.assertTrue(created)

    def test_fetch_html_preserves_kicker_error_contract(self):
        with patch.object(
            module,
            "fetch_text_with_retry",
            side_effect=http.HttpFetchError("FFToday fetch failed after 4 attempt(s): status=403"),
        ):
            with self.assertRaisesRegex(module.FFTodayProjectionError, "status=403"):
                module.fetch_html("https://example.test", 30)

    def test_main_skips_without_request_outside_preseason(self):
        with (
            patch.object(module, "skip_reason", return_value="phase regular_season"),
            patch.object(module, "fetch_html") as fetch_html,
        ):
            self.assertEqual(0, module.main(["--season", "2026", "--dry-run"]))
        fetch_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
