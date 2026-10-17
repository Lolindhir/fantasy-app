"""Real canonical Source acceptance / empty Derived-root restore for NFLGame (#1077).

This executes under normal CI on the repository's checked-in season partitions,
not on synthetic hand-crafted rows. Never writes into tracked data-derived.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from nfl_games_materialize import discover_seasons, materialize  # noqa: E402


class RealNflGamesRestoreTests(unittest.TestCase):
    def test_all_canonical_seasons_restore_from_clean_derived_root(self) -> None:
        seasons = discover_seasons(ROOT)
        self.assertTrue(seasons, "No canonical NFL seasons")
        with tempfile.TemporaryDirectory(prefix="nfl-games-restore-") as temp:
            empty_root = Path(temp)
            for season in seasons:
                with self.subTest(season=season):
                    source = ROOT / DATA_SOURCE_ROOT / "nfl"
                    inputs = [
                        json.loads((source / folder / f"{season}.json").read_text(encoding="utf-8"))
                        for folder in ("schedules", "game-finality", "schedule-odds")
                    ]
                    self.assertEqual(len(inputs[0]["Games"]), len(inputs[1]["Games"]))
                    self.assertEqual(len(inputs[0]["Games"]), len(inputs[2]["Games"]))
                    preview = materialize(ROOT, season, out_root=empty_root)
                    self.assertTrue(preview["WouldWrite"])
                    self.assertFalse(preview["Written"])
                    written = materialize(ROOT, season, out_root=empty_root, write=True)
                    self.assertTrue(written["Written"])
                    self.assertEqual(written["GameCount"], len(inputs[0]["Games"]))
                    second = materialize(ROOT, season, out_root=empty_root, write=True)
                    self.assertTrue(second["Unchanged"], "Repeat builder must be a byte-level no-op")
                    self.assertFalse(second["Written"])
                    output = json.loads(
                        (empty_root / "nfl-games" / f"{season}.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(output["Season"], season)
                    self.assertEqual(len(output["Games"]), len(inputs[0]["Games"]))
                    self.assertTrue(all(set(g["Market"]) == {
                        "SourceDataset", "SpreadLine", "TotalLine",
                        "ImpliedAwayPoints", "ImpliedHomePoints"
                    } for g in output["Games"]))
            self.assertEqual(
                sorted(int(p.stem) for p in (empty_root / "nfl-games").glob("*.json")), seasons
            )

    def test_current_real_source_line_reconciles(self) -> None:
        season = max(discover_seasons(ROOT))
        source = ROOT / DATA_SOURCE_ROOT / "nfl"
        odds = json.loads((source / "schedule-odds" / f"{season}.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="nfl-game-check-") as temp:
            summary = materialize(ROOT, season, out_root=Path(temp), write=True)
            expected = sum(
                1 for game in odds["Games"]
                if game.get("SpreadLine") is not None and game.get("TotalLine") is not None
            )
            self.assertEqual(summary["WithCompleteMarketLines"], expected)


if __name__ == "__main__":
    unittest.main()
