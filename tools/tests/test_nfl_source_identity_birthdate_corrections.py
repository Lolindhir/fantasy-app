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


def write_players(root: Path, birth_date: str):
    write_csv(
        root / "source-data/providers/nflverse/players/raw-latest.csv",
        [
            {
                "gsis_id": "00-0041330",
                "display_name": "Alan Herron",
                "pfr_id": "",
                "position": "OT",
                "espn_id": "5164879",
                "pff_id": "181445",
                "birth_date": birth_date,
            }
        ],
        ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "pff_id", "birth_date"],
    )


def write_supporting_sources(root: Path):
    write_csv(
        root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
        [
            {
                "mfl_id": "B",
                "gsis_id": "00-B",
                "sleeper_id": "2000",
                "espn_id": "2",
                "pfr_id": "PlayerB00",
                "pff_id": "22",
                "name": "Player B",
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
                "gsis_id": "00-B",
                "pfr_player_id": "PlayerB00",
                "pfr_player_name": "Player B",
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


class NflSourceIdentityBirthdateCorrectionTests(unittest.TestCase):
    def test_three_matching_strong_ids_preserve_identity_across_nflverse_dob_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_players(root, "2003-03-10")
            write_supporting_sources(root)
            datasets = {dataset.id: dataset for dataset in common_mod.load_registry(root)}

            first = materialize(root, datasets)
            first_payload = json.loads(
                (root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8")
            )
            first_row = next(
                row
                for row in first_payload["Players"]
                if row.get("IDs", {}).get("GSIS") == "00-0041330"
            )
            canonical_id = first_row["CanonicalPlayerID"]
            self.assertEqual("2003-03-10", first_row["BirthDate"])

            write_players(root, "2003-01-02")
            second = materialize(root, datasets)
            second_payload = json.loads(
                (root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8")
            )
            matching = [
                row
                for row in second_payload["Players"]
                if row.get("IDs", {}).get("GSIS") == "00-0041330"
                or "00-0041330" in row.get("IDAliases", {}).get("GSIS", [])
            ]

            self.assertEqual(1, len(matching))
            self.assertEqual(canonical_id, matching[0]["CanonicalPlayerID"])
            self.assertEqual("2003-01-02", matching[0]["BirthDate"])
            self.assertEqual(0, second["providerMappingConflictCount"])
            self.assertEqual(
                0,
                second["audit"]["identityInvariantViolations"]["duplicateLinkProviderIDCount"],
            )

            third = materialize(root, datasets)
            self.assertFalse(third["identityChanged"])
            self.assertFalse(third["providerMappingsChanged"])
            self.assertEqual(0, third["draftFilesChanged"])
            self.assertFalse(third["auditChanged"])
            self.assertTrue(first["identityChanged"])


if __name__ == "__main__":
    unittest.main()
