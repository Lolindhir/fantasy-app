from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy import scoring_settings_fingerprint  # noqa: E402
from player_week_fantasy_materialize import (  # noqa: E402
    build_player_week_fantasy_dataset,
    output_path,
)


class PlayerWeekFantasyMaterializationTests(unittest.TestCase):
    def test_current_2026_week3_materialization_is_contract_valid_and_dynamic(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        payload = build_player_week_fantasy_dataset(
            repo_root,
            league_id="nfl-reise",
            season=2026,
            week=3,
            scoring_season=2026,
        )

        league_path = repo_root / "source-data/leagues/nfl-reise/seasons/2026/league.json"
        league = json.loads(league_path.read_text(encoding="utf-8"))
        expected_hash = scoring_settings_fingerprint(league["ScoringSettings"])

        self.assertEqual(payload["ContractVersion"], 1)
        self.assertEqual(payload["CanonicalLeagueID"], "nfl-reise")
        self.assertEqual(payload["Season"], 2026)
        self.assertEqual(payload["Week"], 3)
        self.assertEqual(payload["ScoringProfile"]["SettingsHash"], expected_hash)
        self.assertEqual(payload["ProjectionModel"]["PointModel"], "V4-C")
        self.assertEqual(payload["ProjectionModel"]["IntervalModel"], "V4-C-PI1")
        self.assertEqual(payload["ProjectionModel"]["PointFitSeasons"], [2023, 2024, 2025])
        self.assertEqual(
            payload["ProjectionModel"]["IntervalCalibrationPointFitSeasons"],
            [2023, 2024],
        )
        self.assertEqual(payload["ProjectionModel"]["IntervalCalibrationSeason"], 2025)
        self.assertGreater(payload["Materialization"]["RecordCount"], 300)
        self.assertGreater(
            payload["Materialization"]["ProjectionStatusCounts"].get("available", 0),
            100,
        )
        self.assertEqual(payload["Materialization"]["RecordCount"], len(payload["Records"]))
        ids = [row["CanonicalPlayerID"] for row in payload["Records"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_initial_productive_week3_snapshot_is_persisted_and_pinned(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        path = output_path(repo_root, league_id="nfl-reise", season=2026, week=3)
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["ScoringProfile"]["SettingsHash"],
            "sha256:1495de25c56dd51836665d2643ee066a954c3c8941efb6ce518b83e71f137300",
        )
        self.assertEqual(payload["Materialization"]["RecordCount"], 820)
        self.assertEqual(
            payload["Materialization"]["ProjectionStatusCounts"],
            {"available": 642, "insufficient-history": 178},
        )
        self.assertEqual(payload["Materialization"]["ActualStateCounts"], {"unavailable": 820})
        self.assertFalse(payload["Materialization"]["ActualScoringEvidenceFinalized"])
        self.assertFalse(payload["Materialization"]["TargetWeeklyRosterFinalized"])
        self.assertEqual(payload["ProjectionModel"]["IntervalCalibrationRows"], 5724)


if __name__ == "__main__":
    unittest.main()
