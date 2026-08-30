import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib import common as common_mod
from nfl_source_data_lib.materialize import materialize


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_registry(root: Path):
    registry = {
        "schemaVersion": 1,
        "datasets": [
            {
                "id": "nflverse.players",
                "provider": "nflverse",
                "upstream": "test",
                "sourceUrl": "https://example.invalid/players.csv",
                "sourceFormat": "csv",
                "rawPath": "providers/nflverse/players/raw-latest.csv",
                "metadataPath": "providers/nflverse/players/metadata.json",
                "requiredColumns": ["gsis_id", "display_name", "pfr_id", "position"],
                "minimumRows": 1,
                "kind": "identity",
                "refreshPolicy": "periodic",
                "retentionPolicy": "latest",
                "license": "test",
                "attribution": "test",
            },
            {
                "id": "nflverse.ff-player-ids",
                "provider": "ffverse",
                "upstream": "test",
                "sourceUrl": "https://example.invalid/ids.csv",
                "sourceFormat": "csv",
                "rawPath": "providers/nflverse/ff-player-ids/raw-latest.csv",
                "metadataPath": "providers/nflverse/ff-player-ids/metadata.json",
                "requiredColumns": [
                    "mfl_id",
                    "gsis_id",
                    "sleeper_id",
                    "espn_id",
                    "pfr_id",
                    "name",
                    "draft_year",
                    "draft_round",
                    "draft_pick",
                    "draft_ovr",
                ],
                "minimumRows": 1,
                "kind": "identity-mapping",
                "refreshPolicy": "periodic",
                "retentionPolicy": "latest",
                "license": "test",
                "attribution": "test",
            },
            {
                "id": "nflverse.draft-picks",
                "provider": "nflverse",
                "upstream": "test",
                "sourceUrl": "https://example.invalid/draft.csv",
                "sourceFormat": "csv",
                "rawPath": "providers/nflverse/draft-picks/raw-latest.csv",
                "metadataPath": "providers/nflverse/draft-picks/metadata.json",
                "requiredColumns": [
                    "season",
                    "round",
                    "pick",
                    "team",
                    "gsis_id",
                    "pfr_player_id",
                    "pfr_player_name",
                    "position",
                ],
                "minimumRows": 1,
                "kind": "historical-event",
                "refreshPolicy": "periodic",
                "retentionPolicy": "permanent",
                "license": "test",
                "attribution": "test",
            },
        ],
    }
    (root / "source-data").mkdir(parents=True, exist_ok=True)
    (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")


def write_supporting_files(root: Path):
    write_csv(
        root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
        [
            {
                "mfl_id": "dummy",
                "gsis_id": "00-dummy",
                "sleeper_id": "dummy",
                "espn_id": "999",
                "pfr_id": "Dummy00",
                "pff_id": "999",
                "name": "Dummy Player",
                "birthdate": "1990-01-01",
                "position": "WR",
                "draft_year": "2025",
                "draft_round": "1",
                "draft_pick": "1",
                "draft_ovr": "1",
            }
        ],
        [
            "mfl_id",
            "gsis_id",
            "sleeper_id",
            "espn_id",
            "pfr_id",
            "pff_id",
            "name",
            "birthdate",
            "position",
            "draft_year",
            "draft_round",
            "draft_pick",
            "draft_ovr",
        ],
    )
    write_csv(
        root / "source-data/providers/nflverse/draft-picks/raw-latest.csv",
        [
            {
                "season": "2025",
                "round": "1",
                "pick": "1",
                "team": "ABC",
                "gsis_id": "00-dummy",
                "pfr_player_id": "Dummy00",
                "pfr_player_name": "Dummy Player",
                "position": "WR",
            }
        ],
        [
            "season",
            "round",
            "pick",
            "team",
            "gsis_id",
            "pfr_player_id",
            "pfr_player_name",
            "position",
        ],
    )
    (root / "public/data").mkdir(parents=True, exist_ok=True)
    (root / "public/data/Players.json").write_text("[]", encoding="utf-8")
    (root / "public/data/Players_Relevant.json").write_text("[]", encoding="utf-8")
    (root / "public/data/League.json").write_text(json.dumps({"Season": 2026}), encoding="utf-8")


def write_existing_identity_state(root: Path, players, mappings):
    path = root / "source-data/nfl/identities"
    path.mkdir(parents=True, exist_ok=True)
    (path / "players.json").write_text(
        json.dumps(
            {
                "SchemaVersion": 2,
                "IdentityPolicy": {},
                "Players": players,
            }
        ),
        encoding="utf-8",
    )
    (path / "provider-mappings.json").write_text(
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


class NflSourceIdentityReplayCorrectionTests(unittest.TestCase):
    def test_swapped_stale_pfr_values_are_corrected_without_alias_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_supporting_files(root)
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [
                    {
                        "gsis_id": "00-A",
                        "display_name": "Player A",
                        "first_name": "Player",
                        "last_name": "A",
                        "pfr_id": "PlayerA02",
                        "position": "DE",
                        "espn_id": "101",
                        "pff_id": "201",
                        "esb_id": "ESB-A",
                        "nfl_id": "NFL-A",
                        "birth_date": "1995-08-17",
                    },
                    {
                        "gsis_id": "00-B",
                        "display_name": "Player B",
                        "first_name": "Player",
                        "last_name": "B",
                        "pfr_id": "PlayerB02",
                        "position": "OT",
                        "espn_id": "102",
                        "pff_id": "202",
                        "esb_id": "ESB-B",
                        "nfl_id": "NFL-B",
                        "birth_date": "1997-11-17",
                    },
                ],
                [
                    "gsis_id",
                    "display_name",
                    "first_name",
                    "last_name",
                    "pfr_id",
                    "position",
                    "espn_id",
                    "pff_id",
                    "esb_id",
                    "nfl_id",
                    "birth_date",
                ],
            )
            write_existing_identity_state(
                root,
                [
                    {
                        "CanonicalPlayerID": "NFLP-a",
                        "Name": "Player A",
                        "FirstName": "Player",
                        "LastName": "A",
                        "BirthDate": "1995-08-17",
                        "Position": "DE",
                        "LatestTeam": "AAA",
                        "IDs": {
                            "GSIS": "00-A",
                            "ESPN": "101",
                            "PFF": "201",
                            "PFR": "PlayerB02",
                            "ESB": "ESB-A",
                            "NFL": "NFL-A",
                        },
                        "IDAliases": {},
                        "Sources": ["nflverse.players"],
                    },
                    {
                        "CanonicalPlayerID": "NFLP-b",
                        "Name": "Player B",
                        "FirstName": "Player",
                        "LastName": "B",
                        "BirthDate": "1997-11-17",
                        "Position": "OT",
                        "LatestTeam": "BBB",
                        "IDs": {
                            "GSIS": "00-B",
                            "ESPN": "102",
                            "PFF": "202",
                            "PFR": "PlayerA02",
                            "ESB": "ESB-B",
                            "NFL": "NFL-B",
                        },
                        "IDAliases": {},
                        "Sources": ["nflverse.players"],
                    },
                ],
                [
                    {
                        "Provider": "PFR",
                        "ExternalID": "PlayerB02",
                        "CanonicalPlayerID": "NFLP-a",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["nflverse.players"],
                    },
                    {
                        "Provider": "PFR",
                        "ExternalID": "PlayerA02",
                        "CanonicalPlayerID": "NFLP-b",
                        "FirstObservedSeason": 2026,
                        "LastObservedSeason": 2026,
                        "Sources": ["nflverse.players"],
                    },
                ],
            )
            datasets = {dataset.id: dataset for dataset in common_mod.load_registry(root)}

            result = materialize(root, datasets)
            payload = json.loads(
                (root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8")
            )
            rows = {row["CanonicalPlayerID"]: row for row in payload["Players"]}
            self.assertEqual("PlayerA02", rows["NFLP-a"]["IDs"]["PFR"])
            self.assertEqual("PlayerB02", rows["NFLP-b"]["IDs"]["PFR"])
            self.assertNotIn("PFR", rows["NFLP-a"].get("IDAliases", {}))
            self.assertNotIn("PFR", rows["NFLP-b"].get("IDAliases", {}))
            self.assertEqual(0, result["providerMappingConflictCount"])
            self.assertEqual(
                0,
                result["audit"]["identityInvariantViolations"]["duplicateLinkProviderIDCount"],
            )

            mapping_payload = json.loads(
                (root / "source-data/nfl/identities/provider-mappings.json").read_text(
                    encoding="utf-8"
                )
            )
            pfr = {
                (item["ExternalID"], item["CanonicalPlayerID"])
                for item in mapping_payload["Mappings"]
                if item["Provider"] == "PFR"
            }
            self.assertIn(("PlayerA02", "NFLP-a"), pfr)
            self.assertIn(("PlayerB02", "NFLP-b"), pfr)
            self.assertNotIn(("PlayerB02", "NFLP-a"), pfr)
            self.assertNotIn(("PlayerA02", "NFLP-b"), pfr)

            second = materialize(root, datasets)
            self.assertFalse(second["identityChanged"])
            self.assertFalse(second["providerMappingsChanged"])
            self.assertEqual(0, second["draftFilesChanged"])
            self.assertFalse(second["auditChanged"])

    def test_two_strong_and_two_secondary_ids_preserve_identity_across_dob_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_supporting_files(root)
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [
                    {
                        "gsis_id": "00-E",
                        "display_name": "Player E",
                        "first_name": "Player",
                        "last_name": "E",
                        "pfr_id": "",
                        "position": "LB",
                        "espn_id": "501",
                        "pff_id": "",
                        "esb_id": "ESB-E",
                        "nfl_id": "NFL-E",
                        "birth_date": "2002-08-07",
                    }
                ],
                [
                    "gsis_id",
                    "display_name",
                    "first_name",
                    "last_name",
                    "pfr_id",
                    "position",
                    "espn_id",
                    "pff_id",
                    "esb_id",
                    "nfl_id",
                    "birth_date",
                ],
            )
            write_existing_identity_state(
                root,
                [
                    {
                        "CanonicalPlayerID": "NFLP-e",
                        "Name": "Player E",
                        "FirstName": "Player",
                        "LastName": "E",
                        "BirthDate": "2001-11-08",
                        "Position": "LB",
                        "LatestTeam": "EEE",
                        "IDs": {
                            "GSIS": "00-E",
                            "ESPN": "501",
                            "ESB": "ESB-E",
                            "NFL": "NFL-E",
                        },
                        "IDAliases": {},
                        "Sources": ["nflverse.players"],
                    }
                ],
                [],
            )
            datasets = {dataset.id: dataset for dataset in common_mod.load_registry(root)}

            result = materialize(root, datasets)
            payload = json.loads(
                (root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8")
            )
            row = next(item for item in payload["Players"] if item["CanonicalPlayerID"] == "NFLP-e")
            self.assertEqual("2002-08-07", row["BirthDate"])
            self.assertEqual("00-E", row["IDs"]["GSIS"])
            self.assertEqual("501", row["IDs"]["ESPN"])
            self.assertEqual(0, result["providerMappingConflictCount"])


if __name__ == "__main__":
    unittest.main()
