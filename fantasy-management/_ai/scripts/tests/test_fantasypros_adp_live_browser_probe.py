"""Temporary PR-only live probe for the FantasyPros ADP browser fallback.

This file is removed after the branch has proven the current live pages on an
actual GitHub-hosted runner. It never writes repository data.
"""

import importlib.util
import os
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FETCHER_PATH = SCRIPT_DIR / "fetch_fantasypros_adp.py"
BROWSER_PATH = SCRIPT_DIR / "fantasypros_adp_browser.py"
BRANCH = "agent/fix-fantasypros-adp-browser-render"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


fetcher = load_module("fantasypros_adp_live_probe_fetcher", FETCHER_PATH)
browser = load_module("fantasypros_adp_live_probe_browser", BROWSER_PATH)


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("GITHUB_HEAD_REF") == BRANCH,
    "temporary live probe runs only on its dedicated pull-request branch",
)
class FantasyProsAdpLiveBrowserProbe(unittest.TestCase):
    def test_current_public_adp_pages_render_and_parse(self):
        season = datetime.now(timezone.utc).year
        results = []
        for index, (key, config) in enumerate(fetcher.FORMAT_CONFIGS.items()):
            if index:
                time.sleep(5)
            url = fetcher.build_source_url(config, season)
            html, browser_metadata = browser.render_adp_page_with_browser(
                url,
                timeout=45,
                virtual_time_budget_ms=30_000,
            )
            rows, diagnostics, raw = fetcher.parse_adp_page(
                html,
                config,
                season=season,
                source_url=url,
                extraction_method="temporary_pr_live_browser_probe",
                ranking_fetch_url=url,
            )
            self.assertGreaterEqual(len(rows), config["min_rows"])
            self.assertTrue(diagnostics["active_source_ids"])
            self.assertEqual(
                "temporary_pr_live_browser_probe",
                raw["extraction_method"],
            )
            results.append(
                {
                    "format": key,
                    "rows": len(rows),
                    "sources": diagnostics["active_source_ids"],
                    "browser": browser_metadata,
                }
            )
        print(f"FantasyPros ADP live browser probe: {results}")


if __name__ == "__main__":
    unittest.main()
