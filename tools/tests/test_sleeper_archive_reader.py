"""#988 4A.3: real-schema, ephemeral combined Sleeper archive reader regression.

No historical Sleeper data is fabricated or committed: the current checked-in
latest is copied as a test fixture, with timestamps modified *only* in the
temporary root to exercise the future archive contract.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source import market_observations as market  # noqa: E402
from external_source.registry import load_registry  # noqa: E402
from external_source.sleeper_snapshot_discovery import (  # noqa: E402
    discover_sleeper_snapshots,
)


class SleeperArchivedHistoryReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="sleeper-archive-reader-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        source = self.root / "data-source"
        source.mkdir(parents=True)
        original = REPO_ROOT / "data-source"
        all_datasets = load_registry(REPO_ROOT)["datasets"]
        sleeve = [row for row in all_datasets if row["provider"] == "sleeper"]
        self.assertEqual(2, len(sleeve))
        (source / "external-registry.json").write_text(
            json.dumps({"schemaVersion": 1, "datasets": sleeve}), encoding="utf-8",
        )
        for name in (
            "nfl/schedules/2026.json",
            "nfl/identities/provider-mappings.json",
            "market/roster-activity/sleeper/latest.json",
        ):
            dest = source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / name, dest)
        self.snapshots = source / "market/roster-activity/sleeper/snapshots"
        self.latest_path = source / "market/roster-activity/sleeper/latest.json"
        self.latest = json.loads(self.latest_path.read_text(encoding="utf-8"))
        self.latest_original_bytes = self.latest_path.read_bytes()

    def append_fixture(self, observed: datetime) -> Path:
        doc = copy.deepcopy(self.latest)
        doc.pop("comparison")
        doc["generated_at"] = observed.isoformat()
        slug = f"{observed:%H%M%S}Z-{doc['semantic_fingerprint'][:8]}"
        path = self.snapshots / observed.date().isoformat() / slug / "observation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return path

    def test_latest_only_fallback_then_persisted_two_day_source_without_backfill(self) -> None:
        first = market.inventory(self.root)
        self.assertEqual(2, len(first))
        self.assertTrue(all(x["HistoryMode"] == "latest-only" for x in first))
        self.assertTrue(all(x["ObservationCount"] == 1 for x in first))
        original = market.render_partition(self.root, "sleeper.trending.add", 2026)
        self.assertTrue(original["Observations"][0]["SourcePath"].endswith("latest.json"))

        base = datetime(2026, 10, 17, 10, 1, 2, tzinfo=timezone.utc)
        self.append_fixture(base)
        next_day = base + timedelta(days=1)
        self.append_fixture(next_day)
        observations = discover_sleeper_snapshots(self.snapshots)
        self.assertEqual(2, len(observations))
        self.assertEqual(2, len(market.inventory(self.root)))
        for action in ("add", "drop"):
            dataset_id = f"sleeper.trending.{action}"
            info = next(x for x in market.inventory(self.root) if x["DatasetID"] == dataset_id)
            self.assertEqual("persisted-snapshots", info["HistoryMode"])
            self.assertEqual(2, info["ObservationCount"])
            rendered = market.render_partition(self.root, dataset_id, 2026)
            self.assertEqual("persisted-snapshots", rendered["HistoryMode"])
            self.assertEqual(2, len(rendered["Observations"]))
            self.assertTrue(all(
                o["SourcePath"].endswith("observation.json")
                and "snapshots/" in o["SourcePath"]
                and len(o["Rows"]) == len(self.latest["players"])
                for o in rendered["Observations"]
            ))
            self.assertTrue(all(
                "comparison" not in value for o in rendered["Observations"]
                for row in o["Rows"] for value in (row["ProviderValues"],)
            ))
            self.assertEqual(
                market.digest(rendered), market.digest(
                    market.render_partition(self.root, dataset_id, 2026)
                ),
            )
        self.assertEqual(self.latest_original_bytes, self.latest_path.read_bytes())

    def test_archive_missing_document_and_tampered_schema_fail_closed(self) -> None:
        base = datetime(2026, 10, 17, 10, 1, 2, tzinfo=timezone.utc)
        path = self.append_fixture(base)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing immutable Sleeper observation"):
            market.inventory(self.root)
        path = self.append_fixture(base)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["comparison"] = {"baseline": False}
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "comparison leaked"):
            market.inventory(self.root)

    def test_utc_clock_fingerprint_and_provider_identity_must_match_path(self) -> None:
        base = datetime(2026, 10, 17, 10, 1, 2, tzinfo=timezone.utc)
        path = self.append_fixture(base)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["semantic_fingerprint"] = "f" * 64
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            market.inventory(self.root)
        path.unlink()
        path = self.append_fixture(base)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["generated_at"] = "2026-10-17T10:02:00+00:00"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "time mismatch"):
            market.inventory(self.root)


if __name__ == "__main__":
    unittest.main()
