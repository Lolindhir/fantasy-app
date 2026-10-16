import importlib.util
import io
import sys
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from external_source import http  # noqa: E402

SCRIPT = TOOLS_DIR / "external_source" / "fftoday_offense.py"
spec = importlib.util.spec_from_file_location("fftoday_offense_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
from external_source import season_phase as gate  # noqa: E402

REPO_ROOT = TOOLS_DIR.parent
DATASET_ID = "fftoday.projection.redraft-qb-preseason"


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


class FakeHeaders(dict):
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")
        self.headers = FakeHeaders({"Content-Type": "text/html; charset=utf-8"})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


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

    def test_position_contracts_have_distinct_source_routes_and_ranking_ids(self):
        urls = set()
        ranking_ids = set()
        for position, config in module.POSITIONS.items():
            with self.subTest(position=position):
                url = module.source_url(position, 2026)
                self.assertIn(f"PosID={config['pos_id']}", url)
                self.assertIn("Season=2026", url)
                self.assertEqual(f"redraft-{position.lower()}-preseason", module.ranking_id(position))
                urls.add(url)
                ranking_ids.add(module.ranking_id(position))
        self.assertEqual(len(module.POSITIONS), len(urls))
        self.assertEqual(len(module.POSITIONS), len(ranking_ids))

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

    def test_http_fetch_retries_403_and_honors_retry_after(self):
        error = urllib.error.HTTPError(
            "https://example.test",
            403,
            "Forbidden",
            FakeHeaders({"Retry-After": "7"}),
            io.BytesIO(b"temporarily blocked"),
        )
        with (
            patch.object(http.urllib.request, "urlopen", side_effect=[error, FakeResponse("ok")]) as urlopen,
            patch.object(http.random, "uniform", return_value=0.0),
            patch.object(http.time, "sleep") as sleep,
        ):
            body, headers = http.fetch_text_with_retry(
                "https://example.test",
                source_name="FFToday",
                retry_delays=(1.0,),
            )
        self.assertEqual("ok", body)
        self.assertEqual("text/html; charset=utf-8", headers["content_type"])
        self.assertEqual(2, urlopen.call_count)
        sleep.assert_called_once_with(7.0)

    def test_http_fetch_fails_closed_after_bounded_403_retries(self):
        errors = [
            urllib.error.HTTPError(
                "https://example.test",
                403,
                "Forbidden",
                FakeHeaders(),
                io.BytesIO(b"still blocked"),
            )
            for _ in range(2)
        ]
        with (
            patch.object(http.urllib.request, "urlopen", side_effect=errors) as urlopen,
            patch.object(http.random, "uniform", return_value=0.0),
            patch.object(http.time, "sleep"),
        ):
            with self.assertRaisesRegex(http.HttpFetchError, "status=403") as raised:
                http.fetch_text_with_retry(
                    "https://example.test",
                    source_name="FFToday",
                    retry_delays=(0.0,),
                )
        self.assertIn("body_excerpt='still blocked'", str(raised.exception))
        self.assertEqual(2, urlopen.call_count)

    def test_fetch_html_preserves_projection_error_contract(self):
        with patch.object(
            module,
            "fetch_text_with_retry",
            side_effect=http.HttpFetchError("FFToday fetch failed after 4 attempt(s): status=403"),
        ):
            with self.assertRaisesRegex(module.ProjectionError, "status=403"):
                module.fetch_html("https://example.test")

    def test_cloudflare_challenge_403_is_not_retried_or_bypassed(self):
        error = urllib.error.HTTPError(
            "https://example.test",
            403,
            "Forbidden",
            FakeHeaders(),
            io.BytesIO(b"<!DOCTYPE html><title>Just a moment...</title>"),
        )
        with (
            patch.object(http.urllib.request, "urlopen", side_effect=[error]) as urlopen,
            patch.object(http.time, "sleep") as sleep,
        ):
            with self.assertRaisesRegex(http.HttpFetchBlockedError, "access challenge") as raised:
                http.fetch_text_with_retry(
                    "https://example.test",
                    source_name="FFToday",
                    retry_delays=(1.0, 2.0, 3.0),
                )
        self.assertIn("Just a moment", str(raised.exception))
        self.assertEqual(1, urlopen.call_count)
        sleep.assert_not_called()

    def test_challenge_header_403_is_not_retried(self):
        error = urllib.error.HTTPError(
            "https://example.test",
            403,
            "Forbidden",
            FakeHeaders({"cf-mitigated": "challenge"}),
            io.BytesIO(b""),
        )
        with patch.object(http.urllib.request, "urlopen", side_effect=[error]) as urlopen:
            with self.assertRaises(http.HttpFetchBlockedError):
                http.fetch_text_with_retry("https://example.test", retry_delays=(0.0,))
        self.assertEqual(1, urlopen.call_count)

    def test_registry_season_policy_only_allows_the_preseason_phase(self):
        when = datetime(2026, 8, 10, tzinfo=timezone.utc)
        for phase, expect_skip in (
            ("pre_regular_season", False),
            ("regular_season", True),
            ("postseason", True),
            ("post_regular_season", True),
        ):
            with patch.object(gate, "resolve_nfl_season_context", return_value={"phase": phase}):
                reason = gate.skip_reason(REPO_ROOT, DATASET_ID, 2026, when)
            self.assertEqual(expect_skip, reason is not None, phase)

    def test_season_gate_skips_a_season_without_canonical_schedule(self):
        when = datetime(2026, 8, 10, tzinfo=timezone.utc)
        with patch.object(
            gate,
            "resolve_nfl_season_context",
            side_effect=gate.NflSeasonContextError("missing"),
        ):
            self.assertIn("no canonical NFL schedule", gate.skip_reason(REPO_ROOT, DATASET_ID, 2027, when))

    def test_main_skips_without_request_outside_preseason(self):
        with (
            patch.object(module, "skip_reason", return_value="phase regular_season"),
            patch.object(module, "fetch_all_pages") as fetch_all,
            patch("sys.argv", ["fftoday_offense.py", "--skip-unchanged"]),
        ):
            self.assertEqual(0, module.main())
        fetch_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
