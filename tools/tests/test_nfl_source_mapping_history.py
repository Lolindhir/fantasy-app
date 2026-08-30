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
from nfl_source_data_lib.provider_mappings import build_provider_mapping_payload


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

    def _write_mapping_payload(self, root: Path, mappings):
        path = root / "source-data/nfl/identities/provider-mappings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "TemporalResolution": "season",
                    "Mappings": mappings,
                    "Conflicts": [],
                }
            ),
            encoding="utf-8",
        )

    def test_same_season_stale_anchor_mapping_is_replaced_for_same_player(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": "PFR",
                        "ExternalID": "Old00",
                        "CanonicalPlayerID": "NFLP-a",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["nflverse.players"],
                    }
                ],
            )
            claims = [
                {
                    "Provider": "PFR",
                    "ExternalID": "New00",
                    "CanonicalPlayerID": "NFLP-a",
                    "Sources": ["nflverse.players"],
                }
            ]
            payload = build_provider_mapping_payload(root, claims, [], 2026)
            self.assertEqual(
                [("New00", 2026, 2026)],
                [
                    (item["ExternalID"], item["FirstObservedSeason"], item["LastObservedSeason"])
                    for item in payload["Mappings"]
                    if item["Provider"] == "PFR"
                ],
            )
            self.assertEqual([], payload["Conflicts"])

    def test_earlier_anchor_history_is_closed_before_corrected_current_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": "PFR",
                        "ExternalID": "Old00",
                        "CanonicalPlayerID": "NFLP-a",
                        "FirstObservedSeason": 2024,
                        "LastObservedSeason": 2026,
                        "Sources": ["nflverse.players"],
                    }
                ],
            )
            claims = [
                {
                    "Provider": "PFR",
                    "ExternalID": "New00",
                    "CanonicalPlayerID": "NFLP-a",
                    "Sources": ["nflverse.players"],
                }
            ]
            payload = build_provider_mapping_payload(root, claims, [], 2026)
            rows = {
                item["ExternalID"]: (item["FirstObservedSeason"], item["LastObservedSeason"])
                for item in payload["Mappings"]
                if item["Provider"] == "PFR"
            }
            self.assertEqual((2024, 2025), rows["Old00"])
            self.assertEqual((2026, 2026), rows["New00"])
            self.assertEqual([], payload["Conflicts"])

    def test_anchor_mapping_owned_by_different_current_player_still_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": "PFR",
                        "ExternalID": "Shared00",
                        "CanonicalPlayerID": "NFLP-old",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["nflverse.players"],
                    }
                ],
            )
            claims = [
                {
                    "Provider": "PFR",
                    "ExternalID": "Shared00",
                    "CanonicalPlayerID": "NFLP-new",
                    "Sources": ["nflverse.players"],
                }
            ]
            payload = build_provider_mapping_payload(root, claims, [], 2026)
            self.assertEqual(1, len(payload["Conflicts"]))
            self.assertEqual(
                ["NFLP-new", "NFLP-old"],
                payload["Conflicts"][0]["CanonicalPlayerIDs"],
            )
            self.assertFalse(
                any(
                    item["CanonicalPlayerID"] == "NFLP-new"
                    and item["ExternalID"] == "Shared00"
                    for item in payload["Mappings"]
                )
            )

    def test_non_anchor_mapping_is_not_auto_retired_as_latest_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_mapping_payload(
                root,
                [
                    {
                        "Provider": "Sleeper",
                        "ExternalID": "OldSleeper",
                        "CanonicalPlayerID": "NFLP-a",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["app.Players"],
                    }
                ],
            )
            claims = [
                {
                    "Provider": "Sleeper",
                    "ExternalID": "NewSleeper",
                    "CanonicalPlayerID": "NFLP-a",
                    "Sources": ["app.Players"],
                }
            ]
            payload = build_provider_mapping_payload(root, claims, [], 2026)
            self.assertEqual(
                {"OldSleeper", "NewSleeper"},
                {
                    item["ExternalID"]
                    for item in payload["Mappings"]
                    if item["Provider"] == "Sleeper"
                },
            )


if __name__ == "__main__":
    unittest.main()
