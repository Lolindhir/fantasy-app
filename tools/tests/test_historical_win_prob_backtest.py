"""Summary arithmetic of the win-prob backtest (Issue #1443); synthetic rows only."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from historical_win_prob_backtest import summarize  # noqa: E402


def row(chance, won, upset=False):
    return {"Season": 2026, "Week": 1, "Status": "scored", "FavoriteChance": chance, "FavoriteWon": won, "Upset": upset}


class SummarizeTests(unittest.TestCase):
    def test_brier_win_rate_and_bands(self) -> None:
        result = summarize([row(0.8, True), row(0.6, False, upset=True), {"Season": 2026, "Week": 1, "Status": "unknown-chance"}])
        self.assertEqual(3, result["Matchups"])
        self.assertEqual(2, result["Scored"])
        self.assertEqual(1, result["UnknownChance"])
        self.assertEqual(0.5, result["FavoriteWinRate"])
        self.assertEqual(round(((0.2 ** 2) + (0.6 ** 2)) / 2, 4), result["Brier"])
        self.assertEqual({"60-70", "80-100"}, set(result["Bands"]))

    def test_no_scored_rows(self) -> None:
        self.assertEqual({"Matchups": 0, "Scored": 0}, summarize([]))


if __name__ == "__main__":
    unittest.main()
