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


class NflSourceQuarantineReplayTests(unittest.TestCase):
    def test_mfl_only_quarantine_replays_existing_internal_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-data").mkdir(parents=True)
            registry = {
                "schemaVersion": 1,
                "datasets": [
                    {
                        "id": "nflverse.players", "provider": "nflverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/players.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/players/raw-latest.csv",
                        "metadataPath": "providers/nflverse/players/metadata.json",
                        "requiredColumns": ["gsis_id", "display_name", "pfr_id", "position"],
                        "minimumRows": 1, "kind": "identity", "refreshPolicy": "periodic",
                        "retentionPolicy": "latest", "license": "test", "attribution": "test"
                    },
                    {
                        "id": "nflverse.ff-player-ids", "provider": "ffverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/ids.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/ff-player-ids/raw-latest.csv",
                        "metadataPath": "providers/nflverse/ff-player-ids/metadata.json",
                        "requiredColumns": ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
                        "minimumRows": 1, "kind": "identity-mapping", "refreshPolicy": "periodic",
                        "retentionPolicy": "latest", "license": "test", "attribution": "test"
                    },
                    {
                        "id": "nflverse.draft-picks", "provider": "nflverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/draft.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/draft-picks/raw-latest.csv",
                        "metadataPath": "providers/nflverse/draft-picks/metadata.json",
                        "requiredColumns": ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"],
                        "minimumRows": 1, "kind": "historical-event", "refreshPolicy": "periodic",
                        "retentionPolicy": "permanent", "license": "test", "attribution": "test"
                    },
                ],
            }
            (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")

            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [{"gsis_id": "00-A", "display_name": "Current Player", "pfr_id": "CurrPl00", "position": "WR", "espn_id": "1", "birth_date": "2000-01-01"}],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "birth_date"],
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [{"mfl_id": "LEGACY", "gsis_id": "00-A", "sleeper_id": "OLD", "espn_id": "1", "pfr_id": "CurrPl00", "name": "Legacy Homonym", "birthdate": "1970-01-01", "position": "DL", "draft_year": "1990", "draft_round": "1", "draft_pick": "10", "draft_ovr": "10"}],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
            )
            write_csv(
                root / "source-data/providers/nflverse/draft-picks/raw-latest.csv",
                [{"season": "2025", "round": "1", "pick": "1", "team": "ABC", "gsis_id": "00-A", "pfr_player_id": "CurrPl00", "pfr_player_name": "Current Player", "position": "WR"}],
                ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"],
            )
            (root / "public/data").mkdir(parents=True)
            (root / "public/data/Players.json").write_text("[]", encoding="utf-8")
            (root / "public/data/Players_Relevant.json").write_text("[]", encoding="utf-8")
            (root / "public/data/League.json").write_text(json.dumps({"Season": 2026}), encoding="utf-8")

            datasets = {dataset.id: dataset for dataset in common_mod.load_registry(root)}
            first = materialize(root, datasets)
            canonical = json.loads((root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8"))
            legacy = next(row for row in canonical["Players"] if row.get("IDs", {}).get("MFL") == "LEGACY")
            legacy_id = legacy["NFLPlayerID"]

            second = materialize(root, datasets)
            canonical_again = json.loads((root / "source-data/nfl/identities/players.json").read_text(encoding="utf-8"))
            replayed = next(row for row in canonical_again["Players"] if row.get("IDs", {}).get("MFL") == "LEGACY")

            self.assertTrue(first["identityChanged"])
            self.assertEqual(legacy_id, replayed["NFLPlayerID"])
            self.assertFalse(second["identityChanged"])
            self.assertFalse(second["providerMappingsChanged"])
            self.assertEqual(0, second["draftFilesChanged"])
            self.assertFalse(second["auditChanged"])


if __name__ == "__main__":
    unittest.main()
