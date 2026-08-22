import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.combine import build_combine_files
from nfl_source_data_lib.common import (
    Dataset,
    REGISTRY_SCHEMA_VERSION,
    load_registry,
    load_registry_manifest,
    planned_dataset_ids,
)
from nfl_source_data_lib.lifecycle import effective_partition_payload


COMBINE_FIELDS = [
    "season", "draft_year", "draft_team", "draft_round", "draft_ovr",
    "pfr_id", "cfb_id", "player_name", "pos", "school", "ht", "wt",
    "forty", "bench", "vertical", "broad_jump", "cone", "shuttle",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def combine_dataset(raw_path: Path) -> Dataset:
    return Dataset(
        "nflverse.combine",
        "nflverse",
        "test",
        "https://example.invalid/combine.csv",
        raw_path,
        Path("metadata.json"),
        tuple(COMBINE_FIELDS),
        1,
        "athletic-measurement-history",
        "discover-new-partitions",
        "permanent-by-season",
        "test",
        "test",
        "immutable-history",
        "season",
        "freeze-existing-partitions",
        "explicit-force",
    )


class RegistryCombineTests(unittest.TestCase):
    def test_repository_registry_uses_v2_lifecycle_contract(self):
        manifest = load_registry_manifest(REPO_ROOT)
        self.assertEqual(REGISTRY_SCHEMA_VERSION, manifest["schemaVersion"])
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        self.assertEqual("immutable-history", active["nflverse.draft-picks"].lifecycle_class)
        self.assertEqual("immutable-history", active["nflverse.combine"].lifecycle_class)
        self.assertIn("nflverse.depth-charts", planned_dataset_ids(REPO_ROOT))

    def test_invalid_immutable_lifecycle_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-data").mkdir()
            registry = {
                "schemaVersion": REGISTRY_SCHEMA_VERSION,
                "datasets": [{
                    "id": "x.bad",
                    "provider": "x",
                    "upstream": "x",
                    "sourceUrl": "https://example.invalid/x.csv",
                    "rawPath": "providers/x/raw.csv",
                    "metadataPath": "providers/x/meta.json",
                    "requiredColumns": ["a"],
                    "minimumRows": 1,
                    "kind": "history",
                    "refreshPolicy": "discover-new-partitions",
                    "retentionPolicy": "permanent-by-season",
                    "lifecycle": {
                        "class": "immutable-history",
                        "partitionKey": "season",
                        "finalization": "never",
                        "repairPolicy": "normal",
                    },
                    "license": "test",
                    "attribution": "test",
                }],
            }
            (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry(root)

    def test_finalized_partition_is_preserved_without_explicit_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2025.json"
            existing = {"Finalized": True, "Records": [{"value": "old"}]}
            path.write_text(json.dumps(existing), encoding="utf-8")
            dataset = combine_dataset(Path(tmp) / "combine.csv")
            candidate = {"Finalized": True, "Records": [{"value": "new"}]}

            effective, preserved = effective_partition_payload(
                dataset,
                path=path,
                candidate=candidate,
                partition_season=2025,
                observation_season=2026,
                force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(existing, effective)

            effective, preserved = effective_partition_payload(
                dataset,
                path=path,
                candidate=candidate,
                partition_season=2025,
                observation_season=2026,
                force=True,
            )
            self.assertFalse(preserved)
            self.assertEqual(candidate, effective)

    def test_combine_resolves_only_pfr_and_links_canonical_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "draft_year": "2025",
                "draft_team": "Test Team",
                "draft_round": "1",
                "draft_ovr": "5",
                "pfr_id": "PlayTe00",
                "cfb_id": "player-test",
                "player_name": "Test Player",
                "pos": "WR",
                "school": "Test U",
                "ht": "6-2",
                "wt": "205",
                "forty": "4.41",
                "bench": "12",
                "vertical": "38.5",
                "broad_jump": "124",
                "cone": "6.91",
                "shuttle": "4.12",
            }])
            canonical = [{"NFLPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                2025: {
                    "Picks": [{
                        "NFLPlayerID": "NFLP-1",
                        "Round": 1,
                        "PositionInRound": 5,
                        "OverallPick": 5,
                        "Team": "TT",
                    }]
                }
            }

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, drafts)
            item = grouped[2025][0]
            self.assertEqual("NFLP-1", item["NFLPlayerID"])
            self.assertEqual(74, item["Measurements"]["HeightInches"])
            self.assertEqual(5, item["Draft"]["OverallPick"])
            self.assertEqual([], conflicts)

    def test_combine_never_name_matches_without_pfr(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "player_name": "Same Name",
                "pos": "RB",
            }])
            canonical = [{"NFLPlayerID": "NFLP-1", "Name": "Same Name", "IDs": {}}]
            grouped, _ = build_combine_files(combine_dataset(raw), canonical, {})
            self.assertIsNone(grouped[2025][0]["NFLPlayerID"])

    def test_combine_draft_disagreement_is_audited_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "draft_year": "2025",
                "draft_round": "2",
                "draft_ovr": "50",
                "pfr_id": "PlayTe00",
                "player_name": "Test Player",
            }])
            canonical = [{"NFLPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                2025: {
                    "Picks": [{
                        "NFLPlayerID": "NFLP-1",
                        "Round": 1,
                        "PositionInRound": 5,
                        "OverallPick": 5,
                        "Team": "TT",
                    }]
                }
            }

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, drafts)
            self.assertEqual(5, grouped[2025][0]["Draft"]["OverallPick"])
            self.assertEqual(50, grouped[2025][0]["SourceDraftEvidence"]["OverallPick"])
            self.assertEqual(1, len(conflicts))
            self.assertEqual(
                {"combine": 50, "canonicalDraft": 5},
                conflicts[0]["Differences"]["OverallPick"],
            )


if __name__ == "__main__":
    unittest.main()
