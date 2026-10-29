"""#988 4D: scoped, source-only market-observations partition invalidation tests."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source import market_observations as market  # noqa: E402
from external_source import market_observations_product as product  # noqa: E402
from tools.tests.test_market_observations_restore_preflight import (  # noqa: E402
    SourceOnlyRestoreFixture, save_json, DATASET,
)


class MarketProductPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        # Existing canonical Source-only synthetic fixture. Use its own temp
        # dir but do not inherit the original test cases a second time.
        self.fixture = SourceOnlyRestoreFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tmp.cleanup)
        self.root = self.fixture.root

    def plan(self, previous=None):
        return product.plan_partitions(self.root, previous=previous)

    def test_candidate_plan_new_then_identical_second_run_is_noop(self) -> None:
        initial = self.plan()
        self.assertEqual({"new": 1, "changed": 0, "unchanged": 0, "orphaned": 0}, initial["Counts"])
        self.assertEqual("read-only; no writes, scheduler, or provider fetch", initial["Mode"])
        entry = initial["Partitions"][0]
        self.assertEqual(DATASET, entry["DatasetID"])
        self.assertEqual(2026, entry["ObservationSeason"])
        self.assertEqual(2, entry["ObservationCount"])
        self.assertEqual(4, entry["RowCount"])
        self.assertEqual("unknown", entry["Rights"]["Storage"])
        self.assertEqual("unknown", entry["Rights"]["Publication"])
        self.assertIs(False, entry["Rights"]["WriterEnabled"])
        self.assertEqual(2, len(entry["SourceEvidence"]))
        self.assertEqual(
            "data-source/nfl/identities/provider-mappings.json",
            entry["Dependencies"]["CanonicalMappingFile"],
        )
        self.assertFalse(market.candidate_path(self.root, DATASET, 2026).exists())

        second = self.plan(initial)
        self.assertEqual({"new": 0, "changed": 0, "unchanged": 1, "orphaned": 0}, second["Counts"])
        self.assertEqual(entry["CandidateSHA256"], second["Partitions"][0]["CandidateSHA256"])
        self.assertFalse((self.root / "data-derived").exists())

    def test_heartbeat_and_latest_pointer_only_do_not_dirty(self) -> None:
        baseline = self.plan()
        save_json(self.fixture.ranking_root / "latest.json", {
            "fetched_at": "2026-10-17T12:00:00Z", "ranking_file": "not/history",
        })
        save_json(self.root / "data-source/market/_status/fantasycalc.json", {
            "fetched_at": "2026-10-17T12:00:00Z", "state": "success",
        })
        self.assertEqual(1, self.plan(baseline)["Counts"]["unchanged"])

    def test_historical_source_and_mapping_corrections_dirty_only_partition(self) -> None:
        baseline = self.plan()
        self.fixture.snapshot("2026-10-01", 55)
        changed = self.plan(baseline)
        self.assertEqual(1, changed["Counts"]["changed"])
        self.assertNotEqual(
            baseline["Partitions"][0]["CandidateSHA256"],
            changed["Partitions"][0]["CandidateSHA256"],
        )
        self.fixture.set_mapping("CANON-B")
        mapped = self.plan(changed)
        self.assertEqual(1, mapped["Counts"]["changed"])
        self.assertEqual(
            changed["Partitions"][0]["SourceEvidence"],
            mapped["Partitions"][0]["SourceEvidence"],
        )
        self.assertEqual(1, self.plan(mapped)["Counts"]["unchanged"])

    def test_registry_rights_change_dirty_but_never_enable_writer(self) -> None:
        original = self.plan()
        self.fixture.dataset["rights"]["storage"] = "allowed"
        self.fixture.dataset["rights"]["publication"] = "allowed"
        save_json(self.fixture.registry, {
            "schemaVersion": 1, "datasets": [self.fixture.dataset],
        })
        changed = self.plan(original)
        self.assertEqual(1, changed["Counts"]["changed"])
        self.assertEqual("allowed", changed["Partitions"][0]["Rights"]["Storage"])
        self.assertIs(False, changed["Partitions"][0]["Rights"]["WriterEnabled"])

    def test_registry_phase_policy_changes_dirty_even_with_same_provider_rows(self) -> None:
        baseline = self.plan()
        self.fixture.dataset["seasonPolicy"]["regular_season"] = "inactive"
        save_json(self.fixture.registry, {
            "schemaVersion": 1, "datasets": [self.fixture.dataset],
        })
        changed = self.plan(baseline)
        self.assertEqual(1, changed["Counts"]["changed"])
        self.assertEqual(
            baseline["Partitions"][0]["CandidateSHA256"],
            changed["Partitions"][0]["CandidateSHA256"],
        )
        self.assertEqual(
            "inactive", changed["Partitions"][0]["Dependencies"]["RegistrySeasonPolicy"]["regular_season"],
        )

    def test_orphaned_prior_partition_is_reported_but_never_deleted(self) -> None:
        baseline = self.plan()
        stale = dict(baseline["Partitions"][0])
        stale["ObservationSeason"] = 2027
        baseline["Partitions"].append(stale)
        destination = self.root / "data-derived" / "market-observations" / DATASET / "2027.json"
        save_json(destination, {"previous": "do not delete"})
        plan = self.plan(baseline)
        self.assertEqual({"new": 0, "changed": 0, "unchanged": 1, "orphaned": 1}, plan["Counts"])
        orphan = next(p for p in plan["Partitions"] if p["Change"] == "orphaned")
        self.assertIs(False, orphan["DeletionAuthorized"])
        self.assertEqual({"previous": "do not delete"}, json.loads(destination.read_text()))

    def test_unknown_previous_schema_duplicate_or_invalid_hash_fails_closed(self) -> None:
        baseline = self.plan()
        prior = dict(baseline, PlanSchemaVersion=2)
        with self.assertRaisesRegex(product.ProductPlanError, "PlanSchemaVersion"):
            self.plan(prior)
        duplicate = dict(baseline, Partitions=baseline["Partitions"] * 2)
        with self.assertRaisesRegex(product.ProductPlanError, "Duplicate previous"):
            self.plan(duplicate)
        invalid = dict(baseline, Partitions=[dict(baseline["Partitions"][0], CandidateSHA256="bad")])
        with self.assertRaisesRegex(product.ProductPlanError, "invalid partition"):
            self.plan(invalid)

    def test_product_adapter_version_bump_invalidates_without_source_change(self) -> None:
        baseline = self.plan()
        with patch.object(product, "PRODUCT_ADAPTER_VERSION", product.PRODUCT_ADAPTER_VERSION + 1):
            bumped = self.plan(baseline)
            self.assertEqual(1, bumped["Counts"]["changed"])
            self.assertEqual(
                baseline["Partitions"][0]["CandidateSHA256"],
                bumped["Partitions"][0]["CandidateSHA256"],
            )

    def test_historical_snapshot_correction_dirties_only_its_season_partition(self) -> None:
        save_json(
            self.root / "data-source" / "nfl" / "schedules" / "2027.json",
            {"Season": 2027, "Games": [
                {"GameType": "REG", "GameDay": "2027-09-06"},
                {"GameType": "REG", "GameDay": "2027-12-31"},
            ]},
        )
        self.fixture.snapshot("2027-10-01", 50)
        initial = self.plan()
        self.assertEqual(2, initial["Counts"]["new"])
        self.fixture.snapshot("2026-10-01", 77)
        changed = self.plan(initial)
        self.assertEqual(1, changed["Counts"]["changed"])
        self.assertEqual(1, changed["Counts"]["unchanged"])
        by_season = {row["ObservationSeason"]: row for row in changed["Partitions"]}
        self.assertEqual("changed", by_season[2026]["Change"])
        self.assertEqual("unchanged", by_season[2027]["Change"])
        self.assertTrue(
            by_season[2027]["Dependencies"]["SeasonScheduleFile"].endswith("/2027.json")
        )

    def test_dataset_filter_and_cli_never_output_raw_player_data(self) -> None:
        with self.assertRaises(ValueError):
            product.plan_partitions(self.root, dataset_ids=["wrong.dataset.id"])
        result = self.plan()
        only = product.plan_partitions(self.root, dataset_ids=[DATASET], previous=result)
        self.assertEqual(1, only["Counts"]["unchanged"])
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = product.main(["--repo-root", str(self.root), "--dataset-id", DATASET])
        self.assertEqual(0, code)
        data = json.loads(stream.getvalue())
        self.assertEqual(1, data["Counts"]["new"])
        self.assertNotIn("Fixture Player", stream.getvalue())
        self.assertNotIn("Future Draft Pick", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
