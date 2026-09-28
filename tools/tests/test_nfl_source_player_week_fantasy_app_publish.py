from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from player_week_fantasy_app_publish import (  # noqa: E402
    build_app_player_week_fantasy_read_model,
    write_json_if_changed,
)


def projection(points: float | None = 10.5) -> dict:
    if points is None:
        return {
            "Status": "insufficient-history",
            "Points": None,
            "PredictionRange": None,
            "RangeQuality": "unavailable",
            "HistoryGames": 0,
            "ParticipationCondition": "conditional-on-participation",
            "AvailabilityAdjustmentApplied": False,
            "PointModel": "V4-C",
            "IntervalModel": "V4-C-PI1",
        }
    return {
        "Status": "available",
        "Points": points,
        "PredictionRange": {
            "Level": 0.9,
            "Lower": points - 5,
            "Upper": points + 8,
        },
        "RangeQuality": "limited-history-fallback",
        "HistoryGames": 4,
        "ParticipationCondition": "conditional-on-participation",
        "AvailabilityAdjustmentApplied": False,
        "PointModel": "V4-C",
        "IntervalModel": "V4-C-PI1",
    }


def source_contract() -> dict:
    return {
        "ContractVersion": 1,
        "CanonicalLeagueID": "league-a",
        "Season": 2026,
        "Week": 3,
        "ScoringProfile": {
            "Season": 2026,
            "SettingsHash": "sha256:" + ("a" * 64),
            "FingerprintVersion": 1,
            "ActiveSettingsCount": 1,
        },
        "Records": [
            {
                "CanonicalPlayerID": "NFLP-b",
                "Projection": projection(None),
                "Actual": {"Points": None, "State": "unavailable"},
            },
            {
                "CanonicalPlayerID": "NFLP-a",
                "Projection": projection(),
                "Actual": {"Points": None, "State": "unavailable"},
            },
        ],
    }


class PlayerWeekFantasyAppPublicationTests(unittest.TestCase):
    def test_publication_preserves_all_canonical_rows_and_exposes_nullable_app_identity(self) -> None:
        result = build_app_player_week_fantasy_read_model(
            source_contract(),
            {
                "Players": [
                    {"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "100"}},
                    {"CanonicalPlayerID": "NFLP-b", "IDs": {}},
                ]
            },
            {
                "Records": [
                    {
                        "CanonicalPlayerID": "NFLP-a",
                        "SleeperPlayerID": "100",
                    }
                ]
            },
        )

        self.assertEqual(result["SchemaVersion"], 1)
        self.assertEqual(
            result["IdentityCoverage"],
            {
                "Provider": "Sleeper",
                "ResolvedRecordCount": 1,
                "UnavailableRecordCount": 1,
            },
        )
        self.assertEqual(
            [record["CanonicalPlayerID"] for record in result["Records"]],
            ["NFLP-a", "NFLP-b"],
        )
        self.assertEqual(result["Records"][0]["PlayerID"], "100")
        self.assertIsNone(result["Records"][1]["PlayerID"])
        self.assertEqual(result["Records"][0]["Projection"]["Points"], 10.5)

    def test_cross_source_sleeper_identity_disagreement_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity disagreement"):
            build_app_player_week_fantasy_read_model(
                source_contract(),
                {
                    "Players": [
                        {"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "100"}},
                        {"CanonicalPlayerID": "NFLP-b", "IDs": {}},
                    ]
                },
                {
                    "Records": [
                        {
                            "CanonicalPlayerID": "NFLP-a",
                            "SleeperPlayerID": "101",
                        }
                    ]
                },
            )

    def test_duplicate_active_sleeper_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate active Sleeper identity link"):
            build_app_player_week_fantasy_read_model(
                source_contract(),
                {
                    "Players": [
                        {"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "100"}},
                        {"CanonicalPlayerID": "NFLP-b", "IDs": {"Sleeper": "100"}},
                    ]
                },
                {
                    "Records": [
                        {
                            "CanonicalPlayerID": "NFLP-a",
                            "SleeperPlayerID": "100",
                        }
                    ]
                },
            )

    def test_publication_write_is_semantic_no_op_for_identical_payload(self) -> None:
        payload = {
            "SchemaVersion": 1,
            "Records": [{"CanonicalPlayerID": "NFLP-a", "PlayerID": "100"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PlayerWeekFantasy.json"
            self.assertTrue(write_json_if_changed(path, payload))
            first = path.read_text(encoding="utf-8")
            self.assertFalse(write_json_if_changed(path, payload))
            self.assertEqual(path.read_text(encoding="utf-8"), first)


if __name__ == "__main__":
    unittest.main()
