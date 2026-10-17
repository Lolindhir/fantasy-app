from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
from odds_scoped_source_preflight import source_candidate  # noqa: E402


class OddsSourcePreflightTests(unittest.TestCase):
    def test_real_source_candidate_reproduces_canonical_without_writes(self):
        odds_path = ROOT / "data-source/nfl/schedule-odds/2026.json"
        raw_path = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        before = odds_path.read_bytes(), raw_path.read_bytes()
        candidate, audit = source_candidate(ROOT, raw_path, 2026)
        original = json.loads(odds_path.read_text(encoding="utf-8"))
        self.assertEqual(candidate, original)
        self.assertEqual(audit["seasonCount"], 28)
        self.assertEqual(len(candidate["Games"]), 272)
        self.assertEqual(before, (odds_path.read_bytes(), raw_path.read_bytes()))

    def test_price_only_movement_is_derived_noop(self):
        raw = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        first, _ = source_candidate(ROOT, raw, 2026)
        with tempfile.TemporaryDirectory() as tmp:
            second_path = Path(tmp) / "games.csv"
            rows = list(csv.DictReader(raw.open(encoding="utf-8", newline="")))
            game = next(row for row in rows if row["game_id"].startswith("2026_"))
            game["home_moneyline"] = "9999"
            with second_path.open("w", encoding="utf-8", newline="") as writer_file:
                writer = csv.DictWriter(writer_file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            second, _ = source_candidate(ROOT, second_path, 2026)
            before = {g["GameID"]: (g["SpreadLine"], g["TotalLine"]) for g in first["Games"]}
            after = {g["GameID"]: (g["SpreadLine"], g["TotalLine"]) for g in second["Games"]}
            self.assertEqual(before, after)
            self.assertNotEqual(first, second, "Source price evidence did change")

    def test_duplicate_upstream_game_fails_closed(self):
        raw = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "duplicate.csv"
            original = raw.read_text(encoding="utf-8")
            duplicated = next(line for line in original.splitlines() if line.startswith("2026_"))
            copy.write_text(original + duplicated + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate upstream GameID"):
                source_candidate(ROOT, copy, 2026)


if __name__ == "__main__":
    unittest.main()
