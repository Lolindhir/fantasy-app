import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.mapping_history import (
    build_historical_app_mapping_claims,
    extend_provider_mapping_payload,
)


class NflSourceMappingHistoryTests(unittest.TestCase):
    def test_archived_player_snapshot_extends_sleeper_and_tank_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "public/data/past_seasons"
            archive.mkdir(parents=True)
            archive.joinpath("Players_2023.json").write_text(
                json.dumps([
                    {"ID": "S1", "TankID": "T1", "Name": "Player A", "Position": "WR"}
                ]),
                encoding="utf-8",
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"Sleeper": "S1", "Tank01": "T1"},
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)
            self.assertEqual([], conflicts)
            self.assertEqual(1, stats["snapshotSeasonCount"])
            self.assertEqual(1, stats["resolvedPlayerCount"])
            self.assertEqual(
                {
                    ("Sleeper", "S1", "NFLP-a", 2023),
                    ("Tank01", "T1", "NFLP-a", 2023),
                },
                {
                    (item["Provider"], item["ExternalID"], item["CanonicalPlayerID"], item["ObservedSeason"])
                    for item in claims
                },
            )

            payload = {
                "SchemaVersion": 2,
                "TemporalResolution": "season",
                "Mappings": [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "S1",
                        "CanonicalPlayerID": "NFLP-a",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["app.Players"],
                    }
                ],
                "Conflicts": [],
            }
            extended = extend_provider_mapping_payload(payload, claims, conflicts)
            sleeper = next(
                item
                for item in extended["Mappings"]
                if item["Provider"] == "Sleeper" and item["ExternalID"] == "S1"
            )
            self.assertEqual(2023, sleeper["FirstObservedSeason"])
            self.assertEqual(2026, sleeper["LastObservedSeason"])
            self.assertIn("app.PastPlayers.2023", sleeper["Sources"])

    def test_archived_snapshot_disagreement_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "public/data/past_seasons"
            archive.mkdir(parents=True)
            archive.joinpath("Players_2024.json").write_text(
                json.dumps([
                    {"ID": "S1", "TankID": "T2", "Name": "Ambiguous Player", "Position": "RB"}
                ]),
                encoding="utf-8",
            )
            canonical = [
                {"CanonicalPlayerID": "NFLP-a", "IDs": {"Sleeper": "S1"}, "IDAliases": {}},
                {"CanonicalPlayerID": "NFLP-b", "IDs": {"Tank01": "T2"}, "IDAliases": {}},
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)
            self.assertEqual([], claims)
            self.assertEqual(1, stats["conflictingPlayerCount"])
            self.assertEqual(1, len(conflicts))
            self.assertEqual(
                {"Sleeper": "NFLP-a", "Tank01": "NFLP-b"},
                conflicts[0]["ResolvedByProvider"],
            )

    def test_archived_snapshot_does_not_backfill_from_sleeper_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "public/data/past_seasons"
            archive.mkdir(parents=True)
            archive.joinpath("Players_2025.json").write_text(
                json.dumps([
                    {"ID": "1000", "Name": "Old Player", "Position": "WR"}
                ]),
                encoding="utf-8",
            )
            canonical = [
                {"CanonicalPlayerID": "NFLP-current", "IDs": {"Sleeper": "1000"}, "IDAliases": {}}
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)
            self.assertEqual([], claims)
            self.assertEqual([], conflicts)
            self.assertEqual(1, stats["unresolvedPlayerCount"])
            self.assertEqual(1, stats["insufficientCorroborationCount"])

    def test_archived_snapshot_uses_espn_as_second_corroborator_and_can_seed_tank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "public/data/past_seasons"
            archive.mkdir(parents=True)
            archive.joinpath("Players_2022.json").write_text(
                json.dumps([
                    {"ID": "S1", "TankID": "legacy-tank", "ESPNID": "E1", "Name": "Player A", "Position": "WR"}
                ]),
                encoding="utf-8",
            )
            canonical = [
                {
                    "CanonicalPlayerID": "NFLP-a",
                    "IDs": {"Sleeper": "S1", "ESPN": "E1"},
                    "IDAliases": {},
                }
            ]

            claims, conflicts, stats = build_historical_app_mapping_claims(root, canonical)
            self.assertEqual([], conflicts)
            self.assertEqual(1, stats["resolvedPlayerCount"])
            self.assertEqual(
                {"Sleeper", "Tank01", "ESPN"},
                {item["Provider"] for item in claims},
            )
            self.assertTrue(all(item["CanonicalPlayerID"] == "NFLP-a" for item in claims))

    def test_non_overlapping_historical_reuse_is_kept_as_two_mappings(self):
        payload = {
            "SchemaVersion": 2,
            "TemporalResolution": "season",
            "Mappings": [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "1000",
                    "CanonicalPlayerID": "NFLP-new",
                    "FirstObservedSeason": 2036,
                    "LastObservedSeason": 2036,
                    "Sources": ["app.Players"],
                }
            ],
            "Conflicts": [],
        }
        claims = [
            {
                "Provider": "Sleeper",
                "ExternalID": "1000",
                "CanonicalPlayerID": "NFLP-old",
                "ObservedSeason": 2025,
                "Sources": ["app.PastPlayers.2025"],
            }
        ]
        extended = extend_provider_mapping_payload(payload, claims, [])
        rows = [
            item
            for item in extended["Mappings"]
            if item["Provider"] == "Sleeper" and item["ExternalID"] == "1000"
        ]
        self.assertEqual(2, len(rows))
        self.assertEqual({"NFLP-old", "NFLP-new"}, {item["CanonicalPlayerID"] for item in rows})
        self.assertEqual(0, len(extended["Conflicts"]))


if __name__ == "__main__":
    unittest.main()
