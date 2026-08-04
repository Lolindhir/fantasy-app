import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FETCHER_PATH = SCRIPT_DIR / "fetch_fantasypros_adp.py"
BROWSER_PATH = SCRIPT_DIR / "fantasypros_adp_browser.py"
HELPERS_PATH = Path(__file__).with_name("test_fetch_fantasypros_adp.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


fetcher = load_module("fantasypros_adp_fetch_browser_test", FETCHER_PATH)
browser = load_module("fantasypros_adp_browser_test", BROWSER_PATH)
helpers = load_module("fantasypros_adp_existing_test_helpers", HELPERS_PATH)


class FantasyProsAdpBrowserFallbackTests(unittest.TestCase):
    def test_live_format_uses_browser_after_canonical_and_export_shells(self):
        config = fetcher.FORMAT_CONFIGS["ppr-overall"]
        export_url = fetcher.build_export_url(config, 2026, current_season=2026)
        requests = [
            (helpers.make_shell(), {"content_type": "text/html"}, config["url"]),
            (helpers.make_shell(), {"content_type": "text/html"}, export_url),
        ]
        request_calls = []
        render_calls = []

        def request(url, referer=""):
            request_calls.append((url, referer))
            return requests[len(request_calls) - 1]

        def render(url):
            render_calls.append(url)
            return helpers.make_html(), {
                "browser_executable": "/usr/bin/google-chrome",
                "headless_flag": "--headless=new",
                "virtual_time_budget_ms": 20000,
            }

        item = fetcher._prepare_live_format(
            config=config,
            season=2026,
            request=request,
            render=render,
        )

        self.assertEqual(2, len(request_calls))
        self.assertEqual([config["url"]], render_calls)
        self.assertEqual(120, len(item["rows"]))
        self.assertEqual(
            "headless_browser_dom_fallback",
            item["raw_payload"]["extraction_method"],
        )
        provenance = item["raw_payload"]["fetch_provenance"]
        self.assertEqual(config["url"], provenance["ranking_fetch_url"])
        self.assertEqual(
            "/usr/bin/google-chrome",
            provenance["response_headers"]["browser_render"]["browser_executable"],
        )
        self.assertIn("official export", item["raw_payload"]["fallback_reason"])

    def test_browser_renderer_accepts_rendered_ranking_dom(self):
        completed = subprocess.CompletedProcess(
            args=["google-chrome"],
            returncode=0,
            stdout=helpers.make_html(),
            stderr="",
        )
        with mock.patch.object(
            browser, "find_browser_executable", return_value="/usr/bin/google-chrome"
        ), mock.patch.object(browser, "_run_browser", return_value=completed) as run:
            html, metadata = browser.render_adp_page_with_browser(
                "https://www.fantasypros.com/nfl/adp/ppr-overall.php",
                timeout=30,
            )

        self.assertIn("<table id=\"adp\">", html)
        self.assertEqual("/usr/bin/google-chrome", metadata["browser_executable"])
        self.assertEqual("--headless=new", metadata["headless_flag"])
        self.assertEqual(1, metadata["attempt_count"])
        run.assert_called_once()

    def test_browser_renderer_retries_legacy_headless_then_fails_closed(self):
        completed = subprocess.CompletedProcess(
            args=["google-chrome"],
            returncode=0,
            stdout=helpers.make_shell(),
            stderr="browser diagnostic",
        )
        with mock.patch.object(
            browser, "find_browser_executable", return_value="/usr/bin/google-chrome"
        ), mock.patch.object(browser, "_run_browser", return_value=completed) as run:
            with self.assertRaisesRegex(
                fetcher.FantasyProsAdpError,
                "browser-rendered page contained no ranking table",
            ):
                browser.render_adp_page_with_browser(
                    "https://www.fantasypros.com/nfl/adp/ppr-overall.php",
                    timeout=30,
                )
        self.assertEqual(2, run.call_count)

    def test_browser_renderer_requires_installed_chrome_or_chromium(self):
        with mock.patch.object(browser.shutil, "which", return_value=None):
            with self.assertRaisesRegex(
                fetcher.FantasyProsAdpError,
                "no supported Chrome/Chromium executable found",
            ):
                browser.find_browser_executable()


if __name__ == "__main__":
    unittest.main()
