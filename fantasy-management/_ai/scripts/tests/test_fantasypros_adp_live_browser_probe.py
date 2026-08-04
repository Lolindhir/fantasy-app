"""Temporary PR-only diagnostic probe for live FantasyPros ADP rendering."""

import importlib.util
import json
import os
import re
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


def compact(value):
    return re.sub(r"\s+", " ", value).strip()


def marker_diagnostics(html):
    markers = [
        "ecrData",
        "adpData",
        "player_name",
        "rank_ave",
        "rank_ecr",
        "rank_espn",
        '"players"',
        "DataTable",
        "__NEXT_DATA__",
        "application/json",
    ]
    result = {}
    for marker in markers:
        positions = [match.start() for match in re.finditer(re.escape(marker), html)]
        entry = {"count": len(positions)}
        if positions:
            start = max(0, positions[0] - 220)
            end = min(len(html), positions[0] + 520)
            entry["first_context"] = compact(html[start:end])
        result[marker] = entry
    return result


def table_summaries(html):
    parsed = browser.parse_tables(html)
    summaries = []
    for table in parsed.get("tables", [])[:12]:
        rows = table.get("rows", [])
        summaries.append(
            {
                "attrs": table.get("attrs", {}),
                "row_count": len(rows),
                "first_rows": [
                    [compact(str(cell.get("text", ""))) for cell in row[:20]]
                    for row in rows[:4]
                ],
            }
        )
    return summaries


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("GITHUB_HEAD_REF") == BRANCH,
    "temporary live probe runs only on its dedicated pull-request branch",
)
class FantasyProsAdpLiveBrowserProbe(unittest.TestCase):
    def test_inspect_current_ppr_browser_dom(self):
        season = datetime.now(timezone.utc).year
        config = fetcher.FORMAT_CONFIGS["ppr-overall"]
        url = fetcher.build_source_url(config, season)
        html, browser_metadata = browser.render_adp_page_with_browser(
            url,
            timeout=45,
            virtual_time_budget_ms=30_000,
        )
        script_sources = re.findall(
            r"<script[^>]+src=[\"']([^\"']+)", html, flags=re.IGNORECASE
        )[:30]
        diagnostic = {
            "browser": browser_metadata,
            "rendered_length": len(html),
            "tables": table_summaries(html),
            "markers": marker_diagnostics(html),
            "script_sources": script_sources,
        }
        self.fail(
            "FantasyPros ADP live DOM diagnostic: "
            + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)
        )


if __name__ == "__main__":
    unittest.main()
