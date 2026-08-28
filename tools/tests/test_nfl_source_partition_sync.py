import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset, REGISTRY_SCHEMA_VERSION, load_registry, sync_dataset


def partitioned_dataset(root: Path, *, availability: str = "current-season-may-be-unavailable") -> Dataset:
    return Dataset(
        id="x.stats",
        provider="x",
        upstream="x",
        source_url="https://example.invalid/stats_{season}.csv",
        raw_path=root / "source-data/providers/x/stats/{season}.csv",
        metadata_path=root / "source-data/providers/x/stats/{season}.metadata.json",
        required_columns=("season", "player_id"),
        minimum_rows=1,
        kind="stats",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="x",
        attribution="x",
        lifecycle_class="seasonal-finalizable",
        partition_key="season-week",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="csv",
        availability_policy=availability,
        materialize=False,
    )


class NflSourcePartitionSyncTests(unittest.TestCase):
    def test_partitioned_dataset_resolves_season_url_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = partitioned_dataset(Path(tmp))
            self.assertTrue(str(dataset.raw_path_for(2026)).endswith("/2026.csv"))
            self.assertTrue(str(dataset.metadata_path_for(2026)).endswith("/2026.metadata.json"))
            self.assertTrue(dataset.source_url_for(2026).endswith("stats_2026.csv"))

    def test_current_season_404_is_not_yet_available_and_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = partitioned_dataset(Path(tmp))
            error = urllib.error.HTTPError(dataset.source_url_for(2026), 404, "not found", None, None)
            with patch("nfl_source_data_lib.common.download", side_effect=error):
                first = sync_dataset(dataset, season=2026, current_season=2026)
                second = sync_dataset(dataset, season=2026, current_season=2026)

            self.assertEqual("not-yet-available", first["status"])
            self.assertEqual("not-yet-available", second["status"])
            metadata = json.loads(dataset.metadata_path_for(2026).read_text(encoding="utf-8"))
            self.assertEqual("not-yet-available", metadata["availabilityStatus"])
            self.assertNotIn("retrievedAtUtc", metadata)
            self.assertFalse(dataset.raw_path_for(2026).exists())

    def test_prior_season_404_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = partitioned_dataset(Path(tmp))
            error = urllib.error.HTTPError(dataset.source_url_for(2025), 404, "not found", None, None)
            with patch("nfl_source_data_lib.common.download", side_effect=error):
                with self.assertRaises(urllib.error.HTTPError):
                    sync_dataset(dataset, season=2025, current_season=2026)

    def test_existing_prior_season_partition_is_frozen_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = partitioned_dataset(Path(tmp))
            raw_path = dataset.raw_path_for(2025)
            raw_path.parent.mkdir(parents=True)
            raw_path.write_text("season,player_id\n2025,A\n", encoding="utf-8")

            with patch("nfl_source_data_lib.common.download") as downloader:
                result = sync_dataset(dataset, season=2025, current_season=2026)

            self.assertEqual("frozen-existing", result["status"])
            downloader.assert_not_called()

    def test_registry_v3_requires_season_templates_for_partitioned_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source-data").mkdir()
            registry = {
                "schemaVersion": REGISTRY_SCHEMA_VERSION,
                "datasets": [{
                    "id": "x.bad",
                    "provider": "x",
                    "upstream": "x",
                    "sourceMode": "season-partitioned",
                    "sourceUrl": "https://example.invalid/x.csv",
                    "sourceFormat": "csv",
                    "rawPath": "providers/x/raw.csv",
                    "metadataPath": "providers/x/meta.json",
                    "requiredColumns": ["a"],
                    "minimumRows": 1,
                    "availabilityPolicy": "current-season-may-be-unavailable",
                    "materialize": False,
                    "kind": "stats",
                    "refreshPolicy": "current-season",
                    "retentionPolicy": "permanent-by-season",
                    "lifecycle": {
                        "class": "seasonal-finalizable",
                        "partitionKey": "season",
                        "finalization": "freeze-prior-seasons",
                        "repairPolicy": "explicit-force",
                    },
                    "license": "x",
                    "attribution": "x",
                }],
            }
            (root / "source-data/registry.json").write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry(root)


if __name__ == "__main__":
    unittest.main()
