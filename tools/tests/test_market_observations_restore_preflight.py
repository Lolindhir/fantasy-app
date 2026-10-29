"""#988 4C preflight: isolated Source-only restore and semantic invalidation.

These fixtures live under a temporary directory and are never published. They
prove the *candidate* market-observations renderer does not read existing
data-derived files; they do not claim global all-dataset restore or rights
clearance for a persistent writer.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source import market_observations as market  # noqa: E402
from external_source.registry import dataset_dir, load_registry  # noqa: E402

DATASET = "fantasycalc.value.dynasty-superflex-ppr-8-team"
FIELDS = ("name", "Rank", "position", "asset_type", "source_asset_id", "value", "sleeper_id")


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")


class SourceOnlyRestoreFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dataset = copy.deepcopy(next(
            entry for entry in load_registry(ROOT)["datasets"] if entry["id"] == DATASET
        ))
        self.registry = self.root / "data-source" / "external-registry.json"
        self.mapping = self.root / "data-source" / "nfl" / "identities" / "provider-mappings.json"
        self.ranking_root = dataset_dir(self.root, self.dataset)
        save_json(self.registry, {"schemaVersion": 1, "datasets": [self.dataset]})
        save_json(
            self.root / "data-source" / "nfl" / "schedules" / "2026.json",
            {"Season": 2026, "Games": [
                {"GameType": "REG", "GameDay": "2026-09-06"},
                {"GameType": "REG", "GameDay": "2026-12-31"},
            ]},
        )
        self.set_mapping("CANON-A")
        self.snapshot("2026-10-01", 20)
        self.snapshot("2026-10-02", 30)

    def set_mapping(self, canonical: str, *, valid_from: int = 2026) -> None:
        save_json(self.mapping, {"Mappings": [{
            "Provider": "Sleeper", "ExternalID": "P100",
            "CanonicalPlayerID": canonical,
            "FirstObservedSeason": valid_from,
            "LastObservedSeason": 2028,
        }]})

    def snapshot(
        self, day: str, value: int, *,
        intraday: str | None = None, schema: int = 4, raw_ranking_mismatch: bool = False,
    ) -> Path:
        directory = self.ranking_root / "snapshots" / day
        if intraday is not None:
            directory = directory / intraday
        csv = (
            ",".join(FIELDS) + "\n"
            + f"Fixture Player,1,QB,player,P100,{value},P100\n"
            + "Future Draft Pick,2,PICK,draft_pick,2027-1,5,\n"
        )
        ranking = directory / "ranking.csv"
        ranking.parent.mkdir(parents=True, exist_ok=True)
        ranking.write_text(csv, encoding="utf-8")
        save_json(directory / "metadata.json", {
            "schema_version": schema,
            "ranking_id": "dynasty-superflex-ppr-8-team",
            "fetched_at": f"{day}T10:00:00Z",
            "snapshot": {
                "ranking_sha256": hashlib.sha256(csv.encode("utf-8")).hexdigest(),
                "row_count": 2,
                "csv_columns": list(FIELDS),
            },
        })
        if raw_ranking_mismatch:
            ranking.write_text(csv.replace(str(value), "999"), encoding="utf-8")
        return directory

    def candidate(self) -> dict:
        return market.render_partition(self.root, DATASET, 2026)

    def first_and_second(self, doc: dict) -> tuple[dict, dict]:
        return doc["Observations"][0], doc["Observations"][1]

    def test_source_only_restore_is_stable_without_or_with_untrusted_derived(self) -> None:
        self.assertFalse((self.root / "data-derived").exists())
        before = self.candidate()
        sha = market.digest(before)
        self.assertEqual(2, len(before["Observations"]))
        self.assertEqual("CANON-A", before["Observations"][0]["Rows"][0]["CanonicalPlayerID"])
        self.assertEqual("not-a-player", before["Observations"][0]["Rows"][1]["IdentityStatus"])
        self.assertEqual(market.canonical_json(before), market.canonical_json(self.candidate()))
        self.assertFalse((self.root / "data-derived").exists())
        # Even a poisoned old result in a temporary mirror must not influence the rebuild.
        destination = market.candidate_path(self.root, DATASET, 2026)
        save_json(destination, {"Fake": "stale wrong derived data"})
        self.assertEqual(sha, market.digest(self.candidate()))
        self.assertEqual({"Fake": "stale wrong derived data"}, json.loads(destination.read_text()))

    def test_heartbeat_and_ranked_latest_pointer_are_not_semantic_inputs(self) -> None:
        before = market.digest(self.candidate())
        save_json(self.root / "data-source" / "market" / "_status" / "fantasycalc.json", {
            "fetched_at": "2026-10-17T10:00:00Z", "status": "success",
        })
        save_json(self.ranking_root / "latest.json", {
            "raw_fetched_at": "2026-10-17T10:00:00Z",
            "freshness_status": "live_fetch", "ranking_file": "irrelevant",
        })
        self.assertEqual(before, market.digest(self.candidate()))

    def test_mapping_correction_invalidates_candidate_but_not_snapshot_hashes(self) -> None:
        original = self.candidate()
        self.set_mapping("CANON-B")
        changed = self.candidate()
        self.assertNotEqual(market.digest(original), market.digest(changed))
        self.assertEqual(
            [o["SourceHash"] for o in original["Observations"]],
            [o["SourceHash"] for o in changed["Observations"]],
        )
        self.assertEqual("CANON-B", changed["Observations"][0]["Rows"][0]["CanonicalPlayerID"])
        self.assertEqual("resolved", changed["Observations"][0]["Rows"][0]["IdentityStatus"])
        self.set_mapping("CANON-B", valid_from=2027)
        expired = self.candidate()
        self.assertIsNone(expired["Observations"][0]["Rows"][0]["CanonicalPlayerID"])
        self.assertEqual("unresolved", expired["Observations"][0]["Rows"][0]["IdentityStatus"])
        self.assertNotEqual(market.digest(changed), market.digest(expired))

    def test_older_snapshot_correction_invalidates_partition_not_later_evidence(self) -> None:
        before = self.candidate()
        self.snapshot("2026-10-01", 25)
        after = self.candidate()
        first_before, second_before = self.first_and_second(before)
        first_after, second_after = self.first_and_second(after)
        self.assertNotEqual(market.digest(before), market.digest(after))
        self.assertNotEqual(first_before["SourceHash"], first_after["SourceHash"])
        self.assertEqual(second_before, second_after)
        self.assertEqual("25", first_after["Rows"][0]["ProviderValues"]["value"])

    def test_schema_registry_rights_and_renderer_versions_invalidate(self) -> None:
        baseline = self.candidate()
        self.snapshot("2026-10-01", 20, schema=3)
        old_schema = self.candidate()
        self.assertNotEqual(market.digest(baseline), market.digest(old_schema))
        self.assertEqual(3, old_schema["Observations"][0]["SourceSchemaVersion"])

        self.dataset["rights"]["storage"] = "allowed"  # synthetic test, not licensing approval
        self.dataset["format"]["providerTeamCount"] = 10
        save_json(self.registry, {"schemaVersion": 1, "datasets": [self.dataset]})
        new_registry = self.candidate()
        self.assertNotEqual(market.digest(old_schema), market.digest(new_registry))
        self.assertEqual("allowed", new_registry["Rights"]["storage"])
        self.assertEqual(10, new_registry["Format"]["providerTeamCount"])
        with patch.object(market, "PREVIEW_RENDERER_VERSION", market.PREVIEW_RENDERER_VERSION + 1):
            bumped = self.candidate()
        self.assertNotEqual(market.digest(new_registry), market.digest(bumped))

    def test_intraday_addition_changes_observation_manifest_stably(self) -> None:
        before = self.candidate()
        self.snapshot("2026-10-02", 35, intraday="180000Z-12345678")
        after = self.candidate()
        self.assertEqual(3, len(after["Observations"]))
        self.assertNotEqual(market.digest(before), market.digest(after))
        self.assertIn("180000Z-12345678", after["Observations"][-1]["SnapshotID"])
        self.assertEqual(market.digest(after), market.digest(self.candidate()))
        self.assertEqual(2, len(before["Observations"]))

    def test_missing_or_tampered_old_source_fails_closed_not_last_good_fallback(self) -> None:
        self.snapshot("2026-10-01", 20, raw_ranking_mismatch=True)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.candidate()
        self.snapshot("2026-10-01", 20)
        incomplete = self.ranking_root / "snapshots" / "2026-10-02" / "200000Z-abcdef12"
        incomplete.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "ranking missing"):
            self.candidate()



    def test_source_correction_is_limited_to_discovered_season_partition(self) -> None:
        save_json(
            self.root / "data-source" / "nfl" / "schedules" / "2027.json",
            {"Season": 2027, "Games": [
                {"GameType": "REG", "GameDay": "2027-09-06"},
                {"GameType": "REG", "GameDay": "2027-12-31"},
            ]},
        )
        self.snapshot("2027-10-01", 50)
        listing = market.inventory(self.root)
        self.assertEqual(
            [(2026, 2), (2027, 1)],
            [(row["ObservationSeason"], row["ObservationCount"]) for row in listing],
        )
        before_2026 = market.digest(self.candidate())
        before_2027 = market.digest(market.render_partition(self.root, DATASET, 2027))
        self.snapshot("2026-10-01", 44)
        self.assertNotEqual(before_2026, market.digest(self.candidate()))
        self.assertEqual(
            before_2027, market.digest(market.render_partition(self.root, DATASET, 2027))
        )


if __name__ == "__main__":
    unittest.main()
