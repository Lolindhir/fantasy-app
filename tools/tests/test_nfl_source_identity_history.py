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
    (root / "source-data").mkdir(parents=True, exist_ok=True)
    (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")


def write_draft(root: Path, gsis="00-A", pfr="PlayerA00", name="Player A", season=2025):
    write_csv(
        root / "source-data/providers/nflverse/draft-picks/raw-latest.csv",
        [{"season": str(season), "round": "1", "pick": "1", "team": "ABC", "gsis_id": gsis,
          "pfr_player_id": pfr, "pfr_player_name": name, "position": "WR"}],
        ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"],
    )


def write_app(root: Path, players, season):
    (root / "public/data").mkdir(parents=True, exist_ok=True)
    (root / "public/data/Players.json").write_text(json.dumps(players), encoding="utf-8")
    (root / "public/data/Players_Relevant.json").write_text(json.dumps(players), encoding="utf-8")
    (root / "public/data/League.json").write_text(json.dumps({"Season": season}), encoding="utf-8")


class NflSourceIdentityHistoryTests(unittest.TestCase):
    def test_duplicate_sleeper_id_is_quarantined_instead_of_merging_people(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [
                    {"gsis_id": "00-A", "display_name": "Greg Jones", "pfr_id": "JoneGr01", "position": "RB", "espn_id": "5580", "pff_id": "1776", "birth_date": "1981-05-09"},
                    {"gsis_id": "00-B", "display_name": "Greg K. Jones", "pfr_id": "JoneGr02", "position": "LB", "espn_id": "14172", "pff_id": "6337", "birth_date": "1988-10-05"},
                ],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "pff_id", "birth_date"],
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [
                    {"mfl_id": "A", "gsis_id": "00-A", "sleeper_id": "133", "espn_id": "5580", "pfr_id": "JoneGr01", "pff_id": "1776", "name": "Greg Jones", "birthdate": "1981-05-09", "position": "RB", "draft_year": "2004", "draft_round": "1", "draft_pick": "30", "draft_ovr": "30"},
                    {"mfl_id": "B", "gsis_id": "00-B", "sleeper_id": "133", "espn_id": "14172", "pfr_id": "JoneGr02", "pff_id": "6337", "name": "Greg K. Jones", "birthdate": "1988-10-05", "position": "LB", "draft_year": "2011", "draft_round": "", "draft_pick": "", "draft_ovr": ""},
                ],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "pff_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
            )
            write_draft(root)
            write_app(root, [], 2026)

            datasets = {d.id: d for d in common_mod.load_registry(root)}
            result = materialize(root, datasets)

            self.assertEqual(2, result["identityCount"])
            canonical = json.loads((root / "source-data/nfl/identities/players.json").read_text())
            self.assertEqual(2, len(canonical["Players"]))
            self.assertTrue(all(row.get("IDs", {}).get("Sleeper") != "133" for row in canonical["Players"]))
            conflicts = json.loads((root / "source-data/nfl/identities/provider-mappings.json").read_text())["Conflicts"]
            sleeper_conflict = next(item for item in conflicts if item["Provider"] == "Sleeper" and item["ExternalID"] == "133")
            self.assertEqual(2, len(sleeper_conflict["NFLPlayerIDs"]))
            self.assertEqual(0, result["audit"]["identityInvariantViolations"]["duplicateLinkProviderIDCount"])

    def test_provider_id_can_be_reused_in_a_later_observed_season(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [{"gsis_id": "00-A", "display_name": "Player A", "pfr_id": "PlayerA00", "position": "WR", "espn_id": "1", "birth_date": "2000-01-01"}],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "birth_date"],
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [{"mfl_id": "A", "gsis_id": "00-A", "sleeper_id": "1000", "espn_id": "1", "pfr_id": "PlayerA00", "name": "Player A", "birthdate": "2000-01-01", "position": "WR", "draft_year": "2025", "draft_round": "1", "draft_pick": "1", "draft_ovr": "1"}],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
            )
            write_draft(root)
            write_app(root, [{"ID": "1000", "TankID": "TA", "Name": "Player A", "Position": "WR"}], 2026)
            datasets = {d.id: d for d in common_mod.load_registry(root)}
            materialize(root, datasets)
            first_payload = json.loads((root / "source-data/nfl/identities/provider-mappings.json").read_text())
            first = next(item for item in first_payload["Mappings"] if item["Provider"] == "Sleeper" and item["ExternalID"] == "1000")
            first_internal = first["NFLPlayerID"]
            self.assertEqual((2026, 2026), (first["FirstObservedSeason"], first["LastObservedSeason"]))

            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [{"gsis_id": "00-B", "display_name": "Player B", "pfr_id": "PlayerB00", "position": "RB", "espn_id": "2", "birth_date": "2010-01-01"}],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "birth_date"],
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [{"mfl_id": "B", "gsis_id": "00-B", "sleeper_id": "1000", "espn_id": "2", "pfr_id": "PlayerB00", "name": "Player B", "birthdate": "2010-01-01", "position": "RB", "draft_year": "2035", "draft_round": "1", "draft_pick": "1", "draft_ovr": "1"}],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
            )
            write_draft(root, gsis="00-B", pfr="PlayerB00", name="Player B", season=2035)
            write_app(root, [{"ID": "1000", "TankID": "TB", "Name": "Player B", "Position": "RB"}], 2036)
            second = materialize(root, datasets)
            second_payload = json.loads((root / "source-data/nfl/identities/provider-mappings.json").read_text())
            sleeper_rows = [item for item in second_payload["Mappings"] if item["Provider"] == "Sleeper" and item["ExternalID"] == "1000"]
            self.assertEqual(2, len(sleeper_rows))
            self.assertEqual({2026, 2036}, {item["FirstObservedSeason"] for item in sleeper_rows})
            self.assertEqual(2, len({item["NFLPlayerID"] for item in sleeper_rows}))
            self.assertIn(first_internal, {item["NFLPlayerID"] for item in sleeper_rows})
            self.assertEqual(0, second["providerMappingConflictCount"])

    def test_repeated_materialization_is_a_semantic_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root)
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [{"gsis_id": "00-A", "display_name": "Player A", "pfr_id": "PlayerA00", "position": "WR", "espn_id": "1", "birth_date": "2000-01-01"}],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "birth_date"],
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [{"mfl_id": "A", "gsis_id": "00-A", "sleeper_id": "1000", "espn_id": "1", "pfr_id": "PlayerA00", "name": "Player A", "birthdate": "2000-01-01", "position": "WR", "draft_year": "2025", "draft_round": "1", "draft_pick": "1", "draft_ovr": "1"}],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
            )
            write_draft(root)
            write_app(root, [{"ID": "1000", "TankID": "TA", "Name": "Player A", "Position": "WR"}], 2026)
            datasets = {d.id: d for d in common_mod.load_registry(root)}

            first = materialize(root, datasets)
            paths = [
                root / "source-data/nfl/identities/players.json",
                root / "source-data/nfl/identities/provider-mappings.json",
                root / "source-data/nfl/draft/2025.json",
                root / "source-data/audits/nfl-source-data-audit.json",
            ]
            before = {path: path.read_text(encoding="utf-8") for path in paths}
            second = materialize(root, datasets)
            after = {path: path.read_text(encoding="utf-8") for path in paths}

            self.assertTrue(first["identityChanged"])
            self.assertFalse(second["identityChanged"])
            self.assertFalse(second["providerMappingsChanged"])
            self.assertEqual(0, second["draftFilesChanged"])
            self.assertFalse(second["auditChanged"])
            self.assertEqual(before, after)
            self.assertNotIn("GeneratedAtUtc", after[paths[0]])
            self.assertNotIn("generatedAtUtc", after[paths[3]])


if __name__ == "__main__":
    unittest.main()
