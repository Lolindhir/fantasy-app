from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy_materialize import (  # noqa: E402
    build_player_week_fantasy_dataset,
)


class PlayerWeekFantasyMaterializationCaptureTests(unittest.TestCase):
    def test_capture_current_2026_week3_dataset_from_real_repo(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        payload = build_player_week_fantasy_dataset(
            repo_root,
            league_id="nfl-reise",
            season=2026,
            week=3,
            scoring_season=2026,
        )

        self.assertEqual(payload["ContractVersion"], 1)
        self.assertEqual(payload["CanonicalLeagueID"], "nfl-reise")
        self.assertEqual(payload["Season"], 2026)
        self.assertEqual(payload["Week"], 3)
        self.assertEqual(
            payload["ProjectionModel"]["PointFitSeasons"],
            [2023, 2024, 2025],
        )
        self.assertEqual(
            payload["ProjectionModel"]["IntervalCalibrationSeason"],
            2025,
        )
        self.assertGreater(payload["Materialization"]["RecordCount"], 300)
        self.assertGreater(
            payload["Materialization"]["ProjectionStatusCounts"].get("available", 0),
            100,
        )

        compact = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        chunk_size = 6000
        for index, start in enumerate(range(0, len(compact), chunk_size)):
            print(f"PWF_CAPTURE_CHUNK_{index:03d}={compact[start:start + chunk_size]}")
        self.fail("intentional one-time capture gate: persist generated dataset, then replace this test")


if __name__ == "__main__":
    unittest.main()
