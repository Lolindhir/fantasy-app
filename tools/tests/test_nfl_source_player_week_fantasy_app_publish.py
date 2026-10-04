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

    def test_publication_exposes_display_level_and_shared_range_axis(self) -> None:
        identity = {"Players": [{"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "100"}}]}
        sleeper = {"Records": [{"CanonicalPlayerID": "NFLP-a", "SleeperPlayerID": "100"}]}
        result = build_app_player_week_fantasy_read_model(source_contract(), identity, sleeper)

        # The only available fixture projection is 10.5 with range 5.5..18.5 at level 0.9.
        self.assertEqual(
            result["Display"],
            {"RangeLevel": 0.9, "RangeAxis": {"Min": 5, "Max": 20}},
        )
        self.assertEqual(
            result["Records"][0]["Projection"]["PredictionRanges"],
            [{"Level": 0.9, "Lower": 5.5, "Upper": 18.5}],
        )
        self.assertEqual(result["Records"][1]["Projection"]["PredictionRanges"], [])

    def test_range_axis_is_absent_when_no_range_has_the_display_level(self) -> None:
        source = source_contract()
        for record in source["Records"]:
            range_ = record["Projection"]["PredictionRange"]
            if range_:
                range_["Level"] = 0.8
        result = build_app_player_week_fantasy_read_model(
            source,
            {"Players": [{"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "100"}}]},
            {"Records": [{"CanonicalPlayerID": "NFLP-a", "SleeperPlayerID": "100"}]},
        )

        self.assertIsNone(result["Display"]["RangeAxis"])

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
