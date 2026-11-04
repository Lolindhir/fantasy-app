from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import Counter
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
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.current_payload = build_player_week_fantasy_dataset(
            cls.repo_root,
            league_id="nfl-reise",
            season=2026,
            week=3,
            scoring_season=2026,
        )

    def test_current_2026_week3_materialization_is_contract_valid_and_dynamic(self) -> None:
        repo_root = self.repo_root
        payload = self.current_payload

        league_path = repo_root / "data-source/leagues/nfl-reise/seasons/2026/league.json"
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

    def _assert_persisted_week3_integrity(self, payload: dict) -> None:
        self.assertEqual(payload["ContractVersion"], 1)
        self.assertEqual(payload["CanonicalLeagueID"], "nfl-reise")
        self.assertEqual((payload["Season"], payload["Week"]), (2026, 3))
        self.assertEqual(
            payload["ScoringProfile"]["SettingsHash"],
            "sha256:1495de25c56dd51836665d2643ee066a954c3c8941efb6ce518b83e71f137300",
        )
        materialization = payload["Materialization"]
        records = payload["Records"]
        self.assertEqual(materialization["RecordCount"], 820)
        self.assertEqual(materialization["RecordCount"], len(records))
        player_ids = [row["CanonicalPlayerID"] for row in records]
        self.assertEqual(player_ids, sorted(player_ids))
        self.assertEqual(len(player_ids), len(set(player_ids)))
        self.assertTrue(all(isinstance(player_id, str) and player_id for player_id in player_ids))

        projection_counts = dict(sorted(Counter(row["Projection"]["Status"] for row in records).items()))
        self.assertEqual(set(projection_counts), {"available", "insufficient-history"})
        self.assertEqual(sum(projection_counts.values()), materialization["RecordCount"])
        self.assertEqual(materialization["ProjectionStatusCounts"], projection_counts)
        actual_counts = dict(sorted(Counter(row["Actual"]["State"] for row in records).items()))
        self.assertEqual(sum(actual_counts.values()), materialization["RecordCount"])
        self.assertEqual(materialization["ActualStateCounts"], actual_counts)
        self.assertEqual(actual_counts, {"final": 820})
        self.assertTrue(materialization["ActualScoringEvidenceFinalized"])
        self.assertTrue(all(row["Actual"]["Points"] is not None for row in records))
        self.assertFalse(materialization["TargetWeeklyRosterFinalized"])
        self.assertEqual(materialization["TargetRosterSourceWeek"], 3)
        self.assertFalse(materialization["TargetRosterProvisional"])

        model = payload["ProjectionModel"]
        expected_model = self.current_payload["ProjectionModel"]
        for key in (
            "PointModel", "IntervalModel", "PointFitSeasons",
            "IntervalCalibrationSeason", "IntervalCalibrationPointFitSeasons",
            "IntervalLevels",
        ):
            self.assertEqual(model[key], expected_model[key], key)
        # The historical fit is a reproducible computation, not a fixed
        # snapshot count. Assert exact parity with the current canonical fit,
        # including type/shape, rather than pinning 5724 or accepting >0.
        self.assertIs(type(model["IntervalCalibrationRows"]), int)
        self.assertGreater(model["IntervalCalibrationRows"], 0)
        self.assertEqual(
            model["IntervalCalibrationRows"],
            expected_model["IntervalCalibrationRows"],
        )
        self.assertEqual(model["IntervalLevels"], [0.5, 0.8, 0.9])

    def test_persisted_week3_snapshot_remains_valid_across_historical_backfill(self) -> None:
        path = output_path(self.repo_root, league_id="nfl-reise", season=2026, week=3)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._assert_persisted_week3_integrity(payload)

    def test_persisted_week3_rejects_forged_evidence_and_metadata(self) -> None:
        path = output_path(self.repo_root, league_id="nfl-reise", season=2026, week=3)
        baseline = json.loads(path.read_text(encoding="utf-8"))
        self._assert_persisted_week3_integrity(baseline)
        mutations = {
            "wrong projection count": lambda p: p["Materialization"]["ProjectionStatusCounts"].update(
                {"available": p["Materialization"]["ProjectionStatusCounts"]["available"] + 1}
            ),
            "missing player": lambda p: p["Records"].pop(),
            "duplicate player": lambda p: p["Records"].__setitem__(
                1, copy.deepcopy(p["Records"][0])
            ),
            "invalid calibration shape": lambda p: p["ProjectionModel"].update(
                {"IntervalCalibrationRows": "5731"}
            ),
            "invalid calibration value": lambda p: p["ProjectionModel"].update(
                {"IntervalCalibrationRows": p["ProjectionModel"]["IntervalCalibrationRows"] + 1}
            ),
            "wrong calibration season": lambda p: p["ProjectionModel"].update(
                {"IntervalCalibrationSeason": 2024}
            ),
            "wrong finality": lambda p: p["Materialization"].update(
                {"ActualScoringEvidenceFinalized": False}
            ),
            "forged actual counts": lambda p: p["Materialization"].update(
                {"ActualStateCounts": {"final": 819, "unavailable": 1}}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                broken = copy.deepcopy(baseline)
                mutate(broken)
                with self.assertRaises(AssertionError):
                    self._assert_persisted_week3_integrity(broken)


if __name__ == "__main__":
    unittest.main()
