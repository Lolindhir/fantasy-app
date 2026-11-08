"""Odds observer checkout profile hides no input (Issue #1263, G5 AP3a).

The profile is parsed from odds-refresh.yml. The observer logic (registry, canonical schedules and
schedule-odds, tools code) runs once in a tree that contains only the sparse profile and once in a tree with
the complete data roots; both must return the same observation plan. State is persisted through the GitHub API
(isolated CAS branch), never through the checkout.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import odds_observation  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "odds-refresh.yml"
OBSERVED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def observer_profile() -> list[str]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    step = next(s for s in doc["jobs"]["observe"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert step["with"]["filter"] == "blob:none"
    assert step["with"]["sparse-checkout-cone-mode"] is False
    return [p.strip() for p in step["with"]["sparse-checkout"].splitlines() if p.strip()]


def link_tree(base: Path, entries: list[str]) -> Path:
    base.mkdir(parents=True)
    for entry in entries:
        rel = entry.strip("/")
        source = ROOT / rel
        if source.exists():
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(source, base / rel)
    return base


def latest_odds_season() -> int:
    seasons = sorted(int(p.stem) for p in (ROOT / "data-source/nfl/schedule-odds").glob("*.json"))
    return seasons[-1]


def write_upstream_csv(path: Path, season: int) -> None:
    odds = json.loads((ROOT / f"data-source/nfl/schedule-odds/{season}.json").read_text(encoding="utf-8"))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "spread_line", "total_line"])
        writer.writeheader()
        for game in odds["Games"]:
            writer.writerow({"game_id": game["GameID"], "spread_line": game["SpreadLine"], "total_line": game["TotalLine"]})


def observe(tree: Path, season: int, csv_path: Path) -> dict:
    # fetch_registered_odds reads the registry from the tree; only the download itself is replaced
    def fake_download(_url: str, destination: Path) -> None:
        destination.write_bytes(csv_path.read_bytes())

    with mock.patch.object(odds_observation, "download", fake_download):
        destination = tree / "upstream.csv"
        odds_observation.fetch_registered_odds(tree, destination)
        return odds_observation.run(tree, season=season, upstream_csv=destination, observed_at=OBSERVED_AT)


class OddsObserverSparseProfileTest(unittest.TestCase):
    def test_profile_is_exactly_the_observer_inputs(self) -> None:
        self.assertEqual(
            ["/tools/", "/data-source/registry.json", "/data-source/nfl/schedules/", "/data-source/nfl/schedule-odds/"],
            observer_profile(),
        )

    def test_observer_never_persists_through_the_checkout(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("git push", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("odds_state_publish.py", text)

    def test_plan_is_identical_with_and_without_the_excluded_data(self) -> None:
        season = latest_odds_season()
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "games.csv"
            write_upstream_csv(csv_path, season)
            sparse = link_tree(Path(tmp) / "sparse", observer_profile())
            full = link_tree(Path(tmp) / "full", ["/tools/", "/data-source/", "/data-meta/", "/public/data/"])
            self.assertFalse((sparse / "data-source" / "nfl" / "player-stats").exists())
            self.assertTrue((full / "data-source" / "nfl" / "player-stats").exists())
            self.assertEqual(observe(full, season, csv_path), observe(sparse, season, csv_path))


if __name__ == "__main__":
    unittest.main()
