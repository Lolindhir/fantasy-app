"""#988 / 4C: actual all-dataset Source-only full clean-root restore audit.

Uses the checked-in *real* Source evidence, copied byte-for-byte into a
temporary Source-only root. No pre-existing data-derived, public/data, app
output, producer, scheduler, or persistent output is read or written there.

The two complete render passes validate deterministic candidate bytes across
every observed (DatasetID, NFLObservationSeason) partition. This remains a
read-only candidate check, NOT a persisted materializer/write/no-op test.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import data_source_dir, data_derived_dir  # noqa: E402
from external_source import market_observations as market  # noqa: E402
from external_source.registry import dataset_dir, load_registry  # noqa: E402


def _source_only_clone(root: Path) -> Path:
    """Copy the minimum real Source dependencies; exclude any derived/app files."""
    original = data_source_dir(REPO_ROOT)
    replica = data_source_dir(root)
    replica.mkdir(parents=True, exist_ok=True)

    files = [
        Path("external-registry.json"),
        Path("nfl/identities/provider-mappings.json"),
        Path("market/roster-activity/sleeper/latest.json"),
    ]
    for relative in files:
        destination = replica / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original / relative, destination)
    shutil.copytree(original / "nfl" / "schedules", replica / "nfl" / "schedules")

    datasets = load_registry(REPO_ROOT)["datasets"]
    for dataset in datasets:
        if dataset["provider"] == "sleeper":
            continue
        folder = dataset_dir(REPO_ROOT, dataset) / "snapshots"
        target = dataset_dir(root, dataset) / "snapshots"
        if not folder.is_dir():
            raise AssertionError(f"Missing real Source snapshot history: {dataset['id']}")
        # Snapshots only: explicitly exclude latest pointers, _status/heartbeats,
        # raw provider cache, existing identity.json and any derived/app outputs.
        shutil.copytree(folder, target)
    return root


def _render_all(root: Path, partitions: list[dict]) -> tuple[list[dict], str]:
    """Process every discovered partition without persisting any document."""
    summary: list[dict] = []
    for entry in partitions:
        dataset_id = entry["DatasetID"]
        season = entry["ObservationSeason"]
        document = market.render_partition(root, dataset_id, season)
        observations = document["Observations"]
        assert document["ObservationSeason"] == season
        assert document["DatasetID"] == dataset_id
        assert len(observations) == entry["ObservationCount"]
        assert all(o["SourceHash"] and o["Rows"] for o in observations)
        assert all(o["SourcePath"].startswith("data-source/") for o in observations)
        assert document["Rights"]["storage"] in ("allowed", "restricted", "forbidden", "unknown")
        assert document["Rights"]["publication"] in ("allowed", "restricted", "forbidden", "unknown")
        summary.append({
            "DatasetID": dataset_id,
            "Season": season,
            "ObservationCount": len(observations),
            "RowCount": sum(len(o["Rows"]) for o in observations),
            "CandidateSHA256": market.digest(document),
            "HistoryMode": document["HistoryMode"],
        })
    # Summary contains only dataset identifiers, counts and digests, no provider
    # raw ranking payloads. A stable aggregate digest is safe for CI evidence.
    combined = hashlib.sha256(
        json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return summary, combined


class RealMarketFullCleanRootTest(unittest.TestCase):
    def test_all_registry_datasets_rebuild_twice_from_real_source_only(self) -> None:
        registry = load_registry(REPO_ROOT)
        self.assertEqual(19, len(registry["datasets"]))
        with tempfile.TemporaryDirectory(prefix="market-source-restore-") as temporary:
            clean_root = _source_only_clone(Path(temporary))
            self.assertFalse(data_derived_dir(clean_root).exists())
            self.assertFalse((clean_root / "public").exists())
            source_inventory = market.inventory(clean_root)
            self.assertEqual(
                {d["id"] for d in registry["datasets"]},
                {entry["DatasetID"] for entry in source_inventory},
            )
            self.assertEqual(source_inventory, market.inventory(clean_root))
            self.assertEqual(2, sum(x["HistoryMode"] == "latest-only" for x in source_inventory))
            self.assertTrue(all(x["ObservationCount"] >= 1 for x in source_inventory))
            self.assertEqual(
                len(source_inventory),
                len({(x["DatasetID"], x["ObservationSeason"]) for x in source_inventory}),
            )

            first, hash_first = _render_all(clean_root, source_inventory)
            self.assertFalse(data_derived_dir(clean_root).exists())
            second, hash_second = _render_all(clean_root, source_inventory)
            self.assertEqual(first, second, "Second complete Source-only render drifted")
            self.assertEqual(hash_first, hash_second)
            self.assertFalse(data_derived_dir(clean_root).exists())
            self.assertFalse((clean_root / "public").exists())
            self.assertGreater(sum(row["RowCount"] for row in first), 0)

            # Explicit audit output is metadata only, no proprietary provider rows.
            audit = {
                "Audit": "all-dataset-source-only-clean-root",
                "DatasetCount": len({e["DatasetID"] for e in first}),
                "PartitionCount": len(first),
                "ObservationCount": sum(e["ObservationCount"] for e in first),
                "RowCount": sum(e["RowCount"] for e in first),
                "FirstPassSHA256": hash_first,
                "SecondPassSHA256": hash_second,
                "NoDerivedWritten": not data_derived_dir(clean_root).exists(),
                "SleeperHistory": "latest-only; archive not invented",
                "Scope": "candidate-only; persistent writer and rights gate untested",
            }
            print("MARKET_FULL_RESTORE_AUDIT " + json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
