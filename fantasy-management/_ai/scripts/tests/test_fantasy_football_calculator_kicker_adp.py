import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fantasy_football_calculator_kicker_adp as module


class FantasyFootballCalculatorKickerTests(unittest.TestCase):
    def payload(self):
        players = []
        for index in range(12):
            players.append({
                "player_id": 9000 + index,
                "name": f"Kicker {index}",
                "position": "PK",
                "team": "DAL",
                "adp": 120 + index,
                "adp_formatted": "16.01",
                "times_drafted": 100 - index,
                "high": 100 + index,
                "low": 150 + index,
                "stdev": 5,
                "bye": 7,
            })
        return {"status": "Success", "meta": {}, "players": players}

    def sample(self):
        return {
            "total_drafts": 300,
            "start_date": "2026-07-01",
            "end_date": "2026-07-08",
        }

    def test_parses_separate_kicker_ranking(self):
        rows, diagnostics = module.parse_kickers(self.payload(), self.sample())
        self.assertEqual(12, len(rows))
        self.assertEqual("K", rows[0]["position"])
        self.assertEqual(1, rows[0]["Rank"])
        self.assertEqual("PK", diagnostics["source_position"])
        self.assertTrue(diagnostics["reuses_ppr_all_position_payload"])

    def test_writes_and_skips_unchanged_kicker_snapshot(self):
        rows, diagnostics = module.parse_kickers(self.payload(), self.sample())
        with tempfile.TemporaryDirectory() as directory:
            kwargs = dict(
                repo_root=Path(directory),
                rows=rows,
                payload=self.payload(),
                sample=self.sample(),
                diagnostics=diagnostics,
                source_url="https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=8&year=2026&position=all",
                response_headers={},
                season=2026,
                skip_unchanged=True,
            )
            paths, created = module.write_kicker_format(
                fetched_at=datetime(2026, 8, 8, tzinfo=timezone.utc), **kwargs
            )
            self.assertTrue(created)
            self.assertEqual(4, len(paths))
            paths, created = module.write_kicker_format(
                fetched_at=datetime(2026, 8, 9, tzinfo=timezone.utc), **kwargs
            )
            self.assertFalse(created)
            self.assertEqual(2, len(paths))
            latest = json.loads(
                (module.ranking_root(Path(directory)) / "latest.json").read_text()
            )
            self.assertEqual("2026-08-08", latest["snapshot_date"])
            self.assertTrue(latest["reuses_source_payload_without_extra_request"])


if __name__ == "__main__":
    unittest.main()
