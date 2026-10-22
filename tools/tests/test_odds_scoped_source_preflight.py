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
from odds_observation_buffer import read_upstream_lines  # noqa: E402


class OddsSourcePreflightTests(unittest.TestCase):
    def test_real_source_candidate_reproduces_canonical_without_writes(self):
        odds_path = ROOT / "data-source/nfl/schedule-odds/2026.json"
        raw_path = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        before = odds_path.read_bytes(), raw_path.read_bytes()
        candidate, audit = source_candidate(ROOT, raw_path, 2026)
        original = json.loads(odds_path.read_text(encoding="utf-8"))
        self.assertEqual(candidate["Season"], 2026)
        self.assertGreaterEqual(audit["seasonCount"], 28)
        self.assertEqual(len(candidate["Games"]), 272)
        original_by_id = {game["GameID"]: game for game in original["Games"]}
        observed = read_upstream_lines(raw_path, 2026, set(original_by_id))
        self.assertEqual({game["GameID"] for game in candidate["Games"]}, set(original_by_id))
        for game in candidate["Games"]:
            game_id = game["GameID"]
            self.assertEqual((game["GameType"], game["Week"]),
                             (original_by_id[game_id]["GameType"], original_by_id[game_id]["Week"]))
            self.assertEqual(
                (game["SpreadLine"], game["TotalLine"]),
                (observed[game_id]["SpreadLine"], observed[game_id]["TotalLine"]),
                f"{game_id}: candidate does not reflect the registered raw line source",
            )
        self.assertEqual(before, (odds_path.read_bytes(), raw_path.read_bytes()))

    def test_price_only_movement_is_derived_noop(self):
        raw = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        first, _ = source_candidate(ROOT, raw, 2026)
        with tempfile.TemporaryDirectory() as tmp:
            second_path = Path(tmp) / "games.csv"
            with raw.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            game = next(row for row in rows if row["game_id"].startswith("2026_")
                        and row["home_moneyline"].strip())
            game["home_moneyline"] = str(int(game["home_moneyline"]) + 1)
            with second_path.open("w", encoding="utf-8", newline="") as writer_file:
                writer = csv.DictWriter(writer_file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            second, _ = source_candidate(ROOT, second_path, 2026)
            before = {g["GameID"]: (g["SpreadLine"], g["TotalLine"]) for g in first["Games"]}
            after = {g["GameID"]: (g["SpreadLine"], g["TotalLine"]) for g in second["Games"]}
            self.assertEqual(before, after)
            self.assertNotEqual(first, second, "Source price evidence did change")

    def test_missing_current_season_game_fails_closed_without_writes(self):
        raw = ROOT / "data-source/providers/nflverse/schedule-odds/raw-latest.csv"
        canonical = ROOT / "data-source/nfl/schedule-odds/2026.json"
        baseline = canonical.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            incomplete = Path(tmp) / "incomplete.csv"
            with raw.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            removed = next(i for i, row in enumerate(rows)
                           if row["game_id"].startswith("2026_"))
            rows.pop(removed)
            with incomplete.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "Upstream season GameIDs differ"):
                source_candidate(ROOT, incomplete, 2026)
            self.assertEqual(canonical.read_bytes(), baseline)

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
