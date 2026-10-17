from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT
from nfl_odds_observe import observe

NOW = datetime(2026, 10, 17, 16, 20, tzinfo=timezone.utc)
IDS = ("2026_07_CAR_PHI", "2026_07_HOU_JAX")


def setup_fixture(root: Path):
    base = root / DATA_SOURCE_ROOT
    payloads = {
        "nfl/schedules/2026.json": {
            "Season": 2026, "Games": [{"GameID": game_id} for game_id in IDS],
        },
        "nfl/schedule-odds/2026.json": {
            "Season": 2026, "SourceDataset": "nflverse.schedule-odds",
            "Games": [
                {"GameID": game_id, "SpreadLine": 3.5, "TotalLine": 44.5,
                 "HomeMoneyline": -180, "OverOdds": -110}
                for game_id in IDS
            ],
        },
        "providers/nflverse/schedule-odds/metadata.json": {
            "retrievedAtUtc": (NOW - timedelta(hours=12)).isoformat(),
        },
    }
    for path, payload in payloads.items():
        target = base / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
    candidate = root / "candidate.csv"
    write_candidate(candidate, [{"game_id": game_id, "spread_line": 3.5,
                                 "total_line": 44.5} for game_id in IDS])
    return candidate


def write_candidate(target: Path, rows: list[dict]) -> None:
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, ["game_id", "spread_line", "total_line", "home_moneyline"]
        )
        writer.writeheader()
        writer.writerows(rows)


class NflOddsObserveTests(unittest.TestCase):
    def test_noop_uses_actual_canonical_games(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = setup_fixture(root)
            result = observe(root, 2026, source, NOW)
            self.assertEqual(result["GameCount"], 2)
            self.assertEqual(result["PublishableGameCount"], 0)
            self.assertFalse(result["WriteAttempted"])
            self.assertFalse((root / "data-derived").exists())

    def test_only_small_delta_waits_for_batch_even_with_very_old_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = setup_fixture(root)
            write_candidate(source, [
                {"game_id": IDS[0], "spread_line": 4, "total_line": 44.5},
                {"game_id": IDS[1], "spread_line": 3.5, "total_line": 45.5},
            ])
            self.assertEqual(observe(root, 2026, source, NOW)["PublishableGameCount"], 0)
            due = observe(root, 2026, source, NOW, batch_window_due=True)
            self.assertEqual(due["PublishableGameCount"], 2)
            self.assertEqual(due["Reasons"]["scheduled_batch_window"], 2)

    def test_major_and_availability_changes_publish_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = setup_fixture(root)
            write_candidate(source, [
                {"game_id": IDS[0], "spread_line": 4.5, "total_line": 44.5},
                {"game_id": IDS[1], "spread_line": None, "total_line": 44.5},
            ])
            result = observe(root, 2026, source, NOW)
            self.assertEqual(result["PublishableGameCount"], 2)
            self.assertEqual(result["Reasons"]["large_cumulative_change"], 1)
            self.assertEqual(result["Reasons"]["line_availability_changed"], 1)

    def test_invalid_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = setup_fixture(root)
            for rows in (
                [{"game_id": IDS[0], "spread_line": 3.5, "total_line": 44.5}],
                [{"game_id": IDS[0], "spread_line": 3.5, "total_line": 44.5},
                 {"game_id": IDS[0], "spread_line": 3.5, "total_line": 44.5}],
                [{"game_id": IDS[0], "spread_line": "nan", "total_line": 44.5},
                 {"game_id": IDS[1], "spread_line": 3.5, "total_line": 44.5}],
                [{"game_id": IDS[0], "spread_line": 3.5, "total_line": 44.5},
                 {"game_id": "2026_07_UNKNOWN_GAME", "spread_line": 3.5, "total_line": 44.5}],
            ):
                with self.subTest(rows=rows):
                    write_candidate(source, rows)
                    with self.assertRaises(ValueError):
                        observe(root, 2026, source, NOW)

    def test_real_2026_canonical_raw_projection_is_noop(self):
        source = ROOT / DATA_SOURCE_ROOT
        odds = source / "providers/nflverse/schedule-odds/raw-latest.csv"
        metadata = json.loads(
            (source / "providers/nflverse/schedule-odds/metadata.json").read_text(encoding="utf-8")
        )
        at = datetime.fromisoformat(metadata["retrievedAtUtc"].replace("Z", "+00:00"))
        result = observe(ROOT, 2026, odds, at + timedelta(minutes=1), batch_window_due=True)
        self.assertEqual(result["GameCount"], 272)
        self.assertEqual(result["PublishableGameCount"], 0)
        self.assertEqual(result["Reasons"]["no_relevant_change"], 272)


if __name__ == "__main__":
    unittest.main()
