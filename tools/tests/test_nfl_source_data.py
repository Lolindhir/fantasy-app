import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib import common as common_mod
from nfl_source_data_lib.draft import classify_draft_status
from nfl_source_data_lib.materialize import materialize


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class NflSourceDataTests(unittest.TestCase):
    def test_stable_internal_id_is_deterministic(self):
        self.assertEqual(
            common_mod.stable_internal_id("GSIS:00-123"),
            common_mod.stable_internal_id("GSIS:00-123"),
        )
        self.assertNotEqual(
            common_mod.stable_internal_id("GSIS:00-123"),
            common_mod.stable_internal_id("GSIS:00-124"),
        )

    def test_draft_status_does_not_treat_zero_year_as_udfa(self):
        evidence = {"NFLP-x": {"DraftYear": 0, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, _ = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual("unknown", status)

    def test_draft_status_requires_concrete_year_for_udfa(self):
        evidence = {"NFLP-x": {"DraftYear": 2025, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, year = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual(("undrafted", 2025), (status, year))

    def test_future_draft_year_is_not_yet_drafted(self):
        evidence = {"NFLP-x": {"DraftYear": 2027, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, year = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual(("not_yet_drafted", 2027), (status, year))

    def test_csv_validation_fails_closed_on_missing_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            write_csv(path, [{"a": "1"}], ["a"])
            with self.assertRaises(ValueError):
                common_mod.inspect_csv(path, ["a", "b"], 1)

    def test_end_to_end_materialization_uses_identity_bridge_and_draft_evidence(self):
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
                    }
                ]
            }
            (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")
            write_csv(
                root / "source-data/providers/nflverse/players/raw-latest.csv",
                [
                    {"gsis_id": "00-1", "display_name": "Drafted Player", "pfr_id": "DrafPl00", "position": "WR", "espn_id": "11", "nfl_id": "41405", "birth_date": "2000-01-01"},
                    {"gsis_id": "00-2", "display_name": "Undrafted Player", "pfr_id": "UndrPl00", "position": "RB", "espn_id": "22", "birth_date": "2001-01-01"},
                ],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "nfl_id", "birth_date"]
            )
            write_csv(
                root / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv",
                [
                    {"mfl_id": "1", "gsis_id": "00-1", "sleeper_id": "S1", "espn_id": "11", "pfr_id": "DrafPl00", "nfl_id": "2543774", "name": "Drafted Player", "birthdate": "2000-01-01", "position": "WR", "draft_year": "2025", "draft_round": "2", "draft_pick": "5", "draft_ovr": "37"},
                    {"mfl_id": "2", "gsis_id": "00-2", "sleeper_id": "S2", "espn_id": "22", "pfr_id": "UndrPl00", "name": "Undrafted Player", "birthdate": "2001-01-01", "position": "RB", "draft_year": "2025", "draft_round": "", "draft_pick": "", "draft_ovr": ""},
                    {"mfl_id": "99", "gsis_id": "00-1", "sleeper_id": "S1", "espn_id": "11", "pfr_id": "DrafPl00", "nfl_id": "2543774", "name": "Legacy Homonym", "birthdate": "1970-01-01", "position": "DL", "draft_year": "1990", "draft_round": "1", "draft_pick": "10", "draft_ovr": "10"},
                ],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "nfl_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"]
            )
            write_csv(
                root / "source-data/providers/nflverse/draft-picks/raw-latest.csv",
                [{"season": "2025", "round": "2", "pick": "37", "team": "ABC", "gsis_id": "00-1", "pfr_player_id": "DrafPl00", "pfr_player_name": "Drafted Player", "position": "WR"}],
                ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"]
            )
            (root / "public/data").mkdir(parents=True)
            players = [
                {"ID": "S1", "TankID": "T1", "Name": "Drafted Player", "Position": "WR"},
                {"ID": "S2", "TankID": "T2", "Name": "Undrafted Player", "Position": "RB"},
            ]
            (root / "public/data/Players.json").write_text(json.dumps(players), encoding="utf-8")
            (root / "public/data/Players_Relevant.json").write_text(json.dumps(players), encoding="utf-8")

            datasets = {d.id: d for d in common_mod.load_registry(root)}
            result = materialize(root, datasets)

            self.assertEqual(3, result["identityCount"])
            self.assertEqual(1, result["identitySourceMappingConflictCount"])
            self.assertEqual(1, result["audit"]["identitySourceMappingConflictCount"])
            self.assertEqual({"drafted": 1, "undrafted": 1}, result["audit"]["draftStatusCoverage"])
            conflict = result["audit"]["identitySourceMappingConflicts"][0]
            self.assertEqual("99", conflict["MFLID"])
            self.assertEqual("birthdate_conflict_with_nflverse_players", conflict["Reason"])
            self.assertIn("Sleeper", conflict["SuppressedIDs"])

            canonical = json.loads((root / "source-data/nfl/identities/players.json").read_text())
            by_sleeper = {row["IDs"]["Sleeper"]: row for row in canonical["Players"] if row["IDs"].get("Sleeper")}
            self.assertEqual("T1", by_sleeper["S1"]["IDs"]["Tank01"])
            self.assertEqual("41405", by_sleeper["S1"]["IDs"]["NFL"])
            self.assertEqual("2543774", by_sleeper["S1"]["IDs"]["NFLCom"])
            quarantined = next(row for row in canonical["Players"] if row["IDs"].get("MFL") == "99")
            self.assertNotIn("Sleeper", quarantined["IDs"])
            self.assertNotIn("GSIS", quarantined["IDs"])

            draft = json.loads((root / "source-data/nfl/draft/2025.json").read_text())
            self.assertEqual(by_sleeper["S1"]["NFLPlayerID"], draft["Picks"][0]["NFLPlayerID"])
            self.assertEqual(1, draft["Picks"][0]["PositionInRound"])

    def test_write_json_if_changed_avoids_timestampless_churn(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            self.assertTrue(common_mod.write_json_if_changed(path, {"a": 1}))
            self.assertFalse(common_mod.write_json_if_changed(path, {"a": 1}))


if __name__ == "__main__":
    unittest.main()
